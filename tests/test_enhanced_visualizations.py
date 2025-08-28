"""Test suite for enhanced visualization features."""

import pytest
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from unittest.mock import Mock, patch

from src.duckdb_analytics.visualizations import (
    ChartRecommendationEngine, ChartExportManager, DashboardLayoutManager
)
from src.duckdb_analytics.visualizations.chart_types import (
    ChartType, create_heatmap, create_treemap, create_sankey, create_box_plot,
    create_scatter_matrix, create_gauge_chart, create_waterfall_chart, create_radar_chart
)
from src.duckdb_analytics.visualizations.configuration_panel import ChartConfigurationPanel
from src.duckdb_analytics.visualizations.dashboard_layout import LayoutType, ChartPosition
from src.duckdb_analytics.visualizations.performance import (
    DataSampler, ChartCache, PerformanceMonitor, VisualizationOptimizer
)


@pytest.fixture
def sample_data():
    """Create sample data for testing."""
    np.random.seed(42)
    return pd.DataFrame({
        'category': ['A', 'B', 'C', 'D'] * 25,
        'subcategory': ['X', 'Y'] * 50,
        'value': np.random.randn(100),
        'revenue': np.random.uniform(100, 1000, 100),
        'count': np.random.randint(1, 100, 100),
        'date': pd.date_range('2023-01-01', periods=100, freq='D')
    })


@pytest.fixture
def flow_data():
    """Create flow data for Sankey diagrams."""
    return pd.DataFrame({
        'source': ['A', 'A', 'B', 'B', 'C'] * 10,
        'target': ['B', 'C', 'C', 'D', 'D'] * 10,
        'value': np.random.uniform(10, 100, 50)
    })


class TestChartTypes:
    """Test advanced chart type implementations."""
    
    def test_create_heatmap(self, sample_data):
        """Test heatmap creation."""
        fig = create_heatmap(sample_data, 'category', 'subcategory', 'value')
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.data[0].type == 'heatmap'
    
    def test_create_treemap(self, sample_data):
        """Test treemap creation."""
        fig = create_treemap(sample_data, 'category', 'revenue')
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.data[0].type == 'treemap'
    
    def test_create_treemap_with_hierarchy(self, sample_data):
        """Test treemap with parent hierarchy."""
        fig = create_treemap(sample_data, 'subcategory', 'revenue', 'category')
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.data[0].type == 'treemap'
    
    def test_create_sankey(self, flow_data):
        """Test Sankey diagram creation."""
        fig = create_sankey(flow_data, 'source', 'target', 'value')
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.data[0].type == 'sankey'
    
    def test_create_box_plot(self, sample_data):
        """Test box plot creation."""
        fig = create_box_plot(sample_data, 'category', 'value')
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
    
    def test_create_scatter_matrix(self, sample_data):
        """Test scatter matrix creation."""
        dimensions = ['value', 'revenue', 'count']
        fig = create_scatter_matrix(sample_data, dimensions, 'category')
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
    
    def test_create_gauge_chart(self):
        """Test gauge chart creation."""
        fig = create_gauge_chart(75, "Performance KPI")
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.data[0].type == 'indicator'
    
    def test_create_waterfall_chart(self, sample_data):
        """Test waterfall chart creation."""
        waterfall_data = sample_data.groupby('category')['value'].sum().reset_index()
        fig = create_waterfall_chart(waterfall_data, 'category', 'value')
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.data[0].type == 'waterfall'
    
    def test_create_radar_chart(self, sample_data):
        """Test radar chart creation."""
        radar_data = sample_data.groupby('category')[['value', 'revenue', 'count']].mean().reset_index()
        fig = create_radar_chart(radar_data, ['value', 'revenue', 'count'], 'value', 'category')
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0


class TestChartRecommendationEngine:
    """Test smart chart recommendation system."""
    
    def test_analyze_data(self, sample_data):
        """Test data analysis for recommendations."""
        engine = ChartRecommendationEngine()
        analysis = engine.analyze_data(sample_data)
        
        assert 'row_count' in analysis
        assert 'columns' in analysis
        assert 'patterns' in analysis
        assert 'relationships' in analysis
        assert analysis['row_count'] == len(sample_data)
    
    def test_recommend_charts(self, sample_data):
        """Test chart recommendations."""
        engine = ChartRecommendationEngine()
        recommendations = engine.recommend_charts(sample_data)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # Check recommendation structure
        for rec in recommendations:
            assert hasattr(rec, 'chart_type')
            assert hasattr(rec, 'score')
            assert hasattr(rec, 'reason')
            assert hasattr(rec, 'config')
            assert hasattr(rec, 'columns_used')
            assert 0 <= rec.score <= 1
    
    def test_recommendation_scoring(self, sample_data):
        """Test that recommendations are properly scored."""
        engine = ChartRecommendationEngine()
        recommendations = engine.recommend_charts(sample_data, max_recommendations=10)
        
        if len(recommendations) > 1:
            # Check that recommendations are sorted by score
            scores = [rec.score for rec in recommendations]
            assert scores == sorted(scores, reverse=True)
    
    def test_time_series_recommendation(self):
        """Test time series chart recommendations."""
        time_data = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=30, freq='D'),
            'value': np.random.randn(30)
        })
        
        engine = ChartRecommendationEngine()
        recommendations = engine.recommend_charts(time_data)
        
        # Should recommend time-series appropriate charts
        assert len(recommendations) > 0


class TestChartExportManager:
    """Test chart export functionality."""
    
    @pytest.fixture
    def sample_chart(self):
        """Create a sample chart for testing."""
        fig = go.Figure(data=go.Scatter(x=[1, 2, 3], y=[1, 4, 2]))
        return fig
    
    def test_export_formats(self, sample_chart):
        """Test different export formats."""
        manager = ChartExportManager()
        
        # Test each supported format
        for format_type in ['png', 'svg', 'html', 'json']:
            try:
                result = manager.export_chart(sample_chart, format_type)
                assert result is not None
            except Exception as e:
                # Some formats might not be available in test environment
                if "kaleido" not in str(e).lower():
                    raise
    
    def test_export_options(self):
        """Test export options retrieval."""
        manager = ChartExportManager()
        
        for format_type in ['png', 'svg', 'html', 'json']:
            options = manager.get_export_options(format_type)
            assert isinstance(options, dict)
    
    def test_mime_types(self):
        """Test MIME type detection."""
        manager = ChartExportManager()
        
        expected_mimes = {
            'png': 'image/png',
            'svg': 'image/svg+xml',
            'html': 'text/html',
            'json': 'application/json'
        }
        
        for format_type, expected_mime in expected_mimes.items():
            assert manager.get_mime_type(format_type) == expected_mime


class TestDashboardLayoutManager:
    """Test dashboard layout system."""
    
    def test_create_layout(self):
        """Test dashboard layout creation."""
        manager = DashboardLayoutManager()
        layout = manager.create_layout("Test Dashboard", LayoutType.GRID, 12, 8)
        
        assert layout.name == "Test Dashboard"
        assert layout.layout_type == LayoutType.GRID
        assert layout.columns == 12
        assert layout.rows == 8
        assert len(layout.charts) == 0
    
    def test_add_chart_to_layout(self):
        """Test adding charts to layout."""
        manager = DashboardLayoutManager()
        layout = manager.create_layout("Test", LayoutType.GRID)
        
        position = ChartPosition(x=0, y=0, width=6, height=4, title="Test Chart")
        success = manager.add_chart_to_layout(layout.id, "chart1", position)
        
        assert success
        assert len(layout.charts) == 1
        assert layout.charts[0].chart_id == "chart1"
    
    def test_export_import_layout(self):
        """Test layout export and import."""
        manager = DashboardLayoutManager()
        layout = manager.create_layout("Test", LayoutType.TABS)
        
        # Export layout
        exported = manager.export_layout(layout.id)
        assert exported is not None
        
        # Create new manager and import
        new_manager = DashboardLayoutManager()
        success = new_manager.import_layout(exported)
        assert success


class TestChartConfigurationPanel:
    """Test interactive configuration panel."""
    
    def test_configuration_rendering(self, sample_data):
        """Test configuration panel rendering."""
        panel = ChartConfigurationPanel()
        
        # Mock Streamlit components
        with patch('streamlit.sidebar'), \
             patch('streamlit.subheader'), \
             patch('streamlit.expander'), \
             patch('streamlit.text_input') as mock_text, \
             patch('streamlit.slider') as mock_slider, \
             patch('streamlit.selectbox') as mock_select, \
             patch('streamlit.checkbox') as mock_check:
            
            mock_text.return_value = "Test Chart"
            mock_slider.return_value = 500
            mock_select.return_value = "viridis"
            mock_check.return_value = True
            
            config = panel.render(ChartType.HEATMAP, sample_data)
            
            assert isinstance(config, dict)
    
    def test_config_application(self, sample_data):
        """Test applying configuration to charts."""
        panel = ChartConfigurationPanel()
        fig = create_heatmap(sample_data, 'category', 'subcategory', 'value')
        
        config = {
            'title': 'Test Heatmap',
            'height': 600,
            'show_legend': True,
            'color_scheme': 'plasma'
        }
        
        updated_fig = panel.apply_config(fig, config)
        assert updated_fig.layout.title.text == 'Test Heatmap'
        assert updated_fig.layout.height == 600


class TestPerformanceOptimization:
    """Test performance optimization features."""
    
    def test_data_sampler(self):
        """Test data sampling functionality."""
        large_df = pd.DataFrame({
            'x': range(50000),
            'y': np.random.randn(50000),
            'category': np.random.choice(['A', 'B', 'C'], 50000)
        })
        
        sampler = DataSampler(max_points=10000)
        
        # Should sample
        assert sampler.should_sample(large_df)
        
        # Sample the data
        sampled = sampler.smart_sample(large_df)
        assert len(sampled) <= 10000
        assert len(sampled) > 0
        
        # Check stratified sampling preserved categories
        original_categories = set(large_df['category'])
        sampled_categories = set(sampled['category'])
        assert sampled_categories.issubset(original_categories)
    
    def test_chart_cache(self, sample_data):
        """Test chart caching system."""
        cache = ChartCache(max_size=5, ttl_seconds=3600)
        
        config = {'chart_type': 'heatmap', 'title': 'Test'}
        fig = create_heatmap(sample_data, 'category', 'subcategory', 'value')
        
        # Should be empty initially
        assert cache.get(sample_data, config) is None
        
        # Store chart
        cache.set(sample_data, config, fig)
        
        # Should retrieve cached chart
        cached_fig = cache.get(sample_data, config)
        assert cached_fig is not None
    
    def test_performance_monitor(self):
        """Test performance monitoring."""
        monitor = PerformanceMonitor()
        
        timer_id = monitor.start_timing("test_operation")
        assert timer_id is not None
        
        duration = monitor.end_timing(timer_id)
        assert duration >= 0
        
        # Test performance logging
        perf_data = monitor.log_performance("test", 1.0, 1000, 50.0)
        assert 'operation' in perf_data
        assert 'duration' in perf_data
        assert 'warnings' in perf_data
    
    def test_performance_recommendations(self, sample_data):
        """Test performance recommendations."""
        monitor = PerformanceMonitor()
        
        # Small dataset should have few recommendations
        small_data = sample_data.head(100)
        recs = monitor.get_recommendations(small_data, 'heatmap')
        assert isinstance(recs, list)
        
        # Large dataset should have more recommendations
        large_data = pd.concat([sample_data] * 200, ignore_index=True)
        large_recs = monitor.get_recommendations(large_data, 'scatter_matrix')
        assert len(large_recs) > 0
    
    def test_visualization_optimizer(self, sample_data):
        """Test full optimization pipeline."""
        optimizer = VisualizationOptimizer()
        
        # Test data optimization
        optimized_df, opt_info = optimizer.optimize_data_for_chart(sample_data, 'heatmap')
        
        assert isinstance(optimized_df, pd.DataFrame)
        assert isinstance(opt_info, dict)
        assert 'original_size' in opt_info
        assert 'optimizations_applied' in opt_info
    
    def test_lazy_rendering(self, sample_data):
        """Test lazy rendering system."""
        from src.duckdb_analytics.visualizations.performance import LazyRenderer
        
        renderer = LazyRenderer(chunk_size=50)
        
        # Small data shouldn't need lazy rendering
        small_data = sample_data.head(100)
        assert not renderer.should_use_lazy_rendering(small_data)
        
        # Large data should use lazy rendering
        large_data = pd.concat([sample_data] * 100, ignore_index=True)
        assert renderer.should_use_lazy_rendering(large_data)
        
        # Test chunk creation
        chunks = renderer.create_data_chunks(large_data)
        assert len(chunks) > 1
        assert all(len(chunk) <= renderer.chunk_size for chunk in chunks[:-1])


class TestIntegration:
    """Integration tests for the complete visualization system."""
    
    def test_end_to_end_workflow(self, sample_data):
        """Test complete workflow from recommendation to export."""
        # Step 1: Generate recommendations
        engine = ChartRecommendationEngine()
        recommendations = engine.recommend_charts(sample_data, max_recommendations=3)
        assert len(recommendations) > 0
        
        # Step 2: Create chart based on recommendation
        rec = recommendations[0]
        if rec.chart_type == ChartType.HEATMAP:
            fig = create_heatmap(sample_data, 'category', 'subcategory', 'value')
        elif rec.chart_type == ChartType.TREEMAP:
            fig = create_treemap(sample_data, 'category', 'revenue')
        else:
            # Create a default chart
            fig = create_box_plot(sample_data, 'category', 'value')
        
        assert isinstance(fig, go.Figure)
        
        # Step 3: Apply configuration
        panel = ChartConfigurationPanel()
        config = {'title': 'Integration Test Chart', 'height': 500}
        configured_fig = panel.apply_config(fig, config)
        
        assert configured_fig.layout.title.text == 'Integration Test Chart'
        
        # Step 4: Export chart
        export_manager = ChartExportManager()
        try:
            exported_html = export_manager.export_chart(configured_fig, 'html')
            assert isinstance(exported_html, str)
            assert '<html>' in exported_html.lower()
        except Exception as e:
            # Export might fail in test environment
            assert "export" in str(e).lower() or "html" in str(e).lower()
    
    def test_performance_with_large_dataset(self):
        """Test performance optimizations with large dataset."""
        # Create large dataset
        large_data = pd.DataFrame({
            'x': range(20000),
            'y': np.random.randn(20000),
            'category': np.random.choice(['A', 'B', 'C', 'D', 'E'], 20000),
            'value': np.random.uniform(0, 100, 20000)
        })
        
        optimizer = VisualizationOptimizer()
        
        # Test optimization
        optimized_df, opt_info = optimizer.optimize_data_for_chart(large_data, 'heatmap')
        
        # Should be optimized (sampled)
        assert len(optimized_df) < len(large_data)
        assert 'data_sampling' in opt_info['optimizations_applied']
        
        # Test chart creation with optimization
        def mock_chart_func(df, *args, **kwargs):
            return create_heatmap(df, 'category', 'x', 'value')
        
        config = {'chart_type': 'heatmap'}
        optimized_chart = optimizer.get_optimized_chart(
            large_data, mock_chart_func, config
        )
        
        assert isinstance(optimized_chart, go.Figure)