# Project Code Structure

## Directory Layout
```
duck-db-proj/
├── src/duckdb_analytics/         # Core package
│   ├── core/                     # DuckDB connection and query engine
│   │   ├── connection.py         # Database connection management
│   │   ├── query_engine.py       # Query execution
│   │   ├── optimized_query_executor.py  # Optimized query execution
│   │   ├── query_metrics.py      # Query performance metrics
│   │   └── performance_optimizer.py     # Performance optimization
│   ├── analytics/                # Analytics functions
│   │   ├── templates.py          # Query templates
│   │   ├── filter_builder.py     # Filter construction
│   │   ├── profiler.py           # Data profiling
│   │   └── performance.py        # Performance analytics
│   ├── ui/                       # Streamlit UI components
│   │   ├── sql_editor.py         # Enhanced SQL editor
│   │   ├── streaming_components.py      # Streaming display components
│   │   ├── smart_pagination.py   # Pagination
│   │   ├── column_statistics.py  # Column stats display
│   │   ├── data_export.py        # Export functionality
│   │   └── ...                   # Other UI components
│   ├── llm/                      # LLM integration
│   │   ├── sql_generator.py      # SQL generation from natural language
│   │   ├── schema_extractor.py   # Schema extraction
│   │   ├── context_manager.py    # Context management
│   │   └── query_validator.py    # Query validation
│   ├── visualizations/           # Visualization components
│   │   ├── chart_types.py        # Different chart implementations
│   │   ├── recommendation_engine.py     # Chart recommendations
│   │   ├── dashboard_layout.py   # Dashboard layout
│   │   └── export_manager.py     # Visualization export
│   └── cli.py                    # Command-line interface
├── tests/                         # Test files
│   ├── test_*.py                  # Various test modules
├── data/samples/                  # Sample data directory
├── docs/                          # Documentation
├── app.py                         # Main Streamlit application
├── generate_sample_data.py        # Sample data generator
├── requirements.txt               # Python dependencies
├── pyproject.toml                 # Project configuration
└── README.md                      # Project documentation
```

## Key Modules
- **core**: Database connection and query execution
- **analytics**: Pre-built analytics functions and templates
- **ui**: Streamlit UI components for the dashboard
- **llm**: LLM integration for natural language to SQL
- **visualizations**: Chart and visualization components
- **cli**: Command-line interface implementation