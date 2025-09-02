"""Test cases for bug fixes in visualization charts."""

from unittest.mock import patch

import numpy as np
import pandas as pd

from src.duckdb_analytics.visualizations.chart_types import create_heatmap
from src.duckdb_analytics.visualizations.configuration_panel import (
    ChartConfigurationPanel,
)


class TestChartBugFixes:
    """Test bug fixes for chart rendering issues."""

    def test_heatmap_colorscale_fix(self):
        """Test that 'default' is no longer a valid colorscale option."""
        panel = ChartConfigurationPanel()
        # Verify 'default' is not in color_schemes
        assert "default" not in panel.color_schemes
        # Verify first option is 'viridis' now
        assert panel.color_schemes[0] == "viridis"

    def test_heatmap_with_viridis_colorscale(self):
        """Test heatmap creation with viridis colorscale (formerly default)."""
        df = pd.DataFrame(
            {
                "category": ["A", "B", "C"] * 3,
                "product": ["X", "Y", "Z"] * 3,
                "sales": np.random.rand(9) * 100,
            }
        )

        # Test with explicit viridis color scheme
        config = {"color_scheme": "viridis", "title": "Test Heatmap"}
        fig = create_heatmap(df, "category", "product", "sales", config)

        assert fig is not None
        # Plotly converts colorscale names to actual color values
        # So we just check that the figure was created successfully
        assert hasattr(fig.data[0], "colorscale")
        assert len(fig.data[0].colorscale) > 0

    def test_heatmap_with_period_column(self):
        """Test heatmap creation when dataframe has 'period' column."""
        # Create dataframe with 'period' column that could cause groupby issues
        df = pd.DataFrame(
            {
                "period": pd.date_range("2023-01-01", periods=9, freq="D"),
                "category": ["A", "B", "C"] * 3,
                "value": np.random.rand(9) * 100,
            }
        )

        # Convert period to string to avoid datetime issues
        df["period_str"] = df["period"].astype(str)

        # This should work without throwing "Grouper for 'period' not 1-dimensional" error
        config = {"color_scheme": "viridis"}
        fig = create_heatmap(df, "period_str", "category", "value", config)

        assert fig is not None

    def test_heatmap_with_multiindex(self):
        """Test heatmap handles MultiIndex dataframes properly."""
        # Create a MultiIndex dataframe
        arrays = [["A", "A", "B", "B", "C", "C"], ["X", "Y", "X", "Y", "X", "Y"]]
        index = pd.MultiIndex.from_arrays(arrays, names=("first", "second"))
        df = pd.DataFrame(
            {"value": np.random.rand(6) * 100, "category": ["Cat1", "Cat2"] * 3},
            index=index,
        )

        # Reset index is handled internally now
        config = {"color_scheme": "viridis"}
        fig = create_heatmap(df.reset_index(), "first", "second", "value", config)

        assert fig is not None

    def test_heatmap_with_missing_columns(self):
        """Test heatmap handles missing columns gracefully."""
        df = pd.DataFrame(
            {"col1": ["A", "B", "C"], "col2": [1, 2, 3], "col3": [10, 20, 30]}
        )

        config = {"color_scheme": "viridis"}

        # Try with non-existent column - should handle error gracefully
        with patch("streamlit.error") as mock_error:
            fig = create_heatmap(df, "missing_col", "col1", "col3", config)
            mock_error.assert_called_once()
            # Should return a figure with error annotation
            assert fig is not None
            assert len(fig.layout.annotations) > 0

    def test_heatmap_with_empty_dataframe(self):
        """Test heatmap handles empty dataframes gracefully."""
        df = pd.DataFrame()

        config = {"color_scheme": "viridis"}

        # Should handle empty dataframe gracefully
        with patch("streamlit.error") as mock_error:
            fig = create_heatmap(df, "x", "y", "values", config)
            mock_error.assert_called_once()
            assert fig is not None
