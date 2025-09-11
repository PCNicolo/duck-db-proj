# Suggested Commands for Development

## Running the Application
```bash
# Main application
streamlit run app.py

# Alternative with specific port
streamlit run app.py --server.port 8501
```

## Dependency Management
```bash
# Install dependencies
pip install -r requirements.txt

# Install with development dependencies
pip install -e ".[dev]"

# Upgrade dependencies
pip install --upgrade -r requirements.txt
```

## Code Quality Tools
```bash
# Format code with Black
black src/ app.py

# Lint with Ruff
ruff check src/ app.py

# Type checking with mypy
mypy src/ app.py

# Run all quality checks
black . && ruff check . && mypy .
```

## Testing
```bash
# Run tests (when available)
pytest

# Run with coverage
pytest --cov=src/duckdb_analytics

# Run specific test file
pytest tests/test_specific.py
```

## Git Commands
```bash
# Check status
git status

# Stage changes
git add .

# Commit with message
git commit -m "feat: description"

# Push to branch
git push origin branch-name
```

## Database Operations
```bash
# Open DuckDB CLI for analytics.db
duckdb analytics.db

# Generate sample data
python generate_sample_data.py
```

## Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate (macOS/Linux)
source .venv/bin/activate

# Deactivate
deactivate
```

## System Utilities (macOS)
```bash
# List files with details
ls -la

# Find files
find . -name "*.py"

# Search in files
grep -r "pattern" .

# Monitor processes
ps aux | grep python

# Check disk usage
du -sh .
```

## LM Studio Setup
1. Download and install LM Studio
2. Load a SQL-capable model
3. Ensure server runs on http://localhost:1234
4. Test connection before running app