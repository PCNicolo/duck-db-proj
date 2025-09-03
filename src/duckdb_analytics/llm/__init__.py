"""LLM integration module for DuckDB Analytics with performance optimizations."""

from .context_manager import ContextWindowManager
from .enhanced_sql_generator import EnhancedSQLGenerator
from .optimized_context_manager import OptimizedContextManager
from .optimized_schema_extractor import OptimizedSchemaExtractor
from .performance_utils import PerformanceMetrics, TokenBudgetManager
from .query_validator import QueryValidator
from .schema_cache import MultiLevelCache, SchemaCache
from .schema_extractor import SchemaExtractor
from .sql_generator import SQLGenerator

__all__ = [
    # Original components (backward compatibility)
    "SQLGenerator",
    "SchemaExtractor",
    "ContextWindowManager",
    "QueryValidator",
    # Enhanced components
    "EnhancedSQLGenerator",
    "OptimizedSchemaExtractor",
    "OptimizedContextManager",
    # Performance utilities
    "PerformanceMetrics",
    "TokenBudgetManager",
    "SchemaCache",
    "MultiLevelCache",
]
