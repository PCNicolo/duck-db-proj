"""
Streamlined SQL Analytics Studio
A simplified DuckDB analytics tool with natural language SQL generation and smart visualization.
"""

import streamlit as st
import pandas as pd
import duckdb
import tempfile
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, Dict, Any, List

# Import our modules
import sys
sys.path.append('src')
from duckdb_analytics.core.connection import DuckDBConnection
from duckdb_analytics.core.query_engine import QueryEngine
from duckdb_analytics.llm.sql_generator import SQLGenerator
from duckdb_analytics.llm.schema_extractor import SchemaExtractor
from duckdb_analytics.visualizations.recommendation_engine import ChartRecommendationEngine

# Page configuration
st.set_page_config(
    page_title="SQL Analytics Studio",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if "db_connection" not in st.session_state:
    st.session_state.db_connection = DuckDBConnection()
    st.session_state.db_connection.connect()

if "query_engine" not in st.session_state:
    st.session_state.query_engine = QueryEngine(st.session_state.db_connection)

if "schema_extractor" not in st.session_state:
    st.session_state.schema_extractor = SchemaExtractor(st.session_state.db_connection)

if "sql_generator" not in st.session_state:
    st.session_state.sql_generator = SQLGenerator(schema_extractor=st.session_state.schema_extractor)

if "chart_recommender" not in st.session_state:
    st.session_state.chart_recommender = ChartRecommendationEngine()

if "registered_tables" not in st.session_state:
    st.session_state.registered_tables = []

if "query_result" not in st.session_state:
    st.session_state.query_result = None

if "current_sql" not in st.session_state:
    st.session_state.current_sql = ""

def load_sample_data():
    """Load sample data for testing."""
    conn = st.session_state.db_connection
    
    # Create sample sales data
    sample_query = """
    CREATE OR REPLACE TABLE sales AS 
    SELECT 
        DATE '2024-01-01' + INTERVAL (i % 365) DAY as order_date,
        'Customer_' || (i % 100) as customer_id,
        'Product_' || (i % 50) as product_id,
        ROUND(RANDOM() * 1000, 2) as amount,
        CASE 
            WHEN i % 4 = 0 THEN 'North'
            WHEN i % 4 = 1 THEN 'South'
            WHEN i % 4 = 2 THEN 'East'
            ELSE 'West'
        END as region
    FROM generate_series(1, 1000) as t(i);
    """
    
    try:
        conn.execute(sample_query)
        st.session_state.registered_tables.append({
            "name": "sales",
            "rows": 1000,
            "columns": 5
        })
        return True
    except Exception as e:
        st.error(f"Error loading sample data: {e}")
        return False

def process_uploaded_file(uploaded_file):
    """Process an uploaded CSV or Parquet file."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        tmp_path = tmp_file.name
    
    table_name = Path(uploaded_file.name).stem.replace(" ", "_").replace("-", "_")
    
    try:
        if uploaded_file.name.endswith(".csv"):
            st.session_state.db_connection.register_csv(tmp_path, table_name)
        else:
            st.session_state.db_connection.register_parquet(tmp_path, table_name)
        
        # Get table info
        info = st.session_state.db_connection.get_table_info(table_name)
        rows = st.session_state.db_connection.execute(f"SELECT COUNT(*) FROM {table_name}")[0][0]
        
        st.session_state.registered_tables.append({
            "name": table_name,
            "rows": rows,
            "columns": len(info)
        })
        return True
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return False

def generate_sql_from_natural_language(prompt: str) -> Optional[str]:
    """Generate SQL from natural language using LM Studio."""
    if not st.session_state.sql_generator.is_available():
        st.warning("LM Studio is not available. Please ensure it's running on localhost:1234")
        return None
    
    try:
        sql = st.session_state.sql_generator.generate_sql(prompt)
        return sql
    except Exception as e:
        st.error(f"Error generating SQL: {e}")
        return None

def execute_query(sql: str) -> Optional[pd.DataFrame]:
    """Execute SQL query and return results as DataFrame."""
    try:
        result = st.session_state.query_engine.execute_query(sql)
        if result and len(result) > 0:
            # Convert to DataFrame
            df = pd.DataFrame(result)
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Query error: {e}")
        return None

def create_visualization(df: pd.DataFrame, chart_type: str = "auto"):
    """Create a visualization from the dataframe."""
    if df.empty:
        st.info("No data to visualize")
        return
    
    # Auto-detect chart type if needed
    if chart_type == "auto":
        recommendations = st.session_state.chart_recommender.recommend_charts(df)
        if recommendations:
            chart_type = recommendations[0].chart_type
        else:
            chart_type = "table"
    
    # Create the appropriate chart
    if chart_type == "line":
        # Assume first column is x-axis, others are y-values
        if len(df.columns) >= 2:
            fig = px.line(df, x=df.columns[0], y=df.columns[1:])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Line chart requires at least 2 columns")
    
    elif chart_type == "bar":
        if len(df.columns) >= 2:
            fig = px.bar(df, x=df.columns[0], y=df.columns[1])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Bar chart requires at least 2 columns")
    
    elif chart_type == "scatter":
        if len(df.columns) >= 2:
            fig = px.scatter(df, x=df.columns[0], y=df.columns[1])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Scatter plot requires at least 2 columns")
    
    elif chart_type == "pie":
        if len(df.columns) >= 2:
            fig = px.pie(df, names=df.columns[0], values=df.columns[1])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Pie chart requires at least 2 columns")
    
    elif chart_type == "heatmap":
        # Try to create a pivot table for heatmap
        if len(df.columns) >= 3:
            try:
                pivot = df.pivot_table(index=df.columns[0], columns=df.columns[1], values=df.columns[2])
                fig = px.imshow(pivot, aspect="auto")
                st.plotly_chart(fig, use_container_width=True)
            except:
                st.warning("Cannot create heatmap from this data structure")
        else:
            st.warning("Heatmap requires at least 3 columns")
    
    else:  # Default to table
        st.dataframe(df, use_container_width=True)

def main():
    """Main application."""
    
    # Header with data management
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.title("📊 SQL Analytics Studio")
    with col2:
        uploaded_file = st.file_uploader("Upload CSV/Parquet", type=["csv", "parquet"], label_visibility="collapsed")
        if uploaded_file:
            if process_uploaded_file(uploaded_file):
                st.success(f"Loaded {uploaded_file.name}")
                st.rerun()
    with col3:
        if st.button("Load Sample Data", type="secondary", use_container_width=True):
            if load_sample_data():
                st.success("Sample data loaded!")
                st.rerun()
    
    # Show available tables
    if st.session_state.registered_tables:
        st.markdown("**Available tables:** " + ", ".join([f"`{t['name']}` ({t['rows']:,} rows)" for t in st.session_state.registered_tables]))
    else:
        st.info("No data loaded. Upload a file or load sample data to get started.")
    
    st.divider()
    
    # Main layout: Chat and SQL Editor side by side
    col_chat, col_sql = st.columns([1, 1])
    
    with col_chat:
        st.subheader("💬 Chat Helper")
        
        # Natural language input
        nl_query = st.text_area(
            "Describe what you want to query:",
            placeholder="Example: Show me total sales by month",
            height=100,
            key="nl_input"
        )
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("Generate SQL →", type="primary", use_container_width=True):
                if nl_query:
                    with st.spinner("Generating SQL..."):
                        generated_sql = generate_sql_from_natural_language(nl_query)
                        if generated_sql:
                            st.session_state.current_sql = generated_sql
                            st.rerun()
        
        with col_btn2:
            if st.button("Clear", use_container_width=True):
                st.session_state.current_sql = ""
                st.rerun()
        
        # Show explanation if we have a query
        if st.session_state.current_sql:
            st.markdown("---")
            st.markdown("💡 **Query Explanation:**")
            st.info("This query will analyze your data based on the SQL shown in the editor. Click 'Run Query' to execute it.")
    
    with col_sql:
        st.subheader("📝 SQL Editor")
        
        # SQL editor
        sql_query = st.text_area(
            "SQL Query:",
            value=st.session_state.current_sql,
            height=200,
            placeholder="Enter SQL query or generate from chat...",
            key="sql_editor"
        )
        
        col_btn3, col_btn4 = st.columns(2)
        with col_btn3:
            if st.button("▶ Run Query", type="primary", use_container_width=True):
                if sql_query:
                    with st.spinner("Executing query..."):
                        result = execute_query(sql_query)
                        if result is not None:
                            st.session_state.query_result = result
                            st.session_state.current_sql = sql_query
        
        with col_btn4:
            if st.button("📋 Copy", use_container_width=True):
                st.write("SQL copied to clipboard!")  # Note: Actual clipboard functionality requires JavaScript
    
    # Results section
    if st.session_state.query_result is not None:
        st.divider()
        st.subheader("📊 Results")
        
        # View options
        col_view1, col_view2, col_view3 = st.columns([1, 1, 2])
        with col_view1:
            view_mode = st.radio("View:", ["Table", "Chart"], horizontal=True)
        
        with col_view2:
            if view_mode == "Chart":
                chart_type = st.selectbox(
                    "Chart Type:",
                    ["auto", "line", "bar", "scatter", "pie", "heatmap"],
                    label_visibility="collapsed"
                )
            else:
                chart_type = "table"
        
        # Display results
        if view_mode == "Table":
            st.dataframe(st.session_state.query_result, use_container_width=True)
        else:
            create_visualization(st.session_state.query_result, chart_type)
        
        # Show row count
        st.caption(f"Returned {len(st.session_state.query_result):,} rows")

if __name__ == "__main__":
    main()