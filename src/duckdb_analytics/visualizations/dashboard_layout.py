"""Dashboard layout system for multiple charts."""

import streamlit as st
import json
from typing import Dict, Any, List, Optional, Tuple
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from dataclasses import dataclass, asdict
from enum import Enum


class LayoutType(Enum):
    """Available dashboard layout types."""
    GRID = "grid"
    TABS = "tabs"
    COLUMNS = "columns"
    ROWS = "rows"
    CUSTOM = "custom"


@dataclass
class ChartPosition:
    """Chart position and size in dashboard layout."""
    x: int = 0
    y: int = 0
    width: int = 6
    height: int = 4
    title: str = ""
    chart_id: str = ""


@dataclass
class DashboardLayout:
    """Dashboard layout configuration."""
    id: str
    name: str
    layout_type: LayoutType
    columns: int = 12
    rows: int = 8
    charts: List[ChartPosition] = None
    global_config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.charts is None:
            self.charts = []
        if self.global_config is None:
            self.global_config = {}


class DashboardLayoutManager:
    """Manager for dashboard layouts and multi-chart displays."""
    
    def __init__(self):
        self.layouts = {}
        self.chart_cache = {}
        
    def create_layout(self, name: str, layout_type: LayoutType,
                     columns: int = 12, rows: int = 8) -> DashboardLayout:
        """Create a new dashboard layout."""
        layout_id = f"layout_{len(self.layouts)}"
        
        layout = DashboardLayout(
            id=layout_id,
            name=name,
            layout_type=layout_type,
            columns=columns,
            rows=rows,
            charts=[],
            global_config={
                'title': name,
                'theme': 'plotly_white',
                'font_size': 12,
                'show_titles': True
            }
        )
        
        self.layouts[layout_id] = layout
        return layout
    
    def add_chart_to_layout(self, layout_id: str, chart_id: str, 
                           position: ChartPosition) -> bool:
        """Add a chart to a layout at specified position."""
        if layout_id not in self.layouts:
            return False
            
        position.chart_id = chart_id
        self.layouts[layout_id].charts.append(position)
        return True
    
    def render_dashboard(self, layout_id: str, charts: Dict[str, go.Figure]) -> None:
        """Render a complete dashboard with multiple charts."""
        if layout_id not in self.layouts:
            st.error("Dashboard layout not found")
            return
            
        layout = self.layouts[layout_id]
        
        # Dashboard header
        st.title(layout.global_config.get('title', layout.name))
        
        # Render based on layout type
        if layout.layout_type == LayoutType.GRID:
            self._render_grid_layout(layout, charts)
        elif layout.layout_type == LayoutType.TABS:
            self._render_tabs_layout(layout, charts)
        elif layout.layout_type == LayoutType.COLUMNS:
            self._render_columns_layout(layout, charts)
        elif layout.layout_type == LayoutType.ROWS:
            self._render_rows_layout(layout, charts)
        else:
            self._render_custom_layout(layout, charts)
    
    def _render_grid_layout(self, layout: DashboardLayout, 
                           charts: Dict[str, go.Figure]) -> None:
        """Render grid-based dashboard layout."""
        # Create grid container
        for chart_pos in layout.charts:
            if chart_pos.chart_id in charts:
                # Calculate Streamlit columns based on position
                cols = st.columns(layout.columns)
                
                # Position chart in appropriate column
                col_index = min(chart_pos.x, len(cols) - 1)
                
                with cols[col_index]:
                    fig = charts[chart_pos.chart_id]
                    
                    # Apply position-specific settings
                    fig.update_layout(
                        height=chart_pos.height * 100,
                        title=chart_pos.title or fig.layout.title.text
                    )
                    
                    st.plotly_chart(fig, use_container_width=True, key=f"chart_{chart_pos.chart_id}")
    
    def _render_tabs_layout(self, layout: DashboardLayout,
                           charts: Dict[str, go.Figure]) -> None:
        """Render tab-based dashboard layout."""
        tab_names = [pos.title or f"Chart {i+1}" for i, pos in enumerate(layout.charts)]
        tabs = st.tabs(tab_names)
        
        for i, (tab, chart_pos) in enumerate(zip(tabs, layout.charts)):
            with tab:
                if chart_pos.chart_id in charts:
                    fig = charts[chart_pos.chart_id]
                    st.plotly_chart(fig, use_container_width=True, key=f"tab_chart_{chart_pos.chart_id}")
    
    def _render_columns_layout(self, layout: DashboardLayout,
                              charts: Dict[str, go.Figure]) -> None:
        """Render column-based dashboard layout."""
        cols = st.columns(len(layout.charts))
        
        for col, chart_pos in zip(cols, layout.charts):
            with col:
                if chart_pos.chart_id in charts:
                    fig = charts[chart_pos.chart_id]
                    fig.update_layout(title=chart_pos.title or fig.layout.title.text)
                    st.plotly_chart(fig, use_container_width=True, key=f"col_chart_{chart_pos.chart_id}")
    
    def _render_rows_layout(self, layout: DashboardLayout,
                           charts: Dict[str, go.Figure]) -> None:
        """Render row-based dashboard layout."""
        for chart_pos in layout.charts:
            if chart_pos.chart_id in charts:
                fig = charts[chart_pos.chart_id]
                fig.update_layout(title=chart_pos.title or fig.layout.title.text)
                st.plotly_chart(fig, use_container_width=True, key=f"row_chart_{chart_pos.chart_id}")
                st.divider()
    
    def _render_custom_layout(self, layout: DashboardLayout,
                             charts: Dict[str, go.Figure]) -> None:
        """Render custom dashboard layout."""
        # Custom layout allows for more complex arrangements
        # This is a simplified version - could be extended with more sophisticated positioning
        
        # Group charts by row
        chart_rows = {}
        for chart_pos in layout.charts:
            row = chart_pos.y
            if row not in chart_rows:
                chart_rows[row] = []
            chart_rows[row].append(chart_pos)
        
        # Render each row
        for row in sorted(chart_rows.keys()):
            row_charts = sorted(chart_rows[row], key=lambda x: x.x)
            
            if len(row_charts) == 1:
                # Single chart in row
                chart_pos = row_charts[0]
                if chart_pos.chart_id in charts:
                    fig = charts[chart_pos.chart_id]
                    fig.update_layout(
                        title=chart_pos.title or fig.layout.title.text,
                        height=chart_pos.height * 100
                    )
                    st.plotly_chart(fig, use_container_width=True, key=f"custom_chart_{chart_pos.chart_id}")
            else:
                # Multiple charts in row
                cols = st.columns([pos.width for pos in row_charts])
                
                for col, chart_pos in zip(cols, row_charts):
                    with col:
                        if chart_pos.chart_id in charts:
                            fig = charts[chart_pos.chart_id]
                            fig.update_layout(
                                title=chart_pos.title or fig.layout.title.text,
                                height=chart_pos.height * 100
                            )
                            st.plotly_chart(fig, use_container_width=True, key=f"custom_chart_{chart_pos.chart_id}")
    
    def render_layout_builder(self) -> Optional[str]:
        """Render interactive layout builder interface."""
        st.subheader("🏗️ Dashboard Layout Builder")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Layout configuration
            st.write("**Create New Layout**")
            
            layout_name = st.text_input("Layout Name", value="My Dashboard")
            
            layout_type = st.selectbox(
                "Layout Type",
                options=[layout.value for layout in LayoutType],
                format_func=lambda x: x.replace('_', ' ').title()
            )
            
            if layout_type == LayoutType.GRID.value:
                columns = st.slider("Columns", min_value=1, max_value=12, value=12)
                rows = st.slider("Rows", min_value=1, max_value=12, value=8)
            else:
                columns = 12
                rows = 8
            
            if st.button("Create Layout", type="primary"):
                layout = self.create_layout(
                    layout_name, 
                    LayoutType(layout_type),
                    columns,
                    rows
                )
                st.success(f"Layout '{layout_name}' created with ID: {layout.id}")
                return layout.id
        
        with col2:
            # Preview existing layouts
            st.write("**Existing Layouts**")
            
            if self.layouts:
                layout_options = {f"{layout.name} ({layout.id})": layout.id 
                                for layout in self.layouts.values()}
                
                selected = st.selectbox(
                    "Select Layout to Preview",
                    list(layout_options.keys())
                )
                
                if selected:
                    layout_id = layout_options[selected]
                    layout = self.layouts[layout_id]
                    
                    st.json(asdict(layout))
                    
                    if st.button("Delete Layout"):
                        del self.layouts[layout_id]
                        st.success(f"Layout deleted")
                        st.rerun()
            else:
                st.info("No layouts created yet")
        
        return None
    
    def export_layout(self, layout_id: str) -> Optional[str]:
        """Export layout configuration as JSON."""
        if layout_id not in self.layouts:
            return None
            
        layout = self.layouts[layout_id]
        layout_dict = asdict(layout)
        
        # Convert LayoutType enum to string for JSON serialization
        if 'layout_type' in layout_dict:
            layout_dict['layout_type'] = layout_dict['layout_type'].value
        
        return json.dumps(layout_dict, indent=2)
    
    def import_layout(self, layout_json: str) -> bool:
        """Import layout configuration from JSON."""
        try:
            layout_data = json.loads(layout_json)
            
            # Convert dict back to dataclass
            layout = DashboardLayout(
                id=layout_data['id'],
                name=layout_data['name'],
                layout_type=LayoutType(layout_data['layout_type']),
                columns=layout_data['columns'],
                rows=layout_data['rows'],
                charts=[ChartPosition(**chart) for chart in layout_data['charts']],
                global_config=layout_data['global_config']
            )
            
            self.layouts[layout.id] = layout
            return True
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            st.error(f"Error importing layout: {e}")
            return False
    
    def create_subplot_dashboard(self, charts: Dict[str, go.Figure],
                               layout_config: Dict[str, Any]) -> go.Figure:
        """Create a single figure with multiple subplots."""
        chart_list = list(charts.items())
        num_charts = len(chart_list)
        
        if num_charts == 0:
            return go.Figure()
        
        # Calculate subplot arrangement
        if num_charts == 1:
            rows, cols = 1, 1
        elif num_charts == 2:
            rows, cols = 1, 2
        elif num_charts <= 4:
            rows, cols = 2, 2
        elif num_charts <= 6:
            rows, cols = 2, 3
        else:
            rows = int(num_charts**0.5) + 1
            cols = int(num_charts / rows) + 1
        
        # Create subplots
        subplot_titles = [name for name, _ in chart_list]
        fig = make_subplots(
            rows=rows,
            cols=cols,
            subplot_titles=subplot_titles,
            specs=[[{"secondary_y": False} for _ in range(cols)] for _ in range(rows)]
        )
        
        # Add charts to subplots
        for i, (name, chart) in enumerate(chart_list):
            row = (i // cols) + 1
            col = (i % cols) + 1
            
            # Add traces from original chart
            for trace in chart.data:
                fig.add_trace(trace, row=row, col=col)
        
        # Update layout
        fig.update_layout(
            title=layout_config.get('title', 'Dashboard'),
            height=layout_config.get('height', 800),
            showlegend=layout_config.get('show_legend', True)
        )
        
        return fig
    
    def get_responsive_config(self) -> Dict[str, Any]:
        """Get responsive configuration for mobile/tablet viewing."""
        return {
            'responsive': True,
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': [
                'pan2d', 'lasso2d', 'select2d', 'autoScale2d', 'hoverClosestCartesian',
                'hoverCompareCartesian', 'toggleHover', 'toggleSpikelines'
            ],
            'toImageButtonOptions': {
                'format': 'png',
                'filename': 'dashboard',
                'height': 800,
                'width': 1200,
                'scale': 2
            }
        }