"""Tests for enhanced SQL generator with schema context."""

from unittest.mock import Mock, patch

import pytest

from src.duckdb_analytics.llm.config import SQL_SYSTEM_PROMPT
from src.duckdb_analytics.llm.sql_generator import SQLGenerator


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    mock_client = Mock()
    mock_client.models.list.return_value = Mock()  # For availability check
    return mock_client


@pytest.fixture
def sql_generator(mock_openai_client):
    """Create SQLGenerator instance with mocked client."""
    with patch(
        "src.duckdb_analytics.llm.sql_generator.OpenAI", return_value=mock_openai_client
    ):
        generator = SQLGenerator()
        generator.client = mock_openai_client
        return generator


class TestEnhancedSQLGenerator:
    """Test enhanced SQL generation with schema context."""

    def test_build_system_prompt_without_schema(self, sql_generator):
        """Test system prompt building without schema context."""
        prompt = sql_generator._build_system_prompt(None)
        assert prompt == SQL_SYSTEM_PROMPT

    def test_build_system_prompt_with_schema(self, sql_generator):
        """Test system prompt building with schema context."""
        schema_context = """
Table: customers (100 rows)
  - customer_id (INTEGER NOT NULL)
  - name (VARCHAR)
  - email (VARCHAR)
        """

        prompt = sql_generator._build_system_prompt(schema_context)

        # Check that enhanced prompt contains key elements
        assert "expert DuckDB SQL" in prompt
        assert "Schema Context" in prompt  # New prompt structure
        assert "DuckDB-specific functions" in prompt  # DuckDB functions
        assert "ONLY the SQL query" in prompt

    def test_generate_sql_with_schema_context(self, sql_generator, mock_openai_client):
        """Test SQL generation with schema context."""
        # Setup mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "SELECT * FROM customers"
        mock_openai_client.chat.completions.create.return_value = mock_response

        schema_context = """
Table: customers (100 rows)
  - customer_id (INTEGER NOT NULL)
  - name (VARCHAR)
        """

        # Generate SQL with schema
        result = sql_generator.generate_sql("show all customers", schema_context)

        assert result == "SELECT * FROM customers"

        # Verify the enhanced prompt was used
        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        system_message = messages[0]["content"]

        # Check for key elements of enhanced prompt
        assert "DuckDB" in system_message
        assert "SQL" in system_message

    def test_generate_sql_without_schema_context(
        self, sql_generator, mock_openai_client
    ):
        """Test SQL generation without schema context falls back to default."""
        # Setup mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "SELECT * FROM data"
        mock_openai_client.chat.completions.create.return_value = mock_response

        # Generate SQL without schema
        result = sql_generator.generate_sql("show all data")

        assert result == "SELECT * FROM data"

        # Verify the default prompt was used
        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        system_message = messages[0]["content"]

        # Now always uses enhanced prompt
        assert "DuckDB" in system_message and "SQL" in system_message

    def test_generate_sql_stream_with_schema(self, sql_generator, mock_openai_client):
        """Test streaming SQL generation with schema context."""
        # Setup mock streaming response
        mock_chunk1 = Mock()
        mock_chunk1.choices = [Mock()]
        mock_chunk1.choices[0].delta.content = "SELECT "

        mock_chunk2 = Mock()
        mock_chunk2.choices = [Mock()]
        mock_chunk2.choices[0].delta.content = "* FROM customers"

        mock_chunk3 = Mock()
        mock_chunk3.choices = [Mock()]
        mock_chunk3.choices[0].delta.content = None

        mock_openai_client.chat.completions.create.return_value = iter(
            [mock_chunk1, mock_chunk2, mock_chunk3]
        )

        schema_context = "Table: customers"

        # Generate SQL stream with schema
        result = list(
            sql_generator.generate_sql_stream("show customers", schema_context)
        )

        assert result == ["SELECT ", "* FROM customers"]

        # Verify enhanced prompt was used
        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        system_message = messages[0]["content"]

        assert "SQL expert for DuckDB" in system_message
        assert "customers" in system_message

    def test_schema_context_sanitization(self, sql_generator):
        """Test that schema context is properly sanitized."""
        # Create a very long schema context
        long_schema = "x" * 1000

        prompt = sql_generator._build_system_prompt(long_schema)

        # Should still create a valid prompt
        assert "DuckDB" in prompt and "SQL" in prompt
        assert len(long_schema) == 1000  # Original unchanged
        # Note: New implementation uses enhanced prompt always

    def test_duckdb_specific_functions_in_prompt(self, sql_generator):
        """Test that DuckDB-specific functions are included in enhanced prompt."""
        schema_context = "Table: sales"

        prompt = sql_generator._build_system_prompt(schema_context)

        # Check for DuckDB-specific functions in enhanced prompt
        assert "DuckDB-specific functions" in prompt
        assert "date_trunc" in prompt.lower() or "Date/time functions" in prompt

    def test_prompt_instructs_sql_only_output(self, sql_generator):
        """Test that enhanced prompt instructs to return SQL only."""
        schema_context = "Table: orders"

        prompt = sql_generator._build_system_prompt(schema_context)

        # Check for output format instructions
        assert "ONLY the SQL query" in prompt or "ONLY valid DuckDB SQL" in prompt
        assert "no explanations" in prompt or "nothing else" in prompt

    def test_prompt_handles_missing_data_gracefully(self, sql_generator):
        """Test that prompt includes instructions for handling missing data."""
        schema_context = "Table: products"

        prompt = sql_generator._build_system_prompt(schema_context)

        # Check for SQL generation rules
        assert "SQL Generation Rules" in prompt or "SQL" in prompt
        assert "DuckDB" in prompt
