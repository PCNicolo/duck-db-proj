"""Optimized context window management with intelligent prioritization."""

import logging
import re
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from .config import MAX_CONTEXT_TOKENS, QUERY_TYPE_HINTS, QUERY_TYPE_PATTERNS
from .performance_utils import (
    TokenBudgetManager,
    estimate_tokens_accurate,
    timer_decorator,
)
from .schema_extractor import TableSchema

logger = logging.getLogger(__name__)


class OptimizedContextManager:
    """High-performance context window management with advanced features."""
    
    def __init__(
        self,
        max_tokens: int = MAX_CONTEXT_TOKENS,
        model_type: str = "llama"
    ):
        """
        Initialize optimized context manager.
        
        Args:
            max_tokens: Maximum tokens in context window
            model_type: Type of model for token estimation
        """
        self.max_tokens = max_tokens
        self.model_type = model_type
        self.budget_manager = TokenBudgetManager(max_tokens)
        
        # Pre-compiled patterns for performance
        self._compiled_patterns = self._compile_patterns()
        
        # Cache for tokenized content
        self._token_cache: Dict[str, int] = {}
        
        # Inverted index for fast table/column lookup
        self._table_index: Dict[str, Set[str]] = defaultdict(set)
        self._column_index: Dict[str, Set[str]] = defaultdict(set)
    
    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Pre-compile regex patterns for performance."""
        compiled = {}
        
        for query_type, patterns in QUERY_TYPE_PATTERNS.items():
            compiled[query_type] = [
                re.compile(r'\b' + re.escape(pattern) + r'\b', re.IGNORECASE)
                for pattern in patterns
            ]
        
        return compiled
    
    def build_indexes(self, schema: Dict[str, TableSchema]):
        """Build inverted indexes for fast lookup."""
        self._table_index.clear()
        self._column_index.clear()
        
        for table_name, table_schema in schema.items():
            # Index table name parts
            for part in table_name.lower().split('_'):
                self._table_index[part].add(table_name)
            
            # Index column names
            for col in table_schema.columns:
                for part in col.name.lower().split('_'):
                    self._column_index[part].add(f"{table_name}.{col.name}")
    
    @timer_decorator
    def estimate_tokens(self, text: str, use_cache: bool = True) -> int:
        """
        Estimate tokens with caching and accurate model-specific counting.
        
        Args:
            text: Text to estimate
            use_cache: Whether to use cached estimates
            
        Returns:
            Estimated token count
        """
        if use_cache and text in self._token_cache:
            return self._token_cache[text]
        
        tokens = estimate_tokens_accurate(text, self.model_type)
        
        if use_cache:
            self._token_cache[text] = tokens
        
        return tokens
    
    @timer_decorator
    def detect_query_intent(self, query: str) -> Dict[str, float]:
        """
        Advanced query intent detection with confidence scores.
        
        Args:
            query: Natural language query
            
        Returns:
            Dictionary of query types with confidence scores
        """
        query_lower = query.lower()
        intent_scores = defaultdict(float)
        
        # Check compiled patterns
        for query_type, patterns in self._compiled_patterns.items():
            matches = sum(1 for pattern in patterns if pattern.search(query_lower))
            if matches:
                intent_scores[query_type] = matches / len(patterns)
        
        # Additional heuristics
        if "?" in query:
            intent_scores["question"] += 0.2
        
        if any(word in query_lower for word in ["all", "every", "each"]):
            intent_scores["comprehensive"] += 0.3
        
        if any(word in query_lower for word in ["top", "best", "worst", "most", "least"]):
            intent_scores["ranking"] += 0.4
        
        # Normalize scores
        total = sum(intent_scores.values())
        if total > 0:
            for key in intent_scores:
                intent_scores[key] /= total
        
        return dict(intent_scores) if intent_scores else {"general": 1.0}
    
    @timer_decorator
    def prioritize_tables_advanced(
        self,
        query: str,
        schema: Dict[str, TableSchema],
        max_tables: int = 10,
        intent: Optional[Dict[str, float]] = None
    ) -> List[Tuple[str, float]]:
        """
        Advanced table prioritization with multiple scoring factors.
        
        Args:
            query: Natural language query
            schema: Database schema
            max_tables: Maximum tables to include
            intent: Query intent scores
            
        Returns:
            List of (table_name, score) tuples
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        table_scores = defaultdict(float)
        
        for table_name, table_schema in schema.items():
            score = 0.0
            
            # Direct table name match
            table_lower = table_name.lower()
            if table_lower in query_lower:
                score += 100
            
            # Table name word overlap
            table_words = set(table_lower.split('_'))
            word_overlap = len(query_words & table_words)
            score += word_overlap * 20
            
            # Use inverted index for fast lookup
            for word in query_words:
                if table_name in self._table_index.get(word, set()):
                    score += 15
            
            # Column matches using index
            col_matches = 0
            for col in table_schema.columns:
                col_lower = col.name.lower()
                if col_lower in query_lower:
                    score += 25
                    col_matches += 1
                
                # Check column index
                for word in query_words:
                    if f"{table_name}.{col.name}" in self._column_index.get(word, set()):
                        score += 10
                        col_matches += 1
            
            # Boost based on column diversity
            if col_matches > 0:
                score += min(col_matches * 5, 25)
            
            # Consider relationships
            if table_schema.foreign_keys:
                score += len(table_schema.foreign_keys) * 3
            
            # Intent-based scoring
            if intent:
                if intent.get("aggregation", 0) > 0.3 and table_schema.row_count:
                    # Prefer larger tables for aggregation
                    if table_schema.row_count > 1000:
                        score += 10
                
                if intent.get("joining", 0) > 0.3 and table_schema.foreign_keys:
                    # Boost tables with relationships for joins
                    score += 15
            
            # Size penalty for very large tables without specific mention
            if table_schema.row_count and table_schema.row_count > 1000000:
                if table_lower not in query_lower:
                    score *= 0.7
            
            table_scores[table_name] = score
        
        # Sort and filter
        sorted_tables = sorted(
            table_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Include high-scoring tables and minimum set
        result = []
        for table_name, score in sorted_tables:
            if score > 10 or len(result) < 3:  # Include at least 3 tables
                result.append((table_name, score))
                if len(result) >= max_tables:
                    break
        
        return result
    
    @timer_decorator
    def build_optimized_context(
        self,
        query: str,
        schema: Dict[str, TableSchema],
        base_prompt: str,
        context_level: str = "standard"
    ) -> Tuple[str, Dict]:
        """
        Build optimized context with token budget management.
        
        Args:
            query: User query
            schema: Database schema
            base_prompt: Base system prompt
            context_level: Detail level
            
        Returns:
            Tuple of (prompt, metadata)
        """
        # Detect query intent
        intent = self.detect_query_intent(query)
        
        # Get token budgets
        budgets = {
            "system": self.budget_manager.get_budget("system_prompt"),
            "query": self.budget_manager.get_budget("query"),
            "schema": self.budget_manager.get_budget("schema"),
            "hints": self.budget_manager.get_budget("examples")
        }
        
        # Build prompt parts
        prompt_parts = []
        metadata = {
            "intent": intent,
            "budgets": budgets,
            "tokens_used": {}
        }
        
        # Add base prompt
        base_tokens = self.estimate_tokens(base_prompt)
        if base_tokens <= budgets["system"]:
            prompt_parts.append(base_prompt)
            metadata["tokens_used"]["system"] = base_tokens
        else:
            # Truncate base prompt if needed
            truncated = self._truncate_to_budget(base_prompt, budgets["system"])
            prompt_parts.append(truncated)
            metadata["tokens_used"]["system"] = budgets["system"]
        
        # Add query-specific hints based on intent
        hints = self._get_intent_hints(intent)
        if hints:
            hint_tokens = self.estimate_tokens(hints)
            if hint_tokens <= budgets["hints"]:
                prompt_parts.append("\n## Query Guidance")
                prompt_parts.append(hints)
                metadata["tokens_used"]["hints"] = hint_tokens
        
        # Prioritize and add schema
        prioritized_tables = self.prioritize_tables_advanced(
            query, schema, max_tables=15, intent=intent
        )
        
        schema_context = self._build_schema_context(
            schema,
            prioritized_tables,
            context_level,
            budgets["schema"]
        )
        
        prompt_parts.append("\n## Database Schema")
        prompt_parts.append(schema_context)
        metadata["tokens_used"]["schema"] = self.estimate_tokens(schema_context)
        
        # Add user query
        query_section = f"\n## User Query\nConvert to SQL: {query}"
        prompt_parts.append(query_section)
        metadata["tokens_used"]["query"] = self.estimate_tokens(query_section)
        
        # Combine and validate
        full_prompt = "\n".join(prompt_parts)
        total_tokens = sum(metadata["tokens_used"].values())
        
        metadata["total_tokens"] = total_tokens
        metadata["within_budget"] = total_tokens <= self.max_tokens
        metadata["tables_included"] = len(prioritized_tables)
        
        return full_prompt, metadata
    
    def _get_intent_hints(self, intent: Dict[str, float]) -> str:
        """Get hints based on query intent."""
        hints = []
        
        for query_type, confidence in sorted(
            intent.items(),
            key=lambda x: x[1],
            reverse=True
        )[:2]:  # Top 2 intents
            if confidence > 0.3 and query_type in QUERY_TYPE_HINTS:
                hints.append(f"- {QUERY_TYPE_HINTS[query_type]}")
        
        return "\n".join(hints) if hints else ""
    
    def _build_schema_context(
        self,
        schema: Dict[str, TableSchema],
        prioritized_tables: List[Tuple[str, float]],
        context_level: str,
        token_budget: int
    ) -> str:
        """Build schema context within token budget."""
        context_parts = []
        current_tokens = 0
        
        for table_name, score in prioritized_tables:
            if table_name not in schema:
                continue
            
            table_schema = schema[table_name]
            
            # Build table section
            table_section = self._format_table_schema(
                table_schema,
                context_level,
                include_samples=(score > 50)  # Include samples for high-scoring tables
            )
            
            section_tokens = self.estimate_tokens(table_section)
            
            # Check if adding this table exceeds budget
            if current_tokens + section_tokens > token_budget:
                # Try with minimal format
                minimal_section = self._format_table_schema(
                    table_schema,
                    "minimal",
                    include_samples=False
                )
                minimal_tokens = self.estimate_tokens(minimal_section)
                
                if current_tokens + minimal_tokens <= token_budget:
                    context_parts.append(minimal_section)
                    current_tokens += minimal_tokens
                else:
                    # Stop adding tables
                    break
            else:
                context_parts.append(table_section)
                current_tokens += section_tokens
        
        return "\n".join(context_parts)
    
    def _format_table_schema(
        self,
        table_schema: TableSchema,
        context_level: str,
        include_samples: bool = True
    ) -> str:
        """Format individual table schema."""
        parts = []
        
        # Table header
        row_info = f" ({table_schema.row_count:,} rows)" if table_schema.row_count else ""
        parts.append(f"\n### Table: {table_schema.name}{row_info}")
        
        # Columns
        parts.append("Columns:")
        
        for col in table_schema.columns:
            col_desc = f"  - {col.name}: {col.data_type}"
            
            if context_level != "minimal":
                constraints = []
                if col.is_primary_key:
                    constraints.append("PK")
                if col.is_unique:
                    constraints.append("UNIQUE")
                if not col.is_nullable:
                    constraints.append("NOT NULL")
                
                if constraints:
                    col_desc += f" [{', '.join(constraints)}]"
            
            parts.append(col_desc)
        
        # Relationships
        if context_level != "minimal" and table_schema.foreign_keys:
            parts.append("\nRelationships:")
            for fk in table_schema.foreign_keys[:3]:  # Limit to 3
                parts.append(f"  - {fk}")
        
        # Sample data
        if include_samples and table_schema.sample_data and context_level != "minimal":
            parts.append("\nSample Data:")
            col_names = [col.name for col in table_schema.columns]
            parts.append(f"  {' | '.join(col_names[:5])}")  # Limit columns
            
            for row in table_schema.sample_data[:2]:  # Limit rows
                formatted_values = []
                for val in row[:5]:  # Limit columns
                    if val is None:
                        formatted_values.append("NULL")
                    elif isinstance(val, str) and len(val) > 20:
                        formatted_values.append(val[:17] + "...")
                    else:
                        formatted_values.append(str(val))
                parts.append(f"  {' | '.join(formatted_values)}")
        
        return "\n".join(parts)
    
    def _truncate_to_budget(self, text: str, token_budget: int) -> str:
        """Truncate text to fit within token budget."""
        current_tokens = self.estimate_tokens(text)
        
        if current_tokens <= token_budget:
            return text
        
        # Binary search for optimal truncation point
        lines = text.split('\n')
        left, right = 0, len(lines)
        
        while left < right:
            mid = (left + right + 1) // 2
            truncated = '\n'.join(lines[:mid])
            if self.estimate_tokens(truncated) <= token_budget:
                left = mid
            else:
                right = mid - 1
        
        return '\n'.join(lines[:left]) + "\n[Truncated to fit token budget]"
    
    def clear_cache(self):
        """Clear all caches."""
        self._token_cache.clear()
        self._table_index.clear()
        self._column_index.clear()