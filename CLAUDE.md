# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DuckDB Analytics Dashboard - A local data analytics platform built on DuckDB for zero-copy querying of CSV and Parquet files with an interactive Streamlit interface and CLI tools.

## Key Commands

### Development & Running
```bash
# Start the Streamlit dashboard
streamlit run app.py

# Quick start with existing data
python scripts/setup/startup.py

# Generate sample data for testing
python scripts/setup/generate_sample_data.py

# Code formatting and linting
black src/ tests/ --line-length 88
ruff check src/ tests/ --fix

# Type checking
mypy src/
```

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run specific test categories
pytest tests/unit/ -v          # Unit tests only
pytest tests/integration/ -v   # Integration tests only
pytest tests/e2e/ -v           # End-to-end tests only

# Run with coverage
pytest tests/ --cov=src/duckdb_analytics --cov-report=html

# Run specific test file
pytest tests/unit/test_sql_generation.py -v
```

## Project Organization

### Directory Structure
- `src/`: Source code (core application logic)
- `tests/`: Test suite organized by type (unit/, integration/, e2e/, fixtures/)
- `scripts/`: Utility scripts (setup/, maintenance/, dev/)
- `docs/`: Documentation (architecture/, features/, performance/, development/, archive/)
- `app.py`: Main Streamlit application entry point

### Test Organization
Tests are organized by type in the `tests/` directory:
- `unit/`: Fast, isolated tests for individual components
- `integration/`: Tests for component interactions and LLM integration
- `e2e/`: End-to-end tests simulating user workflows
- `fixtures/`: Shared test data and utilities

## Architecture & Code Structure

### Core Components

1. **DuckDB Connection Layer** (`src/duckdb_analytics/core/`)
   - `connection.py`: Manages DuckDB connections with optimized M1 settings
   - `connection_pool.py`: Connection pooling for concurrent operations
   - `query_engine.py`: Query execution and result handling
   - Uses zero-copy analytics - queries files directly without loading into memory

2. **LLM Integration** (`src/duckdb_analytics/llm/`)
   - `enhanced_sql_generator.py`: Natural language to SQL conversion using local LLM
   - `schema_extractor.py`: Extracts and caches database schema for context
   - `query_explainer.py`: Generates explanations for SQL queries
   - Connects to local LLM at `http://localhost:1234/v1`

3. **UI Components** (`src/duckdb_analytics/ui/`)
   - `sql_editor.py`: Interactive SQL editor with syntax highlighting
   - `visualizer.py`: Chart generation using Plotly
   - `chat_interface.py`: Natural language query interface
   - `data_export.py`: Export functionality for results

4. **Visualization Engine** (`src/duckdb_analytics/visualizations/`)
   - `recommendation_engine.py`: Suggests appropriate chart types based on data
   - `chart_types.py`: Various Plotly chart configurations

### Key Design Patterns

- **Connection Management**: Single shared DuckDB connection with optimized settings for M1 Pro
- **Lazy Loading**: Files are registered as views, not loaded into memory
- **Query Caching**: Results cached in session state to avoid re-execution
- **Schema Caching**: Database schema cached for faster LLM context building
- **Error Recovery**: All database operations wrapped with proper error handling

### Performance Optimizations (M1 Pro Specific)

The codebase is optimized for M1 Pro with these settings:
- Thread count: 4 (optimized for efficiency cores)
- Memory limit: 2GB (conservative for 16GB system)
- Checkpoint threshold: 128MB (faster checkpoints)
- Object caching enabled for better performance

### State Management

Streamlit session state stores:
- `db_connection`: Shared DuckDB connection
- `query_engine`: Query execution interface
- `schema_extractor`: Cached schema information
- `sql_generator`: LLM SQL generator instance
- `registered_tables`: List of loaded data tables
- `query_result`: Latest query results
- `current_sql`: Current SQL query

### Data Flow

1. Data files (CSV/Parquet) → DuckDB views (zero-copy)
2. Natural language query → LLM → SQL generation
3. SQL → DuckDB execution → Results
4. Results → Visualization recommendation → Chart display
5. Optional: Export results as CSV/Parquet

## Working with the LLM Integration

The project uses a local LLM for SQL generation. Key points:
- Expects LLM server at `http://localhost:1234/v1`
- Uses OpenAI-compatible API
- Schema context is automatically included in prompts
- Query explanations generated for non-technical users
- Timeout handling for slow LLM responses (10s default)

## Database Operations

Always use the existing connection patterns:
```python
# Use the shared connection
conn = st.session_state.db_connection

# Execute queries through QueryEngine
result = st.session_state.query_engine.execute(sql_query)

# Register new data files as views (not tables)
conn.execute(f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_csv_auto('{file_path}')")
```

## UI Development

When modifying the Streamlit interface:
- Use `st.session_state` for persistent data
- Implement proper loading states with `st.spinner`
- Handle errors with `st.error` and provide user-friendly messages
- Use columns (`st.columns`) for responsive layouts
- Cache expensive operations with `@st.cache_data`

## LLM Thinking Pad Feature

The application includes a toggleable "Thinking Pad" for SQL generation:
- **Fast Mode (default)**: Quick SQL generation with minimal overhead (~800 tokens)
- **Detailed Mode**: Comprehensive 4-section analysis showing query strategy, business context, schema decisions, and implementation reasoning (~2500 tokens)
- Toggle persists during session via `st.session_state.enable_thinking_pad`
- Optimized for Llama 3.1 8B and similar models

## Current Development Focus

### Recent Optimizations
The codebase recently underwent major improvements:
- **Performance**: 66% latency reduction in SQL generation (10s → 3.4s)
- **Schema Caching**: One-time extraction with >95% cache hit rate
- **Connection Pooling**: Efficient concurrent operation handling
- **Thinking Pad**: Toggle between fast and detailed SQL generation modes
- **Error Recovery**: Comprehensive error handling with graceful degradation

### Code Quality Notes
- **Duplicate Modules**: Some modules have both original and optimized versions (e.g., `schema_extractor.py` and `optimized_schema_extractor.py`). These are intentional for A/B testing and stability. See `docs/development/code-structure-analysis.md` for details.
- **Performance Settings**: M1 Pro optimized with 4 threads, 2GB memory limit, 128MB checkpoint threshold
- **Token Management**: Fast mode uses ~800 tokens, detailed mode uses ~2500 tokens

When making changes, maintain these performance gains by:
- Using cached schema when available
- Avoiding redundant database queries
- Implementing proper connection management
- Preserving both module versions until migration is complete