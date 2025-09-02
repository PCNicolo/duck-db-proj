"""Test the Copy to Editor functionality for SQL queries."""

from unittest.mock import MagicMock

import pytest


# Mock streamlit session state
@pytest.fixture
def mock_session_state():
    """Create a mock session state."""
    session_state = MagicMock()
    session_state.chat_history = []
    session_state.editor_sql = None
    return session_state


def test_sql_extraction_from_message():
    """Test that SQL is correctly extracted from assistant messages."""
    # Test case 1: SQL with comment header
    content1 = """-- ✅ Valid SQL generated from: You: give me counts of every customer age group...
SELECT COUNT(*), age_group FROM customers GROUP BY age_group LIMIT 100;"""

    sql_lines = []
    for line in content1.split("\n"):
        line_stripped = line.strip()
        if line_stripped and not line_stripped.startswith("--"):
            sql_lines.append(line)
        elif line_stripped and "--" in line_stripped:
            sql_part = line.split("--")[0].strip()
            if sql_part:
                sql_lines.append(sql_part)

    clean_sql = "\n".join(sql_lines).strip()
    assert (
        clean_sql
        == "SELECT COUNT(*), age_group FROM customers GROUP BY age_group LIMIT 100;"
    )

    # Test case 2: SQL with multiple comment lines
    content2 = """-- This is a comment
-- Another comment
SELECT * FROM table_name
WHERE column = 'value'
-- Inline comment
ORDER BY id;"""

    sql_lines = []
    for line in content2.split("\n"):
        line_stripped = line.strip()
        if line_stripped and not line_stripped.startswith("--"):
            sql_lines.append(line)
        elif line_stripped and "--" in line_stripped:
            sql_part = line.split("--")[0].strip()
            if sql_part:
                sql_lines.append(sql_part)

    clean_sql = "\n".join(sql_lines).strip()
    expected = """SELECT * FROM table_name
WHERE column = 'value'
ORDER BY id;"""
    assert clean_sql == expected

    # Test case 3: SQL with inline comments
    content3 = """SELECT id, -- user id
name, -- user name
age FROM users;"""

    sql_lines = []
    for line in content3.split("\n"):
        line_stripped = line.strip()
        if line_stripped and not line_stripped.startswith("--"):
            # Handle inline comments
            if "--" in line:
                sql_part = line.split("--")[0].strip()
                if sql_part:
                    sql_lines.append(sql_part)
            else:
                sql_lines.append(line)
        elif line_stripped and "--" in line_stripped:
            sql_part = line.split("--")[0].strip()
            if sql_part:
                sql_lines.append(sql_part)

    clean_sql = "\n".join(sql_lines).strip()
    expected = """SELECT id,
name,
age FROM users;"""
    assert clean_sql == expected


def test_editor_sql_transfer():
    """Test that SQL is correctly transferred to editor."""
    # Test the logic of setting and clearing editor_sql
    mock_state = MagicMock()

    # Test setting editor_sql
    test_sql = "SELECT * FROM customers LIMIT 10;"
    mock_state.editor_sql = test_sql

    # Simulate transfer
    if mock_state.editor_sql:
        transferred_sql = mock_state.editor_sql
        if (
            transferred_sql
            and isinstance(transferred_sql, str)
            and transferred_sql.strip()
        ):
            query = transferred_sql.strip()
            mock_state.editor_sql = None

    assert query == test_sql
    assert mock_state.editor_sql is None


def test_query_validation():
    """Test query validation before execution."""
    # Test empty query
    query = ""
    assert not query or not query.strip()

    # Test whitespace-only query
    query = "   \n\t   "
    assert not query or not query.strip()

    # Test valid query
    query = "SELECT * FROM table;"
    assert query and query.strip()

    # Test query with extra whitespace
    query = "  SELECT * FROM table;  \n"
    cleaned = query.strip()
    assert cleaned == "SELECT * FROM table;"


def test_sql_with_special_cases():
    """Test SQL extraction with special cases."""
    # Test case with only comments
    content = """-- Only comments here
-- No actual SQL"""

    sql_lines = []
    for line in content.split("\n"):
        line_stripped = line.strip()
        if line_stripped and not line_stripped.startswith("--"):
            sql_lines.append(line)

    assert len(sql_lines) == 0

    # Test case with mixed valid and invalid content
    content = """-- Header comment
SELECT * FROM users
-- Middle comment
WHERE active = true
-- End comment"""

    sql_lines = []
    for line in content.split("\n"):
        line_stripped = line.strip()
        if line_stripped and not line_stripped.startswith("--"):
            sql_lines.append(line)

    clean_sql = "\n".join(sql_lines).strip()
    expected = """SELECT * FROM users
WHERE active = true"""
    assert clean_sql == expected


if __name__ == "__main__":
    test_sql_extraction_from_message()
    test_editor_sql_transfer()
    test_query_validation()
    test_sql_with_special_cases()
    print("All tests passed!")
