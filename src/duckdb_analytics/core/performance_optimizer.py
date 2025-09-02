"""Performance optimization utilities for DuckDB queries and data handling."""

import io
import logging
import queue
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Generator, List, Optional

import duckdb
import pandas as pd
import pyarrow as pa

logger = logging.getLogger(__name__)


@dataclass
class ConnectionPoolConfig:
    """Configuration for connection pool."""

    min_connections: int = 1
    max_connections: int = 5
    connection_timeout: float = 30.0
    idle_timeout: float = 300.0
    validation_query: str = "SELECT 1"


class DuckDBConnectionPool:
    """
    Connection pool for DuckDB (simulated since DuckDB is single-writer).
    Provides connection reuse and management.
    """

    def __init__(
        self, database: str = ":memory:", config: Optional[ConnectionPoolConfig] = None
    ):
        """
        Initialize connection pool.

        Args:
            database: Database path or :memory:
            config: Pool configuration
        """
        self.database = database
        self.config = config or ConnectionPoolConfig()

        # Connection management
        self._available_connections = queue.Queue(maxsize=self.config.max_connections)
        self._in_use_connections = set()
        self._lock = threading.Lock()

        # Initialize minimum connections
        for _ in range(self.config.min_connections):
            conn = self._create_connection()
            self._available_connections.put(conn)

        # Start connection validator thread
        self._validator_thread = threading.Thread(
            target=self._validate_connections, daemon=True
        )
        self._validator_thread.start()

    def _create_connection(self) -> duckdb.DuckDBPyConnection:
        """Create a new DuckDB connection."""
        conn = duckdb.connect(self.database)

        # Set optimal configuration
        conn.execute("SET threads TO 4")
        conn.execute("SET memory_limit = '4GB'")
        conn.execute("SET enable_object_cache = true")

        return conn

    def acquire(self, timeout: Optional[float] = None) -> duckdb.DuckDBPyConnection:
        """
        Acquire a connection from the pool.

        Args:
            timeout: Maximum time to wait for connection

        Returns:
            DuckDB connection
        """
        timeout = timeout or self.config.connection_timeout

        try:
            # Try to get available connection
            conn = self._available_connections.get(timeout=timeout)

            # Validate connection
            if not self._is_valid(conn):
                conn = self._create_connection()

            with self._lock:
                self._in_use_connections.add(conn)

            return conn

        except queue.Empty:
            # No available connections, create new if under limit
            with self._lock:
                total = self._available_connections.qsize() + len(
                    self._in_use_connections
                )
                if total < self.config.max_connections:
                    conn = self._create_connection()
                    self._in_use_connections.add(conn)
                    return conn

            raise TimeoutError(f"Could not acquire connection within {timeout} seconds")

    def release(self, conn: duckdb.DuckDBPyConnection):
        """
        Release connection back to pool.

        Args:
            conn: Connection to release
        """
        with self._lock:
            if conn in self._in_use_connections:
                self._in_use_connections.remove(conn)

        # Return to available pool
        try:
            self._available_connections.put_nowait(conn)
        except queue.Full:
            # Pool is full, close connection
            try:
                conn.close()
            except:
                pass

    def _is_valid(self, conn: duckdb.DuckDBPyConnection) -> bool:
        """Check if connection is valid."""
        try:
            conn.execute(self.config.validation_query).fetchone()
            return True
        except:
            return False

    def _validate_connections(self):
        """Periodically validate idle connections."""
        while True:
            time.sleep(60)  # Check every minute

            # Validate available connections
            validated = []
            while not self._available_connections.empty():
                try:
                    conn = self._available_connections.get_nowait()
                    if self._is_valid(conn):
                        validated.append(conn)
                    else:
                        try:
                            conn.close()
                        except:
                            pass
                except queue.Empty:
                    break

            # Return validated connections
            for conn in validated:
                try:
                    self._available_connections.put_nowait(conn)
                except queue.Full:
                    try:
                        conn.close()
                    except:
                        pass

    def close_all(self):
        """Close all connections in the pool."""
        # Close in-use connections
        with self._lock:
            for conn in self._in_use_connections:
                try:
                    conn.close()
                except:
                    pass
            self._in_use_connections.clear()

        # Close available connections
        while not self._available_connections.empty():
            try:
                conn = self._available_connections.get_nowait()
                conn.close()
            except:
                pass


class DataSerializer:
    """Optimized data serialization for Streamlit and caching."""

    @staticmethod
    def dataframe_to_parquet_bytes(df: pd.DataFrame) -> bytes:
        """
        Serialize DataFrame to Parquet bytes.

        Args:
            df: DataFrame to serialize

        Returns:
            Parquet bytes
        """
        buffer = io.BytesIO()
        df.to_parquet(buffer, compression="snappy", index=False)
        return buffer.getvalue()

    @staticmethod
    def parquet_bytes_to_dataframe(data: bytes) -> pd.DataFrame:
        """
        Deserialize Parquet bytes to DataFrame.

        Args:
            data: Parquet bytes

        Returns:
            DataFrame
        """
        buffer = io.BytesIO(data)
        return pd.read_parquet(buffer)

    @staticmethod
    def dataframe_to_arrow_bytes(df: pd.DataFrame) -> bytes:
        """
        Serialize DataFrame to Arrow IPC bytes.

        Args:
            df: DataFrame to serialize

        Returns:
            Arrow IPC bytes
        """
        table = pa.Table.from_pandas(df)
        buffer = io.BytesIO()

        with pa.ipc.RecordBatchStreamWriter(buffer, table.schema) as writer:
            writer.write_table(table)

        return buffer.getvalue()

    @staticmethod
    def arrow_bytes_to_dataframe(data: bytes) -> pd.DataFrame:
        """
        Deserialize Arrow IPC bytes to DataFrame.

        Args:
            data: Arrow IPC bytes

        Returns:
            DataFrame
        """
        buffer = io.BytesIO(data)

        with pa.ipc.open_stream(buffer) as reader:
            table = reader.read_all()

        return table.to_pandas()

    @staticmethod
    def optimize_dataframe_memory(df: pd.DataFrame) -> pd.DataFrame:
        """
        Optimize DataFrame memory usage.

        Args:
            df: DataFrame to optimize

        Returns:
            Optimized DataFrame
        """
        # Optimize numeric columns
        for col in df.select_dtypes(include=["int"]).columns:
            df[col] = pd.to_numeric(df[col], downcast="integer")

        for col in df.select_dtypes(include=["float"]).columns:
            df[col] = pd.to_numeric(df[col], downcast="float")

        # Convert string columns to category if beneficial
        for col in df.select_dtypes(include=["object"]).columns:
            num_unique = df[col].nunique()
            num_total = len(df[col])

            if num_unique / num_total < 0.5:  # Less than 50% unique
                df[col] = df[col].astype("category")

        return df


class LazyDataLoader:
    """Lazy loading for large columns and datasets."""

    def __init__(self, connection, query: str, chunk_size: int = 10000):
        """
        Initialize lazy loader.

        Args:
            connection: Database connection
            query: SQL query
            chunk_size: Rows per chunk
        """
        self.connection = connection
        self.query = query
        self.chunk_size = chunk_size
        self._result = None
        self._current_chunk = 0
        self._total_rows = None

    def __iter__(self) -> Generator[pd.DataFrame, None, None]:
        """Iterate over chunks lazily."""
        self._result = self.connection.execute(self.query)

        while True:
            chunk = self._result.fetch_df_chunk(self.chunk_size)
            if chunk.empty:
                break

            yield chunk
            self._current_chunk += 1

    def get_column_lazy(
        self, column_name: str, limit: Optional[int] = None
    ) -> pd.Series:
        """
        Load a specific column lazily.

        Args:
            column_name: Column to load
            limit: Maximum rows to load

        Returns:
            Column data as Series
        """
        query = f"SELECT {column_name} FROM ({self.query}) AS subquery"
        if limit:
            query += f" LIMIT {limit}"

        result = self.connection.execute(query)
        return result.df()[column_name]

    def get_preview(self, rows: int = 100) -> pd.DataFrame:
        """
        Get preview of the dataset.

        Args:
            rows: Number of rows to preview

        Returns:
            Preview DataFrame
        """
        preview_query = f"SELECT * FROM ({self.query}) AS subquery LIMIT {rows}"
        return self.connection.execute(preview_query).df()


class QueryOptimizationHints:
    """Provides optimization hints for queries."""

    @staticmethod
    def analyze_query_plan(connection, query: str) -> Dict[str, Any]:
        """
        Analyze query plan for optimization opportunities.

        Args:
            connection: Database connection
            query: SQL query

        Returns:
            Analysis results with hints
        """
        hints = {"query": query[:500], "suggestions": [], "estimated_cost": 0}

        try:
            # Get query plan
            explain_result = connection.execute(f"EXPLAIN {query}")
            plan = explain_result.fetchall()[0][1]

            # Analyze plan for optimization opportunities
            if "FULL SCAN" in plan.upper():
                hints["suggestions"].append(
                    {
                        "type": "INDEX",
                        "message": "Query performs full table scan. Consider adding indexes.",
                        "priority": "HIGH",
                    }
                )

            if "HASH JOIN" in plan.upper():
                hints["suggestions"].append(
                    {
                        "type": "JOIN",
                        "message": "Hash join detected. Ensure join columns have appropriate indexes.",
                        "priority": "MEDIUM",
                    }
                )

            if "SORT" in plan.upper() and "INDEX" not in plan.upper():
                hints["suggestions"].append(
                    {
                        "type": "SORT",
                        "message": "Sorting without index. Consider adding index on ORDER BY columns.",
                        "priority": "MEDIUM",
                    }
                )

            # Check for missing LIMIT on large queries
            if "SELECT *" in query.upper() and "LIMIT" not in query.upper():
                hints["suggestions"].append(
                    {
                        "type": "LIMIT",
                        "message": "No LIMIT clause on SELECT *. Consider adding LIMIT for better performance.",
                        "priority": "LOW",
                    }
                )

            # Parse estimated rows from plan
            import re

            rows_match = re.search(r"rows=(\d+)", plan)
            if rows_match:
                hints["estimated_rows"] = int(rows_match.group(1))

        except Exception as e:
            logger.error(f"Failed to analyze query plan: {e}")
            hints["error"] = str(e)

        return hints

    @staticmethod
    def suggest_indexes(connection, table_name: str) -> List[str]:
        """
        Suggest indexes for a table based on common patterns.

        Args:
            connection: Database connection
            table_name: Table name

        Returns:
            List of suggested index statements
        """
        suggestions = []

        try:
            # Get table columns
            result = connection.execute(f"DESCRIBE {table_name}")
            columns = [row[0] for row in result.fetchall()]

            # Suggest indexes for common patterns
            for col in columns:
                col_lower = col.lower()

                # ID columns
                if "id" in col_lower and col_lower != "id":
                    suggestions.append(
                        f"CREATE INDEX idx_{table_name}_{col} ON {table_name}({col});"
                    )

                # Date/time columns
                if any(
                    dt in col_lower for dt in ["date", "time", "created", "updated"]
                ):
                    suggestions.append(
                        f"CREATE INDEX idx_{table_name}_{col} ON {table_name}({col});"
                    )

                # Foreign key columns
                if col_lower.endswith("_id"):
                    suggestions.append(
                        f"CREATE INDEX idx_{table_name}_{col} ON {table_name}({col});"
                    )

        except Exception as e:
            logger.error(f"Failed to suggest indexes: {e}")

        return suggestions


class MemoryManager:
    """Manages memory usage for large result sets."""

    def __init__(self, max_memory_mb: int = 500):
        """
        Initialize memory manager.

        Args:
            max_memory_mb: Maximum memory usage in MB
        """
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.current_usage = 0
        self._lock = threading.Lock()

    def can_allocate(self, size_bytes: int) -> bool:
        """Check if memory can be allocated."""
        with self._lock:
            return self.current_usage + size_bytes <= self.max_memory_bytes

    def allocate(self, size_bytes: int) -> bool:
        """
        Allocate memory.

        Args:
            size_bytes: Bytes to allocate

        Returns:
            True if allocated successfully
        """
        with self._lock:
            if self.current_usage + size_bytes <= self.max_memory_bytes:
                self.current_usage += size_bytes
                return True
            return False

    def release(self, size_bytes: int):
        """Release allocated memory."""
        with self._lock:
            self.current_usage = max(0, self.current_usage - size_bytes)

    def get_usage_percentage(self) -> float:
        """Get current memory usage percentage."""
        with self._lock:
            return (self.current_usage / self.max_memory_bytes) * 100

    @staticmethod
    def estimate_dataframe_size(df: pd.DataFrame) -> int:
        """Estimate DataFrame memory size in bytes."""
        return df.memory_usage(deep=True).sum()

    def should_spill_to_disk(self, additional_bytes: int) -> bool:
        """Check if data should be spilled to disk."""
        with self._lock:
            return (self.current_usage + additional_bytes) > (
                self.max_memory_bytes * 0.8
            )


class QueryTimeoutManager:
    """Manages query timeouts and cancellation."""

    def __init__(self, default_timeout: int = 30):
        """
        Initialize timeout manager.

        Args:
            default_timeout: Default timeout in seconds
        """
        self.default_timeout = default_timeout
        self.active_queries: Dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def set_timeout(self, query_id: str, connection, timeout: Optional[int] = None):
        """
        Set timeout for a query.

        Args:
            query_id: Query identifier
            connection: Database connection
            timeout: Timeout in seconds
        """
        timeout = timeout or self.default_timeout

        def cancel_query():
            try:
                # DuckDB doesn't support query cancellation directly
                # This is a placeholder for future implementation
                logger.warning(f"Query {query_id} timed out after {timeout} seconds")
            except Exception as e:
                logger.error(f"Failed to cancel query: {e}")

        timer = threading.Timer(timeout, cancel_query)
        timer.start()

        with self._lock:
            self.active_queries[query_id] = timer

    def clear_timeout(self, query_id: str):
        """Clear timeout for a completed query."""
        with self._lock:
            if query_id in self.active_queries:
                timer = self.active_queries.pop(query_id)
                timer.cancel()
