#!/usr/bin/env python3
"""Test script to verify SQL generation improvements."""

import time
import logging
from src.duckdb_analytics.llm.enhanced_sql_generator import EnhancedSQLGenerator
from src.duckdb_analytics.core.connection import DuckDBConnection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_sql_generation():
    """Test the improved SQL generation process."""
    
    # Initialize connection and generator
    conn = DuckDBConnection()
    conn.connect()  # Uses in-memory database by default
    
    # Create sample data
    conn.execute("""
        CREATE TABLE sales (
            id INTEGER PRIMARY KEY,
            product_name VARCHAR,
            amount DECIMAL(10,2),
            sale_date DATE
        )
    """)
    
    conn.execute("""
        INSERT INTO sales VALUES 
        (1, 'Product A', 100.00, '2024-01-15'),
        (2, 'Product B', 200.00, '2024-01-16'),
        (3, 'Product A', 150.00, '2024-02-01')
    """)
    
    # Initialize SQL generator
    generator = EnhancedSQLGenerator(conn)
    
    # Test cases
    test_queries = [
        "Show me total sales by product",
        "What are the top selling products?",
        "List all sales in January 2024"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Testing: {query}")
        print('='*60)
        
        start_time = time.time()
        
        try:
            # Test without LLM feedback (fast)
            print("\n1. Testing without LLM feedback...")
            sql, metadata = generator.generate_sql_with_explanation(
                query,
                include_llm_feedback=False,
                return_metrics=True
            )
            
            if sql:
                print(f"✅ SQL generated successfully in {time.time() - start_time:.2f}s")
                print(f"   Generated SQL: {sql[:100]}...")
                print(f"   Cache hit: {metadata.get('cache_hit', False)}")
                print(f"   Generation time: {metadata.get('generation_time', 0):.2f}s")
            else:
                print("❌ Failed to generate SQL")
            
            # Test with LLM feedback (should handle timeout gracefully)
            print("\n2. Testing with LLM feedback (may timeout gracefully)...")
            start_time = time.time()
            
            sql, metadata = generator.generate_sql_with_explanation(
                query,
                include_llm_feedback=True,
                return_metrics=True
            )
            
            if sql:
                print(f"✅ SQL generated successfully in {time.time() - start_time:.2f}s")
                has_feedback = metadata.get('explanation', {}).get('feedback_incorporated', False)
                print(f"   LLM feedback included: {has_feedback}")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    # Test timeout handling
    print(f"\n{'='*60}")
    print("Testing timeout handling...")
    print('='*60)
    
    # This should handle timeout gracefully
    complex_query = "Generate a complex analysis of sales trends with multiple joins and aggregations"
    
    start_time = time.time()
    sql, metadata = generator.generate_sql_with_explanation(
        complex_query,
        include_llm_feedback=True,  # This might timeout
        return_metrics=True
    )
    
    elapsed = time.time() - start_time
    
    if sql:
        print(f"✅ Handled complex query in {elapsed:.2f}s")
        print(f"   Feedback timeout handled: {not metadata.get('explanation', {}).get('feedback_incorporated', False)}")
    else:
        print(f"❌ Failed after {elapsed:.2f}s")
    
    conn.close()
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    test_sql_generation()