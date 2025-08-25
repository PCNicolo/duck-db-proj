"""SQL Generator service using LM Studio's local LLM."""

import logging
from typing import Generator, Optional

import httpx
from openai import OpenAI

from .config import (
    LM_STUDIO_URL,
    MAX_TOKENS,
    MODEL_NAME,
    REQUEST_TIMEOUT,
    SQL_SYSTEM_PROMPT,
    TEMPERATURE,
)

logger = logging.getLogger(__name__)


class SQLGenerator:
    """Service for generating SQL queries from natural language using LM Studio."""

    def __init__(self, base_url: str = LM_STUDIO_URL, model: str = MODEL_NAME):
        """Initialize the SQL Generator with LM Studio connection.
        
        Args:
            base_url: LM Studio API endpoint URL
            model: Model identifier (usually "local-model" for LM Studio)
        """
        import time
        self.base_url = base_url
        self.model = model
        self.client = OpenAI(
            base_url=base_url,
            api_key="not-needed",  # LM Studio doesn't need API key
            timeout=REQUEST_TIMEOUT
        )
        self._available = None
        self._last_check_time = 0
        self._check_interval = 30  # Re-check availability every 30 seconds

    def is_available(self) -> bool:
        """Check if LM Studio is available and responding.
        
        Returns:
            True if LM Studio is accessible, False otherwise
        """
        import time
        current_time = time.time()
        
        # Re-check availability if cached result is stale
        if self._available is not None and (current_time - self._last_check_time) < self._check_interval:
            return self._available

        try:
            # Try to list models to check connectivity
            models = self.client.models.list()
            self._available = True
            self._last_check_time = current_time
            logger.info(f"LM Studio is available at {self.base_url}")
            return True
        except Exception as e:
            logger.warning(f"LM Studio not available: {str(e)}")
            self._available = False
            self._last_check_time = current_time
            return False

    def generate_sql(self, natural_language_query: str, schema_context: Optional[str] = None) -> Optional[str]:
        """Generate SQL query from natural language input.
        
        Args:
            natural_language_query: The user's natural language query
            schema_context: Optional database schema context for better SQL generation
            
        Returns:
            Generated SQL query string or None if generation fails
        """
        if not self.is_available():
            logger.error("LM Studio is not available")
            return None

        max_retries = 2
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Build enhanced system prompt with schema context
                system_prompt = self._build_system_prompt(schema_context)

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": natural_language_query}
                    ],
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS,
                    stream=False
                )

                sql_query = response.choices[0].message.content
                break  # Success, exit retry loop
                
            except httpx.TimeoutException as e:
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error(f"Request timed out after {max_retries} attempts")
                    return None
                logger.warning(f"Request timeout, retrying ({retry_count}/{max_retries})...")
                import time
                time.sleep(0.5 * retry_count)  # Exponential backoff
                continue
            except Exception as e:
                logger.error(f"Error generating SQL: {str(e)}")
                return None

        # Validate response is not empty
        if not sql_query or not sql_query.strip():
            logger.warning("LLM returned empty SQL query")
            return None

        # Basic SQL validation
        sql_query = sql_query.strip()
        sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER', 'WITH']
        if not any(sql_query.upper().startswith(kw) for kw in sql_keywords):
            logger.warning(f"LLM response doesn't appear to be valid SQL: {sql_query[:100]}")
            # Still return it, but log the warning

        logger.info(f"Generated SQL for query: {natural_language_query[:50]}...")
        return sql_query

    def generate_sql_stream(self, natural_language_query: str, schema_context: Optional[str] = None) -> Generator[str, None, None]:
        """Generate SQL query with streaming response for better UX.
        
        Args:
            natural_language_query: The user's natural language query
            schema_context: Optional database schema context for better SQL generation
            
        Yields:
            Chunks of the generated SQL query
        """
        if not self.is_available():
            logger.error("LM Studio is not available")
            yield "Error: LM Studio is not available"
            return

        try:
            # Build enhanced system prompt with schema context
            system_prompt = self._build_system_prompt(schema_context)

            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": natural_language_query}
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

        except httpx.TimeoutException:
            logger.error(f"Request timed out after {REQUEST_TIMEOUT} seconds")
            yield f"\nError: Request timed out after {REQUEST_TIMEOUT} seconds"
        except Exception as e:
            logger.error(f"Error generating SQL: {str(e)}")
            yield f"\nError: {str(e)}"

    def format_query_with_context(self, query: str, table_context: Optional[str] = None) -> str:
        """Format user query with optional table context for better SQL generation.
        
        Args:
            query: User's natural language query
            table_context: Optional context about available tables/columns
            
        Returns:
            Formatted query string with context
        """
        # Sanitize input to prevent prompt injection
        query = query.strip()[:500]  # Limit query length

        if table_context:
            # Sanitize table context as well
            table_context = table_context.strip()[:500]
            return f"Given the following table information:\n{table_context}\n\nConvert this to SQL: {query}"
        return query

    def reset_availability(self):
        """Reset the availability cache to force re-check on next request."""
        self._available = None

    def _build_system_prompt(self, schema_context: Optional[str] = None) -> str:
        """Build enhanced system prompt with optional schema context.
        
        Args:
            schema_context: Optional database schema information
            
        Returns:
            Enhanced system prompt for SQL generation
        """
        if schema_context:
            # Build enhanced prompt with schema information
            enhanced_prompt = f"""You are a SQL expert for DuckDB. 

Available tables and columns in the database:
{schema_context}

Important DuckDB-specific functions:
- DATE_TRUNC('day'/'month'/'year', date_column) for date truncation
- EXTRACT(YEAR/MONTH/DAY FROM date_column) for date parts
- STRING_AGG(column, delimiter) for string concatenation
- LIST_AGG(column) for creating lists
- UNNEST(array_column) for array expansion

Convert the user's natural language query to valid DuckDB SQL using ONLY the tables and columns shown above.
Return ONLY the SQL query without any explanation or markdown formatting.
If the requested data doesn't exist in the schema, politely indicate that in a SQL comment."""
            return enhanced_prompt
        else:
            # Use default prompt when no schema context
            return SQL_SYSTEM_PROMPT
