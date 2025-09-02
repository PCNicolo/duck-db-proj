"""DuckDB connection management."""

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb

logger = logging.getLogger(__name__)


class DuckDBConnection:
    """Manages DuckDB database connections and configurations."""

    def __init__(self, database: Optional[str] = None, read_only: bool = False):
        """
        Initialize DuckDB connection.

        Args:
            database: Path to database file. None for in-memory database.
            read_only: Whether to open database in read-only mode.
        """
        self.database = database or ":memory:"
        self.read_only = read_only
        self._connection: Optional[duckdb.DuckDBPyConnection] = None
        self._config = self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default DuckDB configuration."""
        return {
            "threads": 4,
            "memory_limit": "4GB",
            "max_memory": "4GB",
            "temp_directory": "/tmp/duckdb_temp",
            "enable_object_cache": True,
            "enable_http_metadata_cache": True,
        }

    def connect(self) -> duckdb.DuckDBPyConnection:
        """Establish connection to DuckDB."""
        if self._connection is None:
            self._connection = duckdb.connect(
                database=self.database, read_only=self.read_only, config=self._config
            )
            self._setup_extensions()
            logger.info(f"Connected to DuckDB: {self.database}")
        return self._connection

    def _setup_extensions(self) -> None:
        """Install and load required DuckDB extensions."""
        if self._connection:
            extensions = ["httpfs", "parquet", "json"]
            for ext in extensions:
                try:
                    self._connection.install_extension(ext)
                    self._connection.load_extension(ext)
                    logger.debug(f"Loaded extension: {ext}")
                except Exception as e:
                    logger.warning(f"Failed to load extension {ext}: {e}")

    @contextmanager
    def cursor(self):
        """Context manager for database cursor."""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    def execute(self, query: str, params: Optional[List[Any]] = None) -> Any:
        """
        Execute a SQL query.

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            Query result
        """
        conn = self.connect()
        try:
            if params:
                result = conn.execute(query, params)
            else:
                result = conn.execute(query)
            return result
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def execute_many(self, queries: List[str]) -> List[Any]:
        """Execute multiple SQL queries in sequence."""
        results = []
        for query in queries:
            results.append(self.execute(query))
        return results

    def register_csv(self, filepath: str, table_name: str) -> None:
        """Register a CSV file as a DuckDB table."""
        filepath = Path(filepath).resolve()
        if not filepath.exists():
            raise FileNotFoundError(f"CSV file not found: {filepath}")

        query = f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_csv_auto('{filepath}')"
        self.execute(query)
        logger.info(f"Registered CSV as table: {table_name}")

    def register_parquet(self, filepath: str, table_name: str) -> None:
        """Register a Parquet file as a DuckDB table."""
        filepath = Path(filepath).resolve()
        if not filepath.exists():
            raise FileNotFoundError(f"Parquet file not found: {filepath}")

        query = f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_parquet('{filepath}')"
        self.execute(query)
        logger.info(f"Registered Parquet as table: {table_name}")

    def list_tables(self) -> List[str]:
        """List all available tables and views."""
        result = self.execute("SHOW TABLES")
        return [row[0] for row in result.fetchall()]

    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get information about a table."""
        info = {}

        # Get column information
        result = self.execute(f"DESCRIBE {table_name}")
        info["columns"] = [
            {"name": row[0], "type": row[1], "null": row[2], "key": row[3]}
            for row in result.fetchall()
        ]

        # Get row count
        result = self.execute(f"SELECT COUNT(*) FROM {table_name}")
        info["row_count"] = result.fetchone()[0]

        return info

    def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("DuckDB connection closed")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
