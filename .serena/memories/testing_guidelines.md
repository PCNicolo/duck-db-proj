# Testing Guidelines for DuckDB Analytics Project

## Important: Test Organization

**CRITICAL**: All tests MUST be placed in the `tests/` directory, NOT in `scripts/`

### Directory Structure
Tests are organized by type in the `tests/` directory:
- `tests/unit/` - Fast, isolated tests for individual components
- `tests/integration/` - Tests for component interactions and LLM integration  
- `tests/e2e/` - End-to-end tests simulating user workflows
- `tests/fixtures/` - Shared test data and utilities

### Running Tests
```bash
# Run all tests
pytest tests/ -v

# Run specific test categories
pytest tests/unit/ -v          # Unit tests only
pytest tests/integration/ -v   # Integration tests only
pytest tests/e2e/ -v           # End-to-end tests only

# Run with coverage
pytest tests/ --cov=src/duckdb_analytics --cov-report=html

# Run specific test file
pytest tests/unit/test_sql_generation.py -v
```

### Test File Naming
- Unit tests: `test_<module_name>.py`
- Integration tests: `test_integration_<feature>.py`
- E2E tests: `test_e2e_<workflow>.py`

### Key Testing Rules
1. NEVER create test files in `scripts/` - that's for utility scripts only
2. Always use pytest as the test runner
3. Test files must start with `test_` to be discovered by pytest
4. Use fixtures from `tests/fixtures/` for shared test data
5. Mock external dependencies (LLM, database) for unit tests
6. Integration tests can use real LLM connections when needed
7. E2E tests should simulate complete user workflows

### Scripts vs Tests
- `scripts/` - For utility scripts, setup, maintenance, development tools
- `tests/` - For ALL test code including unit, integration, and e2e tests

This is a strict requirement from CLAUDE.md and must be followed for all test development.