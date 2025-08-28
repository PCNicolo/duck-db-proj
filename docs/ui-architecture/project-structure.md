# Project Structure

```
duck-db-proj/
├── startup.py                 # Main Streamlit application entry point
├── pages/                     # Streamlit multi-page app structure
│   ├── 1_📊_Analytics.py     # Analytics tab/page
│   ├── 2_📈_Visualizations.py # Visualizations tab/page
│   └── 3_🔍_Data_Explorer.py  # Data Explorer tab/page
├── components/                # Reusable UI components
│   ├── __init__.py
│   ├── chat_interface.py     # Chat UI component
│   ├── sql_editor.py         # SQL editor component
│   ├── data_uploader.py      # File upload component
│   └── result_viewer.py      # Query results display
├── services/                  # Business logic and integrations
│   ├── __init__.py
│   ├── llm_service.py        # LM-Studio integration
│   ├── duckdb_service.py     # DuckDB operations
│   ├── schema_extractor.py   # Schema extraction utilities
│   └── query_optimizer.py    # SQL query optimization
├── utils/                     # Utility functions
│   ├── __init__.py
│   ├── session_state.py      # Session state management
│   ├── validators.py         # Input validation
│   ├── formatters.py         # Data formatting utilities
│   └── cache_manager.py      # Caching utilities
├── config/                    # Configuration files
│   ├── __init__.py
│   ├── app_config.py         # Application settings
│   ├── llm_config.py         # LM-Studio configuration
│   └── database_config.py    # DuckDB configuration
├── assets/                    # Static assets
│   ├── styles/
│   │   └── custom.css        # Custom CSS styles
│   ├── images/
│   │   └── logo.png          # Application logo
│   └── prompts/
│       └── sql_generation.txt # LLM prompt templates
├── tests/                     # Test files
│   ├── __init__.py
│   ├── test_integration.py
│   ├── test_llm_integration.py
│   ├── test_schema_extractor.py
│   └── test_sql_generator_enhanced.py
├── data/                      # Sample data and uploads
│   ├── samples/              # Sample CSV/Parquet files
│   └── uploads/              # User uploaded files
├── .streamlit/                # Streamlit configuration
│   ├── config.toml           # Streamlit app configuration
│   └── secrets.toml          # Sensitive configuration (gitignored)
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (gitignored)
├── .gitignore
└── README.md                  # Project documentation
```
