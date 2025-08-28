"""Progress indicators and feedback components for long-running operations."""

import streamlit as st
import time
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
import threading
from dataclasses import dataclass, field
import asyncio


@dataclass
class QueryProgress:
    """Track query execution progress."""
    query_id: str
    start_time: datetime
    estimated_duration: float
    current_progress: float = 0.0
    rows_processed: int = 0
    chunks_processed: int = 0
    is_complete: bool = False
    is_cancelled: bool = False
    error: Optional[str] = None
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        return (datetime.now() - self.start_time).total_seconds()
    
    @property
    def estimated_remaining(self) -> float:
        """Get estimated remaining time."""
        if self.current_progress > 0:
            total_estimated = self.elapsed_time / self.current_progress
            return max(0, total_estimated - self.elapsed_time)
        return self.estimated_duration - self.elapsed_time
    
    @property
    def progress_percentage(self) -> float:
        """Get progress as percentage."""
        return min(100, self.current_progress * 100)


class QueryProgressTracker:
    """Manages progress tracking for multiple queries."""
    
    def __init__(self):
        """Initialize progress tracker."""
        self.active_queries: Dict[str, QueryProgress] = {}
        self._lock = threading.Lock()
        
    def start_query(self, query_id: str, estimated_duration: float) -> QueryProgress:
        """Start tracking a new query."""
        with self._lock:
            progress = QueryProgress(
                query_id=query_id,
                start_time=datetime.now(),
                estimated_duration=estimated_duration
            )
            self.active_queries[query_id] = progress
            return progress
    
    def update_progress(
        self,
        query_id: str,
        progress: Optional[float] = None,
        rows: Optional[int] = None,
        chunks: Optional[int] = None
    ):
        """Update query progress."""
        with self._lock:
            if query_id in self.active_queries:
                query = self.active_queries[query_id]
                if progress is not None:
                    query.current_progress = progress
                if rows is not None:
                    query.rows_processed = rows
                if chunks is not None:
                    query.chunks_processed = chunks
    
    def complete_query(self, query_id: str):
        """Mark query as complete."""
        with self._lock:
            if query_id in self.active_queries:
                self.active_queries[query_id].is_complete = True
                self.active_queries[query_id].current_progress = 1.0
    
    def cancel_query(self, query_id: str):
        """Mark query as cancelled."""
        with self._lock:
            if query_id in self.active_queries:
                self.active_queries[query_id].is_cancelled = True
    
    def fail_query(self, query_id: str, error: str):
        """Mark query as failed."""
        with self._lock:
            if query_id in self.active_queries:
                self.active_queries[query_id].error = error
    
    def get_progress(self, query_id: str) -> Optional[QueryProgress]:
        """Get current progress for a query."""
        with self._lock:
            return self.active_queries.get(query_id)
    
    def cleanup_completed(self, max_age_seconds: int = 300):
        """Remove completed queries older than max_age."""
        with self._lock:
            current_time = datetime.now()
            to_remove = []
            
            for query_id, progress in self.active_queries.items():
                if progress.is_complete or progress.is_cancelled or progress.error:
                    age = (current_time - progress.start_time).total_seconds()
                    if age > max_age_seconds:
                        to_remove.append(query_id)
            
            for query_id in to_remove:
                del self.active_queries[query_id]


def create_progress_bar(
    progress: QueryProgress,
    show_cancel: bool = True,
    cancel_callback: Optional[Callable] = None
) -> None:
    """
    Create a progress bar with detailed information.
    
    Args:
        progress: QueryProgress object
        show_cancel: Whether to show cancel button
        cancel_callback: Function to call on cancel
    """
    # Main progress bar
    if progress.is_complete:
        st.success(f"✅ Query completed in {progress.elapsed_time:.1f}s")
    elif progress.is_cancelled:
        st.warning("⚠️ Query cancelled")
    elif progress.error:
        st.error(f"❌ Query failed: {progress.error}")
    else:
        # Active query progress
        col1, col2 = st.columns([4, 1])
        
        with col1:
            progress_text = f"Executing query... ({progress.progress_percentage:.0f}%)"
            if progress.rows_processed > 0:
                progress_text += f" - {progress.rows_processed:,} rows"
            
            st.progress(
                progress.current_progress,
                text=progress_text
            )
        
        with col2:
            if show_cancel and cancel_callback:
                if st.button("Cancel", key=f"cancel_{progress.query_id}", type="secondary"):
                    cancel_callback()
        
        # Detailed metrics
        metric_cols = st.columns(4)
        
        with metric_cols[0]:
            st.metric("⏱️ Elapsed", f"{progress.elapsed_time:.1f}s")
        
        with metric_cols[1]:
            remaining = progress.estimated_remaining
            if remaining > 0:
                st.metric("⏳ Remaining", f"~{remaining:.1f}s")
            else:
                st.metric("⏳ Remaining", "Calculating...")
        
        with metric_cols[2]:
            if progress.rows_processed > 0:
                rows_per_sec = progress.rows_processed / max(progress.elapsed_time, 0.1)
                st.metric("⚡ Speed", f"{rows_per_sec:.0f} rows/s")
        
        with metric_cols[3]:
            if progress.chunks_processed > 0:
                st.metric("📦 Chunks", f"{progress.chunks_processed}")


def create_spinner_with_elapsed_time(
    message: str = "Processing...",
    estimated_time: Optional[float] = None
) -> 'ElapsedTimeSpinner':
    """
    Create a spinner that shows elapsed time.
    
    Args:
        message: Message to display
        estimated_time: Estimated duration in seconds
        
    Returns:
        ElapsedTimeSpinner context manager
    """
    return ElapsedTimeSpinner(message, estimated_time)


class ElapsedTimeSpinner:
    """Spinner that displays elapsed time."""
    
    def __init__(self, message: str, estimated_time: Optional[float] = None):
        """Initialize spinner."""
        self.message = message
        self.estimated_time = estimated_time
        self.start_time = None
        self.placeholder = None
        self._stop_flag = threading.Event()
        self._thread = None
    
    def __enter__(self):
        """Start spinner."""
        self.start_time = datetime.now()
        self.placeholder = st.empty()
        self._stop_flag.clear()
        
        # Start update thread
        self._thread = threading.Thread(target=self._update_spinner)
        self._thread.start()
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop spinner."""
        self._stop_flag.set()
        if self._thread:
            self._thread.join(timeout=1)
        
        if self.placeholder:
            self.placeholder.empty()
    
    def _update_spinner(self):
        """Update spinner display in background."""
        spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        spinner_idx = 0
        
        while not self._stop_flag.is_set():
            elapsed = (datetime.now() - self.start_time).total_seconds()
            
            # Build display message
            display_msg = f"{spinner_chars[spinner_idx]} {self.message}"
            display_msg += f" ({elapsed:.1f}s"
            
            if self.estimated_time:
                remaining = max(0, self.estimated_time - elapsed)
                display_msg += f" / ~{self.estimated_time:.0f}s"
                if remaining > 0:
                    display_msg += f", {remaining:.0f}s remaining"
            
            display_msg += ")"
            
            # Update display
            if self.placeholder:
                self.placeholder.markdown(display_msg)
            
            # Update spinner
            spinner_idx = (spinner_idx + 1) % len(spinner_chars)
            time.sleep(0.1)


def show_row_count_indicator(current_rows: int, estimated_total: Optional[int] = None):
    """
    Display row count indicator with optional total estimate.
    
    Args:
        current_rows: Current number of rows loaded
        estimated_total: Estimated total rows (if known)
    """
    if estimated_total:
        progress = min(current_rows / estimated_total, 1.0)
        st.progress(
            progress,
            text=f"Loading rows: {current_rows:,} / {estimated_total:,}"
        )
    else:
        # Indeterminate progress
        st.info(f"📊 Loaded {current_rows:,} rows...")


def create_time_estimation_display(
    query: str,
    historical_times: Optional[list] = None
) -> float:
    """
    Display time estimation for a query.
    
    Args:
        query: SQL query string
        historical_times: List of historical execution times
        
    Returns:
        Estimated time in seconds
    """
    # Simple heuristic estimation
    query_lower = query.lower()
    base_time = 0.5
    
    # Add time for complexity
    if 'join' in query_lower:
        base_time += 1.0 * query_lower.count('join')
    if 'group by' in query_lower:
        base_time += 0.5
    if 'order by' in query_lower:
        base_time += 0.3
    if 'distinct' in query_lower:
        base_time += 0.2
    if 'window' in query_lower or 'over' in query_lower:
        base_time += 1.5
    
    # Adjust based on history
    if historical_times and len(historical_times) > 0:
        avg_historical = sum(historical_times) / len(historical_times)
        estimated_time = (base_time + avg_historical) / 2
    else:
        estimated_time = base_time
    
    # Display estimation
    if estimated_time < 1:
        st.info("⚡ Query should execute quickly (< 1 second)")
    elif estimated_time < 5:
        st.info(f"⏱️ Estimated execution time: {estimated_time:.1f} seconds")
    else:
        st.warning(f"⏳ This query may take a while (~{estimated_time:.0f} seconds)")
    
    return estimated_time


def create_cancel_mechanism(
    cancel_callback: Callable,
    query_id: str
) -> bool:
    """
    Create a cancel mechanism for long-running queries.
    
    Args:
        cancel_callback: Function to call on cancel
        query_id: Unique query identifier
        
    Returns:
        True if cancelled
    """
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col2:
        if st.button(
            "🛑 Cancel Query",
            key=f"cancel_{query_id}",
            type="secondary",
            use_container_width=True
        ):
            cancel_callback()
            st.warning("Cancelling query... Please wait.")
            return True
    
    return False


class AsyncProgressUpdater:
    """Asynchronous progress updater for real-time updates."""
    
    def __init__(self, placeholder: st.delta_generator.DeltaGenerator):
        """
        Initialize async updater.
        
        Args:
            placeholder: Streamlit placeholder for updates
        """
        self.placeholder = placeholder
        self.progress_data = {
            'current': 0,
            'total': 100,
            'message': 'Processing...',
            'metrics': {}
        }
        self._stop_flag = threading.Event()
        self._lock = threading.Lock()
    
    def update(
        self,
        current: Optional[int] = None,
        total: Optional[int] = None,
        message: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None
    ):
        """Update progress data."""
        with self._lock:
            if current is not None:
                self.progress_data['current'] = current
            if total is not None:
                self.progress_data['total'] = total
            if message is not None:
                self.progress_data['message'] = message
            if metrics:
                self.progress_data['metrics'].update(metrics)
    
    async def run_updates(self, update_interval: float = 0.5):
        """Run asynchronous update loop."""
        while not self._stop_flag.is_set():
            with self._lock:
                data = self.progress_data.copy()
            
            # Update display
            with self.placeholder.container():
                progress = data['current'] / max(data['total'], 1)
                st.progress(progress, text=data['message'])
                
                if data['metrics']:
                    cols = st.columns(len(data['metrics']))
                    for i, (key, value) in enumerate(data['metrics'].items()):
                        with cols[i]:
                            st.metric(key, value)
            
            await asyncio.sleep(update_interval)
    
    def stop(self):
        """Stop the updater."""
        self._stop_flag.set()