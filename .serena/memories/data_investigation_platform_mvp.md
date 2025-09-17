# Data Investigation Platform MVP - 2025-09-16

## Project Vision
Personal open-source data analysis tool for quick investigation of CSV/Parquet files using LLM-powered SQL generation and smart visualizations.

## Key Design Decisions

### Core Philosophy
- Personal tool, not commercial product
- Open-source for community benefit
- Simplicity over enterprise features
- Fast iteration over perfection

### Main Features
1. **Project-based workspace** - Organize different data investigations
2. **Smart file ingestion** - Drop files, get instant profiling
3. **LLM everywhere** - SQL generation, data cleaning, pattern detection
4. **Auto-relationship detection** - Find connections between files
5. **Export suite** - HTML, Jupyter, SQL scripts

### Technical Choices
- Streamlit for UI (already using, simple)
- DuckDB for data engine (fast, local)
- Local LLM via LM Studio (privacy, no API costs)
- Project folders for organization
- YAML for configuration

### MVP Scope (6 weeks)
- Week 1-2: Project system + file ingestion
- Week 3-4: Intelligence layer + query history
- Week 5-6: Visualizations + export

### Documentation Created
- `/docs/LLM_DATA_VIZ_V3/` contains all MVP documentation
- Emphasizes personal use, not commercial
- Practical implementation focus
- Clear feature priorities

### Key Implementation Files to Create
1. `src/project_manager/` - Project lifecycle
2. `src/data_intelligence/` - Profiling and relationships
3. `src/visualization/` - Smart charts
4. `src/export/` - Multiple export formats

### Success Metrics
- Can analyze multiple CSVs in <30 seconds
- Queries feel interactive
- Exports work standalone
- Actually want to use it daily