#!/usr/bin/env python3
"""
Test script for the streamlined SQL Analytics Studio.
"""

import sys
sys.path.append('src')

import pandas as pd
import duckdb
from duckdb_analytics.core.connection import DuckDBConnection
from duckdb_analytics.core.query_engine import QueryEngine
from duckdb_analytics.llm.sql_generator import SQLGenerator
from duckdb_analytics.llm.schema_extractor import SchemaExtractor
from duckdb_analytics.visualizations.recommendation_engine import ChartRecommendationEngine


def test_database_connection():
    """Test DuckDB connection and basic operations."""
    print("Testing DuckDB connection...")
    conn = DuckDBConnection()
    conn.connect()
    
    # Create test table
    conn.execute("""
        CREATE OR REPLACE TABLE test_sales AS 
        SELECT 
            DATE '2024-01-01' + INTERVAL (i % 30) DAY as date,
            'Product_' || (i % 5) as product,
            ROUND(RANDOM() * 100, 2) as sales
        FROM generate_series(1, 100) as t(i)
    """)
    
    # Query the data
    result = conn.execute("SELECT COUNT(*) FROM test_sales")
    count = result.fetchone()[0]
    print(f"✅ Created test table with {count} rows")
    
    # Test query engine
    engine = QueryEngine(conn)
    query_result = engine.execute_query("SELECT product, SUM(sales) as total_sales FROM test_sales GROUP BY product")
    if query_result is not None:
        if not isinstance(query_result, pd.DataFrame):
            df = pd.DataFrame(query_result)
        else:
            df = query_result
        print(f"✅ Query engine working - got {len(df)} product categories")
    else:
        print("⚠️ Query returned no results")
    
    return conn


def test_llm_integration(conn):
    """Test LM Studio integration for SQL generation."""
    print("\nTesting LM Studio integration...")
    
    schema_extractor = SchemaExtractor(conn)
    sql_generator = SQLGenerator(schema_extractor=schema_extractor)
    
    # Check availability
    if sql_generator.is_available():
        print("✅ LM Studio is connected and available")
        
        # Test SQL generation
        try:
            prompt = "Show me total sales by product"
            sql = sql_generator.generate_sql(prompt)
            if sql:
                print(f"✅ Generated SQL: {sql[:100]}...")
            else:
                print("⚠️ SQL generation returned None - LM Studio may need a model loaded")
        except Exception as e:
            print(f"⚠️ SQL generation error: {e}")
    else:
        print("⚠️ LM Studio is not available - please ensure it's running on localhost:1234")
    
    return sql_generator


def test_visualization_engine():
    """Test smart visualization recommendation engine."""
    print("\nTesting visualization engine...")
    
    # Create test dataframes with different structures
    test_data = {
        'time_series': pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=30),
            'value': [100 + i*5 + (i%7)*10 for i in range(30)]
        }),
        'categorical': pd.DataFrame({
            'category': ['A', 'B', 'C', 'D', 'E'],
            'count': [45, 38, 52, 41, 43]
        }),
        'scatter': pd.DataFrame({
            'x': range(20),
            'y': [i*2 + (i%3)*5 for i in range(20)]
        })
    }
    
    engine = ChartRecommendationEngine()
    
    for data_type, df in test_data.items():
        recommendations = engine.recommend_charts(df)
        if recommendations:
            best = recommendations[0]
            print(f"✅ {data_type}: Recommended {best.chart_type} (score: {best.score:.2f})")
        else:
            print(f"⚠️ {data_type}: No recommendations generated")


def test_streamlit_components():
    """Test that all UI components are importable."""
    print("\nTesting UI components...")
    
    try:
        from duckdb_analytics.ui.chat_interface import ChatInterface
        print("✅ ChatInterface imported successfully")
    except ImportError as e:
        print(f"❌ ChatInterface import failed: {e}")
    
    try:
        from duckdb_analytics.ui.sql_editor import EnhancedSQLEditor
        print("✅ EnhancedSQLEditor imported successfully")
    except ImportError as e:
        print(f"❌ EnhancedSQLEditor import failed: {e}")
    
    try:
        from duckdb_analytics.ui.visualizer import SmartVisualizer
        print("✅ SmartVisualizer imported successfully")
    except ImportError as e:
        print(f"❌ SmartVisualizer import failed: {e}")


def main():
    """Run all tests."""
    print("=" * 50)
    print("SQL Analytics Studio - Streamlined Version Test")
    print("=" * 50)
    
    # Test core functionality
    conn = test_database_connection()
    
    # Test LLM integration
    test_llm_integration(conn)
    
    # Test visualization
    test_visualization_engine()
    
    # Test UI components
    test_streamlit_components()
    
    print("\n" + "=" * 50)
    print("Testing complete!")
    print("\nTo run the app:")
    print("  streamlit run app.py")
    print("\nMake sure LM Studio is running on localhost:1234 for full functionality.")
    print("=" * 50)


if __name__ == "__main__":
    main()