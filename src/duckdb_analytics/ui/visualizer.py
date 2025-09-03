"""
Unified visualization component with auto-detection and manual override.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, Literal

ChartType = Literal["auto", "line", "bar", "scatter", "pie", "heatmap", "table"]

class SmartVisualizer:
    """Smart visualization with auto-detection."""
    
    def __init__(self, recommendation_engine):
        self.recommendation_engine = recommendation_engine
    
    def render(self, df: pd.DataFrame, default_type: ChartType = "auto"):
        """Render the visualization component."""
        if df is None or df.empty:
            st.info("No data to visualize. Run a query first.")
            return
        
        # Controls
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            view_mode = st.radio(
                "View as:",
                ["Table", "Chart"],
                horizontal=True,
                key="view_mode"
            )
        
        with col2:
            if view_mode == "Chart":
                chart_type = st.selectbox(
                    "Chart type:",
                    ["auto", "line", "bar", "scatter", "pie", "heatmap"],
                    key="chart_type"
                )
            else:
                chart_type = "table"
        
        with col3:
            # Export button placeholder
            if st.button("📥 Export", help="Export visualization"):
                st.info("Export functionality coming soon!")
        
        # Display visualization
        if view_mode == "Table":
            self.render_table(df)
        else:
            self.render_chart(df, chart_type)
        
        # Show data summary
        st.caption(f"📊 {len(df):,} rows × {len(df.columns)} columns")
    
    def render_table(self, df: pd.DataFrame):
        """Render data as a table."""
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
    
    def render_chart(self, df: pd.DataFrame, chart_type: ChartType):
        """Render data as a chart."""
        
        # Auto-detect best chart type
        if chart_type == "auto":
            chart_type = self.detect_best_chart(df)
            st.info(f"Auto-selected: {chart_type.title()} chart")
        
        try:
            if chart_type == "line":
                self.render_line_chart(df)
            elif chart_type == "bar":
                self.render_bar_chart(df)
            elif chart_type == "scatter":
                self.render_scatter_chart(df)
            elif chart_type == "pie":
                self.render_pie_chart(df)
            elif chart_type == "heatmap":
                self.render_heatmap(df)
            else:
                self.render_table(df)
        except Exception as e:
            st.error(f"Could not create {chart_type} chart: {str(e)}")
            st.info("Showing data as table instead:")
            self.render_table(df)
    
    def detect_best_chart(self, df: pd.DataFrame) -> str:
        """Auto-detect the best chart type for the data."""
        
        # Use recommendation engine if available
        try:
            recommendations = self.recommendation_engine.recommend_charts(df)
            if recommendations:
                return recommendations[0].chart_type
        except:
            pass
        
        # Fallback to simple heuristics
        num_cols = len(df.columns)
        num_rows = len(df)
        
        # Check data types
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
        
        # Time series data -> Line chart
        if datetime_cols and numeric_cols:
            return "line"
        
        # Two columns, one categorical, one numeric -> Bar or Pie
        if num_cols == 2:
            if len(numeric_cols) == 1:
                if num_rows <= 10:
                    return "pie"
                else:
                    return "bar"
        
        # Two numeric columns -> Scatter
        if len(numeric_cols) >= 2:
            return "scatter"
        
        # Three columns suitable for pivot -> Heatmap
        if num_cols >= 3 and len(numeric_cols) >= 1:
            return "heatmap"
        
        # Default to bar chart
        return "bar"
    
    def render_line_chart(self, df: pd.DataFrame):
        """Render a line chart."""
        if len(df.columns) < 2:
            st.warning("Line chart requires at least 2 columns")
            return
        
        # Use first column as x-axis, rest as y-values
        x_col = df.columns[0]
        y_cols = df.columns[1:].tolist()
        
        fig = px.line(df, x=x_col, y=y_cols, title="Line Chart")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    def render_bar_chart(self, df: pd.DataFrame):
        """Render a bar chart."""
        if len(df.columns) < 2:
            st.warning("Bar chart requires at least 2 columns")
            return
        
        x_col = df.columns[0]
        y_col = df.columns[1]
        
        fig = px.bar(df, x=x_col, y=y_col, title="Bar Chart")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    def render_scatter_chart(self, df: pd.DataFrame):
        """Render a scatter plot."""
        if len(df.columns) < 2:
            st.warning("Scatter plot requires at least 2 columns")
            return
        
        x_col = df.columns[0]
        y_col = df.columns[1]
        
        # Add size/color if available
        size_col = df.columns[2] if len(df.columns) > 2 else None
        color_col = df.columns[3] if len(df.columns) > 3 else None
        
        fig = px.scatter(
            df, x=x_col, y=y_col,
            size=size_col, color=color_col,
            title="Scatter Plot"
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    def render_pie_chart(self, df: pd.DataFrame):
        """Render a pie chart."""
        if len(df.columns) < 2:
            st.warning("Pie chart requires at least 2 columns")
            return
        
        names_col = df.columns[0]
        values_col = df.columns[1]
        
        fig = px.pie(df, names=names_col, values=values_col, title="Pie Chart")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    def render_heatmap(self, df: pd.DataFrame):
        """Render a heatmap."""
        if len(df.columns) < 3:
            st.warning("Heatmap requires at least 3 columns")
            return
        
        try:
            # Try to create a pivot table
            pivot = df.pivot_table(
                index=df.columns[0],
                columns=df.columns[1],
                values=df.columns[2],
                aggfunc='mean'
            )
            
            fig = go.Figure(data=go.Heatmap(
                z=pivot.values,
                x=pivot.columns.tolist(),
                y=pivot.index.tolist(),
                colorscale='Blues'
            ))
            fig.update_layout(title="Heatmap", height=400)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Cannot create heatmap: {str(e)}")
            self.render_table(df)