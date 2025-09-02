"""Tests for optimized query executor."""

import time
from datetime import datetime
from unittest.mock import Mock

import pandas as pd
import pytest

from src.duckdb_analytics.core.connection import DuckDBConnection
from src.duckdb_analytics.core.optimized_query_executor import (
    OptimizedQueryExecutor,
    QueryCacheManager,
    QueryErrorHandler,
    QueryMetrics,
)


class TestQueryCacheManager:
    """Test cases for QueryCacheManager."""

    def test_cache_initialization(self):
        """Test cache manager initialization."""
        cache = QueryCacheManager(max_size=10, max_memory_mb=50)
        assert cache.max_size == 10
        assert cache.max_memory_bytes == 50 * 1024 * 1024
        assert len(cache.cache) == 0
        assert cache.memory_usage == 0

    def test_cache_put_and_get(self):
        """Test putting and getting items from cache."""
        cache = QueryCacheManager(max_size=10)

        # Create test DataFrame
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

        # Put item in cache
        cache.put("key1", df, "SELECT * FROM test")

        # Get item from cache
        result = cache.get("key1")
        assert result is not None
        pd.testing.assert_frame_equal(result, df)

        # Check stats
        assert cache.stats["hits"] == 1
        assert cache.stats["misses"] == 0

    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = QueryCacheManager(max_size=2)

        # Add items to fill cache
        df1 = pd.DataFrame({"a": [1]})
        df2 = pd.DataFrame({"b": [2]})
        df3 = pd.DataFrame({"c": [3]})

        cache.put("key1", df1, "query1")
        cache.put("key2", df2, "query2")
        cache.put("key3", df3, "query3")  # Should evict key1

        # Check that key1 was evicted
        assert cache.get("key1") is None
        assert cache.get("key2") is not None
        assert cache.get("key3") is not None
        assert cache.stats["evictions"] == 1

    def test_cache_memory_limit(self):
        """Test cache memory limit enforcement."""
        # Create cache with very small memory limit
        cache = QueryCacheManager(max_size=100, max_memory_mb=0.001)  # 1KB

        # Try to add large DataFrame
        large_df = pd.DataFrame({"a": range(1000)})
        cache.put("large", large_df, "query")

        # Should have evicted due to memory limit
        assert cache.memory_usage <= cache.max_memory_bytes

    def test_cache_invalidation(self):
        """Test cache invalidation."""
        cache = QueryCacheManager()

        # Add multiple items
        df1 = pd.DataFrame({"a": [1]})
        df2 = pd.DataFrame({"b": [2]})

        cache.put("key1", df1, "SELECT * FROM table1")
        cache.put("key2", df2, "SELECT * FROM table2")

        # Invalidate specific pattern
        count = cache.invalidate("table1")
        assert count == 1
        assert cache.get("key1") is None
        assert cache.get("key2") is not None

        # Invalidate all
        count = cache.invalidate()
        assert count == 1
        assert len(cache.cache) == 0


class TestQueryErrorHandler:
    """Test cases for QueryErrorHandler."""

    def test_syntax_error_categorization(self):
        """Test categorization of syntax errors."""
        error = "Syntax error at or near 'SELCT'"
        result = QueryErrorHandler.categorize_error(error)

        assert result["type"] == "SYNTAX_ERROR"
        assert result["message"] == "SQL syntax error detected"
        assert len(result["suggestions"]) > 0

    def test_table_not_found_categorization(self):
        """Test categorization of table not found errors."""
        error = "Table 'users' does not exist"
        result = QueryErrorHandler.categorize_error(error)

        assert result["type"] == "TABLE_NOT_FOUND"
        assert result["message"] == "Table not found in database"
        assert "Verify table name spelling" in result["suggestions"][0]

    def test_column_not_found_categorization(self):
        """Test categorization of column not found errors."""
        error = "Binder Error: column 'username' does not exist"
        result = QueryErrorHandler.categorize_error(error)

        assert result["type"] == "COLUMN_NOT_FOUND"
        assert result["message"] == "Column not found in table"

    def test_unknown_error_categorization(self):
        """Test categorization of unknown errors."""
        error = "Some random error message"
        result = QueryErrorHandler.categorize_error(error)

        assert result["type"] == "UNKNOWN"
        assert result["message"] == "Unknown error occurred"

    def test_suggest_correction_table_not_found(self):
        """Test query correction suggestions for table not found."""
        query = "SELECT * FROM users"
        error = {"type": "TABLE_NOT_FOUND", "original": "Table 'users' does not exist"}

        suggestion = QueryErrorHandler.suggest_correction(query, error)
        assert suggestion is not None
        assert "SHOW TABLES" in suggestion


class TestOptimizedQueryExecutor:
    """Test cases for OptimizedQueryExecutor."""

    @pytest.fixture
    def mock_connection(self):
        """Create mock DuckDB connection."""
        connection = Mock(spec=DuckDBConnection)
        connection.execute = Mock()
        return connection

    @pytest.fixture
    def executor(self, mock_connection):
        """Create OptimizedQueryExecutor instance."""
        return OptimizedQueryExecutor(
            connection=mock_connection, cache_size=10, chunk_size=100
        )

    def test_executor_initialization(self, executor):
        """Test executor initialization."""
        assert executor.chunk_size == 100
        assert executor.enable_progress is True
        assert executor.cache is not None
        assert executor.slow_query_threshold == 2.0

    def test_cache_key_generation(self, executor):
        """Test cache key generation."""
        key1 = executor._get_cache_key("SELECT * FROM table")
        key2 = executor._get_cache_key("SELECT * FROM table")
        key3 = executor._get_cache_key("SELECT * FROM other")

        assert key1 == key2  # Same query should produce same key
        assert key1 != key3  # Different queries should produce different keys

    def test_execute_streaming_with_cache_hit(self, executor, mock_connection):
        """Test streaming execution with cache hit."""
        # Pre-populate cache
        cached_df = pd.DataFrame({"a": range(10)})
        query = "SELECT * FROM test"
        cache_key = executor._get_cache_key(query)
        executor.cache.put(cache_key, cached_df, query)

        # Execute query (should hit cache)
        chunks = list(executor.execute_streaming(query, chunk_size=3))

        # Verify cache was used (connection.execute not called)
        mock_connection.execute.assert_not_called()

        # Verify chunks
        assert len(chunks) == 4  # 10 rows / 3 per chunk = 4 chunks
        assert len(chunks[0]) == 3
        assert len(chunks[-1]) == 1

    def test_execute_streaming_with_progress_callback(self, executor, mock_connection):
        """Test streaming execution with progress callback."""
        # Mock result
        mock_result = Mock()
        chunks = [
            pd.DataFrame({"a": [1, 2, 3]}),
            pd.DataFrame({"a": [4, 5, 6]}),
            pd.DataFrame(),  # Empty to signal end
        ]
        mock_result.fetch_df_chunk = Mock(side_effect=chunks)
        mock_connection.execute.return_value = mock_result

        # Track progress updates
        progress_updates = []

        def progress_callback(info):
            progress_updates.append(info)

        # Execute with progress tracking
        result_chunks = list(
            executor.execute_streaming(
                "SELECT * FROM test", progress_callback=progress_callback
            )
        )

        # Verify progress updates
        assert len(progress_updates) == 2
        assert progress_updates[0]["rows_fetched"] == 3
        assert progress_updates[1]["rows_fetched"] == 6

    def test_execute_query_complete(self, executor, mock_connection):
        """Test complete query execution."""
        # Mock result
        mock_result = Mock()
        chunks = [
            pd.DataFrame({"a": [1, 2, 3]}),
            pd.DataFrame({"a": [4, 5, 6]}),
            pd.DataFrame(),
        ]
        mock_result.fetch_df_chunk = Mock(side_effect=chunks)
        mock_connection.execute.return_value = mock_result

        # Execute query
        result = executor.execute_query("SELECT * FROM test")

        # Verify result
        assert len(result) == 6
        assert list(result["a"]) == [1, 2, 3, 4, 5, 6]

    def test_query_cancellation(self, executor, mock_connection):
        """Test query cancellation."""

        # Mock slow result
        def slow_fetch(size):
            time.sleep(0.1)
            return pd.DataFrame({"a": [1]})

        mock_result = Mock()
        mock_result.fetch_df_chunk = slow_fetch
        mock_connection.execute.return_value = mock_result

        # Start query in thread and cancel
        import threading

        chunks = []

        def run_query():
            for chunk in executor.execute_streaming("SELECT * FROM test"):
                chunks.append(chunk)

        thread = threading.Thread(target=run_query)
        thread.start()

        # Cancel after brief delay
        time.sleep(0.05)
        executor.cancel_query()
        thread.join(timeout=1)

        # Should have stopped early
        assert executor._cancel_flag.is_set()

    def test_estimate_query_time(self, executor):
        """Test query time estimation."""
        # Simple query
        simple_time = executor.estimate_query_time("SELECT * FROM table")
        assert simple_time > 0

        # Complex query with joins
        complex_time = executor.estimate_query_time(
            "SELECT * FROM t1 JOIN t2 ON t1.id = t2.id GROUP BY t1.name ORDER BY count"
        )
        assert complex_time > simple_time

        # Add history and re-estimate
        executor.query_history.append(
            QueryMetrics(start_time=datetime.now(), execution_time=1.5)
        )
        new_estimate = executor.estimate_query_time("SELECT * FROM table")
        assert new_estimate != simple_time  # Should be adjusted based on history

    def test_optimize_query_suggestions(self, executor):
        """Test query optimization suggestions."""
        # Query without LIMIT
        query = "SELECT * FROM large_table"
        optimized, suggestions = executor.optimize_query(query)

        assert "LIMIT 1000" in optimized
        assert any("LIMIT" in s for s in suggestions)

        # Query with multiple joins
        query = "SELECT * FROM t1 JOIN t2 JOIN t3 JOIN t4"
        optimized, suggestions = executor.optimize_query(query)

        assert any("JOIN order" in s for s in suggestions)

    def test_error_handling(self, executor, mock_connection):
        """Test error handling in query execution."""
        # Mock connection to raise error
        mock_connection.execute.side_effect = Exception("Table 'users' does not exist")

        # Execute query and expect enhanced error
        with pytest.raises(Exception) as exc_info:
            result = executor.execute_query("SELECT * FROM users")

        error_msg = str(exc_info.value)
        assert "Table not found" in error_msg
        assert "Suggestions:" in error_msg

    def test_get_statistics(self, executor):
        """Test statistics collection."""
        # Add some query history
        executor.query_history.append(
            QueryMetrics(
                start_time=datetime.now(), execution_time=0.5, rows_fetched=100
            )
        )
        executor.query_history.append(
            QueryMetrics(
                start_time=datetime.now(),
                execution_time=3.0,  # Slow query
                rows_fetched=1000,
            )
        )

        # Get statistics
        stats = executor.get_statistics()

        assert stats["queries"]["total"] == 2
        assert stats["queries"]["slow_queries"] == 1
        assert stats["queries"]["avg_execution_time"] == 1.75
        assert stats["queries"]["total_rows_fetched"] == 1100

    def test_clear_cache(self, executor):
        """Test cache clearing."""
        # Add items to cache
        df = pd.DataFrame({"a": [1]})
        executor.cache.put("key1", df, "SELECT * FROM table1")
        executor.cache.put("key2", df, "SELECT * FROM table2")

        # Clear specific pattern
        count = executor.clear_cache("table1")
        assert count == 1

        # Clear all
        count = executor.clear_cache()
        assert count == 1
        assert len(executor.cache.cache) == 0
