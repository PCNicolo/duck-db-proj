"""DuckDB schema extraction and caching for LLM context."""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class TableSchema:
    """Represents schema information for a database table."""
    name: str
    columns: List[Dict[str, str]] = field(default_factory=list)
    row_count: Optional[int] = None
    sample_data: Optional[pd.DataFrame] = None


class SchemaExtractor:
    """Extracts and caches DuckDB schema information for LLM context."""

    def __init__(self, duckdb_conn):
        """
        Initialize the schema extractor.
        
        Args:
            duckdb_conn: DuckDB connection object or DuckDBConnection instance
        """
        self.conn = duckdb_conn
        self._schema_cache: Optional[Dict[str, TableSchema]] = None
        self._raw_schema_df: Optional[pd.DataFrame] = None

    def get_schema(self, force_refresh: bool = False) -> Dict[str, TableSchema]:
        """
        Get cached schema or extract if not cached.
        
        Args:
            force_refresh: Force refresh of schema cache
            
        Returns:
            Dictionary of table names to TableSchema objects
        """
        if not self._schema_cache or force_refresh:
            self._schema_cache = self._extract_schema()
        return self._schema_cache

    def _extract_schema(self) -> Dict[str, TableSchema]:
        """
        Extract schema information from DuckDB.
        
        Returns:
            Dictionary of table names to TableSchema objects
        """
        schema_dict = {}

        try:
            # Query information schema for all tables and columns
            query = """
            SELECT 
                table_name, 
                column_name, 
                data_type,
                is_nullable,
                column_default,
                ordinal_position
            FROM information_schema.columns 
            WHERE table_schema = 'main'
            ORDER BY table_name, ordinal_position
            """

            # Execute query and get results
            if hasattr(self.conn, 'execute'):
                result = self.conn.execute(query)
                self._raw_schema_df = result.fetchdf() if hasattr(result, 'fetchdf') else pd.DataFrame(result.fetchall())
            else:
                # Direct DuckDB connection
                result = self.conn.execute(query)
                self._raw_schema_df = result.df()

            if self._raw_schema_df.empty:
                logger.warning("No tables found in database schema")
                return schema_dict

            # Group by table name
            for table_name in self._raw_schema_df['table_name'].unique():
                table_df = self._raw_schema_df[self._raw_schema_df['table_name'] == table_name]

                # Create TableSchema object
                table_schema = TableSchema(name=table_name)

                # Add column information
                for _, row in table_df.iterrows():
                    column_info = {
                        'name': row['column_name'],
                        'type': row['data_type'],
                        'nullable': row['is_nullable'] == 'YES',
                        'default': row['column_default']
                    }
                    table_schema.columns.append(column_info)

                # Try to get row count (may fail for views)
                try:
                    count_query = f"SELECT COUNT(*) as cnt FROM {table_name}"
                    if hasattr(self.conn, 'execute'):
                        count_result = self.conn.execute(count_query)
                        count_df = count_result.fetchdf() if hasattr(count_result, 'fetchdf') else pd.DataFrame(count_result.fetchall())
                        table_schema.row_count = int(count_df.iloc[0]['cnt']) if not count_df.empty else 0
                    else:
                        count_result = self.conn.execute(count_query).df()
                        table_schema.row_count = int(count_result.iloc[0]['cnt'])
                except Exception as e:
                    logger.debug(f"Could not get row count for {table_name}: {e}")

                schema_dict[table_name] = table_schema

            logger.info(f"Extracted schema for {len(schema_dict)} tables")

        except Exception as e:
            logger.error(f"Failed to extract schema: {e}")
            raise

        return schema_dict

    def format_for_llm(self, include_samples: bool = False, max_tables: int = 50) -> str:
        """
        Format schema information for LLM context.
        
        Args:
            include_samples: Whether to include sample data
            max_tables: Maximum number of tables to include
            
        Returns:
            Formatted string representation of schema
        """
        schema = self.get_schema()

        if not schema:
            return "No tables available in database."

        formatted_parts = []
        table_count = 0

        for table_name, table_schema in schema.items():
            if table_count >= max_tables:
                formatted_parts.append(f"\n... and {len(schema) - max_tables} more tables")
                break

            # Format table header
            row_info = f" ({table_schema.row_count:,} rows)" if table_schema.row_count is not None else ""
            formatted_parts.append(f"\nTable: {table_name}{row_info}")

            # Format columns
            column_strs = []
            for col in table_schema.columns:
                nullable = "" if col.get('nullable', True) else " NOT NULL"
                column_strs.append(f"  - {col['name']} ({col['type']}{nullable})")

            formatted_parts.append("\n".join(column_strs))
            table_count += 1

        return "\n".join(formatted_parts)

    def validate_sql(self, sql_query: str) -> Tuple[bool, List[str]]:
        """
        Validate SQL query against actual schema.
        
        Args:
            sql_query: SQL query to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        schema = self.get_schema()

        # Basic validation - check if query is not empty
        if not sql_query or not sql_query.strip():
            errors.append("SQL query is empty")
            return False, errors

        # Extract table names from query (basic regex approach)
        import re

        # Find table references (this is simplified, doesn't handle all SQL syntax)
        table_pattern = r'\b(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        found_tables = re.findall(table_pattern, sql_query.upper().replace(sql_query, sql_query.upper()))

        # Also check the original case
        found_tables.extend(re.findall(table_pattern, sql_query, re.IGNORECASE))

        # Remove duplicates and clean
        found_tables = list(set([t.strip('`"\'').lower() for t in found_tables]))

        # Check if tables exist
        available_tables = [t.lower() for t in schema.keys()]

        for table in found_tables:
            if table.lower() not in available_tables:
                # Suggest similar table names
                similar = self._find_similar_names(table, available_tables)
                if similar:
                    errors.append(f"Table '{table}' not found. Did you mean: {', '.join(similar[:3])}?")
                else:
                    errors.append(f"Table '{table}' not found. Available tables: {', '.join(list(schema.keys())[:5])}")

        # Try to parse and validate with DuckDB (non-executing)
        try:
            # Use EXPLAIN to validate without executing
            if hasattr(self.conn, 'execute'):
                self.conn.execute(f"EXPLAIN {sql_query}")
            else:
                self.conn.execute(f"EXPLAIN {sql_query}")
        except Exception as e:
            error_msg = str(e)
            # Parse DuckDB error for more specific feedback
            if "Catalog Error" in error_msg:
                # Extract the problematic identifier
                match = re.search(r"Table with name (\w+) does not exist", error_msg)
                if match:
                    table_name = match.group(1)
                    similar = self._find_similar_names(table_name, available_tables)
                    if similar:
                        errors.append(f"Table '{table_name}' does not exist. Similar tables: {', '.join(similar[:3])}")
                    else:
                        errors.append(f"Table '{table_name}' does not exist")
                else:
                    errors.append(f"Schema validation error: {error_msg}")
            elif "Binder Error" in error_msg:
                # Column doesn't exist
                match = re.search(r"Column ['\"]?(\w+)['\"]? (does not exist|not found)", error_msg)
                if match:
                    column_name = match.group(1)
                    errors.append(f"Column '{column_name}' not found. Check column names in schema.")
                else:
                    errors.append(f"Column binding error: {error_msg}")
            else:
                errors.append(f"SQL syntax error: {error_msg}")

        return len(errors) == 0, errors

    def _find_similar_names(self, name: str, available_names: List[str], threshold: float = 0.6) -> List[str]:
        """
        Find similar names using simple character matching.
        
        Args:
            name: Name to match
            available_names: List of available names
            threshold: Similarity threshold (0-1)
            
        Returns:
            List of similar names
        """
        from difflib import SequenceMatcher

        similar = []
        name_lower = name.lower()

        for available in available_names:
            ratio = SequenceMatcher(None, name_lower, available.lower()).ratio()
            if ratio >= threshold:
                similar.append((available, ratio))

        # Sort by similarity and return names only
        similar.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in similar]

    def get_table_columns(self, table_name: str) -> List[str]:
        """
        Get column names for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column names
        """
        schema = self.get_schema()
        table_schema = schema.get(table_name)

        if not table_schema:
            # Try case-insensitive search
            for t_name, t_schema in schema.items():
                if t_name.lower() == table_name.lower():
                    table_schema = t_schema
                    break

        if table_schema:
            return [col['name'] for col in table_schema.columns]
        return []

    def get_sample_data(self, table_name: str, limit: int = 5) -> Optional[pd.DataFrame]:
        """
        Get sample data from a table.
        
        Args:
            table_name: Name of the table
            limit: Number of rows to sample
            
        Returns:
            DataFrame with sample data or None if error
        """
        try:
            query = f"SELECT * FROM {table_name} LIMIT {limit}"
            if hasattr(self.conn, 'execute'):
                result = self.conn.execute(query)
                return result.fetchdf() if hasattr(result, 'fetchdf') else pd.DataFrame(result.fetchall())
            else:
                return self.conn.execute(query).df()
        except Exception as e:
            logger.debug(f"Could not get sample data for {table_name}: {e}")
            return None
