# Scripts Directory

## Directory Structure

- **setup/**: Initial setup and data generation scripts
  - `startup.py`: Quick start script for initializing the application
  - `generate_sample_data.py`: Generate sample CSV/Parquet data for testing

- **maintenance/**: Cleanup and maintenance utilities
  - `cleanup_unused.py`: Remove unused imports and dead code

- **dev/**: Development and temporary scripts
  - `temp_parse_function.py`: Temporary parsing utilities (consider removing if obsolete)

## Usage

### Setup Scripts
```bash
# Initialize the application
python scripts/setup/startup.py

# Generate sample data
python scripts/setup/generate_sample_data.py
```

### Maintenance Scripts
```bash
# Clean up unused code
python scripts/maintenance/cleanup_unused.py
```