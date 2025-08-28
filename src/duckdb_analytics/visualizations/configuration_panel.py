"""Interactive chart configuration panel."""

import streamlit as st
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from .chart_types import ChartType


class ChartConfigurationPanel:
    """Interactive configuration panel for chart customization."""
    
    def __init__(self):
        self.color_schemes = [
            'viridis', 'plasma', 'inferno', 'magma', 'cividis',
            'blues', 'reds', 'greens', 'purples', 'oranges', 'greys',
            'plotly', 'set1', 'set2', 'set3', 'pastel1', 'pastel2'
        ]
        
    def render(self, chart_type: ChartType, df: pd.DataFrame,
               current_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Render configuration panel and return updated config."""
        if current_config is None:
            current_config = {}
            
        with st.sidebar:
            st.subheader("🎨 Chart Configuration")
            
            config = self._render_basic_settings(current_config)
            config.update(self._render_color_settings(current_config))
            config.update(self._render_layout_settings(current_config))
            
            # Chart-specific settings
            if chart_type in [ChartType.HEATMAP, ChartType.BOX_PLOT, ChartType.SCATTER_MATRIX]:
                config.update(self._render_axis_settings(current_config))
            
            if chart_type == ChartType.GAUGE:
                config.update(self._render_gauge_settings(current_config))
                
            if chart_type in [ChartType.TREEMAP, ChartType.SANKEY]:
                config.update(self._render_hierarchy_settings(current_config))
                
            config.update(self._render_data_settings(df, current_config))
            
        return config
    
    def _render_basic_settings(self, current_config: Dict[str, Any]) -> Dict[str, Any]:
        """Render basic chart settings."""
        config = {}
        
        with st.expander("📊 Basic Settings", expanded=True):
            config['title'] = st.text_input(
                "Chart Title",
                value=current_config.get('title', ''),
                key="chart_title"
            )
            
            config['height'] = st.slider(
                "Chart Height",
                min_value=200,
                max_value=1000,
                value=current_config.get('height', 500),
                step=50,
                key="chart_height"
            )
            
            config['width'] = st.slider(
                "Chart Width",
                min_value=400,
                max_value=1400,
                value=current_config.get('width', 800),
                step=50,
                key="chart_width"
            )
            
            config['font_size'] = st.slider(
                "Font Size",
                min_value=8,
                max_value=20,
                value=current_config.get('font_size', 12),
                key="font_size"
            )
        
        return config
    
    def _render_color_settings(self, current_config: Dict[str, Any]) -> Dict[str, Any]:
        """Render color and theme settings."""
        config = {}
        
        with st.expander("🎨 Colors & Theme"):
            config['color_scheme'] = st.selectbox(
                "Color Scheme",
                self.color_schemes,
                index=self.color_schemes.index(current_config.get('color_scheme', 'viridis'))
                if current_config.get('color_scheme') in self.color_schemes else 0,
                key="color_scheme"
            )
            
            config['background_color'] = st.color_picker(
                "Background Color",
                value=current_config.get('background_color', '#ffffff'),
                key="bg_color"
            )
            
            config['grid_color'] = st.color_picker(
                "Grid Color",
                value=current_config.get('grid_color', '#e6e6e6'),
                key="grid_color"
            )
            
            config['text_color'] = st.color_picker(
                "Text Color", 
                value=current_config.get('text_color', '#000000'),
                key="text_color"
            )
            
        return config
    
    def _render_layout_settings(self, current_config: Dict[str, Any]) -> Dict[str, Any]:
        """Render layout and positioning settings."""
        config = {}
        
        with st.expander("📐 Layout & Position"):
            config['show_legend'] = st.checkbox(
                "Show Legend",
                value=current_config.get('show_legend', True),
                key="show_legend"
            )
            
            if config['show_legend']:
                config['legend_position'] = st.selectbox(
                    "Legend Position",
                    ['top', 'bottom', 'left', 'right', 'top-left', 'top-right', 
                     'bottom-left', 'bottom-right'],
                    index=0,
                    key="legend_pos"
                )
            
            config['show_grid'] = st.checkbox(
                "Show Grid",
                value=current_config.get('show_grid', True),
                key="show_grid"
            )
            
            config['margin_top'] = st.slider(
                "Top Margin",
                min_value=0,
                max_value=100,
                value=current_config.get('margin_top', 20),
                key="margin_top"
            )
            
            config['margin_bottom'] = st.slider(
                "Bottom Margin", 
                min_value=0,
                max_value=100,
                value=current_config.get('margin_bottom', 20),
                key="margin_bottom"
            )
            
        return config
    
    def _render_axis_settings(self, current_config: Dict[str, Any]) -> Dict[str, Any]:
        """Render axis configuration settings."""
        config = {}
        
        with st.expander("📏 Axes"):
            config['x_title'] = st.text_input(
                "X-Axis Title",
                value=current_config.get('x_title', ''),
                key="x_title"
            )
            
            config['y_title'] = st.text_input(
                "Y-Axis Title",
                value=current_config.get('y_title', ''),
                key="y_title"
            )
            
            config['x_tickangle'] = st.slider(
                "X-Axis Label Rotation",
                min_value=-90,
                max_value=90,
                value=current_config.get('x_tickangle', 0),
                key="x_tickangle"
            )
            
            config['y_tickangle'] = st.slider(
                "Y-Axis Label Rotation",
                min_value=-90,
                max_value=90,
                value=current_config.get('y_tickangle', 0),
                key="y_tickangle"
            )
            
            config['x_showticklabels'] = st.checkbox(
                "Show X-Axis Labels",
                value=current_config.get('x_showticklabels', True),
                key="x_showlabels"
            )
            
            config['y_showticklabels'] = st.checkbox(
                "Show Y-Axis Labels",
                value=current_config.get('y_showticklabels', True),
                key="y_showlabels"
            )
            
        return config
    
    def _render_gauge_settings(self, current_config: Dict[str, Any]) -> Dict[str, Any]:
        """Render gauge-specific settings."""
        config = {}
        
        with st.expander("🔢 Gauge Settings"):
            config['min_value'] = st.number_input(
                "Minimum Value",
                value=current_config.get('min_value', 0),
                key="gauge_min"
            )
            
            config['max_value'] = st.number_input(
                "Maximum Value",
                value=current_config.get('max_value', 100),
                key="gauge_max"
            )
            
            config['threshold'] = st.number_input(
                "Threshold Value",
                value=current_config.get('threshold', 80),
                min_value=config['min_value'],
                max_value=config['max_value'],
                key="gauge_threshold"
            )
            
            config['show_needle'] = st.checkbox(
                "Show Needle",
                value=current_config.get('show_needle', True),
                key="show_needle"
            )
            
            config['gauge_shape'] = st.selectbox(
                "Gauge Shape",
                ['angular', 'bullet'],
                index=0,
                key="gauge_shape"
            )
            
        return config
    
    def _render_hierarchy_settings(self, current_config: Dict[str, Any]) -> Dict[str, Any]:
        """Render settings for hierarchical charts."""
        config = {}
        
        with st.expander("🌳 Hierarchy Settings"):
            config['max_depth'] = st.slider(
                "Maximum Depth",
                min_value=1,
                max_value=5,
                value=current_config.get('max_depth', 3),
                key="max_depth"
            )
            
            config['show_values'] = st.checkbox(
                "Show Values",
                value=current_config.get('show_values', True),
                key="show_values"
            )
            
            config['show_percentages'] = st.checkbox(
                "Show Percentages",
                value=current_config.get('show_percentages', True),
                key="show_percentages"
            )
            
            if current_config.get('chart_type') == ChartType.TREEMAP:
                config['treemap_textinfo'] = st.selectbox(
                    "Text Information",
                    ['label', 'label+value', 'label+percent root', 'label+value+percent root'],
                    index=3,
                    key="treemap_textinfo"
                )
                
        return config
    
    def _render_data_settings(self, df: pd.DataFrame, 
                             current_config: Dict[str, Any]) -> Dict[str, Any]:
        """Render data-related settings."""
        config = {}
        
        with st.expander("📊 Data Settings"):
            config['sample_data'] = st.checkbox(
                "Use Data Sampling",
                value=current_config.get('sample_data', False),
                help="Sample data for better performance with large datasets",
                key="sample_data"
            )
            
            if config['sample_data']:
                max_rows = min(len(df), 10000)
                config['sample_size'] = st.slider(
                    "Sample Size",
                    min_value=100,
                    max_value=max_rows,
                    value=min(current_config.get('sample_size', 1000), max_rows),
                    key="sample_size"
                )
            
            config['sort_data'] = st.checkbox(
                "Sort Data",
                value=current_config.get('sort_data', False),
                key="sort_data"
            )
            
            if config['sort_data']:
                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                all_cols = df.columns.tolist()
                
                config['sort_by'] = st.selectbox(
                    "Sort By Column",
                    all_cols,
                    index=0,
                    key="sort_by"
                )
                
                config['sort_ascending'] = st.checkbox(
                    "Ascending Order",
                    value=current_config.get('sort_ascending', True),
                    key="sort_ascending"
                )
            
            # Data filtering
            config['filter_data'] = st.checkbox(
                "Apply Filters",
                value=current_config.get('filter_data', False),
                key="filter_data"
            )
            
            if config['filter_data']:
                config['filters'] = self._render_data_filters(df, current_config.get('filters', {}))
                
        return config
    
    def _render_data_filters(self, df: pd.DataFrame, 
                            current_filters: Dict[str, Any]) -> Dict[str, Any]:
        """Render data filtering controls."""
        filters = {}
        
        st.subheader("🔍 Data Filters")
        
        # Column-based filters
        for col in df.columns:
            col_type = df[col].dtype
            
            if col_type in ['int64', 'float64']:
                # Numeric filter
                min_val = float(df[col].min())
                max_val = float(df[col].max())
                
                filter_range = st.slider(
                    f"{col} Range",
                    min_value=min_val,
                    max_value=max_val,
                    value=current_filters.get(col, (min_val, max_val)),
                    key=f"filter_{col}"
                )
                filters[col] = filter_range
                
            elif col_type == 'object':
                # Categorical filter
                unique_values = df[col].unique().tolist()
                if len(unique_values) <= 20:  # Only show for reasonable number of categories
                    selected_values = st.multiselect(
                        f"{col} Values",
                        unique_values,
                        default=current_filters.get(col, unique_values),
                        key=f"filter_{col}"
                    )
                    filters[col] = selected_values
        
        return filters
    
    def apply_config(self, fig, config: Dict[str, Any]):
        """Apply configuration to a plotly figure."""
        # Update layout
        layout_updates = {
            'title': config.get('title', ''),
            'height': config.get('height', 500),
            'width': config.get('width', 800),
            'font': {'size': config.get('font_size', 12)},
            'plot_bgcolor': config.get('background_color', '#ffffff'),
            'paper_bgcolor': config.get('background_color', '#ffffff'),
            'showlegend': config.get('show_legend', True)
        }
        
        # Grid settings
        if config.get('show_grid', True):
            layout_updates['xaxis'] = {'showgrid': True, 'gridcolor': config.get('grid_color', '#e6e6e6')}
            layout_updates['yaxis'] = {'showgrid': True, 'gridcolor': config.get('grid_color', '#e6e6e6')}
        
        # Axis titles
        if config.get('x_title'):
            layout_updates.setdefault('xaxis', {})['title'] = config['x_title']
        if config.get('y_title'):
            layout_updates.setdefault('yaxis', {})['title'] = config['y_title']
            
        # Axis label settings
        if 'x_tickangle' in config:
            layout_updates.setdefault('xaxis', {})['tickangle'] = config['x_tickangle']
        if 'y_tickangle' in config:
            layout_updates.setdefault('yaxis', {})['tickangle'] = config['y_tickangle']
            
        if 'x_showticklabels' in config:
            layout_updates.setdefault('xaxis', {})['showticklabels'] = config['x_showticklabels']
        if 'y_showticklabels' in config:
            layout_updates.setdefault('yaxis', {})['showticklabels'] = config['y_showticklabels']
        
        # Margins
        layout_updates['margin'] = {
            't': config.get('margin_top', 20),
            'b': config.get('margin_bottom', 20),
            'l': 50,
            'r': 20
        }
        
        # Legend position
        if config.get('legend_position'):
            legend_positions = {
                'top': {'x': 0.5, 'y': 1.1, 'xanchor': 'center'},
                'bottom': {'x': 0.5, 'y': -0.1, 'xanchor': 'center'},
                'left': {'x': -0.1, 'y': 0.5, 'yanchor': 'middle'},
                'right': {'x': 1.1, 'y': 0.5, 'yanchor': 'middle'},
                'top-left': {'x': 0, 'y': 1},
                'top-right': {'x': 1, 'y': 1},
                'bottom-left': {'x': 0, 'y': 0},
                'bottom-right': {'x': 1, 'y': 0}
            }
            legend_pos = legend_positions.get(config['legend_position'], {})
            layout_updates['legend'] = legend_pos
        
        fig.update_layout(**layout_updates)
        
        return fig
    
    def get_preview_config(self, chart_type: ChartType) -> Dict[str, Any]:
        """Get default configuration for chart preview."""
        base_config = {
            'title': f'Sample {chart_type.value.title().replace("_", " ")}',
            'height': 400,
            'width': 600,
            'show_legend': True,
            'color_scheme': 'viridis'
        }
        
        return base_config