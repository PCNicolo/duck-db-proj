# Code Style and Conventions

## Python Version
- Python 3.10+ (target versions: 3.10, 3.11, 3.12)

## Code Style
- **Formatter**: Black with line-length=88
- **Linter**: Ruff with line-length=88, target-version="py310"
- **Type Checker**: MyPy with strict settings (disallow_untyped_defs=true)

## Naming Conventions
- **Files**: snake_case (e.g., query_engine.py, sql_editor.py)
- **Classes**: PascalCase (e.g., DuckDBConnection, QueryEngine, SQLGenerator)
- **Functions/Methods**: snake_case (e.g., execute_query, get_table_info)
- **Constants**: UPPER_SNAKE_CASE
- **Private methods**: Prefix with underscore (e.g., _validate_query)

## Type Hints
- All functions should have type hints for parameters and return types
- Use typing module for complex types (List, Dict, Any, Optional, Union)
- MyPy is configured with strict type checking

## Docstrings
- Functions and classes should have docstrings
- Follow Google/NumPy docstring style
- Include parameter descriptions and return types in docstrings

## Module Structure
- Each module has an __init__.py file
- Imports are organized (standard library, third-party, local)
- Use absolute imports from src.duckdb_analytics

## Testing
- Test files prefixed with test_ in tests/ directory
- Use pytest for testing
- Test functions named test_<functionality>()

## Ruff Rules
- E (Error codes)
- F (Pyflakes)
- W (Warning codes)  
- I (isort)
- N (Naming conventions)
- B (Bugbear)