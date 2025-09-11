"""Optimized schema extraction with batch queries and parallel processing."""

import concurrent.futures
import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from .performance_utils import (
    PerformanceMetrics,
    calculate_content_hash,
    timer_decorator,
)
from .schema_cache import SchemaCache
from .schema_extractor import ColumnInfo, ForeignKeyRelation, TableSchema

logger = logging.getLogger(__name__)


class OptimizedSchemaExtractor:
    """High-performance schema extraction with advanced optimizations."""
    
    def __init__(
        self,
        duckdb_conn,
        cache: Optional[SchemaCache] = None,
        sample_rows: int = 3,
        max_workers: int = 4,
        batch_size: int = 100
    ):
        """
        Initialize optimized schema extractor.
        
        Args:
            duckdb_conn: DuckDB connection
            cache: Schema cache instance
            sample_rows: Number of sample rows to extract
            max_workers: Maximum worker threads for parallel operations
        """
        self.conn = duckdb_conn
        self.cache = cache or SchemaCache()
        self.sample_rows = sample_rows
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.metrics = PerformanceMetrics()
        
        # Pre-compiled queries for performance
        self._queries = self._compile_queries()
        
        # Connection pool for parallel operations
        self._conn_pool = []
    
    def _compile_queries(self) -> Dict[str, str]:
        """Pre-compile optimized queries."""
        return {
            # Single CTE query to get all metadata at once - optimized with better row counting
            "full_metadata": """
                WITH table_info AS (
                    SELECT 
                        c.table_name,
                        c.column_name,
                        c.data_type,
                        c.is_nullable,
                        c.column_default,
                        c.ordinal_position,
                        t.estimated_row_count
                    FROM information_schema.columns c
                    LEFT JOIN (
                        SELECT 
                            table_name,
                            -- Use COUNT(*) with LIMIT for faster estimation
                            CASE 
                                WHEN COUNT(*) < 10000 THEN COUNT(*)
                                ELSE 10000  -- Cap for performance
                            END as estimated_row_count
                        FROM (
                            SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'
                            UNION ALL
                            SELECT table_name FROM information_schema.views WHERE table_schema = 'main'
                        ) all_tables
                        GROUP BY table_name
                    ) t ON c.table_name = t.table_name
                    WHERE c.table_schema = 'main'
                    AND c.table_name IN (
                        SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'
                        UNION ALL
                        SELECT table_name FROM information_schema.views WHERE table_schema = 'main'
                    )
                ),
                pk_info AS (
                    -- Attempt to identify primary keys through naming convention
                    SELECT 
                        table_name,
                        column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'main'
                    AND (
                        column_name = 'id' 
                        OR column_name LIKE '%_id'
                        OR column_name LIKE 'pk_%'
                    )
                    AND ordinal_position = 1
                    AND table_name IN (
                        SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'
                        UNION ALL
                        SELECT table_name FROM information_schema.views WHERE table_schema = 'main'
                    )
                )
                SELECT 
                    ti.*,
                    CASE WHEN pk.column_name IS NOT NULL THEN TRUE ELSE FALSE END as is_likely_pk
                FROM table_info ti
                LEFT JOIN pk_info pk 
                    ON ti.table_name = pk.table_name 
                    AND ti.column_name = pk.column_name
                ORDER BY ti.table_name, ti.ordinal_position
            """,
            
            # Batch row count query
            "batch_counts": """
                SELECT 
                    table_name,
                    COUNT(*) as row_count
                FROM information_schema.tables t
                CROSS JOIN LATERAL (
                    SELECT COUNT(*) FROM {table_name}
                ) AS counts
                WHERE table_schema = 'main'
                AND table_name IN ({tables})
                GROUP BY table_name
            """,
            
            # Cardinality statistics for multiple columns
            "batch_cardinality": """
                SELECT 
                    '{table}' as table_name,
                    '{column}' as column_name,
                    COUNT(DISTINCT {column}) as cardinality,
                    COUNT(*) as total_rows,
                    CAST(COUNT(DISTINCT {column}) AS FLOAT) / NULLIF(COUNT(*), 0) as selectivity
                FROM {table}
            """
        }
    
    @timer_decorator
    def extract_schema_optimized(
        self,
        force_refresh: bool = False,
        tables: Optional[List[str]] = None
    ) -> Dict[str, TableSchema]:
        """
        Extract schema with optimized queries and caching.
        
        Args:
            force_refresh: Force refresh of cache
            tables: Specific tables to extract (None for all)
            
        Returns:
            Dictionary of table schemas
        """
        self.metrics.start_operation("full_extraction")
        
        # Check cache first
        if not force_refresh:
            cache_key = calculate_content_hash(tables or "all")
            cached_schema = self.cache.get_schema(cache_key)
            if cached_schema:
                self.metrics.end_operation("full_extraction", {"source": "cache"})
                return cached_schema
        
        # Extract metadata with single optimized query
        metadata_df = self._extract_all_metadata()
        
        if metadata_df.empty:
            logger.warning("No tables found in database")
            self.metrics.end_operation("full_extraction", {"source": "empty"})
            return {}
        
        # Filter tables if specified
        if tables:
            metadata_df = metadata_df[metadata_df["table_name"].isin(tables)]
        
        # Build schema dictionary
        schema_dict = self._build_schema_dict(metadata_df)
        
        # Parallel extraction of additional data
        self._enrich_schema_parallel(schema_dict)
        
        # Cache the results
        cache_key = calculate_content_hash(tables or list(schema_dict.keys()))
        self.cache.set_schema(cache_key, schema_dict)
        
        # Cache individual tables
        for table_name, table_schema in schema_dict.items():
            self.cache.set_table(table_name, table_schema)
        
        self.metrics.end_operation("full_extraction", {
            "source": "fresh",
            "tables": len(schema_dict)
        })
        
        return schema_dict
    
    @timer_decorator
    def _extract_all_metadata(self) -> pd.DataFrame:
        """Extract all metadata with single query."""
        try:
            query = self._queries["full_metadata"]
            
            if hasattr(self.conn, "execute"):
                result = self.conn.execute(query)
                df = result.fetchdf() if hasattr(result, "fetchdf") else pd.DataFrame(result.fetchall())
            else:
                df = self.conn.execute(query).df()
            
            return df
        except Exception as e:
            logger.error(f"Failed to extract metadata: {e}")
            # Fallback to simpler query
            return self._extract_basic_metadata()
    
    def _extract_basic_metadata(self) -> pd.DataFrame:
        """Fallback to basic metadata extraction."""
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
        
        if hasattr(self.conn, "execute"):
            result = self.conn.execute(query)
            return result.fetchdf() if hasattr(result, "fetchdf") else pd.DataFrame(result.fetchall())
        else:
            return self.conn.execute(query).df()
    
    def _build_schema_dict(self, metadata_df: pd.DataFrame) -> Dict[str, TableSchema]:
        """Build schema dictionary from metadata dataframe."""
        schema_dict = {}
        
        for table_name in metadata_df["table_name"].unique():
            table_df = metadata_df[metadata_df["table_name"] == table_name]
            table_schema = TableSchema(name=table_name)
            
            # Extract row count if available
            if "estimated_row_count" in table_df.columns:
                row_count = table_df.iloc[0].get("estimated_row_count")
                if pd.notna(row_count):
                    table_schema.row_count = int(row_count)
            
            # Build columns
            for _, row in table_df.iterrows():
                is_pk = row.get("is_likely_pk", False) if "is_likely_pk" in row else False
                
                column_info = ColumnInfo(
                    name=row["column_name"],
                    data_type=row["data_type"],
                    is_nullable=row.get("is_nullable", "YES") == "YES",
                    is_primary_key=is_pk,
                    is_unique=is_pk or "unique" in row["column_name"].lower(),
                    default_value=row.get("column_default"),
                    column_position=int(row["ordinal_position"])
                )
                table_schema.columns.append(column_info)
            
            # Infer foreign keys
            table_schema.foreign_keys = self._infer_foreign_keys(table_schema)
            
            schema_dict[table_name] = table_schema
        
        return schema_dict
    
    def _infer_foreign_keys(self, table_schema: TableSchema) -> List[ForeignKeyRelation]:
        """Infer foreign key relationships from column names."""
        foreign_keys = []
        
        for col in table_schema.columns:
            if col.name.endswith("_id") and col.name != "id":
                # Likely a foreign key
                ref_table = col.name[:-3]  # Remove '_id'
                
                fk = ForeignKeyRelation(
                    from_table=table_schema.name,
                    from_column=col.name,
                    to_table=ref_table,
                    to_column="id"
                )
                foreign_keys.append(fk)
        
        return foreign_keys
    
    def _enrich_schema_parallel(self, schema_dict: Dict[str, TableSchema]):
        """Enrich schema with additional data using parallel processing."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit tasks for sample data and statistics
            futures = []
            
            for table_name, table_schema in schema_dict.items():
                # Only get samples for tables with reasonable row counts
                if table_schema.row_count and table_schema.row_count > 0:
                    if table_schema.row_count < 100000:  # Skip very large tables
                        future = executor.submit(
                            self._get_table_samples,
                            table_name,
                            self.sample_rows
                        )
                        futures.append((table_name, "samples", future))
                    
                    # Get cardinality for key columns
                    for col in table_schema.columns:
                        if col.is_primary_key or col.is_unique or "id" in col.name.lower():
                            future = executor.submit(
                                self._get_column_cardinality,
                                table_name,
                                col.name
                            )
                            futures.append((table_name, f"card_{col.name}", future))
            
            # Collect results
            for table_name, data_type, future in futures:
                try:
                    result = future.result(timeout=2.0)  # 2 second timeout per operation
                    
                    if data_type == "samples":
                        schema_dict[table_name].sample_data = result
                    elif data_type.startswith("card_"):
                        col_name = data_type[5:]  # Remove 'card_' prefix
                        if result is not None:
                            schema_dict[table_name].cardinality_stats[col_name] = result
                            
                except concurrent.futures.TimeoutError:
                    logger.debug(f"Timeout getting {data_type} for {table_name}")
                except Exception as e:
                    logger.debug(f"Error getting {data_type} for {table_name}: {e}")
    
    def _get_table_samples(self, table_name: str, limit: int) -> Optional[List[List[Any]]]:
        """Get sample data for a table."""
        try:
            query = f"SELECT * FROM {table_name} LIMIT {limit}"
            
            if hasattr(self.conn, "execute"):
                result = self.conn.execute(query)
                df = result.fetchdf() if hasattr(result, "fetchdf") else pd.DataFrame(result.fetchall())
            else:
                df = self.conn.execute(query).df()
            
            if not df.empty:
                return df.values.tolist()
            
        except Exception as e:
            logger.debug(f"Could not get samples for {table_name}: {e}")
        
        return None
    
    def _get_column_cardinality(self, table_name: str, column_name: str) -> Optional[int]:
        """Get cardinality for a column."""
        try:
            query = f"SELECT COUNT(DISTINCT {column_name}) as card FROM {table_name}"
            
            if hasattr(self.conn, "execute"):
                result = self.conn.execute(query)
                df = result.fetchdf() if hasattr(result, "fetchdf") else pd.DataFrame(result.fetchall())
            else:
                df = self.conn.execute(query).df()
            
            if not df.empty:
                return int(df.iloc[0]["card"])
            
        except Exception as e:
            logger.debug(f"Could not get cardinality for {table_name}.{column_name}: {e}")
        
        return None
    
    def get_table_names(self) -> List[str]:
        """Get list of all table names quickly."""
        # Check cache first
        cached_names = self.cache.get_query_pattern("table_names")
        if cached_names:
            return cached_names
        
        query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        
        try:
            if hasattr(self.conn, "execute"):
                result = self.conn.execute(query)
                df = result.fetchdf() if hasattr(result, "fetchdf") else pd.DataFrame(result.fetchall())
            else:
                df = self.conn.execute(query).df()
            
            table_names = df["table_name"].tolist() if not df.empty else []
            
            # Cache the result
            self.cache.set_query_pattern("table_names", table_names)
            
            return table_names
            
        except Exception as e:
            logger.error(f"Failed to get table names: {e}")
            return []
    
    def validate_and_refresh(self, schema: Dict[str, TableSchema]) -> bool:
        """
        Validate cached schema and refresh if needed.
        
        Args:
            schema: Cached schema to validate
            
        Returns:
            True if schema is valid, False if refresh needed
        """
        current_tables = set(self.get_table_names())
        cached_tables = set(schema.keys())
        
        # Check if tables have changed
        if current_tables != cached_tables:
            logger.info("Table list changed, refresh needed")
            return False
        
        # Sample check on a few tables for schema changes
        sample_tables = list(current_tables)[:min(3, len(current_tables))]
        
        for table_name in sample_tables:
            # Quick column count check
            query = f"""
                SELECT COUNT(*) as col_count 
                FROM information_schema.columns 
                WHERE table_schema = 'main' AND table_name = '{table_name}'
            """
            
            try:
                if hasattr(self.conn, "execute"):
                    result = self.conn.execute(query)
                    df = result.fetchdf() if hasattr(result, "fetchdf") else pd.DataFrame(result.fetchall())
                else:
                    df = self.conn.execute(query).df()
                
                current_col_count = int(df.iloc[0]["col_count"])
                cached_col_count = len(schema[table_name].columns)
                
                if current_col_count != cached_col_count:
                    logger.info(f"Column count changed for {table_name}")
                    return False
                    
            except Exception as e:
                logger.debug(f"Could not validate {table_name}: {e}")
        
        return True