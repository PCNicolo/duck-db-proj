"""Context window management for LLM interactions."""

import logging
from typing import Dict, List, Optional, Tuple

from .config import (
    MAX_CONTEXT_TOKENS,
    QUERY_TYPE_HINTS,
    QUERY_TYPE_PATTERNS,
    SCHEMA_TOKEN_ESTIMATE_RATIO,
)

logger = logging.getLogger(__name__)


class ContextWindowManager:
    """Manages context window for optimal LLM performance."""

    def __init__(self, max_tokens: int = MAX_CONTEXT_TOKENS):
        """
        Initialize the context window manager.

        Args:
            max_tokens: Maximum tokens allowed in context
        """
        self.max_tokens = max_tokens
        self.token_ratio = SCHEMA_TOKEN_ESTIMATE_RATIO

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for given text.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        # Simple estimation: ~1.5 tokens per character for SQL/schema content
        return int(len(text) * self.token_ratio / 4)  # Rough estimate

    def detect_query_type(self, query: str) -> List[str]:
        """
        Detect the type of query from natural language.

        Args:
            query: Natural language query

        Returns:
            List of detected query types
        """
        query_lower = query.lower()
        detected_types = []

        for query_type, patterns in QUERY_TYPE_PATTERNS.items():
            if any(pattern in query_lower for pattern in patterns):
                detected_types.append(query_type)

        return detected_types if detected_types else ["general"]

    def prioritize_tables(
        self, query: str, schema: Dict, max_tables: int = 10
    ) -> List[str]:
        """
        Prioritize tables based on query relevance.

        Args:
            query: Natural language query
            schema: Full database schema
            max_tables: Maximum number of tables to include

        Returns:
            List of prioritized table names
        """
        query_lower = query.lower()
        scored_tables = []

        for table_name, table_schema in schema.items():
            score = 0
            table_lower = table_name.lower()

            # Direct table name mention
            if table_lower in query_lower:
                score += 100

            # Partial match
            elif any(part in query_lower for part in table_lower.split("_")):
                score += 50

            # Column name matches
            for col in table_schema.columns:
                col_lower = col.name.lower()
                if col_lower in query_lower:
                    score += 20
                elif any(part in query_lower for part in col_lower.split("_")):
                    score += 10

            # Boost tables with relationships (likely to be joined)
            if hasattr(table_schema, "foreign_keys") and table_schema.foreign_keys:
                score += 5

            # Consider table size (prefer smaller tables for examples)
            if table_schema.row_count and table_schema.row_count < 10000:
                score += 2

            scored_tables.append((table_name, score))

        # Sort by score and return top tables
        scored_tables.sort(key=lambda x: x[1], reverse=True)

        # Always include high-scoring tables, fill rest up to max_tables
        result = []
        for table_name, score in scored_tables:
            if score > 0 or len(result) < 3:  # Include at least 3 tables
                result.append(table_name)
                if len(result) >= max_tables:
                    break

        return result

    def truncate_context(
        self, context: str, target_tokens: Optional[int] = None
    ) -> str:
        """
        Intelligently truncate context to fit token limit.

        Args:
            context: Full context string
            target_tokens: Target token count (uses max_tokens if not specified)

        Returns:
            Truncated context
        """
        target = target_tokens or self.max_tokens
        current_tokens = self.estimate_tokens(context)

        if current_tokens <= target:
            return context

        # Split context into sections
        lines = context.split("\n")
        essential_lines = []
        optional_lines = []

        for line in lines:
            # Keep headers and structure
            if line.startswith("#") or line.startswith("Table:") or not line.strip():
                essential_lines.append(line)
            # Sample data is optional
            elif "Sample Data:" in line or line.startswith("  ") and "|" in line:
                optional_lines.append(line)
            else:
                essential_lines.append(line)

        # Build truncated context
        truncated = "\n".join(essential_lines)
        current_tokens = self.estimate_tokens(truncated)

        # Add optional lines if space permits
        for line in optional_lines:
            line_tokens = self.estimate_tokens(line)
            if current_tokens + line_tokens < target:
                truncated += "\n" + line
                current_tokens += line_tokens
            else:
                break

        if current_tokens > target:
            # More aggressive truncation needed
            truncated += "\n\n[Context truncated to fit token limit]"

        return truncated

    def build_dynamic_prompt(
        self, base_prompt: str, query: str, schema_context: str
    ) -> Tuple[str, Dict]:
        """
        Build a dynamic prompt based on query type and context.

        Args:
            base_prompt: Base system prompt
            query: User's natural language query
            schema_context: Formatted schema information

        Returns:
            Tuple of (complete prompt, metadata dict)
        """
        # Detect query type
        query_types = self.detect_query_type(query)

        # Add query-specific hints
        hints = []
        for qtype in query_types:
            if qtype in QUERY_TYPE_HINTS:
                hints.append(QUERY_TYPE_HINTS[qtype])

        # Build complete prompt
        prompt_parts = [base_prompt]

        if hints:
            prompt_parts.append("\n## Query-Specific Guidance")
            prompt_parts.extend(hints)

        prompt_parts.append("\n## Database Schema")
        prompt_parts.append(schema_context)

        prompt_parts.append("\n## User Query")
        prompt_parts.append(f"Convert to SQL: {query}")

        full_prompt = "\n".join(prompt_parts)

        # Check token limits
        estimated_tokens = self.estimate_tokens(full_prompt)

        if estimated_tokens > self.max_tokens:
            logger.warning(
                f"Prompt exceeds token limit ({estimated_tokens} > {self.max_tokens}), truncating..."
            )
            # Truncate schema context
            reduced_schema = self.truncate_context(
                schema_context,
                target_tokens=self.max_tokens
                - self.estimate_tokens("\n".join(prompt_parts[:2] + prompt_parts[-2:])),
            )
            prompt_parts[-3] = reduced_schema
            full_prompt = "\n".join(prompt_parts)
            estimated_tokens = self.estimate_tokens(full_prompt)

        metadata = {
            "query_types": query_types,
            "estimated_tokens": estimated_tokens,
            "truncated": estimated_tokens > self.max_tokens,
            "hints_applied": len(hints),
        }

        return full_prompt, metadata

    def compress_schema_context(
        self, schema_context: str, compression_level: str = "standard"
    ) -> str:
        """
        Compress schema context based on level.

        Args:
            schema_context: Full schema context
            compression_level: 'minimal', 'standard', or 'comprehensive'

        Returns:
            Compressed schema context
        """
        if compression_level == "comprehensive":
            return schema_context  # No compression

        lines = schema_context.split("\n")
        compressed = []

        if compression_level == "minimal":
            # Keep only table names and column names/types
            for line in lines:
                if (
                    line.startswith("#")
                    or line.startswith("Table:")
                    or (
                        line.strip().startswith("-")
                        and ":" in line
                        and "Sample" not in line
                    )
                ):
                    # Simplify column descriptions
                    if line.strip().startswith("-"):
                        parts = line.split(":")
                        if len(parts) >= 2:
                            col_name = parts[0].strip("- ")
                            col_type = parts[1].split("[")[0].strip()
                            compressed.append(f"  - {col_name}: {col_type}")
                    else:
                        compressed.append(line)
        else:  # standard
            # Keep everything except sample data
            skip_samples = False
            for line in lines:
                if "Sample Data:" in line:
                    skip_samples = True
                elif line.startswith("Table:") or line.startswith("#"):
                    skip_samples = False
                    compressed.append(line)
                elif not skip_samples:
                    compressed.append(line)

        return "\n".join(compressed)
