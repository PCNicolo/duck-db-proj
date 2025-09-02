"""Tests for enhanced schema extraction functionality."""

import time
import unittest
from unittest.mock import patch

import duckdb

from src.duckdb_analytics.llm.schema_extractor import (
    SchemaExtractor,
)


class TestEnhancedSchemaExtraction(unittest.TestCase):
    """Test suite for enhanced schema extraction features."""

    def setUp(self):
        """Set up test database and extractor."""
        self.conn = duckdb.connect(":memory:")
        self._create_test_schema()
        self.extractor = SchemaExtractor(self.conn, cache_ttl=60, sample_rows=2)

    def _create_test_schema(self):
        """Create test tables with various data types and constraints."""
        # Create users table with constraints
        self.conn.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(100) NOT NULL,
                created_at DATE DEFAULT CURRENT_DATE,
                is_active BOOLEAN DEFAULT TRUE
            )
        """
        )

        # Create orders table with foreign key
        self.conn.execute(
            """
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                total_amount DECIMAL(10, 2),
                order_date DATE NOT NULL,
                status VARCHAR(50) DEFAULT 'pending'
            )
        """
        )

        # Insert sample data
        self.conn.execute(
            """
            INSERT INTO users (id, email, username) VALUES 
            (1, 'alice@example.com', 'alice'),
            (2, 'bob@example.com', 'bob'),
            (3, 'charlie@example.com', 'charlie')
        """
        )

        self.conn.execute(
            """
            INSERT INTO orders (order_id, user_id, total_amount, order_date) VALUES
            (101, 1, 99.99, '2024-01-15'),
            (102, 2, 149.50, '2024-01-16'),
            (103, 1, 75.00, '2024-01-17')
        """
        )

    def test_column_info_extraction(self):
        """Test that column information is properly extracted."""
        schema = self.extractor.get_schema()

        # Check users table columns
        self.assertIn("users", schema)
        users_table = schema["users"]

        # Check column count
        self.assertEqual(len(users_table.columns), 5)

        # Check specific column properties
        id_column = next(c for c in users_table.columns if c.name == "id")
        self.assertEqual(id_column.data_type, "INTEGER")
        self.assertTrue(id_column.is_primary_key)
        self.assertFalse(id_column.is_nullable)

        email_column = next(c for c in users_table.columns if c.name == "email")
        self.assertEqual(email_column.data_type, "VARCHAR")
        self.assertTrue(email_column.is_unique)
        self.assertFalse(email_column.is_nullable)

    def test_sample_data_extraction(self):
        """Test that sample data is properly extracted."""
        schema = self.extractor.get_schema()

        users_table = schema["users"]
        self.assertIsNotNone(users_table.sample_data)
        self.assertEqual(
            len(users_table.sample_data), 2
        )  # Should respect sample_rows=2

        # Check sample data content
        first_row = users_table.sample_data[0]
        self.assertEqual(first_row[0], 1)  # id
        self.assertEqual(first_row[1], "alice@example.com")  # email

    def test_table_statistics(self):
        """Test that table statistics are properly collected."""
        schema = self.extractor.get_schema()

        users_table = schema["users"]
        self.assertEqual(users_table.row_count, 3)

        orders_table = schema["orders"]
        self.assertEqual(orders_table.row_count, 3)

        # Check cardinality stats for key columns
        if users_table.cardinality_stats:
            self.assertIn("id", users_table.cardinality_stats)
            self.assertEqual(users_table.cardinality_stats["id"], 3)

    def test_cache_functionality(self):
        """Test schema caching and invalidation."""
        # First call should extract schema
        schema1 = self.extractor.get_schema()
        self.assertIsNotNone(schema1)

        # Second call should use cache
        with patch.object(self.extractor, "_extract_schema") as mock_extract:
            schema2 = self.extractor.get_schema()
            mock_extract.assert_not_called()
            self.assertEqual(schema1, schema2)

        # Force refresh should bypass cache
        with patch.object(
            self.extractor, "_extract_schema", return_value=schema1
        ) as mock_extract:
            schema3 = self.extractor.get_schema(force_refresh=True)
            mock_extract.assert_called_once()

    def test_cache_ttl(self):
        """Test cache TTL expiration."""
        # Create extractor with very short TTL
        extractor = SchemaExtractor(self.conn, cache_ttl=0.1)  # 100ms TTL

        schema1 = extractor.get_schema()
        time.sleep(0.2)  # Wait for cache to expire

        with patch.object(
            extractor, "_extract_schema", return_value=schema1
        ) as mock_extract:
            schema2 = extractor.get_schema()
            mock_extract.assert_called_once()  # Should re-extract after TTL

    def test_format_for_llm_minimal(self):
        """Test minimal context formatting for LLM."""
        schema = self.extractor.get_schema()
        formatted = self.extractor.format_for_llm(
            include_samples=False, context_level="minimal"
        )

        # Should include table and column names
        self.assertIn("Table: users", formatted)
        self.assertIn("id:", formatted)
        self.assertIn("email:", formatted)

        # Should not include sample data in minimal mode
        self.assertNotIn("Sample Data:", formatted)

    def test_format_for_llm_standard(self):
        """Test standard context formatting for LLM."""
        formatted = self.extractor.format_for_llm(
            include_samples=True, context_level="standard"
        )

        # Should include constraints
        self.assertIn("PRIMARY KEY", formatted)
        self.assertIn("UNIQUE", formatted)
        self.assertIn("NOT NULL", formatted)

        # Should include sample data
        self.assertIn("Sample Data:", formatted)
        self.assertIn("alice@example.com", formatted)

    def test_format_for_llm_comprehensive(self):
        """Test comprehensive context formatting for LLM."""
        formatted = self.extractor.format_for_llm(
            include_samples=True, context_level="comprehensive"
        )

        # Should include everything
        self.assertIn("PRIMARY KEY", formatted)
        self.assertIn("Sample Data:", formatted)
        self.assertIn("Query Guidelines:", formatted)

        # Should include cardinality if available
        # Note: This depends on implementation details

    def test_sql_validation(self):
        """Test SQL query validation against schema."""
        # Valid query
        valid_sql = "SELECT * FROM users WHERE email = 'test@example.com'"
        is_valid, errors = self.extractor.validate_sql(valid_sql)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

        # Invalid table name
        invalid_sql = "SELECT * FROM non_existent_table"
        is_valid, errors = self.extractor.validate_sql(invalid_sql)
        self.assertFalse(is_valid)
        self.assertTrue(
            any(
                "not found" in str(e).lower() or "not exist" in str(e).lower()
                for e in errors
            )
        )

        # Empty query
        empty_sql = ""
        is_valid, errors = self.extractor.validate_sql(empty_sql)
        self.assertFalse(is_valid)
        self.assertTrue(any("empty" in str(e).lower() for e in errors))

    def test_cache_invalidation(self):
        """Test manual cache invalidation."""
        schema1 = self.extractor.get_schema()
        self.assertIsNotNone(self.extractor._cache_timestamp)

        self.extractor.invalidate_cache()
        self.assertIsNone(self.extractor._cache_timestamp)
        self.assertIsNone(self.extractor._schema_cache)

        # Next call should re-extract
        with patch.object(
            self.extractor, "_extract_schema", return_value=schema1
        ) as mock_extract:
            schema2 = self.extractor.get_schema()
            mock_extract.assert_called_once()

    def test_cache_warming(self):
        """Test cache warming functionality."""
        self.extractor.invalidate_cache()
        self.assertIsNone(self.extractor._schema_cache)

        self.extractor.warm_cache()
        self.assertIsNotNone(self.extractor._schema_cache)
        self.assertEqual(
            len(self.extractor._schema_cache), 2
        )  # users and orders tables

    def tearDown(self):
        """Clean up test database."""
        self.conn.close()


if __name__ == "__main__":
    unittest.main()
