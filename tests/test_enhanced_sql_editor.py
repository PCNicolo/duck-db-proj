"""Test suite for Enhanced SQL Editor."""

import os
import sys
from unittest.mock import MagicMock, Mock

import pytest

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class MockSessionState(dict):
    """Mock class for Streamlit session state."""

    def __setattr__(self, key, value):
        self[key] = value

    def __getattr__(self, key):
        return self.get(key)

    def __contains__(self, key):
        return dict.__contains__(self, key)


# Mock streamlit module
sys.modules["streamlit"] = MagicMock()
import streamlit as st

st.session_state = MockSessionState()

from src.duckdb_analytics.ui.sql_editor import EnhancedSQLEditor


class TestEnhancedSQLEditor:
    """Test cases for the Enhanced SQL Editor."""

    @pytest.fixture
    def mock_query_engine(self):
        """Create a mock query engine."""
        mock = Mock()
        mock.execute_query = MagicMock(return_value=Mock())
        return mock

    @pytest.fixture
    def mock_db_connection(self):
        """Create a mock database connection."""
        mock = Mock()
        mock.get_table_info = MagicMock(
            return_value={
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "name", "type": "VARCHAR"},
                    {"name": "created_at", "type": "TIMESTAMP"},
                ],
                "row_count": 100,
            }
        )
        return mock

    def test_init_session_state(self, mock_query_engine, mock_db_connection):
        """Test session state initialization."""
        # Reset session state
        st.session_state = MockSessionState()

        editor = EnhancedSQLEditor(mock_query_engine, mock_db_connection)

        # Check that session state variables are initialized
        assert "query_history" in st.session_state
        assert "history_index" in st.session_state
        assert "favorite_queries" in st.session_state
        assert "editor_theme" in st.session_state
        assert "editor_font_size" in st.session_state
        assert "show_line_numbers" in st.session_state
        assert "schema_expanded" in st.session_state
        assert "fullscreen_mode" in st.session_state

    def test_format_sql_basic(self, mock_query_engine, mock_db_connection):
        """Test basic SQL formatting without sqlparse."""
        editor = EnhancedSQLEditor(mock_query_engine, mock_db_connection)

        # Test query formatting
        input_sql = (
            "select * from users where id = 1 and name = 'test' order by created_at"
        )
        formatted = editor._format_sql(input_sql)

        # Check that keywords are capitalized
        assert "SELECT" in formatted
        assert "FROM" in formatted
        assert "WHERE" in formatted
        assert "ORDER BY" in formatted

        # Check that formatting adds newlines
        assert "\n" in formatted

    def test_add_to_history(self, mock_query_engine, mock_db_connection):
        """Test adding queries to history."""
        # Initialize session state with query_history
        st.session_state = MockSessionState()
        st.session_state["query_history"] = []

        editor = EnhancedSQLEditor(mock_query_engine, mock_db_connection)

        # Add a query to history
        test_query = "SELECT * FROM users"
        editor._add_to_history(test_query, 0.5)

        # Check that query was added
        assert len(st.session_state.query_history) == 1
        assert st.session_state.query_history[0]["query"] == test_query
        assert "timestamp" in st.session_state.query_history[0]
        assert st.session_state.query_history[0]["execution_time"] == "0.500s"

    def test_add_to_favorites(self, mock_query_engine, mock_db_connection):
        """Test adding queries to favorites."""
        # Initialize session state with favorite_queries
        st.session_state = MockSessionState()
        st.session_state["favorite_queries"] = []

        editor = EnhancedSQLEditor(mock_query_engine, mock_db_connection)

        # Add a query to favorites
        test_query = "SELECT COUNT(*) FROM orders"
        editor._add_to_favorites(test_query)

        # Check that query was added
        assert len(st.session_state.favorite_queries) == 1
        assert st.session_state.favorite_queries[0]["query"] == test_query
        assert "name" in st.session_state.favorite_queries[0]
        assert "created_at" in st.session_state.favorite_queries[0]

    def test_get_type_icon(self, mock_query_engine, mock_db_connection):
        """Test data type icon mapping."""
        editor = EnhancedSQLEditor(mock_query_engine, mock_db_connection)

        # Test various data types
        assert editor._get_type_icon("INTEGER") == "🔢"
        assert editor._get_type_icon("VARCHAR") == "📝"
        assert editor._get_type_icon("TIMESTAMP") == "⏰"
        assert editor._get_type_icon("DATE") == "📅"
        assert editor._get_type_icon("BOOLEAN") == "✓"
        assert editor._get_type_icon("JSON") == "{}"
        assert editor._get_type_icon("UNKNOWN") == "📊"  # Default

    def test_history_limit(self, mock_query_engine, mock_db_connection):
        """Test that history is limited to prevent memory issues."""
        # Initialize session state with query_history
        st.session_state = MockSessionState()
        st.session_state["query_history"] = []

        editor = EnhancedSQLEditor(mock_query_engine, mock_db_connection)

        # Add more than 100 queries
        for i in range(105):
            editor._add_to_history(f"SELECT {i} FROM test", 0.1)

        # Check that history is limited to 100
        assert len(st.session_state.query_history) == 100

    def test_sql_keywords(self):
        """Test that SQL keywords are properly defined."""
        from src.duckdb_analytics.ui.sql_editor import DUCKDB_KEYWORDS, SQL_KEYWORDS

        # Check common SQL keywords
        assert "SELECT" in SQL_KEYWORDS
        assert "FROM" in SQL_KEYWORDS
        assert "WHERE" in SQL_KEYWORDS
        assert "JOIN" in SQL_KEYWORDS

        # Check DuckDB specific keywords
        assert "PIVOT" in DUCKDB_KEYWORDS
        assert "ASOF" in DUCKDB_KEYWORDS
        assert "QUALIFY" in DUCKDB_KEYWORDS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
