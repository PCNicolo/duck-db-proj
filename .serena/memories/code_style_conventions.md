# Code Style and Conventions

## Python Style
- **Line Length**: 88 characters (Black default)
- **Target Python Version**: 3.10, 3.11, 3.12
- **Formatting Tool**: Black (automatic formatting)
- **Linting**: Ruff with rules E, F, W, I, N, B
- **Type Hints**: Required (mypy strict mode)

## Code Organization
- **Project Structure**: src-layout with packages under `src/duckdb_analytics/`
- **Module Organization**:
  - `core/`: Database connections and query engine
  - `llm/`: Language model integration and SQL generation
  - `ui/`: Streamlit UI components
  - `visualizations/`: Chart generation and recommendations

## Naming Conventions
- **Functions/Variables**: snake_case (e.g., `load_sample_data`, `execute_query`)
- **Classes**: PascalCase (e.g., `DuckDBConnection`, `EnhancedSQLGenerator`)
- **Constants**: UPPER_SNAKE_CASE
- **Private Methods**: Leading underscore (e.g., `_config`)

## Import Style
- Standard library imports first
- Third-party imports second
- Local imports last
- Each group separated by blank line
- Absolute imports preferred for local modules

## Documentation
- Module-level docstrings for all files
- Function/method docstrings following Google style
- Type hints for all function parameters and returns
- Inline comments for complex logic

## Best Practices
- Early returns to reduce nesting
- Context managers for resource management
- Logging instead of print statements
- Session state management for Streamlit components