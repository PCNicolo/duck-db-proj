"""
Enhanced Thinking Pad UI Component for Streamlit.

This module provides an improved thinking pad display with real-time streaming,
progress visualization, and interactive features.
"""

import streamlit as st
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class ThinkingStage:
    """Represents a stage in the thinking process."""
    icon: str
    label: str
    content: str
    progress: float
    timestamp: float
    status: str = "pending"  # pending, active, complete


class EnhancedThinkingPad:
    """
    Enhanced thinking pad UI component with streaming support.
    """
    
    def __init__(self, container=None):
        """
        Initialize thinking pad.
        
        Args:
            container: Streamlit container for the thinking pad
        """
        self.container = container or st.container()
        self.stages: List[ThinkingStage] = []
        self.sql_buffer = []
        self.start_time = None
        self.is_streaming = False
        
        # Initialize session state
        if "thinking_stages" not in st.session_state:
            st.session_state.thinking_stages = []
        if "sql_stream" not in st.session_state:
            st.session_state.sql_stream = ""
        if "thinking_confidence" not in st.session_state:
            st.session_state.thinking_confidence = 0.0
    
    def start_streaming(self):
        """Start a new streaming session."""
        self.is_streaming = True
        self.start_time = time.time()
        self.stages = []
        self.sql_buffer = []
        st.session_state.thinking_stages = []
        st.session_state.sql_stream = ""
        st.session_state.thinking_confidence = 0.0
    
    def stop_streaming(self):
        """Stop the streaming session."""
        self.is_streaming = False
    
    def add_thinking_stage(
        self,
        icon: str,
        label: str,
        content: str,
        progress: float = 0.0
    ):
        """
        Add a new thinking stage.
        
        Args:
            icon: Emoji or icon for the stage
            label: Stage label
            content: Stage content/description
            progress: Progress percentage (0-1)
        """
        stage = ThinkingStage(
            icon=icon,
            label=label,
            content=content,
            progress=progress,
            timestamp=time.time(),
            status="active" if self.is_streaming else "complete"
        )
        
        self.stages.append(stage)
        st.session_state.thinking_stages = self.stages
        
        # Update display
        if self.is_streaming:
            self.render_streaming()
    
    def update_sql_stream(self, sql_chunk: str):
        """
        Update the SQL stream with new content.
        
        Args:
            sql_chunk: New SQL content to append
        """
        self.sql_buffer.append(sql_chunk)
        st.session_state.sql_stream = "".join(self.sql_buffer)
        
        if self.is_streaming:
            self.render_streaming()
    
    def update_confidence(self, confidence: float):
        """Update confidence score."""
        st.session_state.thinking_confidence = confidence
    
    def render_streaming(self):
        """Render the thinking pad in streaming mode."""
        with self.container:
            # Header with real-time timer
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("### 🤖 LLM Thinking Pad")
            with col2:
                if self.start_time:
                    elapsed = time.time() - self.start_time
                    st.caption(f"⏱️ {elapsed:.1f}s")
            
            # Progress bar
            if self.stages:
                latest_stage = self.stages[-1]
                st.progress(
                    latest_stage.progress,
                    text=f"{latest_stage.icon} {latest_stage.label}"
                )
            
            # Thinking stages
            self._render_thinking_stages()
            
            # SQL preview (if streaming)
            if st.session_state.sql_stream:
                self._render_sql_preview()
            
            # Confidence meter
            if st.session_state.thinking_confidence > 0:
                self._render_confidence_meter()
    
    def render_static(self, thinking_process: str, sql: str, confidence: float = 0.0):
        """
        Render the thinking pad in static mode (non-streaming).
        
        Args:
            thinking_process: Complete thinking process text
            sql: Generated SQL
            confidence: Confidence score
        """
        with self.container:
            st.markdown("### 🤖 LLM Thinking Pad")
            
            # Display thinking process
            with st.expander("💭 Thinking Process", expanded=True):
                st.markdown(thinking_process)
            
            # Display SQL
            if sql:
                with st.expander("📝 Generated SQL", expanded=False):
                    st.code(sql, language="sql")
            
            # Confidence meter
            if confidence > 0:
                self._render_confidence_meter(confidence)
    
    def _render_thinking_stages(self):
        """Render thinking stages with visual indicators."""
        if not self.stages:
            return
        
        # Use columns for better layout
        thinking_container = st.container()
        with thinking_container:
            st.markdown("#### 💭 Thinking Process")
            
            for i, stage in enumerate(self.stages):
                # Determine stage styling
                if stage.status == "complete":
                    stage_class = "✅"
                elif stage.status == "active":
                    stage_class = "🔄"
                else:
                    stage_class = "⏳"
                
                # Create stage display
                with st.container():
                    col1, col2 = st.columns([1, 10])
                    with col1:
                        st.write(stage_class)
                    with col2:
                        st.markdown(f"**{stage.icon} {stage.label}**")
                        if stage.content:
                            st.caption(stage.content)
                
                # Add separator between stages
                if i < len(self.stages) - 1:
                    st.divider()
    
    def _render_sql_preview(self):
        """Render SQL preview with syntax highlighting."""
        st.markdown("#### 📝 SQL Generation")
        
        # Show streaming SQL with placeholder for incomplete parts
        sql_display = st.session_state.sql_stream
        if self.is_streaming and not sql_display.endswith(";"):
            sql_display += " ..."
        
        st.code(sql_display, language="sql")
    
    def _render_confidence_meter(self, confidence: Optional[float] = None):
        """
        Render confidence meter with visual indicator.
        
        Args:
            confidence: Confidence score (0-1), uses session state if not provided
        """
        conf_value = confidence or st.session_state.thinking_confidence
        
        # Determine confidence level and color
        if conf_value >= 0.8:
            level = "High"
            color = "🟢"
        elif conf_value >= 0.5:
            level = "Medium"
            color = "🟡"
        else:
            level = "Low"
            color = "🔴"
        
        # Display confidence
        col1, col2 = st.columns([1, 3])
        with col1:
            st.metric("Confidence", f"{conf_value:.0%}")
        with col2:
            st.markdown(f"{color} **{level} Confidence**")
            st.progress(conf_value)
    
    def handle_stream_update(self, update: Dict[str, Any]):
        """
        Handle streaming update from the generator.
        
        Args:
            update: Update dictionary with type, content, and metadata
        """
        update_type = update.get("type")
        content = update.get("content", "")
        metadata = update.get("metadata", {})
        
        if update_type == "thinking":
            # Parse thinking update
            stage_label = metadata.get("stage", "Processing")
            progress = metadata.get("progress", 0.0)
            
            # Map stage to icon
            stage_icons = {
                "understanding": "🎯",
                "analyzing_schema": "📊",
                "identifying_tables": "🔍",
                "building_query": "🛠️",
                "adding_filters": "🔧",
                "optimizing": "⚡",
                "validating": "✅",
                "complete": "🎉"
            }
            
            icon = stage_icons.get(stage_label, "💭")
            
            self.add_thinking_stage(
                icon=icon,
                label=stage_label.replace("_", " ").title(),
                content=content,
                progress=progress
            )
            
        elif update_type == "sql":
            # Update SQL stream
            self.update_sql_stream(content)
            
        elif update_type == "complete":
            # Mark streaming as complete
            self.stop_streaming()
            
            # Update final confidence
            if "confidence" in metadata:
                self.update_confidence(metadata["confidence"])
            
            # Mark all stages as complete
            for stage in self.stages:
                stage.status = "complete"
            
            # Final render
            self.render_streaming()
            
        elif update_type == "error":
            # Handle error
            self.stop_streaming()
            st.error(f"Generation error: {content}")


class ThinkingPadConfig:
    """Configuration UI for thinking pad settings."""
    
    @staticmethod
    def render_config_panel():
        """Render configuration panel for thinking pad."""
        with st.expander("⚙️ Thinking Pad Settings", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                # Display mode
                display_mode = st.selectbox(
                    "Display Mode",
                    ["Streaming", "Static", "Compact"],
                    help="How to display the thinking process"
                )
                
                # Verbosity level
                verbosity = st.slider(
                    "Verbosity Level",
                    min_value=1,
                    max_value=5,
                    value=3,
                    help="How detailed should the thinking process be"
                )
                
                # Auto-expand
                auto_expand = st.checkbox(
                    "Auto-expand thinking pad",
                    value=True,
                    help="Automatically expand thinking pad when generating"
                )
            
            with col2:
                # Show confidence
                show_confidence = st.checkbox(
                    "Show confidence meter",
                    value=True,
                    help="Display confidence score for generated SQL"
                )
                
                # Show timing
                show_timing = st.checkbox(
                    "Show generation timing",
                    value=True,
                    help="Display time taken for generation"
                )
                
                # Enable animations
                enable_animations = st.checkbox(
                    "Enable animations",
                    value=True,
                    help="Show animated progress indicators"
                )
            
            # Advanced settings
            with st.expander("Advanced Settings"):
                # Stream delay
                stream_delay = st.slider(
                    "Stream delay (ms)",
                    min_value=0,
                    max_value=500,
                    value=100,
                    step=50,
                    help="Delay between streaming updates"
                )
                
                # Max thinking stages
                max_stages = st.number_input(
                    "Max thinking stages to display",
                    min_value=3,
                    max_value=20,
                    value=8,
                    help="Maximum number of thinking stages to show"
                )
                
                # SQL preview lines
                sql_preview_lines = st.number_input(
                    "SQL preview lines",
                    min_value=5,
                    max_value=50,
                    value=15,
                    help="Number of SQL lines to show in preview"
                )
            
            return {
                "display_mode": display_mode,
                "verbosity": verbosity,
                "auto_expand": auto_expand,
                "show_confidence": show_confidence,
                "show_timing": show_timing,
                "enable_animations": enable_animations,
                "stream_delay": stream_delay,
                "max_stages": max_stages,
                "sql_preview_lines": sql_preview_lines
            }


def demo_thinking_pad():
    """Demo function to showcase the enhanced thinking pad."""
    st.title("Enhanced Thinking Pad Demo")
    
    # Create thinking pad
    thinking_pad = EnhancedThinkingPad()
    
    # Configuration panel
    config = ThinkingPadConfig.render_config_panel()
    
    # Demo controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Start Streaming Demo"):
            thinking_pad.start_streaming()
            
            # Simulate streaming updates
            import time
            stages = [
                ("🎯", "Understanding Request", "Analyzing: 'Show total sales by month'", 0.2),
                ("📊", "Analyzing Schema", "Found sales table with date and amount columns", 0.4),
                ("🛠️", "Building Query", "Creating SELECT statement with GROUP BY", 0.6),
                ("⚡", "Optimizing", "Adding indexes and optimizing joins", 0.8),
                ("✅", "Validating", "Query syntax validated successfully", 1.0)
            ]
            
            for icon, label, content, progress in stages:
                thinking_pad.add_thinking_stage(icon, label, content, progress)
                time.sleep(0.5)  # Simulate delay
                
                # Add some SQL
                if progress > 0.4:
                    sql_chunk = f"\nSELECT DATE_TRUNC('month', date) as month"
                    thinking_pad.update_sql_stream(sql_chunk)
            
            thinking_pad.update_confidence(0.85)
            thinking_pad.stop_streaming()
    
    with col2:
        if st.button("Show Static Demo"):
            thinking_process = """
            🎯 Understanding your request: Show total sales by month
            
            📊 Analyzing the database schema:
            - Found 'sales' table with relevant columns
            - Identified 'date' and 'amount' columns
            
            🛠️ Building the query structure:
            - Using DATE_TRUNC for monthly grouping
            - Applying SUM aggregation on amount
            
            ⚡ Optimizing for performance:
            - Using appropriate indexes
            - Limiting result set
            
            ✅ Query validated and ready!
            """
            
            sql = """
            SELECT 
                DATE_TRUNC('month', date) as month,
                SUM(amount) as total_sales
            FROM sales
            GROUP BY month
            ORDER BY month DESC
            LIMIT 12;
            """
            
            thinking_pad.render_static(thinking_process, sql, 0.92)
    
    with col3:
        if st.button("Clear"):
            st.session_state.thinking_stages = []
            st.session_state.sql_stream = ""
            st.session_state.thinking_confidence = 0.0
            st.rerun()


if __name__ == "__main__":
    demo_thinking_pad()