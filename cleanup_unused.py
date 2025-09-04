#!/usr/bin/env python3
"""
Cleanup script to remove unused Python files from src/duckdb_analytics/
Based on import dependency analysis from app.py
"""

import os
import shutil
from pathlib import Path

# Files that are NOT used by app.py and can be safely removed
UNUSED_FILES = [
    "src/duckdb_analytics/data/file_manager.py",
    "src/duckdb_analytics/llm/query_validator.py",
    "src/duckdb_analytics/core/performance_optimizer.py",
    "src/duckdb_analytics/llm/context_manager.py",
    "src/duckdb_analytics/llm/settings.py",
    "src/duckdb_analytics/core/optimized_query_executor.py",
    "src/duckdb_analytics/core/query_metrics.py",
    "src/duckdb_analytics/llm/sql_generator.py",
    "src/duckdb_analytics/ui/sql_editor.py",
    "src/duckdb_analytics/ui/data_export.py",
    "src/duckdb_analytics/ui/chat_interface.py",
    "src/duckdb_analytics/ui/visualizer.py",
    "src/duckdb_analytics/llm/benchmark.py",
]

# Directories that will be empty after cleanup
EMPTY_DIRS_TO_REMOVE = [
    "src/duckdb_analytics/data",  # Both files will be removed
    "src/duckdb_analytics/ui",     # All UI files will be removed
]

def cleanup_unused_files(dry_run=True):
    """Remove unused Python files and empty directories."""
    
    print("🧹 SQL Analytics Studio Cleanup")
    print("=" * 50)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No files will be deleted")
        print("=" * 50)
    
    removed_count = 0
    total_size = 0
    
    # Remove unused files
    print("\n📄 Files to remove:")
    for file_path in UNUSED_FILES:
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            total_size += file_size
            size_kb = file_size / 1024
            
            if dry_run:
                print(f"  ❌ {file_path} ({size_kb:.1f} KB)")
            else:
                os.remove(file_path)
                print(f"  ✅ Removed: {file_path} ({size_kb:.1f} KB)")
            removed_count += 1
        else:
            print(f"  ⚠️  Already gone: {file_path}")
    
    # Remove empty directories and their __init__.py files
    print("\n📁 Directories to remove:")
    for dir_path in EMPTY_DIRS_TO_REMOVE:
        if os.path.exists(dir_path):
            # Check for __init__.py
            init_file = os.path.join(dir_path, "__init__.py")
            if os.path.exists(init_file):
                if dry_run:
                    print(f"  ❌ {init_file}")
                else:
                    os.remove(init_file)
                    print(f"  ✅ Removed: {init_file}")
                removed_count += 1
            
            # Remove directory if empty
            if not dry_run:
                try:
                    os.rmdir(dir_path)
                    print(f"  ✅ Removed directory: {dir_path}")
                except OSError:
                    print(f"  ⚠️  Directory not empty: {dir_path}")
            else:
                print(f"  ❌ {dir_path}/")
    
    # Clean __pycache__ directories
    print("\n🗑️  Cleaning cache directories:")
    cache_count = 0
    for root, dirs, files in os.walk("src/duckdb_analytics"):
        if "__pycache__" in dirs:
            cache_path = os.path.join(root, "__pycache__")
            if dry_run:
                print(f"  ❌ {cache_path}")
            else:
                shutil.rmtree(cache_path)
                print(f"  ✅ Removed: {cache_path}")
            cache_count += 1
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Cleanup Summary:")
    print(f"  • Files removed: {removed_count}")
    print(f"  • Space freed: {total_size / 1024:.1f} KB")
    print(f"  • Cache directories: {cache_count}")
    
    if dry_run:
        print("\n💡 To perform actual cleanup, run:")
        print("   python cleanup_unused.py --execute")
    else:
        print("\n✅ Cleanup complete!")
    
    return removed_count

def show_remaining_structure():
    """Show what will remain after cleanup."""
    print("\n📂 Structure after cleanup:")
    print("src/duckdb_analytics/")
    print("├── __init__.py")
    print("├── core/")
    print("│   ├── __init__.py")
    print("│   ├── connection.py ✅")
    print("│   └── query_engine.py ✅")
    print("├── llm/")
    print("│   ├── __init__.py")
    print("│   ├── config.py ✅")
    print("│   ├── enhanced_sql_generator.py ✅")
    print("│   ├── optimized_context_manager.py ✅")
    print("│   ├── optimized_schema_extractor.py ✅")
    print("│   ├── performance_utils.py ✅")
    print("│   ├── query_explainer.py ✅")
    print("│   ├── schema_cache.py ✅")
    print("│   └── schema_extractor.py ✅")
    print("└── visualizations/")
    print("    ├── __init__.py")
    print("    ├── chart_types.py ✅")
    print("    └── recommendation_engine.py ✅")
    print("\n✅ = Used by app.py")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        print("⚠️  EXECUTING CLEANUP - FILES WILL BE DELETED!")
        response = input("Are you sure? (yes/no): ")
        if response.lower() == "yes":
            cleanup_unused_files(dry_run=False)
            show_remaining_structure()
        else:
            print("Cancelled.")
    else:
        cleanup_unused_files(dry_run=True)
        show_remaining_structure()
        print("\n💡 This was a dry run. To execute:")
        print("   python cleanup_unused.py --execute")