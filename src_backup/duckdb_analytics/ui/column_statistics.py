"""Inline column statistics and data profiling components."""

from typing import Any, Dict, List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


class ColumnStatisticsManager:
    """Manager for inline column statistics and mini-visualizations."""

    def __init__(self, db_connection=None):
        """Initialize column statistics manager."""
        self.db_connection = db_connection

        # Initialize session state
        if "column_stats_cache" not in st.session_state:
            st.session_state.column_stats_cache = {}

        if "column_stats_preferences" not in st.session_state:
            st.session_state.column_stats_preferences = {
                "show_sparklines": True,
                "show_distributions": True,
                "show_data_quality": True,
                "cache_enabled": True,
                "auto_refresh": False,
            }

    def render_column_statistics_interface(
        self, df: pd.DataFrame, table_name: str = "data"
    ) -> Dict[str, Any]:
        """
        Render comprehensive column statistics interface.

        Args:
            df: DataFrame to analyze
            table_name: Name for caching and identification

        Returns:
            Dictionary containing column statistics and analysis results
        """
        st.subheader("📊 Column Statistics & Data Quality")

        if df.empty:
            st.warning("No data available for analysis")
            return {}

        # Render statistics preferences
        stats_config = self._render_statistics_preferences()

        # Generate or retrieve column statistics
        column_stats = self._get_or_generate_column_stats(df, table_name, stats_config)

        # Render statistics display
        self._render_statistics_display(df, column_stats, stats_config)

        return column_stats

    def _render_statistics_preferences(self) -> Dict[str, Any]:
        """Render statistics display preferences."""
        with st.expander("⚙️ Statistics Display Options"):
            col1, col2, col3 = st.columns(3)

            with col1:
                show_sparklines = st.checkbox(
                    "Show Sparklines",
                    value=st.session_state.column_stats_preferences["show_sparklines"],
                    help="Display mini charts for numeric columns",
                )

                show_distributions = st.checkbox(
                    "Show Distributions",
                    value=st.session_state.column_stats_preferences[
                        "show_distributions"
                    ],
                    help="Display distribution summaries",
                )

            with col2:
                show_data_quality = st.checkbox(
                    "Show Data Quality",
                    value=st.session_state.column_stats_preferences[
                        "show_data_quality"
                    ],
                    help="Display data quality indicators",
                )

                cache_enabled = st.checkbox(
                    "Enable Caching",
                    value=st.session_state.column_stats_preferences["cache_enabled"],
                    help="Cache statistics for better performance",
                )

            with col3:
                auto_refresh = st.checkbox(
                    "Auto Refresh",
                    value=st.session_state.column_stats_preferences["auto_refresh"],
                    help="Automatically refresh statistics when data changes",
                )

                if st.button("🔄 Refresh All Stats"):
                    # Clear cache to force refresh
                    st.session_state.column_stats_cache = {}
                    st.rerun()

        # Update preferences
        st.session_state.column_stats_preferences.update(
            {
                "show_sparklines": show_sparklines,
                "show_distributions": show_distributions,
                "show_data_quality": show_data_quality,
                "cache_enabled": cache_enabled,
                "auto_refresh": auto_refresh,
            }
        )

        return st.session_state.column_stats_preferences

    def _get_or_generate_column_stats(
        self, df: pd.DataFrame, table_name: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get cached statistics or generate new ones."""
        cache_key = f"{table_name}_{len(df)}_{df.columns.tolist()}"

        # Check cache
        if (
            config["cache_enabled"]
            and cache_key in st.session_state.column_stats_cache
            and not config["auto_refresh"]
        ):
            return st.session_state.column_stats_cache[cache_key]

        # Generate new statistics
        with st.spinner("Analyzing column statistics..."):
            column_stats = self._generate_comprehensive_stats(df, config)

        # Cache results
        if config["cache_enabled"]:
            st.session_state.column_stats_cache[cache_key] = column_stats

            # Limit cache size
            if len(st.session_state.column_stats_cache) > 10:
                oldest_key = list(st.session_state.column_stats_cache.keys())[0]
                del st.session_state.column_stats_cache[oldest_key]

        return column_stats

    def _generate_comprehensive_stats(
        self, df: pd.DataFrame, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive statistics for all columns."""
        stats = {
            "overview": self._generate_overview_stats(df),
            "columns": {},
            "data_quality": self._generate_data_quality_overview(df),
        }

        for column in df.columns:
            stats["columns"][column] = self._analyze_single_column(
                df[column], column, config
            )

        return stats

    def _generate_overview_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate overall dataset statistics."""
        return {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024 / 1024,
            "numeric_columns": len(df.select_dtypes(include=[np.number]).columns),
            "categorical_columns": len(
                df.select_dtypes(include=["object", "category"]).columns
            ),
            "datetime_columns": len(df.select_dtypes(include=["datetime64"]).columns),
            "boolean_columns": len(df.select_dtypes(include=["bool"]).columns),
            "missing_cells": df.isnull().sum().sum(),
            "duplicate_rows": df.duplicated().sum(),
            "completeness_score": 1
            - (df.isnull().sum().sum() / (len(df) * len(df.columns))),
        }

    def _generate_data_quality_overview(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate data quality overview."""
        quality_issues = []
        quality_score = 1.0

        # Check for missing data
        missing_pct = df.isnull().sum().sum() / (len(df) * len(df.columns))
        if missing_pct > 0.1:
            quality_issues.append(f"High missing data rate: {missing_pct:.1%}")
            quality_score -= missing_pct * 0.3

        # Check for duplicate rows
        dup_pct = df.duplicated().sum() / len(df)
        if dup_pct > 0.05:
            quality_issues.append(f"High duplicate rate: {dup_pct:.1%}")
            quality_score -= dup_pct * 0.2

        # Check for inconsistent data types
        for col in df.columns:
            if df[col].dtype == "object":
                # Check if numeric values are stored as strings
                try:
                    numeric_count = (
                        pd.to_numeric(df[col], errors="coerce").notna().sum()
                    )
                    if numeric_count > len(df) * 0.8:
                        quality_issues.append(
                            f"Column '{col}' appears numeric but stored as text"
                        )
                        quality_score -= 0.1
                except:
                    pass

        return {
            "overall_score": max(0.0, quality_score),
            "issues": quality_issues,
            "recommendations": self._generate_quality_recommendations(quality_issues),
        }

    def _generate_quality_recommendations(self, issues: List[str]) -> List[str]:
        """Generate recommendations based on quality issues."""
        recommendations = []

        for issue in issues:
            if "missing data" in issue.lower():
                recommendations.append(
                    "Consider imputation strategies or explicit handling of missing values"
                )
            elif "duplicate" in issue.lower():
                recommendations.append(
                    "Review and remove duplicate records if appropriate"
                )
            elif "numeric but stored as text" in issue.lower():
                recommendations.append(
                    "Convert numeric text columns to proper numeric types"
                )

        return recommendations

    def _analyze_single_column(
        self, series: pd.Series, column_name: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze a single column comprehensively."""
        stats = {
            "basic_info": self._get_basic_column_info(series),
            "distribution": {},
            "data_quality": {},
            "patterns": {},
            "sparkline_data": None,
        }

        # Type-specific analysis
        if pd.api.types.is_numeric_dtype(series):
            stats.update(self._analyze_numeric_column(series, config))
        elif pd.api.types.is_string_dtype(series):
            stats.update(self._analyze_text_column(series, config))
        elif pd.api.types.is_datetime64_any_dtype(series):
            stats.update(self._analyze_datetime_column(series, config))
        elif pd.api.types.is_bool_dtype(series):
            stats.update(self._analyze_boolean_column(series, config))

        # Data quality analysis
        stats["data_quality"] = self._analyze_column_quality(series)

        return stats

    def _get_basic_column_info(self, series: pd.Series) -> Dict[str, Any]:
        """Get basic information about a column."""
        return {
            "data_type": str(series.dtype),
            "count": len(series),
            "non_null_count": series.notna().sum(),
            "null_count": series.isnull().sum(),
            "null_percentage": series.isnull().sum() / len(series) * 100,
            "unique_count": series.nunique(),
            "unique_percentage": (
                series.nunique() / len(series) * 100 if len(series) > 0 else 0
            ),
        }

    def _analyze_numeric_column(
        self, series: pd.Series, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze numeric column."""
        clean_series = series.dropna()

        stats = {"numeric_stats": {}, "distribution": {}, "outliers": {}}

        if len(clean_series) > 0:
            # Basic statistics
            stats["numeric_stats"] = {
                "min": float(clean_series.min()),
                "max": float(clean_series.max()),
                "mean": float(clean_series.mean()),
                "median": float(clean_series.median()),
                "std": float(clean_series.std()),
                "variance": float(clean_series.var()),
                "skewness": float(clean_series.skew()) if len(clean_series) > 2 else 0,
                "kurtosis": (
                    float(clean_series.kurtosis()) if len(clean_series) > 3 else 0
                ),
            }

            # Quartiles
            quartiles = clean_series.quantile([0.25, 0.5, 0.75])
            stats["numeric_stats"].update(
                {
                    "q1": float(quartiles[0.25]),
                    "q2": float(quartiles[0.5]),
                    "q3": float(quartiles[0.75]),
                    "iqr": float(quartiles[0.75] - quartiles[0.25]),
                }
            )

            # Distribution analysis
            stats["distribution"] = {
                "range": float(clean_series.max() - clean_series.min()),
                "coefficient_of_variation": (
                    float(clean_series.std() / clean_series.mean())
                    if clean_series.mean() != 0
                    else float("inf")
                ),
                "is_constant": clean_series.nunique() == 1,
                "is_binary": clean_series.nunique() == 2,
            }

            # Outlier detection using IQR method
            q1, q3 = quartiles[0.25], quartiles[0.75]
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            outliers = clean_series[
                (clean_series < lower_bound) | (clean_series > upper_bound)
            ]

            stats["outliers"] = {
                "count": len(outliers),
                "percentage": (
                    len(outliers) / len(clean_series) * 100
                    if len(clean_series) > 0
                    else 0
                ),
                "lower_bound": float(lower_bound),
                "upper_bound": float(upper_bound),
            }

            # Sparkline data
            if config["show_sparklines"] and len(clean_series) > 10:
                # Create histogram data for sparkline
                hist_data = np.histogram(clean_series, bins=20)
                stats["sparkline_data"] = {
                    "type": "histogram",
                    "values": hist_data[0].tolist(),
                    "bins": hist_data[1].tolist(),
                }

        return stats

    def _analyze_text_column(
        self, series: pd.Series, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze text column."""
        clean_series = series.dropna()

        stats = {"text_stats": {}, "patterns": {}, "top_values": {}}

        if len(clean_series) > 0:
            # Basic text statistics
            lengths = clean_series.str.len()

            stats["text_stats"] = {
                "min_length": int(lengths.min()),
                "max_length": int(lengths.max()),
                "mean_length": float(lengths.mean()),
                "median_length": float(lengths.median()),
                "std_length": float(lengths.std()),
                "total_characters": int(lengths.sum()),
            }

            # Pattern analysis
            patterns = {
                "email_pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                "phone_pattern": r"^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$",
                "url_pattern": r"^https?:\/\/[^\s]+$",
                "numeric_pattern": r"^\d+$",
                "alphanumeric_pattern": r"^[a-zA-Z0-9]+$",
                "uppercase_pattern": r"^[A-Z\s]+$",
                "lowercase_pattern": r"^[a-z\s]+$",
            }

            pattern_matches = {}
            for pattern_name, pattern in patterns.items():
                matches = clean_series.str.match(pattern, na=False).sum()
                if matches > 0:
                    pattern_matches[pattern_name] = {
                        "count": int(matches),
                        "percentage": float(matches / len(clean_series) * 100),
                    }

            stats["patterns"] = pattern_matches

            # Top values
            value_counts = clean_series.value_counts().head(10)
            stats["top_values"] = {
                "values": value_counts.index.tolist(),
                "counts": value_counts.values.tolist(),
                "percentages": (value_counts / len(clean_series) * 100).tolist(),
            }

            # Sparkline data for text lengths
            if config["show_sparklines"] and len(clean_series) > 10:
                hist_data = np.histogram(lengths, bins=15)
                stats["sparkline_data"] = {
                    "type": "histogram",
                    "values": hist_data[0].tolist(),
                    "bins": hist_data[1].tolist(),
                    "title": "Text Length Distribution",
                }

        return stats

    def _analyze_datetime_column(
        self, series: pd.Series, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze datetime column."""
        clean_series = series.dropna()

        stats = {
            "datetime_stats": {},
            "temporal_patterns": {},
            "time_series_data": None,
        }

        if len(clean_series) > 0:
            # Basic datetime statistics
            stats["datetime_stats"] = {
                "min_date": clean_series.min().isoformat(),
                "max_date": clean_series.max().isoformat(),
                "date_range_days": (clean_series.max() - clean_series.min()).days,
                "unique_dates": clean_series.nunique(),
            }

            # Temporal patterns
            stats["temporal_patterns"] = {
                "years": sorted(clean_series.dt.year.unique().tolist()),
                "months": clean_series.dt.month.value_counts().to_dict(),
                "days_of_week": clean_series.dt.dayofweek.value_counts().to_dict(),
                "hours": (
                    clean_series.dt.hour.value_counts().to_dict()
                    if clean_series.dt.hour.nunique() > 1
                    else {}
                ),
            }

            # Time series sparkline
            if config["show_sparklines"] and len(clean_series) > 5:
                # Group by time periods for sparkline
                if len(clean_series) > 100:
                    # Monthly aggregation for large datasets
                    ts_data = clean_series.dt.to_period("M").value_counts().sort_index()
                else:
                    # Daily aggregation for smaller datasets
                    ts_data = clean_series.dt.date.value_counts().sort_index()

                stats["sparkline_data"] = {
                    "type": "timeseries",
                    "dates": [str(d) for d in ts_data.index],
                    "values": ts_data.values.tolist(),
                    "title": "Date Distribution",
                }

        return stats

    def _analyze_boolean_column(
        self, series: pd.Series, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze boolean column."""
        clean_series = series.dropna()

        stats = {"boolean_stats": {}, "distribution": {}}

        if len(clean_series) > 0:
            true_count = clean_series.sum()
            false_count = len(clean_series) - true_count

            stats["boolean_stats"] = {
                "true_count": int(true_count),
                "false_count": int(false_count),
                "true_percentage": float(true_count / len(clean_series) * 100),
                "false_percentage": float(false_count / len(clean_series) * 100),
            }

            stats["distribution"] = {
                "is_balanced": abs(true_count - false_count) / len(clean_series) < 0.2,
                "dominant_value": True if true_count > false_count else False,
                "dominance_ratio": max(true_count, false_count) / len(clean_series),
            }

        return stats

    def _analyze_column_quality(self, series: pd.Series) -> Dict[str, Any]:
        """Analyze data quality for a column."""
        quality_score = 1.0
        issues = []

        # Missing data
        null_pct = series.isnull().sum() / len(series)
        if null_pct > 0.1:
            issues.append(f"High missing data: {null_pct:.1%}")
            quality_score -= null_pct * 0.3

        # Uniqueness
        if len(series) > 1:
            unique_pct = series.nunique() / len(series)
            if (
                unique_pct < 0.01 and series.nunique() > 1
            ):  # Very low uniqueness but not constant
                issues.append("Very low uniqueness")
                quality_score -= 0.2

        # Data type consistency
        if pd.api.types.is_string_dtype(series):
            # Check for mixed types in string column
            try:
                numeric_convertible = (
                    pd.to_numeric(series, errors="coerce").notna().sum()
                )
                if (
                    0.1 < numeric_convertible / len(series) < 0.9
                ):  # Partial convertibility suggests inconsistency
                    issues.append("Mixed data types detected")
                    quality_score -= 0.15
            except:
                pass

        return {
            "score": max(0.0, quality_score),
            "issues": issues,
            "completeness": 1 - null_pct,
            "uniqueness": series.nunique() / len(series) if len(series) > 0 else 0,
        }

    def _render_statistics_display(
        self, df: pd.DataFrame, column_stats: Dict[str, Any], config: Dict[str, Any]
    ):
        """Render the statistics display interface."""
        # Overview section
        self._render_overview_section(
            column_stats["overview"], column_stats["data_quality"]
        )

        # Column-by-column analysis
        st.subheader("📋 Column Analysis")

        # Column selection for detailed view
        selected_columns = st.multiselect(
            "Select columns for detailed analysis",
            df.columns.tolist(),
            default=(
                df.columns.tolist()[:5] if len(df.columns) > 5 else df.columns.tolist()
            ),
            help="Choose which columns to analyze in detail",
        )

        # Display mode selection
        display_mode = st.radio(
            "Display Mode",
            ["Grid View", "Detailed View", "Summary Table"],
            horizontal=True,
            help="Choose how to display column statistics",
        )

        if display_mode == "Grid View":
            self._render_grid_view(df, column_stats, selected_columns, config)
        elif display_mode == "Detailed View":
            self._render_detailed_view(df, column_stats, selected_columns, config)
        else:  # Summary Table
            self._render_summary_table(df, column_stats, selected_columns)

    def _render_overview_section(
        self, overview: Dict[str, Any], data_quality: Dict[str, Any]
    ):
        """Render dataset overview section."""
        st.subheader("📈 Dataset Overview")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Rows", f"{overview['total_rows']:,}")
            st.metric("Missing Cells", f"{overview['missing_cells']:,}")

        with col2:
            st.metric("Total Columns", overview["total_columns"])
            st.metric("Duplicate Rows", f"{overview['duplicate_rows']:,}")

        with col3:
            st.metric("Memory Usage", f"{overview['memory_usage_mb']:.2f} MB")
            st.metric("Completeness", f"{overview['completeness_score']:.1%}")

        with col4:
            st.metric("Data Quality Score", f"{data_quality['overall_score']:.1%}")

            # Quality indicator
            if data_quality["overall_score"] >= 0.8:
                st.success("🟢 Good Quality")
            elif data_quality["overall_score"] >= 0.6:
                st.warning("🟡 Fair Quality")
            else:
                st.error("🔴 Poor Quality")

        # Column type breakdown
        st.subheader("📊 Column Types")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Numeric", overview["numeric_columns"])
        with col2:
            st.metric("Categorical", overview["categorical_columns"])
        with col3:
            st.metric("DateTime", overview["datetime_columns"])
        with col4:
            st.metric("Boolean", overview["boolean_columns"])

        # Data quality issues and recommendations
        if data_quality["issues"]:
            with st.expander("⚠️ Data Quality Issues"):
                for issue in data_quality["issues"]:
                    st.write(f"• {issue}")

                st.subheader("💡 Recommendations")
                for rec in data_quality["recommendations"]:
                    st.write(f"• {rec}")

    def _render_grid_view(
        self,
        df: pd.DataFrame,
        column_stats: Dict[str, Any],
        selected_columns: List[str],
        config: Dict[str, Any],
    ):
        """Render grid view of column statistics."""
        cols_per_row = 3

        for i in range(0, len(selected_columns), cols_per_row):
            cols = st.columns(cols_per_row)

            for j, column in enumerate(selected_columns[i : i + cols_per_row]):
                with cols[j]:
                    self._render_column_card(
                        column, df[column], column_stats["columns"][column], config
                    )

    def _render_column_card(
        self,
        column_name: str,
        series: pd.Series,
        stats: Dict[str, Any],
        config: Dict[str, Any],
    ):
        """Render a compact card for a single column."""
        with st.container():
            # Header with data type
            data_type = stats["basic_info"]["data_type"]
            type_emoji = {
                "int64": "🔢",
                "float64": "🔢",
                "object": "📝",
                "datetime64[ns]": "📅",
                "bool": "☑️",
                "category": "🏷️",
            }

            emoji = type_emoji.get(data_type, "❓")
            st.markdown(f"**{emoji} {column_name}**")
            st.caption(f"Type: {data_type}")

            # Key metrics
            col1, col2 = st.columns(2)

            with col1:
                st.metric("Count", f"{stats['basic_info']['non_null_count']:,}")
                st.metric("Unique", f"{stats['basic_info']['unique_count']:,}")

            with col2:
                st.metric("Missing", f"{stats['basic_info']['null_percentage']:.1f}%")
                quality_score = stats["data_quality"]["score"]
                st.metric("Quality", f"{quality_score:.1%}")

            # Type-specific statistics
            if "numeric_stats" in stats:
                st.write("**Range**")
                st.write(
                    f"{stats['numeric_stats']['min']:.2f} → {stats['numeric_stats']['max']:.2f}"
                )
                st.write(f"**Mean:** {stats['numeric_stats']['mean']:.2f}")

            elif "text_stats" in stats:
                st.write("**Length Range**")
                st.write(
                    f"{stats['text_stats']['min_length']} → {stats['text_stats']['max_length']} chars"
                )
                st.write(f"**Avg:** {stats['text_stats']['mean_length']:.1f}")

            elif "datetime_stats" in stats:
                st.write("**Date Range**")
                st.write(f"{stats['datetime_stats']['date_range_days']} days")

            elif "boolean_stats" in stats:
                st.write("**Distribution**")
                true_pct = stats["boolean_stats"]["true_percentage"]
                st.write(f"True: {true_pct:.1f}%")

            # Sparkline
            if config["show_sparklines"] and stats.get("sparkline_data"):
                self._render_mini_sparkline(stats["sparkline_data"])

            # Data quality indicators
            if config["show_data_quality"] and stats["data_quality"]["issues"]:
                st.warning(f"⚠️ {len(stats['data_quality']['issues'])} issues")

    def _render_detailed_view(
        self,
        df: pd.DataFrame,
        column_stats: Dict[str, Any],
        selected_columns: List[str],
        config: Dict[str, Any],
    ):
        """Render detailed view for selected columns."""
        for column in selected_columns:
            with st.expander(
                f"📊 {column} - Detailed Analysis", expanded=len(selected_columns) == 1
            ):
                self._render_detailed_column_analysis(
                    column, df[column], column_stats["columns"][column], config
                )

    def _render_detailed_column_analysis(
        self,
        column_name: str,
        series: pd.Series,
        stats: Dict[str, Any],
        config: Dict[str, Any],
    ):
        """Render detailed analysis for a single column."""
        col1, col2 = st.columns(2)

        with col1:
            # Basic information
            st.subheader("ℹ️ Basic Information")
            basic_info = stats["basic_info"]

            metrics_data = [
                ("Data Type", basic_info["data_type"]),
                ("Total Count", f"{basic_info['count']:,}"),
                ("Non-Null Count", f"{basic_info['non_null_count']:,}"),
                ("Null Count", f"{basic_info['null_count']:,}"),
                ("Null Percentage", f"{basic_info['null_percentage']:.2f}%"),
                ("Unique Values", f"{basic_info['unique_count']:,}"),
                ("Uniqueness", f"{basic_info['unique_percentage']:.2f}%"),
            ]

            for label, value in metrics_data:
                st.write(f"**{label}:** {value}")

        with col2:
            # Data quality
            st.subheader("🔍 Data Quality")
            quality = stats["data_quality"]

            # Quality score with color coding
            score = quality["score"]
            if score >= 0.8:
                st.success(f"Quality Score: {score:.1%} 🟢")
            elif score >= 0.6:
                st.warning(f"Quality Score: {score:.1%} 🟡")
            else:
                st.error(f"Quality Score: {score:.1%} 🔴")

            st.write(f"**Completeness:** {quality['completeness']:.1%}")
            st.write(f"**Uniqueness:** {quality['uniqueness']:.1%}")

            if quality["issues"]:
                st.write("**Issues:**")
                for issue in quality["issues"]:
                    st.write(f"• {issue}")

        # Type-specific detailed analysis
        if "numeric_stats" in stats:
            self._render_numeric_details(stats, config)
        elif "text_stats" in stats:
            self._render_text_details(stats, config)
        elif "datetime_stats" in stats:
            self._render_datetime_details(stats, config)
        elif "boolean_stats" in stats:
            self._render_boolean_details(stats, config)

        # Enhanced visualizations
        if config["show_distributions"]:
            self._render_distribution_visualization(series, stats)

    def _render_numeric_details(self, stats: Dict[str, Any], config: Dict[str, Any]):
        """Render detailed numeric column analysis."""
        st.subheader("🔢 Numeric Statistics")

        numeric_stats = stats["numeric_stats"]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.write("**Central Tendency**")
            st.write(f"Mean: {numeric_stats['mean']:.4f}")
            st.write(f"Median: {numeric_stats['median']:.4f}")
            st.write(f"Mode: {numeric_stats.get('mode', 'N/A')}")

        with col2:
            st.write("**Spread**")
            st.write(f"Std Dev: {numeric_stats['std']:.4f}")
            st.write(f"Variance: {numeric_stats['variance']:.4f}")
            st.write(f"Range: {stats['distribution']['range']:.4f}")
            st.write(f"IQR: {numeric_stats['iqr']:.4f}")

        with col3:
            st.write("**Shape**")
            st.write(f"Skewness: {numeric_stats['skewness']:.4f}")
            st.write(f"Kurtosis: {numeric_stats['kurtosis']:.4f}")
            st.write(f"CV: {stats['distribution']['coefficient_of_variation']:.4f}")

        # Quartile information
        st.write("**Quartiles**")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Min", f"{numeric_stats['min']:.2f}")
        with col2:
            st.metric("Q1", f"{numeric_stats['q1']:.2f}")
        with col3:
            st.metric("Q3", f"{numeric_stats['q3']:.2f}")
        with col4:
            st.metric("Max", f"{numeric_stats['max']:.2f}")

        # Outlier information
        if "outliers" in stats:
            outliers = stats["outliers"]
            if outliers["count"] > 0:
                st.warning(
                    f"⚠️ {outliers['count']} outliers detected ({outliers['percentage']:.1f}%)"
                )
                st.write(
                    f"Outlier bounds: [{outliers['lower_bound']:.2f}, {outliers['upper_bound']:.2f}]"
                )

    def _render_text_details(self, stats: Dict[str, Any], config: Dict[str, Any]):
        """Render detailed text column analysis."""
        st.subheader("📝 Text Statistics")

        text_stats = stats["text_stats"]

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Length Statistics**")
            st.write(f"Min Length: {text_stats['min_length']}")
            st.write(f"Max Length: {text_stats['max_length']}")
            st.write(f"Mean Length: {text_stats['mean_length']:.1f}")
            st.write(f"Median Length: {text_stats['median_length']:.1f}")
            st.write(f"Total Characters: {text_stats['total_characters']:,}")

        with col2:
            # Pattern analysis
            if "patterns" in stats and stats["patterns"]:
                st.write("**Detected Patterns**")
                for pattern_name, pattern_info in stats["patterns"].items():
                    pattern_display = pattern_name.replace("_pattern", "").title()
                    st.write(
                        f"{pattern_display}: {pattern_info['count']} ({pattern_info['percentage']:.1f}%)"
                    )

        # Top values
        if "top_values" in stats:
            st.write("**Most Frequent Values**")
            top_values = stats["top_values"]

            for i, (value, count, pct) in enumerate(
                zip(
                    top_values["values"][:5],
                    top_values["counts"][:5],
                    top_values["percentages"][:5],
                    strict=False,
                )
            ):
                st.write(f"{i+1}. '{value}' - {count:,} ({pct:.1f}%)")

    def _render_datetime_details(self, stats: Dict[str, Any], config: Dict[str, Any]):
        """Render detailed datetime column analysis."""
        st.subheader("📅 DateTime Statistics")

        datetime_stats = stats["datetime_stats"]

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Date Range**")
            st.write(f"Earliest: {datetime_stats['min_date']}")
            st.write(f"Latest: {datetime_stats['max_date']}")
            st.write(f"Range: {datetime_stats['date_range_days']} days")
            st.write(f"Unique Dates: {datetime_stats['unique_dates']:,}")

        with col2:
            # Temporal patterns
            if "temporal_patterns" in stats:
                patterns = stats["temporal_patterns"]

                st.write("**Temporal Patterns**")

                if patterns["years"]:
                    st.write(
                        f"Years: {min(patterns['years'])} - {max(patterns['years'])}"
                    )

                # Most common month
                if patterns["months"]:
                    most_common_month = max(
                        patterns["months"].items(), key=lambda x: x[1]
                    )
                    month_names = [
                        "Jan",
                        "Feb",
                        "Mar",
                        "Apr",
                        "May",
                        "Jun",
                        "Jul",
                        "Aug",
                        "Sep",
                        "Oct",
                        "Nov",
                        "Dec",
                    ]
                    st.write(
                        f"Most common month: {month_names[most_common_month[0]-1]}"
                    )

                # Most common day of week
                if patterns["days_of_week"]:
                    most_common_day = max(
                        patterns["days_of_week"].items(), key=lambda x: x[1]
                    )
                    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                    st.write(f"Most common day: {day_names[most_common_day[0]]}")

    def _render_boolean_details(self, stats: Dict[str, Any], config: Dict[str, Any]):
        """Render detailed boolean column analysis."""
        st.subheader("☑️ Boolean Statistics")

        boolean_stats = stats["boolean_stats"]

        col1, col2 = st.columns(2)

        with col1:
            st.metric("True Count", f"{boolean_stats['true_count']:,}")
            st.metric("True Percentage", f"{boolean_stats['true_percentage']:.1f}%")

        with col2:
            st.metric("False Count", f"{boolean_stats['false_count']:,}")
            st.metric("False Percentage", f"{boolean_stats['false_percentage']:.1f}%")

        # Distribution analysis
        distribution = stats["distribution"]

        if distribution["is_balanced"]:
            st.success("✅ Balanced distribution")
        else:
            dominant = "True" if distribution["dominant_value"] else "False"
            ratio = distribution["dominance_ratio"]
            st.info(f"Dominant value: {dominant} ({ratio:.1%})")

    def _render_summary_table(
        self,
        df: pd.DataFrame,
        column_stats: Dict[str, Any],
        selected_columns: List[str],
    ):
        """Render summary table view."""
        st.subheader("📋 Summary Table")

        summary_data = []

        for column in selected_columns:
            stats = column_stats["columns"][column]
            basic = stats["basic_info"]
            quality = stats["data_quality"]

            row = {
                "Column": column,
                "Type": basic["data_type"],
                "Count": f"{basic['non_null_count']:,}",
                "Missing": f"{basic['null_percentage']:.1f}%",
                "Unique": f"{basic['unique_count']:,}",
                "Uniqueness": f"{basic['unique_percentage']:.1f}%",
                "Quality Score": f"{quality['score']:.1%}",
            }

            # Add type-specific columns
            if "numeric_stats" in stats:
                row["Mean"] = f"{stats['numeric_stats']['mean']:.2f}"
                row["Std"] = f"{stats['numeric_stats']['std']:.2f}"
                row["Min"] = f"{stats['numeric_stats']['min']:.2f}"
                row["Max"] = f"{stats['numeric_stats']['max']:.2f}"

            elif "text_stats" in stats:
                row["Avg Length"] = f"{stats['text_stats']['mean_length']:.1f}"
                row["Max Length"] = f"{stats['text_stats']['max_length']}"

            summary_data.append(row)

        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True)

        # Export summary
        if st.button("📥 Export Summary"):
            csv_data = summary_df.to_csv(index=False)
            st.download_button(
                "Download Summary CSV",
                csv_data,
                "column_statistics_summary.csv",
                "text/csv",
            )

    def _render_mini_sparkline(self, sparkline_data: Dict[str, Any]):
        """Render a mini sparkline visualization."""
        if sparkline_data["type"] == "histogram":
            # Create mini histogram
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=list(range(len(sparkline_data["values"]))),
                    y=sparkline_data["values"],
                    marker_color="lightblue",
                    showlegend=False,
                )
            )

            fig.update_layout(
                height=100,
                margin=dict(l=0, r=0, t=0, b=0),
                xaxis=dict(showticklabels=False, showgrid=False),
                yaxis=dict(showticklabels=False, showgrid=False),
                plot_bgcolor="rgba(0,0,0,0)",
            )

            st.plotly_chart(
                fig, use_container_width=True, config={"displayModeBar": False}
            )

        elif sparkline_data["type"] == "timeseries":
            # Create mini time series
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=sparkline_data["dates"],
                    y=sparkline_data["values"],
                    mode="lines",
                    line=dict(color="steelblue", width=2),
                    showlegend=False,
                )
            )

            fig.update_layout(
                height=100,
                margin=dict(l=0, r=0, t=0, b=0),
                xaxis=dict(showticklabels=False, showgrid=False),
                yaxis=dict(showticklabels=False, showgrid=False),
                plot_bgcolor="rgba(0,0,0,0)",
            )

            st.plotly_chart(
                fig, use_container_width=True, config={"displayModeBar": False}
            )

    def _render_distribution_visualization(
        self, series: pd.Series, stats: Dict[str, Any]
    ):
        """Render distribution visualization for a column."""
        st.subheader("📈 Distribution Visualization")

        if pd.api.types.is_numeric_dtype(series):
            # Histogram for numeric data
            fig = px.histogram(
                x=series.dropna(),
                nbins=30,
                title=f"Distribution of {series.name}",
                template="plotly_white",
            )

            # Add mean and median lines
            mean_val = series.mean()
            median_val = series.median()

            fig.add_vline(
                x=mean_val,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Mean: {mean_val:.2f}",
            )
            fig.add_vline(
                x=median_val,
                line_dash="dash",
                line_color="blue",
                annotation_text=f"Median: {median_val:.2f}",
            )

            st.plotly_chart(fig, use_container_width=True)

        elif pd.api.types.is_string_dtype(series):
            # Bar chart for top categories
            if "top_values" in stats:
                top_values = stats["top_values"]

                fig = px.bar(
                    x=top_values["values"][:10],
                    y=top_values["counts"][:10],
                    title=f"Top 10 Values in {series.name}",
                    template="plotly_white",
                )

                fig.update_xaxis(title="Values")
                fig.update_yaxis(title="Count")

                st.plotly_chart(fig, use_container_width=True)

        elif pd.api.types.is_datetime64_any_dtype(series):
            # Time series plot
            if "temporal_patterns" in stats:
                # Create monthly aggregation
                monthly_counts = series.dt.to_period("M").value_counts().sort_index()

                fig = px.line(
                    x=[str(p) for p in monthly_counts.index],
                    y=monthly_counts.values,
                    title=f"Temporal Distribution of {series.name}",
                    template="plotly_white",
                )

                fig.update_xaxis(title="Month")
                fig.update_yaxis(title="Count")

                st.plotly_chart(fig, use_container_width=True)
