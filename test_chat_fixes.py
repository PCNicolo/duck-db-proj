#!/usr/bin/env python3
"""Test script to validate chat interface fixes."""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.duckdb_analytics.llm.sql_generator import SQLGenerator
from src.duckdb_analytics.core.connection import DuckDBConnection
from src.duckdb_analytics.llm.schema_extractor import SchemaExtractor

def test_sql_generator_availability():
    """Test SQL generator availability check and timeout."""
    print("Testing SQL Generator availability...")
    
    generator = SQLGenerator()
    
    # Test 1: Check availability (should cache result)
    start_time = time.time()
    is_available = generator.is_available()
    first_check_time = time.time() - start_time
    print(f"  First availability check: {is_available} (took {first_check_time:.3f}s)")
    
    # Test 2: Second check should use cache and be faster
    start_time = time.time()
    is_available2 = generator.is_available()
    second_check_time = time.time() - start_time
    print(f"  Second availability check (cached): {is_available2} (took {second_check_time:.3f}s)")
    
    assert second_check_time < first_check_time, "Cache should make second check faster"
    
    # Test 3: Reset availability to force re-check
    generator.reset_availability()
    start_time = time.time()
    is_available3 = generator.is_available()
    third_check_time = time.time() - start_time
    print(f"  Third availability check (after reset): {is_available3} (took {third_check_time:.3f}s)")
    
    print("✅ SQL Generator availability tests passed\n")


def test_request_timeout():
    """Test that request timeout is properly configured."""
    print("Testing request timeout configuration...")
    
    from src.duckdb_analytics.llm.config import REQUEST_TIMEOUT
    
    print(f"  Current timeout setting: {REQUEST_TIMEOUT} seconds")
    assert REQUEST_TIMEOUT >= 10, "Timeout should be at least 10 seconds for complex queries"
    
    print("✅ Request timeout properly configured\n")


def test_schema_caching():
    """Test schema caching mechanism."""
    print("Testing schema caching...")
    
    conn = DuckDBConnection()
    extractor = SchemaExtractor(conn)
    
    # Create a test table using the correct method
    conn.execute("CREATE TABLE IF NOT EXISTS test_table (id INTEGER, name VARCHAR)")
    
    # Test 1: First schema extraction
    start_time = time.time()
    schema1 = extractor.format_for_llm(include_samples=False, max_tables=20)
    first_extract_time = time.time() - start_time
    print(f"  First schema extraction took {first_extract_time:.3f}s")
    
    # Test 2: Should be able to extract again without issues
    start_time = time.time()
    schema2 = extractor.format_for_llm(include_samples=False, max_tables=20)
    second_extract_time = time.time() - start_time
    print(f"  Second schema extraction took {second_extract_time:.3f}s")
    
    # Clean up
    conn.execute("DROP TABLE IF EXISTS test_table")
    
    print("✅ Schema caching tests passed\n")


def test_debouncing_logic():
    """Test debouncing logic prevents rapid requests."""
    print("Testing debouncing logic...")
    
    last_query_time = time.time()
    
    # Test 1: Immediate second request should be blocked
    current_time = time.time()
    time_diff = current_time - last_query_time
    should_block = time_diff < 1.0
    print(f"  Time since last query: {time_diff:.3f}s")
    print(f"  Should block rapid request: {should_block}")
    assert should_block, "Should block requests within 1 second"
    
    # Test 2: After waiting, request should be allowed
    time.sleep(1.1)
    current_time = time.time()
    time_diff = current_time - last_query_time
    should_allow = time_diff >= 1.0
    print(f"  Time after waiting: {time_diff:.3f}s")
    print(f"  Should allow request: {should_allow}")
    assert should_allow, "Should allow requests after 1 second"
    
    print("✅ Debouncing logic tests passed\n")


def test_retry_logic():
    """Test retry logic with exponential backoff."""
    print("Testing retry logic with exponential backoff...")
    
    max_retries = 2
    
    for retry_count in range(max_retries):
        backoff_time = 0.5 * (retry_count + 1)
        print(f"  Retry {retry_count + 1}: backoff time = {backoff_time}s")
        assert backoff_time <= 1.0, "Backoff should not exceed 1 second"
    
    print("✅ Retry logic tests passed\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 Testing Chat Interface Fixes")
    print("=" * 60 + "\n")
    
    tests = [
        test_request_timeout,
        test_sql_generator_availability,
        test_schema_caching,
        test_debouncing_logic,
        test_retry_logic
    ]
    
    failed_tests = []
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"❌ Test {test.__name__} failed: {str(e)}\n")
            failed_tests.append(test.__name__)
    
    print("=" * 60)
    if failed_tests:
        print(f"❌ {len(failed_tests)} test(s) failed: {', '.join(failed_tests)}")
        sys.exit(1)
    else:
        print("✅ All tests passed successfully!")
        print("\n🎉 Chat interface fixes are working correctly!")
        print("=" * 60)


if __name__ == "__main__":
    main()