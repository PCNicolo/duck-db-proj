# Detailed Migration Checklist - SQL Analytics Transformation

## Phase 1: Backup & Preparation (Day 1)
### Safety First
- [ ] Create git branch: `git checkout -b streamlined-sql-analytics`
- [ ] Full backup: `cp -r src/ src_backup/`
- [ ] Document current dependencies: `pip freeze > requirements_old.txt`
- [ ] Test current app works: `streamlit run app.py`
- [ ] Backup database file: `cp analytics.db analytics_backup.db`

### Documentation
- [ ] Screenshot current UI for reference
- [ ] Document current file structure
- [ ] Note any custom configurations

## Phase 2: Remove Components (Day 1-2)
### CLI Removal
- [ ] Delete `src/duckdb_analytics/cli.py`
- [ ] Remove CLI entry point from `pyproject.toml`
- [ ] Remove Click from requirements.txt
- [ ] Update `__init__.py` to remove CLI imports

### Analytics Module Cleanup
- [ ] Delete entire `src/duckdb_analytics/analytics/` directory
  - [ ] templates.py
  - [ ] filter_builder.py
  - [ ] profiler.py
  - [ ] performance.py
- [ ] Remove analytics imports from app.py

### UI Components Removal
- [ ] From `src/duckdb_analytics/ui/`, delete:
  - [ ] enhanced_editor.py (beta features)
  - [ ] smart_pagination.py
  - [ ] column_statistics.py
  - [ ] streaming_components.py
  - [ ] Any other complex UI components
- [ ] Keep only:
  - [ ] sql_editor.py (will simplify)
  - [ ] data_export.py (might keep for CSV export)

### Visualization Simplification
- [ ] From `src/duckdb_analytics/visualizations/`, delete:
  - [ ] dashboard_layout.py
  - [ ] configuration_panel.py
  - [ ] performance.py
  - [ ] export_manager.py (unless needed for simple export)
- [ ] Keep and simplify:
  - [ ] chart_types.py
  - [ ] recommendation_engine.py (simplify to auto-detect only)

### App.py Tab Removal
- [ ] Remove analytics_tab() function and all related helpers
- [ ] Remove data_explorer_tab() function
- [ ] Remove visualizations_tab() complex features
- [ ] Remove tab navigation from main()

## Phase 3: Restructure (Day 2-3)
### Directory Structure
- [ ] Create new simplified structure:
  ```
  src/
  ├── core/
  │   ├── __init__.py
  │   ├── connection.py (keep as-is)
  │   └── query_engine.py (simplify)
  ├── llm/
  │   ├── __init__.py
  │   ├── config.py (keep as-is)
  │   ├── sql_generator.py (keep as-is)
  │   └── query_explainer.py (NEW - add explanation feature)
  ├── ui/
  │   ├── __init__.py
  │   ├── chat_interface.py (NEW)
  │   ├── sql_editor.py (simplify)
  │   └── visualizer.py (NEW - unified viz)
  └── data/
      ├── __init__.py
      ├── loader.py (from current file upload)
      └── sample_generator.py (from generate_sample_data.py)
  ```

### Core Module Updates
- [ ] Simplify query_engine.py - remove metrics, optimization
- [ ] Keep connection.py mostly as-is
- [ ] Remove performance tracking code

### LLM Module Enhancement
- [ ] Create query_explainer.py for SQL explanation feature
- [ ] Add method to explain query results in plain English
- [ ] Integrate with existing SQLGenerator

## Phase 4: Build New UI (Day 3-4)
### Create Chat Interface (ui/chat_interface.py)
- [ ] Create Streamlit chat UI component
- [ ] Connect to LM Studio via SQLGenerator
- [ ] Add "Send to Editor" button
- [ ] Add query explanation display area
- [ ] Style with minimal design

### Simplify SQL Editor (ui/sql_editor.py)
- [ ] Remove enhanced features (autocomplete, snippets)
- [ ] Keep basic syntax highlighting
- [ ] Add simple Run button
- [ ] Add Copy button
- [ ] Remove execution plan viewer

### Create Unified Visualizer (ui/visualizer.py)
- [ ] Implement auto-detect chart type using simplified recommendation_engine
- [ ] Add dropdown for manual chart type override
- [ ] Support: Line, Bar, Scatter, Pie, Heatmap
- [ ] Use Plotly for all charts
- [ ] Add simple export to PNG

### Rewrite app.py
- [ ] Create single-page layout
- [ ] Implement side-by-side chat/editor
- [ ] Add results area with table/chart toggle
- [ ] Keep file upload in header/sidebar
- [ ] Add sample data generator button
- [ ] Remove all tabs
- [ ] Implement query → table → viz flow

## Phase 5: Integration (Day 4-5)
### Data Flow
- [ ] Connect chat to SQL generator
- [ ] Wire editor to query engine
- [ ] Connect results to visualizer
- [ ] Test CSV/Parquet upload
- [ ] Test sample data generation

### Session Management
- [ ] Simplify session state
- [ ] Remove query history (or keep minimal)
- [ ] Fresh state on startup
- [ ] Maintain table registrations

### Error Handling
- [ ] Add try/catch for LM Studio connection
- [ ] Handle query errors gracefully
- [ ] Add fallback for visualization failures

## Phase 6: Testing (Day 5)
### Functional Testing
- [ ] Test natural language to SQL conversion
- [ ] Test manual SQL editing
- [ ] Test query execution
- [ ] Test all chart types
- [ ] Test file uploads
- [ ] Test sample data

### Edge Cases
- [ ] Test with LM Studio offline
- [ ] Test with invalid SQL
- [ ] Test with empty results
- [ ] Test with large datasets
- [ ] Test with various file formats

### Performance
- [ ] Check app startup time
- [ ] Test query performance
- [ ] Verify visualization rendering
- [ ] Check memory usage

## Phase 7: Cleanup (Day 6)
### Dependencies
- [ ] Update requirements.txt
- [ ] Remove unused packages
- [ ] Update pyproject.toml
- [ ] Clean up imports

### Documentation
- [ ] Update README.md
- [ ] Create simple user guide
- [ ] Document LM Studio setup
- [ ] Remove old documentation

### Code Quality
- [ ] Remove all commented code
- [ ] Clean up debugging prints
- [ ] Format with black/ruff
- [ ] Run basic linting

## Phase 8: Finalization (Day 6)
### Testing
- [ ] Full end-to-end test
- [ ] User acceptance testing
- [ ] Performance benchmarking

### Deployment
- [ ] Commit changes
- [ ] Create before/after comparison
- [ ] Document breaking changes
- [ ] Merge to main (if approved)

## Rollback Plan
If issues arise:
1. `git stash` current changes
2. `git checkout main`
3. `cp -r src_backup/* src/`
4. `pip install -r requirements_old.txt`
5. Restore from backup: `cp analytics_backup.db analytics.db`

## Success Metrics
- [ ] App starts without errors
- [ ] Natural language → SQL works
- [ ] Visualizations render correctly
- [ ] File upload works
- [ ] Sample data loads
- [ ] UI is clean and minimal
- [ ] Performance is acceptable
- [ ] No critical features lost