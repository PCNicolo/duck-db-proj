# SQL Analytics Studio - Project Overview

## Purpose
SQL Analytics Studio is a streamlined data analytics tool that provides:
1. **Natural Language to SQL conversion** - Chat interface powered by LM Studio for converting natural language queries to SQL
2. **Smart Visualization** - Automatic detection of optimal chart types with manual override capabilities
3. **DuckDB Integration** - Fast, embedded analytics database for local data processing

## Tech Stack
- **Language**: Python 3.10+
- **Database**: DuckDB (embedded analytical database)
- **Frontend**: Streamlit (web application framework)
- **Visualization**: Plotly, Altair
- **Data Processing**: Pandas, PyArrow
- **LLM Integration**: LM Studio (local LLM) via OpenAI-compatible API
- **Other**: python-dotenv, sqlparse, markdown-tree-parser

## Key Features
- Side-by-side layout with chat helper and SQL editor
- CSV/Parquet file upload and sample data generation
- Auto-detecting chart types (line, bar, scatter, pie, heatmap)
- Query execution with performance monitoring
- Streamlined single-page interface

## Development Environment
- **System**: Darwin (macOS)
- **Python Version**: 3.10+
- **Virtual Environment**: .venv
- **Package Manager**: pip with pyproject.toml configuration