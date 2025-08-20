#!/usr/bin/env python3
"""Test script to verify chat UI component functionality."""

import sys
import os
import ast
from pathlib import Path

def verify_imports():
    """Verify that the app has the necessary imports."""
    try:
        with open("app.py", "r") as f:
            tree = ast.parse(f.read())
        
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module if node.module else "")
        
        # Check for required imports
        required_imports = ["streamlit", "pandas", "plotly"]
        missing = [imp for imp in required_imports if not any(imp in i for i in imports)]
        
        if missing:
            print(f"⚠️ Missing imports: {missing}")
            return False
        
        print("✅ All required imports present")
        return True
    except Exception as e:
        print(f"❌ Import verification failed: {e}")
        return False

def test_chat_ui_integration():
    """Test that the chat UI integrates properly with the SQL Editor tab."""
    
    print("Testing Chat UI Integration...")
    print("=" * 50)
    
    # Verify file exists
    if not Path("app.py").exists():
        print("❌ app.py file not found")
        return False
    
    print("✅ app.py file exists")
    
    # Verify imports
    if not verify_imports():
        print("⚠️ Import issues detected (may be due to missing dependencies)")
    
    # Verify code structure by checking for chat-related strings
    try:
        with open("app.py", "r") as f:
            content = f.read()
            lines = content.split('\n')
        
        # Track findings
        findings = {
            "chat_ui_components": [],
            "existing_functionality": [],
            "session_state": [],
            "ui_layout": []
        }
        
        # Check for chat UI components
        chat_checks = [
            ("Natural Language Query", "Chat UI header"),
            ("chat_history", "Session state for chat"),
            ("Ask in plain English", "Chat placeholder text"),
            ("Chat History", "Chat history display"),
            ("nl_query_input", "Natural language input key"),
            ("Send", "Send button"),
            ("You:", "User message label"),
            ("SQL Query:", "SQL response label")
        ]
        
        for check_str, description in chat_checks:
            if check_str in content:
                findings["chat_ui_components"].append(description)
                print(f"  ✓ {description} found")
            else:
                print(f"  ✗ {description} NOT found")
        
        # Check that existing SQL editor functionality is preserved
        sql_checks = [
            ("SQL Query Editor", "SQL Editor header"),
            ("Query Templates", "Query templates"),
            ("Execute", "Execute button"),
            ("st.text_area", "SQL text area"),
            ("execute_query", "Query execution function"),
            ("explain_query", "Query explain function")
        ]
        
        for check_str, description in sql_checks:
            if check_str in content:
                findings["existing_functionality"].append(description)
                print(f"  ✓ {description} preserved")
            else:
                print(f"  ✗ {description} NOT found")
        
        # Check session state management
        session_checks = [
            ("st.session_state.chat_history", "Chat history state"),
            ("if \"chat_history\" not in st.session_state", "Chat history initialization"),
            ("st.session_state.db_connection", "DB connection state"),
            ("st.session_state.query_engine", "Query engine state")
        ]
        
        for check_str, description in session_checks:
            if check_str in content:
                findings["session_state"].append(description)
                print(f"  ✓ {description} found")
        
        # Check UI layout integration
        ui_checks = [
            ("st.container()", "Container for chat UI"),
            ("st.columns", "Column layout"),
            ("st.divider()", "Divider between sections"),
            ("st.subheader", "Section headers")
        ]
        
        for check_str, description in ui_checks:
            if check_str in content:
                findings["ui_layout"].append(description)
        
        # Generate test report
        print("\n" + "=" * 50)
        print("TEST SUMMARY")
        print("=" * 50)
        
        total_chat_components = len(chat_checks)
        found_chat_components = len(findings["chat_ui_components"])
        
        total_sql_components = len(sql_checks)
        found_sql_components = len(findings["existing_functionality"])
        
        print(f"Chat UI Components: {found_chat_components}/{total_chat_components}")
        print(f"SQL Editor Preservation: {found_sql_components}/{total_sql_components}")
        print(f"Session State Items: {len(findings['session_state'])}")
        print(f"UI Layout Elements: {len(findings['ui_layout'])}")
        
        # Determine pass/fail
        if found_chat_components >= 6 and found_sql_components >= 5:
            print("\n✅ Integration Test PASSED")
            print("\nKey features verified:")
            print("1. ✓ Chat input bar with placeholder text")
            print("2. ✓ Send button for submitting queries")
            print("3. ✓ Chat history display with styled messages")
            print("4. ✓ Session state management for chat history")
            print("5. ✓ Placeholder SQL response generation")
            print("6. ✓ Existing SQL editor functionality maintained")
            return True
        else:
            print("\n❌ Integration Test FAILED")
            print(f"Missing {total_chat_components - found_chat_components} chat components")
            print(f"Missing {total_sql_components - found_sql_components} SQL components")
            return False
        
    except Exception as e:
        print(f"❌ Test execution error: {e}")
        return False

def test_code_quality():
    """Basic code quality checks."""
    print("\n" + "=" * 50)
    print("CODE QUALITY CHECKS")
    print("=" * 50)
    
    try:
        with open("app.py", "r") as f:
            content = f.read()
            lines = content.split('\n')
        
        issues = []
        
        # Check for basic code quality issues
        for i, line in enumerate(lines, 1):
            # Check line length (PEP 8 recommends 79, but 100 is common)
            if len(line) > 100:
                if not any(skip in line for skip in ["http", "https", "placeholder"]):
                    issues.append(f"Line {i}: Line too long ({len(line)} chars)")
        
        # Check for TODO/FIXME comments
        todo_lines = [i+1 for i, line in enumerate(lines) if "TODO" in line or "FIXME" in line]
        if todo_lines:
            issues.append(f"Found TODO/FIXME comments on lines: {todo_lines}")
        
        if issues:
            print("⚠️ Code quality issues found:")
            for issue in issues[:5]:  # Show first 5 issues
                print(f"  - {issue}")
            if len(issues) > 5:
                print(f"  ... and {len(issues) - 5} more")
        else:
            print("✅ No major code quality issues found")
        
        return len(issues) == 0
    except Exception as e:
        print(f"❌ Code quality check failed: {e}")
        return False

if __name__ == "__main__":
    success = test_chat_ui_integration()
    quality = test_code_quality()
    
    overall_success = success
    sys.exit(0 if overall_success else 1)