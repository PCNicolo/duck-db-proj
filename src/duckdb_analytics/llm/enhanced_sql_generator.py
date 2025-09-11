"""Enhanced SQL Generator with performance optimizations."""

import logging
import time
from typing import Dict, Optional, Tuple

from openai import OpenAI

from .config import (
    DEFAULT_CONTEXT_LEVEL,
    FEEDBACK_TIMEOUT,
    LM_STUDIO_URL,
    MAX_TOKENS,
    MAX_TOKENS_FAST_MODE,
    MAX_TOKENS_DETAILED_MODE,
    MODEL_NAME,
    REQUEST_TIMEOUT,
    REQUEST_TIMEOUT_DETAILED,
    SCHEMA_WARM_ON_STARTUP,
    SQL_SYSTEM_PROMPT,
    SQL_FAST_MODE_PROMPT,
    SQL_DETAILED_MODE_PROMPT,
    TEMPERATURE,
)
from .optimized_context_manager import OptimizedContextManager
from .optimized_schema_extractor import OptimizedSchemaExtractor
from .performance_utils import PerformanceMetrics, calculate_content_hash
from .schema_cache import SchemaCache
from .query_explainer import QueryExplainer

logger = logging.getLogger(__name__)


class EnhancedSQLGenerator:
    """High-performance SQL generation with caching and optimization."""
    
    def __init__(
        self,
        duckdb_conn,
        base_url: str = LM_STUDIO_URL,
        model: str = MODEL_NAME,
        cache_dir: Optional[str] = None,
        warm_cache: bool = SCHEMA_WARM_ON_STARTUP
    ):
        """
        Initialize enhanced SQL generator.
        
        Args:
            duckdb_conn: DuckDB connection
            base_url: LM Studio API endpoint
            model: Model identifier
            cache_dir: Directory for persistent cache
            warm_cache: Whether to warm cache on startup
        """
        self.duckdb_conn = duckdb_conn
        self.base_url = base_url
        self.model = model
        
        # Initialize OpenAI client
        self.client = OpenAI(
            base_url=base_url,
            api_key="not-needed",
            timeout=REQUEST_TIMEOUT_DETAILED  # Use longer timeout to handle detailed mode
        )
        
        # Initialize optimized components
        self.cache = SchemaCache()
        self.schema_extractor = OptimizedSchemaExtractor(
            duckdb_conn=duckdb_conn,
            cache=self.cache
        )
        self.context_manager = OptimizedContextManager()
        
        # Performance tracking
        self.metrics = PerformanceMetrics()
        
        # Availability tracking
        self._available = None
        self._last_check_time = 0
        self._check_interval = 30
        
        # Query pattern cache
        self._query_pattern_cache: Dict[str, str] = {}
        
        # Initialize query explainer for enhanced explanations
        self.query_explainer = QueryExplainer(llm_client=self.client, base_url=base_url)
        
        # Warm cache if requested
        if warm_cache:
            self._warm_cache()
    
    def _warm_cache(self):
        """Warm up caches on initialization."""
        logger.info("Warming up schema cache...")
        start_time = time.time()
        
        try:
            # Extract and cache schema
            schema = self.schema_extractor.extract_schema_optimized()
            
            # Build indexes for context manager
            self.context_manager.build_indexes(schema)
            
            # Cache successful patterns from config
            common_patterns = [
                ("select all from", "SELECT * FROM {table} LIMIT 100"),
                ("count rows in", "SELECT COUNT(*) FROM {table}"),
                ("distinct values in", "SELECT DISTINCT {column} FROM {table}"),
                ("average of", "SELECT AVG({column}) FROM {table}"),
                ("sum of", "SELECT SUM({column}) FROM {table}"),
                ("group by", "SELECT {column}, COUNT(*) FROM {table} GROUP BY {column}"),
            ]
            
            for pattern, sql_template in common_patterns:
                pattern_hash = calculate_content_hash(pattern)
                self.cache.set_query_pattern(pattern_hash, sql_template)
            
            elapsed = time.time() - start_time
            logger.info(f"Cache warmed in {elapsed:.2f}s with {len(schema)} tables")
            
        except Exception as e:
            logger.warning(f"Failed to warm cache: {e}")
    
    def is_available(self) -> bool:
        """Check if LM Studio is available."""
        current_time = time.time()
        
        # Use cached result if recent
        if (
            self._available is not None
            and (current_time - self._last_check_time) < self._check_interval
        ):
            return self._available
        
        try:
            # Check connectivity
            models = self.client.models.list()
            self._available = True
            self._last_check_time = current_time
            logger.info(f"LM Studio available at {self.base_url}")
            return True
        except Exception as e:
            logger.warning(f"LM Studio not available: {e}")
            self._available = False
            self._last_check_time = current_time
            return False
    
    def generate_sql(
        self,
        natural_language_query: str,
        context_level: str = DEFAULT_CONTEXT_LEVEL,
        use_cache: bool = True,
        validate: bool = True,
        return_metrics: bool = False,
        thinking_mode: bool = False
    ) -> Tuple[Optional[str], Dict]:
        """
        Generate SQL from natural language with optimizations.
        
        Args:
            natural_language_query: User's query
            context_level: Schema detail level
            use_cache: Whether to use cached patterns
            validate: Whether to validate generated SQL
            return_metrics: Whether to return performance metrics
            
        Returns:
            Tuple of (SQL query, metadata dictionary)
        """
        self.metrics.start_operation("generate_sql")
        metadata = {
            "cache_hit": False,
            "generation_time": 0,
            "validation_passed": None,
            "performance_metrics": {}
        }
        
        # Check query pattern cache
        if use_cache:
            query_hash = calculate_content_hash(natural_language_query.lower())
            cached_sql = self.cache.get_query_pattern(query_hash)
            
            if cached_sql:
                logger.debug("Using cached query pattern")
                metadata["cache_hit"] = True
                metadata["generation_time"] = 0
                
                if return_metrics:
                    metadata["performance_metrics"] = self.metrics.get_summary()
                
                self.metrics.end_operation("generate_sql", {"source": "cache"})
                return self._adapt_cached_sql(cached_sql, natural_language_query), metadata
        
        # Check LLM availability
        if not self.is_available():
            logger.error("LM Studio is not available")
            self.metrics.end_operation("generate_sql", {"source": "unavailable"})
            return None, metadata
        
        # Get optimized schema
        self.metrics.start_operation("schema_extraction")
        schema = self.schema_extractor.extract_schema_optimized()
        self.metrics.end_operation("schema_extraction")
        
        # Build optimized context
        self.metrics.start_operation("context_building")
        
        # Choose prompt based on thinking mode
        if thinking_mode:
            base_prompt = SQL_DETAILED_MODE_PROMPT
            max_tokens = MAX_TOKENS_DETAILED_MODE
        else:
            base_prompt = SQL_FAST_MODE_PROMPT
            max_tokens = MAX_TOKENS_FAST_MODE
        
        prompt, context_metadata = self.context_manager.build_optimized_context(
            query=natural_language_query,
            schema=schema,
            base_prompt=base_prompt,
            context_level=context_level
        )
        
        # Debug logging for thinking mode
        if thinking_mode:
            logger.info(f"DETAILED MODE ACTIVE - Using {len(base_prompt)} char prompt")
            logger.info(f"Base prompt starts with: {base_prompt[:100]}...")
        else:
            logger.info(f"FAST MODE ACTIVE - Using {len(base_prompt)} char prompt")
        self.metrics.end_operation("context_building")
        
        metadata.update(context_metadata)
        
        # Generate SQL with LLM
        self.metrics.start_operation("llm_generation")
        start_time = time.time()
        
        try:
            # Try to generate SQL with retry logic
            max_retries = 2
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": natural_language_query}
                        ],
                        max_tokens=max_tokens,
                        temperature=TEMPERATURE,
                        stream=False,
                        timeout=REQUEST_TIMEOUT_DETAILED if thinking_mode else REQUEST_TIMEOUT
                    )
                    
                    sql_response = response.choices[0].message.content.strip()
                    
                    # Parse response based on thinking mode
                    if thinking_mode:
                        sql_query, thinking_process = self._parse_detailed_response(sql_response)
                        # Store thinking process in metadata for display
                        metadata["detailed_thinking"] = thinking_process
                        logger.info(f"Detailed mode - raw response length: {len(sql_response)}")
                        logger.info(f"Detailed mode - thinking process length: {len(thinking_process)}")
                        logger.info(f"Detailed mode - SQL extracted: {sql_query[:100]}...")
                    else:
                        sql_query = self._clean_sql_output(sql_response)
                        metadata["detailed_thinking"] = None
                    
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        raise e
                    logger.warning(f"Retry {retry_count}/{max_retries} after error: {str(e)}")
                    time.sleep(1)  # Brief pause before retry
            
            metadata["generation_time"] = time.time() - start_time
            self.metrics.end_operation("llm_generation", {"success": True})
            
            # Validate if requested
            if validate:
                self.metrics.start_operation("sql_validation")
                is_valid, errors = self._validate_sql(sql_query, schema)
                metadata["validation_passed"] = is_valid
                
                if not is_valid:
                    metadata["validation_errors"] = errors
                    logger.warning(f"SQL validation failed: {errors}")
                
                self.metrics.end_operation("sql_validation", {"valid": is_valid})
            
            # Cache successful generation
            if use_cache and sql_query and (not validate or metadata["validation_passed"]):
                query_hash = calculate_content_hash(natural_language_query.lower())
                self.cache.set_query_pattern(query_hash, sql_query)
            
            if return_metrics:
                metadata["performance_metrics"] = self.metrics.get_summary()
            
            self.metrics.end_operation("generate_sql", {"source": "llm"})
            return sql_query, metadata
            
        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            metadata["error"] = str(e)
            self.metrics.end_operation("llm_generation", {"success": False})
            self.metrics.end_operation("generate_sql", {"source": "error"})
            
            if return_metrics:
                metadata["performance_metrics"] = self.metrics.get_summary()
            
            return None, metadata

    def generate_sql_with_explanation(
        self,
        natural_language_query: str,
        context_level: str = DEFAULT_CONTEXT_LEVEL,
        return_metrics: bool = False,
        include_llm_feedback: bool = True,
        thinking_mode: bool = False
    ) -> Tuple[Optional[str], Dict]:
        """
        Generate SQL with enhanced explanation and LLM feedback.
        
        Args:
            natural_language_query: User's natural language query
            context_level: Schema context detail level
            return_metrics: Whether to include performance metrics
            include_llm_feedback: Whether to request LLM feedback
            
        Returns:
            Tuple of (SQL query, metadata with explanation)
        """
        # First generate the SQL
        sql_query, metadata = self.generate_sql(
            natural_language_query,
            context_level=context_level,
            return_metrics=return_metrics,
            thinking_mode=thinking_mode
        )
        
        if not sql_query:
            return sql_query, metadata
        
        try:
            # Get schema for context
            schema = self.schema_extractor.extract_schema_optimized()
            
            # Get LLM feedback if requested (with timeout protection)
            llm_feedback = None
            if include_llm_feedback:
                try:
                    # Try to get feedback but don't let it block the main flow
                    llm_feedback = self.query_explainer.get_llm_feedback(
                        sql_query=sql_query,
                        natural_language_query=natural_language_query,
                        execution_result=None,  # Can be added later if query is executed
                        timeout=FEEDBACK_TIMEOUT  # Use configured timeout for feedback
                    )
                except Exception:
                    # Silently continue without feedback - it's optional
                    llm_feedback = None
            
            # Generate enhanced explanation
            explanation_result = self.query_explainer.generate_explanation(
                sql_query=sql_query,
                natural_language_query=natural_language_query,
                schema_context=schema,
                llm_feedback=llm_feedback
            )
            
            # Add explanation to metadata
            metadata["explanation"] = explanation_result
            
            logger.info(f"Generated SQL with explanation (confidence: {explanation_result['confidence']:.2f})")
            
        except Exception as e:
            logger.error(f"Error generating explanation: {str(e)}")
            # Still return the SQL even if explanation fails
            metadata["explanation"] = {
                "explanation": "Unable to generate detailed explanation.",
                "query_breakdown": [],
                "feedback_incorporated": False,
                "confidence": 0.0,
                "error": str(e)
            }
        
        return sql_query, metadata
    
    def _adapt_cached_sql(self, sql_template: str, query: str) -> str:
        """Adapt cached SQL template to current query."""
        # Handle case where sql_template might be a CacheEntry object
        if hasattr(sql_template, 'data'):
            sql_template = sql_template.data
        elif hasattr(sql_template, 'replace'):
            # It's already a string, continue
            pass
        else:
            # Fallback - convert to string
            sql_template = str(sql_template)
        
        # Simple adaptation - can be enhanced with more sophisticated logic
        query_lower = query.lower()
        
        # Extract table names from query
        schema = self.schema_extractor.extract_schema_optimized()
        for table_name in schema.keys():
            if table_name.lower() in query_lower:
                sql_template = sql_template.replace("{table}", table_name)
                
                # Find column references
                for col in schema[table_name].columns:
                    if col.name.lower() in query_lower:
                        sql_template = sql_template.replace("{column}", col.name)
                        break
                break
        
        return sql_template
    
    def _clean_sql_output(self, sql: str) -> str:
        """Clean SQL output from LLM."""
        # Remove markdown code blocks
        sql = sql.replace("```sql", "").replace("```", "")
        
        # Remove explanatory text
        lines = sql.split('\n')
        sql_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip comment lines and explanations
            if line and not line.startswith('--') and not line.startswith('#'):
                sql_lines.append(line)
        
        sql = ' '.join(sql_lines)
        
        # Ensure it ends with semicolon
        if sql and not sql.endswith(';'):
            sql += ';'
        
        return sql
    
    def _generate_fallback_sql(self, natural_language_query: str) -> str:
        """Generate SQL when detailed response didn't include SQL section."""
        try:
            # Get optimized schema
            schema = self.schema_extractor.extract_schema_optimized()
            
            # Use fast mode prompt for focused SQL generation
            prompt, _ = self.context_manager.build_optimized_context(
                query=natural_language_query,
                schema=schema,
                base_prompt=SQL_FAST_MODE_PROMPT,
                context_level="minimal"
            )
            
            # Make a focused call with lower token limit
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=800,  # Lower token limit for focused SQL
                timeout=REQUEST_TIMEOUT
            )
            
            if response and response.choices:
                sql_response = response.choices[0].message.content.strip()
                return self._clean_sql_output(sql_response)
            else:
                logger.warning("No response from fallback SQL generation")
                return None
                
        except Exception as e:
            logger.error(f"Fallback SQL generation failed: {e}")
            return None
    
    def _parse_detailed_response(self, response: str) -> Tuple[str, str]:
        """Parse detailed mode response to extract SQL and thinking process."""
        try:
            logger.info(f"Parsing detailed response (first 200 chars): {response[:200]}...")
            
            # Look for SQL section in multiple ways
            sql_markers = ["SQL:", "```sql", "**SQL:**", "SELECT", "WITH", "INSERT", "UPDATE", "DELETE"]
            sql_start = -1
            
            for marker in sql_markers:
                pos = response.find(marker)
                if pos != -1:
                    sql_start = pos
                    break
            
            if sql_start != -1:
                # Extract thinking process (everything before SQL)
                thinking_process = response[:sql_start].strip()
                
                # Extract SQL query
                sql_part = response[sql_start:]
                
                # Clean up SQL part based on what we found
                if "```sql" in sql_part:
                    sql_start_code = sql_part.find("```sql") + 6
                    sql_end_code = sql_part.find("```", sql_start_code)
                    if sql_end_code != -1:
                        sql_query = sql_part[sql_start_code:sql_end_code].strip()
                    else:
                        sql_query = sql_part[sql_start_code:].strip()
                elif "SQL:" in sql_part:
                    sql_query = sql_part.replace("SQL:", "").strip()
                else:
                    # Just take everything after the marker
                    sql_query = sql_part.strip()
                
                # Clean the extracted SQL
                sql_query = self._clean_sql_output(sql_query)
                
                logger.info(f"Extracted thinking process length: {len(thinking_process)}")
                logger.info(f"Extracted SQL: {sql_query}")
                
                # If we didn't get much thinking process, use the whole response as thinking
                if len(thinking_process.strip()) < 100:
                    logger.warning("Short thinking process, using full response as thinking")
                    thinking_process = response
                
                return sql_query, thinking_process
            else:
                # No clear SQL marker found - check for detailed response markers
                detailed_markers = ["🎯 STRATEGY:", "📊 BUSINESS CONTEXT:", "🔍 SCHEMA DECISIONS:", "✅ IMPLEMENTATION:"]
                marker_count = sum(1 for marker in detailed_markers if marker in response)
                
                if marker_count >= 2:
                    # This looks like a detailed response, try to extract SQL from lines
                    logger.info(f"Found {marker_count} detailed markers, treating as structured response")
                    lines = response.split('\n')
                    sql_lines = []
                    found_sql = False
                    
                    for line in lines:
                        if line.strip().upper().startswith(('SELECT', 'WITH', 'INSERT', 'UPDATE', 'DELETE')):
                            found_sql = True
                        if found_sql:
                            sql_lines.append(line)
                    
                    if sql_lines:
                        sql_query = '\n'.join(sql_lines)
                        sql_query = self._clean_sql_output(sql_query)
                        thinking_process = response.replace('\n'.join(sql_lines), '').strip()
                        return sql_query, thinking_process
                    else:
                        # No SQL found in detailed response - this is a partial response
                        # Log this as a token limit issue and make another call for just SQL
                        logger.warning(f"Detailed response has no SQL - likely token limit reached. Response length: {len(response)}")
                        logger.info("Making fallback call for SQL generation...")
                        
                        # Try to extract the original query from the thinking to make a focused SQL call
                        try:
                            # Make a quick SQL-only call
                            fallback_sql = self._generate_fallback_sql(natural_language_query)
                            if fallback_sql:
                                logger.info(f"Successfully generated fallback SQL: {fallback_sql[:100]}...")
                                return fallback_sql, response
                            else:
                                logger.warning("Fallback SQL generation failed")
                                return "SELECT 1;", response
                        except Exception as e:
                            logger.error(f"Fallback SQL generation error: {e}")
                            return "SELECT 1;", response
                else:
                    # Not a detailed response
                    if len(response.strip()) > 100:
                        return self._clean_sql_output(response), response
                    else:
                        return self._clean_sql_output(response), "Quick SQL generation without detailed analysis"
                
        except Exception as e:
            logger.warning(f"Failed to parse detailed response: {e}")
            return self._clean_sql_output(response), f"Response parsing failed: {response[:200]}..."

    def _validate_sql(self, sql: str, schema: Dict) -> Tuple[bool, list]:
        """Validate SQL against schema."""
        errors = []
        
        if not sql or not sql.strip():
            errors.append("SQL query is empty")
            return False, errors
        
        # Try to execute EXPLAIN
        try:
            if hasattr(self.duckdb_conn, "execute"):
                self.duckdb_conn.execute(f"EXPLAIN {sql}")
            else:
                self.duckdb_conn.execute(f"EXPLAIN {sql}")
            
            return True, []
            
        except Exception as e:
            error_msg = str(e)
            
            # Parse error for better feedback
            if "does not exist" in error_msg:
                errors.append(f"Table or column not found: {error_msg}")
            elif "syntax error" in error_msg.lower():
                errors.append(f"SQL syntax error: {error_msg}")
            else:
                errors.append(f"Validation error: {error_msg}")
            
            return False, errors
    
    def generate_sql_stream(
        self,
        natural_language_query: str,
        context_level: str = DEFAULT_CONTEXT_LEVEL
    ):
        """
        Generate SQL with streaming response.
        
        Args:
            natural_language_query: User's query
            context_level: Schema detail level
            
        Yields:
            SQL tokens as they're generated
        """
        # Get schema and build context
        schema = self.schema_extractor.extract_schema_optimized()
        prompt, _ = self.context_manager.build_optimized_context(
            query=natural_language_query,
            schema=schema,
            base_prompt=SQL_SYSTEM_PROMPT,
            context_level=context_level
        )
        
        try:
            # Stream response
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": natural_language_query}
                ],
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            yield f"-- Error: {e}"
    
    def get_performance_report(self) -> Dict:
        """Get detailed performance report."""
        return {
            "metrics": self.metrics.get_summary(),
            "cache_stats": self.cache.cache.get_stats(),
            "schema_tables": len(self.schema_extractor.get_table_names()),
            "cached_patterns": len(self._query_pattern_cache)
        }
    
    def clear_caches(self):
        """Clear all caches."""
        self.cache.cache.clear()
        self.context_manager.clear_cache()
        self._query_pattern_cache.clear()
        self.metrics.reset()
        logger.info("All caches cleared")