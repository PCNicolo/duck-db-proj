"""SQL query execution and optimization engine."""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from .connection import DuckDBConnection

logger = logging.getLogger(__name__)


class QueryEngine:
    """Handles SQL query execution with caching and optimization."""

    def __init__(self, connection: DuckDBConnection, cache_size: int = 100):
        """
        Initialize query engine.

        Args:
            connection: DuckDB connection instance
            cache_size: Maximum number of cached query results
        """
        self.connection = connection
        self.cache_size = cache_size
        self._query_cache: Dict[str, Any] = {}
        self._query_stats: Dict[str, Dict] = {}

    def _get_cache_key(self, query: str, params: Optional[List[Any]] = None) -> str:
        """Generate cache key for query."""
        cache_data = {"query": query, "params": params}
        cache_str = json.dumps(cache_data, sort_keys=True, default=str)
        return hashlib.md5(cache_str.encode()).hexdigest()

    def execute_query(
        self,
        query: str,
        params: Optional[List[Any]] = None,
        use_cache: bool = True,
        timeout: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Execute SQL query and return results as DataFrame.

        Args:
            query: SQL query string
            params: Optional query parameters
            use_cache: Whether to use query result caching
            timeout: Query timeout in seconds

        Returns:
            Query results as pandas DataFrame
        """
        # Check cache
        cache_key = self._get_cache_key(query, params)
        if use_cache and cache_key in self._query_cache:
            logger.debug(f"Cache hit for query: {cache_key}")
            self._update_stats(cache_key, cached=True)
            return self._query_cache[cache_key]

        # Execute query
        start_time = datetime.now()
        try:
            if timeout:
                self.connection.execute(f"SET statement_timeout = '{timeout}s'")

            result = self.connection.execute(query, params)
            df = result.df()

            # Update cache
            if use_cache:
                self._update_cache(cache_key, df)

            # Update statistics
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_stats(cache_key, cached=False, execution_time=execution_time)

            logger.info(f"Query executed in {execution_time:.2f}s")
            return df

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def _update_cache(self, cache_key: str, result: pd.DataFrame) -> None:
        """Update query result cache."""
        # Implement LRU cache
        if len(self._query_cache) >= self.cache_size:
            # Remove oldest cache entry
            oldest_key = next(iter(self._query_cache))
            del self._query_cache[oldest_key]

        self._query_cache[cache_key] = result

    def _update_stats(
        self, cache_key: str, cached: bool, execution_time: Optional[float] = None
    ) -> None:
        """Update query statistics."""
        if cache_key not in self._query_stats:
            self._query_stats[cache_key] = {
                "count": 0,
                "cache_hits": 0,
                "total_time": 0,
                "avg_time": 0,
            }

        stats = self._query_stats[cache_key]
        stats["count"] += 1

        if cached:
            stats["cache_hits"] += 1
        elif execution_time:
            stats["total_time"] += execution_time
            stats["avg_time"] = stats["total_time"] / (
                stats["count"] - stats["cache_hits"]
            )

    def explain_query(self, query: str) -> str:
        """Get query execution plan."""
        explain_query = f"EXPLAIN {query}"
        result = self.connection.execute(explain_query)
        return result.fetchall()[0][1]

    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query performance."""
        analyze_query = f"EXPLAIN ANALYZE {query}"
        result = self.connection.execute(analyze_query)
        return {"plan": result.fetchall()[0][1]}

    def validate_query(self, query: str) -> bool:
        """Validate SQL query syntax."""
        try:
            # Try to prepare the query without executing
            self.connection.execute(f"PREPARE stmt AS {query}")
            self.connection.execute("DEALLOCATE stmt")
            return True
        except Exception as e:
            logger.error(f"Query validation failed: {e}")
            return False

    def build_aggregation_query(
        self,
        table: str,
        group_by: List[str],
        aggregations: Dict[str, str],
        where: Optional[str] = None,
        having: Optional[str] = None,
        order_by: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> str:
        """
        Build aggregation SQL query.

        Args:
            table: Table name
            group_by: GROUP BY columns
            aggregations: Dictionary of {alias: aggregation_expression}
            where: WHERE clause
            having: HAVING clause
            order_by: ORDER BY columns
            limit: LIMIT value

        Returns:
            SQL query string
        """
        # Build SELECT clause
        select_parts = group_by.copy()
        for alias, expr in aggregations.items():
            select_parts.append(f"{expr} AS {alias}")

        query_parts = [f"SELECT {', '.join(select_parts)}", f"FROM {table}"]

        if where:
            query_parts.append(f"WHERE {where}")

        if group_by:
            query_parts.append(f"GROUP BY {', '.join(group_by)}")

        if having:
            query_parts.append(f"HAVING {having}")

        if order_by:
            query_parts.append(f"ORDER BY {', '.join(order_by)}")

        if limit:
            query_parts.append(f"LIMIT {limit}")

        return " ".join(query_parts)

    def build_join_query(
        self,
        tables: List[Dict[str, str]],
        select_columns: List[str],
        join_conditions: List[str],
        where: Optional[str] = None,
        order_by: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> str:
        """
        Build JOIN SQL query.

        Args:
            tables: List of table definitions [{name, alias, join_type}]
            select_columns: Columns to select
            join_conditions: JOIN conditions
            where: WHERE clause
            order_by: ORDER BY columns
            limit: LIMIT value

        Returns:
            SQL query string
        """
        # Build FROM clause
        from_parts = [f"{tables[0]['name']} {tables[0].get('alias', '')}"]

        # Build JOIN clauses
        for i, table in enumerate(tables[1:], 1):
            join_type = table.get("join_type", "INNER")
            join_part = f"{join_type} JOIN {table['name']} {table.get('alias', '')}"
            if i - 1 < len(join_conditions):
                join_part += f" ON {join_conditions[i-1]}"
            from_parts.append(join_part)

        query_parts = [
            f"SELECT {', '.join(select_columns)}",
            "FROM " + " ".join(from_parts),
        ]

        if where:
            query_parts.append(f"WHERE {where}")

        if order_by:
            query_parts.append(f"ORDER BY {', '.join(order_by)}")

        if limit:
            query_parts.append(f"LIMIT {limit}")

        return " ".join(query_parts)

    def get_statistics(self) -> Dict[str, Any]:
        """Get query engine statistics."""
        total_queries = sum(s["count"] for s in self._query_stats.values())
        total_cache_hits = sum(s["cache_hits"] for s in self._query_stats.values())

        return {
            "total_queries": total_queries,
            "total_cache_hits": total_cache_hits,
            "cache_hit_rate": (
                total_cache_hits / total_queries if total_queries > 0 else 0
            ),
            "cache_size": len(self._query_cache),
            "query_stats": self._query_stats,
        }

    def clear_cache(self) -> None:
        """Clear query result cache."""
        self._query_cache.clear()
        logger.info("Query cache cleared")
