#!/usr/bin/env python3
"""
Direct test of enhanced generator with detailed mode
"""

import sys
import duckdb
import streamlit as st

# Add src to path
sys.path.append('src')

from src.duckdb_analytics.llm.enhanced_sql_generator import EnhancedSQLGenerator

def test_direct():
    """Test enhanced generator directly with detailed mode."""
    
    print("🧪 Testing Enhanced Generator Directly")
    print("=" * 50)
    
    # Create DuckDB connection
    conn = duckdb.connect(":memory:")
    
    # Create sample data
    conn.execute("""
        CREATE TABLE products (
            id INTEGER,
            name VARCHAR,
            category VARCHAR,
            price DECIMAL,
            profit_margin DECIMAL
        )
    """)
    
    conn.execute("""
        INSERT INTO products VALUES 
        (1, 'Widget A', 'Electronics', 100.50, 0.25),
        (2, 'Widget B', 'Electronics', 75.25, 0.35),
        (3, 'Gadget C', 'Tools', 120.00, 0.40),
        (4, 'Device D', 'Electronics', 90.75, 0.20)
    """)
    
    # Initialize enhanced generator
    generator = EnhancedSQLGenerator(conn)
    
    # Test query
    test_query = "show me the products with highest profit margin"
    
    print(f"📝 Test Query: '{test_query}'")
    print()
    
    # Test detailed mode
    print("🧠 Testing Detailed Thinking Mode")
    print("-" * 40)
    
    try:
        sql, metadata = generator.generate_sql_with_explanation(
            test_query,
            thinking_mode=True,
            return_metrics=True,
            include_llm_feedback=False
        )
        
        print(f"✅ SQL Generated: {sql}")
        print()
        print(f"📊 Metadata keys: {list(metadata.keys())}")
        
        # Check for detailed thinking
        if 'detailed_thinking' in metadata:
            thinking = metadata['detailed_thinking']
            print(f"💭 Detailed Thinking Found: {len(str(thinking))} characters")
            print("=" * 50)
            print(thinking)
            print("=" * 50)
        else:
            print("❌ No detailed_thinking in metadata")
            
        # Check for other explanation data
        if 'explanation' in metadata:
            explanation = metadata['explanation']
            print(f"🔍 Found explanation: {type(explanation)} - {explanation}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_direct()