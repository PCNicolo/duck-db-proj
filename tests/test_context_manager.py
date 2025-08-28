"""Tests for context window management."""

import unittest
from unittest.mock import MagicMock

from src.duckdb_analytics.llm.context_manager import ContextWindowManager
from src.duckdb_analytics.llm.schema_extractor import ColumnInfo, TableSchema


class TestContextWindowManager(unittest.TestCase):
    """Test suite for context window management."""

    def setUp(self):
        """Set up test context manager."""
        self.manager = ContextWindowManager(max_tokens=1000)

    def test_token_estimation(self):
        """Test token estimation for text."""
        # Short text
        short_text = "SELECT * FROM users"
        tokens = self.manager.estimate_tokens(short_text)
        self.assertGreater(tokens, 0)
        self.assertLess(tokens, 20)
        
        # Longer text
        long_text = "SELECT u.id, u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id WHERE o.date > '2024-01-01'"
        tokens = self.manager.estimate_tokens(long_text)
        self.assertGreater(tokens, 20)

    def test_query_type_detection(self):
        """Test detection of query types from natural language."""
        # Aggregation query
        query = "What is the total sum of sales by month?"
        types = self.manager.detect_query_type(query)
        self.assertIn('aggregation', types)
        
        # Filtering query
        query = "Show me all orders where status is pending"
        types = self.manager.detect_query_type(query)
        self.assertIn('filtering', types)
        
        # Joining query
        query = "Combine user data with their order history"
        types = self.manager.detect_query_type(query)
        self.assertIn('joining', types)
        
        # Time series query
        query = "Show daily revenue trend over time"
        types = self.manager.detect_query_type(query)
        self.assertIn('time_series', types)
        
        # General query
        query = "Get data from database"
        types = self.manager.detect_query_type(query)
        self.assertEqual(types, ['general'])

    def test_table_prioritization(self):
        """Test table prioritization based on query relevance."""
        # Create mock schema
        schema = {
            'users': self._create_mock_table('users', ['id', 'name', 'email']),
            'orders': self._create_mock_table('orders', ['id', 'user_id', 'total']),
            'products': self._create_mock_table('products', ['id', 'name', 'price']),
            'categories': self._create_mock_table('categories', ['id', 'name']),
        }
        
        # Query mentioning specific tables
        query = "Show me all users and their orders"
        prioritized = self.manager.prioritize_tables(query, schema, max_tables=3)
        self.assertIn('users', prioritized[:2])
        self.assertIn('orders', prioritized[:2])
        
        # Query with column mentions
        query = "What is the total price of products?"
        prioritized = self.manager.prioritize_tables(query, schema, max_tables=3)
        self.assertIn('products', prioritized[:2])

    def test_context_truncation(self):
        """Test intelligent context truncation."""
        # Create a long context
        context = """## Database Schema

### Table: users (1000 rows)
Columns:
  - id: INTEGER [PRIMARY KEY]
  - name: VARCHAR
  - email: VARCHAR [UNIQUE]

Sample Data:
  id | name | email
  1 | Alice | alice@example.com
  2 | Bob | bob@example.com

### Table: orders (5000 rows)
Columns:
  - id: INTEGER [PRIMARY KEY]
  - user_id: INTEGER
  - total: DECIMAL

Sample Data:
  id | user_id | total
  101 | 1 | 99.99
  102 | 2 | 149.50
""" * 10  # Repeat to make it long
        
        # Truncate to fit token limit
        truncated = self.manager.truncate_context(context, target_tokens=100)
        self.assertLess(len(truncated), len(context))
        self.assertIn('Table:', truncated)  # Should keep structure
        
        # Check that essential parts are preserved
        self.assertIn('###', truncated)  # Headers should remain

    def test_dynamic_prompt_building(self):
        """Test dynamic prompt construction."""
        base_prompt = "You are a SQL expert."
        query = "Calculate total sales by month"
        schema_context = "Table: orders\nColumns: id, date, total"
        
        prompt, metadata = self.manager.build_dynamic_prompt(
            base_prompt, query, schema_context
        )
        
        # Check prompt structure
        self.assertIn(base_prompt, prompt)
        self.assertIn(schema_context, prompt)
        self.assertIn(query, prompt)
        
        # Check metadata
        self.assertIn('query_types', metadata)
        self.assertIn('aggregation', metadata['query_types'])
        self.assertIn('estimated_tokens', metadata)
        self.assertIsInstance(metadata['estimated_tokens'], int)

    def test_schema_compression(self):
        """Test schema context compression."""
        full_context = """### Table: users (1000 rows)
Columns:
  - id: INTEGER [PRIMARY KEY, NOT NULL]
  - name: VARCHAR [NOT NULL]
  - email: VARCHAR [UNIQUE, NOT NULL]

Sample Data:
  id | name | email
  1 | Alice | alice@example.com
  2 | Bob | bob@example.com

Relationships:
  - orders.user_id -> users.id"""
        
        # Minimal compression
        minimal = self.manager.compress_schema_context(full_context, 'minimal')
        self.assertNotIn('Sample Data:', minimal)
        self.assertIn('id: INTEGER', minimal)
        
        # Standard compression
        standard = self.manager.compress_schema_context(full_context, 'standard')
        self.assertNotIn('Sample Data:', standard)
        self.assertIn('[PRIMARY KEY', standard)
        
        # Comprehensive (no compression)
        comprehensive = self.manager.compress_schema_context(full_context, 'comprehensive')
        self.assertEqual(comprehensive, full_context)

    def test_token_limit_handling(self):
        """Test handling of token limit exceeded scenarios."""
        # Create a very long schema context
        long_schema = "Table: test\n" + "Column: col" * 1000
        
        base_prompt = "SQL expert prompt"
        query = "Simple query"
        
        # Should truncate and set metadata correctly
        prompt, metadata = self.manager.build_dynamic_prompt(
            base_prompt, query, long_schema
        )
        
        # Check that prompt was truncated or properly managed
        # The prompt should be around the max tokens or indicate truncation
        estimated = self.manager.estimate_tokens(prompt)
        
        # Either the prompt is within reasonable limits or metadata indicates handling
        self.assertTrue(
            estimated <= self.manager.max_tokens * 1.5 or  # Allow some overhead
            metadata.get('truncated', False) or
            '[Context truncated' in prompt
        )
        
        # Metadata should indicate the situation
        self.assertIn('estimated_tokens', metadata)
        self.assertIsInstance(metadata['estimated_tokens'], int)

    def _create_mock_table(self, name: str, columns: list) -> TableSchema:
        """Create a mock TableSchema for testing."""
        table = TableSchema(name=name)
        table.columns = [
            ColumnInfo(name=col, data_type='VARCHAR', is_nullable=True)
            for col in columns
        ]
        table.row_count = 1000
        return table


if __name__ == '__main__':
    unittest.main()