"""Advanced filtering UI components for Data Explorer."""

from datetime import date
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st


class AdvancedFilterBuilder:
    """Advanced filter builder with multi-condition support."""

    def __init__(self):
        """Initialize filter builder."""
        self.filters = []
        self.logical_operator = "AND"  # AND or OR

        # Initialize session state
        if "filter_builder_filters" not in st.session_state:
            st.session_state.filter_builder_filters = []
        if "filter_builder_logic" not in st.session_state:
            st.session_state.filter_builder_logic = "AND"

    def render_filter_builder(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Render the advanced filter builder UI.

        Args:
            df: DataFrame to build filters for

        Returns:
            Dictionary containing filter configuration
        """
        st.subheader("🔧 Advanced Filters")

        # Logic operator selection
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            st.session_state.filter_builder_logic = st.selectbox(
                "Filter Logic",
                ["AND", "OR"],
                index=0 if st.session_state.filter_builder_logic == "AND" else 1,
            )

        with col2:
            if st.button("➕ Add Filter"):
                st.session_state.filter_builder_filters.append(
                    {
                        "id": len(st.session_state.filter_builder_filters),
                        "column": df.columns[0],
                        "operator": "equals",
                        "value": "",
                        "data_type": str(df[df.columns[0]].dtype),
                    }
                )
                st.rerun()

        with col3:
            if st.button("🗑️ Clear All Filters"):
                st.session_state.filter_builder_filters = []
                st.rerun()

        # Render individual filters
        filters_to_remove = []
        for i, filter_config in enumerate(st.session_state.filter_builder_filters):
            with st.expander(f"Filter {i+1}", expanded=True):
                filter_config = self._render_single_filter(df, filter_config, i)
                st.session_state.filter_builder_filters[i] = filter_config

                # Remove button
                if st.button(f"Remove Filter {i+1}", key=f"remove_{i}"):
                    filters_to_remove.append(i)

        # Remove filters marked for deletion
        for idx in reversed(filters_to_remove):
            st.session_state.filter_builder_filters.pop(idx)
            st.rerun()

        # Filter templates
        self._render_filter_templates(df)

        # Save/Load functionality
        self._render_save_load_filters()

        return {
            "filters": st.session_state.filter_builder_filters,
            "logic": st.session_state.filter_builder_logic,
        }

    def _render_single_filter(
        self, df: pd.DataFrame, filter_config: Dict, index: int
    ) -> Dict:
        """Render a single filter configuration."""
        col1, col2, col3 = st.columns(3)

        with col1:
            # Column selection
            filter_config["column"] = st.selectbox(
                "Column",
                df.columns.tolist(),
                index=(
                    list(df.columns).index(filter_config["column"])
                    if filter_config["column"] in df.columns
                    else 0
                ),
                key=f"col_{index}",
            )

            # Update data type
            filter_config["data_type"] = str(df[filter_config["column"]].dtype)

        with col2:
            # Operator selection based on data type
            operators = self._get_operators_for_type(filter_config["data_type"])
            current_op = (
                filter_config["operator"]
                if filter_config["operator"] in operators
                else operators[0]
            )
            filter_config["operator"] = st.selectbox(
                "Operator",
                operators,
                index=operators.index(current_op),
                key=f"op_{index}",
            )

        with col3:
            # Value input based on operator and data type
            filter_config["value"] = self._render_value_input(df, filter_config, index)

        return filter_config

    def _render_value_input(self, df: pd.DataFrame, filter_config: Dict, index: int):
        """Render value input based on operator and data type."""
        column = filter_config["column"]
        operator = filter_config["operator"]
        data_type = filter_config["data_type"]
        current_value = filter_config.get("value", "")

        if operator in ["is_null", "is_not_null"]:
            st.write("No value needed")
            return None

        elif operator == "between":
            col1, col2 = st.columns(2)
            with col1:
                if "int" in data_type or "float" in data_type:
                    min_val = st.number_input(
                        "Min",
                        value=(
                            float(df[column].min())
                            if pd.notna(df[column].min())
                            else 0.0
                        ),
                        key=f"min_{index}",
                    )
                else:
                    min_val = st.text_input("Min", key=f"min_{index}")
            with col2:
                if "int" in data_type or "float" in data_type:
                    max_val = st.number_input(
                        "Max",
                        value=(
                            float(df[column].max())
                            if pd.notna(df[column].max())
                            else 0.0
                        ),
                        key=f"max_{index}",
                    )
                else:
                    max_val = st.text_input("Max", key=f"max_{index}")
            return [min_val, max_val]

        elif operator in ["in_list", "not_in_list"]:
            # Multi-select for list values
            unique_values = df[column].dropna().unique().tolist()
            if len(unique_values) <= 50:
                selected = st.multiselect(
                    "Values",
                    unique_values,
                    default=current_value if isinstance(current_value, list) else [],
                    key=f"list_{index}",
                )
                return selected
            else:
                # Text area for manual input
                st.write("Too many unique values. Enter comma-separated values:")
                text_input = st.text_area(
                    "Values (comma-separated)",
                    value=(
                        ", ".join(current_value)
                        if isinstance(current_value, list)
                        else str(current_value)
                    ),
                    key=f"text_list_{index}",
                )
                return [v.strip() for v in text_input.split(",") if v.strip()]

        elif operator == "regex":
            return st.text_input(
                "Regular Expression",
                value=str(current_value),
                key=f"regex_{index}",
                help="Enter a valid regular expression pattern",
            )

        else:
            # Standard single value input
            if "int" in data_type:
                return st.number_input(
                    "Value",
                    value=(
                        int(current_value)
                        if current_value and str(current_value).isdigit()
                        else 0
                    ),
                    step=1,
                    key=f"val_{index}",
                )
            elif "float" in data_type:
                return st.number_input(
                    "Value",
                    value=(
                        float(current_value)
                        if current_value
                        and str(current_value).replace(".", "").isdigit()
                        else 0.0
                    ),
                    key=f"val_{index}",
                )
            elif "datetime" in data_type:
                return st.date_input(
                    "Value",
                    value=(
                        pd.to_datetime(current_value).date()
                        if current_value
                        else date.today()
                    ),
                    key=f"date_{index}",
                )
            elif "bool" in data_type:
                return st.checkbox(
                    "Value",
                    value=bool(current_value) if current_value else False,
                    key=f"bool_{index}",
                )
            else:
                return st.text_input(
                    "Value",
                    value=str(current_value) if current_value else "",
                    key=f"text_{index}",
                )

    def _get_operators_for_type(self, data_type: str) -> List[str]:
        """Get available operators for a data type."""
        base_operators = ["equals", "not_equals", "is_null", "is_not_null"]

        if "int" in data_type or "float" in data_type:
            return base_operators + [
                "greater_than",
                "less_than",
                "greater_equal",
                "less_equal",
                "between",
                "in_list",
                "not_in_list",
            ]
        elif "object" in data_type or "string" in data_type:
            return base_operators + [
                "contains",
                "not_contains",
                "starts_with",
                "ends_with",
                "in_list",
                "not_in_list",
                "regex",
            ]
        elif "datetime" in data_type:
            return base_operators + ["greater_than", "less_than", "between"]
        elif "bool" in data_type:
            return ["equals", "not_equals"]
        else:
            return base_operators

    def _render_filter_templates(self, df: pd.DataFrame):
        """Render filter templates for common patterns."""
        with st.expander("📋 Filter Templates"):
            st.write("Quick filter templates:")

            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("Show Non-Null Only"):
                    self._add_template_filter(df, "non_null")
                    st.rerun()

            with col2:
                if st.button("Show Recent Data"):
                    self._add_template_filter(df, "recent")
                    st.rerun()

            with col3:
                if st.button("Show Top Values"):
                    self._add_template_filter(df, "top_values")
                    st.rerun()

    def _add_template_filter(self, df: pd.DataFrame, template_type: str):
        """Add a predefined filter template."""
        if template_type == "non_null":
            # Add filters to exclude null values for columns with nulls
            for col in df.columns:
                if df[col].isnull().any():
                    st.session_state.filter_builder_filters.append(
                        {
                            "id": len(st.session_state.filter_builder_filters),
                            "column": col,
                            "operator": "is_not_null",
                            "value": None,
                            "data_type": str(df[col].dtype),
                        }
                    )

        elif template_type == "recent":
            # Add filter for recent dates if datetime columns exist
            datetime_cols = df.select_dtypes(include=["datetime64"]).columns
            if len(datetime_cols) > 0:
                col = datetime_cols[0]
                recent_date = df[col].max() - pd.Timedelta(days=30)
                st.session_state.filter_builder_filters.append(
                    {
                        "id": len(st.session_state.filter_builder_filters),
                        "column": col,
                        "operator": "greater_than",
                        "value": recent_date.date(),
                        "data_type": str(df[col].dtype),
                    }
                )

    def _render_save_load_filters(self):
        """Render save/load filter functionality."""
        with st.expander("💾 Save/Load Filters"):
            col1, col2 = st.columns(2)

            with col1:
                filter_name = st.text_input("Filter Set Name")
                if st.button("Save Current Filters") and filter_name:
                    self._save_filter_set(filter_name)
                    st.success(f"Saved filter set: {filter_name}")

            with col2:
                saved_filters = self._get_saved_filter_sets()
                if saved_filters:
                    selected_filter = st.selectbox(
                        "Load Saved Filters", [""] + list(saved_filters.keys())
                    )
                    if st.button("Load Filters") and selected_filter:
                        self._load_filter_set(
                            selected_filter, saved_filters[selected_filter]
                        )
                        st.success(f"Loaded filter set: {selected_filter}")
                        st.rerun()

    def _save_filter_set(self, name: str):
        """Save current filter set to session state."""
        if "saved_filter_sets" not in st.session_state:
            st.session_state.saved_filter_sets = {}

        st.session_state.saved_filter_sets[name] = {
            "filters": st.session_state.filter_builder_filters.copy(),
            "logic": st.session_state.filter_builder_logic,
        }

    def _load_filter_set(self, name: str, filter_set: Dict):
        """Load a saved filter set."""
        st.session_state.filter_builder_filters = filter_set["filters"].copy()
        st.session_state.filter_builder_logic = filter_set["logic"]

    def _get_saved_filter_sets(self) -> Dict:
        """Get saved filter sets from session state."""
        return st.session_state.get("saved_filter_sets", {})

    def apply_filters(
        self, df: pd.DataFrame, filter_config: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        Apply filters to DataFrame.

        Args:
            df: Input DataFrame
            filter_config: Filter configuration from render_filter_builder

        Returns:
            Filtered DataFrame
        """
        if not filter_config["filters"]:
            return df

        conditions = []
        for filter_def in filter_config["filters"]:
            condition = self._build_condition(df, filter_def)
            if condition is not None:
                conditions.append(condition)

        if not conditions:
            return df

        # Combine conditions with logical operator
        if filter_config["logic"] == "AND":
            final_condition = conditions[0]
            for condition in conditions[1:]:
                final_condition = final_condition & condition
        else:  # OR
            final_condition = conditions[0]
            for condition in conditions[1:]:
                final_condition = final_condition | condition

        return df[final_condition]

    def _build_condition(
        self, df: pd.DataFrame, filter_def: Dict
    ) -> Optional[pd.Series]:
        """Build pandas boolean condition from filter definition."""
        column = filter_def["column"]
        operator = filter_def["operator"]
        value = filter_def["value"]

        if column not in df.columns:
            return None

        col_data = df[column]

        try:
            if operator == "equals":
                return col_data == value
            elif operator == "not_equals":
                return col_data != value
            elif operator == "greater_than":
                return col_data > value
            elif operator == "less_than":
                return col_data < value
            elif operator == "greater_equal":
                return col_data >= value
            elif operator == "less_equal":
                return col_data <= value
            elif operator == "between" and isinstance(value, list) and len(value) == 2:
                return (col_data >= value[0]) & (col_data <= value[1])
            elif operator == "contains":
                return col_data.astype(str).str.contains(
                    str(value), na=False, case=False
                )
            elif operator == "not_contains":
                return ~col_data.astype(str).str.contains(
                    str(value), na=False, case=False
                )
            elif operator == "starts_with":
                return col_data.astype(str).str.startswith(str(value), na=False)
            elif operator == "ends_with":
                return col_data.astype(str).str.endswith(str(value), na=False)
            elif operator == "in_list":
                return (
                    col_data.isin(value)
                    if value
                    else pd.Series([False] * len(col_data))
                )
            elif operator == "not_in_list":
                return (
                    ~col_data.isin(value)
                    if value
                    else pd.Series([True] * len(col_data))
                )
            elif operator == "is_null":
                return col_data.isnull()
            elif operator == "is_not_null":
                return col_data.notnull()
            elif operator == "regex":
                return col_data.astype(str).str.match(str(value), na=False)
            else:
                return None
        except Exception as e:
            st.warning(f"Filter error for column {column}: {str(e)}")
            return None

    def to_sql_where_clause(self, filter_config: Dict[str, Any]) -> str:
        """
        Convert filter configuration to SQL WHERE clause.

        Args:
            filter_config: Filter configuration from render_filter_builder

        Returns:
            SQL WHERE clause string
        """
        if not filter_config["filters"]:
            return ""

        conditions = []
        for filter_def in filter_config["filters"]:
            condition = self._build_sql_condition(filter_def)
            if condition:
                conditions.append(condition)

        if not conditions:
            return ""

        # Combine conditions with logical operator
        logic_op = f" {filter_config['logic']} "
        return f"WHERE {logic_op.join(conditions)}"

    def _build_sql_condition(self, filter_def: Dict) -> str:
        """Build SQL condition from filter definition."""
        column = filter_def["column"]
        operator = filter_def["operator"]
        value = filter_def["value"]

        # Escape column name if needed
        column_escaped = f'"{column}"' if " " in column else column

        if operator == "equals":
            return f"{column_escaped} = '{value}'"
        elif operator == "not_equals":
            return f"{column_escaped} != '{value}'"
        elif operator == "greater_than":
            return f"{column_escaped} > '{value}'"
        elif operator == "less_than":
            return f"{column_escaped} < '{value}'"
        elif operator == "greater_equal":
            return f"{column_escaped} >= '{value}'"
        elif operator == "less_equal":
            return f"{column_escaped} <= '{value}'"
        elif operator == "between" and isinstance(value, list) and len(value) == 2:
            return f"{column_escaped} BETWEEN '{value[0]}' AND '{value[1]}'"
        elif operator == "contains":
            return f"{column_escaped} LIKE '%{value}%'"
        elif operator == "not_contains":
            return f"{column_escaped} NOT LIKE '%{value}%'"
        elif operator == "starts_with":
            return f"{column_escaped} LIKE '{value}%'"
        elif operator == "ends_with":
            return f"{column_escaped} LIKE '%{value}'"
        elif operator == "in_list":
            values = "', '".join([str(v) for v in value])
            return f"{column_escaped} IN ('{values}')"
        elif operator == "not_in_list":
            values = "', '".join([str(v) for v in value])
            return f"{column_escaped} NOT IN ('{values}')"
        elif operator == "is_null":
            return f"{column_escaped} IS NULL"
        elif operator == "is_not_null":
            return f"{column_escaped} IS NOT NULL"
        elif operator == "regex":
            return f"{column_escaped} ~ '{value}'"
        else:
            return ""
