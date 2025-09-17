# Feature Specifications

## Core Philosophy
This is a personal tool I'm building for my own data exploration needs. Every feature should make MY workflow faster and more enjoyable. If others find it useful, that's a bonus.

## 1. Project Management System

### Purpose
Keep my different data investigations organized and separate.

### Features
```yaml
project_creation:
  - Simple name-based projects (e.g., "taxes_2024", "random_analysis")
  - Each project is a folder on my machine
  - Easy to backup, move, or delete
  
project_switching:
  - Quick dropdown to switch between projects
  - Remembers last opened project
  - Shows recent projects first
  
project_config:
  - YAML file I can manually edit if needed
  - Stores data file paths, metrics, preferences
  - Version controlled with Git if desired
```

### Implementation Priority: HIGH
*Why: I need organization from day one or I'll have CSV files everywhere*

## 2. Smart Data Ingestion

### Purpose
Stop wasting time figuring out how to join random CSV files.

### Features
```yaml
file_drop:
  - Drag & drop multiple files at once
  - Support CSV, Parquet, SQLite, DuckDB files
  - Auto-detect delimiter, encoding, headers
  
instant_profiling:
  - Row count, column types, null percentages
  - Distribution graphs for numeric columns
  - Unique value counts for categoricals
  - "Interesting findings" (e.g., "90% of values are zero")
  
relationship_detection:
  - Find columns with matching names across files
  - Detect potential foreign keys (matching value sets)
  - Suggest JOIN operations
  - Create unified virtual view
```

### Implementation Priority: HIGH
*Why: This is the core value - making random data instantly queryable*

## 3. LLM-Powered SQL Generation (Enhancement)

### Purpose
I don't want to remember SQL syntax for every little query.

### Current State
Already have basic NL → SQL working with thinking pad.

### Enhancements
```yaml
context_awareness:
  - Remember what tables are loaded
  - Understand column meanings from names
  - Learn my query patterns over time
  
query_suggestions:
  - "You might also want to know..."
  - "Last time with similar data you asked..."
  - "Common analyses for this data type..."
  
error_recovery:
  - If SQL fails, try to fix it automatically
  - Explain what went wrong in plain English
  - Suggest alternatives
```

### Implementation Priority: MEDIUM
*Why: Basic version works, these are nice-to-haves*

## 4. Data Cleaning Assistant

### Purpose
I hate manually cleaning messy data. Let the LLM help.

### Features
```yaml
issue_detection:
  - Inconsistent date formats
  - Mixed case text (USA vs usa vs United States)
  - Obvious outliers
  - Missing value patterns
  
cleaning_operations:
  - LLM generates cleaning SQL/Python
  - Preview changes before applying
  - Save as "cleaning recipe" for reuse
  - Undo capability
  
examples:
  - "Standardize all dates to YYYY-MM-DD"
  - "Merge similar category names"
  - "Fill missing values with group median"
  - "Remove $ and convert to numeric"
```

### Implementation Priority: MEDIUM
*Why: Super useful but I can work around it initially*

## 5. Smart Visualizations

### Purpose
Get the right chart without thinking about chart types.

### Features
```yaml
auto_chart_selection:
  - Time series → Line chart with trend
  - Categories → Bar or pie (based on count)
  - Geographic → Map if location data detected
  - Correlations → Scatter or heatmap
  
interactivity:
  - Plotly charts with zoom, pan, hover
  - Click to filter/drill down
  - Export as PNG or interactive HTML
  
dashboard_mode:
  - Arrange multiple charts
  - Save dashboard layout
  - Update all charts with new data
```

### Implementation Priority: HIGH
*Why: Visualizations are how I actually understand data*

## 6. Query History & Sessions

### Purpose
Stop losing great queries I wrote yesterday.

### Features
```yaml
query_history:
  - Every query saved with timestamp
  - Searchable by content or date
  - Categorizable (e.g., "revenue analysis")
  - Copy previous query with one click
  
sessions:
  - Record entire investigation flow
  - Include queries, results, visualizations
  - Replay session on updated data
  - Save as template for similar analyses
  
query_library:
  - Save favorite queries with names
  - Parameter substitution (e.g., @start_date)
  - Share queries between projects
```

### Implementation Priority: HIGH
*Why: I constantly forget useful queries I've written*

## 7. Metric Builder

### Purpose
Define calculations once, use everywhere.

### Features
```yaml
visual_builder:
  - Drag columns to create formulas
  - See live preview of calculation
  - Name and describe the metric
  
metric_storage:
  - Save metrics at project level
  - Detect when metrics apply to new data
  - Version control for metric definitions
  
usage:
  - Reference in queries: "show me CLV by segment"
  - Auto-calculate when applicable
  - Export metric definitions
```

### Implementation Priority: LOW
*Why: Nice to have but not essential for MVP*

## 8. Export Suite

### Purpose
Get my analysis out of the tool and into presentations/reports.

### Features
```yaml
html_export:
  - Self-contained file with embedded data
  - All charts interactive (works offline)
  - Shareable via email
  
jupyter_notebook:
  - All queries as code cells
  - Markdown explanations
  - Reproducible analysis
  
sql_scripts:
  - Clean, commented SQL
  - CREATE VIEW statements for metrics
  - Ready for production databases
  
csv_export:
  - Query results as CSV
  - Include metadata (query, timestamp)
  - Bulk export all session queries
```

### Implementation Priority: HIGH
*Why: I need to share findings with others who don't have the tool*

## 9. Investigation Templates

### Purpose
Reuse analysis patterns on similar datasets.

### Features
```yaml
template_creation:
  - Save session as template
  - Mark required columns/tables
  - Add instructions/documentation
  
template_library:
  - Personal templates folder
  - Download templates from GitHub
  - Share templates as gists
  
template_application:
  - Check if template fits current data
  - Map columns automatically
  - Run all template queries in sequence
```

### Implementation Priority: LOW
*Why: Advanced feature, not needed initially*

## 10. Performance Features

### Purpose
Don't wait around for queries to run.

### Features
```yaml
query_caching:
  - Cache results for identical queries
  - Invalidate on data change
  - Manual cache clear option
  
background_execution:
  - Long queries run in background
  - Show progress indicator
  - Cancel option
  
smart_sampling:
  - Preview with first 1000 rows
  - Full results on demand
  - Sample for quick exploration
```

### Implementation Priority: MEDIUM
*Why: DuckDB is already fast, but caching would be nice*

## MVP Feature Set (First Release)

### Must Have (Week 1-2)
1. ✅ Project creation and switching
2. ✅ Multi-file drag & drop with profiling
3. ✅ Enhanced SQL generation (already exists)
4. ✅ Smart visualizations
5. ✅ Query history
6. ✅ HTML export

### Should Have (Week 3-4)
7. ⭕ Session recording
8. ⭕ Data cleaning assistant
9. ⭕ Relationship detection
10. ⭕ Jupyter export

### Nice to Have (Future)
11. ○ Metric builder
12. ○ Investigation templates
13. ○ Advanced caching
14. ○ Dashboard layouts

## Non-Goals (What This Tool Is NOT)

- ❌ Multi-user collaboration tool
- ❌ Cloud-based service
- ❌ Enterprise BI platform
- ❌ Real-time data streaming
- ❌ Data warehouse replacement
- ❌ Commercial product

This is a personal tool for ad-hoc data analysis. Keep it simple, fast, and enjoyable to use.