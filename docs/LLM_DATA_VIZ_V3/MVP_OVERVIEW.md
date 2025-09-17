# Data Investigation Platform - MVP Overview

## Project Purpose
A personal open-source data investigation tool that I'm building for my own use - to drop any dataset (CSV, Parquet, DB files) and instantly begin extracting insights through AI-powered SQL generation, smart visualizations, and intelligent data profiling. Shared publicly for anyone who finds it useful.

## Core Value Proposition
**"Drop files → Get instant intelligence"**

Transform scattered data files into actionable insights without writing SQL or learning complex BI tools. The platform learns from your investigation patterns and provides increasingly intelligent assistance.

## Personal Use Case
A personal open-source tool for my own data investigation needs:
- Quickly analyzing random CSV exports and datasets
- Exploring data from various sources without complex setup
- Building a reusable toolkit for data exploration
- Sharing as open-source for others who might find it useful

## Key Differentiators

### 1. Project-Based Workspace
- Each dataset investigation is a contained "project"
- Maintains context, metrics, and query history per project
- Easy switching between different data investigations

### 2. Intelligent Multi-File Handling
- Auto-detects relationships between dropped files
- Suggests joins and creates unified virtual datasets
- No manual SQL JOIN writing required

### 3. LLM-Powered Everything
- Natural language to SQL conversion
- Data cleaning assistance
- Pattern detection and anomaly identification
- Investigation guidance and recommendations

### 4. Smart Data Profiling
- Instant statistical analysis on file drop
- Distribution visualizations
- Data quality alerts
- Interesting patterns highlighted automatically

### 5. Export Excellence
- Interactive HTML dashboards (offline-capable)
- Jupyter notebooks with reproducible code
- Production-ready SQL scripts
- Streamlit/Dash app templates

## MVP Scope

### Phase 1: Foundation (Weeks 1-2)
- Project creation and management system
- Multi-file upload with DuckDB integration
- Basic data profiling on upload
- Enhanced SQL generation with current LLM

### Phase 2: Intelligence Layer (Weeks 3-4)
- Auto-relationship detection between files
- Smart metric suggestions based on data type
- Query history with categorization
- Session recording and replay

### Phase 3: Visualization & Export (Weeks 5-6)
- Smart chart type selection
- Interactive visualizations with Plotly
- HTML export with embedded data
- Jupyter notebook generation

### Phase 4: Polish & Enhancement (Week 7-8)
- Data cleaning assistant
- Investigation templates
- Performance optimizations
- UI/UX refinements

## Personal Goals
- Make my data exploration workflow 10x faster
- Stop writing repetitive SQL queries
- Build a tool I actually want to use daily
- Create something worth sharing with the open-source community
- Learn and experiment with LLM integration in data tools

## Technical Stack
- **Backend**: Python, DuckDB, FastAPI
- **Frontend**: Streamlit (MVP), potentially React (future)
- **LLM**: Local LM Studio integration
- **Visualization**: Plotly, Altair
- **Storage**: Local file system with project structure

## Risk Mitigation
- **Performance**: Use DuckDB's efficient query engine
- **LLM Reliability**: Implement fallbacks and query validation
- **Data Privacy**: Everything runs locally, no cloud dependencies
- **Complexity**: Start with essential features, iterate based on usage