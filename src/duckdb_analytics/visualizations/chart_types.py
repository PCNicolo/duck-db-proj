"""Advanced chart types for enhanced visualizations."""

from enum import Enum
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


class ChartType(Enum):
    """Available chart types."""

    HEATMAP = "heatmap"
    TREEMAP = "treemap"
    SANKEY = "sankey"
    BOX_PLOT = "box_plot"
    SCATTER_MATRIX = "scatter_matrix"
    GAUGE = "gauge"
    WATERFALL = "waterfall"
    RADAR = "radar"


def create_heatmap(
    df: pd.DataFrame,
    x: str,
    y: str,
    values: str,
    config: Optional[Dict[str, Any]] = None,
) -> go.Figure:
    """Create a heatmap visualization."""
    config = config or {}

    # Handle potential issues with column names that might be reserved or problematic
    try:
        # Make a copy to avoid modifying the original dataframe
        df_copy = df.copy()

        # Reset index if necessary to avoid multi-index issues
        if isinstance(df_copy.index, pd.MultiIndex):
            df_copy = df_copy.reset_index()

        # Ensure the required columns exist
        if x not in df_copy.columns:
            raise ValueError(f"Column '{x}' not found in dataframe")
        if y not in df_copy.columns:
            raise ValueError(f"Column '{y}' not found in dataframe")
        if values not in df_copy.columns:
            raise ValueError(f"Column '{values}' not found in dataframe")

        # Create pivot table for heatmap
        pivot_df = df_copy.pivot_table(
            index=y, columns=x, values=values, aggfunc=config.get("aggregation", "mean")
        )

        # Handle empty pivot table
        if pivot_df.empty:
            raise ValueError("Pivot table resulted in empty dataframe")

    except Exception as e:
        # Fallback to a simple error message if pivot fails
        import streamlit as st

        st.error(f"Error creating heatmap: {str(e)}")
        # Create a minimal figure with error message
        fig = go.Figure()
        fig.add_annotation(
            text=f"Unable to create heatmap: {str(e)}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )
        fig.update_layout(height=config.get("height", 500))
        return fig

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot_df.values,
            x=pivot_df.columns,
            y=pivot_df.index,
            colorscale=config.get("color_scheme", "viridis"),
            showscale=True,
        )
    )

    fig.update_layout(
        title=config.get("title", "Heatmap"),
        xaxis_title=x,
        yaxis_title=y,
        height=config.get("height", 500),
    )

    return fig


def create_treemap(
    df: pd.DataFrame,
    labels: str,
    values: str,
    parents: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> go.Figure:
    """Create a treemap visualization."""
    config = config or {}

    # Prepare data for treemap
    treemap_data = df.copy()

    if parents is None:
        # Create a simple treemap without hierarchy
        fig = go.Figure(
            go.Treemap(
                labels=treemap_data[labels],
                values=treemap_data[values],
                textinfo="label+value+percent root",
                texttemplate="<b>%{label}</b><br>%{value}<br>%{percentRoot}",
                pathbar_visible=False,
            )
        )
    else:
        # Create hierarchical treemap
        fig = go.Figure(
            go.Treemap(
                labels=treemap_data[labels],
                values=treemap_data[values],
                parents=treemap_data[parents],
                textinfo="label+value+percent root",
                texttemplate="<b>%{label}</b><br>%{value}<br>%{percentRoot}",
                pathbar_visible=True,
            )
        )

    fig.update_layout(
        title=config.get("title", "Treemap"),
        height=config.get("height", 500),
        font_size=config.get("font_size", 12),
    )

    return fig


def create_sankey(
    df: pd.DataFrame,
    source: str,
    target: str,
    value: str,
    config: Optional[Dict[str, Any]] = None,
) -> go.Figure:
    """Create a Sankey diagram visualization."""
    config = config or {}

    # Prepare data for sankey
    sources = df[source].tolist()
    targets = df[target].tolist()
    values = df[value].tolist()

    # Get unique nodes
    all_nodes = list(set(sources + targets))
    node_dict = {node: i for i, node in enumerate(all_nodes)}

    # Map sources and targets to indices
    source_indices = [node_dict[s] for s in sources]
    target_indices = [node_dict[t] for t in targets]

    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    pad=15,
                    thickness=20,
                    line=dict(color="black", width=0.5),
                    label=all_nodes,
                    color=config.get("node_color", "blue"),
                ),
                link=dict(
                    source=source_indices,
                    target=target_indices,
                    value=values,
                    color=config.get("link_color", "rgba(0,0,255,0.3)"),
                ),
            )
        ]
    )

    fig.update_layout(
        title=config.get("title", "Sankey Diagram"),
        font_size=config.get("font_size", 10),
        height=config.get("height", 600),
    )

    return fig


def create_box_plot(
    df: pd.DataFrame, x: Optional[str], y: str, config: Optional[Dict[str, Any]] = None
) -> go.Figure:
    """Create a box plot visualization."""
    config = config or {}

    if x:
        fig = px.box(
            df,
            x=x,
            y=y,
            title=config.get("title", "Box Plot"),
            color=config.get("color_by"),
        )
    else:
        fig = px.box(df, y=y, title=config.get("title", "Box Plot"))

    fig.update_layout(
        height=config.get("height", 500), showlegend=config.get("show_legend", True)
    )

    return fig


def create_scatter_matrix(
    df: pd.DataFrame,
    dimensions: List[str],
    color_by: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> go.Figure:
    """Create a scatter plot matrix."""
    config = config or {}

    fig = px.scatter_matrix(
        df,
        dimensions=dimensions,
        color=color_by,
        title=config.get("title", "Scatter Plot Matrix"),
        height=config.get("height", 800),
    )

    fig.update_traces(diagonal_visible=False)
    return fig


def create_gauge_chart(
    value: float, title: str, config: Optional[Dict[str, Any]] = None
) -> go.Figure:
    """Create a gauge chart for KPI display."""
    config = config or {}

    min_val = config.get("min", 0)
    max_val = config.get("max", 100)
    threshold_colors = config.get(
        "threshold_colors", {"low": "red", "medium": "yellow", "high": "green"}
    )

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=value,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": title},
            delta={"reference": config.get("reference", max_val * 0.8)},
            gauge={
                "axis": {"range": [None, max_val]},
                "bar": {"color": config.get("bar_color", "darkblue")},
                "steps": [
                    {
                        "range": [min_val, max_val * 0.3],
                        "color": threshold_colors["low"],
                    },
                    {
                        "range": [max_val * 0.3, max_val * 0.7],
                        "color": threshold_colors["medium"],
                    },
                    {
                        "range": [max_val * 0.7, max_val],
                        "color": threshold_colors["high"],
                    },
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": config.get("threshold", max_val * 0.9),
                },
            },
        )
    )

    fig.update_layout(height=config.get("height", 400))
    return fig


def create_waterfall_chart(
    df: pd.DataFrame, x: str, y: str, config: Optional[Dict[str, Any]] = None
) -> go.Figure:
    """Create a waterfall chart for financial data."""
    config = config or {}

    # Calculate cumulative values for waterfall
    values = df[y].tolist()
    categories = df[x].tolist()

    # Create waterfall chart
    fig = go.Figure(
        go.Waterfall(
            name="Waterfall",
            orientation="v",
            measure=config.get("measure", ["relative"] * len(values)),
            x=categories,
            y=values,
            textposition="outside",
            text=[f"{val:+.1f}" for val in values],
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            increasing={"marker": {"color": config.get("increasing_color", "green")}},
            decreasing={"marker": {"color": config.get("decreasing_color", "red")}},
            totals={"marker": {"color": config.get("total_color", "blue")}},
        )
    )

    fig.update_layout(
        title=config.get("title", "Waterfall Chart"),
        showlegend=config.get("show_legend", True),
        height=config.get("height", 500),
    )

    return fig


def create_radar_chart(
    df: pd.DataFrame,
    categories: List[str],
    values_col: str,
    group_by: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> go.Figure:
    """Create a radar/spider chart."""
    config = config or {}

    fig = go.Figure()

    if group_by:
        # Multiple series radar chart
        groups = df[group_by].unique()
        for group in groups:
            group_data = df[df[group_by] == group]
            fig.add_trace(
                go.Scatterpolar(
                    r=group_data[values_col],
                    theta=(
                        group_data[categories[0]]
                        if len(categories) == 1
                        else categories
                    ),
                    fill="toself",
                    name=str(group),
                )
            )
    else:
        # Single series radar chart
        fig.add_trace(
            go.Scatterpolar(
                r=df[values_col],
                theta=df[categories[0]] if len(categories) == 1 else categories,
                fill="toself",
                name=config.get("series_name", "Series"),
            )
        )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, df[values_col].max() * 1.1])
        ),
        showlegend=config.get("show_legend", True),
        title=config.get("title", "Radar Chart"),
        height=config.get("height", 500),
    )

    return fig
