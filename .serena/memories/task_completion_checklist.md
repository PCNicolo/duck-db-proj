# Task Completion Checklist

When completing any development task, follow this checklist:

## 1. Code Quality Checks
- [ ] Run Black formatter: `black src/ app.py`
- [ ] Run Ruff linter: `ruff check src/ app.py`
- [ ] Run type checking: `mypy src/ app.py`
- [ ] Fix any issues identified by the tools

## 2. Testing (when tests are available)
- [ ] Run test suite: `pytest`
- [ ] Ensure all tests pass
- [ ] Add tests for new functionality (if applicable)
- [ ] Check test coverage: `pytest --cov=src/duckdb_analytics`

## 3. Documentation
- [ ] Update docstrings for new/modified functions
- [ ] Update README if functionality changed
- [ ] Add inline comments for complex logic
- [ ] Update type hints

## 4. Manual Verification
- [ ] Test the application: `streamlit run app.py`
- [ ] Verify new features work as expected
- [ ] Test with sample data
- [ ] Check for regressions in existing features

## 5. Git Workflow
- [ ] Stage changes: `git add .`
- [ ] Review changes: `git diff --cached`
- [ ] Commit with descriptive message: `git commit -m "type: description"`
- [ ] Push to feature branch (not main)

## 6. Performance Checks
- [ ] Monitor query execution times
- [ ] Check memory usage for large datasets
- [ ] Verify UI responsiveness
- [ ] Test with various data sizes

## 7. LM Studio Integration
- [ ] Verify LM Studio is running on port 1234
- [ ] Test natural language to SQL conversion
- [ ] Check error handling for LLM failures

## Quick Command Sequence
```bash
# Format and check code quality
black . && ruff check . && mypy .

# Run tests (when available)
pytest

# Run application to verify
streamlit run app.py

# Commit changes
git add . && git commit -m "feat: your change description"
```