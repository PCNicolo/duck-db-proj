#!/usr/bin/env python3
"""
Manual test script for Copy to Editor functionality.
Run this to test the SQL extraction logic.
"""

def extract_sql_from_message(content):
    """Extract SQL from a message content, removing comments."""
    sql_lines = []
    for line in content.split("\n"):
        line_stripped = line.strip()
        # Skip comment lines but keep SQL lines
        if line_stripped and not line_stripped.startswith("--"):
            sql_lines.append(line)
        # Also handle inline comments (e.g., "SELECT * -- comment")
        elif line_stripped and "--" in line_stripped:
            # Extract the SQL part before the comment
            sql_part = line.split("--")[0].strip()
            if sql_part:
                sql_lines.append(sql_part)
    
    if sql_lines:
        return "\n".join(sql_lines).strip()
    return ""


# Test cases
test_cases = [
    {
        "name": "Valid SQL with header comment",
        "input": """-- ✅ Valid SQL generated from: You: give me counts of every customer age group...
SELECT COUNT(*), age_group FROM customers GROUP BY age_group LIMIT 100;""",
        "expected": "SELECT COUNT(*), age_group FROM customers GROUP BY age_group LIMIT 100;"
    },
    {
        "name": "SQL with multiple comments",
        "input": """-- Header comment
SELECT * FROM users
-- Middle comment
WHERE active = true
-- End comment""",
        "expected": """SELECT * FROM users
WHERE active = true"""
    },
    {
        "name": "SQL with inline comments",
        "input": """SELECT 
    COUNT(*) as total, -- count all rows
    age_group -- group by this column
FROM customers 
GROUP BY age_group;""",
        "expected": """SELECT
    COUNT(*) as total,
    age_group
FROM customers
GROUP BY age_group;"""
    }
]

print("Testing SQL extraction from messages:")
print("=" * 50)

for i, test in enumerate(test_cases, 1):
    print(f"\nTest {i}: {test['name']}")
    print(f"Input:\n{test['input']}")
    
    result = extract_sql_from_message(test['input'])
    
    print(f"\nExtracted SQL:\n{result}")
    print(f"\nExpected:\n{test['expected']}")
    
    if result == test['expected']:
        print("✅ PASSED")
    else:
        print("❌ FAILED")
        print(f"Difference: Got '{result}' but expected '{test['expected']}'")

print("\n" + "=" * 50)
print("Manual testing complete!")
print("\nTo test in the app:")
print("1. Run: streamlit run app.py")
print("2. Ask the LLM to generate a SQL query")
print("3. Click 'Copy to Editor' button")
print("4. Verify the SQL appears correctly in the editor")
print("5. Click the red Execute button")
print("6. Check that the query runs without syntax errors")