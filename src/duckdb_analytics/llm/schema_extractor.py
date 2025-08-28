"""DuckDB schema extraction and caching for LLM context."""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ColumnInfo:
    """Detailed column information."""
    name: str
    data_type: str
    is_nullable: bool = True
    is_primary_key: bool = False
    is_unique: bool = False
    default_value: Optional[str] = None
    column_position: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'type': self.data_type,
            'nullable': self.is_nullable,
            'primary_key': self.is_primary_key,
            'unique': self.is_unique,
            'default': self.default_value,
            'position': self.column_position
        }


@dataclass
class ForeignKeyRelation:
    """Foreign key relationship information."""
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    constraint_name: Optional[str] = None
    
    def __str__(self) -> str:
        return f"{self.from_table}.{self.from_column} -> {self.to_table}.{self.to_column}"


@dataclass
class TableSchema:
    """Enhanced schema information for a database table."""
    name: str
    columns: List[ColumnInfo] = field(default_factory=list)
    row_count: Optional[int] = None
    sample_data: Optional[List[List[Any]]] = None
    foreign_keys: List[ForeignKeyRelation] = field(default_factory=list)
    indexes: List[Dict[str, Any]] = field(default_factory=list)
    cardinality_stats: Dict[str, int] = field(default_factory=dict)


class SchemaExtractor:
    """Extracts and caches DuckDB schema information for LLM context."""

    def __init__(self, duckdb_conn, cache_ttl: int = 3600, sample_rows: int = 3):
        """
        Initialize the enhanced schema extractor.
        
        Args:
            duckdb_conn: DuckDB connection object or DuckDBConnection instance
            cache_ttl: Cache time-to-live in seconds (default: 1 hour)
            sample_rows: Number of sample rows to extract (default: 3)
        """
        self.conn = duckdb_conn
        self._schema_cache: Optional[Dict[str, TableSchema]] = None
        self._cache_timestamp: Optional[float] = None
        self._cache_key: Optional[str] = None
        self.cache_ttl = cache_ttl
        self.sample_rows = sample_rows
        self._raw_schema_df: Optional[pd.DataFrame] = None

    def get_schema(self, force_refresh: bool = False) -> Dict[str, TableSchema]:
        """
        Get cached schema or extract if not cached.
        
        Args:
            force_refresh: Force refresh of schema cache
            
        Returns:
            Dictionary of table names to TableSchema objects
        """
        # Check if cache is valid
        if not force_refresh and self._is_cache_valid():
            logger.debug("Using cached schema")
            return self._schema_cache
            
        # Extract fresh schema
        logger.info("Extracting fresh schema")
        self._schema_cache = self._extract_schema()
        self._cache_timestamp = time.time()
        self._update_cache_key()
        return self._schema_cache
    
    def _is_cache_valid(self) -> bool:
        """Check if the schema cache is still valid."""
        if not self._schema_cache or not self._cache_timestamp:
            return False
            
        # Check TTL
        if time.time() - self._cache_timestamp > self.cache_ttl:
            logger.debug("Cache expired based on TTL")
            return False
            
        # Check if tables have changed (basic check)
        try:
            current_tables = self._get_table_list()
            cached_tables = set(self._schema_cache.keys())
            if set(current_tables) != cached_tables:
                logger.debug("Table list changed, invalidating cache")
                return False
        except Exception as e:
            logger.debug(f"Error checking table list: {e}")
            return False
            
        return True
    
    def _get_table_list(self) -> List[str]:
        """Get list of tables in the database."""
        query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        if hasattr(self.conn, 'execute'):
            result = self.conn.execute(query)
            df = result.fetchdf() if hasattr(result, 'fetchdf') else pd.DataFrame(result.fetchall())
        else:
            df = self.conn.execute(query).df()
        return df['table_name'].tolist() if not df.empty else []
    
    def _update_cache_key(self):
        """Update the cache key based on current schema."""
        if not self._schema_cache:
            self._cache_key = None
            return
            
        # Create a hash of table names and their column counts
        cache_data = {
            table: len(schema.columns) 
            for table, schema in self._schema_cache.items()
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        self._cache_key = hashlib.md5(cache_str.encode()).hexdigest()

    def _extract_schema(self) -> Dict[str, TableSchema]:
        """
        Extract schema information from DuckDB.
        
        Returns:
            Dictionary of table names to TableSchema objects
        """
        schema_dict = {}

        try:
            # Enhanced query with more metadata
            # Note: Simplified query due to DuckDB constraint metadata limitations
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

                # Add enhanced column information
                for _, row in table_df.iterrows():
                    # Check if column is a primary key (simple heuristic for now)
                    is_pk = 'id' in row['column_name'].lower() and row['ordinal_position'] == 1
                    is_unique = 'email' in row['column_name'].lower() or is_pk
                    
                    column_info = ColumnInfo(
                        name=row['column_name'],
                        data_type=row['data_type'],
                        is_nullable=row['is_nullable'] == 'YES',
                        is_primary_key=is_pk,
                        is_unique=is_unique,
                        default_value=row['column_default'],
                        column_position=int(row['ordinal_position'])
                    )
                    table_schema.columns.append(column_info)

                # Get table statistics and sample data
                try:
                    # Row count
                    count_query = f"SELECT COUNT(*) as cnt FROM {table_name}"
                    if hasattr(self.conn, 'execute'):
                        count_result = self.conn.execute(count_query)
                        count_df = count_result.fetchdf() if hasattr(count_result, 'fetchdf') else pd.DataFrame(count_result.fetchall())
                        table_schema.row_count = int(count_df.iloc[0]['cnt']) if not count_df.empty else 0
                    else:
                        count_result = self.conn.execute(count_query).df()
                        table_schema.row_count = int(count_result.iloc[0]['cnt'])
                    
                    # Sample data (if table has rows)
                    if table_schema.row_count and table_schema.row_count > 0:
                        sample_query = f"SELECT * FROM {table_name} LIMIT {self.sample_rows}"
                        if hasattr(self.conn, 'execute'):
                            sample_result = self.conn.execute(sample_query)
                            sample_df = sample_result.fetchdf() if hasattr(sample_result, 'fetchdf') else pd.DataFrame(sample_result.fetchall())
                        else:
                            sample_df = self.conn.execute(sample_query).df()
                        
                        if not sample_df.empty:
                            # Convert to list of lists for easier serialization
                            table_schema.sample_data = sample_df.values.tolist()
                    
                    # Get cardinality statistics for key columns
                    for col in table_schema.columns:
                        if col.is_primary_key or col.is_unique or 'id' in col.name.lower():
                            try:
                                card_query = f"SELECT COUNT(DISTINCT {col.name}) as card FROM {table_name}"
                                if hasattr(self.conn, 'execute'):
                                    card_result = self.conn.execute(card_query)
                                    card_df = card_result.fetchdf() if hasattr(card_result, 'fetchdf') else pd.DataFrame(card_result.fetchall())
                                    if not card_df.empty:
                                        table_schema.cardinality_stats[col.name] = int(card_df.iloc[0]['card'])
                                else:
                                    card_df = self.conn.execute(card_query).df()
                                    if not card_df.empty:
                                        table_schema.cardinality_stats[col.name] = int(card_df.iloc[0]['card'])
                            except Exception as e:
                                logger.debug(f"Could not get cardinality for {table_name}.{col.name}: {e}")
                                
                except Exception as e:
                    logger.debug(f"Could not get statistics for {table_name}: {e}")
                
                # Try to extract foreign key relationships (simplified for now)
                # Note: DuckDB's constraint metadata API is limited, using heuristics
                try:
                    # Common foreign key patterns
                    for col in table_schema.columns:
                        if col.name.endswith('_id') and col.name != 'id':
                            # This looks like a foreign key
                            ref_table = col.name[:-3]  # Remove '_id' suffix
                            if ref_table + 's' in schema_dict:  # Check plural form
                                ref_table = ref_table + 's'
                            
                            fk = ForeignKeyRelation(
                                from_table=table_name,
                                from_column=col.name,
                                to_table=ref_table,
                                to_column='id'
                            )
                            table_schema.foreign_keys.append(fk)
                            logger.debug(f"Inferred FK: {fk}")
                    
                except Exception as e:
                    logger.debug(f"Could not infer foreign keys for {table_name}: {e}")

                schema_dict[table_name] = table_schema

            logger.info(f"Extracted schema for {len(schema_dict)} tables")

        except Exception as e:
            logger.error(f"Failed to extract schema: {e}")
            raise

        return schema_dict

    def format_for_llm(self, include_samples: bool = True, max_tables: int = 50, 
                       context_level: str = 'standard') -> str:
        """
        Format enhanced schema information for LLM context.
        
        Args:
            include_samples: Whether to include sample data
            max_tables: Maximum number of tables to include
            context_level: 'minimal', 'standard', or 'comprehensive'
            
        Returns:
            Formatted string representation of schema
        """
        schema = self.get_schema()

        if not schema:
            return "No tables available in database."

        formatted_parts = ["## Database Schema\n"]
        table_count = 0

        for table_name, table_schema in schema.items():
            if table_count >= max_tables:
                formatted_parts.append(f"\n... and {len(schema) - max_tables} more tables")
                break

            # Format table header with statistics
            row_info = f" ({table_schema.row_count:,} rows)" if table_schema.row_count is not None else ""
            formatted_parts.append(f"\n### Table: {table_name}{row_info}")

            # Format columns with enhanced information
            formatted_parts.append("Columns:")
            for col in table_schema.columns:
                # Build column description
                col_desc = f"  - {col.name}: {col.data_type}"
                
                # Add constraints
                constraints = []
                if col.is_primary_key:
                    constraints.append("PRIMARY KEY")
                if col.is_unique:
                    constraints.append("UNIQUE")
                if not col.is_nullable:
                    constraints.append("NOT NULL")
                if col.default_value:
                    constraints.append(f"DEFAULT {col.default_value}")
                
                if constraints:
                    col_desc += f" [{', '.join(constraints)}]"
                
                # Add cardinality info if available
                if col.name in table_schema.cardinality_stats and context_level == 'comprehensive':
                    card = table_schema.cardinality_stats[col.name]
                    col_desc += f" (cardinality: {card:,})"
                
                formatted_parts.append(col_desc)
            
            # Add foreign key relationships if available
            if table_schema.foreign_keys and context_level in ['standard', 'comprehensive']:
                formatted_parts.append("\nRelationships:")
                for fk in table_schema.foreign_keys:
                    formatted_parts.append(f"  - {fk}")
            
            # Add sample data if requested
            if include_samples and table_schema.sample_data and context_level != 'minimal':
                formatted_parts.append("\nSample Data:")
                # Get column names
                col_names = [col.name for col in table_schema.columns]
                formatted_parts.append(f"  {' | '.join(col_names)}")
                formatted_parts.append(f"  {'-' * (len(' | '.join(col_names)))}")
                
                for row in table_schema.sample_data[:self.sample_rows]:
                    # Format row values, handling None and truncating long strings
                    formatted_values = []
                    for val in row:
                        if val is None:
                            formatted_values.append('NULL')
                        elif isinstance(val, str) and len(val) > 50:
                            formatted_values.append(val[:47] + '...')
                        else:
                            formatted_values.append(str(val))
                    formatted_parts.append(f"  {' | '.join(formatted_values)}")
            
            table_count += 1

        # Add query hints if comprehensive
        if context_level == 'comprehensive':
            formatted_parts.append("\n## Query Guidelines:")
            formatted_parts.append("- Use appropriate JOINs based on relationships")
            formatted_parts.append("- Consider NULL values in WHERE clauses")
            formatted_parts.append("- Use indexes on primary/unique columns for performance")
            formatted_parts.append("- Apply LIMIT clauses for safety")

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
            return [col.name for col in table_schema.columns]
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
    
    def invalidate_cache(self):
        """Manually invalidate the schema cache."""
        self._schema_cache = None
        self._cache_timestamp = None
        self._cache_key = None
        logger.info("Schema cache invalidated")
    
    def warm_cache(self):
        """Warm the cache by pre-loading schema."""
        logger.info("Warming schema cache...")
        self.get_schema(force_refresh=True)
        logger.info(f"Schema cache warmed with {len(self._schema_cache)} tables")
