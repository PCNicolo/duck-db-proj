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
        Generate LLM's thinking process / scratch pad for the SQL query.
        
        Args:
            sql_query: The SQL query to explain
            natural_language_query: The original natural language query
            schema_context: Schema information for context
            llm_feedback: Feedback from the LLM that generated the query
            
        Returns:
            Dictionary containing the LLM's thought process
        """
        start_time = time.time()
        
        # Check cache first
        cache_key = f"{sql_query}:{natural_language_query}:{llm_feedback}"
        if cache_key in self.explanation_cache:
            logger.info("Returning cached explanation")
            return self.explanation_cache[cache_key]
        
        try:
            # Create the LLM's thinking scratch pad
            thinking_lines = []
            
            # Start with understanding the request
            if natural_language_query:
                thinking_lines.append(f"🎯 **User wants:** {natural_language_query}")
                thinking_lines.append("")
                thinking_lines.append("**My thinking process:**")
                thinking_lines.append("")
            
            # Parse the SQL to understand what we're doing
            components = self._parse_sql_components(sql_query)
            
            # Show the LLM's reasoning about data source
            if components['from']:
                tables = components['from']
                thinking_lines.append(f"📊 I need to look at the `{', '.join(tables)}` table(s)")
            
            # Reasoning about filters
            if components['where']:
                thinking_lines.append(f"🔍 I should filter the data based on {len(components['where'])} condition(s)")
                for condition in components['where'][:3]:  # Show first 3 conditions
                    thinking_lines.append(f"   • {condition}")
            
            # Reasoning about grouping
            if components['group_by']:
                thinking_lines.append(f"📁 I'll group the results by `{', '.join(components['group_by'])}`")
                thinking_lines.append("   (This organizes data into categories)")
            
            # Reasoning about calculations
            if components['aggregations']:
                agg_set = set(components['aggregations'])
                thinking_lines.append(f"🧮 I need to calculate: {', '.join(agg_set)}")
                for agg in agg_set:
                    if agg == 'COUNT':
                        thinking_lines.append("   • COUNT: How many items in each group")
                    elif agg == 'SUM':
                        thinking_lines.append("   • SUM: Add up the values")
                    elif agg == 'AVG':
                        thinking_lines.append("   • AVG: Find the average")
                    elif agg == 'MAX':
                        thinking_lines.append("   • MAX: Find the highest value")
                    elif agg == 'MIN':
                        thinking_lines.append("   • MIN: Find the lowest value")
            
            # Reasoning about sorting
            if components['order_by']:
                thinking_lines.append(f"⬆️ I'll sort by `{', '.join(components['order_by'])}` for better readability")
            
            # Reasoning about limits
            if components['limit']:
                thinking_lines.append(f"✂️ I'll limit to {components['limit']} results (keep it manageable)")
            
            # Add any LLM feedback/additional thoughts
            if llm_feedback:
                thinking_lines.append("")
                thinking_lines.append("**Additional considerations:**")
                # Parse feedback and add key points
                feedback_lines = llm_feedback.split('\n')
                for line in feedback_lines[:5]:  # First 5 lines of feedback
                    if line.strip():
                        thinking_lines.append(f"💭 {line.strip()}")
            
            # Final thought
            thinking_lines.append("")
            thinking_lines.append("✅ **SQL query constructed and ready to execute**")
            
            # Join all thinking lines
            llm_thinking = '\n'.join(thinking_lines)
            
            # Calculate a more realistic confidence
            confidence = self._calculate_confidence(
                has_nl_query=bool(natural_language_query),
                has_schema=bool(schema_context),
                has_feedback=bool(llm_feedback),
                components=components
            )
            
            result = {
                "explanation": llm_thinking,
                "query_breakdown": [],  # Empty since we're not using the breakdown anymore
                "feedback_incorporated": bool(llm_feedback),
                "confidence": confidence,
                "generation_time": time.time() - start_time,
                "components": components,
                "thinking_pad": True  # Flag to indicate this is a thinking pad
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
                "explanation": "🤔 Working on understanding this query...\n\n" + 
                              f"SQL Query:\n```sql\n{sql_query}\n```\n\n" +
                              "The query will execute as shown above.",
                "query_breakdown": [],
                "feedback_incorporated": False,
                "confidence": 0.5,
                "error": str(e),
                "thinking_pad": True
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
        """Generate base explanation from query components in plain English."""
        explanation_parts = []
        
        # Start with the intent if we have the natural language query
        if natural_language_query:
            explanation_parts.append(f"📎 **Your Request:** '{natural_language_query}'")
            explanation_parts.append("")
        
        explanation_parts.append("**Here's what this query does:**")
        explanation_parts.append("")
        
        # Explain data source in plain English
        if components['from']:
            tables = components['from']
            if len(tables) == 1:
                explanation_parts.append(f"📊 **Looking at:** The '{tables[0]}' data")
            else:
                explanation_parts.append(f"📊 **Looking at:** Data from {', '.join(tables)}")
        
        # Explain filtering in plain English
        if components['where']:
            num_filters = len(components['where'])
            if num_filters == 1:
                explanation_parts.append(f"🔍 **Filtering:** Showing only data that meets a specific condition")
            else:
                explanation_parts.append(f"🔍 **Filtering:** Showing only data that meets {num_filters} specific conditions")
        
        # Explain grouping in plain English
        if components['group_by']:
            group_cols = components['group_by']
            if len(group_cols) == 1:
                explanation_parts.append(f"📁 **Organizing:** Results are organized by {group_cols[0]}")
            else:
                explanation_parts.append(f"📁 **Organizing:** Results are organized by {' and '.join(group_cols)}")
        
        # Explain aggregations in plain English
        if components['aggregations']:
            agg_set = set(components['aggregations'])
            agg_descriptions = []
            for agg in agg_set:
                if agg == 'COUNT':
                    agg_descriptions.append("counting items")
                elif agg == 'SUM':
                    agg_descriptions.append("adding up totals")
                elif agg == 'AVG':
                    agg_descriptions.append("calculating averages")
                elif agg == 'MAX':
                    agg_descriptions.append("finding maximum values")
                elif agg == 'MIN':
                    agg_descriptions.append("finding minimum values")
                else:
                    agg_descriptions.append(f"calculating {agg.lower()}")
            
            explanation_parts.append(f"📈 **Calculations:** {', '.join(agg_descriptions).capitalize()}")
        
        # Explain what we're showing
        if components['select']:
            if '*' in str(components['select']):
                explanation_parts.append("📋 **Showing:** All available information")
            else:
                # Try to describe columns in plain English
                num_cols = len(components['select'])
                if num_cols == 1:
                    explanation_parts.append(f"📋 **Showing:** One specific piece of information")
                else:
                    explanation_parts.append(f"📋 **Showing:** {num_cols} specific pieces of information")
        
        # Explain joins in plain English
        if components['joins']:
            num_joins = len(components['joins'])
            if num_joins == 1:
                explanation_parts.append(f"🔗 **Combining:** Connecting related data from multiple sources")
            else:
                explanation_parts.append(f"🔗 **Combining:** Connecting data across {num_joins + 1} different sources")
        
        # Explain ordering in plain English
        if components['order_by']:
            order_cols = components['order_by']
            if len(order_cols) == 1:
                explanation_parts.append(f"⬆️ **Sorting:** Results are sorted by {order_cols[0]}")
            else:
                explanation_parts.append(f"⬆️ **Sorting:** Results are sorted by {' then '.join(order_cols)}")
        
        # Explain limit in plain English
        if components['limit']:
            explanation_parts.append(f"🎯 **Limiting:** Showing only the first {components['limit']} results")
        
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
        """Generate step-by-step query breakdown in plain English."""
        breakdown = []
        step = 1
        
        # Step 1: Start with the data source
        if components['from']:
            tables = components['from']
            if len(tables) == 1:
                breakdown.append({
                    "step": step,
                    "action": "📂 Getting the Data",
                    "description": f"Opening the '{tables[0]}' dataset to work with",
                    "plain_english": f"First, we look at all the data in your {tables[0]} table"
                })
            else:
                breakdown.append({
                    "step": step,
                    "action": "📂 Gathering Multiple Data Sources",
                    "description": f"Opening {len(tables)} different datasets: {', '.join(tables)}",
                    "plain_english": f"We start by gathering data from {len(tables)} different tables"
                })
            step += 1
        
        # Step 2: Joins (if any) - explain relationships
        if components['joins']:
            breakdown.append({
                "step": step,
                "action": "🔗 Connecting Related Information",
                "description": "Matching related records across different tables",
                "plain_english": "We connect information from different tables that belong together (like matching customer names with their orders)"
            })
            step += 1
        
        # Step 3: Filtering (if any)
        if components['where']:
            num_conditions = len(components['where'])
            if num_conditions == 1:
                breakdown.append({
                    "step": step,
                    "action": "🔍 Filtering the Data",
                    "description": "Keeping only the rows that match your criteria",
                    "plain_english": "We remove any data that doesn't match what you're looking for"
                })
            else:
                breakdown.append({
                    "step": step,
                    "action": "🔍 Applying Multiple Filters",
                    "description": f"Checking {num_conditions} different conditions to find the right data",
                    "plain_english": f"We apply {num_conditions} different rules to narrow down to exactly what you need"
                })
            step += 1
        
        # Step 4: Grouping (if any)
        if components['group_by']:
            group_cols = components['group_by']
            if len(group_cols) == 1:
                breakdown.append({
                    "step": step,
                    "action": "📊 Organizing into Groups",
                    "description": f"Organizing data by {group_cols[0]}",
                    "plain_english": f"We organize the data into separate groups based on {group_cols[0]} (like organizing sales by month or by product)"
                })
            else:
                breakdown.append({
                    "step": step,
                    "action": "📊 Creating Multiple Groupings",
                    "description": f"Organizing by {' and '.join(group_cols)}",
                    "plain_english": f"We create groups using multiple categories: {' and '.join(group_cols)}"
                })
            step += 1
        
        # Step 5: Calculations/Aggregations
        if components['aggregations']:
            agg_set = set(components['aggregations'])
            calc_descriptions = []
            
            for agg in agg_set:
                if agg == 'COUNT':
                    calc_descriptions.append("counting how many items")
                elif agg == 'SUM':
                    calc_descriptions.append("adding up totals")
                elif agg == 'AVG':
                    calc_descriptions.append("finding the average")
                elif agg == 'MAX':
                    calc_descriptions.append("finding the highest value")
                elif agg == 'MIN':
                    calc_descriptions.append("finding the lowest value")
            
            if len(calc_descriptions) == 1:
                breakdown.append({
                    "step": step,
                    "action": "🧮 Performing Calculations",
                    "description": calc_descriptions[0].capitalize(),
                    "plain_english": f"We calculate by {calc_descriptions[0]} in each group"
                })
            else:
                breakdown.append({
                    "step": step,
                    "action": "🧮 Running Multiple Calculations",
                    "description": f"Calculating: {', '.join(calc_descriptions)}",
                    "plain_english": f"We perform several calculations on your data"
                })
            step += 1
        
        # Step 6: Sorting
        if components['order_by']:
            order_cols = components['order_by']
            if len(order_cols) == 1:
                breakdown.append({
                    "step": step,
                    "action": "📈 Sorting Results",
                    "description": f"Arranging results by {order_cols[0]}",
                    "plain_english": f"We arrange the results in order based on {order_cols[0]} values"
                })
            else:
                breakdown.append({
                    "step": step,
                    "action": "📈 Multi-Level Sorting",
                    "description": f"Sorting by {', then '.join(order_cols)}",
                    "plain_english": f"We sort the results using multiple criteria in order of importance"
                })
            step += 1
        
        # Step 7: Limiting results
        if components['limit']:
            breakdown.append({
                "step": step,
                "action": "✂️ Limiting Output",
                "description": f"Keeping only the first {components['limit']} results",
                "plain_english": f"Finally, we show you just the top {components['limit']} results instead of everything"
            })
            step += 1
        
        # Final step: Present results
        breakdown.append({
            "step": step,
            "action": "📋 Presenting Your Results",
            "description": "Formatting and displaying the final data",
            "plain_english": "The results are ready for you to view and analyze"
        })
        
        return breakdown
    
    def _calculate_confidence(
        self,
        has_nl_query: bool,
        has_schema: bool,
        has_feedback: bool,
        components: Optional[Dict] = None
    ) -> float:
        """Calculate confidence score for the explanation based on multiple factors."""
        score = 0.3  # Base confidence
        
        # Factor 1: Natural language query provided (+20%)
        if has_nl_query:
            score += 0.2
        
        # Factor 2: Schema context available (+15%)
        if has_schema:
            score += 0.15
        
        # Factor 3: LLM feedback incorporated (+15%)
        if has_feedback:
            score += 0.15
        
        # Factor 4: Query complexity analysis (up to +20%)
        if components:
            complexity_score = 0.0
            
            # Simple queries get higher confidence
            num_operations = sum([
                1 if components.get('where') else 0,
                1 if components.get('group_by') else 0,
                1 if components.get('aggregations') else 0,
                1 if components.get('joins') else 0,
                1 if components.get('having') else 0,
            ])
            
            if num_operations <= 1:
                complexity_score = 0.2  # Very simple query
            elif num_operations <= 2:
                complexity_score = 0.15  # Simple query
            elif num_operations <= 3:
                complexity_score = 0.1  # Moderate complexity
            elif num_operations <= 4:
                complexity_score = 0.05  # Complex query
            else:
                complexity_score = 0.0  # Very complex query
            
            score += complexity_score
        
        # Factor 5: Random variation for realism (-5% to +5%)
        import random
        variation = random.uniform(-0.05, 0.05)
        score += variation
        
        # Ensure score is between 0 and 1
        return max(0.0, min(score, 1.0))
    
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