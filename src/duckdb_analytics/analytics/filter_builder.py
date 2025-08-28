"""Interactive Filter and Aggregation Builder for DuckDB Analytics Dashboard."""

import streamlit as st
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class OperatorType(Enum):
    """SQL operators for filtering."""
    EQUALS = "="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    GREATER_THAN_EQUAL = ">="
    LESS_THAN = "<"
    LESS_THAN_EQUAL = "<="
    LIKE = "LIKE"
    NOT_LIKE = "NOT LIKE"
    IN = "IN"
    NOT_IN = "NOT IN"
    IS_NULL = "IS NULL"
    IS_NOT_NULL = "IS NOT NULL"
    BETWEEN = "BETWEEN"
    STARTS_WITH = "STARTS_WITH"
    ENDS_WITH = "ENDS_WITH"
    CONTAINS = "CONTAINS"

class AggregationFunction(Enum):
    """SQL aggregation functions."""
    COUNT = "COUNT"
    COUNT_DISTINCT = "COUNT(DISTINCT {})"
    SUM = "SUM"
    AVG = "AVG"
    MIN = "MIN"
    MAX = "MAX"
    STDDEV = "STDDEV"
    VARIANCE = "VARIANCE"
    MEDIAN = "MEDIAN"

@dataclass
class FilterCondition:
    """Represents a single filter condition."""
    column: str
    operator: OperatorType
    value: Union[str, int, float, List[Any], None]
    value2: Optional[Union[str, int, float]] = None  # For BETWEEN operator
    logic: str = "AND"  # AND or OR

@dataclass
class AggregationSpec:
    """Represents an aggregation specification."""
    column: str
    function: AggregationFunction
    alias: Optional[str] = None

@dataclass
class GroupBySpec:
    """Represents a GROUP BY specification."""
    columns: List[str]
    having_conditions: List[FilterCondition] = None

class FilterBuilder:
    """Interactive visual filter and aggregation builder."""
    
    def __init__(self, db_connection, available_columns: List[Dict[str, Any]]):
        self.db_connection = db_connection
        self.available_columns = available_columns
        self.column_names = [col['name'] for col in available_columns]
        self.column_types = {col['name']: col.get('type', '').lower() for col in available_columns}
        
    def render(self, table_name: str) -> Dict[str, Any]:
        """Render the interactive filter builder interface."""
        st.subheader("🔧 Interactive Filter & Aggregation Builder")
        
        # Initialize session state
        if f"filter_conditions_{table_name}" not in st.session_state:
            st.session_state[f"filter_conditions_{table_name}"] = []
        if f"aggregations_{table_name}" not in st.session_state:
            st.session_state[f"aggregations_{table_name}"] = []
        if f"group_by_columns_{table_name}" not in st.session_state:
            st.session_state[f"group_by_columns_{table_name}"] = []
            
        # Create tabs for different builder sections
        filter_tab, agg_tab, query_tab = st.tabs(["🔍 Filters", "📊 Aggregations", "📝 Generated Query"])
        
        with filter_tab:
            self._render_filter_section(table_name)
            
        with agg_tab:
            self._render_aggregation_section(table_name)
            
        with query_tab:
            query_result = self._render_query_section(table_name)
            
        return query_result
        
    def _render_filter_section(self, table_name: str):
        """Render the filter conditions section."""
        st.write("### Filter Conditions")
        
        conditions = st.session_state[f"filter_conditions_{table_name}"]
        
        # Display existing conditions
        for i, condition in enumerate(conditions):
            self._render_filter_condition(table_name, i, condition)
            
        # Add new condition button
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("➕ Add Filter Condition", key=f"add_filter_{table_name}"):
                new_condition = FilterCondition(
                    column=self.column_names[0] if self.column_names else "",
                    operator=OperatorType.EQUALS,
                    value=None
                )
                st.session_state[f"filter_conditions_{table_name}"].append(new_condition)
                st.rerun()
                
        with col2:
            if conditions and st.button("🗑️ Clear All Filters", key=f"clear_filters_{table_name}"):
                st.session_state[f"filter_conditions_{table_name}"] = []
                st.rerun()
                
    def _render_filter_condition(self, table_name: str, index: int, condition: FilterCondition):
        """Render a single filter condition."""
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([2, 1, 2, 1, 1])
            
            with col1:
                # Column selector
                column_idx = self.column_names.index(condition.column) if condition.column in self.column_names else 0
                selected_column = st.selectbox(
                    "Column",
                    self.column_names,
                    index=column_idx,
                    key=f"filter_col_{table_name}_{index}"
                )
                condition.column = selected_column
                
            with col2:
                # Operator selector based on column type
                operators = self._get_operators_for_column(selected_column)
                operator_values = [op.value for op in operators]
                
                try:
                    operator_idx = operator_values.index(condition.operator.value)
                except (ValueError, AttributeError):
                    operator_idx = 0
                    
                selected_operator = st.selectbox(
                    "Operator",
                    operator_values,
                    index=operator_idx,
                    key=f"filter_op_{table_name}_{index}"
                )
                condition.operator = OperatorType(selected_operator)
                
            with col3:
                # Value input based on operator and column type
                condition.value = self._render_value_input(
                    selected_column, condition.operator, condition.value,
                    f"filter_val_{table_name}_{index}"
                )
                
                # Second value for BETWEEN operator
                if condition.operator == OperatorType.BETWEEN:
                    condition.value2 = st.number_input(
                        "And",
                        value=condition.value2 or 0,
                        key=f"filter_val2_{table_name}_{index}"
                    )
                    
            with col4:
                # Logic connector (except for last condition)
                if index > 0:
                    condition.logic = st.selectbox(
                        "Logic",
                        ["AND", "OR"],
                        index=0 if condition.logic == "AND" else 1,
                        key=f"filter_logic_{table_name}_{index}"
                    )
                    
            with col5:
                # Remove condition button
                if st.button("🗑️", key=f"remove_filter_{table_name}_{index}"):
                    conditions = st.session_state[f"filter_conditions_{table_name}"]
                    conditions.pop(index)
                    st.session_state[f"filter_conditions_{table_name}"] = conditions
                    st.rerun()
                    
        st.divider()
        
    def _render_aggregation_section(self, table_name: str):
        """Render the aggregation section."""
        st.write("### Aggregations & Grouping")
        
        # Group By section
        st.write("#### Group By Columns")
        selected_group_cols = st.multiselect(
            "Select columns to group by",
            self.column_names,
            default=st.session_state[f"group_by_columns_{table_name}"],
            key=f"group_by_{table_name}"
        )
        st.session_state[f"group_by_columns_{table_name}"] = selected_group_cols
        
        # Aggregations section
        st.write("#### Aggregation Functions")
        aggregations = st.session_state[f"aggregations_{table_name}"]
        
        # Display existing aggregations
        for i, agg in enumerate(aggregations):
            self._render_aggregation_spec(table_name, i, agg)
            
        # Add new aggregation button
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("➕ Add Aggregation", key=f"add_agg_{table_name}"):
                new_agg = AggregationSpec(
                    column=self.column_names[0] if self.column_names else "",
                    function=AggregationFunction.COUNT
                )
                st.session_state[f"aggregations_{table_name}"].append(new_agg)
                st.rerun()
                
        with col2:
            if aggregations and st.button("🗑️ Clear All Aggregations", key=f"clear_aggs_{table_name}"):
                st.session_state[f"aggregations_{table_name}"] = []
                st.rerun()
                
    def _render_aggregation_spec(self, table_name: str, index: int, agg: AggregationSpec):
        """Render a single aggregation specification."""
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            
            with col1:
                # Column selector (only numeric columns for most functions)
                available_cols = self._get_columns_for_aggregation(agg.function)
                if agg.column not in available_cols and available_cols:
                    agg.column = available_cols[0]
                    
                column_idx = available_cols.index(agg.column) if agg.column in available_cols else 0
                selected_column = st.selectbox(
                    "Column",
                    available_cols,
                    index=column_idx,
                    key=f"agg_col_{table_name}_{index}"
                )
                agg.column = selected_column
                
            with col2:
                # Function selector
                func_values = [f.name for f in AggregationFunction]
                try:
                    func_idx = func_values.index(agg.function.name)
                except (ValueError, AttributeError):
                    func_idx = 0
                    
                selected_function = st.selectbox(
                    "Function",
                    func_values,
                    index=func_idx,
                    key=f"agg_func_{table_name}_{index}"
                )
                agg.function = AggregationFunction[selected_function]
                
                # Update available columns when function changes
                available_cols = self._get_columns_for_aggregation(agg.function)
                if agg.column not in available_cols and available_cols:
                    agg.column = available_cols[0]
                    
            with col3:
                # Alias input
                agg.alias = st.text_input(
                    "Alias",
                    value=agg.alias or f"{agg.function.name.lower()}_{agg.column}",
                    key=f"agg_alias_{table_name}_{index}"
                )
                
            with col4:
                # Remove aggregation button
                if st.button("🗑️", key=f"remove_agg_{table_name}_{index}"):
                    aggregations = st.session_state[f"aggregations_{table_name}"]
                    aggregations.pop(index)
                    st.session_state[f"aggregations_{table_name}"] = aggregations
                    st.rerun()
                    
        st.divider()
        
    def _render_query_section(self, table_name: str) -> Dict[str, Any]:
        """Render the generated query section."""
        st.write("### Generated Query")
        
        try:
            # Generate SQL query
            query = self.build_query(table_name)
            
            # Display query
            st.code(query, language="sql")
            
            # Query explanation
            with st.expander("📖 Query Explanation"):
                explanation = self._explain_query(table_name)
                st.markdown(explanation)
                
            # Execute query button
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("▶️ Execute Query", key=f"execute_builder_{table_name}", type="primary"):
                    return self._execute_query(query)
                    
            with col2:
                if st.button("📋 Copy to Editor", key=f"copy_builder_{table_name}"):
                    st.session_state.editor_sql = query
                    st.success("✅ Query copied to SQL editor")
                    
        except Exception as e:
            st.error(f"❌ Error generating query: {str(e)}")
            
        return {"success": False, "error": "No query executed"}
        
    def build_query(self, table_name: str) -> str:
        """Build SQL query from current filter and aggregation settings."""
        conditions = st.session_state[f"filter_conditions_{table_name}"]
        aggregations = st.session_state[f"aggregations_{table_name}"]
        group_by_cols = st.session_state[f"group_by_columns_{table_name}"]
        
        # Build SELECT clause
        select_parts = []
        
        # Add group by columns
        if group_by_cols:
            select_parts.extend(group_by_cols)
            
        # Add aggregations
        for agg in aggregations:
            if agg.function == AggregationFunction.COUNT_DISTINCT:
                agg_sql = agg.function.value.format(agg.column)
            else:
                agg_sql = f"{agg.function.value}({agg.column})"
                
            if agg.alias:
                agg_sql += f" AS {agg.alias}"
                
            select_parts.append(agg_sql)
            
        # Default to SELECT * if no specific selections
        if not select_parts:
            select_clause = "*"
        else:
            select_clause = ",\n    ".join(select_parts)
            
        # Build WHERE clause
        where_clause = ""
        if conditions:
            where_parts = []
            for i, condition in enumerate(conditions):
                condition_sql = self._build_condition_sql(condition)
                if i > 0:
                    condition_sql = f"{condition.logic} {condition_sql}"
                where_parts.append(condition_sql)
            where_clause = f"WHERE {' '.join(where_parts)}"
            
        # Build GROUP BY clause
        group_by_clause = ""
        if group_by_cols:
            group_by_clause = f"GROUP BY {', '.join(group_by_cols)}"
            
        # Assemble full query
        query_parts = [
            f"SELECT {select_clause}",
            f"FROM {table_name}"
        ]
        
        if where_clause:
            query_parts.append(where_clause)
            
        if group_by_clause:
            query_parts.append(group_by_clause)
            
        # Add ORDER BY if group by is used
        if group_by_cols:
            query_parts.append(f"ORDER BY {', '.join(group_by_cols)}")
            
        return "\n".join(query_parts)
        
    def _build_condition_sql(self, condition: FilterCondition) -> str:
        """Build SQL for a single condition."""
        column = condition.column
        operator = condition.operator
        value = condition.value
        
        if operator == OperatorType.IS_NULL:
            return f"{column} IS NULL"
        elif operator == OperatorType.IS_NOT_NULL:
            return f"{column} IS NOT NULL"
        elif operator == OperatorType.BETWEEN:
            return f"{column} BETWEEN {self._format_value(value)} AND {self._format_value(condition.value2)}"
        elif operator == OperatorType.IN:
            if isinstance(value, list):
                formatted_values = [self._format_value(v) for v in value]
                return f"{column} IN ({', '.join(formatted_values)})"
            else:
                return f"{column} IN ({self._format_value(value)})"
        elif operator == OperatorType.NOT_IN:
            if isinstance(value, list):
                formatted_values = [self._format_value(v) for v in value]
                return f"{column} NOT IN ({', '.join(formatted_values)})"
            else:
                return f"{column} NOT IN ({self._format_value(value)})"
        elif operator == OperatorType.STARTS_WITH:
            return f"{column} LIKE {self._format_value(f'{value}%')}"
        elif operator == OperatorType.ENDS_WITH:
            return f"{column} LIKE {self._format_value(f'%{value}')}"
        elif operator == OperatorType.CONTAINS:
            return f"{column} LIKE {self._format_value(f'%{value}%')}"
        else:
            return f"{column} {operator.value} {self._format_value(value)}"
            
    def _format_value(self, value: Any) -> str:
        """Format value for SQL query."""
        if value is None:
            return "NULL"
        elif isinstance(value, str):
            # Escape single quotes
            escaped_value = value.replace("'", "''")
            return f"'{escaped_value}'"
        else:
            return str(value)
            
    def _get_operators_for_column(self, column: str) -> List[OperatorType]:
        """Get appropriate operators for a column type."""
        col_type = self.column_types.get(column, '').lower()
        
        base_operators = [
            OperatorType.EQUALS,
            OperatorType.NOT_EQUALS,
            OperatorType.IS_NULL,
            OperatorType.IS_NOT_NULL
        ]
        
        if any(t in col_type for t in ['int', 'float', 'double', 'decimal', 'numeric']):
            # Numeric operators
            return base_operators + [
                OperatorType.GREATER_THAN,
                OperatorType.GREATER_THAN_EQUAL,
                OperatorType.LESS_THAN,
                OperatorType.LESS_THAN_EQUAL,
                OperatorType.BETWEEN,
                OperatorType.IN,
                OperatorType.NOT_IN
            ]
        elif any(t in col_type for t in ['varchar', 'text', 'string', 'char']):
            # Text operators
            return base_operators + [
                OperatorType.LIKE,
                OperatorType.NOT_LIKE,
                OperatorType.STARTS_WITH,
                OperatorType.ENDS_WITH,
                OperatorType.CONTAINS,
                OperatorType.IN,
                OperatorType.NOT_IN
            ]
        elif any(t in col_type for t in ['date', 'time', 'timestamp']):
            # Date operators
            return base_operators + [
                OperatorType.GREATER_THAN,
                OperatorType.GREATER_THAN_EQUAL,
                OperatorType.LESS_THAN,
                OperatorType.LESS_THAN_EQUAL,
                OperatorType.BETWEEN
            ]
        else:
            return base_operators + [OperatorType.IN, OperatorType.NOT_IN]
            
    def _render_value_input(self, column: str, operator: OperatorType, current_value: Any, key: str) -> Any:
        """Render appropriate input widget for value based on column type and operator."""
        if operator in [OperatorType.IS_NULL, OperatorType.IS_NOT_NULL]:
            return None
            
        col_type = self.column_types.get(column, '').lower()
        
        if operator in [OperatorType.IN, OperatorType.NOT_IN]:
            # Multi-value input
            value_text = st.text_input(
                "Values (comma-separated)",
                value=', '.join(map(str, current_value)) if isinstance(current_value, list) else str(current_value or ''),
                key=key
            )
            if value_text:
                try:
                    # Try to parse as numbers if numeric column
                    if any(t in col_type for t in ['int', 'float', 'double', 'decimal', 'numeric']):
                        return [float(v.strip()) if '.' in v.strip() else int(v.strip()) for v in value_text.split(',')]
                    else:
                        return [v.strip() for v in value_text.split(',')]
                except ValueError:
                    return [v.strip() for v in value_text.split(',')]
            return []
            
        elif any(t in col_type for t in ['int', 'float', 'double', 'decimal', 'numeric']):
            # Numeric input
            return st.number_input(
                "Value",
                value=current_value or 0,
                key=key
            )
        elif any(t in col_type for t in ['date', 'time', 'timestamp']):
            # Date input
            return st.date_input(
                "Value",
                value=current_value,
                key=key
            )
        else:
            # Text input
            return st.text_input(
                "Value",
                value=current_value or '',
                key=key
            )
            
    def _get_columns_for_aggregation(self, function: AggregationFunction) -> List[str]:
        """Get appropriate columns for aggregation function."""
        if function == AggregationFunction.COUNT:
            return ["*"] + self.column_names
        elif function in [AggregationFunction.COUNT_DISTINCT]:
            return self.column_names
        else:
            # Numeric functions only work on numeric columns
            numeric_columns = [
                col for col, col_type in self.column_types.items()
                if any(t in col_type for t in ['int', 'float', 'double', 'decimal', 'numeric'])
            ]
            return numeric_columns if numeric_columns else self.column_names
            
    def _explain_query(self, table_name: str) -> str:
        """Generate human-readable explanation of the query."""
        conditions = st.session_state[f"filter_conditions_{table_name}"]
        aggregations = st.session_state[f"aggregations_{table_name}"]
        group_by_cols = st.session_state[f"group_by_columns_{table_name}"]
        
        explanation = []
        
        # Describe what we're selecting
        if not aggregations and not group_by_cols:
            explanation.append("📄 **Selecting all columns** from the table")
        else:
            if group_by_cols:
                explanation.append(f"📊 **Grouping data by**: {', '.join(group_by_cols)}")
            if aggregations:
                agg_descriptions = []
                for agg in aggregations:
                    agg_descriptions.append(f"{agg.function.name}({agg.column})")
                explanation.append(f"🔢 **Calculating**: {', '.join(agg_descriptions)}")
                
        # Describe filters
        if conditions:
            filter_descriptions = []
            for condition in conditions:
                if condition.operator == OperatorType.IS_NULL:
                    filter_descriptions.append(f"{condition.column} is empty")
                elif condition.operator == OperatorType.IS_NOT_NULL:
                    filter_descriptions.append(f"{condition.column} is not empty")
                elif condition.operator == OperatorType.BETWEEN:
                    filter_descriptions.append(f"{condition.column} is between {condition.value} and {condition.value2}")
                else:
                    filter_descriptions.append(f"{condition.column} {condition.operator.value} {condition.value}")
            explanation.append(f"🔍 **Filtering where**: {' and '.join(filter_descriptions)}")
            
        # Describe ordering
        if group_by_cols:
            explanation.append(f"📈 **Ordered by**: {', '.join(group_by_cols)}")
            
        return "\n\n".join(explanation)
        
    def _execute_query(self, query: str) -> Dict[str, Any]:
        """Execute the generated query."""
        try:
            # Import here to avoid circular imports
            import time
            from src.duckdb_analytics.core.query_engine import QueryEngine
            
            # Get query engine from session state or create new one
            if hasattr(st.session_state, 'query_engine'):
                query_engine = st.session_state.query_engine
            else:
                query_engine = QueryEngine(self.db_connection)
                
            start_time = time.time()
            df = query_engine.execute_query(query)
            execution_time = time.time() - start_time
            
            # Store results in session state
            st.session_state.query_result = df
            st.session_state.execution_time = execution_time
            
            st.success(f"✅ Query executed successfully in {execution_time:.3f}s")
            st.dataframe(df, use_container_width=True)
            
            return {
                "success": True,
                "data": df,
                "execution_time": execution_time,
                "query": query
            }
            
        except Exception as e:
            st.error(f"❌ Query execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }