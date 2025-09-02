# Project Transformation Plan - Streamlined SQL Analytics

## Transformation Goal
Convert multi-tab analytics dashboard into focused 2-component system:
1. SQL Editor with side-by-side Chat Interface (using existing LM Studio)
2. Simple unified visualization with auto-detect + user controls

## Components to Remove
- CLI module (src/duckdb_analytics/cli.py)
- Analytics tab & all templates
- Multiple visualization tabs
- Data explorer tab
- Enhanced editor beta
- Query templates system
- Execution plan viewer
- File catalog management
- Dashboard builder
- Complex filtering UI

## Components to Keep
- Core DuckDB connection (simplified)
- LLM integration (as-is for LM Studio)
- CSV/Parquet file upload
- Sample data generation
- Basic query execution

## New Architecture
- Single-page Streamlit app
- Side-by-side chat and SQL editor
- Query → Table → Visualization flow
- Auto-detect chart type with manual override
- Minimal UI with maximum content space

## UI Layout
Left Panel: Chat interface for NLP→SQL
Right Panel: SQL editor with run button
Bottom: Results area with table/chart toggle
Chart types: Auto, Line, Bar, Scatter, Pie, Heatmap

## Implementation Phases
1. Strip Down - Remove unnecessary components
2. Restructure - Organize remaining code
3. Build New UI - Create streamlined interface
4. Polish - Optimize and test