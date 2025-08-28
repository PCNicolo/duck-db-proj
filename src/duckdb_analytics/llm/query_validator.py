"""SQL query validation and error correction suggestions."""

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class QueryValidator:
    """Validates generated SQL queries and provides correction suggestions."""
    
    def __init__(self, schema_extractor):
        """
        Initialize the query validator.
        
        Args:
            schema_extractor: SchemaExtractor instance for schema validation
        """
        self.schema_extractor = schema_extractor
        self.common_mistakes = {
            'missing_limit': {
                'pattern': r'^SELECT\s+.*(?<!LIMIT\s+\d+)$',
                'suggestion': 'Add LIMIT clause for safety',
                'fix': lambda sql: f"{sql} LIMIT 100"
            },
            'wrong_date_function': {
                'pattern': r'DATE_FORMAT|STR_TO_DATE|TO_DATE',
                'suggestion': 'Use DuckDB date functions: DATE_TRUNC, STRFTIME',
                'fix': None
            },
            'wrong_string_concat': {
                'pattern': r'CONCAT\s*\(',
                'suggestion': 'Use || operator or STRING_AGG for concatenation',
                'fix': lambda sql: sql.replace('CONCAT(', 'STRING_AGG(')
            }
        }
    
    def validate_and_correct(self, sql_query: str) -> Tuple[str, List[str], List[str]]:
        """
        Validate SQL query and suggest corrections.
        
        Args:
            sql_query: SQL query to validate
            
        Returns:
            Tuple of (corrected_query, warnings, errors)
        """
        warnings = []
        errors = []
        corrected_query = sql_query.strip()
        
        # Check for common mistakes
        for mistake_name, mistake_config in self.common_mistakes.items():
            if re.search(mistake_config['pattern'], corrected_query, re.IGNORECASE):
                warnings.append(mistake_config['suggestion'])
                if mistake_config['fix']:
                    corrected_query = mistake_config['fix'](corrected_query)
        
        # Validate against schema
        is_valid, schema_errors = self.schema_extractor.validate_sql(corrected_query)
        if not is_valid:
            errors.extend(schema_errors)
        
        # Check for missing LIMIT clause on SELECT queries
        if corrected_query.upper().startswith('SELECT') and 'LIMIT' not in corrected_query.upper():
            warnings.append("Consider adding LIMIT clause for safety")
            corrected_query += " LIMIT 100"
        
        # Check for potential performance issues
        if self._has_performance_issues(corrected_query):
            warnings.append("Query may have performance implications on large datasets")
        
        return corrected_query, warnings, errors
    
    def _has_performance_issues(self, sql_query: str) -> bool:
        """
        Check if query might have performance issues.
        
        Args:
            sql_query: SQL query to check
            
        Returns:
            True if potential performance issues detected
        """
        sql_upper = sql_query.upper()
        
        # Check for cartesian products (JOIN without ON clause)
        if 'JOIN' in sql_upper and 'ON' not in sql_upper:
            return True
        
        # Check for SELECT * on large tables
        if 'SELECT *' in sql_upper and 'LIMIT' not in sql_upper:
            return True
        
        # Check for multiple nested subqueries
        if sql_upper.count('SELECT') > 3:
            return True
        
        return False
    
    def suggest_query_improvements(self, sql_query: str, natural_language: str) -> List[str]:
        """
        Suggest improvements for the generated SQL query.
        
        Args:
            sql_query: Generated SQL query
            natural_language: Original natural language query
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        sql_upper = sql_query.upper()
        nl_lower = natural_language.lower()
        
        # Suggest aggregations if keywords present
        if any(word in nl_lower for word in ['average', 'sum', 'total', 'count']):
            if 'GROUP BY' not in sql_upper:
                suggestions.append("Consider using GROUP BY for aggregations")
        
        # Suggest date functions if date-related
        if any(word in nl_lower for word in ['daily', 'monthly', 'yearly', 'date', 'time']):
            if 'DATE_TRUNC' not in sql_upper:
                suggestions.append("Consider using DATE_TRUNC for date grouping")
        
        # Suggest ordering if top/bottom mentioned
        if any(word in nl_lower for word in ['top', 'bottom', 'highest', 'lowest', 'most', 'least']):
            if 'ORDER BY' not in sql_upper:
                suggestions.append("Consider adding ORDER BY for sorting")
        
        # Suggest DISTINCT if unique mentioned
        if 'unique' in nl_lower or 'distinct' in nl_lower:
            if 'DISTINCT' not in sql_upper:
                suggestions.append("Consider using DISTINCT for unique values")
        
        return suggestions
    
    def log_query_execution(self, query: str, success: bool, execution_time: Optional[float] = None,
                           error_message: Optional[str] = None):
        """
        Log query execution for analysis and improvement.
        
        Args:
            query: Executed SQL query
            success: Whether execution was successful
            execution_time: Query execution time in seconds
            error_message: Error message if execution failed
        """
        log_entry = {
            'query': query[:500],  # Truncate long queries
            'success': success,
            'execution_time': execution_time,
            'error': error_message
        }
        
        if success:
            logger.info(f"Query executed successfully in {execution_time:.3f}s")
        else:
            logger.error(f"Query failed: {error_message}")
        
        # This could be extended to save to a file or database for analysis
        # For now, just log it
        logger.debug(f"Query log: {log_entry}")