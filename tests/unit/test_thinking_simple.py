#!/usr/bin/env python3
"""Simple test to verify thinking pad functionality."""

import streamlit as st
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Mock streamlit session state for testing
if 'session_state' not in dir(st):
    class MockSessionState:
        def __init__(self):
            self.enable_thinking_pad = True
            self.current_sql = ""
    st.session_state = MockSessionState()

from duckdb_analytics.llm.config import SQL_DETAILED_MODE_PROMPT, SQL_FAST_MODE_PROMPT

def test_prompts():
    """Test that prompts are correctly configured."""
    
    print("Testing Prompt Configuration")
    print("=" * 60)
    
    # Check Fast Mode Prompt
    print("\n🚀 FAST MODE PROMPT:")
    print("-" * 40)
    print(f"Length: {len(SQL_FAST_MODE_PROMPT)} characters")
    print("First 200 chars:", SQL_FAST_MODE_PROMPT[:200])
    assert "Generate ONLY valid DuckDB SQL" in SQL_FAST_MODE_PROMPT
    print("✅ Fast mode prompt validated")
    
    # Check Detailed Mode Prompt
    print("\n🧠 DETAILED MODE PROMPT:")
    print("-" * 40)
    print(f"Length: {len(SQL_DETAILED_MODE_PROMPT)} characters")
    print("First 300 chars:", SQL_DETAILED_MODE_PROMPT[:300])
    
    # Check for SQL-first structure
    assert "SQL QUERY:" in SQL_DETAILED_MODE_PROMPT
    assert "ANALYSIS:" in SQL_DETAILED_MODE_PROMPT
    assert "🎯 STRATEGY:" in SQL_DETAILED_MODE_PROMPT
    assert "📊 BUSINESS CONTEXT:" in SQL_DETAILED_MODE_PROMPT
    assert "🔍 SCHEMA DECISIONS:" in SQL_DETAILED_MODE_PROMPT
    assert "✅ IMPLEMENTATION:" in SQL_DETAILED_MODE_PROMPT
    
    # Verify SQL comes before analysis
    sql_pos = SQL_DETAILED_MODE_PROMPT.find("SQL QUERY:")
    analysis_pos = SQL_DETAILED_MODE_PROMPT.find("ANALYSIS:")
    assert sql_pos < analysis_pos, "SQL should come before analysis in prompt"
    
    print("✅ Detailed mode prompt validated")
    print(f"✅ SQL-first structure confirmed (SQL at pos {sql_pos}, Analysis at pos {analysis_pos})")
    
    return True

def test_thinking_pad_ui():
    """Test the enhanced thinking pad UI component."""
    from duckdb_analytics.ui.enhanced_thinking_pad import EnhancedThinkingPad
    
    print("\n" + "=" * 60)
    print("Testing Enhanced Thinking Pad UI")
    print("=" * 60)
    
    # Create a mock container
    class MockContainer:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
    
    # Test thinking pad initialization
    pad = EnhancedThinkingPad(MockContainer())
    assert pad is not None
    print("✅ Thinking pad initialized")
    
    # Test parsing of structured thinking
    test_thinking = """
🎯 STRATEGY: I will use aggregation to sum sales by product. This gives us total revenue per product.

📊 BUSINESS CONTEXT: This shows which products generate the most revenue. Important for inventory and marketing decisions.

🔍 SCHEMA DECISIONS: Using the sales table with product and amount columns. No joins needed for this simple aggregation.

✅ IMPLEMENTATION: Using SUM() with GROUP BY for efficient aggregation. Added ORDER BY for better readability.
"""
    
    sections = pad._parse_thinking_sections(test_thinking)
    assert len(sections) == 4
    assert sections["🎯 STRATEGY"] != ""
    assert sections["📊 BUSINESS CONTEXT"] != ""
    print("✅ Thinking sections parsed correctly")
    print(f"   Found {len([v for v in sections.values() if v])} non-empty sections")
    
    return True

if __name__ == "__main__":
    print("🧪 Testing Thinking Pad Components")
    print("=" * 60)
    
    try:
        # Test prompts
        if test_prompts():
            print("\n✅ Prompt tests passed!")
        
        # Test UI components
        if test_thinking_pad_ui():
            print("\n✅ UI component tests passed!")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED SUCCESSFULLY!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)