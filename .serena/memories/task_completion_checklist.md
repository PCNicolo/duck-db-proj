# Task Completion Checklist

When completing any development task in this project, follow these steps:

## 1. Code Quality Checks
```bash
# Format all modified files with Black
black src/ tests/ app.py

# Run linting checks and auto-fix issues
ruff check --fix src/ tests/ app.py

# Run type checking
mypy src/
```

## 2. Testing
```bash
# Run all tests to ensure nothing is broken
pytest

# Run tests with coverage if working on new features
pytest --cov=src/duckdb_analytics

# Run specific test files related to your changes
pytest tests/test_<relevant_module>.py -v
```

## 3. Manual Testing
- If you modified the Streamlit app: `streamlit run app.py` and test the UI
- If you modified the CLI: Test relevant CLI commands
- If you added new queries: Test with sample data

## 4. Documentation
- Update docstrings if function signatures changed
- Update README.md if adding new features
- Update ARCHITECTURE.md if changing system design

## 5. Git Workflow
```bash
# Check what files were modified
git status

# Review changes
git diff

# Stage and commit changes
git add .
git commit -m "Descriptive commit message"
```

## Important Notes
- Always run tests before committing
- Ensure Black formatting is applied (line-length=88)
- Fix any Ruff linting issues
- Address MyPy type checking errors
- The project uses strict type checking - all functions need type hints

## Quick All-in-One Command
```bash
# Run all checks in sequence
black src/ tests/ app.py && ruff check src/ tests/ app.py && mypy src/ && pytest
```

If all checks pass, your code is ready to commit!