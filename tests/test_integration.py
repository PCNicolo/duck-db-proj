"""Integration tests for schema-aware SQL generation."""

import pytest
import duckdb
from unittest.mock import Mock, MagicMock, patch

from src.duckdb_analytics.llm.schema_extractor import SchemaExtractor
from src.duckdb_analytics.llm.sql_generator import SQLGenerator
from src.duckdb_analytics.core.connection import DuckDBConnection


@pytest.fixture
def test_db_connection():
    """Create a test database with sample data."""
    conn = DuckDBConnection(":memory:")
    
    # Create sample tables
    conn.execute("""
        CREATE TABLE sales (
            sale_id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            product_id INTEGER,
            sale_date DATE,
            amount DECIMAL(10, 2)
        )
    """)
    
    conn.execute("""
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            name VARCHAR,
            email VARCHAR,
            country VARCHAR
        )
    """)
    
    conn.execute("""
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            product_name VARCHAR,
            category VARCHAR,
            price DECIMAL(10, 2)
        )
    """)
    
    # Insert sample data
    conn.execute("""
        INSERT INTO customers VALUES 
        (1, 'John Doe', 'john@example.com', 'USA'),
        (2, 'Jane Smith', 'jane@example.com', 'UK'),
        (3, 'Bob Johnson', 'bob@example.com', 'Canada')
    """)
    
    conn.execute("""
        INSERT INTO products VALUES 
        (1, 'Laptop', 'Electronics', 999.99),
        (2, 'Mouse', 'Electronics', 29.99),
        (3, 'Desk', 'Furniture', 299.99)
    """)
    
    conn.execute("""
        INSERT INTO sales VALUES 
        (1, 1, 1, '2024-01-15', 999.99),
        (2, 2, 2, '2024-01-16', 29.99),
        (3, 1, 3, '2024-01-17', 299.99),
        (4, 3, 1, '2024-01-18', 999.99),
        (5, 2, 3, '2024-01-19', 299.99)
    """)
    
    return conn


class TestSchemaIntegration:
    """Test integration between schema extraction and SQL generation."""
    
    def test_schema_extraction_with_sample_database(self, test_db_connection):
        """Test schema extraction from sample database."""
        extractor = SchemaExtractor(test_db_connection)
        schema = extractor.get_schema()
        
        # Verify all tables are extracted
        assert len(schema) == 3
        assert 'sales' in schema
        assert 'customers' in schema
        assert 'products' in schema
        
        # Verify sales table schema
        sales_schema = schema['sales']
        assert sales_schema.row_count == 5
        assert len(sales_schema.columns) == 5
        
        # Verify column names
        column_names = [col.name if hasattr(col, 'name') else col['name'] for col in sales_schema.columns]
        assert 'sale_id' in column_names
        assert 'customer_id' in column_names
        assert 'amount' in column_names
    
    def test_llm_prompt_generation(self, test_db_connection):
        """Test LLM prompt generation with schema context."""
        extractor = SchemaExtractor(test_db_connection)
        schema_context = extractor.format_for_llm()
        
        # Verify schema context contains all tables
        assert 'Table: sales' in schema_context
        assert 'Table: customers' in schema_context
        assert 'Table: products' in schema_context
        
        # Verify row counts are included
        assert '5 rows' in schema_context  # sales
        assert '3 rows' in schema_context  # customers or products
        
        # Verify column information
        assert 'sale_id' in schema_context
        assert 'customer_id' in schema_context
        assert 'product_name' in schema_context
    
    def test_sql_validation_integration(self, test_db_connection):
        """Test SQL validation against actual schema."""
        extractor = SchemaExtractor(test_db_connection)
        
        # Valid query
        valid_sql = "SELECT * FROM customers WHERE customer_id = 1"
        is_valid, errors = extractor.validate_sql(valid_sql)
        assert is_valid is True
        assert len(errors) == 0
        
        # Invalid table name
        invalid_sql = "SELECT * FROM users"
        is_valid, errors = extractor.validate_sql(invalid_sql)
        assert is_valid is False
        assert len(errors) > 0
        assert any('users' in error for error in errors)
        
        # Join query with valid tables
        join_sql = """
        SELECT c.name, s.amount 
        FROM customers c 
        JOIN sales s ON c.customer_id = s.customer_id
        """
        is_valid, errors = extractor.validate_sql(join_sql)
        assert is_valid is True
    
    def test_similar_table_suggestions(self, test_db_connection):
        """Test that similar table names are suggested for typos."""
        extractor = SchemaExtractor(test_db_connection)
        
        # Typo in table name
        sql_with_typo = "SELECT * FROM custmers"  # 'custmers' instead of 'customers'
        is_valid, errors = extractor.validate_sql(sql_with_typo)
        
        assert is_valid is False
        assert len(errors) > 0
        # Should suggest 'customers' as similar
        assert any('customers' in error for error in errors)
    
    @patch('src.duckdb_analytics.llm.sql_generator.OpenAI')
    def test_end_to_end_sql_generation(self, mock_openai, test_db_connection):
        """Test end-to-end SQL generation with schema context."""
        # Setup mock LLM response
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.models.list.return_value = Mock()  # For availability check
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """
        SELECT c.name, SUM(s.amount) as total_sales
        FROM customers c
        JOIN sales s ON c.customer_id = s.customer_id
        GROUP BY c.name
        ORDER BY total_sales DESC
        """
        mock_client.chat.completions.create.return_value = mock_response
        
        # Create components
        extractor = SchemaExtractor(test_db_connection)
        generator = SQLGenerator()
        generator.client = mock_client
        
        # Get schema context
        schema_context = extractor.format_for_llm()
        
        # Generate SQL with schema context
        natural_query = "Show me total sales by customer"
        generated_sql = generator.generate_sql(natural_query, schema_context)
        
        assert generated_sql is not None
        assert 'customers' in generated_sql
        assert 'sales' in generated_sql
        assert 'SUM' in generated_sql
        
        # Validate the generated SQL
        is_valid, errors = extractor.validate_sql(generated_sql)
        assert is_valid is True
        assert len(errors) == 0
        
        # Verify the system prompt included schema
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        system_message = messages[0]['content']
        
        assert 'DuckDB' in system_message
        assert 'customers' in system_message
        assert 'sales' in system_message
        assert 'products' in system_message
    
    def test_schema_caching_during_session(self, test_db_connection):
        """Test that schema is properly cached during a session."""
        extractor = SchemaExtractor(test_db_connection)
        
        # First extraction
        schema1 = extractor.get_schema()
        assert extractor._schema_cache is not None
        initial_count = len(schema1)
        
        # Get schema again without changes - should use cache
        with patch.object(extractor, '_extract_schema') as mock_extract:
            schema2 = extractor.get_schema()
            mock_extract.assert_not_called()  # Should use cache
            assert len(schema2) == initial_count
        
        # Add a new table
        test_db_connection.execute("""
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                order_date DATE
            )
        """)
        
        # The enhanced cache detects table changes and auto-invalidates
        # This is the new, correct behavior
        schema3 = extractor.get_schema()
        assert 'orders' in schema3  # Cache was invalidated, new table appears
        assert len(schema3) == initial_count + 1
        
        # Force refresh to ensure it still works
        schema4 = extractor.get_schema(force_refresh=True)
        assert 'orders' in schema4
        assert len(schema4) == initial_count + 1
    
    def test_column_extraction_for_table(self, test_db_connection):
        """Test extracting columns for a specific table."""
        extractor = SchemaExtractor(test_db_connection)
        
        # Get columns for customers table
        columns = extractor.get_table_columns('customers')
        assert 'customer_id' in columns
        assert 'name' in columns
        assert 'email' in columns
        assert 'country' in columns
        assert len(columns) == 4
        
        # Test case-insensitive lookup
        columns_upper = extractor.get_table_columns('CUSTOMERS')
        assert columns_upper == columns
        
        # Non-existent table
        columns_invalid = extractor.get_table_columns('invalid_table')
        assert columns_invalid == []