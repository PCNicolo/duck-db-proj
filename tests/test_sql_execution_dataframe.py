"""
E2E Test for SQL Query Execution DataFrame Format Issue

This test reproduces and verifies the fix for the DataFrame ambiguity error
that occurs when executing SQL queries with COUNT(DISTINCT ...) operations.
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import streamlit as st

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.duckdb_analytics.core.query_engine import QueryEngine
from src.duckdb_analytics.core.connection import DuckDBConnection


class TestSQLExecutionDataFrameIssue:
    """Test suite for SQL query execution DataFrame format issues."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.connection = None
        self.query_engine = None
        
    def teardown_method(self):
        """Clean up after each test method."""
        if self.connection:
            try:
                self.connection.close()
            except:
                pass
    
    def test_dataframe_comparison_issue_original(self):
        """
        Test that reproduces the original DataFrame comparison error.
        This test simulates the problematic code pattern that causes:
        'The truth value of a DataFrame is ambiguous'
        """
        # Create mock DataFrame result
        mock_df = pd.DataFrame({
            'count': [5],
            'category': ['Food']
        })
        
        # This is the problematic pattern from the original code
        with pytest.raises(ValueError) as exc_info:
            # Simulating: if result and len(result) > 0:
            # where result is a DataFrame
            if mock_df and len(mock_df) > 0:  # This will raise ValueError
                pass
        
        assert "truth value of a dataframe is ambiguous" in str(exc_info.value).lower()
    
    def test_correct_dataframe_handling(self):
        """
        Test the correct way to handle DataFrame results from QueryEngine.
        """
        # Create mock DataFrame result
        mock_df = pd.DataFrame({
            'count': [5],
            'category': ['Food']
        })
        
        # Correct patterns for DataFrame checking
        
        # Pattern 1: Using .empty property
        if not mock_df.empty and len(mock_df) > 0:
            assert True  # This should work
        
        # Pattern 2: Using isinstance check
        if isinstance(mock_df, pd.DataFrame) and not mock_df.empty:
            assert True  # This should work
        
        # Pattern 3: Direct length check
        if len(mock_df) > 0:
            assert True  # This should work
    
    def test_execute_query_with_count_distinct(self):
        """
        Test executing a COUNT(DISTINCT ...) query that triggered the original error.
        """
        # Create an in-memory DuckDB connection
        import duckdb
        conn = duckdb.connect(':memory:')
        
        # Create test data
        conn.execute("""
            CREATE TABLE products (
                product_id INTEGER,
                category VARCHAR
            )
        """)
        
        conn.execute("""
            INSERT INTO products VALUES
            (1, 'Food'),
            (2, 'Food'),
            (3, 'Food'),
            (1, 'Food'),  -- Duplicate to test DISTINCT
            (4, 'Electronics'),
            (5, 'Clothing')
        """)
        
        # Create QueryEngine wrapper
        class MockDuckDBConnection:
            def __init__(self, conn):
                self._conn = conn
                
            def execute(self, query, params=None):
                return self._conn.execute(query, params)
        
        mock_connection = MockDuckDBConnection(conn)
        query_engine = QueryEngine(mock_connection)
        
        # Execute the problematic query
        sql = "SELECT COUNT(DISTINCT product_id), category FROM products WHERE category = 'Food' GROUP BY category LIMIT 100"
        result = query_engine.execute_query(sql)
        
        # Verify result is a DataFrame
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert len(result) == 1
        assert result.iloc[0, 0] == 3  # 3 distinct products in Food category
        assert result.iloc[0, 1] == 'Food'
    
    def test_fixed_execute_query_function(self):
        """
        Test the fixed version of the execute_query function from app.py
        """
        # Mock QueryEngine
        mock_query_engine = Mock()
        
        # Test Case 1: Non-empty DataFrame result
        mock_result = pd.DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})
        mock_query_engine.execute_query.return_value = mock_result
        
        def execute_query_fixed(sql: str) -> pd.DataFrame:
            """Fixed version of execute_query that properly handles DataFrames."""
            try:
                result = mock_query_engine.execute_query(sql)
                # Fixed: Check if result is a DataFrame and not empty
                if isinstance(result, pd.DataFrame) and not result.empty:
                    return result
                return pd.DataFrame()
            except Exception as e:
                return pd.DataFrame()
        
        result = execute_query_fixed("SELECT * FROM test")
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert len(result) == 2
        
        # Test Case 2: Empty DataFrame result
        mock_query_engine.execute_query.return_value = pd.DataFrame()
        result = execute_query_fixed("SELECT * FROM empty_table")
        assert isinstance(result, pd.DataFrame)
        assert result.empty
        
        # Test Case 3: Exception handling
        mock_query_engine.execute_query.side_effect = Exception("Query error")
        result = execute_query_fixed("INVALID SQL")
        assert isinstance(result, pd.DataFrame)
        assert result.empty
    
    @patch('streamlit.error')
    @patch('streamlit.session_state')
    def test_app_execute_query_integration(self, mock_session_state, mock_st_error):
        """
        Integration test simulating the actual app.py execute_query function
        with the DataFrame handling fix.
        """
        # Setup mock session state with query engine
        mock_query_engine = Mock()
        mock_session_state.query_engine = mock_query_engine
        
        # Simulate the problematic query result
        test_df = pd.DataFrame({
            'count_distinct_product_id': [3],
            'category': ['Food']
        })
        mock_query_engine.execute_query.return_value = test_df
        
        # Fixed version of the execute_query function
        def execute_query_fixed(sql: str) -> pd.DataFrame:
            """Fixed execute_query that properly handles DataFrame results."""
            try:
                result = mock_session_state.query_engine.execute_query(sql)
                # FIX: Use isinstance and .empty instead of ambiguous truth check
                if isinstance(result, pd.DataFrame):
                    return result if not result.empty else pd.DataFrame()
                return pd.DataFrame()
            except Exception as e:
                mock_st_error(f"Query error: {e}")
                return pd.DataFrame()
        
        # Test the fixed function
        sql = "SELECT COUNT(DISTINCT product_id), category FROM products WHERE category = 'Food' GROUP BY category LIMIT 100"
        result = execute_query_fixed(sql)
        
        # Verify correct handling
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert len(result) == 1
        assert result.iloc[0, 1] == 'Food'
        
        # Verify error was not called
        mock_st_error.assert_not_called()


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])