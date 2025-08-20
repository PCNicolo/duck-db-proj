"""DuckDB Analytics Dashboard - Streamlit Application."""

import logging
import tempfile
from pathlib import Path
from typing import List

import pandas as pd
import plotly.express as px
import streamlit as st

from src.duckdb_analytics.core.connection import DuckDBConnection
from src.duckdb_analytics.core.query_engine import QueryEngine
from src.duckdb_analytics.data.file_manager import FileManager
from src.duckdb_analytics.llm.sql_generator import SQLGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def auto_load_data():
    """Auto-load data files from data/samples directory."""
    data_dir = Path("data/samples")
    if not data_dir.exists():
        return

    loaded_count = 0

    # Load CSV files
    for csv_file in data_dir.glob("*.csv"):
        table_name = csv_file.stem
        try:
            st.session_state.db_connection.register_csv(str(csv_file), table_name)

            # Get table info
            table_info = st.session_state.db_connection.get_table_info(table_name)

            # Add to registered tables
            st.session_state.registered_tables.append({
                "name": table_name,
                "path": str(csv_file),
                "rows": table_info["row_count"],
                "columns": len(table_info["columns"])
            })
            loaded_count += 1
        except Exception as e:
            print(f"Failed to load {csv_file}: {e}")

    # Optionally load Parquet files with _parquet suffix to avoid duplicates
    for parquet_file in data_dir.glob("*.parquet"):
        table_name = parquet_file.stem + "_parquet"
        try:
            st.session_state.db_connection.register_parquet(
                str(parquet_file), table_name
            )

            # Get table info
            table_info = st.session_state.db_connection.get_table_info(table_name)

            # Add to registered tables
            st.session_state.registered_tables.append({
                "name": table_name,
                "path": str(parquet_file),
                "rows": table_info["row_count"],
                "columns": len(table_info["columns"])
            })
            loaded_count += 1
        except Exception as e:
            print(f"Failed to load {parquet_file}: {e}")

    if loaded_count > 0:
        st.success(f"✅ Auto-loaded {loaded_count} data files from data/samples/")

# Page configuration
st.set_page_config(
    page_title="DuckDB Analytics Dashboard",
    page_icon="🦆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "db_connection" not in st.session_state:
    st.session_state.db_connection = DuckDBConnection()
    st.session_state.query_engine = QueryEngine(st.session_state.db_connection)
    st.session_state.file_manager = FileManager()
    st.session_state.sql_generator = SQLGenerator()
    st.session_state.registered_tables = []

    # Auto-load existing data files from data/samples
    auto_load_data()
    
    # Check LM Studio availability on startup
    if st.session_state.sql_generator.is_available():
        st.success("✅ LM Studio connected successfully")
    else:
        st.warning("⚠️ LM Studio not available - Natural language queries will be limited")

def main():
    """Main application entry point."""
    st.title("🦆 DuckDB Analytics Dashboard")
    st.markdown("**Analyze CSV and Parquet files with zero-copy SQL queries**")

    # Sidebar
    with st.sidebar:
        st.header("📁 Data Management")

        # File upload
        uploaded_files = st.file_uploader(
            "Upload Data Files",
            type=["csv", "parquet"],
            accept_multiple_files=True
        )

        if uploaded_files:
            process_uploaded_files(uploaded_files)

        # Display registered tables
        if st.session_state.registered_tables:
            st.subheader("📊 Available Tables")
            for table in st.session_state.registered_tables:
                with st.expander(f"📋 {table['name']}"):
                    st.write(f"**Rows:** {table['rows']:,}")
                    st.write(f"**Columns:** {table['columns']}")
                    btn_key = f"preview_{table['name']}"
                    if st.button(f"Preview {table['name']}", key=btn_key):
                        preview_table(table['name'])

        # Query statistics
        if st.button("📈 Query Statistics"):
            show_query_statistics()

    # Main content area with tabs
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📝 SQL Editor", "📊 Analytics", "📈 Visualizations", "🔍 Data Explorer"]
    )

    with tab1:
        sql_editor_tab()

    with tab2:
        analytics_tab()

    with tab3:
        visualizations_tab()

    with tab4:
        data_explorer_tab()

def process_uploaded_files(uploaded_files):
    """Process uploaded data files."""
    for uploaded_file in uploaded_files:
        # Save to temporary location
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=uploaded_file.name
        ) as tmp_file:
            tmp_file.write(uploaded_file.getbuffer())
            tmp_path = tmp_file.name

        # Register with DuckDB
        table_name = Path(uploaded_file.name).stem.replace(" ", "_").replace("-", "_")

        try:
            if uploaded_file.name.endswith(".csv"):
                st.session_state.db_connection.register_csv(tmp_path, table_name)
            else:
                st.session_state.db_connection.register_parquet(tmp_path, table_name)

            # Get table info
            table_info = st.session_state.db_connection.get_table_info(table_name)

            # Add to registered tables
            st.session_state.registered_tables.append({
                "name": table_name,
                "path": tmp_path,
                "rows": table_info["row_count"],
                "columns": len(table_info["columns"])
            })

            st.success(f"✅ Registered table: {table_name}")
        except Exception as e:
            st.error(f"❌ Failed to register {uploaded_file.name}: {e}")

def preview_table(table_name: str, limit: int = 10):
    """Preview table data."""
    query = f"SELECT * FROM {table_name} LIMIT {limit}"
    try:
        df = st.session_state.query_engine.execute_query(query)
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Failed to preview table: {e}")

def sql_editor_tab():
    """SQL query editor interface."""
    st.header("SQL Query Editor")

    # Initialize chat history in session state if not present
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Limit chat history to prevent memory issues (keep last 50 messages)
    MAX_CHAT_HISTORY = 50
    if len(st.session_state.chat_history) > MAX_CHAT_HISTORY:
        st.session_state.chat_history = st.session_state.chat_history[-MAX_CHAT_HISTORY:]

    # Chat UI Component - Natural Language Interface
    with st.container():
        st.subheader("💬 Natural Language Query")

        # Chat input area
        col_chat, col_send = st.columns([5, 1])
        with col_chat:
            user_query = st.text_input(
                "Ask a question",
                placeholder=(
                    "Ask in plain English "
                    "(e.g., 'Show me top 10 customers by revenue')"
                ),
                key="nl_query_input",
                label_visibility="collapsed"
            )

        with col_send:
            send_button = st.button("Send", type="primary", use_container_width=True)

        # Process chat input
        if (send_button or user_query) and user_query.strip():
            # Validate input length (prevent potential DOS)
            if len(user_query) > 1000:
                st.error("Query too long. Please limit to 1000 characters.")
            else:
                # Add user message to chat history
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": user_query.strip()
                })

                # Generate SQL using LM Studio if available
                if st.session_state.sql_generator.is_available():
                    with st.spinner("Generating SQL..."):
                        # Get table context if tables are registered
                        table_context = None
                        if st.session_state.registered_tables:
                            table_names = [t["name"] for t in st.session_state.registered_tables]
                            table_context = f"Available tables: {', '.join(table_names)}"
                        
                        # Format query with context
                        formatted_query = st.session_state.sql_generator.format_query_with_context(
                            user_query.strip(), table_context
                        )
                        
                        # Generate SQL
                        try:
                            generated_sql = st.session_state.sql_generator.generate_sql(formatted_query)
                            
                            if generated_sql:
                                # Validate the generated SQL doesn't contain dangerous operations
                                dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE']
                                sql_upper = generated_sql.upper()
                                
                                contains_dangerous = any(keyword in sql_upper for keyword in dangerous_keywords)
                                if contains_dangerous:
                                    sql_response = f"-- ⚠️ Generated SQL contains potentially dangerous operations\n"
                                    sql_response += f"-- Please review carefully before execution:\n{generated_sql}"
                                else:
                                    sql_response = f"-- Generated from: {user_query[:100]}...\n{generated_sql}"
                            else:
                                sql_response = "-- Failed to generate SQL. Possible issues:\n"
                                sql_response += "-- 1. LM Studio connection timeout (3 seconds)\n"
                                sql_response += "-- 2. Model returned empty response\n"
                                sql_response += "-- 3. Try rephrasing your query"
                        except Exception as e:
                            logger.error(f"Error generating SQL: {str(e)}")
                            sql_response = f"-- Error generating SQL: {str(e)[:100]}"
                else:
                    # Fallback if LM Studio is not available
                    sql_response = f"-- Natural Language: {user_query[:200]}\n"  # Truncate for safety
                    sql_response += "-- LM Studio not available. Please ensure:\n"
                    sql_response += "-- 1. LM Studio is running on port 1234\n"
                    sql_response += "-- 2. A SQL-capable model is loaded\n"
                    sql_response += "-- See docs/LM_STUDIO_SETUP.md for instructions"

                # Add SQL response to chat history
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": sql_response
                })

                # Clear the input field by rerunning the app
                st.rerun()

        # Chat History Display Area
        if st.session_state.chat_history:
            st.markdown("### Chat History")

            # Create a scrollable container for chat messages
            chat_container = st.container()
            with chat_container:
                for message in st.session_state.chat_history:
                    if message["role"] == "user":
                        # User message - right-aligned style
                        with st.container():
                            # Using columns for right alignment instead of unsafe HTML
                            col1, col2 = st.columns([1, 2])
                            with col2:
                                st.info(f"**You:** {message['content']}")
                    else:
                        # SQL response - left-aligned with code highlighting
                        with st.container():
                            st.markdown("**SQL Query:**")
                            st.code(message["content"], language="sql")
                            
                            # Add button to copy SQL to editor if it's a valid generated query
                            if not message["content"].startswith("--") or "\n" in message["content"]:
                                # Extract SQL (remove comments)
                                sql_lines = [line for line in message["content"].split("\n") 
                                           if not line.strip().startswith("--")]
                                if sql_lines:
                                    clean_sql = "\n".join(sql_lines)
                                    if st.button(f"📋 Copy to Editor", key=f"copy_{st.session_state.chat_history.index(message)}"):
                                        st.session_state.editor_sql = clean_sql
                                        st.rerun()

    # Divider between chat and SQL editor
    st.divider()

    # Pre-built query templates
    col1, col2 = st.columns([3, 1])

    with col2:
        template = st.selectbox(
            "Query Templates",
            ["Custom", "SELECT ALL", "COUNT", "GROUP BY", "JOIN", "WINDOW"]
        )

        if template != "Custom":
            query = get_query_template(template)
        else:
            query = ""

    with col1:
        # SQL editor - check if we need to populate from chat
        if "editor_sql" in st.session_state:
            query = st.session_state.editor_sql
            del st.session_state.editor_sql
            
        sql_query = st.text_area(
            "Enter SQL Query",
            value=query,
            height=200,
            placeholder="SELECT * FROM table_name LIMIT 100"
        )

    # Query execution
    col1, col2, col3 = st.columns([1, 1, 4])

    with col1:
        if st.button("▶️ Execute", type="primary"):
            execute_query(sql_query)

    with col2:
        if st.button("📋 Explain"):
            explain_query(sql_query)

    # Results area
    if "query_result" in st.session_state:
        st.subheader("Query Results")

        df = st.session_state.query_result

        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Rows", f"{len(df):,}")
        with col2:
            st.metric("Columns", f"{len(df.columns):,}")
        with col3:
            if "execution_time" in st.session_state:
                st.metric("Execution Time", f"{st.session_state.execution_time:.3f}s")

        # Display data
        st.dataframe(df, use_container_width=True)

        # Export options
        col1, col2, col3 = st.columns(3)
        with col1:
            csv = df.to_csv(index=False)
            st.download_button(
                "📥 Download CSV",
                csv,
                "query_result.csv",
                "text/csv"
            )
        with col2:
            parquet = df.to_parquet(index=False)
            st.download_button(
                "📥 Download Parquet",
                parquet,
                "query_result.parquet",
                "application/octet-stream"
            )

def analytics_tab():
    """Pre-built analytics interface."""
    st.header("Analytics Dashboard")

    if not st.session_state.registered_tables:
        st.info("📤 Please upload data files to begin analysis")
        return

    # Select table for analysis
    table_name = st.selectbox(
        "Select Table",
        [t["name"] for t in st.session_state.registered_tables]
    )

    if table_name:
        # Get table schema
        table_info = st.session_state.db_connection.get_table_info(table_name)
        columns = [col["name"] for col in table_info["columns"]]

        # Analysis options
        st.subheader("📊 Quick Analytics")

        col1, col2 = st.columns(2)

        with col1:
            # Summary statistics
            if st.button("📈 Summary Statistics"):
                show_summary_statistics(table_name)

        with col2:
            # Missing values
            if st.button("❓ Missing Values"):
                show_missing_values(table_name)

        # Aggregation builder
        st.subheader("🔧 Custom Aggregation")

        col1, col2, col3 = st.columns(3)

        with col1:
            group_by_cols = st.multiselect("GROUP BY", columns)

        with col2:
            agg_col = st.selectbox("Aggregate Column", columns)

        with col3:
            agg_func = st.selectbox(
                "Function",
                ["COUNT", "SUM", "AVG", "MIN", "MAX", "STDDEV"]
            )

        if st.button("🚀 Run Aggregation"):
            run_aggregation(table_name, group_by_cols, agg_col, agg_func)

def visualizations_tab():
    """Data visualization interface."""
    st.header("Data Visualizations")

    if "query_result" not in st.session_state:
        st.info("📊 Execute a query to visualize results")
        return

    df = st.session_state.query_result

    # Visualization type selection
    viz_type = st.selectbox(
        "Visualization Type",
        ["Line Chart", "Bar Chart", "Scatter Plot", "Histogram", "Box Plot", "Heatmap"]
    )

    # Column selection based on viz type
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    all_cols = df.columns.tolist()

    if viz_type == "Line Chart":
        col1, col2 = st.columns(2)
        with col1:
            x_col = st.selectbox("X-axis", all_cols)
        with col2:
            y_cols = st.multiselect("Y-axis", numeric_cols)

        if x_col and y_cols:
            fig = px.line(df, x=x_col, y=y_cols, title="Line Chart")
            st.plotly_chart(fig, use_container_width=True)

    elif viz_type == "Bar Chart":
        col1, col2 = st.columns(2)
        with col1:
            x_col = st.selectbox("X-axis", all_cols)
        with col2:
            y_col = st.selectbox("Y-axis", numeric_cols)

        if x_col and y_col:
            fig = px.bar(df, x=x_col, y=y_col, title="Bar Chart")
            st.plotly_chart(fig, use_container_width=True)

    elif viz_type == "Scatter Plot":
        col1, col2, col3 = st.columns(3)
        with col1:
            x_col = st.selectbox("X-axis", numeric_cols)
        with col2:
            y_col = st.selectbox("Y-axis", numeric_cols)
        with col3:
            color_col = st.selectbox("Color", [None] + all_cols)

        if x_col and y_col:
            fig = px.scatter(
                df, x=x_col, y=y_col, color=color_col, title="Scatter Plot"
            )
            st.plotly_chart(fig, use_container_width=True)

    elif viz_type == "Histogram":
        col = st.selectbox("Column", numeric_cols)
        bins = st.slider("Number of Bins", 10, 100, 30)

        if col:
            fig = px.histogram(df, x=col, nbins=bins, title=f"Histogram of {col}")
            st.plotly_chart(fig, use_container_width=True)

    elif viz_type == "Box Plot":
        col1, col2 = st.columns(2)
        with col1:
            y_col = st.selectbox("Values", numeric_cols)
        with col2:
            x_col = st.selectbox("Categories (optional)", [None] + all_cols)

        if y_col:
            fig = px.box(df, x=x_col, y=y_col, title="Box Plot")
            st.plotly_chart(fig, use_container_width=True)

    elif viz_type == "Heatmap":
        if len(numeric_cols) >= 2:
            corr_matrix = df[numeric_cols].corr()
            fig = px.imshow(corr_matrix, title="Correlation Heatmap",
                          labels=dict(color="Correlation"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Need at least 2 numeric columns for correlation heatmap")

def data_explorer_tab():
    """Interactive data exploration interface."""
    st.header("Data Explorer")

    if not st.session_state.registered_tables:
        st.info("📤 Please upload data files to explore")
        return

    # Table selection
    table_name = st.selectbox(
        "Select Table to Explore",
        [t["name"] for t in st.session_state.registered_tables]
    )

    if table_name:
        # Load data
        query = f"SELECT * FROM {table_name}"
        df = st.session_state.query_engine.execute_query(query)

        # Filtering options
        st.subheader("🔍 Filters")

        filters = {}
        columns = df.columns.tolist()

        # Dynamic filter creation
        for col in columns:
            col_type = df[col].dtype

            if col_type in ["int64", "float64"]:
                col1, col2 = st.columns(2)
                with col1:
                    min_val = st.number_input(
                        f"{col} (min)", value=float(df[col].min())
                    )
                with col2:
                    max_val = st.number_input(
                        f"{col} (max)", value=float(df[col].max())
                    )
                filters[col] = (min_val, max_val)

            elif col_type == "object":
                unique_vals = df[col].unique().tolist()
                if len(unique_vals) <= 20:
                    selected = st.multiselect(
                        f"{col}", unique_vals, default=unique_vals
                    )
                    filters[col] = selected

        # Apply filters
        filtered_df = df.copy()
        for col, filter_val in filters.items():
            if isinstance(filter_val, tuple):
                filtered_df = filtered_df[
                    (filtered_df[col] >= filter_val[0]) &
                    (filtered_df[col] <= filter_val[1])
                ]
            elif isinstance(filter_val, list):
                filtered_df = filtered_df[filtered_df[col].isin(filter_val)]

        # Display filtered data
        st.subheader(f"📊 Data View ({len(filtered_df):,} rows)")
        st.dataframe(filtered_df, use_container_width=True)

        # Export filtered data
        if len(filtered_df) > 0:
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                "📥 Download Filtered Data",
                csv,
                f"{table_name}_filtered.csv",
                "text/csv"
            )

def get_query_template(template: str) -> str:
    """Get SQL query template."""
    templates = {
        "SELECT ALL": "SELECT * FROM table_name LIMIT 100",
        "COUNT": "SELECT COUNT(*) as count FROM table_name",
        "GROUP BY": """SELECT
    column1,
    COUNT(*) as count,
    AVG(column2) as avg_value
FROM table_name
GROUP BY column1
ORDER BY count DESC""",
        "JOIN": """SELECT
    t1.column1,
    t2.column2
FROM table1 t1
JOIN table2 t2 ON t1.id = t2.id
LIMIT 100""",
        "WINDOW": """SELECT
    column1,
    column2,
    ROW_NUMBER() OVER (PARTITION BY column1 ORDER BY column2) as row_num
FROM table_name"""
    }
    return templates.get(template, "")

def execute_query(query: str):
    """Execute SQL query and store results."""
    try:
        import time
        start_time = time.time()

        df = st.session_state.query_engine.execute_query(query)
        execution_time = time.time() - start_time

        st.session_state.query_result = df
        st.session_state.execution_time = execution_time

        st.success(f"✅ Query executed successfully in {execution_time:.3f}s")
    except Exception as e:
        st.error(f"❌ Query failed: {e}")

def explain_query(query: str):
    """Explain query execution plan."""
    try:
        plan = st.session_state.query_engine.explain_query(query)
        st.code(plan, language="text")
    except Exception as e:
        st.error(f"Failed to explain query: {e}")

def show_query_statistics():
    """Display query engine statistics."""
    stats = st.session_state.query_engine.get_statistics()

    st.subheader("Query Statistics")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Queries", stats["total_queries"])
    with col2:
        st.metric("Cache Hits", stats["total_cache_hits"])
    with col3:
        st.metric("Cache Hit Rate", f"{stats['cache_hit_rate']:.1%}")

def show_summary_statistics(table_name: str):
    """Show summary statistics for a table."""
    query = f"SELECT * FROM {table_name}"
    df = st.session_state.query_engine.execute_query(query)

    st.subheader("Summary Statistics")
    st.dataframe(df.describe(), use_container_width=True)

def show_missing_values(table_name: str):
    """Show missing values analysis."""
    query = f"SELECT * FROM {table_name}"
    df = st.session_state.query_engine.execute_query(query)

    missing = df.isnull().sum()
    missing_pct = (missing / len(df)) * 100

    missing_df = pd.DataFrame({
        "Column": missing.index,
        "Missing Count": missing.values,
        "Missing %": missing_pct.values
    })

    st.subheader("Missing Values Analysis")
    st.dataframe(missing_df, use_container_width=True)

def run_aggregation(
    table_name: str, group_by_cols: List[str], agg_col: str, agg_func: str
):
    """Run custom aggregation query."""
    if not group_by_cols:
        query = f"SELECT {agg_func}({agg_col}) as result FROM {table_name}"
    else:
        group_by_str = ", ".join(group_by_cols)
        select_str = (
            ", ".join(group_by_cols) +
            f", {agg_func}({agg_col}) as {agg_func.lower()}_{agg_col}"
        )
        query = f"SELECT {select_str} FROM {table_name} GROUP BY {group_by_str}"

    execute_query(query)

if __name__ == "__main__":
    main()

