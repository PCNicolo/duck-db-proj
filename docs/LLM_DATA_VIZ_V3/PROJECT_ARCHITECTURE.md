# Project Architecture

## System Overview

```
┌─────────────────────────────────────────────────────┐
│                   User Interface                     │
│                  (Streamlit MVP)                     │
├─────────────────────────────────────────────────────┤
│                 Project Manager                      │
│         (Project Creation & Switching)               │
├─────────────────────────────────────────────────────┤
│     Data Layer          │      Intelligence Layer    │
│  ┌─────────────────┐    │    ┌──────────────────┐  │
│  │  File Ingestion │    │    │   LLM Service    │  │
│  │    (CSV/Parquet)│    │    │  (SQL Generation) │  │
│  ├─────────────────┤    │    ├──────────────────┤  │
│  │  DuckDB Engine  │◄───┼───►│ Query Optimizer  │  │
│  ├─────────────────┤    │    ├──────────────────┤  │
│  │  Data Profiler  │    │    │ Pattern Detector │  │
│  └─────────────────┘    │    └──────────────────┘  │
├─────────────────────────────────────────────────────┤
│                  Visualization Layer                 │
│         (Plotly Charts & Smart Selection)            │
├─────────────────────────────────────────────────────┤
│                    Export Layer                      │
│        (HTML, Jupyter, SQL, Dashboard)               │
└─────────────────────────────────────────────────────┘
```

## Directory Structure

```
duck-db-proj/
├── projects/                    # User projects root
│   ├── {project_name}/
│   │   ├── data/               # Original data files
│   │   ├── cleaned/            # Processed data
│   │   ├── metrics/            # Saved calculations
│   │   ├── sessions/           # Investigation history
│   │   ├── exports/            # Generated outputs
│   │   └── project.yaml        # Project configuration
│   └── .projects_index.json    # Project registry
│
├── src/
│   ├── project_manager/        # Project lifecycle management
│   │   ├── __init__.py
│   │   ├── project.py         # Project class
│   │   ├── initializer.py     # Smart initialization
│   │   └── session_manager.py # Session recording
│   │
│   ├── data_intelligence/      # Data analysis layer
│   │   ├── __init__.py
│   │   ├── profiler.py        # Statistical profiling
│   │   ├── relationship_detector.py
│   │   ├── metric_builder.py
│   │   └── cleaning_assistant.py
│   │
│   ├── llm_services/           # LLM integration (existing)
│   │   ├── enhanced_sql_generator.py
│   │   ├── data_advisor.py    # New: Investigation guide
│   │   └── pattern_analyzer.py # New: Pattern detection
│   │
│   ├── visualization/          # Smart visualization
│   │   ├── __init__.py
│   │   ├── chart_selector.py  # Auto chart type selection
│   │   ├── plotly_builder.py
│   │   └── dashboard_generator.py
│   │
│   └── export/                 # Export functionality
│       ├── __init__.py
│       ├── html_exporter.py
│       ├── notebook_generator.py
│       ├── sql_exporter.py
│       └── dashboard_template.py
│
├── templates/                   # UI templates
│   ├── project_wizard.html
│   └── investigation_canvas.html
│
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/
```

## Core Components

### 1. Project Manager
**Purpose**: Manages project lifecycle and workspace isolation

**Key Classes**:
```python
class Project:
    - project_id: str
    - name: str
    - created_at: datetime
    - data_files: List[DataFile]
    - metrics: Dict[str, Metric]
    - sessions: List[Session]
    - config: ProjectConfig
    
class ProjectInitializer:
    - analyze_data_domain(files: List[File]) -> DomainType
    - suggest_metrics(domain: DomainType) -> List[Metric]
    - detect_relationships(files: List[File]) -> RelationshipMap
    - create_initial_config() -> ProjectConfig
```

### 2. Data Intelligence Layer
**Purpose**: Provides smart data analysis and profiling

**Key Components**:
- **DataProfiler**: Statistical analysis, distributions, quality checks
- **RelationshipDetector**: Finds joinable columns across files
- **MetricBuilder**: Creates and manages calculated metrics
- **CleaningAssistant**: LLM-powered data cleaning suggestions

### 3. LLM Services (Enhanced)
**Purpose**: AI-powered assistance beyond SQL generation

**New Services**:
- **DataAdvisor**: Guides investigations, suggests next steps
- **PatternAnalyzer**: Finds anomalies, correlations, trends
- **NarrativeGenerator**: Creates readable reports from analyses

### 4. Visualization Layer
**Purpose**: Intelligent chart generation and display

**Smart Features**:
- Auto-detect appropriate chart type based on data shape
- Interactive Plotly charts with drill-down capabilities
- Dashboard layout generation for multiple visualizations

### 5. Export Layer
**Purpose**: Multiple export formats for different use cases

**Export Types**:
- **HTML Package**: Self-contained with embedded data and interactivity
- **Jupyter Notebook**: Reproducible analysis with code cells
- **SQL Scripts**: Production-ready, commented SQL
- **Dashboard Template**: Streamlit/Dash app skeleton

## Data Flow

### Project Initialization Flow
```
1. User creates new project
2. User drops data files
3. System profiles each file
4. LLM analyzes data domain
5. System suggests project configuration
6. User approves/modifies configuration
7. Project workspace created
```

### Query Execution Flow
```
1. User enters natural language query
2. LLM generates SQL with context awareness
3. DuckDB executes query
4. Results cached in session
5. Visualization layer auto-selects chart type
6. Display results with interactive charts
```

### Session Recording Flow
```
1. Each query/visualization saved to session
2. Session maintains chronological order
3. Sessions can be replayed on fresh data
4. Sessions can become templates
```

## Key Design Decisions

### 1. Local-First Architecture
- All processing happens locally
- No cloud dependencies
- Data never leaves user's machine

### 2. Project Isolation
- Each project is self-contained
- Projects can be zipped and shared
- No cross-project data pollution

### 3. Lazy Loading
- Files registered as DuckDB views
- Data loaded only when queried
- Efficient memory usage

### 4. Extensible Metric System
- Metrics defined in YAML
- Portable across projects
- LLM can suggest new metrics

### 5. Template System
- Sessions can become templates
- Templates work on similar data structures
- Community templates possible (future)

## Performance Considerations

### Query Optimization
- Query result caching with TTL
- Incremental data updates
- Smart sampling for large datasets

### UI Responsiveness
- Background query execution
- Progressive result loading
- Optimistic UI updates

### Memory Management
- DuckDB handles large files efficiently
- Streaming results for large outputs
- Cleanup of old cached results