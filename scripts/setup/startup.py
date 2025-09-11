#!/usr/bin/env python3
"""Quick startup script to load existing data and launch the dashboard."""

import duckdb
import streamlit as st
from pathlib import Path
import subprocess
import sys

def setup_database():
    """Set up DuckDB with existing data files."""
    print("Setting up DuckDB database with existing data...")
    
    # Connect to DuckDB
    conn = duckdb.connect('analytics.db')
    
    # Register all CSV and Parquet files in data/samples
    data_dir = Path("data/samples")
    
    if not data_dir.exists():
        print(f"Error: {data_dir} directory not found!")
        return False
    
    tables_loaded = []
    
    # Load CSV files
    for csv_file in data_dir.glob("*.csv"):
        table_name = csv_file.stem
        try:
            conn.execute(f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_csv_auto('{csv_file}')")
            tables_loaded.append(table_name)
            print(f"✓ Loaded {csv_file.name} as table: {table_name}")
        except Exception as e:
            print(f"✗ Failed to load {csv_file.name}: {e}")
    
    # Load Parquet files (prefer these for better performance)
    for parquet_file in data_dir.glob("*.parquet"):
        table_name = parquet_file.stem + "_parquet"
        try:
            conn.execute(f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_parquet('{parquet_file}')")
            print(f"✓ Loaded {parquet_file.name} as table: {table_name}")
        except Exception as e:
            print(f"✗ Failed to load {parquet_file.name}: {e}")
    
    # Show available tables
    print("\n" + "="*50)
    print("Available tables:")
    print("="*50)
    
    tables = conn.execute("SHOW TABLES").fetchall()
    for table in tables:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {table[0]}").fetchone()[0]
            print(f"  • {table[0]:<30} ({count:,} rows)")
        except:
            print(f"  • {table[0]}")
    
    # Run a sample query to verify
    print("\n" + "="*50)
    print("Sample Query: Top 5 Product Categories by Revenue")
    print("="*50)
    
    try:
        result = conn.execute("""
            SELECT 
                category,
                COUNT(*) as transactions,
                SUM(total_amount) as total_revenue,
                AVG(total_amount) as avg_transaction
            FROM sales_data
            GROUP BY category
            ORDER BY total_revenue DESC
            LIMIT 5
        """).fetchdf()
        print(result.to_string())
    except Exception as e:
        print(f"Sample query failed: {e}")
    
    conn.close()
    print("\n✨ Database ready! Starting Streamlit dashboard...")
    return True

def main():
    """Main entry point."""
    print("="*60)
    print("DuckDB Analytics Dashboard - Quick Start")
    print("="*60)
    
    # Check if data exists
    data_dir = Path("data/samples")
    if not data_dir.exists() or not list(data_dir.glob("*.csv")):
        print("\n⚠️  No data files found!")
        print("Run this first: python generate_sample_data.py")
        sys.exit(1)
    
    # Setup database
    if setup_database():
        print("\nLaunching dashboard at http://localhost:8501")
        print("Press Ctrl+C to stop\n")
        
        # Launch Streamlit
        subprocess.run(["streamlit", "run", "app.py"])

if __name__ == "__main__":
    main()