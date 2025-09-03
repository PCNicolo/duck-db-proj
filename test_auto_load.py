#!/usr/bin/env python3
"""Test that data auto-loads from the data/samples directory."""

import sys
sys.path.append('src')

import os
from pathlib import Path
from duckdb_analytics.core.connection import DuckDBConnection

def test_auto_loading():
    """Test that all data files are loadable."""
    
    # Initialize connection
    conn = DuckDBConnection()
    conn.connect()
    
    # Get list of expected files
    data_dir = "data/samples"
    if not os.path.exists(data_dir):
        print(f"❌ Data directory not found: {data_dir}")
        return
    
    files = os.listdir(data_dir)
    parquet_files = [f for f in files if f.endswith('.parquet')]
    csv_files = [f for f in files if f.endswith('.csv')]
    
    print(f"📁 Found {len(parquet_files)} Parquet files and {len(csv_files)} CSV files")
    print("-" * 50)
    
    # Test loading each file
    loaded_tables = []
    for file in parquet_files:
        table_name = Path(file).stem
        file_path = os.path.join(data_dir, file)
        try:
            conn.register_parquet(file_path, table_name)
            result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            rows = result[0] if result else 0
            loaded_tables.append((table_name, rows, "parquet"))
            print(f"✅ Loaded {table_name} from Parquet: {rows:,} rows")
        except Exception as e:
            print(f"❌ Failed to load {file}: {e}")
    
    print("-" * 50)
    print(f"Successfully loaded {len(loaded_tables)} tables:")
    print()
    
    # Display summary
    total_rows = 0
    for table, rows, file_type in sorted(loaded_tables):
        print(f"  📊 {table:<20} {rows:>10,} rows ({file_type})")
        total_rows += rows
    
    print("-" * 50)
    print(f"  Total: {len(loaded_tables)} tables, {total_rows:,} rows")
    print()
    
    # Test a sample query
    if loaded_tables:
        test_table = loaded_tables[0][0]
        print(f"Testing query on {test_table}...")
        result = conn.execute(f"SELECT * FROM {test_table} LIMIT 5")
        df = result.df()
        print(f"✅ Query successful - returned {len(df)} rows")
        print(f"   Columns: {', '.join(df.columns.tolist())}")
    
    print("\n✅ Auto-loading test complete!")

if __name__ == "__main__":
    test_auto_loading()