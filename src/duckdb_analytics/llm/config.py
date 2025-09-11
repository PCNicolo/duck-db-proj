"""Enhanced configuration for LM Studio LLM integration."""

# LM Studio connection settings
LM_STUDIO_URL = "http://localhost:1234/v1"
MODEL_NAME = "meta-llama-3.1-8b-instruct"  # Use the available model in LM Studio

# Request settings
REQUEST_TIMEOUT = 5.0  # Fast mode timeout (was 30.0)
REQUEST_TIMEOUT_DETAILED = 120.0  # Detailed thinking mode timeout - needs much longer for complete analysis
FEEDBACK_TIMEOUT = 1.0  # Reduced feedback timeout (was 3.0)
# Token limits for different modes
MAX_TOKENS = 2000  # Legacy default
MAX_TOKENS_FAST_MODE = 800    # Fast mode: minimal tokens for speed
MAX_TOKENS_DETAILED_MODE = 4000  # Detailed mode: more tokens for comprehensive explanations
TEMPERATURE = 0.1  # Low temperature for consistent SQL generation

# Context window management
MAX_CONTEXT_TOKENS = 4000  # Maximum tokens for context (adjust based on model)
SCHEMA_TOKEN_ESTIMATE_RATIO = 1.5  # Approximate tokens per character ratio
SAMPLE_ROWS_DEFAULT = 3  # Default number of sample rows to include
CONTEXT_DETAIL_LEVELS = ["minimal", "standard", "comprehensive"]
DEFAULT_CONTEXT_LEVEL = "standard"

# Schema caching settings
SCHEMA_CACHE_TTL = 3600  # 1 hour in seconds
SCHEMA_CACHE_ENABLED = True
SCHEMA_WARM_ON_STARTUP = True

# Enhanced system prompt for SQL generation (Fast Mode)
SQL_FAST_MODE_PROMPT = """You are an expert DuckDB SQL assistant. Generate SQL quickly and efficiently.

## Your Task
Convert natural language queries to optimized DuckDB SQL based on the provided schema.

## SQL Generation Rules
1. Generate ONLY valid DuckDB SQL - no explanations or markdown
2. Use exact table and column names from the schema (case-sensitive)
3. Always include LIMIT clause (default 100 unless specified)
4. Handle NULL values with IS NULL/IS NOT NULL or COALESCE
5. Use ILIKE for case-insensitive text searches
6. Apply appropriate JOINs based on relationships
7. Use DuckDB-specific functions when beneficial
8. Return ONLY the SQL query, nothing else
"""

# Enhanced system prompt for SQL generation (Detailed Mode)
SQL_DETAILED_MODE_PROMPT = """You are a database expert. When I give you a natural language query, provide a detailed analysis following this EXACT format:

QUERY ANALYSIS:

🎯 STRATEGY: Write 2-3 sentences explaining your approach to this query - what method you chose and why this is the best strategy for this specific request.

📊 BUSINESS CONTEXT: Write 2-3 sentences explaining what business question this answers and why the results matter to stakeholders.

🔍 SCHEMA DECISIONS: Write 2-3 sentences explaining which tables/columns you used and why, including any JOIN decisions and data type considerations.

✅ IMPLEMENTATION: Write 2-3 sentences explaining why you chose this specific SQL syntax and any performance considerations or alternatives.

SQL:
```sql
[Your SQL query here]
```

CRITICAL: You MUST provide detailed explanations in ALL sections above. Do not skip any sections. Each section needs 2-3 complete sentences

## SQL Generation Rules
1. Generate valid DuckDB SQL based on the provided schema
2. Use exact table and column names from the schema (case-sensitive)
3. Always include LIMIT clause (default 100 unless specified)
4. Handle NULL values with IS NULL/IS NOT NULL or COALESCE
5. Use ILIKE for case-insensitive text searches
6. Apply appropriate JOINs based on relationships
7. Use DuckDB-specific functions when beneficial
"""

# Legacy system prompt (kept for compatibility)
SQL_SYSTEM_PROMPT = """You are an expert DuckDB SQL assistant with comprehensive schema knowledge.

## Your Task
Convert natural language queries to optimized DuckDB SQL based on the provided schema.

## Schema Context
You have access to detailed schema information including:
- Table structures with column types and constraints
- Sample data for understanding value formats
- Table relationships and foreign keys
- Row counts and cardinality statistics

## SQL Generation Rules
1. Generate ONLY valid DuckDB SQL - no explanations or markdown
2. Use exact table and column names from the schema (case-sensitive)
3. Always include LIMIT clause (default 100 unless specified)
4. Handle NULL values with IS NULL/IS NOT NULL or COALESCE
5. Use ILIKE for case-insensitive text searches
6. Apply appropriate JOINs based on relationships
7. Use DuckDB-specific functions when beneficial:
   - list_* functions for arrays
   - struct_* functions for nested data
   - Date/time functions like date_trunc, date_diff
8. Optimize queries using:
   - Indexes on primary/unique columns
   - Appropriate aggregations (GROUP BY, HAVING)
   - Window functions when needed
9. Validate column references against schema before output
10. Return ONLY the SQL query, nothing else

## Common Query Patterns
- Summaries: Use COUNT, SUM, AVG, MIN, MAX with GROUP BY
- Filtering: Use WHERE with appropriate operators
- Sorting: Use ORDER BY with ASC/DESC
- Joins: Use INNER/LEFT/RIGHT JOIN based on relationships
- Subqueries: Use when aggregating before joining
"""

# Query type detection patterns
QUERY_TYPE_PATTERNS = {
    "aggregation": [
        "sum",
        "total",
        "count",
        "average",
        "mean",
        "max",
        "min",
        "group by",
    ],
    "filtering": ["where", "filter", "only", "exclude", "between", "greater", "less"],
    "joining": ["combine", "merge", "relate", "with", "including", "join"],
    "sorting": ["sort", "order", "rank", "top", "bottom", "first", "last"],
    "time_series": [
        "over time",
        "by date",
        "trend",
        "timeline",
        "daily",
        "monthly",
        "yearly",
    ],
}

# Dynamic prompt templates for different query types
QUERY_TYPE_HINTS = {
    "aggregation": "Focus on GROUP BY and aggregate functions. Consider HAVING for filtered aggregations.",
    "filtering": "Apply WHERE clauses efficiently. Use indexes on filter columns when possible.",
    "joining": "Use appropriate JOIN types. Consider join order for performance.",
    "sorting": "Apply ORDER BY after filtering. Use indexes for sort columns.",
    "time_series": "Use date_trunc for time grouping. Consider window functions for running totals.",
}
