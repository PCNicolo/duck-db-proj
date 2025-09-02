"""Optimized SQL query execution with streaming, caching, and progress tracking."""

import hashlib
import json
import logging
import re
import threading
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, Tuple

import pandas as pd

from .connection import DuckDBConnection

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Query execution metrics."""

    start_time: datetime
    end_time: Optional[datetime] = None
    rows_fetched: int = 0
    chunks_fetched: int = 0
    cache_hit: bool = False
    execution_time: float = 0.0
    memory_usage: int = 0


class QueryCacheManager:
    """LRU cache manager for query results with size limits."""

    def __init__(self, max_size: int = 100, max_memory_mb: int = 100):
        """
        Initialize cache manager.

        Args:
            max_size: Maximum number of cached queries
            max_memory_mb: Maximum memory usage in MB
        """
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache = OrderedDict()
        self.memory_usage = 0
        self.stats = {"hits": 0, "misses": 0, "evictions": 0}

    def _calculate_size(self, df: pd.DataFrame) -> int:
        """Calculate approximate memory size of DataFrame."""
        return df.memory_usage(deep=True).sum()

    def get(self, key: str) -> Optional[pd.DataFrame]:
        """Get cached result if available."""
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.stats["hits"] += 1
            return self.cache[key]["data"]
        self.stats["misses"] += 1
        return None

    def put(self, key: str, data: pd.DataFrame, query: str) -> None:
        """Store result in cache with LRU eviction."""
        size = self._calculate_size(data)

        # Evict items if necessary
        while (
            len(self.cache) >= self.max_size
            or self.memory_usage + size > self.max_memory_bytes
        ):
            if not self.cache:
                break
            oldest_key, oldest_value = self.cache.popitem(last=False)
            self.memory_usage -= oldest_value["size"]
            self.stats["evictions"] += 1

        # Add new item
        self.cache[key] = {
            "data": data.copy(),
            "query": query,
            "timestamp": datetime.now(),
            "size": size,
        }
        self.memory_usage += size

    def invalidate(self, pattern: Optional[str] = None) -> int:
        """Invalidate cache entries matching pattern."""
        if pattern is None:
            count = len(self.cache)
            self.cache.clear()
            self.memory_usage = 0
            return count

        # Invalidate matching entries
        keys_to_remove = []
        for key, value in self.cache.items():
            if pattern in value["query"]:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            entry = self.cache.pop(key)
            self.memory_usage -= entry["size"]

        return len(keys_to_remove)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        hit_rate = (
            self.stats["hits"] / (self.stats["hits"] + self.stats["misses"])
            if (self.stats["hits"] + self.stats["misses"]) > 0
            else 0
        )

        return {
            **self.stats,
            "hit_rate": hit_rate,
            "size": len(self.cache),
            "memory_usage_mb": self.memory_usage / (1024 * 1024),
        }


class QueryErrorHandler:
    """Categorizes and provides solutions for query errors."""

    ERROR_PATTERNS = {
        "SYNTAX_ERROR": {
            "pattern": r"(Syntax error|Parser Error)",
            "message": "SQL syntax error detected",
            "suggestions": [
                "Check for missing commas or semicolons",
                "Verify column and table names",
                "Ensure quotes are properly closed",
            ],
        },
        "TABLE_NOT_FOUND": {
            "pattern": r"(Table .* does not exist|Catalog Error.*Table)",
            "message": "Table not found in database",
            "suggestions": [
                "Verify table name spelling",
                "Check if table has been loaded",
                "Use SHOW TABLES to list available tables",
            ],
        },
        "COLUMN_NOT_FOUND": {
            "pattern": r"(Column .* does not exist|Binder Error.*column)",
            "message": "Column not found in table",
            "suggestions": [
                "Verify column name spelling",
                "Use DESCRIBE table_name to see columns",
                "Check for case sensitivity",
            ],
        },
        "TYPE_MISMATCH": {
            "pattern": r"(Type mismatch|Conversion Error)",
            "message": "Data type mismatch",
            "suggestions": [
                "Check data types in WHERE conditions",
                "Use CAST() for type conversions",
                "Verify aggregate function usage",
            ],
        },
        "PERMISSION_DENIED": {
            "pattern": r"(Permission denied|Access denied)",
            "message": "Permission denied",
            "suggestions": ["Check file permissions", "Verify database access rights"],
        },
    }

    @classmethod
    def categorize_error(cls, error_msg: str) -> Dict[str, Any]:
        """Categorize error and provide suggestions."""
        error_str = str(error_msg)

        for error_type, config in cls.ERROR_PATTERNS.items():
            if re.search(config["pattern"], error_str, re.IGNORECASE):
                return {
                    "type": error_type,
                    "message": config["message"],
                    "suggestions": config["suggestions"],
                    "original": error_str,
                }

        return {
            "type": "UNKNOWN",
            "message": "Unknown error occurred",
            "suggestions": ["Check query syntax", "Verify table and column names"],
            "original": error_str,
        }

    @classmethod
    def suggest_correction(cls, query: str, error: Dict[str, Any]) -> Optional[str]:
        """Suggest query correction based on error type."""
        error_type = error.get("type")

        if error_type == "TABLE_NOT_FOUND":
            # Extract table name from error
            match = re.search(
                r'Table [\'"]?(\w+)[\'"]? does not exist', error["original"]
            )
            if match:
                table_name = match.group(1)
                # Suggest similar table name (would need actual table list)
                return "-- Did you mean a different table?\n-- Use SHOW TABLES to see available tables"

        elif error_type == "COLUMN_NOT_FOUND":
            # Extract column name from error
            match = re.search(
                r'Column [\'"]?(\w+)[\'"]? does not exist', error["original"]
            )
            if match:
                column_name = match.group(1)
                return f"-- Column '{column_name}' not found\n-- Use DESCRIBE table_name to see available columns"

        return None


class OptimizedQueryExecutor:
    """Enhanced query executor with streaming, progress tracking, and optimization."""

    def __init__(
        self,
        connection: DuckDBConnection,
        cache_size: int = 100,
        cache_memory_mb: int = 100,
        chunk_size: int = 1000,
        enable_progress: bool = True,
    ):
        """
        Initialize optimized query executor.

        Args:
            connection: DuckDB connection instance
            cache_size: Maximum number of cached queries
            cache_memory_mb: Maximum cache memory in MB
            chunk_size: Default chunk size for streaming
            enable_progress: Enable progress tracking
        """
        self.connection = connection
        self.chunk_size = chunk_size
        self.enable_progress = enable_progress

        # Initialize cache
        self.cache = QueryCacheManager(cache_size, cache_memory_mb)

        # Query metrics
        self.current_metrics: Optional[QueryMetrics] = None
        self.query_history: List[QueryMetrics] = []
        self.slow_query_threshold = 2.0  # seconds

        # Progress tracking
        self.progress_callback = None
        self._cancel_flag = threading.Event()

        # Connection pool (simulated with single connection for now)
        self.connection_pool_size = 5
        self._setup_connection_pool()

    def _setup_connection_pool(self):
        """Setup connection pooling for DuckDB."""
        # Note: DuckDB doesn't support true connection pooling yet
        # This is a placeholder for future implementation
        self.connection_pool = [self.connection]

    def _get_cache_key(self, query: str, params: Optional[List[Any]] = None) -> str:
        """Generate cache key for query."""
        cache_data = {"query": query.strip().lower(), "params": params}
        cache_str = json.dumps(cache_data, sort_keys=True, default=str)
        return hashlib.sha256(cache_str.encode()).hexdigest()

    def execute_streaming(
        self,
        query: str,
        chunk_size: Optional[int] = None,
        use_cache: bool = True,
        timeout: Optional[int] = None,
        progress_callback: Optional[callable] = None,
    ) -> Generator[pd.DataFrame, None, None]:
        """
        Execute query with streaming results.

        Args:
            query: SQL query string
            chunk_size: Number of rows per chunk
            use_cache: Whether to use caching
            timeout: Query timeout in seconds
            progress_callback: Callback for progress updates

        Yields:
            DataFrame chunks
        """
        chunk_size = chunk_size or self.chunk_size
        self.progress_callback = progress_callback
        self._cancel_flag.clear()

        # Check cache first
        cache_key = self._get_cache_key(query)
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.info("Cache hit - returning cached result")
                # Stream cached result in chunks
                for i in range(0, len(cached), chunk_size):
                    if self._cancel_flag.is_set():
                        break
                    yield cached.iloc[i : i + chunk_size]
                return

        # Initialize metrics
        self.current_metrics = QueryMetrics(start_time=datetime.now())

        try:
            # Set timeout if specified
            if timeout:
                self.connection.execute(f"SET statement_timeout = '{timeout}s'")

            # Execute query
            result = self.connection.execute(query)

            # Stream results in chunks
            all_chunks = []
            while True:
                if self._cancel_flag.is_set():
                    logger.info("Query cancelled by user")
                    break

                # Fetch chunk
                chunk = result.fetch_df_chunk(chunk_size)

                if chunk.empty:
                    break

                # Update metrics
                self.current_metrics.chunks_fetched += 1
                self.current_metrics.rows_fetched += len(chunk)

                # Progress callback
                if self.progress_callback:
                    self.progress_callback(
                        {
                            "rows_fetched": self.current_metrics.rows_fetched,
                            "chunks_fetched": self.current_metrics.chunks_fetched,
                            "elapsed_time": (
                                datetime.now() - self.current_metrics.start_time
                            ).total_seconds(),
                        }
                    )

                # Store for cache
                if use_cache:
                    all_chunks.append(chunk)

                yield chunk

            # Update cache with complete result
            if use_cache and all_chunks:
                complete_df = pd.concat(all_chunks, ignore_index=True)
                self.cache.put(cache_key, complete_df, query)

            # Finalize metrics
            self.current_metrics.end_time = datetime.now()
            self.current_metrics.execution_time = (
                self.current_metrics.end_time - self.current_metrics.start_time
            ).total_seconds()

            # Log slow queries
            if self.current_metrics.execution_time > self.slow_query_threshold:
                logger.warning(
                    f"Slow query detected ({self.current_metrics.execution_time:.2f}s): {query[:100]}"
                )

            # Store in history
            self.query_history.append(self.current_metrics)

        except Exception as e:
            error_info = QueryErrorHandler.categorize_error(e)
            logger.error(f"Query execution failed: {error_info['message']}")

            # Provide helpful error with suggestions
            error_msg = f"{error_info['message']}\n"
            error_msg += "Suggestions:\n"
            for suggestion in error_info["suggestions"]:
                error_msg += f"  • {suggestion}\n"

            correction = QueryErrorHandler.suggest_correction(query, error_info)
            if correction:
                error_msg += f"\n{correction}"

            raise Exception(error_msg) from e

    def execute_query(
        self,
        query: str,
        params: Optional[List[Any]] = None,
        use_cache: bool = True,
        timeout: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Execute query and return complete result.

        Args:
            query: SQL query string
            params: Optional query parameters
            use_cache: Whether to use caching
            timeout: Query timeout in seconds

        Returns:
            Complete query result as DataFrame
        """
        # Collect all chunks
        chunks = []
        for chunk in self.execute_streaming(
            query, use_cache=use_cache, timeout=timeout
        ):
            chunks.append(chunk)

        if chunks:
            return pd.concat(chunks, ignore_index=True)
        return pd.DataFrame()

    def cancel_query(self):
        """Cancel the currently running query."""
        self._cancel_flag.set()

    def estimate_query_time(self, query: str) -> float:
        """
        Estimate query execution time based on history.

        Args:
            query: SQL query string

        Returns:
            Estimated time in seconds
        """
        # Simple estimation based on query complexity
        # In production, would use ML model or statistics

        # Count operations
        query_lower = query.lower()
        complexity_score = 0

        # Add complexity for operations
        if "join" in query_lower:
            complexity_score += 2
        if "group by" in query_lower:
            complexity_score += 1.5
        if "order by" in query_lower:
            complexity_score += 1
        if "window" in query_lower or "over" in query_lower:
            complexity_score += 2.5

        # Estimate based on complexity
        base_time = 0.1
        estimated_time = base_time * (1 + complexity_score)

        # Adjust based on history if available
        if self.query_history:
            avg_time = sum(m.execution_time for m in self.query_history[-5:]) / min(
                5, len(self.query_history)
            )
            estimated_time = (estimated_time + avg_time) / 2

        return estimated_time

    def get_query_plan(self, query: str) -> Dict[str, Any]:
        """Get detailed query execution plan."""
        try:
            # Get basic explain
            explain_result = self.connection.execute(f"EXPLAIN {query}")
            basic_plan = explain_result.fetchall()[0][1]

            # Get analyze explain for cost estimates
            analyze_result = self.connection.execute(f"EXPLAIN ANALYZE {query}")
            analyze_plan = analyze_result.fetchall()[0][1]

            return {
                "basic_plan": basic_plan,
                "analyze_plan": analyze_plan,
                "estimated_time": self.estimate_query_time(query),
            }
        except Exception as e:
            logger.error(f"Failed to get query plan: {e}")
            return {"error": str(e)}

    def optimize_query(self, query: str) -> Tuple[str, List[str]]:
        """
        Suggest query optimizations.

        Args:
            query: SQL query string

        Returns:
            Tuple of (optimized_query, suggestions)
        """
        suggestions = []
        optimized = query

        # Check for common optimization opportunities
        query_lower = query.lower()

        # Suggest LIMIT for SELECT *
        if "select *" in query_lower and "limit" not in query_lower:
            suggestions.append("Consider adding LIMIT clause to SELECT * queries")
            optimized += " LIMIT 1000"

        # Suggest indexes for WHERE clauses
        if "where" in query_lower:
            suggestions.append("Ensure columns in WHERE clause are indexed")

        # Suggest column selection instead of SELECT *
        if "select *" in query_lower:
            suggestions.append(
                "Consider selecting only required columns instead of SELECT *"
            )

        # Suggest JOIN order optimization
        if query_lower.count("join") > 2:
            suggestions.append("Consider optimizing JOIN order - smallest tables first")

        return optimized, suggestions

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive query statistics."""
        cache_stats = self.cache.get_stats()

        # Calculate query statistics
        total_queries = len(self.query_history)
        slow_queries = [
            m
            for m in self.query_history
            if m.execution_time > self.slow_query_threshold
        ]

        avg_execution_time = 0
        if total_queries > 0:
            avg_execution_time = (
                sum(m.execution_time for m in self.query_history) / total_queries
            )

        return {
            "cache": cache_stats,
            "queries": {
                "total": total_queries,
                "slow_queries": len(slow_queries),
                "avg_execution_time": avg_execution_time,
                "total_rows_fetched": sum(m.rows_fetched for m in self.query_history),
            },
            "slow_query_threshold": self.slow_query_threshold,
        }

    def clear_cache(self, pattern: Optional[str] = None) -> int:
        """
        Clear cache entries.

        Args:
            pattern: Optional pattern to match queries

        Returns:
            Number of entries cleared
        """
        return self.cache.invalidate(pattern)
