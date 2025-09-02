"""Performance optimization for analytics operations."""

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for analytics operations."""

    operation: str
    duration: float
    memory_usage: Optional[float] = None
    rows_processed: int = 0
    cache_hit: bool = False


class AnalyticsOptimizer:
    """Performance optimizer for analytics operations."""

    def __init__(self, db_connection):
        self.db_connection = db_connection
        self.cache = {}
        self.cache_size_limit = 100
        self.performance_metrics = []

    def optimize_query_for_sampling(
        self, query: str, table_name: str, sample_size: int = 10000
    ) -> str:
        """Optimize queries for large datasets using sampling."""
        # Get table row count
        try:
            count_query = f"SELECT COUNT(*) as count FROM {table_name}"
            count_result = pd.read_sql(count_query, self.db_connection.get_connection())
            total_rows = count_result["count"].iloc[0]

            # If table is large, add sampling
            if total_rows > sample_size:
                # Use TABLESAMPLE for DuckDB
                if "FROM " in query.upper():
                    # Replace table name with sampled version
                    query = query.replace(
                        f"FROM {table_name}",
                        f"FROM (SELECT * FROM {table_name} USING SAMPLE {sample_size})",
                    )
                    logger.info(
                        f"Applied sampling to query: {sample_size} rows from {total_rows} total"
                    )

        except Exception as e:
            logger.warning(f"Could not apply sampling optimization: {e}")

        return query

    def get_optimal_chunk_size(self, table_name: str, base_size: int = 1000) -> int:
        """Calculate optimal chunk size based on table characteristics."""
        try:
            # Get table info
            table_info = self.db_connection.get_table_info(table_name)
            row_count = table_info.get("row_count", 0)
            column_count = len(table_info.get("columns", []))

            # Adjust chunk size based on table size and complexity
            if row_count > 1000000:  # Large table
                chunk_size = min(base_size * 2, 5000)
            elif row_count > 100000:  # Medium table
                chunk_size = base_size * 1.5
            else:  # Small table
                chunk_size = base_size

            # Adjust for column count
            if column_count > 50:
                chunk_size = int(chunk_size * 0.7)  # Reduce for wide tables
            elif column_count > 100:
                chunk_size = int(chunk_size * 0.5)

            return max(int(chunk_size), 100)  # Minimum chunk size

        except Exception as e:
            logger.warning(f"Could not calculate optimal chunk size: {e}")
            return base_size

    def should_use_progressive_loading(self, estimated_result_size: int) -> bool:
        """Determine if progressive loading should be used."""
        # Use progressive loading for large result sets
        return estimated_result_size > 50000

    def estimate_result_size(self, query: str) -> int:
        """Estimate the size of query results."""
        try:
            # Create a COUNT version of the query
            count_query = f"SELECT COUNT(*) as count FROM ({query}) as subq"
            count_result = pd.read_sql(count_query, self.db_connection.get_connection())
            return count_result["count"].iloc[0]
        except Exception as e:
            logger.warning(f"Could not estimate result size: {e}")
            return 0

    def optimize_statistics_query(
        self,
        table_name: str,
        column_name: str,
        operation: str,
        sample_size: int = 10000,
    ) -> str:
        """Optimize statistics queries for better performance."""
        base_query = f"SELECT * FROM {table_name} WHERE {column_name} IS NOT NULL"

        # Check if we need sampling
        optimized_query = self.optimize_query_for_sampling(
            base_query, table_name, sample_size
        )

        return optimized_query

    def cache_result(self, key: str, result: Any) -> None:
        """Cache result with size limit."""
        if len(self.cache) >= self.cache_size_limit:
            # Remove oldest entry (simple LRU)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        self.cache[key] = {"result": result, "timestamp": time.time()}

    def get_cached_result(self, key: str, max_age: int = 300) -> Optional[Any]:
        """Get cached result if still valid."""
        if key in self.cache:
            cached = self.cache[key]
            if time.time() - cached["timestamp"] < max_age:
                return cached["result"]
            else:
                # Remove expired entry
                del self.cache[key]
        return None

    def record_performance(
        self,
        operation: str,
        duration: float,
        rows_processed: int = 0,
        cache_hit: bool = False,
    ) -> None:
        """Record performance metrics."""
        metrics = PerformanceMetrics(
            operation=operation,
            duration=duration,
            rows_processed=rows_processed,
            cache_hit=cache_hit,
        )

        self.performance_metrics.append(metrics)

        # Keep only recent metrics
        if len(self.performance_metrics) > 1000:
            self.performance_metrics = self.performance_metrics[-500:]

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        if not self.performance_metrics:
            return {}

        total_operations = len(self.performance_metrics)
        cache_hits = sum(1 for m in self.performance_metrics if m.cache_hit)

        durations = [m.duration for m in self.performance_metrics]
        avg_duration = sum(durations) / len(durations)

        operations_by_type = {}
        for metric in self.performance_metrics:
            if metric.operation not in operations_by_type:
                operations_by_type[metric.operation] = []
            operations_by_type[metric.operation].append(metric.duration)

        return {
            "total_operations": total_operations,
            "cache_hit_rate": (
                cache_hits / total_operations if total_operations > 0 else 0
            ),
            "average_duration": avg_duration,
            "operations_by_type": {
                op: {
                    "count": len(durations),
                    "avg_duration": sum(durations) / len(durations),
                    "min_duration": min(durations),
                    "max_duration": max(durations),
                }
                for op, durations in operations_by_type.items()
            },
        }

    def optimize_template_execution(
        self, template_name: str, parameters: Dict[str, Any], table_name: str
    ) -> Dict[str, Any]:
        """Optimize template execution with caching and sampling."""
        # Create cache key
        cache_key = (
            f"{template_name}:{table_name}:{hash(str(sorted(parameters.items())))}"
        )

        start_time = time.time()

        # Check cache first
        cached_result = self.get_cached_result(cache_key)
        if cached_result:
            duration = time.time() - start_time
            self.record_performance(
                f"template_{template_name}",
                duration,
                len(cached_result),
                cache_hit=True,
            )
            return {
                "success": True,
                "data": cached_result,
                "cached": True,
                "execution_time": duration,
            }

        # Execute template with optimizations
        try:
            # This would integrate with the template engine
            # For now, return a placeholder
            duration = time.time() - start_time

            # Record performance
            self.record_performance(
                f"template_{template_name}", duration, 0, cache_hit=False
            )

            return {
                "success": True,
                "data": pd.DataFrame(),  # Placeholder
                "cached": False,
                "execution_time": duration,
            }

        except Exception as e:
            duration = time.time() - start_time
            self.record_performance(
                f"template_{template_name}_error", duration, 0, cache_hit=False
            )

            return {"success": False, "error": str(e), "execution_time": duration}


class ProgressiveLoader:
    """Progressive loading for large datasets."""

    def __init__(self, chunk_size: int = 1000):
        self.chunk_size = chunk_size
        self.loaded_chunks = 0
        self.total_chunks = 0

    def load_data_progressively(
        self, query: str, db_connection, progress_callback=None
    ) -> pd.DataFrame:
        """Load data in chunks with progress updates."""
        try:
            # First, get total count
            count_query = f"SELECT COUNT(*) as count FROM ({query}) as subq"
            count_result = pd.read_sql(count_query, db_connection.get_connection())
            total_rows = count_result["count"].iloc[0]

            self.total_chunks = (total_rows + self.chunk_size - 1) // self.chunk_size

            all_chunks = []

            for chunk_start in range(0, total_rows, self.chunk_size):
                chunk_query = f"""
                {query}
                LIMIT {self.chunk_size}
                OFFSET {chunk_start}
                """

                chunk_df = pd.read_sql(chunk_query, db_connection.get_connection())
                all_chunks.append(chunk_df)

                self.loaded_chunks += 1

                if progress_callback:
                    progress = self.loaded_chunks / self.total_chunks
                    progress_callback(progress)

                # Stop if we got less data than expected (end of results)
                if len(chunk_df) < self.chunk_size:
                    break

            return (
                pd.concat(all_chunks, ignore_index=True)
                if all_chunks
                else pd.DataFrame()
            )

        except Exception as e:
            logger.error(f"Error in progressive loading: {e}")
            # Fallback to regular loading
            return pd.read_sql(query, db_connection.get_connection())

    def get_progress(self) -> float:
        """Get current loading progress."""
        if self.total_chunks == 0:
            return 0.0
        return self.loaded_chunks / self.total_chunks
