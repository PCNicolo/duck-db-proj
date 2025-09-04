"""DuckDB connection management."""

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb

logger = logging.getLogger(__name__)


class DuckDBConnection:
    """Manages DuckDB database connections and configurations."""

    def __init__(self, database: Optional[str] = None, read_only: bool = False, enable_cache: bool = False):
        """
        Initialize DuckDB connection with caching support.

        Args:
            database: Path to database file. None for in-memory database.
            read_only: Whether to open database in read-only mode.
            enable_cache: Whether to enable query result caching.
        """
        self.database = database or ":memory:"
        self.read_only = read_only
        self._connection: Optional[duckdb.DuckDBPyConnection] = None
        self._config = self._get_default_config()
        
        # Query result cache
        self.enable_cache = enable_cache
        self._query_cache = {}
        self._cache_max_size = 50  # Maximum cached queries
        self._cache_ttl = 300  # Cache TTL in seconds (5 minutes)
        self._cache_timestamps = {}

    def _get_default_config(self) -> Dict[str, Any]:
        """Get optimized DuckDB configuration for performance."""
        import multiprocessing
        
        # Auto-detect optimal thread count
        cpu_count = multiprocessing.cpu_count()
        optimal_threads = min(cpu_count, 8)  # Cap at 8 for stability
        
        return {
            "threads": optimal_threads,
            "memory_limit": "8GB",  # Increased for better performance
            "max_memory": "8GB",
            "temp_directory": "/tmp/duckdb_temp",
            "enable_object_cache": True,
            "enable_http_metadata_cache": True,
            "default_null_order": "NULLS LAST",

            "checkpoint_threshold": "256MB",
            "wal_autocheckpoint": "256MB",
            "force_compression": "auto",  # Auto compression for better I/O
            "preserve_insertion_order": False,  # Better performance

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
        Execute a SQL query with caching support.

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            Query result
        """
        import time
        import hashlib
        
        # Generate cache key
        cache_key = None
        if self.enable_cache and not params and query.upper().startswith('SELECT'):
            cache_key = hashlib.md5(query.encode()).hexdigest()
            
            # Check cache
            if cache_key in self._query_cache:
                timestamp = self._cache_timestamps.get(cache_key, 0)
                if time.time() - timestamp < self._cache_ttl:
                    logger.debug(f"Cache hit for query: {query[:50]}...")
                    # Return the cached result directly - it's already a result object
                    cached_result = self._query_cache[cache_key]
                    # For SELECT queries, we need to return the actual result
                    return cached_result
                else:
                    # Cache expired
                    del self._query_cache[cache_key]
                    del self._cache_timestamps[cache_key]
        
        conn = self.connect()
        try:
            if params:
                result = conn.execute(query, params)
            else:
                result = conn.execute(query)
            
            # Cache the result if applicable (don't cache result objects, cache the data)
            if cache_key and self.enable_cache:
                # For caching, we need to fetch all data first
                try:
                    # Fetch all data from result to cache it
                    all_data = result.fetchall()
                    # Create a new result-like object that can be cached
                    cached_data = {
                        'data': all_data,
                        'description': result.description if hasattr(result, 'description') else None
                    }
                    
                    # Manage cache size
                    if len(self._query_cache) >= self._cache_max_size:
                        # Remove oldest entry
                        oldest_key = min(self._cache_timestamps, key=self._cache_timestamps.get)
                        del self._query_cache[oldest_key]
                        del self._cache_timestamps[oldest_key]
                    
                    self._query_cache[cache_key] = cached_data
                    self._cache_timestamps[cache_key] = time.time()
                    
                    # Return a new result with the fetched data
                    # We need to re-execute to get a fresh result object
                    result = conn.execute(query)
                except:
                    # If caching fails, just return the original result
                    pass
            
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

    def execute_batch(self, queries: List[str], parallel: bool = True) -> List[Any]:
        """
        Execute multiple queries in batch with optional parallelization.
        
        Args:
            queries: List of SQL queries
            parallel: Whether to execute queries in parallel
            
        Returns:
            List of query results
        """
        import concurrent.futures
        
        if not parallel or len(queries) <= 1:
            return self.execute_many(queries)
        
        results = [None] * len(queries)
        
        def execute_query_wrapper(idx_query):
            idx, query = idx_query
            try:
                return idx, self.execute(query)
            except Exception as e:
                logger.error(f"Query {idx} failed: {e}")
                return idx, None
        
        # Use ThreadPoolExecutor for parallel execution
        max_workers = min(4, len(queries))  # Limit parallel connections
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = executor.map(execute_query_wrapper, enumerate(queries))
            for idx, result in futures:
                results[idx] = result
        
        return results

    def register_csv(self, filepath: str, table_name: str) -> None:
        """Register a CSV file as a DuckDB table."""
        filepath = Path(filepath).resolve()
        if not filepath.exists():
            raise FileNotFoundError(f"CSV file not found: {filepath}")

        # Escape table name to handle special characters and keywords
        safe_table_name = f'"{table_name}"' if not table_name.startswith('"') else table_name
        query = f"CREATE OR REPLACE VIEW {safe_table_name} AS SELECT * FROM read_csv_auto('{filepath}')"
        self.execute(query)
        logger.info(f"Registered CSV as table: {table_name}")

    def register_parquet(self, filepath: str, table_name: str) -> None:
        """Register a Parquet file as a DuckDB table."""
        filepath = Path(filepath).resolve()
        if not filepath.exists():
            raise FileNotFoundError(f"Parquet file not found: {filepath}")

        # Escape table name to handle special characters and keywords
        safe_table_name = f'"{table_name}"' if not table_name.startswith('"') else table_name
        query = f"CREATE OR REPLACE VIEW {safe_table_name} AS SELECT * FROM read_parquet('{filepath}')"
        self.execute(query)
        logger.info(f"Registered Parquet as table: {table_name}")

    def list_tables(self) -> List[str]:
        """List all available tables and views."""
        result = self.execute("SHOW TABLES")
        return [row[0] for row in result.fetchall()]

    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get information about a table."""
        info = {}

        # Use safe table name for queries
        safe_table_name = f'"{table_name}"' if not table_name.startswith('"') else table_name

        # Get column information
        result = self.execute(f"DESCRIBE {safe_table_name}")
        info["columns"] = [
            {"name": row[0], "type": row[1], "null": row[2], "key": row[3]}
            for row in result.fetchall()
        ]

        # Get row count
        result = self.execute(f"SELECT COUNT(*) FROM {safe_table_name}")
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
