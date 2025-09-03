"""Streaming UI components for Streamlit with progress indicators."""

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Generator, Optional

import pandas as pd
import streamlit as st


@dataclass
class StreamingState:
    """State for streaming operations."""

    is_streaming: bool = False
    is_cancelled: bool = False
    rows_loaded: int = 0
    chunks_loaded: int = 0
    start_time: Optional[datetime] = None
    estimated_total: Optional[int] = None
    elapsed_time: float = 0.0


class StreamingQueryDisplay:
    """Manages streaming query display with progress indicators."""

    def __init__(self):
        """Initialize streaming display manager."""
        self.state = StreamingState()
        self.progress_placeholder = None
        self.data_placeholder = None
        self.cancel_placeholder = None
        self.metrics_placeholder = None

    def setup_ui_containers(self):
        """Setup Streamlit UI containers for streaming display."""
        # Create placeholders for different UI elements
        self.metrics_placeholder = st.empty()
        self.progress_placeholder = st.empty()
        self.cancel_placeholder = st.empty()
        self.data_placeholder = st.empty()

    def show_progress(
        self, current: int, total: Optional[int] = None, message: str = "Loading..."
    ):
        """Display progress bar with current status."""
        if self.progress_placeholder:
            if total:
                progress = current / total
                self.progress_placeholder.progress(
                    progress, text=f"{message} ({current:,}/{total:,} rows)"
                )
            else:
                # Indeterminate progress
                self.progress_placeholder.progress(
                    (current % 100) / 100, text=f"{message} ({current:,} rows loaded)"
                )

    def show_elapsed_time(self):
        """Display elapsed time counter."""
        if self.metrics_placeholder and self.state.start_time:
            elapsed = datetime.now() - self.state.start_time
            col1, col2, col3, col4 = self.metrics_placeholder.columns(4)

            with col1:
                st.metric("⏱️ Elapsed", f"{elapsed.total_seconds():.1f}s")

            with col2:
                st.metric("📊 Rows", f"{self.state.rows_loaded:,}")

            with col3:
                st.metric("📦 Chunks", f"{self.state.chunks_loaded:,}")

            with col4:
                if self.state.rows_loaded > 0:
                    rows_per_sec = self.state.rows_loaded / elapsed.total_seconds()
                    st.metric("⚡ Speed", f"{rows_per_sec:.0f} rows/s")

    def show_cancel_button(self, cancel_callback: Callable):
        """Display cancel button during streaming."""
        if self.cancel_placeholder and self.state.is_streaming:
            if self.cancel_placeholder.button(
                "🛑 Cancel Query", type="secondary", use_container_width=True
            ):
                self.state.is_cancelled = True
                cancel_callback()
                st.warning("Query cancellation requested...")

    def stream_dataframe(
        self,
        chunks: Generator[pd.DataFrame, None, None],
        max_display_rows: int = 10000,
        update_interval: float = 0.5,
    ) -> pd.DataFrame:
        """
        Stream DataFrame chunks with progressive display.

        Args:
            chunks: Generator yielding DataFrame chunks
            max_display_rows: Maximum rows to display at once
            update_interval: UI update interval in seconds

        Returns:
            Complete DataFrame
        """
        self.setup_ui_containers()
        self.state = StreamingState(is_streaming=True, start_time=datetime.now())

        all_data = []
        display_data = None
        last_update = time.time()

        try:
            for chunk in chunks:
                if self.state.is_cancelled:
                    st.warning("Query cancelled by user")
                    break

                # Add chunk to results
                all_data.append(chunk)
                self.state.rows_loaded += len(chunk)
                self.state.chunks_loaded += 1

                # Update display periodically
                current_time = time.time()
                if current_time - last_update >= update_interval:
                    # Combine data for display (limit rows)
                    if all_data:
                        display_data = pd.concat(all_data, ignore_index=True)
                        if len(display_data) > max_display_rows:
                            display_data = display_data.head(max_display_rows)

                        # Update UI
                        self.show_elapsed_time()
                        self.show_progress(
                            self.state.rows_loaded,
                            self.state.estimated_total,
                            "Streaming results",
                        )

                        # Display data
                        if self.data_placeholder:
                            with self.data_placeholder.container():
                                if len(all_data[0]) > max_display_rows:
                                    st.warning(
                                        f"Showing first {max_display_rows:,} rows. Full results available after completion."
                                    )
                                st.dataframe(display_data, use_container_width=True)

                        last_update = current_time

            # Final update
            self.state.is_streaming = False

            if all_data:
                final_data = pd.concat(all_data, ignore_index=True)

                # Clear progress indicators
                if self.progress_placeholder:
                    self.progress_placeholder.empty()
                if self.cancel_placeholder:
                    self.cancel_placeholder.empty()

                # Show final metrics
                self.show_elapsed_time()

                # Display final data
                if self.data_placeholder:
                    with self.data_placeholder.container():
                        if len(final_data) > max_display_rows:
                            st.info(
                                f"Dataset contains {len(final_data):,} rows. Showing first {max_display_rows:,} rows."
                            )
                            st.dataframe(
                                final_data.head(max_display_rows),
                                use_container_width=True,
                            )
                        else:
                            st.dataframe(final_data, use_container_width=True)

                return final_data

            return pd.DataFrame()

        except Exception as e:
            st.error(f"Streaming error: {str(e)}")
            self.state.is_streaming = False
            if all_data:
                return pd.concat(all_data, ignore_index=True)
            return pd.DataFrame()


class VirtualScrollDataFrame:
    """Virtual scrolling for large DataFrames."""

    def __init__(self, df: pd.DataFrame, page_size: int = 100):
        """
        Initialize virtual scroll display.

        Args:
            df: DataFrame to display
            page_size: Number of rows per page
        """
        self.df = df
        self.page_size = page_size
        self.total_pages = (len(df) - 1) // page_size + 1

        # Initialize page in session state
        if "virtual_scroll_page" not in st.session_state:
            st.session_state.virtual_scroll_page = 0

    def display(self):
        """Display DataFrame with virtual scrolling."""
        # Page navigation
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])

        with col1:
            if st.button("⏮️ First", disabled=st.session_state.virtual_scroll_page == 0):
                st.session_state.virtual_scroll_page = 0
                st.rerun()

        with col2:
            if st.button(
                "◀️ Previous", disabled=st.session_state.virtual_scroll_page == 0
            ):
                st.session_state.virtual_scroll_page -= 1
                st.rerun()

        with col3:
            # Page selector
            page = st.selectbox(
                "Page",
                range(self.total_pages),
                index=st.session_state.virtual_scroll_page,
                format_func=lambda x: f"Page {x+1} of {self.total_pages}",
                label_visibility="collapsed",
            )
            if page != st.session_state.virtual_scroll_page:
                st.session_state.virtual_scroll_page = page
                st.rerun()

        with col4:
            if st.button(
                "Next ▶️",
                disabled=st.session_state.virtual_scroll_page >= self.total_pages - 1,
            ):
                st.session_state.virtual_scroll_page += 1
                st.rerun()

        with col5:
            if st.button(
                "Last ⏭️",
                disabled=st.session_state.virtual_scroll_page >= self.total_pages - 1,
            ):
                st.session_state.virtual_scroll_page = self.total_pages - 1
                st.rerun()

        # Calculate slice
        start_idx = st.session_state.virtual_scroll_page * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.df))

        # Display info
        st.caption(
            f"Showing rows {start_idx+1:,} to {end_idx:,} of {len(self.df):,} total rows"
        )

        # Display data slice
        st.dataframe(
            self.df.iloc[start_idx:end_idx].reset_index(drop=True),
            use_container_width=True,
        )


class ProgressiveLoader:
    """Progressive loading UI pattern for large datasets."""

    def __init__(self, initial_rows: int = 100, increment: int = 100):
        """
        Initialize progressive loader.

        Args:
            initial_rows: Initial number of rows to display
            increment: Number of rows to load on each expansion
        """
        self.initial_rows = initial_rows
        self.increment = increment

        # Initialize state
        if "progressive_rows_shown" not in st.session_state:
            st.session_state.progressive_rows_shown = initial_rows

    def display(self, df: pd.DataFrame):
        """Display DataFrame with progressive loading."""
        total_rows = len(df)
        rows_shown = min(st.session_state.progressive_rows_shown, total_rows)

        # Display current data
        st.dataframe(df.head(rows_shown), use_container_width=True)

        # Show load more button if there's more data
        if rows_shown < total_rows:
            remaining = total_rows - rows_shown
            button_text = f"Load {min(self.increment, remaining)} more rows ({remaining:,} remaining)"

            if st.button(button_text, type="primary"):
                st.session_state.progressive_rows_shown += self.increment
                st.rerun()

            # Option to load all
            if remaining > self.increment:
                if st.button(
                    f"Load all {remaining:,} remaining rows", type="secondary"
                ):
                    st.session_state.progressive_rows_shown = total_rows
                    st.rerun()
        else:
            st.success(f"Showing all {total_rows:,} rows")


def show_query_progress_indicator(
    elapsed_time: float,
    estimated_time: Optional[float] = None,
    rows_processed: Optional[int] = None,
    show_spinner: bool = True,
):
    """
    Display query progress indicators.

    Args:
        elapsed_time: Elapsed time in seconds
        estimated_time: Estimated total time in seconds
        rows_processed: Number of rows processed
        show_spinner: Whether to show spinner animation
    """
    progress_container = st.container()

    with progress_container:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("⏱️ Elapsed", f"{elapsed_time:.1f}s")

        with col2:
            if estimated_time and estimated_time > 0:
                remaining = max(0, estimated_time - elapsed_time)
                st.metric("⏳ Remaining", f"~{remaining:.1f}s")
            else:
                st.metric("⏳ Remaining", "Calculating...")

        with col3:
            if rows_processed:
                st.metric("📊 Rows", f"{rows_processed:,}")

        if show_spinner:
            if estimated_time and estimated_time > 0:
                progress = min(elapsed_time / estimated_time, 1.0)
                st.progress(progress, text="Executing query...")
            else:
                # Indeterminate progress
                st.progress((elapsed_time * 10 % 100) / 100, text="Executing query...")


def create_cancel_query_button(cancel_callback: Callable) -> bool:
    """
    Create a cancel query button.

    Args:
        cancel_callback: Function to call when cancelled

    Returns:
        True if query was cancelled
    """
    if st.button("🛑 Cancel Query", type="secondary", key="cancel_query"):
        cancel_callback()
        st.warning("Query cancellation requested. Please wait...")
        return True
    return False
