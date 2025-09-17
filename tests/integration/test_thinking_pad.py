#!/usr/bin/env python3
"""Test script for validating thinking pad and SQL generation improvements."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import duckdb
from duckdb_analytics.llm.enhanced_sql_generator import EnhancedSQLGenerator
from duckdb_analytics.llm.config import SQL_FAST_MODE_PROMPT, SQL_DETAILED_MODE_PROMPT
import time
import json

def test_sql_generation():
    """Test both fast and detailed mode SQL generation."""
    
    # Create a test database with sample data
    conn = duckdb.connect(':memory:')
    conn.execute("""
        CREATE TABLE sales (
            id INTEGER PRIMARY KEY,
            product VARCHAR,
            amount DECIMAL(10,2),
            sale_date DATE,
            region VARCHAR
        )
    """)
    
    conn.execute("""
        INSERT INTO sales VALUES
        (1, 'Widget A', 100.50, '2024-01-01', 'North'),
        (2, 'Widget B', 200.75, '2024-01-02', 'South'),
        (3, 'Widget A', 150.00, '2024-01-03', 'East'),
        (4, 'Widget C', 300.25, '2024-01-04', 'West'),
        (5, 'Widget B', 175.50, '2024-01-05', 'North')
    """)
    
    # Initialize SQL generator
    generator = EnhancedSQLGenerator(
        duckdb_conn=conn,
        base_url="http://localhost:1234/v1"
    )
    
    # Check if LLM is available
    if not generator.is_available():
        print("❌ LLM is not available. Please start LM Studio.")
        return False
    
    print("✅ LLM is available")
    
    # Test queries
    test_queries = [
        "Show me total sales by product",
        "What are the top 3 products by revenue?",
        "Calculate average sale amount by region"
    ]
    
    results = {}
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Testing: {query}")
        print('='*60)
        
        # Test Fast Mode
        print("\n🚀 FAST MODE:")
        start_time = time.time()
        sql_fast, metadata_fast = generator.generate_sql(
            natural_language_query=query,
            thinking_mode=False,
            return_metrics=True
        )
        fast_time = time.time() - start_time
        
        if sql_fast:
            print(f"SQL Generated: {sql_fast[:100]}...")
            print(f"Generation time: {fast_time:.2f}s")
            print(f"Cache hit: {metadata_fast.get('cache_hit', False)}")
        else:
            print("❌ Failed to generate SQL")
        
        # Test Detailed Mode
        print("\n🧠 DETAILED MODE:")
        start_time = time.time()
        sql_detailed, metadata_detailed = generator.generate_sql(
            natural_language_query=query,
            thinking_mode=True,
            return_metrics=True
        )
        detailed_time = time.time() - start_time
        
        if sql_detailed:
            print(f"SQL Generated: {sql_detailed[:100]}...")
            print(f"Generation time: {detailed_time:.2f}s")
            
            if metadata_detailed.get("detailed_thinking"):
                thinking = metadata_detailed["detailed_thinking"]
                print(f"\n💭 Thinking Process Preview:")
                # Show first 500 chars of thinking
                print(thinking[:500] + "..." if len(thinking) > 500 else thinking)
                
                # Check for structured sections
                sections = ["🎯 STRATEGY:", "📊 BUSINESS CONTEXT:", "🔍 SCHEMA DECISIONS:", "✅ IMPLEMENTATION:"]
                found_sections = sum(1 for section in sections if section in thinking)
                print(f"\nStructured sections found: {found_sections}/4")
            
            # Check for fallback or fixes
            if metadata_detailed.get("fallback_used"):
                print("⚠️ Fallback SQL generation was used")
            if metadata_detailed.get("partial_fix_applied"):
                print("⚠️ Partial SQL fix was applied")
        else:
            print("❌ Failed to generate SQL")
        
        # Store results
        results[query] = {
            "fast_mode": {
                "sql": sql_fast,
                "time": fast_time,
                "success": bool(sql_fast)
            },
            "detailed_mode": {
                "sql": sql_detailed,
                "time": detailed_time,
                "success": bool(sql_detailed),
                "has_thinking": bool(metadata_detailed.get("detailed_thinking"))
            }
        }
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    
    total_tests = len(test_queries) * 2
    successful_tests = sum(
        r["fast_mode"]["success"] + r["detailed_mode"]["success"] 
        for r in results.values()
    )
    
    print(f"✅ Success rate: {successful_tests}/{total_tests} ({successful_tests/total_tests*100:.1f}%)")
    
    avg_fast_time = sum(r["fast_mode"]["time"] for r in results.values()) / len(results)
    avg_detailed_time = sum(r["detailed_mode"]["time"] for r in results.values()) / len(results)
    
    print(f"⚡ Average Fast Mode time: {avg_fast_time:.2f}s")
    print(f"🧠 Average Detailed Mode time: {avg_detailed_time:.2f}s")
    print(f"📊 Speed difference: {avg_detailed_time/avg_fast_time:.1f}x slower in detailed mode")
    
    # Check thinking process quality
    thinking_count = sum(1 for r in results.values() if r["detailed_mode"]["has_thinking"])
    print(f"💭 Detailed thinking generated: {thinking_count}/{len(results)}")
    
    return successful_tests == total_tests

if __name__ == "__main__":
    print("🧪 Testing Thinking Pad and SQL Generation Improvements")
    print("="*60)
    
    success = test_sql_generation()
    
    if success:
        print("\n✅ All tests passed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the output above.")
        sys.exit(1)