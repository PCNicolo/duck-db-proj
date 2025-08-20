"""Configuration for LM Studio LLM integration."""

# LM Studio connection settings
LM_STUDIO_URL = "http://localhost:1234/v1"
MODEL_NAME = "local-model"  # LM Studio uses "local-model" as identifier

# Request settings
REQUEST_TIMEOUT = 3.0  # 3 second timeout as per requirements
MAX_TOKENS = 500
TEMPERATURE = 0.1  # Low temperature for consistent SQL generation

# System prompt for SQL generation
SQL_SYSTEM_PROMPT = """You are a SQL expert specializing in DuckDB. Convert natural language to DuckDB SQL.
Rules:
1. Only respond with valid SQL queries - no explanations or comments
2. Use DuckDB syntax and functions
3. Always add LIMIT clause for safety (default LIMIT 100 unless specified)
4. Use appropriate aggregate functions when asked for summaries
5. Handle NULL values appropriately
6. For text searches, use ILIKE for case-insensitive matching
7. Return only the SQL query, nothing else"""