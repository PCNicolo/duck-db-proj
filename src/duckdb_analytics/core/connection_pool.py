"""DuckDB connection pooling for improved performance."""

import logging
import threading
import time
from queue import Queue, Empty
from typing import Any, Dict, List, Optional
import duckdb
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DuckDBConnectionPool:
    """Connection pool for DuckDB to reuse connections efficiently."""
    
    def __init__(
        self,
        database: str = ":memory:",
        max_connections: int = 5,
        min_connections: int = 2,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize connection pool.
        
        Args:
            database: Database path or :memory:
            max_connections: Maximum pool size
            min_connections: Minimum connections to maintain
            config: DuckDB configuration
        """
        self.database = database
        self.max_connections = max_connections
        self.min_connections = min_connections
        self.config = config or self._get_optimized_config()
        
        # Thread-safe queue for available connections
        self._available_connections = Queue(maxsize=max_connections)
        self._in_use_connections = set()
        self._lock = threading.Lock()
        self._closed = False
        
        # Statistics
        self._stats = {
            "connections_created": 0,
            "connections_reused": 0,
            "wait_time_total": 0,
            "queries_executed": 0
        }
        
        # Pre-create minimum connections
        self._initialize_pool()
    
    def _get_optimized_config(self) -> Dict[str, Any]:
        """Get optimized DuckDB config for pooled connections."""
        import multiprocessing
        
        return {
            "threads": min(multiprocessing.cpu_count(), 4),
            "memory_limit": "2GB",  # Per connection limit
            "max_memory": "2GB",
            "enable_object_cache": True,
            "enable_http_metadata_cache": True,
            "checkpoint_threshold": "256MB",
            "preserve_insertion_order": False
        }
    
    def _initialize_pool(self):
        """Pre-create minimum connections."""
        for _ in range(self.min_connections):
            conn = self._create_connection()
            self._available_connections.put(conn)
    
    def _create_connection(self) -> duckdb.DuckDBPyConnection:
        """Create a new DuckDB connection."""
        conn = duckdb.connect(
            database=self.database,
            read_only=False,
            config=self.config
        )
        
        # Load extensions
        extensions = ["httpfs", "parquet", "json"]
        for ext in extensions:
            try:
                conn.install_extension(ext)
                conn.load_extension(ext)
            except Exception as e:
                logger.debug(f"Extension {ext}: {e}")
        
        with self._lock:
            self._stats["connections_created"] += 1
        
        logger.debug(f"Created new connection (total: {self._stats['connections_created']})")
        return conn
    
    @contextmanager
    def get_connection(self, timeout: float = 5.0):
        """
        Get a connection from the pool.
        
        Args:
            timeout: Max time to wait for connection
            
        Yields:
            DuckDB connection
        """
        if self._closed:
            raise RuntimeError("Connection pool is closed")
        
        start_time = time.time()
        conn = None
        
        try:
            # Try to get existing connection
            try:
                conn = self._available_connections.get(timeout=timeout)
                with self._lock:
                    self._stats["connections_reused"] += 1
                logger.debug("Reusing existing connection")
            except Empty:
                # Create new connection if under limit
                with self._lock:
                    total_connections = (
                        self._available_connections.qsize() + 
                        len(self._in_use_connections)
                    )
                    if total_connections < self.max_connections:
                        conn = self._create_connection()
                    else:
                        raise TimeoutError(
                            f"No connections available after {timeout}s"
                        )
            
            # Track connection usage
            with self._lock:
                self._in_use_connections.add(conn)
                wait_time = time.time() - start_time
                self._stats["wait_time_total"] += wait_time
            
            yield conn
            
        finally:
            # Return connection to pool
            if conn and not self._closed:
                with self._lock:
                    self._in_use_connections.discard(conn)
                
                # Verify connection is still valid
                try:
                    conn.execute("SELECT 1").fetchone()
                    self._available_connections.put(conn)
                except Exception:
                    # Connection is broken, create a new one
                    logger.debug("Replacing broken connection")
                    try:
                        conn.close()
                    except:
                        pass
                    if self._available_connections.qsize() < self.min_connections:
                        new_conn = self._create_connection()
                        self._available_connections.put(new_conn)
    
    def execute(self, query: str, params: Optional[List[Any]] = None) -> Any:
        """
        Execute a query using a pooled connection.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Query result
        """
        with self.get_connection() as conn:
            with self._lock:
                self._stats["queries_executed"] += 1
            
            if params:
                return conn.execute(query, params)
            else:
                return conn.execute(query)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self._lock:
            return {
                **self._stats,
                "available_connections": self._available_connections.qsize(),
                "in_use_connections": len(self._in_use_connections),
                "avg_wait_time": (
                    self._stats["wait_time_total"] / max(1, self._stats["connections_reused"])
                    if self._stats["connections_reused"] > 0 else 0
                )
            }
    
    def close(self):
        """Close all connections in the pool."""
        self._closed = True
        
        # Close all available connections
        while not self._available_connections.empty():
            try:
                conn = self._available_connections.get_nowait()
                conn.close()
            except Exception as e:
                logger.debug(f"Error closing connection: {e}")
        
        # Note: in-use connections will be closed when returned
        logger.info(f"Connection pool closed. Stats: {self.get_stats()}")


# Singleton pool instance
_pool_instance: Optional[DuckDBConnectionPool] = None
_pool_lock = threading.Lock()


def get_pool(
    database: str = ":memory:",
    max_connections: int = 5,
    reset: bool = False
) -> DuckDBConnectionPool:
    """
    Get or create the singleton connection pool.
    
    Args:
        database: Database path
        max_connections: Maximum pool size
        reset: Force recreate the pool
        
    Returns:
        Connection pool instance
    """
    global _pool_instance
    
    with _pool_lock:
        if reset and _pool_instance:
            _pool_instance.close()
            _pool_instance = None
        
        if _pool_instance is None:
            _pool_instance = DuckDBConnectionPool(
                database=database,
                max_connections=max_connections
            )
        
        return _pool_instance