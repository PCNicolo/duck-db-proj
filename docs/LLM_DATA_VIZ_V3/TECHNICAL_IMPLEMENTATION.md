# Technical Implementation Guide

## Development Philosophy
Keep it simple. This is a personal tool, not enterprise software. Use what already works, don't over-engineer.

## Quick Start Implementation Plan

### Week 1: Foundation
Get the basics working so I can actually use it.

```python
# 1. Project Manager (2 days)
class ProjectManager:
    def create_project(name: str) -> Project
    def load_project(name: str) -> Project
    def list_projects() -> List[str]
    def get_current_project() -> Optional[Project]
    def switch_project(name: str) -> None

# 2. File Ingestion (2 days)
class DataIngestion:
    def register_files(files: List[UploadedFile]) -> List[str]
    def profile_data(table_name: str) -> DataProfile
    def get_sample_data(table_name: str, rows=100) -> pd.DataFrame

# 3. Update Streamlit UI (1 day)
- Add project selector dropdown
- Add file upload area
- Show data profile cards
- Keep existing SQL interface
```

### Week 2: Intelligence
Make it smart about the data.

```python
# 1. Relationship Detector (2 days)
class RelationshipDetector:
    def find_join_candidates(tables: List[str]) -> List[JoinSuggestion]
    def test_join_validity(join: JoinSuggestion) -> bool
    def create_unified_view(joins: List[JoinSuggestion]) -> str

# 2. Enhanced Profiling (2 days)
class DataProfiler:
    def analyze_distribution(column: pd.Series) -> Distribution
    def detect_outliers(column: pd.Series) -> List[Outlier]
    def find_patterns(df: pd.DataFrame) -> List[Pattern]
    def generate_insights(profile: DataProfile) -> List[str]

# 3. Query History (1 day)
class QueryHistory:
    def save_query(sql: str, result: pd.DataFrame) -> None
    def get_history(limit=50) -> List[QueryRecord]
    def search_history(term: str) -> List[QueryRecord]
```

### Week 3: Visualization & Export
Make it pretty and shareable.

```python
# 1. Smart Charts (2 days)
class ChartSelector:
    def recommend_chart_type(df: pd.DataFrame) -> ChartType
    def create_plotly_chart(df: pd.DataFrame, chart_type: ChartType) -> go.Figure
    def make_interactive(fig: go.Figure) -> go.Figure

# 2. Export System (3 days)
class ExportManager:
    def export_html(session: Session) -> str
    def export_notebook(session: Session) -> str
    def export_sql(queries: List[str]) -> str
    def package_for_sharing(project: Project) -> bytes  # zip file
```

## Core Implementation Details

### Project Structure
```
projects/
├── my_analysis/
│   ├── project.yaml        # Simple YAML config
│   ├── data/
│   │   ├── sales.csv       # Original files
│   │   └── customers.parquet
│   ├── sessions/
│   │   └── 2024-01-15.json # Query history
│   └── exports/
│       └── report.html     # Generated outputs
```

### Project Config (project.yaml)
```yaml
name: "My Analysis"
created: "2024-01-15"
files:
  - path: "data/sales.csv"
    table_name: "sales"
    row_count: 10000
  - path: "data/customers.parquet"
    table_name: "customers"
    row_count: 5000
relationships:
  - from: "sales.customer_id"
    to: "customers.id"
    type: "many-to-one"
metrics:
  revenue:
    formula: "SUM(amount)"
    description: "Total revenue"
```

### DuckDB Integration
```python
# Keep it simple - one connection per project
class DuckDBManager:
    def __init__(self, project: Project):
        self.conn = duckdb.connect(":memory:")
        self._load_project_data(project)
    
    def _load_project_data(self, project: Project):
        for file in project.files:
            if file.endswith('.csv'):
                self.conn.execute(f"""
                    CREATE VIEW {table_name} AS 
                    SELECT * FROM read_csv_auto('{file}')
                """)
            elif file.endswith('.parquet'):
                self.conn.execute(f"""
                    CREATE VIEW {table_name} AS 
                    SELECT * FROM read_parquet('{file}')
                """)
    
    def execute_query(self, sql: str) -> pd.DataFrame:
        return self.conn.execute(sql).df()
```

### LLM Integration (Enhance Existing)
```python
# Add project context to SQL generation
class ProjectAwareSQLGenerator(EnhancedSQLGenerator):
    def __init__(self, project: Project, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
    
    def generate_sql(self, query: str) -> str:
        # Add project context to prompt
        context = self._build_project_context()
        return super().generate_sql(query, context=context)
    
    def _build_project_context(self) -> str:
        return f"""
        Available tables: {', '.join(self.project.get_tables())}
        Relationships: {self.project.get_relationships()}
        Common metrics: {self.project.get_metrics()}
        """
```

### Session Recording
```python
# Simple JSON-based session storage
class Session:
    def __init__(self, project: Project):
        self.project = project
        self.queries = []
        self.timestamp = datetime.now()
    
    def add_query(self, sql: str, result: pd.DataFrame, viz: dict = None):
        self.queries.append({
            'timestamp': datetime.now().isoformat(),
            'sql': sql,
            'row_count': len(result),
            'columns': list(result.columns),
            'visualization': viz
        })
    
    def save(self):
        path = f"{self.project.path}/sessions/{self.timestamp}.json"
        with open(path, 'w') as f:
            json.dump(self.queries, f, indent=2)
    
    def replay(self) -> List[pd.DataFrame]:
        results = []
        for query in self.queries:
            result = self.project.execute_query(query['sql'])
            results.append(result)
        return results
```

### HTML Export
```python
def export_to_html(session: Session) -> str:
    # Use Plotly's to_html with include_plotlyjs='cdn'
    html_parts = ['<html><head>...</head><body>']
    
    for query in session.queries:
        html_parts.append(f'<h3>{query["timestamp"]}</h3>')
        html_parts.append(f'<pre>{query["sql"]}</pre>')
        
        if query.get('visualization'):
            fig = plotly.graph_objs.Figure(query['visualization'])
            html_parts.append(fig.to_html(include_plotlyjs='cdn'))
    
    html_parts.append('</body></html>')
    return '\n'.join(html_parts)
```

### Streamlit UI Structure
```python
# Main app.py structure
def main():
    st.set_page_config(page_title="Data Investigation Platform", layout="wide")
    
    # Project selector in sidebar
    with st.sidebar:
        project_name = st.selectbox("Project", get_project_list())
        if st.button("New Project"):
            create_new_project()
    
    # Main area with tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Data", "Query", "Visualize", "Export"])
    
    with tab1:
        # File upload and data profiling
        show_data_manager()
    
    with tab2:
        # SQL query interface (existing)
        show_query_interface()
    
    with tab3:
        # Visualization canvas
        show_visualization_panel()
    
    with tab4:
        # Export options
        show_export_options()
```

## Libraries & Dependencies

### Core (Keep it minimal)
```toml
[tool.poetry.dependencies]
python = "^3.10"
streamlit = "^1.28.0"
duckdb = "^0.9.0"
pandas = "^2.0.0"
plotly = "^5.0.0"
pyyaml = "^6.0"

# Existing LLM deps
openai = "^1.0.0"  # For LM Studio
```

### Development
```toml
[tool.poetry.group.dev.dependencies]
pytest = "^7.0.0"
black = "^23.0.0"
ruff = "^0.1.0"
mypy = "^1.0.0"
```

## Testing Strategy

### Unit Tests (Keep it practical)
```python
# tests/unit/test_project_manager.py
def test_create_project():
    pm = ProjectManager()
    project = pm.create_project("test_project")
    assert project.name == "test_project"
    assert os.path.exists(project.path)

# tests/unit/test_data_profiler.py  
def test_profile_numeric_column():
    data = pd.Series([1, 2, 3, 4, 5, None])
    profile = DataProfiler.profile_column(data)
    assert profile.null_count == 1
    assert profile.mean == 3.0
```

### Integration Tests
```python
# tests/integration/test_full_workflow.py
def test_project_workflow():
    # Create project
    project = ProjectManager().create_project("test")
    
    # Load data
    project.add_file("test_data.csv")
    
    # Run query
    result = project.execute_query("SELECT * FROM test_data")
    assert len(result) > 0
    
    # Export
    html = export_to_html(project.current_session)
    assert "test_data" in html
```

## Performance Considerations

### Quick Wins
1. **DuckDB is already fast** - Don't optimize prematurely
2. **Cache query results** - Simple dict cache with TTL
3. **Lazy load data** - Only profile when requested
4. **Limit preview rows** - Show first 100 by default

### Future Optimizations (If Needed)
- Parallel file profiling
- Background query execution
- Incremental result streaming
- Smart sampling for large files

## Deployment (For Personal Use)

### Local Development
```bash
# Clone repo
git clone https://github.com/myusername/data-investigation-platform

# Install dependencies
poetry install

# Run locally
streamlit run app.py
```

### Packaging (For Sharing)
```bash
# Create standalone executable (future)
pyinstaller --onefile app.py

# Or Docker image
docker build -t data-investigation .
docker run -p 8501:8501 data-investigation
```

## Common Pitfalls to Avoid

1. **Don't over-engineer** - This isn't enterprise software
2. **Keep dependencies minimal** - Every dep is maintenance burden
3. **Use existing code** - We already have working SQL generation
4. **Test with real data** - Use actual CSV files early
5. **Profile first** - Make sure it's actually slow before optimizing

## Success Criteria

✅ I can drag 5 CSV files and start querying in <30 seconds
✅ Queries return results fast enough to feel interactive
✅ I can export analysis as HTML and share it
✅ Project switching is seamless
✅ I actually want to use this tool daily

## Next Steps After MVP

Only if I actually use it and want more:
- Add metric builder UI
- Create template system
- Build cleaning wizard
- Add more export formats
- Consider Electron app for desktop