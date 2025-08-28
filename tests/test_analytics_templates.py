"""Tests for Analytics Template System."""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock

from src.duckdb_analytics.analytics.templates import (
    AnalyticsTemplate,
    TemplateMetadata,
    TemplateParameter,
    ParameterType,
    ColumnFilter,
    TemplateLibrary,
    TemplateEngine
)

class TestAnalyticsTemplate:
    """Test AnalyticsTemplate class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.metadata = TemplateMetadata(
            name="Test Template",
            category="test",
            description="A test template",
            tags=["test"],
            parameters=[
                TemplateParameter(
                    name="column1",
                    type=ParameterType.COLUMN,
                    label="Column 1",
                    description="First column",
                    column_filter=ColumnFilter.NUMERIC
                ),
                TemplateParameter(
                    name="granularity",
                    type=ParameterType.SELECT,
                    label="Granularity",
                    description="Time granularity",
                    options=["day", "week", "month"],
                    default="month"
                )
            ]
        )
        
        self.query_template = "SELECT {column1}, COUNT(*) FROM {table} GROUP BY {column1}"
        self.template = AnalyticsTemplate(self.metadata, self.query_template)
        
    def test_generate_query(self):
        """Test query generation."""
        params = {
            "column1": "revenue",
            "granularity": "day"
        }
        
        query = self.template.generate_query(params, "sales")
        expected = "SELECT revenue, COUNT(*) FROM sales GROUP BY revenue"
        
        assert query == expected
        
    def test_generate_query_missing_required_param(self):
        """Test query generation with missing required parameter."""
        params = {"granularity": "day"}  # Missing column1
        
        with pytest.raises(ValueError, match="Required parameter 'column1' is missing"):
            self.template.generate_query(params, "sales")
            
    def test_validate_parameters(self):
        """Test parameter validation."""
        available_columns = [
            {"name": "revenue", "type": "DOUBLE"},
            {"name": "date", "type": "DATE"},
            {"name": "category", "type": "VARCHAR"}
        ]
        
        # Valid parameters
        params = {"column1": "revenue", "granularity": "month"}
        errors = self.template.validate_parameters(params, available_columns)
        assert errors == []
        
        # Invalid column
        params = {"column1": "nonexistent", "granularity": "month"}
        errors = self.template.validate_parameters(params, available_columns)
        assert len(errors) == 1
        assert "does not exist" in errors[0]
        
        # Invalid option
        params = {"column1": "revenue", "granularity": "invalid"}
        errors = self.template.validate_parameters(params, available_columns)
        assert len(errors) == 1
        assert "not in allowed options" in errors[0]
        
    def test_column_filter_validation(self):
        """Test column filter validation."""
        available_columns = [
            {"name": "revenue", "type": "DOUBLE"},
            {"name": "category", "type": "VARCHAR"}
        ]
        
        # Valid numeric column
        params = {"column1": "revenue", "granularity": "month"}
        errors = self.template.validate_parameters(params, available_columns)
        assert errors == []
        
        # Invalid - text column for numeric filter
        params = {"column1": "category", "granularity": "month"}
        errors = self.template.validate_parameters(params, available_columns)
        assert len(errors) == 1
        assert "does not match filter" in errors[0]
        
    def test_to_dict_and_from_dict(self):
        """Test serialization and deserialization."""
        template_dict = self.template.to_dict()
        reconstructed = AnalyticsTemplate.from_dict(template_dict)
        
        assert reconstructed.metadata.name == self.template.metadata.name
        assert reconstructed.metadata.category == self.template.metadata.category
        assert reconstructed.query_template == self.template.query_template
        assert len(reconstructed.metadata.parameters) == len(self.template.metadata.parameters)

class TestTemplateLibrary:
    """Test TemplateLibrary class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.library = TemplateLibrary()
        
    def test_builtin_templates_loaded(self):
        """Test that built-in templates are loaded."""
        templates = self.library.list_templates()
        assert len(templates) > 0
        
        # Check for specific templates
        template_names = [t.metadata.name for t in templates]
        assert "Time Series Analysis" in template_names
        assert "Cohort Analysis" in template_names
        assert "Funnel Analysis" in template_names
        
    def test_get_template(self):
        """Test getting template by name."""
        template = self.library.get_template("Time Series Analysis")
        assert template is not None
        assert template.metadata.name == "Time Series Analysis"
        
        # Test non-existent template
        template = self.library.get_template("Non-existent Template")
        assert template is None
        
    def test_list_templates_by_category(self):
        """Test filtering templates by category."""
        all_templates = self.library.list_templates()
        temporal_templates = self.library.list_templates("temporal")
        
        assert len(temporal_templates) <= len(all_templates)
        for template in temporal_templates:
            assert template.metadata.category == "temporal"
            
    def test_get_categories(self):
        """Test getting unique categories."""
        categories = self.library.get_categories()
        assert len(categories) > 0
        assert isinstance(categories, list)
        
        # Should include known categories
        assert "temporal" in categories
        assert "behavioral" in categories
        
    def test_add_custom_template(self):
        """Test adding custom template."""
        metadata = TemplateMetadata(
            name="Custom Template",
            category="custom",
            description="A custom template",
            tags=["custom"],
            parameters=[]
        )
        
        custom_template = AnalyticsTemplate(metadata, "SELECT * FROM {table}")
        self.library.add_template(custom_template)
        
        retrieved = self.library.get_template("Custom Template")
        assert retrieved is not None
        assert retrieved.metadata.category == "custom"

class TestTemplateEngine:
    """Test TemplateEngine class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_query_engine = Mock()
        self.mock_db_connection = Mock()
        
        # Mock table info
        self.mock_db_connection.get_table_info.return_value = {
            "columns": [
                {"name": "date", "type": "DATE"},
                {"name": "revenue", "type": "DOUBLE"},
                {"name": "category", "type": "VARCHAR"}
            ]
        }
        
        # Mock query execution result
        self.mock_result_df = pd.DataFrame({
            "period": ["2023-01", "2023-02", "2023-03"],
            "avg_value": [100.0, 150.0, 120.0],
            "count": [10, 15, 12]
        })
        self.mock_query_engine.execute_query.return_value = self.mock_result_df
        
        self.engine = TemplateEngine(self.mock_query_engine, self.mock_db_connection)
        
    def test_execute_template_success(self):
        """Test successful template execution."""
        parameters = {
            "date_column": "date",
            "metric_column": "revenue", 
            "granularity": "month"
        }
        
        result = self.engine.execute_template("Time Series Analysis", parameters, "sales")
        
        assert result["success"] is True
        assert result["data"].equals(self.mock_result_df)
        assert result["row_count"] == len(self.mock_result_df)
        assert "query" in result
        assert "template" in result
        
    def test_execute_template_not_found(self):
        """Test execution with non-existent template."""
        with pytest.raises(ValueError, match="Template 'Non-existent' not found"):
            self.engine.execute_template("Non-existent", {}, "sales")
            
    def test_execute_template_validation_error(self):
        """Test execution with validation errors."""
        parameters = {
            "date_column": "nonexistent",
            "metric_column": "revenue",
            "granularity": "month"
        }
        
        with pytest.raises(ValueError, match="Parameter validation failed"):
            self.engine.execute_template("Time Series Analysis", parameters, "sales")
            
    def test_execute_template_query_error(self):
        """Test execution with query execution error."""
        # Mock query execution to raise an error
        self.mock_query_engine.execute_query.side_effect = Exception("Query failed")
        
        parameters = {
            "date_column": "date",
            "metric_column": "revenue",
            "granularity": "month"
        }
        
        result = self.engine.execute_template("Time Series Analysis", parameters, "sales")
        
        assert result["success"] is False
        assert "error" in result
        assert "Query failed" in result["error"]
        
    def test_template_requirements_validation(self):
        """Test template requirements validation."""
        # Mock table with no numeric columns
        self.mock_db_connection.get_table_info.return_value = {
            "columns": [
                {"name": "category", "type": "VARCHAR"},
                {"name": "description", "type": "TEXT"}
            ]
        }
        
        parameters = {
            "date_column": "category",  # This will fail column filter validation anyway
            "metric_column": "description",
            "granularity": "month"
        }
        
        with pytest.raises(ValueError):
            self.engine.execute_template("Time Series Analysis", parameters, "sales")

class TestParameterTypes:
    """Test parameter type handling."""
    
    def test_number_parameter_validation(self):
        """Test number parameter validation."""
        param = TemplateParameter(
            name="bins",
            type=ParameterType.NUMBER,
            label="Bins",
            description="Number of bins",
            min_value=1,
            max_value=100
        )
        
        metadata = TemplateMetadata(
            name="Test",
            category="test", 
            description="Test",
            tags=[],
            parameters=[param]
        )
        
        template = AnalyticsTemplate(metadata, "SELECT * FROM {table}")
        
        # Valid number
        errors = template.validate_parameters({"bins": 50}, [])
        assert errors == []
        
        # Below minimum
        errors = template.validate_parameters({"bins": 0}, [])
        assert len(errors) == 1
        assert "below minimum" in errors[0]
        
        # Above maximum
        errors = template.validate_parameters({"bins": 150}, [])
        assert len(errors) == 1
        assert "above maximum" in errors[0]
        
        # Invalid type
        errors = template.validate_parameters({"bins": "invalid"}, [])
        assert len(errors) == 1
        assert "must be a number" in errors[0]

if __name__ == "__main__":
    pytest.main([__file__])