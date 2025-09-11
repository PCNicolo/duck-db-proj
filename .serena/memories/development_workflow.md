# Development Workflow

## Starting a New Session
1. Activate virtual environment: `source .venv/bin/activate`
2. Check git status: `git status`
3. Pull latest changes: `git pull origin main`
4. Install/update dependencies if needed: `pip install -r requirements.txt`

## Feature Development Flow
1. Create feature branch: `git checkout -b feature/description`
2. Make changes in appropriate modules
3. Test locally: `streamlit run app.py`
4. Run quality checks: `black . && ruff check .`
5. Commit changes with descriptive messages
6. Push to remote: `git push origin feature/description`

## Common Development Patterns

### Adding New SQL Generation Features
1. Modify `src/duckdb_analytics/llm/enhanced_sql_generator.py`
2. Update schema extraction if needed in `optimized_schema_extractor.py`
3. Test with various natural language inputs
4. Verify generated SQL correctness

### Adding New Visualizations
1. Update `src/duckdb_analytics/visualizations/chart_types.py`
2. Modify recommendation logic in `recommendation_engine.py`
3. Update UI in `app.py` main visualization section
4. Test with different data types

### Improving Performance
1. Profile with `monitor_performance()` function
2. Check DuckDB query plans
3. Optimize in `core/performance_optimizer.py`
4. Measure improvements with benchmarks

## Debugging Tips
- Use Streamlit's `st.write()` for quick debugging output
- Check browser console for JavaScript errors
- Monitor `analytics.db` size and query performance
- Use logging module instead of print statements
- Check LM Studio logs for LLM issues

## Environment Variables
- Copy `.env.example` to `.env` for local configuration
- Never commit `.env` file (it's in .gitignore)
- Use `python-dotenv` to load environment variables

## Data Management
- Sample data in `data/samples/` directory
- Generate new test data with `generate_sample_data.py`
- DuckDB database stored in `analytics.db`
- Support for CSV and Parquet file uploads