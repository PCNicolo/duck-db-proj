"""
Query Explainer with LLM Feedback Integration.

This module provides enhanced query explanations by:
1. Generating natural language explanations of SQL queries
2. Receiving feedback from the LLM that generated the query
3. Incorporating feedback to improve explanations
"""

import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class QueryExplainer:
    """Provides enhanced SQL query explanations with LLM feedback integration."""
    
    def __init__(self, llm_client=None, base_url: str = "http://localhost:1234/v1"):
        """
        Initialize the Query Explainer.
        
        Args:
            llm_client: OpenAI-compatible client for LLM interaction
            base_url: Base URL for the LLM API
        """
        self.llm_client = llm_client
        self.base_url = base_url
        
        # Store feedback history for learning
        self.feedback_history: List[Dict[str, Any]] = []
        
        # Cache for explanations
        self.explanation_cache: Dict[str, Dict[str, Any]] = {}
        
    def generate_explanation(
        self,
        sql_query: str,
        natural_language_query: Optional[str] = None,
        schema_context: Optional[Dict] = None,
        llm_feedback: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate an enhanced explanation of the SQL query.
        
        Args:
            sql_query: The SQL query to explain
            natural_language_query: The original natural language query
            schema_context: Schema information for context
            llm_feedback: Feedback from the LLM that generated the query
            
        Returns:
            Dictionary containing:
                - explanation: Natural language explanation
                - query_breakdown: Step-by-step breakdown
                - feedback_incorporated: Whether feedback was used
                - confidence: Confidence score (0-1)
        """
        start_time = time.time()
        
        # Check cache first
        cache_key = f"{sql_query}:{natural_language_query}:{llm_feedback}"
        if cache_key in self.explanation_cache:
            logger.info("Returning cached explanation")
            return self.explanation_cache[cache_key]
        
        try:
            # Parse SQL query components
            query_components = self._parse_sql_components(sql_query)
            
            # Generate base explanation
            base_explanation = self._generate_base_explanation(
                query_components, natural_language_query
            )
            
            # Enhance with LLM feedback if provided
            if llm_feedback:
                enhanced_explanation = self._incorporate_llm_feedback(
                    base_explanation, llm_feedback, query_components
                )
            else:
                enhanced_explanation = base_explanation
            
            # Generate step-by-step breakdown
            query_breakdown = self._generate_query_breakdown(
                query_components, schema_context
            )
            
            # Calculate confidence based on available context
            confidence = self._calculate_confidence(
                has_nl_query=bool(natural_language_query),
                has_schema=bool(schema_context),
                has_feedback=bool(llm_feedback)
            )
            
            result = {
                "explanation": enhanced_explanation,
                "query_breakdown": query_breakdown,
                "feedback_incorporated": bool(llm_feedback),
                "confidence": confidence,
                "generation_time": time.time() - start_time,
                "components": query_components
            }
            
            # Cache the result
            self.explanation_cache[cache_key] = result
            
            # Store feedback for learning
            if llm_feedback:
                self._store_feedback(sql_query, llm_feedback, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating explanation: {str(e)}")
            return {
                "explanation": "Unable to generate detailed explanation. The query will execute as shown.",
                "query_breakdown": [],
                "feedback_incorporated": False,
                "confidence": 0.0,
                "error": str(e)
            }
    
    def get_llm_feedback(
        self,
        sql_query: str,
        natural_language_query: str,
        execution_result: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Request feedback from LM-Studio about the query.
        
        Args:
            sql_query: The generated SQL query
            natural_language_query: The original request
            execution_result: Optional execution results
            
        Returns:
            Feedback string from the LLM
        """
        if not self.llm_client:
            return None
            
        try:
            prompt = self._build_feedback_prompt(
                sql_query, natural_language_query, execution_result
            )
            
            response = self.llm_client.chat.completions.create(
                model="local-model",
                messages=[
                    {"role": "system", "content": "You are a SQL expert providing feedback on query generation and explanation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            feedback = response.choices[0].message.content
            logger.info(f"Received LLM feedback: {feedback[:100]}...")
            
            return feedback
            
        except Exception as e:
            logger.error(f"Error getting LLM feedback: {str(e)}")
            return None
    
    def _parse_sql_components(self, sql_query: str) -> Dict[str, Any]:
        """Parse SQL query into its components."""
        sql_upper = sql_query.upper()
        components = {
            "select": [],
            "from": [],
            "where": [],
            "group_by": [],
            "having": [],
            "order_by": [],
            "limit": None,
            "joins": [],
            "aggregations": []
        }
        
        # Simple parsing - can be enhanced with proper SQL parser
        lines = sql_query.split('\n')
        current_section = None
        
        for line in lines:
            line_upper = line.strip().upper()
            
            if line_upper.startswith('SELECT'):
                current_section = 'select'
                components['select'] = self._extract_select_columns(line)
            elif line_upper.startswith('FROM'):
                current_section = 'from'
                components['from'] = self._extract_tables(line)
            elif line_upper.startswith('WHERE'):
                current_section = 'where'
                components['where'] = self._extract_conditions(line)
            elif line_upper.startswith('GROUP BY'):
                current_section = 'group_by'
                components['group_by'] = self._extract_columns(line, 'GROUP BY')
            elif line_upper.startswith('ORDER BY'):
                current_section = 'order_by'
                components['order_by'] = self._extract_columns(line, 'ORDER BY')
            elif line_upper.startswith('LIMIT'):
                components['limit'] = self._extract_limit(line)
            elif 'JOIN' in line_upper:
                components['joins'].append(line.strip())
            
            # Detect aggregations
            for agg in ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN']:
                if agg in line_upper:
                    components['aggregations'].append(agg)
        
        return components
    
    def _generate_base_explanation(
        self,
        components: Dict[str, Any],
        natural_language_query: Optional[str]
    ) -> str:
        """Generate base explanation from query components."""
        explanation_parts = []
        
        # Start with the intent if we have the natural language query
        if natural_language_query:
            explanation_parts.append(f"This query addresses: '{natural_language_query}'")
            explanation_parts.append("")
        
        explanation_parts.append("The query will:")
        
        # Explain what we're selecting
        if components['select']:
            if '*' in str(components['select']):
                explanation_parts.append("• Retrieve all columns")
            else:
                explanation_parts.append(f"• Select specific columns: {', '.join(components['select'])}")
        
        # Explain data source
        if components['from']:
            explanation_parts.append(f"• From the table(s): {', '.join(components['from'])}")
        
        # Explain joins
        if components['joins']:
            explanation_parts.append(f"• Combine data using {len(components['joins'])} join(s)")
        
        # Explain filtering
        if components['where']:
            explanation_parts.append(f"• Filter results based on {len(components['where'])} condition(s)")
        
        # Explain grouping
        if components['group_by']:
            explanation_parts.append(f"• Group results by: {', '.join(components['group_by'])}")
        
        # Explain aggregations
        if components['aggregations']:
            agg_set = set(components['aggregations'])
            explanation_parts.append(f"• Apply aggregations: {', '.join(agg_set)}")
        
        # Explain ordering
        if components['order_by']:
            explanation_parts.append(f"• Sort results by: {', '.join(components['order_by'])}")
        
        # Explain limit
        if components['limit']:
            explanation_parts.append(f"• Limit output to {components['limit']} rows")
        
        return '\n'.join(explanation_parts)
    
    def _incorporate_llm_feedback(
        self,
        base_explanation: str,
        llm_feedback: str,
        components: Dict[str, Any]
    ) -> str:
        """Enhance explanation with LLM feedback."""
        enhanced_parts = [base_explanation]
        
        # Add LLM insights
        enhanced_parts.append("\n**Additional Context from Query Generation:**")
        
        # Parse and structure the feedback
        feedback_lines = llm_feedback.split('\n')
        for line in feedback_lines:
            line = line.strip()
            if line and not line.startswith('#'):
                enhanced_parts.append(f"• {line}")
        
        # Add performance considerations if aggregations are present
        if components['aggregations']:
            enhanced_parts.append("\n**Performance Note:**")
            enhanced_parts.append("• This query uses aggregations which may take longer on large datasets")
        
        return '\n'.join(enhanced_parts)
    
    def _generate_query_breakdown(
        self,
        components: Dict[str, Any],
        schema_context: Optional[Dict]
    ) -> List[Dict[str, str]]:
        """Generate step-by-step query breakdown."""
        breakdown = []
        step = 1
        
        # Step 1: Data source
        if components['from']:
            breakdown.append({
                "step": step,
                "action": "Data Source",
                "description": f"Access table(s): {', '.join(components['from'])}",
                "sql_fragment": f"FROM {', '.join(components['from'])}"
            })
            step += 1
        
        # Step 2: Joins
        if components['joins']:
            for join in components['joins']:
                breakdown.append({
                    "step": step,
                    "action": "Join Tables",
                    "description": "Combine data from multiple tables",
                    "sql_fragment": join
                })
                step += 1
        
        # Step 3: Filtering
        if components['where']:
            breakdown.append({
                "step": step,
                "action": "Apply Filters",
                "description": f"Filter data using {len(components['where'])} condition(s)",
                "sql_fragment": f"WHERE ..."
            })
            step += 1
        
        # Step 4: Grouping
        if components['group_by']:
            breakdown.append({
                "step": step,
                "action": "Group Data",
                "description": f"Group by {', '.join(components['group_by'])}",
                "sql_fragment": f"GROUP BY {', '.join(components['group_by'])}"
            })
            step += 1
        
        # Step 5: Aggregations
        if components['aggregations']:
            breakdown.append({
                "step": step,
                "action": "Calculate Aggregations",
                "description": f"Apply functions: {', '.join(set(components['aggregations']))}",
                "sql_fragment": "SELECT ... aggregation functions ..."
            })
            step += 1
        
        # Step 6: Sorting
        if components['order_by']:
            breakdown.append({
                "step": step,
                "action": "Sort Results",
                "description": f"Order by {', '.join(components['order_by'])}",
                "sql_fragment": f"ORDER BY {', '.join(components['order_by'])}"
            })
            step += 1
        
        # Step 7: Limit
        if components['limit']:
            breakdown.append({
                "step": step,
                "action": "Limit Results",
                "description": f"Return top {components['limit']} rows",
                "sql_fragment": f"LIMIT {components['limit']}"
            })
        
        return breakdown
    
    def _calculate_confidence(
        self,
        has_nl_query: bool,
        has_schema: bool,
        has_feedback: bool
    ) -> float:
        """Calculate confidence score for the explanation."""
        score = 0.5  # Base confidence
        
        if has_nl_query:
            score += 0.2
        if has_schema:
            score += 0.2
        if has_feedback:
            score += 0.1
        
        return min(score, 1.0)
    
    def _store_feedback(
        self,
        sql_query: str,
        feedback: str,
        result: Dict[str, Any]
    ):
        """Store feedback for future learning."""
        self.feedback_history.append({
            "timestamp": datetime.now().isoformat(),
            "sql_query": sql_query,
            "feedback": feedback,
            "explanation": result['explanation'],
            "confidence": result['confidence']
        })
        
        # Keep only last 100 feedback items
        if len(self.feedback_history) > 100:
            self.feedback_history = self.feedback_history[-100:]
    
    def _build_feedback_prompt(
        self,
        sql_query: str,
        natural_language_query: str,
        execution_result: Optional[Dict]
    ) -> str:
        """Build prompt for requesting LLM feedback."""
        prompt = f"""
Given the following SQL query generation:

Original Request: {natural_language_query}

Generated SQL:
{sql_query}

Please provide feedback on:
1. How well the SQL addresses the original request
2. Any potential optimizations or improvements
3. Key aspects of the query that users should understand
4. Any potential issues or edge cases

Keep the feedback concise and focused on helping users understand what the query does.
"""
        
        if execution_result:
            prompt += f"\n\nExecution Result Summary: {execution_result.get('summary', 'N/A')}"
        
        return prompt
    
    # Helper methods for parsing
    def _extract_select_columns(self, line: str) -> List[str]:
        """Extract column names from SELECT clause."""
        select_part = line.upper().replace('SELECT', '').strip()
        if select_part == '*':
            return ['*']
        columns = [col.strip() for col in select_part.split(',')]
        return columns
    
    def _extract_tables(self, line: str) -> List[str]:
        """Extract table names from FROM clause."""
        from_part = line.upper().replace('FROM', '').strip()
        tables = [table.strip() for table in from_part.split(',')]
        return tables
    
    def _extract_conditions(self, line: str) -> List[str]:
        """Extract conditions from WHERE clause."""
        where_part = line.upper().replace('WHERE', '').strip()
        # Simple split by AND/OR - can be enhanced
        conditions = []
        for cond in where_part.replace(' AND ', '|').replace(' OR ', '|').split('|'):
            if cond.strip():
                conditions.append(cond.strip())
        return conditions
    
    def _extract_columns(self, line: str, keyword: str) -> List[str]:
        """Extract column names after a keyword."""
        part = line.upper().replace(keyword, '').strip()
        columns = [col.strip() for col in part.split(',')]
        return columns
    
    def _extract_limit(self, line: str) -> Optional[int]:
        """Extract LIMIT value."""
        try:
            limit_part = line.upper().replace('LIMIT', '').strip()
            return int(limit_part)
        except:
            return None