# Suggested Commands for DuckDB Analytics Dashboard

## Development Commands

### Running the Application
```bash
# Start the Streamlit dashboard
streamlit run app.py

# Generate sample data for testing
python generate_sample_data.py

# Use the CLI tool
python -m duckdb_analytics.cli --help
python -m duckdb_analytics.cli tables
python -m duckdb_analytics.cli query "SELECT * FROM sales_data LIMIT 10"
```

### Testing Commands
```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src/duckdb_analytics

# Run specific test file
pytest tests/test_<module>.py

# Run tests with verbose output
pytest -v
```

### Code Quality Commands
```bash
# Format code with Black
black src/ tests/ app.py

# Check formatting without making changes
black --check src/ tests/ app.py

# Lint with Ruff
ruff check src/ tests/ app.py

# Fix linting issues automatically
ruff check --fix src/ tests/ app.py

# Type checking with MyPy
mypy src/

# Run all quality checks
black src/ tests/ app.py && ruff check src/ tests/ app.py && mypy src/
```

### Git Commands (Darwin/macOS specific)
```bash
# Check status
git status

# Stage changes
git add .

# Commit with message
git commit -m "Description of changes"

# View commit history
git log --oneline

# Create feature branch
git checkout -b feature/branch-name

# Push to remote
git push origin branch-name
```

### System Utilities (Darwin/macOS)
```bash
# List files with details
ls -la

# Find files
find . -name "*.py" -type f

# Search in files (using ripgrep if installed, otherwise grep)
grep -r "pattern" src/
rg "pattern" src/  # if ripgrep is installed

# Check disk usage
du -sh *

# Monitor processes
top
ps aux | grep python

# Check Python environment
which python
python --version
pip list
```

### Virtual Environment
```bash
# The project appears to use a .venv virtual environment
# Activate virtual environment
source .venv/bin/activate

# Deactivate virtual environment  
deactivate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -e ".[dev]"
```

## Quick Development Workflow
1. Activate virtual environment: `source .venv/bin/activate`
2. Make code changes
3. Format code: `black src/ tests/`
4. Lint code: `ruff check --fix src/ tests/`
5. Type check: `mypy src/`
6. Run tests: `pytest`
7. Run application: `streamlit run app.py`