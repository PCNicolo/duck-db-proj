"""DuckDB connection management."""

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb

# Import connection pool for optimized performance
try:
    from .connection_pool import get_pool, DuckDBConnectionPool
    POOL_AVAILABLE = True
except ImportError:
    POOL_AVAILABLE = False

logger = logging.getLogger(__name__)


class DuckDBConnection:
    """Manages DuckDB database connections and configurations."""

    def __init__(self, database: Optional[str] = None, read_only: bool = False, enable_cache: bool = False, use_pool: bool = False):
        """
        Initialize DuckDB connection with caching and pooling support.

        Args:
            database: Path to database file. None for in-memory database.
            read_only: Whether to open database in read-only mode.
            enable_cache: Whether to enable query result caching.
            use_pool: Whether to use connection pooling.
        """
        self.database = database or ":memory:"
        self.read_only = read_only
        self._connection: Optional[duckdb.DuckDBPyConnection] = None
        self._config = self._get_default_config()
        
        # Connection pooling
        self.use_pool = use_pool and POOL_AVAILABLE and not read_only
        self._pool: Optional[DuckDBConnectionPool] = None
        if self.use_pool:
            try:
                self._pool = get_pool(database=self.database, max_connections=5)
                logger.info("Using connection pool for better performance")
            except Exception as e:
                logger.warning(f"Failed to initialize pool: {e}, falling back to single connection")
                self.use_pool = False
        
        # Query result cache
        self.enable_cache = enable_cache
        self._query_cache = {}
        self._cache_max_size = 100  # Increased cache size
        self._cache_ttl = 60  # Reduced TTL to 1 minute for faster iteration
        self._cache_timestamps = {}

    def _get_default_config(self) -> Dict[str, Any]:
        """Get optimized DuckDB configuration for M1 Pro performance."""
        import multiprocessing
        
        # Auto-detect optimal thread count - M1 Pro has 8-10 cores
        cpu_count = multiprocessing.cpu_count()
        optimal_threads = min(cpu_count, 4)  # Reduced for M1 efficiency
        
        return {
            "threads": optimal_threads,
            "memory_limit": "2GB",  # Optimized for 16GB M1 system
            "max_memory": "2GB",
            "temp_directory": "/tmp/duckdb_temp",
            "enable_object_cache": True,
            "enable_http_metadata_cache": True,
            "default_null_order": "NULLS LAST",

            "checkpoint_threshold": "256MB",
            "wal_autocheckpoint": "256MB",
            "preserve_insertion_order": False  # Better performance

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
        Execute a SQL query with caching and pooling support.

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
        
        # Use connection pool if available (currently disabled)
        if self.use_pool and self._pool:
            try:
                result = self._pool.execute(query, params)
                # Cache the result if applicable
                if cache_key and self.enable_cache:
                    self._cache_timestamps[cache_key] = time.time()
                    self._query_cache[cache_key] = result
                return result
            except Exception as e:
                logger.warning(f"Pool execution failed: {e}, falling back to direct connection")
                # Fall through to regular connection
        
        conn = self.connect()
        try:
            if params:
                result = conn.execute(query, params)
            else:
                result = conn.execute(query)
            
            # Simple caching - only cache SELECT query results
            if cache_key and self.enable_cache:
                # Store result for future use (but don't interfere with current execution)
                try:
                    # Manage cache size
                    if len(self._query_cache) >= self._cache_max_size:
                        # Remove oldest entry
                        oldest_key = min(self._cache_timestamps, key=self._cache_timestamps.get)
                        del self._query_cache[oldest_key]
                        del self._cache_timestamps[oldest_key]
                    
                    # Store the result object directly
                    self._query_cache[cache_key] = result
                    self._cache_timestamps[cache_key] = time.time()
                except Exception:
                    # If caching fails, just continue
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
        columns = []
        for row in result.fetchall():
            # DuckDB DESCRIBE returns variable columns, handle safely
            col_info = {
                "name": row[0] if len(row) > 0 else None,
                "type": row[1] if len(row) > 1 else None,
                "null": row[2] if len(row) > 2 else None,
                "key": row[3] if len(row) > 3 else None
            }
            columns.append(col_info)
        info["columns"] = columns

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
