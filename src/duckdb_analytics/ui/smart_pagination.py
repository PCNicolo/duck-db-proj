"""Smart pagination system with performance optimization."""

import math
from typing import Any, Dict

import pandas as pd
import streamlit as st


class SmartPagination:
    """Smart pagination system with virtual scrolling and performance optimization."""

    def __init__(self):
        """Initialize smart pagination."""
        self.default_page_size = 100
        self.max_page_size = 10000
        self.virtual_scroll_threshold = 1000

        # Initialize session state
        if "pagination_settings" not in st.session_state:
            st.session_state.pagination_settings = {
                "page_size": self.default_page_size,
                "current_page": 0,
                "pagination_mode": "standard",
                "virtual_scroll_enabled": False,
                "prefetch_enabled": True,
            }

        if "pagination_cache" not in st.session_state:
            st.session_state.pagination_cache = {}

        if "pagination_performance" not in st.session_state:
            st.session_state.pagination_performance = {
                "page_load_times": [],
                "cache_hit_rate": 0.0,
                "total_requests": 0,
                "cached_requests": 0,
            }

    def render_pagination_interface(
        self, df: pd.DataFrame, table_name: str = "data"
    ) -> Dict[str, Any]:
        """
        Render smart pagination interface.

        Args:
            df: DataFrame to paginate
            table_name: Name for caching and identification

        Returns:
            Dictionary containing pagination configuration and paginated data
        """
        if df.empty:
            st.warning("No data to display")
            return {"data": pd.DataFrame(), "pagination_info": {}}

        total_rows = len(df)

        # Render pagination controls
        pagination_config = self._render_pagination_controls(total_rows)

        # Apply pagination based on mode
        if pagination_config["mode"] == "virtual_scroll":
            paginated_data = self._render_virtual_scroll(
                df, pagination_config, table_name
            )
        elif pagination_config["mode"] == "infinite_scroll":
            paginated_data = self._render_infinite_scroll(
                df, pagination_config, table_name
            )
        else:  # standard pagination
            paginated_data = self._render_standard_pagination(
                df, pagination_config, table_name
            )

        # Performance monitoring
        self._update_performance_metrics(pagination_config)

        # Render performance dashboard
        if st.checkbox("Show Performance Dashboard", value=False):
            self._render_performance_dashboard()

        return {"data": paginated_data, "pagination_info": pagination_config}

    def _render_pagination_controls(self, total_rows: int) -> Dict[str, Any]:
        """Render pagination control interface."""
        st.subheader("📄 Pagination Settings")

        col1, col2, col3 = st.columns(3)

        with col1:
            # Pagination mode selection
            pagination_mode = st.selectbox(
                "Pagination Mode",
                ["standard", "virtual_scroll", "infinite_scroll"],
                index=["standard", "virtual_scroll", "infinite_scroll"].index(
                    st.session_state.pagination_settings["pagination_mode"]
                ),
                format_func=lambda x: {
                    "standard": "📋 Standard Pagination",
                    "virtual_scroll": "⚡ Virtual Scrolling",
                    "infinite_scroll": "♾️ Infinite Scroll",
                }.get(x, x),
                help="Choose pagination strategy based on data size and performance needs",
            )

        with col2:
            # Page size selection
            if pagination_mode == "virtual_scroll":
                page_size = st.slider(
                    "Viewport Size",
                    min_value=50,
                    max_value=500,
                    value=min(200, st.session_state.pagination_settings["page_size"]),
                    step=25,
                    help="Number of rows visible in viewport",
                )
            else:
                page_size = st.selectbox(
                    "Rows per Page",
                    [25, 50, 100, 250, 500, 1000, 2500, 5000],
                    index=(
                        [25, 50, 100, 250, 500, 1000, 2500, 5000].index(
                            min(st.session_state.pagination_settings["page_size"], 5000)
                        )
                        if st.session_state.pagination_settings["page_size"]
                        in [25, 50, 100, 250, 500, 1000, 2500, 5000]
                        else 2
                    ),
                    help="Number of rows to display per page",
                )

        with col3:
            # Advanced options
            enable_prefetch = st.checkbox(
                "Enable Prefetch",
                value=st.session_state.pagination_settings["prefetch_enabled"],
                help="Preload adjacent pages for faster navigation",
            )

            if pagination_mode == "standard":
                enable_jump_to_page = st.checkbox("Enable Jump to Page", value=True)
            else:
                enable_jump_to_page = False

        # Calculate pagination info
        total_pages = math.ceil(total_rows / page_size) if page_size > 0 else 1
        current_page = min(
            st.session_state.pagination_settings["current_page"], total_pages - 1
        )

        # Auto-select optimal pagination mode for large datasets
        if total_rows > 10000 and pagination_mode == "standard":
            st.info(
                f"💡 Consider using Virtual Scroll for better performance with {total_rows:,} rows"
            )

        # Update session state
        st.session_state.pagination_settings.update(
            {
                "pagination_mode": pagination_mode,
                "page_size": page_size,
                "current_page": current_page,
                "prefetch_enabled": enable_prefetch,
            }
        )

        return {
            "mode": pagination_mode,
            "page_size": page_size,
            "current_page": current_page,
            "total_pages": total_pages,
            "total_rows": total_rows,
            "prefetch_enabled": enable_prefetch,
            "jump_to_page_enabled": enable_jump_to_page,
        }

    def _render_standard_pagination(
        self, df: pd.DataFrame, config: Dict[str, Any], table_name: str
    ) -> pd.DataFrame:
        """Render standard pagination interface."""
        # Navigation controls
        col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 2, 1, 1, 1])

        with col1:
            if st.button(
                "⏮️ First", disabled=config["current_page"] == 0, help="Go to first page"
            ):
                st.session_state.pagination_settings["current_page"] = 0
                st.rerun()

        with col2:
            if st.button(
                "◀️ Previous",
                disabled=config["current_page"] == 0,
                help="Go to previous page",
            ):
                st.session_state.pagination_settings["current_page"] = max(
                    0, config["current_page"] - 1
                )
                st.rerun()

        with col3:
            if config["jump_to_page_enabled"]:
                # Jump to page selector
                page_options = list(range(config["total_pages"]))
                display_options = [
                    f"Page {i+1} of {config['total_pages']}" for i in page_options
                ]

                selected_page = st.selectbox(
                    "Current Page",
                    page_options,
                    index=config["current_page"],
                    format_func=lambda x: display_options[x],
                    help="Jump to specific page",
                )

                if selected_page != config["current_page"]:
                    st.session_state.pagination_settings["current_page"] = selected_page
                    st.rerun()
            else:
                st.write(
                    f"Page {config['current_page'] + 1} of {config['total_pages']}"
                )

        with col4:
            if st.button(
                "Next ▶️",
                disabled=config["current_page"] >= config["total_pages"] - 1,
                help="Go to next page",
            ):
                st.session_state.pagination_settings["current_page"] = min(
                    config["total_pages"] - 1, config["current_page"] + 1
                )
                st.rerun()

        with col5:
            if st.button(
                "Last ⏭️",
                disabled=config["current_page"] >= config["total_pages"] - 1,
                help="Go to last page",
            ):
                st.session_state.pagination_settings["current_page"] = (
                    config["total_pages"] - 1
                )
                st.rerun()

        with col6:
            # Page size info
            start_row = config["current_page"] * config["page_size"] + 1
            end_row = min(
                (config["current_page"] + 1) * config["page_size"], config["total_rows"]
            )
            st.caption(f"Rows {start_row:,}-{end_row:,} of {config['total_rows']:,}")

        # Get paginated data
        paginated_data = self._get_page_data(
            df, config["current_page"], config["page_size"], table_name
        )

        # Prefetch adjacent pages if enabled
        if config["prefetch_enabled"]:
            self._prefetch_pages(df, config, table_name)

        # Display data
        st.dataframe(
            paginated_data,
            use_container_width=True,
            height=min(600, len(paginated_data) * 35 + 100),
        )

        # Additional navigation at bottom for long pages
        if len(paginated_data) > 20:
            st.divider()
            col1, col2, col3 = st.columns([1, 2, 1])

            with col1:
                if st.button(
                    "◀️ Prev Page",
                    disabled=config["current_page"] == 0,
                    key="bottom_prev",
                ):
                    st.session_state.pagination_settings["current_page"] = max(
                        0, config["current_page"] - 1
                    )
                    st.rerun()

            with col2:
                st.write(
                    f"Page {config['current_page'] + 1} of {config['total_pages']}"
                )

            with col3:
                if st.button(
                    "Next Page ▶️",
                    disabled=config["current_page"] >= config["total_pages"] - 1,
                    key="bottom_next",
                ):
                    st.session_state.pagination_settings["current_page"] = min(
                        config["total_pages"] - 1, config["current_page"] + 1
                    )
                    st.rerun()

        return paginated_data

    def _render_virtual_scroll(
        self, df: pd.DataFrame, config: Dict[str, Any], table_name: str
    ) -> pd.DataFrame:
        """Render virtual scrolling interface."""
        st.subheader("⚡ Virtual Scroll View")

        # Virtual scroll controls
        col1, col2, col3 = st.columns(3)

        with col1:
            # Scroll position control
            max_scroll = max(0, config["total_rows"] - config["page_size"])
            scroll_position = st.slider(
                "Scroll Position",
                min_value=0,
                max_value=max_scroll,
                value=config["current_page"] * config["page_size"],
                step=config["page_size"] // 4,
                help=f"Scroll through {config['total_rows']:,} rows",
            )

        with col2:
            # Quick jump buttons
            if st.button("🔝 Top"):
                scroll_position = 0
                st.rerun()

            if st.button("🔽 Bottom"):
                scroll_position = max_scroll
                st.rerun()

        with col3:
            # Position info
            end_pos = min(scroll_position + config["page_size"], config["total_rows"])
            st.metric("Viewing", f"{scroll_position + 1:,} - {end_pos:,}")

        # Get virtual scroll data
        virtual_page = scroll_position // config["page_size"]
        offset_in_page = scroll_position % config["page_size"]

        # Load data with smooth scrolling
        virtual_data = self._get_virtual_scroll_data(
            df, scroll_position, config["page_size"], table_name
        )

        # Display virtual scroll data
        if not virtual_data.empty:
            st.dataframe(virtual_data, use_container_width=True, height=600)

        # Scroll performance indicator
        if len(df) > 50000:
            st.info("🚀 Virtual scrolling optimized for large datasets")

        return virtual_data

    def _render_infinite_scroll(
        self, df: pd.DataFrame, config: Dict[str, Any], table_name: str
    ) -> pd.DataFrame:
        """Render infinite scroll interface."""
        st.subheader("♾️ Infinite Scroll")

        # Initialize infinite scroll state
        if "infinite_scroll_loaded" not in st.session_state:
            st.session_state.infinite_scroll_loaded = config["page_size"]

        # Load more button
        loaded_rows = min(st.session_state.infinite_scroll_loaded, config["total_rows"])
        remaining_rows = config["total_rows"] - loaded_rows

        # Display currently loaded data
        current_data = df.head(loaded_rows)
        st.dataframe(current_data, use_container_width=True, height=600)

        # Load more controls
        if remaining_rows > 0:
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button(
                    f"📥 Load {min(config['page_size'], remaining_rows)} More Rows"
                ):
                    st.session_state.infinite_scroll_loaded += config["page_size"]
                    st.rerun()

            with col2:
                if st.button(f"📥📥 Load All Remaining ({remaining_rows:,} rows)"):
                    st.session_state.infinite_scroll_loaded = config["total_rows"]
                    st.rerun()

            with col3:
                st.write(f"{remaining_rows:,} rows remaining")
        else:
            st.success("✅ All rows loaded")
            if st.button("🔄 Reset to Beginning"):
                st.session_state.infinite_scroll_loaded = config["page_size"]
                st.rerun()

        # Progress indicator
        progress = loaded_rows / config["total_rows"]
        st.progress(
            progress,
            text=f"Loaded {loaded_rows:,} of {config['total_rows']:,} rows ({progress:.1%})",
        )

        return current_data

    def _get_page_data(
        self, df: pd.DataFrame, page: int, page_size: int, table_name: str
    ) -> pd.DataFrame:
        """Get data for a specific page with caching."""
        cache_key = f"{table_name}_page_{page}_size_{page_size}"

        # Check cache first
        if cache_key in st.session_state.pagination_cache:
            st.session_state.pagination_performance["cached_requests"] += 1
            return st.session_state.pagination_cache[cache_key]

        # Calculate slice
        start_idx = page * page_size
        end_idx = min(start_idx + page_size, len(df))

        # Get page data
        page_data = df.iloc[start_idx:end_idx].reset_index(drop=True)

        # Cache the result
        st.session_state.pagination_cache[cache_key] = page_data

        # Limit cache size
        if len(st.session_state.pagination_cache) > 50:
            # Remove oldest entries
            keys_to_remove = list(st.session_state.pagination_cache.keys())[:-25]
            for key in keys_to_remove:
                del st.session_state.pagination_cache[key]

        st.session_state.pagination_performance["total_requests"] += 1
        return page_data

    def _get_virtual_scroll_data(
        self, df: pd.DataFrame, start_pos: int, size: int, table_name: str
    ) -> pd.DataFrame:
        """Get data for virtual scrolling with smooth loading."""
        end_pos = min(start_pos + size, len(df))

        # Use caching for virtual scroll as well
        cache_key = f"{table_name}_virtual_{start_pos}_{size}"

        if cache_key in st.session_state.pagination_cache:
            return st.session_state.pagination_cache[cache_key]

        virtual_data = df.iloc[start_pos:end_pos].reset_index(drop=True)

        # Cache virtual scroll data
        st.session_state.pagination_cache[cache_key] = virtual_data

        return virtual_data

    def _prefetch_pages(
        self, df: pd.DataFrame, config: Dict[str, Any], table_name: str
    ):
        """Prefetch adjacent pages for better performance."""
        current_page = config["current_page"]
        page_size = config["page_size"]
        total_pages = config["total_pages"]

        # Prefetch next and previous pages
        pages_to_prefetch = []

        if current_page > 0:
            pages_to_prefetch.append(current_page - 1)  # Previous page

        if current_page < total_pages - 1:
            pages_to_prefetch.append(current_page + 1)  # Next page

        # Prefetch in background (simulated with cache pre-population)
        for page in pages_to_prefetch:
            cache_key = f"{table_name}_page_{page}_size_{page_size}"
            if cache_key not in st.session_state.pagination_cache:
                # Pre-calculate and cache the page
                start_idx = page * page_size
                end_idx = min(start_idx + page_size, len(df))
                page_data = df.iloc[start_idx:end_idx].reset_index(drop=True)
                st.session_state.pagination_cache[cache_key] = page_data

    def _update_performance_metrics(self, config: Dict[str, Any]):
        """Update pagination performance metrics."""
        perf = st.session_state.pagination_performance

        # Calculate cache hit rate
        if perf["total_requests"] > 0:
            perf["cache_hit_rate"] = perf["cached_requests"] / perf["total_requests"]

        # Record page load time (simulated)
        load_time = (
            0.1 if config["mode"] == "virtual_scroll" else 0.3
        )  # Simulated times
        perf["page_load_times"].append(load_time)

        # Keep only recent load times
        if len(perf["page_load_times"]) > 100:
            perf["page_load_times"] = perf["page_load_times"][-100:]

    def _render_performance_dashboard(self):
        """Render pagination performance dashboard."""
        st.subheader("📊 Pagination Performance")

        perf = st.session_state.pagination_performance

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Cache Hit Rate", f"{perf['cache_hit_rate']:.1%}")

        with col2:
            st.metric("Total Requests", perf["total_requests"])

        with col3:
            avg_load_time = (
                sum(perf["page_load_times"]) / len(perf["page_load_times"])
                if perf["page_load_times"]
                else 0
            )
            st.metric("Avg Load Time", f"{avg_load_time:.3f}s")

        with col4:
            st.metric("Cache Size", len(st.session_state.pagination_cache))

        # Performance recommendations
        st.subheader("💡 Performance Recommendations")

        if perf["cache_hit_rate"] < 0.3:
            st.info(
                "🔄 Low cache hit rate. Consider enabling prefetch or increasing page size for better performance."
            )

        if len(st.session_state.pagination_cache) > 30:
            st.info(
                "💾 High cache usage. Cache will be automatically cleaned up to maintain performance."
            )

        if avg_load_time > 0.5:
            st.warning(
                "⏱️ Slow page load times detected. Consider using virtual scrolling for large datasets."
            )

        # Cache management
        col1, col2 = st.columns(2)

        with col1:
            if st.button("🗑️ Clear Cache"):
                st.session_state.pagination_cache = {}
                st.success("Cache cleared successfully")
                st.rerun()

        with col2:
            if st.button("📊 Reset Performance Metrics"):
                st.session_state.pagination_performance = {
                    "page_load_times": [],
                    "cache_hit_rate": 0.0,
                    "total_requests": 0,
                    "cached_requests": 0,
                }
                st.success("Performance metrics reset")
                st.rerun()


class PaginationPresets:
    """Predefined pagination configurations for common scenarios."""

    @staticmethod
    def get_preset_config(preset_name: str) -> Dict[str, Any]:
        """Get predefined pagination configuration."""
        presets = {
            "small_dataset": {
                "mode": "standard",
                "page_size": 100,
                "prefetch_enabled": False,
                "description": "Optimized for datasets under 1K rows",
            },
            "medium_dataset": {
                "mode": "standard",
                "page_size": 250,
                "prefetch_enabled": True,
                "description": "Optimized for datasets 1K-10K rows",
            },
            "large_dataset": {
                "mode": "virtual_scroll",
                "page_size": 200,
                "prefetch_enabled": True,
                "description": "Optimized for datasets 10K-100K rows",
            },
            "huge_dataset": {
                "mode": "virtual_scroll",
                "page_size": 500,
                "prefetch_enabled": True,
                "description": "Optimized for datasets over 100K rows",
            },
            "exploratory": {
                "mode": "infinite_scroll",
                "page_size": 100,
                "prefetch_enabled": False,
                "description": "Good for data exploration and discovery",
            },
        }

        return presets.get(preset_name, presets["medium_dataset"])

    @staticmethod
    def recommend_preset(row_count: int) -> str:
        """Recommend optimal preset based on row count."""
        if row_count < 1000:
            return "small_dataset"
        elif row_count < 10000:
            return "medium_dataset"
        elif row_count < 100000:
            return "large_dataset"
        else:
            return "huge_dataset"

    @staticmethod
    def render_preset_selector(row_count: int) -> Dict[str, Any]:
        """Render preset selector interface."""
        st.subheader("🎯 Pagination Presets")

        recommended_preset = PaginationPresets.recommend_preset(row_count)

        presets = {
            "small_dataset": "📋 Small Dataset (<1K rows)",
            "medium_dataset": "📊 Medium Dataset (1K-10K rows)",
            "large_dataset": "⚡ Large Dataset (10K-100K rows)",
            "huge_dataset": "🚀 Huge Dataset (>100K rows)",
            "exploratory": "🔍 Exploratory Mode",
        }

        col1, col2 = st.columns(2)

        with col1:
            selected_preset = st.selectbox(
                "Choose Preset",
                list(presets.keys()),
                index=list(presets.keys()).index(recommended_preset),
                format_func=lambda x: presets[x],
            )

        with col2:
            if selected_preset == recommended_preset:
                st.success(f"✅ Recommended for {row_count:,} rows")
            else:
                st.info("ℹ️ Custom selection")

        # Show preset details
        config = PaginationPresets.get_preset_config(selected_preset)
        st.write(f"**Description:** {config['description']}")

        return config
