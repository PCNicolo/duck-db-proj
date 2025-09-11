#!/usr/bin/env python3
"""
Test script for LLM Thinking Pad Feature
Tests both Fast Mode and Detailed Thinking Mode
"""

import sys
import time
import duckdb
from src.duckdb_analytics.llm.enhanced_sql_generator import EnhancedSQLGenerator

def test_thinking_modes():
    """Test both fast and detailed thinking modes."""
    print("🧪 Testing LLM Thinking Pad Modes")
    print("=" * 50)
    
    # Create DuckDB connection
    conn = duckdb.connect(":memory:")
    
    # Create sample data
    conn.execute("""
        CREATE TABLE sales (
            id INTEGER,
            product VARCHAR,
            amount DECIMAL,
            date DATE
        )
    """)
    
    conn.execute("""
        INSERT INTO sales VALUES 
        (1, 'Widget A', 100.50, '2024-01-15'),
        (2, 'Widget B', 75.25, '2024-01-16'),
        (3, 'Widget A', 120.00, '2024-01-17'),
        (4, 'Widget C', 90.75, '2024-01-18')
    """)
    
    # Initialize generator
    generator = EnhancedSQLGenerator(conn)
    
    # Test query
    test_query = "Show me total sales by product"
    
    print(f"📝 Test Query: '{test_query}'")
    print()
    
    # Test Fast Mode
    print("🚀 Testing Fast Mode (thinking_mode=False)")
    print("-" * 40)
    
    start_time = time.time()
    try:
        sql_fast, metadata_fast = generator.generate_sql_with_explanation(
            test_query,
            thinking_mode=False,
            return_metrics=True
        )
        
        fast_time = time.time() - start_time
        
        print(f"✅ SQL Generated: {sql_fast}")
        print(f"⏱️ Generation Time: {fast_time:.2f}s")
        print(f"🎯 Target: <3s - {'✅ PASS' if fast_time < 3.0 else '❌ FAIL'}")
        
        if 'detailed_thinking' in metadata_fast:
            print(f"💭 Thinking Process: {metadata_fast['detailed_thinking'] or 'None (Fast Mode)'}")
        
    except Exception as e:
        print(f"❌ Fast Mode Error: {e}")
        fast_time = float('inf')
    
    print()
    
    # Test Detailed Mode  
    print("🧠 Testing Detailed Thinking Mode (thinking_mode=True)")
    print("-" * 40)
    
    start_time = time.time()
    try:
        sql_detailed, metadata_detailed = generator.generate_sql_with_explanation(
            test_query,
            thinking_mode=True,
            return_metrics=True
        )
        
        detailed_time = time.time() - start_time
        
        print(f"✅ SQL Generated: {sql_detailed}")
        print(f"⏱️ Generation Time: {detailed_time:.2f}s")
        print(f"🎯 Target: 10-15s - {'✅ PASS' if 10.0 <= detailed_time <= 15.0 else '❌ FAIL'}")
        
        if 'detailed_thinking' in metadata_detailed:
            thinking = metadata_detailed['detailed_thinking']
            if thinking:
                print(f"💭 Thinking Process Preview:")
                print(thinking[:200] + "..." if len(thinking) > 200 else thinking)
            else:
                print("💭 No detailed thinking captured")
        
        # Debug: Print all metadata to see what's available
        print(f"🔍 Debug - All metadata keys: {list(metadata_detailed.keys())}")
        if 'detailed_thinking' in metadata_detailed:
            print(f"🔍 Debug - detailed_thinking value: '{metadata_detailed['detailed_thinking']}'")
        else:
            print("🔍 Debug - detailed_thinking not in metadata")
        
    except Exception as e:
        print(f"❌ Detailed Mode Error: {e}")
        detailed_time = float('inf')
    
    print()
    
    # Summary
    print("📊 Performance Summary")
    print("-" * 40)
    print(f"Fast Mode: {fast_time:.2f}s {'✅' if fast_time < 3.0 else '❌'}")
    print(f"Detailed Mode: {detailed_time:.2f}s {'✅' if 10.0 <= detailed_time <= 15.0 else '❌'}")
    
    if fast_time < float('inf') and detailed_time < float('inf'):
        speedup = detailed_time / fast_time
        print(f"Speed Difference: {speedup:.1f}x faster in Fast Mode")
    
    conn.close()

if __name__ == "__main__":
    test_thinking_modes()