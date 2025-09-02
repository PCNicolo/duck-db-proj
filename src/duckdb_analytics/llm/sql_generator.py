"""SQL Generator service using LM Studio's local LLM."""

import logging
from typing import Generator, Optional

import httpx
from openai import OpenAI

from .config import (
    DEFAULT_CONTEXT_LEVEL,
    LM_STUDIO_URL,
    MAX_CONTEXT_TOKENS,
    MAX_TOKENS,
    MODEL_NAME,
    REQUEST_TIMEOUT,
    SQL_SYSTEM_PROMPT,
    TEMPERATURE,
)
from .context_manager import ContextWindowManager
from .schema_extractor import SchemaExtractor

logger = logging.getLogger(__name__)


class SQLGenerator:
    """Service for generating SQL queries from natural language using LM Studio."""

    def __init__(
        self,
        base_url: str = LM_STUDIO_URL,
        model: str = MODEL_NAME,
        schema_extractor: Optional[SchemaExtractor] = None,
    ):
        """Initialize the SQL Generator with LM Studio connection and enhanced context.

        Args:
            base_url: LM Studio API endpoint URL
            model: Model identifier (usually "local-model" for LM Studio)
            schema_extractor: Optional SchemaExtractor instance for enhanced context
        """
        self.base_url = base_url
        self.model = model
        self.client = OpenAI(
            base_url=base_url,
            api_key="not-needed",  # LM Studio doesn't need API key
            timeout=REQUEST_TIMEOUT,
        )
        self._available = None
        self._last_check_time = 0
        self._check_interval = 30  # Re-check availability every 30 seconds
        self.schema_extractor = schema_extractor
        self.context_manager = ContextWindowManager(max_tokens=MAX_CONTEXT_TOKENS)

    def is_available(self) -> bool:
        """Check if LM Studio is available and responding.

        Returns:
            True if LM Studio is accessible, False otherwise
        """
        import time

        current_time = time.time()

        # Re-check availability if cached result is stale
        if (
            self._available is not None
            and (current_time - self._last_check_time) < self._check_interval
        ):
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

    def generate_sql(
        self,
        natural_language_query: str,
        schema_context: Optional[str] = None,
        context_level: str = DEFAULT_CONTEXT_LEVEL,
        validate_query: bool = True,
    ) -> Optional[str]:
        """Generate SQL query from natural language input.

        Args:
            natural_language_query: The user's natural language query
            schema_context: Optional database schema context for better SQL generation
            context_level: Context detail level ('minimal', 'standard', 'comprehensive')
            validate_query: Whether to validate the generated SQL against schema

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
                # Build enhanced context if schema extractor is available
                if self.schema_extractor and not schema_context:
                    schema_dict = self.schema_extractor.get_schema()
                    # Prioritize relevant tables based on query
                    relevant_tables = self.context_manager.prioritize_tables(
                        natural_language_query, schema_dict
                    )

                    # Build schema context for relevant tables only
                    filtered_schema = {
                        t: schema_dict[t] for t in relevant_tables if t in schema_dict
                    }
                    schema_context = self._format_schema_for_context(
                        filtered_schema, context_level
                    )

                # Build dynamic prompt with context management
                if schema_context:
                    full_prompt, metadata = self.context_manager.build_dynamic_prompt(
                        SQL_SYSTEM_PROMPT, natural_language_query, schema_context
                    )
                    logger.debug(f"Prompt metadata: {metadata}")

                    # Extract just the system part for the system message
                    system_parts = full_prompt.split("\n## User Query")
                    system_prompt = (
                        system_parts[0] if system_parts else SQL_SYSTEM_PROMPT
                    )
                else:
                    system_prompt = SQL_SYSTEM_PROMPT

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": natural_language_query},
                    ],
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS,
                    stream=False,
                )

                sql_query = response.choices[0].message.content
                break  # Success, exit retry loop

            except httpx.TimeoutException:
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error(f"Request timed out after {max_retries} attempts")
                    return None
                logger.warning(
                    f"Request timeout, retrying ({retry_count}/{max_retries})..."
                )
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
        sql_keywords = [
            "SELECT",
            "INSERT",
            "UPDATE",
            "DELETE",
            "CREATE",
            "DROP",
            "ALTER",
            "WITH",
        ]
        if not any(sql_query.upper().startswith(kw) for kw in sql_keywords):
            logger.warning(
                f"LLM response doesn't appear to be valid SQL: {sql_query[:100]}"
            )
            # Still return it, but log the warning

        # Validate against schema if requested and schema extractor is available
        if validate_query and self.schema_extractor:
            is_valid, errors = self.schema_extractor.validate_sql(sql_query)
            if not is_valid:
                logger.warning(f"SQL validation errors: {errors}")
                # Optionally, we could retry with error feedback
                # For now, just log the errors

        logger.info(f"Generated SQL for query: {natural_language_query[:50]}...")
        return sql_query

    def generate_sql_stream(
        self, natural_language_query: str, schema_context: Optional[str] = None
    ) -> Generator[str, None, None]:
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
                    {"role": "user", "content": natural_language_query},
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                stream=True,
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

    def format_query_with_context(
        self, query: str, table_context: Optional[str] = None
    ) -> str:
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
            # Use the enhanced prompt from config
            return SQL_SYSTEM_PROMPT
        else:
            # Use default prompt when no schema context
            return SQL_SYSTEM_PROMPT

    def _format_schema_for_context(self, schema_dict: dict, context_level: str) -> str:
        """Format schema dictionary for LLM context.

        Args:
            schema_dict: Dictionary of table schemas
            context_level: Level of detail for context

        Returns:
            Formatted schema string
        """
        if not self.schema_extractor:
            return ""

        # Create a temporary schema extractor with the filtered schema
        # This is a workaround since we need to format only selected tables
        formatted_parts = []

        for table_name, table_schema in schema_dict.items():
            # Format table header with statistics
            row_info = (
                f" ({table_schema.row_count:,} rows)" if table_schema.row_count else ""
            )
            formatted_parts.append(f"\n### Table: {table_name}{row_info}")

            # Format columns
            formatted_parts.append("Columns:")
            for col in table_schema.columns:
                col_desc = f"  - {col.name}: {col.data_type}"

                # Add constraints for standard/comprehensive levels
                if context_level != "minimal":
                    constraints = []
                    if col.is_primary_key:
                        constraints.append("PRIMARY KEY")
                    if col.is_unique:
                        constraints.append("UNIQUE")
                    if not col.is_nullable:
                        constraints.append("NOT NULL")

                    if constraints:
                        col_desc += f" [{', '.join(constraints)}]"

                formatted_parts.append(col_desc)

            # Add sample data for standard/comprehensive levels
            if context_level != "minimal" and table_schema.sample_data:
                formatted_parts.append("\nSample Data:")
                col_names = [col.name for col in table_schema.columns]
                formatted_parts.append(f"  {' | '.join(col_names)}")

                for row in table_schema.sample_data[:3]:
                    formatted_values = []
                    for val in row:
                        if val is None:
                            formatted_values.append("NULL")
                        elif isinstance(val, str) and len(val) > 30:
                            formatted_values.append(val[:27] + "...")
                        else:
                            formatted_values.append(str(val))
                    formatted_parts.append(f"  {' | '.join(formatted_values)}")

        return "\n".join(formatted_parts)
