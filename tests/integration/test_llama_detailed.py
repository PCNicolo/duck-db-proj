#!/usr/bin/env python3
"""
Direct test of detailed mode with Llama 3.1 8B
"""

import duckdb
from openai import OpenAI

def test_llama_detailed():
    """Test Llama 3.1 with the new detailed prompt format."""
    
    print("🧪 Testing Llama 3.1 with New Detailed Format")
    print("=" * 50)
    
    # Initialize client for LM Studio
    client = OpenAI(
        base_url="http://localhost:1234/v1",
        api_key="not-needed"
    )
    
    # New simplified prompt
    system_prompt = """You are a database expert. When I give you a natural language query, provide a detailed analysis following this EXACT format:

QUERY ANALYSIS:

🎯 STRATEGY: Write 2-3 sentences explaining your approach to this query - what method you chose and why this is the best strategy for this specific request.

📊 BUSINESS CONTEXT: Write 2-3 sentences explaining what business question this answers and why the results matter to stakeholders.

🔍 SCHEMA DECISIONS: Write 2-3 sentences explaining which tables/columns you used and why, including any JOIN decisions and data type considerations.

✅ IMPLEMENTATION: Write 2-3 sentences explaining why you chose this specific SQL syntax and any performance considerations or alternatives.

SQL:
```sql
[Your SQL query here]
```

CRITICAL: You MUST provide detailed explanations in ALL sections above. Do not skip any sections. Each section needs 2-3 complete sentences."""

    # Schema context
    schema_context = """
Available Tables:
- products (id, name, category, price, profit_margin)
- sales (id, product_id, quantity, date, total_amount)
"""
    
    # Test query
    user_query = "show me the products with the highest profit margin, order from highest profit to lowest limit 20"
    
    print(f"📝 Query: '{user_query}'")
    print(f"💾 Schema: {schema_context.strip()}")
    print()
    
    try:
        print("🔄 Sending request to LM Studio...")
        response = client.chat.completions.create(
            model="meta-llama-3.1-8b-instruct",
            messages=[
                {"role": "system", "content": system_prompt + "\n\nSchema:\n" + schema_context},
                {"role": "user", "content": user_query}
            ],
            max_tokens=2500,
            temperature=0.1,
            timeout=30
        )
        
        result = response.choices[0].message.content.strip()
        
        print("✅ Response received!")
        print("=" * 50)
        print(result)
        print("=" * 50)
        
        # Check if response contains expected sections
        sections = ["🎯 STRATEGY:", "📊 BUSINESS CONTEXT:", "🔍 SCHEMA DECISIONS:", "✅ IMPLEMENTATION:", "SQL:"]
        missing_sections = []
        
        for section in sections:
            if section not in result:
                missing_sections.append(section)
        
        if missing_sections:
            print(f"❌ Missing sections: {missing_sections}")
        else:
            print("✅ All sections present!")
            
        # Count sentences in each section
        if "🎯 STRATEGY:" in result and "📊 BUSINESS CONTEXT:" in result:
            strategy_section = result.split("🎯 STRATEGY:")[1].split("📊 BUSINESS CONTEXT:")[0].strip()
            sentence_count = strategy_section.count('.') + strategy_section.count('!') + strategy_section.count('?')
            print(f"📊 Strategy section sentences: {sentence_count}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_llama_detailed()