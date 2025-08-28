"""Tests for enhanced data explorer components."""

import pytest
import pandas as pd
import streamlit as st
from unittest.mock import Mock, patch

from src.duckdb_analytics.ui.advanced_filters import AdvancedFilterBuilder
from src.duckdb_analytics.ui.column_search import ColumnSearchManager
from src.duckdb_analytics.ui.data_export import DataExporter
from src.duckdb_analytics.ui.smart_pagination import SmartPagination, PaginationPresets
from src.duckdb_analytics.ui.column_statistics import ColumnStatisticsManager


class TestAdvancedFilterBuilder:
    """Test advanced filtering functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.filter_builder = AdvancedFilterBuilder()
        self.test_df = pd.DataFrame({
            'id': [1, 2, 3, 4, 5],
            'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
            'age': [25, 30, 35, 28, 32],
            'salary': [50000, 60000, 70000, 55000, 65000],
            'active': [True, False, True, True, False],
            'hire_date': pd.date_range('2020-01-01', periods=5, freq='D')
        })
    
    def test_get_operators_for_numeric_type(self):
        """Test operator selection for numeric columns."""
        operators = self.filter_builder._get_operators_for_type('int64')
        assert 'greater_than' in operators
        assert 'less_than' in operators
        assert 'between' in operators
        assert 'equals' in operators
    
    def test_get_operators_for_string_type(self):
        """Test operator selection for string columns."""
        operators = self.filter_builder._get_operators_for_type('object')
        assert 'contains' in operators
        assert 'starts_with' in operators
        assert 'regex' in operators
        assert 'equals' in operators
    
    def test_build_condition_equals(self):
        """Test building equals condition."""
        condition = self.filter_builder._build_condition(
            self.test_df, 
            {'column': 'name', 'operator': 'equals', 'value': 'Alice'}
        )
        assert condition is not None
        assert condition.sum() == 1  # Only one match expected
    
    def test_build_condition_between(self):
        """Test building between condition."""
        condition = self.filter_builder._build_condition(
            self.test_df,
            {'column': 'age', 'operator': 'between', 'value': [28, 32]}
        )
        assert condition is not None
        assert condition.sum() == 3  # Three ages in range
    
    def test_apply_filters_single_condition(self):
        """Test applying single filter condition."""
        filter_config = {
            'filters': [
                {'column': 'age', 'operator': 'greater_than', 'value': 30}
            ],
            'logic': 'AND'
        }
        
        filtered_df = self.filter_builder.apply_filters(self.test_df, filter_config)
        assert len(filtered_df) == 2  # Only ages 35 and 32
        assert all(filtered_df['age'] > 30)
    
    def test_apply_filters_multiple_conditions_and(self):
        """Test applying multiple filters with AND logic."""
        filter_config = {
            'filters': [
                {'column': 'age', 'operator': 'greater_than', 'value': 25},
                {'column': 'active', 'operator': 'equals', 'value': True}
            ],
            'logic': 'AND'
        }
        
        filtered_df = self.filter_builder.apply_filters(self.test_df, filter_config)
        assert len(filtered_df) == 2  # Alice and Charlie
        assert all(filtered_df['age'] > 25)
        assert all(filtered_df['active'] == True)
    
    def test_to_sql_where_clause(self):
        """Test SQL WHERE clause generation."""
        filter_config = {
            'filters': [
                {'column': 'age', 'operator': 'greater_than', 'value': 25}
            ],
            'logic': 'AND'
        }
        
        sql_clause = self.filter_builder.to_sql_where_clause(filter_config)
        assert 'WHERE' in sql_clause
        assert 'age' in sql_clause
        assert '>' in sql_clause


class TestColumnSearchManager:
    """Test column-level search functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.search_manager = ColumnSearchManager()
        self.test_df = pd.DataFrame({
            'product_id': [1, 2, 3, 4, 5],
            'product_name': ['Widget A', 'Widget B', 'Gadget X', 'Tool Y', 'Device Z'],
            'price': [19.99, 29.99, 39.99, 15.50, 45.00],
            'in_stock': [True, False, True, True, False],
            'created_date': pd.date_range('2023-01-01', periods=5, freq='D')
        })
    
    def test_apply_text_search_contains(self):
        """Test text search with contains operation."""
        mask = self.search_manager._apply_text_search(
            self.test_df['product_name'], 'Widget', 'Contains', False, 0.0
        )
        assert mask.sum() == 2  # Widget A and Widget B
    
    def test_apply_text_search_starts_with(self):
        """Test text search with starts with operation."""
        mask = self.search_manager._apply_text_search(
            self.test_df['product_name'], 'Widget', 'Starts with', False, 0.0
        )
        assert mask.sum() == 2  # Widget A and Widget B
    
    def test_apply_numeric_search_range(self):
        """Test numeric search with range."""
        mask = self.search_manager._apply_numeric_search(
            self.test_df['price'], [20.0, 40.0], 'Range'
        )
        assert mask.sum() == 2  # 29.99 and 39.99
    
    def test_apply_boolean_search(self):
        """Test boolean search."""
        search_value = {'show_true': True, 'show_false': False, 'show_null': False}
        mask = self.search_manager._apply_boolean_search(
            self.test_df['in_stock'], search_value
        )
        assert mask.sum() == 3  # Three True values


class TestDataExporter:
    """Test data export functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.exporter = DataExporter()
        self.test_df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie'],
            'value': [10.5, 20.7, 30.2]
        })
    
    def test_apply_data_filters_sample(self):
        """Test data filtering with sampling."""
        config = {
            'export_scope': 'Sample',
            'sample_size': 2,
            'sample_method': 'First N',
            'column_mode': 'All Columns',
            'selected_columns': list(self.test_df.columns)
        }
        
        filtered_df = self.exporter._apply_data_filters(self.test_df, config)
        assert len(filtered_df) == 2
        assert list(filtered_df['id']) == [1, 2]
    
    def test_apply_data_filters_column_selection(self):
        """Test data filtering with column selection."""
        config = {
            'export_scope': 'All Data',
            'column_mode': 'Selected Columns',
            'selected_columns': ['id', 'name']
        }
        
        filtered_df = self.exporter._apply_data_filters(self.test_df, config)
        assert list(filtered_df.columns) == ['id', 'name']
        assert len(filtered_df) == 3
    
    def test_generate_sql_statements(self):
        """Test SQL statement generation."""
        options = {
            'table_name': 'test_table',
            'batch_size': 2,
            'include_create_table': True,
            'quote_identifiers': True
        }
        
        sql_statements = self.exporter._generate_sql_statements(self.test_df, options)
        
        assert 'CREATE TABLE' in sql_statements
        assert 'INSERT INTO' in sql_statements
        assert 'test_table' in sql_statements
        assert '"id"' in sql_statements  # Quoted identifiers


class TestSmartPagination:
    """Test smart pagination functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.pagination = SmartPagination()
        self.test_df = pd.DataFrame({
            'id': range(1, 101),  # 100 rows
            'value': [i * 2 for i in range(1, 101)]
        })
    
    def test_get_page_data(self):
        """Test getting page data."""
        page_data = self.pagination._get_page_data(self.test_df, 0, 25, 'test')
        assert len(page_data) == 25
        assert list(page_data['id']) == list(range(1, 26))
    
    def test_get_page_data_last_page(self):
        """Test getting last page data."""
        page_data = self.pagination._get_page_data(self.test_df, 3, 25, 'test')
        assert len(page_data) == 25  # Last full page
        assert list(page_data['id']) == list(range(76, 101))
    
    def test_get_virtual_scroll_data(self):
        """Test virtual scroll data retrieval."""
        virtual_data = self.pagination._get_virtual_scroll_data(self.test_df, 10, 20, 'test')
        assert len(virtual_data) == 20
        assert list(virtual_data['id']) == list(range(11, 31))


class TestPaginationPresets:
    """Test pagination presets."""
    
    def test_recommend_preset_small(self):
        """Test preset recommendation for small dataset."""
        preset = PaginationPresets.recommend_preset(500)
        assert preset == 'small_dataset'
    
    def test_recommend_preset_medium(self):
        """Test preset recommendation for medium dataset."""
        preset = PaginationPresets.recommend_preset(5000)
        assert preset == 'medium_dataset'
    
    def test_recommend_preset_large(self):
        """Test preset recommendation for large dataset."""
        preset = PaginationPresets.recommend_preset(50000)
        assert preset == 'large_dataset'
    
    def test_recommend_preset_huge(self):
        """Test preset recommendation for huge dataset."""
        preset = PaginationPresets.recommend_preset(150000)
        assert preset == 'huge_dataset'
    
    def test_get_preset_config(self):
        """Test getting preset configuration."""
        config = PaginationPresets.get_preset_config('large_dataset')
        assert config['mode'] == 'virtual_scroll'
        assert config['page_size'] == 200
        assert config['prefetch_enabled'] == True


class TestColumnStatisticsManager:
    """Test column statistics functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.stats_manager = ColumnStatisticsManager()
        self.test_df = pd.DataFrame({
            'numeric_col': [1, 2, 3, 4, 5, None],
            'text_col': ['apple', 'banana', 'cherry', 'date', 'elderberry', None],
            'bool_col': [True, False, True, False, True, None],
            'date_col': pd.date_range('2023-01-01', periods=6, freq='D')
        })
    
    def test_generate_overview_stats(self):
        """Test overview statistics generation."""
        overview = self.stats_manager._generate_overview_stats(self.test_df)
        
        assert overview['total_rows'] == 6
        assert overview['total_columns'] == 4
        assert overview['numeric_columns'] == 1
        assert overview['missing_cells'] == 3  # 3 None values
        assert 0 <= overview['completeness_score'] <= 1
    
    def test_analyze_numeric_column(self):
        """Test numeric column analysis."""
        config = {'show_sparklines': True}
        stats = self.stats_manager._analyze_numeric_column(
            self.test_df['numeric_col'], config
        )
        
        assert 'numeric_stats' in stats
        assert 'mean' in stats['numeric_stats']
        assert 'std' in stats['numeric_stats']
        assert 'min' in stats['numeric_stats']
        assert 'max' in stats['numeric_stats']
        
        # Check calculated values
        assert stats['numeric_stats']['mean'] == 3.0  # (1+2+3+4+5)/5
        assert stats['numeric_stats']['min'] == 1.0
        assert stats['numeric_stats']['max'] == 5.0
    
    def test_analyze_text_column(self):
        """Test text column analysis."""
        config = {'show_sparklines': True}
        stats = self.stats_manager._analyze_text_column(
            self.test_df['text_col'], config
        )
        
        assert 'text_stats' in stats
        assert 'min_length' in stats['text_stats']
        assert 'max_length' in stats['text_stats']
        assert 'mean_length' in stats['text_stats']
        
        # Check calculated values
        assert stats['text_stats']['min_length'] == 4  # 'date'
        assert stats['text_stats']['max_length'] == 10  # 'elderberry'
    
    def test_analyze_boolean_column(self):
        """Test boolean column analysis."""
        config = {}
        stats = self.stats_manager._analyze_boolean_column(
            self.test_df['bool_col'], config
        )
        
        assert 'boolean_stats' in stats
        assert stats['boolean_stats']['true_count'] == 3
        assert stats['boolean_stats']['false_count'] == 2
        assert stats['boolean_stats']['true_percentage'] == 60.0  # 3/5
        assert stats['boolean_stats']['false_percentage'] == 40.0  # 2/5
    
    def test_analyze_column_quality(self):
        """Test column data quality analysis."""
        quality = self.stats_manager._analyze_column_quality(self.test_df['numeric_col'])
        
        assert 'score' in quality
        assert 'completeness' in quality
        assert 'uniqueness' in quality
        assert 0 <= quality['score'] <= 1
        assert quality['completeness'] == 5/6  # 5 non-null out of 6


class TestIntegration:
    """Integration tests for enhanced data explorer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.test_df = pd.DataFrame({
            'id': range(1, 51),
            'category': ['A'] * 25 + ['B'] * 25,
            'value': [i * 1.5 for i in range(1, 51)],
            'active': [True, False] * 25
        })
    
    def test_component_integration(self):
        """Test that components work together."""
        with patch('streamlit.session_state', {'filter_builder_filters': [], 'filter_builder_logic': 'AND', 
                                              'column_searches': {}, 'column_search_history': {},
                                              'pagination_settings': {'page_size': 100, 'current_page': 0, 
                                                                     'pagination_mode': 'standard', 
                                                                     'virtual_scroll_enabled': False, 
                                                                     'prefetch_enabled': True},
                                              'pagination_cache': {}, 'pagination_performance': {
                                                  'page_load_times': [], 'cache_hit_rate': 0.0, 
                                                  'total_requests': 0, 'cached_requests': 0}}):
            # Initialize components
            filter_builder = AdvancedFilterBuilder()
            search_manager = ColumnSearchManager()
            pagination = SmartPagination()
            
            # Apply filter
            filter_config = {
                'filters': [
                    {'column': 'value', 'operator': 'greater_than', 'value': 50.0}
                ],
                'logic': 'AND'
            }
            
            filtered_df = filter_builder.apply_filters(self.test_df, filter_config)
            assert len(filtered_df) < len(self.test_df)
            
            # Apply pagination
            page_data = pagination._get_page_data(filtered_df, 0, 10, 'test')
            assert len(page_data) <= 10
            
            # Verify data consistency
            assert all(page_data['value'] > 50.0)


if __name__ == '__main__':
    pytest.main([__file__])