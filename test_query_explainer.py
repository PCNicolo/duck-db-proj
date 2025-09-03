#!/usr/bin/env python3
"""
Test script for the Query Explainer with LLM Feedback Integration.

This script tests the new query explanation feature with LM-Studio feedback.
"""

import sys
import os
sys.path.append('src')

from duckdb_analytics.llm.query_explainer import QueryExplainer
from duckdb_analytics.llm.enhanced_sql_generator import EnhancedSQLGenerator
from duckdb_analytics.core.connection import DuckDBConnection
from duckdb_analytics.core.query_engine import QueryEngine
import duckdb
import pandas as pd


def test_query_explainer():
    """Test the query explainer functionality."""
    print("=" * 60)
    print("Testing Query Explainer with LLM Feedback Integration")
    print("=" * 60)
    
    # Initialize components
    print("\n1. Initializing components...")
    
    # Create a test connection
    conn = duckdb.connect(':memory:')
    
    # Create test data
    conn.execute("""
        CREATE TABLE sales AS 
        SELECT * FROM (VALUES
            ('2024-01', 'Product A', 1000),
            ('2024-01', 'Product B', 1500),
            ('2024-02', 'Product A', 1200),
            ('2024-02', 'Product B', 1800),
            ('2024-03', 'Product A', 1100),
            ('2024-03', 'Product B', 1600)
        ) AS t(month, product, amount)
    """)
    
    print("✓ Test data created")
    
    # Initialize SQL generator with explainer
    sql_generator = EnhancedSQLGenerator(
        duckdb_conn=conn,
        base_url="http://localhost:1234/v1",
        warm_cache=False
    )
    print("✓ SQL Generator initialized")
    
    # Test cases
    test_queries = [
        "Show me total sales by month",
        "What are the top selling products?",
        "Calculate average sales per product"
    ]
    
    print("\n2. Testing Query Explanations...")
    print("-" * 40)
    
    for i, nl_query in enumerate(test_queries, 1):
        print(f"\nTest Case {i}: {nl_query}")
        print("-" * 40)
        
        # Generate SQL with explanation
        sql, metadata = sql_generator.generate_sql_with_explanation(
            natural_language_query=nl_query,
            include_llm_feedback=True
        )
        
        if sql:
            print(f"Generated SQL:\n{sql}\n")
            
            if metadata.get("explanation"):
                explanation = metadata["explanation"]
                print(f"Explanation:\n{explanation['explanation']}\n")
                
                print(f"Confidence: {explanation['confidence']:.0%}")
                print(f"Feedback Incorporated: {explanation['feedback_incorporated']}")
                
                if explanation.get('query_breakdown'):
                    print("\nQuery Breakdown:")
                    for step in explanation['query_breakdown']:
                        print(f"  Step {step['step']}: {step['action']}")
                        print(f"    → {step['description']}")
            else:
                print("No explanation generated")
        else:
            print("Failed to generate SQL")
    
    print("\n" + "=" * 60)
    print("Testing Complete!")
    print("=" * 60)


def test_standalone_explainer():
    """Test the query explainer as a standalone component."""
    print("\n" + "=" * 60)
    print("Testing Standalone Query Explainer")
    print("=" * 60)
    
    # Initialize explainer
    explainer = QueryExplainer()
    
    # Test SQL queries
    test_sqls = [
        (
            "SELECT month, SUM(amount) as total FROM sales GROUP BY month ORDER BY month",
            "Show me total sales by month"
        ),
        (
            "SELECT product, SUM(amount) as total FROM sales GROUP BY product ORDER BY total DESC LIMIT 5",
            "What are the top 5 selling products?"
        ),
        (
            "SELECT COUNT(DISTINCT product) as product_count, AVG(amount) as avg_sales FROM sales",
            "How many products do we have and what's the average sale?"
        )
    ]
    
    print("\nTesting without LLM feedback...")
    print("-" * 40)
    
    for sql, nl_query in test_sqls:
        print(f"\nQuery: {nl_query}")
        print(f"SQL: {sql[:50]}...")
        
        result = explainer.generate_explanation(
            sql_query=sql,
            natural_language_query=nl_query,
            schema_context={"tables": ["sales"], "columns": ["month", "product", "amount"]},
            llm_feedback=None
        )
        
        print(f"Explanation: {result['explanation'][:200]}...")
        print(f"Steps: {len(result['query_breakdown'])}")
        print(f"Confidence: {result['confidence']:.0%}")
    
    print("\n" + "=" * 60)
    print("Standalone Testing Complete!")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Query Explainer")
    parser.add_argument("--standalone", action="store_true", 
                        help="Test standalone explainer without LLM")
    parser.add_argument("--full", action="store_true",
                        help="Test with LM-Studio integration (requires LM-Studio running)")
    
    args = parser.parse_args()
    
    if args.standalone:
        test_standalone_explainer()
    
    if args.full:
        print("\n⚠️  Note: This test requires LM-Studio to be running on localhost:1234")
        input("Press Enter to continue...")
        test_query_explainer()
    
    if not args.standalone and not args.full:
        # Default: run standalone test
        test_standalone_explainer()
        print("\n💡 Tip: Use --full to test with LM-Studio integration")