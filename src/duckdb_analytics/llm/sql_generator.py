"""SQL Generator service using LM Studio's local LLM."""

import logging
from typing import Optional, Generator
from openai import OpenAI
import httpx

from .config import (
    LM_STUDIO_URL,
    MODEL_NAME,
    REQUEST_TIMEOUT,
    MAX_TOKENS,
    TEMPERATURE,
    SQL_SYSTEM_PROMPT
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
        self.base_url = base_url
        self.model = model
        self.client = OpenAI(
            base_url=base_url,
            api_key="not-needed",  # LM Studio doesn't need API key
            timeout=REQUEST_TIMEOUT
        )
        self._available = None
    
    def is_available(self) -> bool:
        """Check if LM Studio is available and responding.
        
        Returns:
            True if LM Studio is accessible, False otherwise
        """
        if self._available is not None:
            return self._available
            
        try:
            # Try to list models to check connectivity
            models = self.client.models.list()
            self._available = True
            logger.info(f"LM Studio is available at {self.base_url}")
            return True
        except Exception as e:
            logger.warning(f"LM Studio not available: {str(e)}")
            self._available = False
            return False
    
    def generate_sql(self, natural_language_query: str) -> Optional[str]:
        """Generate SQL query from natural language input.
        
        Args:
            natural_language_query: The user's natural language query
            
        Returns:
            Generated SQL query string or None if generation fails
        """
        if not self.is_available():
            logger.error("LM Studio is not available")
            return None
            
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SQL_SYSTEM_PROMPT},
                    {"role": "user", "content": natural_language_query}
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                stream=False
            )
            
            sql_query = response.choices[0].message.content
            
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
            
        except httpx.TimeoutException:
            logger.error(f"Request timed out after {REQUEST_TIMEOUT} seconds")
            return None
        except Exception as e:
            logger.error(f"Error generating SQL: {str(e)}")
            return None
    
    def generate_sql_stream(self, natural_language_query: str) -> Generator[str, None, None]:
        """Generate SQL query with streaming response for better UX.
        
        Args:
            natural_language_query: The user's natural language query
            
        Yields:
            Chunks of the generated SQL query
        """
        if not self.is_available():
            logger.error("LM Studio is not available")
            yield "Error: LM Studio is not available"
            return
            
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SQL_SYSTEM_PROMPT},
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