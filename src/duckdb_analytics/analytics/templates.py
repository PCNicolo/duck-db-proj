"""Analytics Template System for DuckDB Analytics Dashboard."""

import json
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Union
from enum import Enum

class ParameterType(Enum):
    """Parameter types for template parameters."""
    COLUMN = "column"
    SELECT = "select" 
    NUMBER = "number"
    TEXT = "text"
    BOOLEAN = "boolean"
    DATE = "date"

class ColumnFilter(Enum):
    """Column filter types."""
    ALL = "all"
    NUMERIC = "numeric"
    TEXT = "text"
    DATE = "date"
    BOOLEAN = "boolean"

@dataclass
class TemplateParameter:
    """Template parameter definition."""
    name: str
    type: ParameterType
    label: str
    description: str
    required: bool = True
    default: Optional[Union[str, int, float, bool]] = None
    options: Optional[List[str]] = None
    column_filter: Optional[ColumnFilter] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None

@dataclass
class TemplateMetadata:
    """Template metadata and configuration."""
    name: str
    category: str
    description: str
    tags: List[str]
    parameters: List[TemplateParameter]
    created_by: str = "system"
    created_at: float = None
    version: str = "1.0"
    requires_numeric_columns: bool = False
    requires_date_columns: bool = False
    min_rows: int = 0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()

class AnalyticsTemplate:
    """Analytics template for generating SQL queries with parameters."""
    
    def __init__(self, metadata: TemplateMetadata, query_template: str):
        self.metadata = metadata
        self.query_template = query_template
        
    def generate_query(self, params: Dict[str, Any], table_name: str) -> str:
        """Generate SQL query from template with parameters."""
        # Prepare parameters for template substitution
        template_params = params.copy()
        template_params['table'] = table_name
        
        # Validate required parameters
        for param in self.metadata.parameters:
            if param.required and param.name not in params:
                raise ValueError(f"Required parameter '{param.name}' is missing")
                
        try:
            # Use format string substitution
            query = self.query_template.format(**template_params)
            return query.strip()
        except KeyError as e:
            raise ValueError(f"Template parameter error: {e}")
            
    def validate_parameters(self, params: Dict[str, Any], available_columns: List[Dict[str, Any]]) -> List[str]:
        """Validate parameters against available columns and constraints."""
        errors = []
        
        for param in self.metadata.parameters:
            value = params.get(param.name)
            
            # Check required parameters
            if param.required and value is None:
                errors.append(f"Parameter '{param.name}' is required")
                continue
                
            if value is None:
                continue
                
            # Validate column parameters
            if param.type == ParameterType.COLUMN:
                column_names = [col['name'] for col in available_columns]
                if value not in column_names:
                    errors.append(f"Column '{value}' does not exist")
                else:
                    # Check column filter
                    if param.column_filter:
                        col_info = next((col for col in available_columns if col['name'] == value), None)
                        if col_info and not self._matches_column_filter(col_info, param.column_filter):
                            errors.append(f"Column '{value}' does not match filter '{param.column_filter.value}'")
                            
            # Validate select parameters
            elif param.type == ParameterType.SELECT:
                if param.options and value not in param.options:
                    errors.append(f"Value '{value}' not in allowed options: {param.options}")
                    
            # Validate numeric parameters
            elif param.type == ParameterType.NUMBER:
                try:
                    num_value = float(value)
                    if param.min_value is not None and num_value < param.min_value:
                        errors.append(f"Value {num_value} is below minimum {param.min_value}")
                    if param.max_value is not None and num_value > param.max_value:
                        errors.append(f"Value {num_value} is above maximum {param.max_value}")
                except (ValueError, TypeError):
                    errors.append(f"Parameter '{param.name}' must be a number")
                    
        return errors
    
    def _matches_column_filter(self, column_info: Dict[str, Any], filter_type: ColumnFilter) -> bool:
        """Check if column matches filter type."""
        col_type = column_info.get('type', '').lower()
        
        if filter_type == ColumnFilter.NUMERIC:
            return any(t in col_type for t in ['int', 'float', 'double', 'decimal', 'numeric'])
        elif filter_type == ColumnFilter.TEXT:
            return any(t in col_type for t in ['varchar', 'text', 'string', 'char'])
        elif filter_type == ColumnFilter.DATE:
            return any(t in col_type for t in ['date', 'time', 'timestamp'])
        elif filter_type == ColumnFilter.BOOLEAN:
            return 'bool' in col_type
            
        return True  # ALL filter
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary."""
        return {
            'metadata': asdict(self.metadata),
            'query_template': self.query_template
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalyticsTemplate':
        """Create template from dictionary."""
        metadata_dict = data['metadata']
        
        # Convert parameters
        parameters = []
        for param_dict in metadata_dict.get('parameters', []):
            param_dict = param_dict.copy()
            if 'type' in param_dict:
                param_dict['type'] = ParameterType(param_dict['type'])
            if 'column_filter' in param_dict and param_dict['column_filter']:
                param_dict['column_filter'] = ColumnFilter(param_dict['column_filter'])
            parameters.append(TemplateParameter(**param_dict))
            
        metadata_dict['parameters'] = parameters
        metadata = TemplateMetadata(**metadata_dict)
        
        return cls(metadata, data['query_template'])

class TemplateLibrary:
    """Library of analytics templates."""
    
    def __init__(self):
        self.templates: Dict[str, AnalyticsTemplate] = {}
        self._load_builtin_templates()
        
    def _load_builtin_templates(self):
        """Load built-in analytics templates."""
        templates = [
            self._create_time_series_template(),
            self._create_cohort_analysis_template(),
            self._create_funnel_analysis_template(),
            self._create_distribution_analysis_template(),
            self._create_correlation_matrix_template(),
            self._create_pivot_table_template(),
        ]
        
        for template in templates:
            self.add_template(template)
    
    def _create_time_series_template(self) -> AnalyticsTemplate:
        """Create time series analysis template."""
        metadata = TemplateMetadata(
            name="Time Series Analysis",
            category="temporal", 
            description="Analyze trends over time with customizable time granularity",
            tags=["time", "trend", "temporal"],
            requires_date_columns=True,
            parameters=[
                TemplateParameter(
                    name="date_column",
                    type=ParameterType.COLUMN,
                    label="Date Column",
                    description="Column containing date/timestamp values",
                    column_filter=ColumnFilter.DATE
                ),
                TemplateParameter(
                    name="metric_column",
                    type=ParameterType.COLUMN,
                    label="Metric Column", 
                    description="Numeric column to analyze over time",
                    column_filter=ColumnFilter.NUMERIC
                ),
                TemplateParameter(
                    name="granularity",
                    type=ParameterType.SELECT,
                    label="Time Granularity",
                    description="Time period for aggregation",
                    options=["day", "week", "month", "quarter", "year"],
                    default="month"
                )
            ]
        )
        
        query = """
        SELECT 
            DATE_TRUNC('{granularity}', {date_column}) as period,
            AVG({metric_column}) as avg_value,
            SUM({metric_column}) as total_value,
            COUNT(*) as count,
            MIN({metric_column}) as min_value,
            MAX({metric_column}) as max_value
        FROM {table}
        WHERE {date_column} IS NOT NULL AND {metric_column} IS NOT NULL
        GROUP BY period
        ORDER BY period
        """
        
        return AnalyticsTemplate(metadata, query)
    
    def _create_cohort_analysis_template(self) -> AnalyticsTemplate:
        """Create cohort analysis template."""
        metadata = TemplateMetadata(
            name="Cohort Analysis",
            category="behavioral",
            description="Analyze user behavior patterns by cohorts over time",
            tags=["cohort", "retention", "behavioral"],
            requires_date_columns=True,
            parameters=[
                TemplateParameter(
                    name="user_id_column",
                    type=ParameterType.COLUMN,
                    label="User ID Column",
                    description="Column containing user identifiers"
                ),
                TemplateParameter(
                    name="event_date_column", 
                    type=ParameterType.COLUMN,
                    label="Event Date Column",
                    description="Column containing event dates",
                    column_filter=ColumnFilter.DATE
                ),
                TemplateParameter(
                    name="cohort_period",
                    type=ParameterType.SELECT,
                    label="Cohort Period",
                    description="Time period for cohort grouping",
                    options=["week", "month", "quarter"],
                    default="month"
                )
            ]
        )
        
        query = """
        WITH cohorts AS (
            SELECT 
                {user_id_column},
                DATE_TRUNC('{cohort_period}', MIN({event_date_column})) as cohort_period,
                DATE_TRUNC('{cohort_period}', {event_date_column}) as period
            FROM {table}
            WHERE {user_id_column} IS NOT NULL AND {event_date_column} IS NOT NULL
            GROUP BY {user_id_column}, DATE_TRUNC('{cohort_period}', {event_date_column})
        )
        SELECT 
            cohort_period,
            period,
            COUNT(DISTINCT {user_id_column}) as active_users,
            EXTRACT(EPOCH FROM (period - cohort_period))/(30*24*3600) as period_number
        FROM cohorts
        GROUP BY cohort_period, period
        ORDER BY cohort_period, period
        """
        
        return AnalyticsTemplate(metadata, query)
        
    def _create_funnel_analysis_template(self) -> AnalyticsTemplate:
        """Create funnel analysis template.""" 
        metadata = TemplateMetadata(
            name="Funnel Analysis",
            category="conversion",
            description="Analyze conversion rates through a multi-step process",
            tags=["funnel", "conversion", "process"],
            parameters=[
                TemplateParameter(
                    name="user_id_column",
                    type=ParameterType.COLUMN,
                    label="User ID Column",
                    description="Column containing user identifiers"
                ),
                TemplateParameter(
                    name="event_column",
                    type=ParameterType.COLUMN,
                    label="Event Column",
                    description="Column containing event names/types"
                ),
                TemplateParameter(
                    name="step1_event",
                    type=ParameterType.TEXT,
                    label="Step 1 Event",
                    description="First step event name"
                ),
                TemplateParameter(
                    name="step2_event",
                    type=ParameterType.TEXT,
                    label="Step 2 Event", 
                    description="Second step event name"
                ),
                TemplateParameter(
                    name="step3_event",
                    type=ParameterType.TEXT,
                    label="Step 3 Event",
                    description="Third step event name",
                    required=False
                )
            ]
        )
        
        query = """
        WITH funnel_events AS (
            SELECT 
                {user_id_column},
                SUM(CASE WHEN {event_column} = '{step1_event}' THEN 1 ELSE 0 END) as step1_count,
                SUM(CASE WHEN {event_column} = '{step2_event}' THEN 1 ELSE 0 END) as step2_count,
                SUM(CASE WHEN {event_column} = '{step3_event}' THEN 1 ELSE 0 END) as step3_count
            FROM {table}
            WHERE {event_column} IN ('{step1_event}', '{step2_event}', '{step3_event}')
            GROUP BY {user_id_column}
        )
        SELECT 
            'Step 1: {step1_event}' as step,
            1 as step_number,
            COUNT(*) as users,
            100.0 as conversion_rate
        FROM funnel_events 
        WHERE step1_count > 0
        UNION ALL
        SELECT 
            'Step 2: {step2_event}' as step,
            2 as step_number,
            COUNT(*) as users,
            ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM funnel_events WHERE step1_count > 0), 2) as conversion_rate
        FROM funnel_events
        WHERE step1_count > 0 AND step2_count > 0
        UNION ALL
        SELECT 
            'Step 3: {step3_event}' as step,
            3 as step_number, 
            COUNT(*) as users,
            ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM funnel_events WHERE step1_count > 0), 2) as conversion_rate
        FROM funnel_events
        WHERE step1_count > 0 AND step2_count > 0 AND step3_count > 0
        ORDER BY step_number
        """
        
        return AnalyticsTemplate(metadata, query)
    
    def _create_distribution_analysis_template(self) -> AnalyticsTemplate:
        """Create distribution analysis template."""
        metadata = TemplateMetadata(
            name="Distribution Analysis",
            category="statistical",
            description="Analyze the statistical distribution of a numeric column",
            tags=["distribution", "statistics", "histogram"],
            requires_numeric_columns=True,
            parameters=[
                TemplateParameter(
                    name="metric_column",
                    type=ParameterType.COLUMN,
                    label="Metric Column",
                    description="Numeric column to analyze",
                    column_filter=ColumnFilter.NUMERIC
                ),
                TemplateParameter(
                    name="bins",
                    type=ParameterType.NUMBER,
                    label="Number of Bins", 
                    description="Number of bins for histogram",
                    default=10,
                    min_value=5,
                    max_value=100
                )
            ]
        )
        
        query = """
        WITH stats AS (
            SELECT 
                MIN({metric_column}) as min_val,
                MAX({metric_column}) as max_val,
                AVG({metric_column}) as mean_val,
                STDDEV({metric_column}) as std_val,
                COUNT(*) as total_count
            FROM {table}
            WHERE {metric_column} IS NOT NULL
        ),
        bins AS (
            SELECT 
                min_val + (max_val - min_val) * (generate_series(0, {bins}) / {bins}::float) as bin_edge
            FROM stats
        ),
        histogram AS (
            SELECT 
                b1.bin_edge as bin_start,
                b2.bin_edge as bin_end,
                COUNT(t.{metric_column}) as count
            FROM bins b1
            JOIN bins b2 ON b2.bin_edge > b1.bin_edge
            LEFT JOIN {table} t ON t.{metric_column} >= b1.bin_edge 
                AND t.{metric_column} < b2.bin_edge
            WHERE b1.bin_edge != (SELECT MAX(bin_edge) FROM bins)
            GROUP BY b1.bin_edge, b2.bin_edge
        )
        SELECT 
            ROUND(bin_start, 2) as bin_start,
            ROUND(bin_end, 2) as bin_end,
            count,
            ROUND(100.0 * count / (SELECT total_count FROM stats), 2) as percentage
        FROM histogram
        ORDER BY bin_start
        """
        
        return AnalyticsTemplate(metadata, query)
    
    def _create_correlation_matrix_template(self) -> AnalyticsTemplate:
        """Create correlation matrix template."""
        metadata = TemplateMetadata(
            name="Correlation Matrix",
            category="statistical", 
            description="Calculate correlation coefficients between numeric columns",
            tags=["correlation", "relationship", "matrix"],
            requires_numeric_columns=True,
            parameters=[
                TemplateParameter(
                    name="columns",
                    type=ParameterType.TEXT,
                    label="Columns (comma-separated)",
                    description="Comma-separated list of numeric columns to correlate"
                )
            ]
        )
        
        # Note: This is a simplified version - full correlation matrix would require dynamic SQL
        query = """
        SELECT 
            'Correlation Analysis' as analysis_type,
            CORR({columns}) as correlation_coefficient,
            COUNT(*) as sample_size
        FROM {table}
        WHERE {columns} IS NOT NULL
        """
        
        return AnalyticsTemplate(metadata, query)
    
    def _create_pivot_table_template(self) -> AnalyticsTemplate:
        """Create pivot table template."""
        metadata = TemplateMetadata(
            name="Pivot Table",
            category="aggregation",
            description="Create pivot table with rows, columns, and aggregated values",
            tags=["pivot", "aggregation", "summary"],
            parameters=[
                TemplateParameter(
                    name="row_column",
                    type=ParameterType.COLUMN,
                    label="Row Column",
                    description="Column to use for rows"
                ),
                TemplateParameter(
                    name="col_column", 
                    type=ParameterType.COLUMN,
                    label="Column Column",
                    description="Column to use for columns"
                ),
                TemplateParameter(
                    name="value_column",
                    type=ParameterType.COLUMN,
                    label="Value Column",
                    description="Column to aggregate",
                    column_filter=ColumnFilter.NUMERIC
                ),
                TemplateParameter(
                    name="aggregation",
                    type=ParameterType.SELECT,
                    label="Aggregation Function",
                    description="Function to aggregate values",
                    options=["SUM", "AVG", "COUNT", "MIN", "MAX"],
                    default="SUM"
                )
            ]
        )
        
        query = """
        SELECT 
            {row_column},
            {col_column},
            {aggregation}({value_column}) as aggregated_value
        FROM {table}
        WHERE {row_column} IS NOT NULL 
            AND {col_column} IS NOT NULL 
            AND {value_column} IS NOT NULL
        GROUP BY {row_column}, {col_column}
        ORDER BY {row_column}, {col_column}
        """
        
        return AnalyticsTemplate(metadata, query)
    
    def add_template(self, template: AnalyticsTemplate):
        """Add template to library."""
        self.templates[template.metadata.name] = template
        
    def get_template(self, name: str) -> Optional[AnalyticsTemplate]:
        """Get template by name."""
        return self.templates.get(name)
        
    def list_templates(self, category: Optional[str] = None) -> List[AnalyticsTemplate]:
        """List all templates, optionally filtered by category."""
        templates = list(self.templates.values())
        if category:
            templates = [t for t in templates if t.metadata.category == category]
        return templates
        
    def get_categories(self) -> List[str]:
        """Get all unique categories."""
        return list(set(t.metadata.category for t in self.templates.values()))

class TemplateEngine:
    """Template execution engine."""
    
    def __init__(self, query_engine, db_connection):
        self.query_engine = query_engine
        self.db_connection = db_connection
        self.library = TemplateLibrary()
        
    def execute_template(self, template_name: str, parameters: Dict[str, Any], 
                        table_name: str) -> Dict[str, Any]:
        """Execute analytics template with parameters."""
        template = self.library.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
            
        # Get table info for validation
        table_info = self.db_connection.get_table_info(table_name)
        columns = table_info.get('columns', [])
        
        # Validate parameters
        errors = template.validate_parameters(parameters, columns)
        if errors:
            raise ValueError(f"Parameter validation failed: {'; '.join(errors)}")
            
        # Check template requirements
        if template.metadata.requires_numeric_columns:
            numeric_cols = [col for col in columns 
                          if any(t in col.get('type', '').lower() 
                               for t in ['int', 'float', 'double', 'decimal', 'numeric'])]
            if not numeric_cols:
                raise ValueError("Template requires numeric columns but none found")
                
        if template.metadata.requires_date_columns:
            date_cols = [col for col in columns
                        if any(t in col.get('type', '').lower()
                             for t in ['date', 'time', 'timestamp'])]
            if not date_cols:
                raise ValueError("Template requires date columns but none found")
                
        # Generate and execute query
        query = template.generate_query(parameters, table_name)
        
        try:
            result_df = self.query_engine.execute_query(query)
            
            return {
                'success': True,
                'data': result_df,
                'query': query,
                'template': template.metadata.name,
                'parameters': parameters,
                'row_count': len(result_df)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'template': template.metadata.name,
                'parameters': parameters
            }