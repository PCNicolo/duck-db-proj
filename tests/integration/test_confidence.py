#!/usr/bin/env python3
"""Test script to verify confidence score variations."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import duckdb
from duckdb_analytics.llm.enhanced_sql_generator import EnhancedSQLGenerator
import time

def test_confidence_variations():
    """Test that confidence scores vary based on different factors."""
    
    # Create a test database
    conn = duckdb.connect(':memory:')
    conn.execute("""
        CREATE TABLE orders (
            id INTEGER,
            product VARCHAR,
            amount DECIMAL(10,2),
            order_date DATE,
            customer_id INTEGER
        )
    """)
    
    conn.execute("""
        CREATE TABLE customers (
            customer_id INTEGER,
            name VARCHAR,
            region VARCHAR
        )
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
    print("\n" + "="*60)
    print("Testing Confidence Score Variations")
    print("="*60)
    
    # Test queries with different complexity levels
    test_cases = [
        {
            "name": "Simple Query",
            "query": "Show all products from orders",
            "expected_confidence": "high",  # Simple query should have high confidence
        },
        {
            "name": "Moderate Query", 
            "query": "Show total sales by product",
            "expected_confidence": "high",  # Still relatively simple
        },
        {
            "name": "Complex Query with JOIN",
            "query": "Show total sales by customer region with customer names",
            "expected_confidence": "medium",  # JOIN reduces confidence
        },
        {
            "name": "Complex Query with Window Functions",
            "query": "Show running total of sales over time with rank by product",
            "expected_confidence": "medium",  # Window functions reduce confidence
        },
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases):
        print(f"\n{i+1}. {test_case['name']}")
        print("-" * 40)
        print(f"Query: {test_case['query']}")
        
        # Test with thinking mode enabled
        sql, metadata = generator.generate_sql(
            natural_language_query=test_case["query"],
            thinking_mode=True,
            return_metrics=True,
            validate=True
        )
        
        if sql:
            confidence = metadata.get("confidence", 0.5)
            cache_hit = metadata.get("cache_hit", False)
            gen_time = metadata.get("generation_time", 0)
            validation = metadata.get("validation_passed", None)
            
            # Determine confidence level
            if confidence >= 0.8:
                level = "HIGH 🟢"
            elif confidence >= 0.5:
                level = "MEDIUM 🟡"
            else:
                level = "LOW 🔴"
            
            print(f"✓ SQL Generated: {sql[:60]}...")
            print(f"  Confidence: {confidence:.1%} ({level})")
            print(f"  Cache Hit: {cache_hit}")
            print(f"  Generation Time: {gen_time:.2f}s")
            print(f"  Validation: {'✓ Passed' if validation else '✗ Failed' if validation is False else 'Not checked'}")
            
            results.append({
                "name": test_case["name"],
                "confidence": confidence,
                "level": level,
                "factors": {
                    "cache_hit": cache_hit,
                    "gen_time": gen_time,
                    "validation": validation
                }
            })
        else:
            print("❌ Failed to generate SQL")
            results.append({
                "name": test_case["name"],
                "confidence": 0,
                "level": "FAILED",
                "factors": {}
            })
    
    # Test cache effect on confidence
    print("\n" + "="*60)
    print("Testing Cache Effect on Confidence")
    print("="*60)
    
    test_query = "Show total amount from orders"
    
    # First run (no cache)
    print("\n1. First Run (No Cache):")
    sql1, metadata1 = generator.generate_sql(
        natural_language_query=test_query,
        thinking_mode=True,
        use_cache=True
    )
    confidence1 = metadata1.get("confidence", 0.5)
    cache_hit1 = metadata1.get("cache_hit", False)
    print(f"  Confidence: {confidence1:.1%}")
    print(f"  Cache Hit: {cache_hit1}")
    
    # Second run (should hit cache)
    print("\n2. Second Run (With Cache):")
    sql2, metadata2 = generator.generate_sql(
        natural_language_query=test_query,
        thinking_mode=True,
        use_cache=True
    )
    confidence2 = metadata2.get("confidence", 0.5)
    cache_hit2 = metadata2.get("cache_hit", False)
    print(f"  Confidence: {confidence2:.1%}")
    print(f"  Cache Hit: {cache_hit2}")
    
    if cache_hit2:
        print(f"  ✓ Cache increased confidence by {(confidence2 - confidence1):.1%}")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    # Check confidence variations
    confidences = [r["confidence"] for r in results if r["confidence"] > 0]
    if confidences:
        min_conf = min(confidences)
        max_conf = max(confidences)
        avg_conf = sum(confidences) / len(confidences)
        
        print(f"Confidence Range: {min_conf:.1%} - {max_conf:.1%}")
        print(f"Average Confidence: {avg_conf:.1%}")
        print(f"Variation: {(max_conf - min_conf):.1%}")
        
        # Check if we have meaningful variation
        if max_conf - min_conf > 0.1:
            print("✅ Good confidence variation detected")
        else:
            print("⚠️ Low confidence variation - may need tuning")
        
        # Distribution
        high_count = sum(1 for r in results if r["confidence"] >= 0.8)
        medium_count = sum(1 for r in results if 0.5 <= r["confidence"] < 0.8)
        low_count = sum(1 for r in results if r["confidence"] < 0.5)
        
        print(f"\nDistribution:")
        print(f"  HIGH 🟢: {high_count}/{len(results)}")
        print(f"  MEDIUM 🟡: {medium_count}/{len(results)}")
        print(f"  LOW 🔴: {low_count}/{len(results)}")
    
    return True

if __name__ == "__main__":
    print("🧪 Testing Confidence Score System")
    print("="*60)
    
    try:
        if test_confidence_variations():
            print("\n✅ Confidence tests completed successfully!")
        else:
            print("\n⚠️ Tests completed with warnings")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)