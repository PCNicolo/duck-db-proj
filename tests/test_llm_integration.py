"""Tests for LM Studio LLM integration."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import httpx
from openai import OpenAI

from src.duckdb_analytics.llm.sql_generator import SQLGenerator
from src.duckdb_analytics.llm.config import (
    LM_STUDIO_URL,
    MODEL_NAME,
    REQUEST_TIMEOUT,
    SQL_SYSTEM_PROMPT
)


class TestSQLGenerator:
    """Test suite for SQLGenerator class."""
    
    def test_init_default_parameters(self):
        """Test SQLGenerator initialization with default parameters."""
        generator = SQLGenerator()
        assert generator.base_url == LM_STUDIO_URL
        assert generator.model == MODEL_NAME
        assert generator._available is None
    
    def test_init_custom_parameters(self):
        """Test SQLGenerator initialization with custom parameters."""
        custom_url = "http://localhost:5000/v1"
        custom_model = "custom-model"
        generator = SQLGenerator(base_url=custom_url, model=custom_model)
        assert generator.base_url == custom_url
        assert generator.model == custom_model
    
    @patch('src.duckdb_analytics.llm.sql_generator.OpenAI')
    def test_is_available_success(self, mock_openai):
        """Test is_available returns True when LM Studio is accessible."""
        # Mock the client and models.list()
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.models.list.return_value = Mock()
        
        generator = SQLGenerator()
        result = generator.is_available()
        
        assert result is True
        assert generator._available is True
        mock_client.models.list.assert_called_once()
    
    @patch('src.duckdb_analytics.llm.sql_generator.OpenAI')
    def test_is_available_failure(self, mock_openai):
        """Test is_available returns False when LM Studio is not accessible."""
        # Mock the client to raise an exception
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.models.list.side_effect = Exception("Connection failed")
        
        generator = SQLGenerator()
        result = generator.is_available()
        
        assert result is False
        assert generator._available is False
    
    @patch('src.duckdb_analytics.llm.sql_generator.OpenAI')
    def test_is_available_cached(self, mock_openai):
        """Test is_available uses cached result on subsequent calls."""
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.models.list.return_value = Mock()
        
        generator = SQLGenerator()
        generator._available = True  # Set cached value
        
        result = generator.is_available()
        
        assert result is True
        # Should not call models.list since we have cached value
        mock_client.models.list.assert_not_called()
    
    @patch('src.duckdb_analytics.llm.sql_generator.OpenAI')
    def test_generate_sql_success(self, mock_openai):
        """Test successful SQL generation."""
        # Setup mocks
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.models.list.return_value = Mock()  # For is_available check
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "SELECT * FROM users WHERE age > 18"
        mock_client.chat.completions.create.return_value = mock_response
        
        generator = SQLGenerator()
        result = generator.generate_sql("Show all adult users")
        
        assert result == "SELECT * FROM users WHERE age > 18"
        mock_client.chat.completions.create.assert_called_once()
        
        # Verify the call parameters
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]['model'] == MODEL_NAME
        assert call_args[1]['temperature'] == 0.1
        assert call_args[1]['max_tokens'] == 500
        assert call_args[1]['stream'] is False
    
    @patch('src.duckdb_analytics.llm.sql_generator.OpenAI')
    def test_generate_sql_not_available(self, mock_openai):
        """Test generate_sql returns None when LM Studio is not available."""
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.models.list.side_effect = Exception("Not connected")
        
        generator = SQLGenerator()
        result = generator.generate_sql("Show all users")
        
        assert result is None
        mock_client.chat.completions.create.assert_not_called()
    
    @patch('src.duckdb_analytics.llm.sql_generator.OpenAI')
    def test_generate_sql_timeout(self, mock_openai):
        """Test generate_sql handles timeout correctly."""
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.models.list.return_value = Mock()  # For is_available check
        mock_client.chat.completions.create.side_effect = httpx.TimeoutException("Timeout")
        
        generator = SQLGenerator()
        result = generator.generate_sql("Show all users")
        
        assert result is None
    
    @patch('src.duckdb_analytics.llm.sql_generator.OpenAI')
    def test_generate_sql_stream_success(self, mock_openai):
        """Test successful streaming SQL generation."""
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.models.list.return_value = Mock()  # For is_available check
        
        # Mock streaming response
        mock_chunks = []
        for text in ["SELECT ", "* ", "FROM ", "users"]:
            chunk = Mock()
            chunk.choices = [Mock()]
            chunk.choices[0].delta.content = text
            mock_chunks.append(chunk)
        
        mock_client.chat.completions.create.return_value = iter(mock_chunks)
        
        generator = SQLGenerator()
        result = list(generator.generate_sql_stream("Show all users"))
        
        assert result == ["SELECT ", "* ", "FROM ", "users"]
        mock_client.chat.completions.create.assert_called_once()
        assert mock_client.chat.completions.create.call_args[1]['stream'] is True
    
    @patch('src.duckdb_analytics.llm.sql_generator.OpenAI')
    def test_generate_sql_stream_not_available(self, mock_openai):
        """Test streaming returns error when LM Studio is not available."""
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.models.list.side_effect = Exception("Not connected")
        
        generator = SQLGenerator()
        result = list(generator.generate_sql_stream("Show all users"))
        
        assert len(result) == 1
        assert "Error: LM Studio is not available" in result[0]
    
    def test_format_query_with_context(self):
        """Test query formatting with table context."""
        generator = SQLGenerator()
        
        # Test with context
        formatted = generator.format_query_with_context(
            "Show all users",
            "users table has columns: id, name, age, email"
        )
        assert "Given the following table information:" in formatted
        assert "users table has columns" in formatted
        assert "Show all users" in formatted
        
        # Test without context
        formatted = generator.format_query_with_context("Show all users", None)
        assert formatted == "Show all users"
        
        # Test input sanitization (length limiting)
        long_query = "x" * 1000
        formatted = generator.format_query_with_context(long_query, None)
        assert len(formatted) <= 500
        
        # Test context sanitization
        long_context = "y" * 1000
        formatted = generator.format_query_with_context("query", long_context)
        assert len(formatted) <= 1100  # ~500 for query + 500 for context + overhead
    
    def test_reset_availability(self):
        """Test resetting availability cache."""
        generator = SQLGenerator()
        generator._available = True
        
        generator.reset_availability()
        
        assert generator._available is None


class TestConfig:
    """Test configuration values."""
    
    def test_config_values(self):
        """Test that configuration values are set correctly."""
        assert LM_STUDIO_URL == "http://localhost:1234/v1"
        assert MODEL_NAME == "local-model"
        assert REQUEST_TIMEOUT == 10.0  # Updated timeout for complex queries
        assert "SQL expert" in SQL_SYSTEM_PROMPT
        assert "DuckDB" in SQL_SYSTEM_PROMPT