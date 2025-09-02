"""Column-level search and filtering components."""

import re
from datetime import date
from typing import Any, Dict, List, Union

import pandas as pd
import streamlit as st


class ColumnSearchManager:
    """Manages column-level search functionality."""

    def __init__(self):
        """Initialize column search manager."""
        # Initialize session state
        if "column_searches" not in st.session_state:
            st.session_state.column_searches = {}
        if "column_search_history" not in st.session_state:
            st.session_state.column_search_history = {}

    def render_column_searches(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Render column-level search interface.

        Args:
            df: DataFrame to search in

        Returns:
            Dictionary of column search configurations
        """
        st.subheader("🔍 Column-Level Search")

        # Global search options
        col1, col2, col3 = st.columns(3)
        with col1:
            case_sensitive = st.checkbox("Case Sensitive", value=False)
        with col2:
            highlight_results = st.checkbox("Highlight Results", value=True)
        with col3:
            show_suggestions = st.checkbox("Show Suggestions", value=True)

        # Search performance indicator
        if len(df) > 10000:
            st.info(
                f"⚡ Searching in {len(df):,} rows. Large datasets may take longer."
            )

        # Column search containers
        search_configs = {}
        columns_to_search = st.multiselect(
            "Select columns to search",
            df.columns.tolist(),
            default=list(st.session_state.column_searches.keys())[
                :5
            ],  # Limit default selection
        )

        if columns_to_search:
            # Create tabs for each column type
            numeric_cols = [
                col
                for col in columns_to_search
                if pd.api.types.is_numeric_dtype(df[col])
            ]
            text_cols = [
                col
                for col in columns_to_search
                if pd.api.types.is_string_dtype(df[col])
            ]
            date_cols = [
                col
                for col in columns_to_search
                if pd.api.types.is_datetime64_any_dtype(df[col])
            ]
            bool_cols = [
                col for col in columns_to_search if pd.api.types.is_bool_dtype(df[col])
            ]

            tabs = []
            tab_names = []

            if text_cols:
                tabs.append("text")
                tab_names.append(f"📝 Text ({len(text_cols)})")
            if numeric_cols:
                tabs.append("numeric")
                tab_names.append(f"🔢 Numeric ({len(numeric_cols)})")
            if date_cols:
                tabs.append("date")
                tab_names.append(f"📅 Date ({len(date_cols)})")
            if bool_cols:
                tabs.append("bool")
                tab_names.append(f"✅ Boolean ({len(bool_cols)})")

            if tabs:
                tab_containers = st.tabs(tab_names)

                for i, tab_type in enumerate(tabs):
                    with tab_containers[i]:
                        if tab_type == "text":
                            search_configs.update(
                                self._render_text_searches(
                                    df, text_cols, case_sensitive, show_suggestions
                                )
                            )
                        elif tab_type == "numeric":
                            search_configs.update(
                                self._render_numeric_searches(df, numeric_cols)
                            )
                        elif tab_type == "date":
                            search_configs.update(
                                self._render_date_searches(df, date_cols)
                            )
                        elif tab_type == "bool":
                            search_configs.update(
                                self._render_bool_searches(df, bool_cols)
                            )

        # Search history
        self._render_search_history()

        # Performance indicators
        if search_configs:
            active_searches = sum(
                1 for config in search_configs.values() if config.get("active", False)
            )
            st.caption(f"Active searches: {active_searches}/{len(search_configs)}")

        return {
            "searches": search_configs,
            "options": {
                "case_sensitive": case_sensitive,
                "highlight_results": highlight_results,
                "show_suggestions": show_suggestions,
            },
        }

    def _render_text_searches(
        self,
        df: pd.DataFrame,
        columns: List[str],
        case_sensitive: bool,
        show_suggestions: bool,
    ) -> Dict[str, Any]:
        """Render text column search interfaces."""
        text_searches = {}

        for col in columns:
            with st.expander(f"Search in '{col}'", expanded=len(columns) <= 3):
                col1, col2 = st.columns([2, 1])

                with col1:
                    # Search input
                    search_key = f"text_search_{col}"
                    current_search = st.session_state.column_searches.get(col, {}).get(
                        "value", ""
                    )

                    search_value = st.text_input(
                        f"Search {col}",
                        value=current_search,
                        key=search_key,
                        placeholder="Enter search term...",
                    )

                with col2:
                    # Search type
                    search_type = st.selectbox(
                        "Type",
                        ["Contains", "Exact", "Starts with", "Ends with", "Regex"],
                        key=f"type_{col}",
                    )

                # Fuzzy matching option
                if search_type in ["Contains", "Starts with", "Ends with"]:
                    fuzzy_threshold = st.slider(
                        "Fuzzy matching threshold (0=exact, 1=very loose)",
                        0.0,
                        1.0,
                        0.0,
                        0.1,
                        key=f"fuzzy_{col}",
                    )
                else:
                    fuzzy_threshold = 0.0

                # Suggestions
                if show_suggestions and search_value:
                    suggestions = self._get_text_suggestions(
                        df[col], search_value, case_sensitive
                    )
                    if suggestions:
                        st.write("💡 Suggestions:")
                        suggestion_cols = st.columns(min(3, len(suggestions)))
                        for i, suggestion in enumerate(suggestions[:3]):
                            with suggestion_cols[i]:
                                if st.button(
                                    f"'{suggestion}'", key=f"suggest_{col}_{i}"
                                ):
                                    st.session_state[search_key] = suggestion
                                    st.rerun()

                # Value frequency analysis
                if search_value:
                    matches = self._apply_text_search(
                        df[col],
                        search_value,
                        search_type,
                        case_sensitive,
                        fuzzy_threshold,
                    )
                    match_count = matches.sum()
                    st.caption(
                        f"Found {match_count:,} matches ({match_count/len(df)*100:.1f}% of rows)"
                    )

                text_searches[col] = {
                    "type": "text",
                    "value": search_value,
                    "search_type": search_type,
                    "case_sensitive": case_sensitive,
                    "fuzzy_threshold": fuzzy_threshold,
                    "active": bool(search_value.strip()),
                }

        return text_searches

    def _render_numeric_searches(
        self, df: pd.DataFrame, columns: List[str]
    ) -> Dict[str, Any]:
        """Render numeric column search interfaces."""
        numeric_searches = {}

        for col in columns:
            with st.expander(f"Search in '{col}'", expanded=len(columns) <= 3):
                col_data = df[col].dropna()
                min_val = float(col_data.min()) if not col_data.empty else 0.0
                max_val = float(col_data.max()) if not col_data.empty else 0.0

                # Search type
                search_type = st.selectbox(
                    "Search Type",
                    [
                        "Range",
                        "Exact Value",
                        "Greater Than",
                        "Less Than",
                        "Top N Values",
                        "Bottom N Values",
                    ],
                    key=f"num_type_{col}",
                )

                if search_type == "Range":
                    col1, col2 = st.columns(2)
                    with col1:
                        range_min = st.number_input(
                            "Min Value", value=min_val, key=f"range_min_{col}"
                        )
                    with col2:
                        range_max = st.number_input(
                            "Max Value", value=max_val, key=f"range_max_{col}"
                        )
                    search_value = [range_min, range_max]

                elif search_type == "Exact Value":
                    search_value = st.number_input(
                        "Exact Value", value=(min_val + max_val) / 2, key=f"exact_{col}"
                    )

                elif search_type in ["Greater Than", "Less Than"]:
                    search_value = st.number_input(
                        "Threshold Value",
                        value=(min_val + max_val) / 2,
                        key=f"threshold_{col}",
                    )

                elif search_type in ["Top N Values", "Bottom N Values"]:
                    n_values = st.number_input(
                        "Number of values",
                        min_value=1,
                        max_value=len(col_data.unique()),
                        value=min(10, len(col_data.unique())),
                        key=f"n_{col}",
                    )

                    # Show the actual threshold values
                    if search_type == "Top N Values":
                        threshold = col_data.nlargest(int(n_values)).min()
                        st.caption(f"Will show values ≥ {threshold}")
                    else:
                        threshold = col_data.nsmallest(int(n_values)).max()
                        st.caption(f"Will show values ≤ {threshold}")

                    search_value = int(n_values)

                # Statistics display
                if search_value is not None:
                    matches = self._apply_numeric_search(
                        col_data, search_value, search_type
                    )
                    if hasattr(matches, "sum"):
                        match_count = matches.sum()
                        st.caption(
                            f"Found {match_count:,} matches ({match_count/len(df)*100:.1f}% of rows)"
                        )

                numeric_searches[col] = {
                    "type": "numeric",
                    "value": search_value,
                    "search_type": search_type,
                    "active": search_value is not None,
                }

        return numeric_searches

    def _render_date_searches(
        self, df: pd.DataFrame, columns: List[str]
    ) -> Dict[str, Any]:
        """Render date column search interfaces."""
        date_searches = {}

        for col in columns:
            with st.expander(f"Search in '{col}'", expanded=len(columns) <= 3):
                col_data = df[col].dropna()

                # Search type
                search_type = st.selectbox(
                    "Search Type",
                    ["Date Range", "Specific Date", "Relative Date", "Date Part"],
                    key=f"date_type_{col}",
                )

                if search_type == "Date Range":
                    col1, col2 = st.columns(2)
                    with col1:
                        start_date = st.date_input(
                            "Start Date",
                            value=(
                                pd.to_datetime(col_data.min()).date()
                                if not col_data.empty
                                else date.today()
                            ),
                            key=f"start_{col}",
                        )
                    with col2:
                        end_date = st.date_input(
                            "End Date",
                            value=(
                                pd.to_datetime(col_data.max()).date()
                                if not col_data.empty
                                else date.today()
                            ),
                            key=f"end_{col}",
                        )
                    search_value = [start_date, end_date]

                elif search_type == "Specific Date":
                    search_value = st.date_input(
                        "Select Date",
                        value=(
                            pd.to_datetime(col_data.median()).date()
                            if not col_data.empty
                            else date.today()
                        ),
                        key=f"specific_{col}",
                    )

                elif search_type == "Relative Date":
                    relative_type = st.selectbox(
                        "Relative to",
                        [
                            "Today",
                            "This Week",
                            "This Month",
                            "This Year",
                            "Last N Days",
                        ],
                        key=f"relative_type_{col}",
                    )

                    if relative_type == "Last N Days":
                        n_days = st.number_input(
                            "Number of days", min_value=1, value=30, key=f"n_days_{col}"
                        )
                        search_value = (relative_type, n_days)
                    else:
                        search_value = (relative_type, None)

                elif search_type == "Date Part":
                    date_part = st.selectbox(
                        "Date Part",
                        ["Year", "Month", "Day", "Weekday", "Quarter"],
                        key=f"date_part_{col}",
                    )

                    part_value = st.number_input(
                        f"{date_part} Value",
                        min_value=1,
                        max_value=(
                            12
                            if date_part == "Month"
                            else (7 if date_part == "Weekday" else 31)
                        ),
                        value=1,
                        key=f"part_value_{col}",
                    )
                    search_value = (date_part, part_value)

                # Match count
                if search_value is not None:
                    matches = self._apply_date_search(
                        col_data, search_value, search_type
                    )
                    if hasattr(matches, "sum"):
                        match_count = matches.sum()
                        st.caption(
                            f"Found {match_count:,} matches ({match_count/len(df)*100:.1f}% of rows)"
                        )

                date_searches[col] = {
                    "type": "date",
                    "value": search_value,
                    "search_type": search_type,
                    "active": search_value is not None,
                }

        return date_searches

    def _render_bool_searches(
        self, df: pd.DataFrame, columns: List[str]
    ) -> Dict[str, Any]:
        """Render boolean column search interfaces."""
        bool_searches = {}

        for col in columns:
            with st.expander(f"Filter '{col}'", expanded=len(columns) <= 3):
                col_data = df[col]

                # Show distribution
                true_count = col_data.sum()
                false_count = len(col_data) - true_count - col_data.isnull().sum()
                null_count = col_data.isnull().sum()

                st.write(
                    f"**Distribution:** ✅ {true_count:,} True | ❌ {false_count:,} False | ❓ {null_count:,} Null"
                )

                # Filter options
                show_true = st.checkbox(
                    "Show True values", value=True, key=f"true_{col}"
                )
                show_false = st.checkbox(
                    "Show False values", value=True, key=f"false_{col}"
                )
                show_null = st.checkbox(
                    "Show Null values", value=True, key=f"null_{col}"
                )

                bool_searches[col] = {
                    "type": "boolean",
                    "value": {
                        "show_true": show_true,
                        "show_false": show_false,
                        "show_null": show_null,
                    },
                    "search_type": "filter",
                    "active": not (show_true and show_false and show_null),
                }

        return bool_searches

    def _render_search_history(self):
        """Render search history interface."""
        if st.session_state.column_search_history:
            with st.expander("📈 Search History"):
                history_items = list(st.session_state.column_search_history.items())[
                    -10:
                ]  # Last 10 items

                for timestamp, search_data in reversed(history_items):
                    col1, col2, col3 = st.columns([2, 2, 1])

                    with col1:
                        st.write(f"**{search_data['column']}:** {search_data['value']}")
                    with col2:
                        st.caption(f"{search_data['type']} - {timestamp}")
                    with col3:
                        if st.button("Reuse", key=f"reuse_{timestamp}"):
                            # Restore search
                            st.session_state.column_searches[search_data["column"]] = (
                                search_data
                            )
                            st.rerun()

    def _get_text_suggestions(
        self, series: pd.Series, search_term: str, case_sensitive: bool
    ) -> List[str]:
        """Get text suggestions based on search term."""
        if not search_term:
            return []

        unique_values = series.astype(str).unique()

        if not case_sensitive:
            search_term = search_term.lower()
            matches = [
                val
                for val in unique_values
                if search_term in str(val).lower()
                and str(val).lower() != search_term.lower()
            ]
        else:
            matches = [
                val
                for val in unique_values
                if search_term in str(val) and str(val) != search_term
            ]

        # Sort by similarity (length difference as proxy)
        matches.sort(key=lambda x: abs(len(str(x)) - len(search_term)))

        return matches[:5]  # Return top 5 suggestions

    def apply_column_searches(
        self, df: pd.DataFrame, search_config: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        Apply column searches to DataFrame.

        Args:
            df: Input DataFrame
            search_config: Search configuration from render_column_searches

        Returns:
            Filtered DataFrame
        """
        if not search_config["searches"]:
            return df

        result_df = df.copy()

        for col, config in search_config["searches"].items():
            if not config.get("active", False) or col not in df.columns:
                continue

            if config["type"] == "text":
                mask = self._apply_text_search(
                    df[col],
                    config["value"],
                    config["search_type"],
                    config["case_sensitive"],
                    config.get("fuzzy_threshold", 0.0),
                )
                result_df = result_df[mask]

            elif config["type"] == "numeric":
                mask = self._apply_numeric_search(
                    df[col], config["value"], config["search_type"]
                )
                result_df = result_df[mask]

            elif config["type"] == "date":
                mask = self._apply_date_search(
                    df[col], config["value"], config["search_type"]
                )
                result_df = result_df[mask]

            elif config["type"] == "boolean":
                mask = self._apply_boolean_search(df[col], config["value"])
                result_df = result_df[mask]

        return result_df

    def _apply_text_search(
        self,
        series: pd.Series,
        search_value: str,
        search_type: str,
        case_sensitive: bool,
        fuzzy_threshold: float,
    ) -> pd.Series:
        """Apply text search to series."""
        if not search_value:
            return pd.Series([True] * len(series))

        text_series = series.astype(str).fillna("")

        if not case_sensitive:
            search_value = search_value.lower()
            text_series = text_series.str.lower()

        if search_type == "Contains":
            return text_series.str.contains(re.escape(search_value), na=False)
        elif search_type == "Exact":
            return text_series == search_value
        elif search_type == "Starts with":
            return text_series.str.startswith(search_value, na=False)
        elif search_type == "Ends with":
            return text_series.str.endswith(search_value, na=False)
        elif search_type == "Regex":
            try:
                return text_series.str.match(search_value, na=False)
            except re.error:
                st.warning(f"Invalid regex pattern: {search_value}")
                return pd.Series([False] * len(series))
        else:
            return pd.Series([True] * len(series))

    def _apply_numeric_search(
        self,
        series: pd.Series,
        search_value: Union[float, List[float], int],
        search_type: str,
    ) -> pd.Series:
        """Apply numeric search to series."""
        clean_series = pd.to_numeric(series, errors="coerce")

        if search_type == "Range":
            return (clean_series >= search_value[0]) & (clean_series <= search_value[1])
        elif search_type == "Exact Value":
            return clean_series == search_value
        elif search_type == "Greater Than":
            return clean_series > search_value
        elif search_type == "Less Than":
            return clean_series < search_value
        elif search_type == "Top N Values":
            threshold = clean_series.nlargest(search_value).min()
            return clean_series >= threshold
        elif search_type == "Bottom N Values":
            threshold = clean_series.nsmallest(search_value).max()
            return clean_series <= threshold
        else:
            return pd.Series([True] * len(series))

    def _apply_date_search(
        self, series: pd.Series, search_value: Any, search_type: str
    ) -> pd.Series:
        """Apply date search to series."""
        date_series = pd.to_datetime(series, errors="coerce")

        if search_type == "Date Range":
            start_date = pd.to_datetime(search_value[0])
            end_date = pd.to_datetime(search_value[1])
            return (date_series >= start_date) & (date_series <= end_date)

        elif search_type == "Specific Date":
            target_date = pd.to_datetime(search_value)
            return date_series.dt.date == target_date.date()

        elif search_type == "Relative Date":
            relative_type, n_days = search_value
            now = pd.Timestamp.now()

            if relative_type == "Today":
                return date_series.dt.date == now.date()
            elif relative_type == "This Week":
                week_start = now - pd.Timedelta(days=now.weekday())
                return date_series >= week_start.normalize()
            elif relative_type == "This Month":
                month_start = now.replace(day=1)
                return date_series >= month_start.normalize()
            elif relative_type == "This Year":
                year_start = now.replace(month=1, day=1)
                return date_series >= year_start.normalize()
            elif relative_type == "Last N Days" and n_days:
                cutoff_date = now - pd.Timedelta(days=n_days)
                return date_series >= cutoff_date

        elif search_type == "Date Part":
            date_part, part_value = search_value

            if date_part == "Year":
                return date_series.dt.year == part_value
            elif date_part == "Month":
                return date_series.dt.month == part_value
            elif date_part == "Day":
                return date_series.dt.day == part_value
            elif date_part == "Weekday":
                return date_series.dt.dayofweek == (part_value - 1)  # Monday=0
            elif date_part == "Quarter":
                return date_series.dt.quarter == part_value

        return pd.Series([True] * len(series))

    def _apply_boolean_search(
        self, series: pd.Series, search_value: Dict[str, bool]
    ) -> pd.Series:
        """Apply boolean search to series."""
        conditions = []

        if search_value["show_true"]:
            conditions.append(series == True)
        if search_value["show_false"]:
            conditions.append(series == False)
        if search_value["show_null"]:
            conditions.append(series.isnull())

        if not conditions:
            return pd.Series([False] * len(series))

        # Combine conditions with OR
        result = conditions[0]
        for condition in conditions[1:]:
            result = result | condition

        return result
