"""Tests for DuckDB schema extraction."""

import pytest
import duckdb
import pandas as pd
from unittest.mock import Mock, MagicMock, patch

from src.duckdb_analytics.llm.schema_extractor import SchemaExtractor, TableSchema


@pytest.fixture
def mock_duckdb_conn():
    """Create a mock DuckDB connection."""
    conn = Mock()
    return conn


@pytest.fixture
def in_memory_conn():
    """Create an in-memory DuckDB connection with test data."""
    conn = duckdb.connect(":memory:")
    
    # Create test tables
    conn.execute("""
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            name VARCHAR NOT NULL,
            email VARCHAR,
            created_date DATE
        )
    """)
    
    conn.execute("""
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            order_date DATE,
            total_amount DECIMAL(10, 2)
        )
    """)
    
    # Insert sample data
    conn.execute("""
        INSERT INTO customers VALUES 
        (1, 'John Doe', 'john@example.com', '2024-01-01'),
        (2, 'Jane Smith', 'jane@example.com', '2024-01-02')
    """)
    
    conn.execute("""
        INSERT INTO orders VALUES 
        (101, 1, '2024-01-15', 99.99),
        (102, 2, '2024-01-16', 149.99)
    """)
    
    return conn


class TestSchemaExtractor:
    """Test SchemaExtractor functionality."""
    
    def test_initialization(self, mock_duckdb_conn):
        """Test SchemaExtractor initialization."""
        extractor = SchemaExtractor(mock_duckdb_conn)
        assert extractor.conn == mock_duckdb_conn
        assert extractor._schema_cache is None
        assert extractor._raw_schema_df is None
    
    def test_extract_schema_with_real_connection(self, in_memory_conn):
        """Test schema extraction with real DuckDB connection."""
        extractor = SchemaExtractor(in_memory_conn)
        schema = extractor.get_schema()
        
        # Check that we got both tables
        assert len(schema) == 2
        assert 'customers' in schema
        assert 'orders' in schema
        
        # Check customers table schema
        customers_schema = schema['customers']
        assert customers_schema.name == 'customers'
        assert len(customers_schema.columns) == 4
        assert customers_schema.row_count == 2
        
        # Check column details
        customer_columns = {col['name']: col for col in customers_schema.columns}
        assert 'customer_id' in customer_columns
        assert 'name' in customer_columns
        assert 'email' in customer_columns
        assert 'created_date' in customer_columns
        
        # Check orders table schema
        orders_schema = schema['orders']
        assert orders_schema.name == 'orders'
        assert len(orders_schema.columns) == 4
        assert orders_schema.row_count == 2
    
    def test_schema_caching(self, in_memory_conn):
        """Test that schema is cached after first extraction."""
        extractor = SchemaExtractor(in_memory_conn)
        
        # First call extracts schema
        schema1 = extractor.get_schema()
        assert extractor._schema_cache is not None
        
        # Second call should return cached schema
        schema2 = extractor.get_schema()
        assert schema1 is schema2  # Same object reference
        
        # Force refresh should extract again
        schema3 = extractor.get_schema(force_refresh=True)
        assert schema3 is not schema1  # Different object
    
    def test_format_for_llm(self, in_memory_conn):
        """Test formatting schema for LLM context."""
        extractor = SchemaExtractor(in_memory_conn)
        formatted = extractor.format_for_llm()
        
        # Check that formatted string contains table information
        assert 'Table: customers' in formatted
        assert 'Table: orders' in formatted
        assert 'customer_id' in formatted
        assert 'INTEGER' in formatted
        assert '2 rows' in formatted
    
    def test_format_for_llm_empty_database(self, mock_duckdb_conn):
        """Test formatting when database is empty."""
        mock_result = Mock()
        mock_result.fetchdf = Mock(return_value=pd.DataFrame())
        mock_duckdb_conn.execute = Mock(return_value=mock_result)
        
        extractor = SchemaExtractor(mock_duckdb_conn)
        formatted = extractor.format_for_llm()
        
        assert formatted == "No tables available in database."
    
    def test_validate_sql_valid_query(self, in_memory_conn):
        """Test SQL validation with valid query."""
        extractor = SchemaExtractor(in_memory_conn)
        
        valid_query = "SELECT * FROM customers WHERE customer_id = 1"
        is_valid, errors = extractor.validate_sql(valid_query)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_sql_invalid_table(self, in_memory_conn):
        """Test SQL validation with non-existent table."""
        extractor = SchemaExtractor(in_memory_conn)
        
        invalid_query = "SELECT * FROM non_existent_table"
        is_valid, errors = extractor.validate_sql(invalid_query)
        
        assert is_valid is False
        assert len(errors) > 0
        # Should have meaningful error about table not existing
    
    def test_validate_sql_empty_query(self, in_memory_conn):
        """Test SQL validation with empty query."""
        extractor = SchemaExtractor(in_memory_conn)
        
        is_valid, errors = extractor.validate_sql("")
        
        assert is_valid is False
        assert len(errors) > 0
        assert "empty" in errors[0].lower()
    
    def test_find_similar_names(self, in_memory_conn):
        """Test finding similar table names."""
        extractor = SchemaExtractor(in_memory_conn)
        extractor.get_schema()  # Load schema
        
        # Test with typo in table name
        similar = extractor._find_similar_names('custmer', ['customers', 'orders'])
        assert 'customers' in similar
    
    def test_get_table_columns(self, in_memory_conn):
        """Test getting columns for a specific table."""
        extractor = SchemaExtractor(in_memory_conn)
        
        columns = extractor.get_table_columns('customers')
        assert 'customer_id' in columns
        assert 'name' in columns
        assert 'email' in columns
        assert 'created_date' in columns
        assert len(columns) == 4
    
    def test_get_table_columns_case_insensitive(self, in_memory_conn):
        """Test getting columns with case-insensitive table name."""
        extractor = SchemaExtractor(in_memory_conn)
        
        columns = extractor.get_table_columns('CUSTOMERS')
        assert len(columns) == 4
    
    def test_get_sample_data(self, in_memory_conn):
        """Test getting sample data from table."""
        extractor = SchemaExtractor(in_memory_conn)
        
        sample = extractor.get_sample_data('customers', limit=1)
        assert sample is not None
        assert len(sample) == 1
        assert 'customer_id' in sample.columns
        assert 'name' in sample.columns
    
    def test_error_handling_in_extraction(self, mock_duckdb_conn):
        """Test error handling during schema extraction."""
        mock_duckdb_conn.execute = Mock(side_effect=Exception("Database error"))
        
        extractor = SchemaExtractor(mock_duckdb_conn)
        
        with pytest.raises(Exception) as exc_info:
            extractor.get_schema()
        
        assert "Database error" in str(exc_info.value)