# Project Structure

## Root Directory
```
duck-db-proj/
├── app.py                    # Main Streamlit application entry point
├── requirements.txt          # Python dependencies
├── pyproject.toml           # Project configuration and tool settings
├── README_STREAMLINED.md    # Streamlined version documentation
├── README.md                # Original project documentation
├── generate_sample_data.py  # Script to generate test data
├── startup.py               # Startup script
├── analytics.db             # DuckDB database file
├── .env.example             # Environment variables template
├── .gitignore              # Git ignore configuration
└── .venv/                  # Virtual environment (ignored)
```

## Source Code Structure
```
src/
└── duckdb_analytics/
    ├── __init__.py
    ├── core/                    # Database and query management
    │   ├── connection.py       # DuckDB connection management
    │   ├── query_engine.py     # Query execution engine
    │   ├── optimized_query_executor.py
    │   ├── query_metrics.py
    │   └── performance_optimizer.py
    ├── llm/                     # Language model integration
    │   ├── enhanced_sql_generator.py  # Main SQL generation
    │   ├── query_explainer.py        # Query explanation
    │   ├── optimized_schema_extractor.py
    │   ├── context_manager.py
    │   ├── config.py
    │   └── settings.py
    ├── ui/                      # Streamlit UI components
    │   ├── chat_interface.py   # Chat helper UI
    │   ├── sql_editor.py       # SQL editor component
    │   ├── visualizer.py       # Visualization UI
    │   └── data_export.py      # Export functionality
    └── visualizations/          # Chart generation
        ├── chart_types.py       # Chart type definitions
        └── recommendation_engine.py  # Smart chart selection
```

## Data Directory
```
data/
└── samples/                    # Sample data files
    ├── customers.parquet
    ├── products.parquet
    ├── sales_data.parquet
    ├── inventory.parquet
    └── web_logs.parquet
```

## Documentation
```
docs/                           # Additional documentation
claudedocs/                     # Claude-specific documentation
```

## Configuration Files
- `.serena/`: Serena MCP configuration and memories
- `.gitignore`: Git ignore patterns
- `.env.example`: Environment variable template
- `pyproject.toml`: Python project configuration