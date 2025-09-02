"""DuckDB Analytics Dashboard - Streamlit Application."""

import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st

from src.duckdb_analytics.core.connection import DuckDBConnection
from src.duckdb_analytics.core.optimized_query_executor import OptimizedQueryExecutor
from src.duckdb_analytics.core.query_engine import QueryEngine
from src.duckdb_analytics.data.file_manager import FileManager
from src.duckdb_analytics.llm.schema_extractor import SchemaExtractor
from src.duckdb_analytics.llm.sql_generator import SQLGenerator
from src.duckdb_analytics.ui.sql_editor import EnhancedSQLEditor
from src.duckdb_analytics.ui.streaming_components import (
    StreamingQueryDisplay,
)

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
            st.session_state.registered_tables.append(
                {
                    "name": table_name,
                    "path": str(csv_file),
                    "rows": table_info["row_count"],
                    "columns": len(table_info["columns"]),
                }
            )
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
            st.session_state.registered_tables.append(
                {
                    "name": table_name,
                    "path": str(parquet_file),
                    "rows": table_info["row_count"],
                    "columns": len(table_info["columns"]),
                }
            )
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
    initial_sidebar_state="expanded",
)

# Initialize session state
if "db_connection" not in st.session_state:
    st.session_state.db_connection = DuckDBConnection()
    st.session_state.query_engine = QueryEngine(st.session_state.db_connection)
    st.session_state.optimized_executor = OptimizedQueryExecutor(
        st.session_state.db_connection,
        cache_size=100,
        cache_memory_mb=100,
        chunk_size=1000,
    )
    st.session_state.file_manager = FileManager()
    st.session_state.sql_generator = SQLGenerator()
    st.session_state.schema_extractor = SchemaExtractor(st.session_state.db_connection)
    st.session_state.registered_tables = []

    # Chat interface state management
    st.session_state.chat_history = []
    st.session_state.processing_query = False
    st.session_state.last_query_time = 0
    st.session_state.pending_query = None
    st.session_state.schema_cache = None
    st.session_state.schema_cache_time = 0

    # Initialize editor_sql if not exists to prevent NoneType errors
    st.session_state.editor_sql = None
    st.session_state.query_result = None
    st.session_state.execution_time = 0

    # Auto-load existing data files from data/samples
    auto_load_data()

    # Check LM Studio availability on startup
    if st.session_state.sql_generator.is_available():
        st.success("✅ LM Studio connected successfully")
    else:
        st.warning(
            "⚠️ LM Studio not available - Natural language queries will be limited"
        )


def main():
    """Main application entry point."""
    st.title("🦆 DuckDB Analytics Dashboard")
    st.markdown("**Analyze CSV and Parquet files with zero-copy SQL queries**")

    # Sidebar
    with st.sidebar:
        st.header("📁 Data Management")

        # File upload
        uploaded_files = st.file_uploader(
            "Upload Data Files", type=["csv", "parquet"], accept_multiple_files=True
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
                        preview_table(table["name"])

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
            st.session_state.registered_tables.append(
                {
                    "name": table_name,
                    "path": tmp_path,
                    "rows": table_info["row_count"],
                    "columns": len(table_info["columns"]),
                }
            )

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
    """SQL query editor interface with enhanced features."""
    st.header("SQL Query Editor")

    # Check if we should use enhanced editor
    use_enhanced = st.checkbox(
        "Use Enhanced Editor (Beta)", value=True, key="use_enhanced_editor"
    )

    if use_enhanced:
        # Use the new enhanced SQL editor
        editor = EnhancedSQLEditor(
            query_engine=st.session_state.query_engine,
            db_connection=st.session_state.db_connection,
        )
        editor.render()

        # Display results if available
        if (
            "query_result" in st.session_state
            and st.session_state.query_result is not None
        ):
            st.divider()
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
                    st.metric(
                        "Execution Time", f"{st.session_state.execution_time:.3f}s"
                    )

            # Display data
            st.dataframe(df, use_container_width=True)

            # Export options
            col1, col2, col3 = st.columns(3)
            with col1:
                csv = df.to_csv(index=False)
                st.download_button(
                    "📥 Download CSV", csv, "query_result.csv", "text/csv"
                )
            with col2:
                parquet = df.to_parquet(index=False)
                st.download_button(
                    "📥 Download Parquet",
                    parquet,
                    "query_result.parquet",
                    "application/octet-stream",
                )
        return

    # Original editor code below (fallback)
    import time

    # Initialize chat history in session state if not present
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Limit chat history to prevent memory issues (keep last 50 messages)
    MAX_CHAT_HISTORY = 50
    if len(st.session_state.chat_history) > MAX_CHAT_HISTORY:
        st.session_state.chat_history = st.session_state.chat_history[
            -MAX_CHAT_HISTORY:
        ]

    # Chat UI Component - Natural Language Interface (Single Container)
    st.subheader("💬 Natural Language Query")

    # Create a form to prevent multiple submissions
    with st.form(key="chat_form", clear_on_submit=True):
        # Chat input area
        user_query = st.text_input(
            "Ask a question",
            placeholder=(
                "Ask in plain English " "(e.g., 'Show me top 10 customers by revenue')"
            ),
            key="nl_query_input_form",
            label_visibility="collapsed",
        )

        # Submit button inside form
        col1, col2, col3 = st.columns([3, 1, 1])
        with col2:
            send_button = st.form_submit_button(
                "Send", type="primary", use_container_width=True
            )
        with col3:
            clear_chat = st.form_submit_button("Clear Chat", use_container_width=True)

    # Clear chat history if requested
    if clear_chat:
        st.session_state.chat_history = []
        st.rerun()

    # Process chat input with debouncing and state management
    if send_button and user_query.strip():
        current_time = time.time()

        # Debouncing: prevent queries within 1 second
        if current_time - st.session_state.last_query_time < 1.0:
            st.warning("⏱️ Please wait a moment before sending another query")
        elif st.session_state.processing_query:
            st.warning("⏳ Still processing previous query, please wait...")
        elif len(user_query) > 1000:
            st.error("Query too long. Please limit to 1000 characters.")
        else:
            # Set processing state
            st.session_state.processing_query = True
            st.session_state.last_query_time = current_time

            # Add user message to chat history
            st.session_state.chat_history.append(
                {"role": "user", "content": user_query.strip()}
            )

            # Generate SQL using LM Studio if available
            if st.session_state.sql_generator.is_available():
                with st.spinner("🤖 Generating SQL query..."):
                    # Use cached schema if available and recent (cache for 5 minutes)
                    schema_context = None
                    if st.session_state.registered_tables:
                        cache_age = current_time - st.session_state.schema_cache_time
                        if st.session_state.schema_cache and cache_age < 300:
                            schema_context = st.session_state.schema_cache
                        else:
                            # Refresh schema cache
                            schema_context = (
                                st.session_state.schema_extractor.format_for_llm(
                                    include_samples=False, max_tables=20
                                )
                            )
                            st.session_state.schema_cache = schema_context
                            st.session_state.schema_cache_time = current_time

                    # Generate SQL with schema context
                    try:
                        generated_sql = st.session_state.sql_generator.generate_sql(
                            user_query.strip(), schema_context
                        )

                        if generated_sql:
                            # Validate SQL against actual schema
                            is_valid, validation_errors = (
                                st.session_state.schema_extractor.validate_sql(
                                    generated_sql
                                )
                            )

                            if not is_valid:
                                # Show validation errors
                                sql_response = (
                                    "-- ⚠️ Generated SQL has validation issues:\n"
                                )
                                for error in validation_errors:
                                    sql_response += f"-- {error}\n"
                                sql_response += f"\n-- Generated SQL (needs correction):\n{generated_sql}"
                            else:
                                # Check for dangerous operations
                                dangerous_keywords = [
                                    "DROP",
                                    "DELETE",
                                    "TRUNCATE",
                                    "ALTER",
                                    "CREATE",
                                ]
                                sql_upper = generated_sql.upper()

                                contains_dangerous = any(
                                    keyword in sql_upper
                                    for keyword in dangerous_keywords
                                )
                                if contains_dangerous:
                                    sql_response = "-- ⚠️ Generated SQL contains potentially dangerous operations\n"
                                    sql_response += f"-- Please review carefully before execution:\n{generated_sql}"
                                else:
                                    sql_response = f"-- ✅ Valid SQL generated from: {user_query[:100]}...\n{generated_sql}"
                        else:
                            sql_response = (
                                "-- Failed to generate SQL. Possible issues:\n"
                            )
                            sql_response += (
                                "-- 1. LM Studio connection timeout (10 seconds)\n"
                            )
                            sql_response += "-- 2. Model returned empty response\n"
                            sql_response += "-- 3. Try rephrasing your query"
                    except Exception as e:
                        logger.error(f"Error generating SQL: {str(e)}")
                        sql_response = f"-- Error generating SQL: {str(e)[:100]}"
            else:
                # Fallback if LM Studio is not available
                sql_response = (
                    f"-- Natural Language: {user_query[:200]}\n"  # Truncate for safety
                )
                sql_response += "-- LM Studio not available. Please ensure:\n"
                sql_response += "-- 1. LM Studio is running on port 1234\n"
                sql_response += "-- 2. A SQL-capable model is loaded\n"
                sql_response += "-- See docs/LM_STUDIO_SETUP.md for instructions"

            # Add SQL response to chat history
            st.session_state.chat_history.append(
                {"role": "assistant", "content": sql_response}
            )

            # Reset processing state
            st.session_state.processing_query = False

            # Rerun to update UI (only once, after all processing is complete)
            st.rerun()

    # Chat History Display Area (Outside the form to prevent duplication)
    if st.session_state.chat_history:
        st.markdown("### Chat History")

        # Create a scrollable container for chat messages with height limit
        chat_container = st.container(height=400)
        with chat_container:
            for idx, message in enumerate(st.session_state.chat_history):
                if message["role"] == "user":
                    # User message - right-aligned style
                    col1, col2 = st.columns([1, 3])
                    with col2:
                        st.info(f"**You:** {message['content']}")
                else:
                    # SQL response - left-aligned with code highlighting
                    st.markdown("**🤖 SQL Assistant:**")
                    st.code(message["content"], language="sql")

                    # Add buttons for valid SQL queries
                    if (
                        not message["content"].startswith("--")
                        or "\n" in message["content"]
                    ):
                        # Extract SQL (remove comments) with defensive programming
                        try:
                            # Safely get message content with fallback
                            content = message.get("content", "")
                            if not content:
                                logger.warning(f"Empty message content at index {idx}")
                                continue

                            # Extract SQL lines safely - improved logic
                            sql_lines = []
                            for line in content.split("\n"):
                                line_stripped = line.strip()
                                # Skip pure comment lines
                                if line_stripped.startswith("--"):
                                    continue
                                # Handle lines that may have inline comments
                                elif line_stripped:
                                    # Check if line contains inline comment
                                    if "--" in line:
                                        # Extract the SQL part before the comment
                                        sql_part = line.split("--")[0].rstrip()
                                        if sql_part.strip():
                                            sql_lines.append(sql_part)
                                    else:
                                        # No comment, add the whole line
                                        sql_lines.append(line)

                            if sql_lines:
                                clean_sql = "\n".join(sql_lines).strip()
                                # Validate clean_sql is not empty after joining
                                if clean_sql and clean_sql.strip():
                                    col1, col2, col3 = st.columns([1, 1, 2])
                                    with col1:
                                        if st.button(
                                            "📋 Copy to Editor", key=f"copy_{idx}"
                                        ):
                                            try:
                                                # Defensive check before setting session state
                                                if clean_sql and isinstance(
                                                    clean_sql, str
                                                ):
                                                    st.session_state.editor_sql = (
                                                        clean_sql
                                                    )
                                                    # Show what was copied for debugging
                                                    st.success(
                                                        f"✅ SQL copied to editor: {clean_sql[:100]}..."
                                                    )
                                                    logger.info(
                                                        f"Copied SQL to editor: {clean_sql}"
                                                    )
                                                    st.rerun()
                                                else:
                                                    st.error(
                                                        "⚠️ Unable to copy: Invalid SQL content"
                                                    )
                                                    logger.error(
                                                        f"Invalid SQL content type: {type(clean_sql)}"
                                                    )
                                            except Exception as e:
                                                st.error(
                                                    f"❌ Failed to copy SQL: {str(e)}"
                                                )
                                                logger.error(
                                                    f"Copy to editor failed: {str(e)}",
                                                    exc_info=True,
                                                )

                                    with col2:
                                        # Add button to execute directly if SQL is valid
                                        if "✅ Valid SQL" in content:
                                            if st.button(
                                                "▶️ Execute", key=f"exec_{idx}"
                                            ):
                                                try:
                                                    execute_query(clean_sql)
                                                except Exception as e:
                                                    st.error(
                                                        f"❌ Execution failed: {str(e)}"
                                                    )
                                                    logger.error(
                                                        f"Query execution failed: {str(e)}",
                                                        exc_info=True,
                                                    )
                        except Exception as e:
                            logger.error(
                                f"Error processing message at index {idx}: {str(e)}",
                                exc_info=True,
                            )
                            st.error("⚠️ Unable to process SQL from message")

    # Divider between chat and SQL editor
    st.divider()

    # Pre-built query templates
    col1, col2 = st.columns([3, 1])

    with col2:
        template = st.selectbox(
            "Query Templates",
            ["Custom", "SELECT ALL", "COUNT", "GROUP BY", "JOIN", "WINDOW"],
        )

    with col1:
        # Initialize current_sql in session state if not exists
        if "current_sql" not in st.session_state:
            st.session_state.current_sql = ""

        # Check if we have SQL from the chat to transfer
        if "editor_sql" in st.session_state and st.session_state.editor_sql:
            # Safely retrieve and validate editor_sql
            try:
                transferred_sql = st.session_state.editor_sql
                if (
                    transferred_sql
                    and isinstance(transferred_sql, str)
                    and transferred_sql.strip()
                ):
                    st.session_state.current_sql = transferred_sql.strip()
                    # Display info that SQL was transferred
                    st.info(
                        f"📋 SQL copied from chat: {st.session_state.current_sql[:50]}..."
                    )
                    # Clear the editor_sql after successful transfer
                    st.session_state.editor_sql = None
                else:
                    logger.warning("editor_sql was empty or invalid type")
                    st.session_state.editor_sql = None
            except Exception as e:
                logger.error(f"Error retrieving editor_sql: {str(e)}", exc_info=True)
                st.session_state.editor_sql = None
        # Check template selection
        elif template != "Custom" and template:
            st.session_state.current_sql = get_query_template(template)

        # Text area that updates the session state
        sql_query = st.text_area(
            "Enter SQL Query",
            value=st.session_state.current_sql,
            height=200,
            placeholder="SELECT * FROM table_name LIMIT 100",
            key="sql_editor",
            on_change=lambda: setattr(
                st.session_state, "current_sql", st.session_state.sql_editor
            ),
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
    if "query_result" in st.session_state and st.session_state.query_result is not None:
        st.subheader("Query Results")

        # Defensive check for query_result
        try:
            df = st.session_state.query_result
            if df is None:
                st.warning("⚠️ No query results available")
                return
        except Exception as e:
            logger.error(f"Error accessing query_result: {str(e)}", exc_info=True)
            st.error(f"❌ Error displaying results: {str(e)}")
            return

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
            st.download_button("📥 Download CSV", csv, "query_result.csv", "text/csv")
        with col2:
            parquet = df.to_parquet(index=False)
            st.download_button(
                "📥 Download Parquet",
                parquet,
                "query_result.parquet",
                "application/octet-stream",
            )


def analytics_tab():
    """Enhanced analytics interface with templates, profiling, and filtering."""
    st.header("Analytics Dashboard")

    if not st.session_state.registered_tables:
        st.info("📤 Please upload data files to begin analysis")
        return

    # Select table for analysis
    table_name = st.selectbox(
        "Select Table", [t["name"] for t in st.session_state.registered_tables]
    )

    if table_name:
        # Initialize analytics components
        if "template_engine" not in st.session_state:
            from src.duckdb_analytics.analytics import (
                AnalyticsOptimizer,
                DataProfiler,
                TemplateEngine,
            )

            st.session_state.template_engine = TemplateEngine(
                st.session_state.query_engine, st.session_state.db_connection
            )
            st.session_state.data_profiler = DataProfiler(
                st.session_state.db_connection, st.session_state.query_engine
            )
            st.session_state.analytics_optimizer = AnalyticsOptimizer(
                st.session_state.db_connection
            )

        # Get table schema
        table_info = st.session_state.db_connection.get_table_info(table_name)
        columns = table_info["columns"]

        # Create tabs for different analytics sections
        template_tab, profiling_tab, filter_tab, quick_tab = st.tabs(
            [
                "📋 Analytics Templates",
                "📊 Data Profiling",
                "🔧 Filter Builder",
                "⚡ Quick Analytics",
            ]
        )

        with template_tab:
            render_analytics_templates(table_name, columns)

        with profiling_tab:
            render_data_profiling(table_name)

        with filter_tab:
            render_filter_builder(table_name, columns)

        with quick_tab:
            render_quick_analytics(table_name, columns)


def render_analytics_templates(table_name: str, columns: List[Dict[str, Any]]):
    """Render analytics templates interface."""
    st.subheader("📋 Analytics Templates")

    try:
        # Get available templates
        library = st.session_state.template_engine.library
        categories = library.get_categories()

        # Category filter
        col1, col2 = st.columns([1, 3])
        with col1:
            selected_category = st.selectbox(
                "Filter by Category",
                ["All"] + categories,
                key="template_category_filter",
            )

        # Get templates for selected category
        if selected_category == "All":
            templates = library.list_templates()
        else:
            templates = library.list_templates(selected_category)

        if not templates:
            st.info("No templates available for the selected category")
            return

        # Template selection
        template_names = [t.metadata.name for t in templates]
        selected_template_name = st.selectbox(
            "Select Analytics Template", template_names, key="selected_template"
        )

        if selected_template_name:
            selected_template = library.get_template(selected_template_name)

            # Display template info
            with st.expander(f"📄 About {selected_template.metadata.name}"):
                st.write(f"**Category:** {selected_template.metadata.category}")
                st.write(f"**Description:** {selected_template.metadata.description}")
                st.write(f"**Tags:** {', '.join(selected_template.metadata.tags)}")

                if selected_template.metadata.requires_numeric_columns:
                    st.info("ℹ️ This template requires numeric columns")
                if selected_template.metadata.requires_date_columns:
                    st.info("ℹ️ This template requires date columns")

            # Parameter configuration
            st.subheader("⚙️ Configure Parameters")

            parameters = {}
            for param in selected_template.metadata.parameters:
                param_value = render_template_parameter(param, columns, table_name)
                parameters[param.name] = param_value

            # Execute template button
            if st.button("🚀 Execute Template", type="primary"):
                try:
                    with st.spinner("Executing analytics template..."):
                        result = st.session_state.template_engine.execute_template(
                            selected_template_name, parameters, table_name
                        )

                    if result["success"]:
                        st.success(
                            f"✅ Template executed successfully ({result['row_count']:,} rows)"
                        )

                        # Store results in session state for other tabs
                        st.session_state.query_result = result["data"]
                        st.session_state.execution_time = (
                            0  # Template execution doesn't track time separately
                        )

                        # Display results
                        st.subheader("📊 Results")
                        st.dataframe(result["data"], use_container_width=True)

                        # Show generated query
                        with st.expander("📝 Generated SQL Query"):
                            st.code(result["query"], language="sql")

                        # Export options
                        col1, col2 = st.columns(2)
                        with col1:
                            csv_data = result["data"].to_csv(index=False)
                            st.download_button(
                                "📥 Download CSV",
                                csv_data,
                                f"{selected_template_name.replace(' ', '_').lower()}_results.csv",
                                "text/csv",
                            )
                        with col2:
                            parquet_data = result["data"].to_parquet(index=False)
                            st.download_button(
                                "📥 Download Parquet",
                                parquet_data,
                                f"{selected_template_name.replace(' ', '_').lower()}_results.parquet",
                                "application/octet-stream",
                            )
                    else:
                        st.error(f"❌ Template execution failed: {result['error']}")
                        with st.expander("📝 Generated SQL Query"):
                            st.code(result["query"], language="sql")

                except Exception as e:
                    st.error(f"❌ Error executing template: {str(e)}")

    except Exception as e:
        st.error(f"❌ Error loading templates: {str(e)}")


def render_template_parameter(param, columns: List[Dict[str, Any]], table_name: str):
    """Render parameter input widget based on parameter type."""
    from src.duckdb_analytics.analytics.templates import ColumnFilter, ParameterType

    column_names = [col["name"] for col in columns]

    if param.type == ParameterType.COLUMN:
        # Filter columns based on column filter
        available_columns = column_names
        if param.column_filter and param.column_filter != ColumnFilter.ALL:
            available_columns = []
            for col in columns:
                col_type = col.get("type", "").lower()
                if param.column_filter == ColumnFilter.NUMERIC:
                    if any(
                        t in col_type
                        for t in ["int", "float", "double", "decimal", "numeric"]
                    ):
                        available_columns.append(col["name"])
                elif param.column_filter == ColumnFilter.TEXT:
                    if any(
                        t in col_type for t in ["varchar", "text", "string", "char"]
                    ):
                        available_columns.append(col["name"])
                elif param.column_filter == ColumnFilter.DATE:
                    if any(t in col_type for t in ["date", "time", "timestamp"]):
                        available_columns.append(col["name"])
                elif param.column_filter == ColumnFilter.BOOLEAN:
                    if "bool" in col_type:
                        available_columns.append(col["name"])

        if not available_columns:
            st.warning(
                f"⚠️ No columns available for parameter '{param.label}' (requires {param.column_filter.value if param.column_filter else 'any'} type)"
            )
            return None

        default_idx = 0
        if param.default and param.default in available_columns:
            default_idx = available_columns.index(param.default)

        return st.selectbox(
            param.label,
            available_columns,
            index=default_idx,
            help=param.description,
            key=f"param_{param.name}_{table_name}",
        )

    elif param.type == ParameterType.SELECT:
        default_idx = 0
        if param.default and param.default in param.options:
            default_idx = param.options.index(param.default)

        return st.selectbox(
            param.label,
            param.options,
            index=default_idx,
            help=param.description,
            key=f"param_{param.name}_{table_name}",
        )

    elif param.type == ParameterType.NUMBER:
        return st.number_input(
            param.label,
            value=param.default or 0,
            min_value=param.min_value,
            max_value=param.max_value,
            help=param.description,
            key=f"param_{param.name}_{table_name}",
        )

    elif param.type == ParameterType.TEXT:
        return st.text_input(
            param.label,
            value=param.default or "",
            help=param.description,
            key=f"param_{param.name}_{table_name}",
        )

    elif param.type == ParameterType.BOOLEAN:
        return st.checkbox(
            param.label,
            value=param.default or False,
            help=param.description,
            key=f"param_{param.name}_{table_name}",
        )

    elif param.type == ParameterType.DATE:
        return st.date_input(
            param.label,
            value=param.default,
            help=param.description,
            key=f"param_{param.name}_{table_name}",
        )
    else:
        return st.text_input(
            param.label,
            value=param.default or "",
            help=param.description,
            key=f"param_{param.name}_{table_name}",
        )


def render_data_profiling(table_name: str):
    """Render data profiling interface."""
    st.subheader("📊 Data Profiling & Quality Analysis")

    try:
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            sample_size = st.number_input(
                "Sample Size for Analysis",
                min_value=100,
                max_value=100000,
                value=10000,
                step=1000,
                help="Number of rows to sample for profiling analysis",
            )

        with col2:
            if st.button("🔍 Generate Profile", type="primary"):
                with st.spinner("Analyzing data quality and generating profile..."):
                    try:
                        # Generate summary statistics
                        stats_result = st.session_state.data_profiler.stats_generator.generate_statistics(
                            table_name, sample_size
                        )
                        st.session_state[f"profile_stats_{table_name}"] = stats_result
                        st.success("✅ Profile generated successfully")
                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ Error generating profile: {str(e)}")

        with col3:
            if st.button("📋 Full Profile"):
                with st.spinner("Generating comprehensive data profile..."):
                    try:
                        profile = st.session_state.data_profiler.profile_table(
                            table_name, sample_size
                        )
                        st.session_state[f"full_profile_{table_name}"] = profile
                        st.success("✅ Full profile generated")
                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ Error generating full profile: {str(e)}")

        # Display profile results
        if f"profile_stats_{table_name}" in st.session_state:
            stats = st.session_state[f"profile_stats_{table_name}"]

            # Overall metrics
            st.subheader("📈 Overall Statistics")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Rows", f"{stats['total_rows']:,}")
            with col2:
                st.metric("Sampled Rows", f"{stats['sampled_rows']:,}")
            with col3:
                st.metric("Total Columns", stats["total_columns"])
            with col4:
                st.metric("Processing Time", f"{stats['processing_time']:.3f}s")

            # Column statistics
            st.subheader("📊 Column Analysis")

            # Create summary dataframe
            column_summary = []
            for col_name, col_stats in stats["column_statistics"].items():
                summary_row = {
                    "Column": col_name,
                    "Type": col_stats.get("type", "unknown"),
                    "Count": col_stats.get("count", 0),
                    "Unique": col_stats.get("unique", 0),
                    "Missing": col_stats.get("missing", 0),
                    "Completeness": f"{col_stats.get('completeness', 0)*100:.1f}%",
                    "Uniqueness": f"{col_stats.get('uniqueness', 0)*100:.1f}%",
                }

                # Add type-specific metrics
                if col_stats.get("type") == "numeric":
                    summary_row["Mean"] = (
                        f"{col_stats.get('mean', 0):.2f}"
                        if col_stats.get("mean")
                        else ""
                    )
                    summary_row["Std Dev"] = (
                        f"{col_stats.get('std_dev', 0):.2f}"
                        if col_stats.get("std_dev")
                        else ""
                    )
                elif col_stats.get("type") == "text":
                    summary_row["Avg Length"] = (
                        f"{col_stats.get('avg_length', 0):.1f}"
                        if col_stats.get("avg_length")
                        else ""
                    )
                elif col_stats.get("type") == "boolean":
                    summary_row["True Ratio"] = (
                        f"{col_stats.get('true_ratio', 0)*100:.1f}%"
                        if col_stats.get("true_ratio")
                        else ""
                    )

                column_summary.append(summary_row)

            if column_summary:
                import pandas as pd

                summary_df = pd.DataFrame(column_summary)
                st.dataframe(summary_df, use_container_width=True)

                # Detailed column analysis
                selected_column = st.selectbox(
                    "Select column for detailed analysis",
                    list(stats["column_statistics"].keys()),
                )

                if selected_column:
                    col_stats = stats["column_statistics"][selected_column]

                    with st.expander(f"📋 Detailed Analysis: {selected_column}"):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.write("**Basic Statistics:**")
                            for key, value in col_stats.items():
                                if key not in ["type", "sql_type"]:
                                    if isinstance(value, float):
                                        st.write(f"- {key.title()}: {value:.4f}")
                                    else:
                                        st.write(f"- {key.title()}: {value}")

                        with col2:
                            st.write("**Data Quality:**")
                            st.write(
                                f"- Completeness: {col_stats.get('completeness', 0)*100:.1f}%"
                            )
                            st.write(
                                f"- Uniqueness: {col_stats.get('uniqueness', 0)*100:.1f}%"
                            )

                            if col_stats.get("outlier_count"):
                                st.write(
                                    f"- Outliers: {col_stats['outlier_count']} ({col_stats['outlier_count']/col_stats.get('count', 1)*100:.1f}%)"
                                )

        # Display full profile if available
        if f"full_profile_{table_name}" in st.session_state:
            profile = st.session_state[f"full_profile_{table_name}"]

            st.subheader("🔍 Comprehensive Profile Analysis")

            # Overall quality score
            overall_quality = profile.overall_quality

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(
                    "Overall Quality", f"{overall_quality['total_score']*100:.1f}%"
                )
            with col2:
                st.metric("Completeness", f"{overall_quality['completeness']*100:.1f}%")
            with col3:
                st.metric("Uniqueness", f"{overall_quality['uniqueness']*100:.1f}%")
            with col4:
                st.metric("Validity", f"{overall_quality['validity']*100:.1f}%")

            # Relationships
            if profile.relationships:
                st.subheader("🔗 Column Relationships")
                for relationship in profile.relationships:
                    if relationship["type"] == "correlation":
                        st.write(
                            f"📊 **{relationship['column1']}** and **{relationship['column2']}** have a "
                            f"{relationship['direction']} correlation (r = {relationship['value']:.3f})"
                        )

    except Exception as e:
        st.error(f"❌ Error in data profiling interface: {str(e)}")


def render_filter_builder(table_name: str, columns: List[Dict[str, Any]]):
    """Render interactive filter builder interface."""
    st.subheader("🔧 Interactive Filter & Query Builder")

    try:
        from src.duckdb_analytics.analytics import FilterBuilder

        # Initialize filter builder
        filter_builder = FilterBuilder(st.session_state.db_connection, columns)

        # Render the filter builder interface
        query_result = filter_builder.render(table_name)

        # Handle query execution results
        if query_result and query_result.get("success"):
            # Results already displayed by filter builder
            pass

    except Exception as e:
        st.error(f"❌ Error in filter builder: {str(e)}")


def render_quick_analytics(table_name: str, columns: List[Dict[str, Any]]):
    """Render quick analytics interface (original functionality)."""
    st.subheader("⚡ Quick Analytics")

    column_names = [col["name"] for col in columns]

    # Analysis options
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
        group_by_cols = st.multiselect("GROUP BY", column_names)

    with col2:
        agg_col = st.selectbox("Aggregate Column", column_names)

    with col3:
        agg_func = st.selectbox(
            "Function", ["COUNT", "SUM", "AVG", "MIN", "MAX", "STDDEV"]
        )

    if st.button("🚀 Run Aggregation"):
        run_aggregation(table_name, group_by_cols, agg_col, agg_func)


def visualizations_tab():
    """Enhanced data visualization interface with advanced chart types and smart recommendations."""
    st.header("Enhanced Data Visualizations")

    if "query_result" not in st.session_state or st.session_state.query_result is None:
        st.info("📊 Execute a query to visualize results")
        return

    # Defensive check for query_result
    try:
        df = st.session_state.query_result
        if df is None or (hasattr(df, "empty") and df.empty):
            st.warning("⚠️ No data available for visualization")
            return
    except Exception as e:
        logger.error(
            f"Error accessing query_result in visualizations: {str(e)}", exc_info=True
        )
        st.error(f"❌ Error loading data for visualization: {str(e)}")
        return

    # Initialize visualization components
    if "chart_recommendation_engine" not in st.session_state:
        from src.duckdb_analytics.visualizations import (
            ChartExportManager,
            ChartRecommendationEngine,
            DashboardLayoutManager,
        )
        from src.duckdb_analytics.visualizations.configuration_panel import (
            ChartConfigurationPanel,
        )

        st.session_state.chart_recommendation_engine = ChartRecommendationEngine()
        st.session_state.chart_export_manager = ChartExportManager()
        st.session_state.dashboard_manager = DashboardLayoutManager()
        st.session_state.config_panel = ChartConfigurationPanel()

    # Create tabs for different visualization features
    chart_tab, recommendations_tab, dashboard_tab, export_tab = st.tabs(
        [
            "📊 Create Charts",
            "🤖 Smart Recommendations",
            "🏗️ Dashboard Builder",
            "📤 Export & Share",
        ]
    )

    with chart_tab:
        render_chart_creation(df)

    with recommendations_tab:
        render_smart_recommendations(df)

    with dashboard_tab:
        render_dashboard_builder(df)

    with export_tab:
        render_export_options()


def render_chart_creation(df: pd.DataFrame):
    """Render the enhanced chart creation interface."""
    from src.duckdb_analytics.visualizations import (
        create_box_plot,
        create_gauge_chart,
        create_heatmap,
        create_radar_chart,
        create_sankey,
        create_scatter_matrix,
        create_treemap,
        create_waterfall_chart,
    )
    from src.duckdb_analytics.visualizations.chart_types import ChartType

    # Chart type selection with enhanced options
    chart_types = {
        "Heatmap": ChartType.HEATMAP,
        "Treemap": ChartType.TREEMAP,
        "Sankey Diagram": ChartType.SANKEY,
        "Box Plot": ChartType.BOX_PLOT,
        "Scatter Matrix": ChartType.SCATTER_MATRIX,
        "Gauge Chart": ChartType.GAUGE,
        "Waterfall Chart": ChartType.WATERFALL,
        "Radar Chart": ChartType.RADAR,
        # Legacy chart types
        "Line Chart": "line",
        "Bar Chart": "bar",
        "Scatter Plot": "scatter",
        "Histogram": "histogram",
    }

    col1, col2 = st.columns([2, 1])

    with col1:
        selected_chart = st.selectbox(
            "Select Chart Type",
            list(chart_types.keys()),
            help="Choose from advanced chart types or classic visualizations",
        )

    with col2:
        if st.button(
            "🤖 Get Recommendations", help="Get AI-powered chart recommendations"
        ):
            st.session_state.show_recommendations = True

    chart_type = chart_types[selected_chart]

    # Get column information
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    all_cols = df.columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    # Chart-specific parameter selection
    chart_config = {}

    if chart_type == ChartType.HEATMAP:
        col1, col2, col3 = st.columns(3)
        with col1:
            x_col = st.selectbox("X-axis", all_cols, key="heatmap_x")
        with col2:
            y_col = st.selectbox("Y-axis", all_cols, key="heatmap_y")
        with col3:
            values_col = st.selectbox("Values", numeric_cols, key="heatmap_values")

        if x_col and y_col and values_col:
            chart_config = st.session_state.config_panel.render(chart_type, df)
            fig = create_heatmap(df, x_col, y_col, values_col, chart_config)
            st.session_state.config_panel.apply_config(fig, chart_config)
            st.plotly_chart(fig, use_container_width=True, key="heatmap_chart")

    elif chart_type == ChartType.TREEMAP:
        col1, col2, col3 = st.columns(3)
        with col1:
            labels_col = st.selectbox("Labels", categorical_cols, key="treemap_labels")
        with col2:
            values_col = st.selectbox("Values", numeric_cols, key="treemap_values")
        with col3:
            parents_col = st.selectbox(
                "Parent Categories (optional)",
                [None] + categorical_cols,
                key="treemap_parents",
            )

        if labels_col and values_col:
            chart_config = st.session_state.config_panel.render(chart_type, df)
            fig = create_treemap(df, labels_col, values_col, parents_col, chart_config)
            st.session_state.config_panel.apply_config(fig, chart_config)
            st.plotly_chart(fig, use_container_width=True, key="treemap_chart")

    elif chart_type == ChartType.SANKEY:
        col1, col2, col3 = st.columns(3)
        with col1:
            source_col = st.selectbox("Source", categorical_cols, key="sankey_source")
        with col2:
            target_col = st.selectbox("Target", categorical_cols, key="sankey_target")
        with col3:
            value_col = st.selectbox("Flow Values", numeric_cols, key="sankey_values")

        if source_col and target_col and value_col:
            chart_config = st.session_state.config_panel.render(chart_type, df)
            fig = create_sankey(df, source_col, target_col, value_col, chart_config)
            st.session_state.config_panel.apply_config(fig, chart_config)
            st.plotly_chart(fig, use_container_width=True, key="sankey_chart")

    elif chart_type == ChartType.BOX_PLOT:
        col1, col2 = st.columns(2)
        with col1:
            y_col = st.selectbox("Values", numeric_cols, key="box_y")
        with col2:
            x_col = st.selectbox(
                "Categories (optional)", [None] + categorical_cols, key="box_x"
            )

        if y_col:
            chart_config = st.session_state.config_panel.render(chart_type, df)
            fig = create_box_plot(df, x_col, y_col, chart_config)
            st.session_state.config_panel.apply_config(fig, chart_config)
            st.plotly_chart(fig, use_container_width=True, key="box_chart")

    elif chart_type == ChartType.SCATTER_MATRIX:
        dimensions = st.multiselect(
            "Select Dimensions",
            numeric_cols,
            default=numeric_cols[:4],
            key="scatter_matrix_dims",
        )
        color_by = st.selectbox(
            "Color By (optional)", [None] + categorical_cols, key="scatter_matrix_color"
        )

        if len(dimensions) >= 2:
            chart_config = st.session_state.config_panel.render(chart_type, df)
            fig = create_scatter_matrix(df, dimensions, color_by, chart_config)
            st.session_state.config_panel.apply_config(fig, chart_config)
            st.plotly_chart(fig, use_container_width=True, key="scatter_matrix_chart")

    elif chart_type == ChartType.GAUGE:
        col1, col2 = st.columns(2)
        with col1:
            value_col = st.selectbox("KPI Value", numeric_cols, key="gauge_value")
        with col2:
            title = st.text_input("Gauge Title", value="KPI Gauge", key="gauge_title")

        if value_col:
            # Use first row value or aggregate if multiple rows
            if len(df) == 1:
                value = float(df[value_col].iloc[0])
            else:
                value = float(df[value_col].mean())

            chart_config = st.session_state.config_panel.render(chart_type, df)
            fig = create_gauge_chart(value, title, chart_config)
            st.plotly_chart(fig, use_container_width=True, key="gauge_chart")

    elif chart_type == ChartType.WATERFALL:
        col1, col2 = st.columns(2)
        with col1:
            x_col = st.selectbox("Categories", all_cols, key="waterfall_x")
        with col2:
            y_col = st.selectbox("Values", numeric_cols, key="waterfall_y")

        if x_col and y_col:
            chart_config = st.session_state.config_panel.render(chart_type, df)
            fig = create_waterfall_chart(df, x_col, y_col, chart_config)
            st.session_state.config_panel.apply_config(fig, chart_config)
            st.plotly_chart(fig, use_container_width=True, key="waterfall_chart")

    elif chart_type == ChartType.RADAR:
        col1, col2, col3 = st.columns(3)
        with col1:
            categories = st.multiselect("Categories", all_cols, key="radar_categories")
        with col2:
            values_col = st.selectbox("Values", numeric_cols, key="radar_values")
        with col3:
            group_by = st.selectbox(
                "Group By (optional)", [None] + categorical_cols, key="radar_group"
            )

        if categories and values_col:
            chart_config = st.session_state.config_panel.render(chart_type, df)
            fig = create_radar_chart(df, categories, values_col, group_by, chart_config)
            st.session_state.config_panel.apply_config(fig, chart_config)
            st.plotly_chart(fig, use_container_width=True, key="radar_chart")

    # Legacy chart types
    elif chart_type == "line":
        col1, col2 = st.columns(2)
        with col1:
            x_col = st.selectbox("X-axis", all_cols, key="line_x")
        with col2:
            y_cols = st.multiselect("Y-axis", numeric_cols, key="line_y")

        if x_col and y_cols:
            fig = px.line(df, x=x_col, y=y_cols, title="Line Chart")
            st.plotly_chart(fig, use_container_width=True)

    elif chart_type == "bar":
        col1, col2 = st.columns(2)
        with col1:
            x_col = st.selectbox("X-axis", all_cols, key="bar_x")
        with col2:
            y_col = st.selectbox("Y-axis", numeric_cols, key="bar_y")

        if x_col and y_col:
            fig = px.bar(df, x=x_col, y=y_col, title="Bar Chart")
            st.plotly_chart(fig, use_container_width=True)

    elif chart_type == "scatter":
        col1, col2, col3 = st.columns(3)
        with col1:
            x_col = st.selectbox("X-axis", numeric_cols, key="scatter_x")
        with col2:
            y_col = st.selectbox("Y-axis", numeric_cols, key="scatter_y")
        with col3:
            color_col = st.selectbox("Color", [None] + all_cols, key="scatter_color")

        if x_col and y_col:
            fig = px.scatter(
                df, x=x_col, y=y_col, color=color_col, title="Scatter Plot"
            )
            st.plotly_chart(fig, use_container_width=True)

    elif chart_type == "histogram":
        col1, col2 = st.columns(2)
        with col1:
            col = st.selectbox("Column", numeric_cols, key="hist_col")
        with col2:
            bins = st.slider("Number of Bins", 10, 100, 30, key="hist_bins")

        if col:
            fig = px.histogram(df, x=col, nbins=bins, title=f"Histogram of {col}")
            st.plotly_chart(fig, use_container_width=True)


def render_smart_recommendations(df: pd.DataFrame):
    """Render AI-powered chart recommendations."""
    st.subheader("🤖 Smart Chart Recommendations")

    if st.button("🔍 Analyze Data & Generate Recommendations", type="primary"):
        with st.spinner("Analyzing data patterns and generating recommendations..."):
            try:
                recommendations = (
                    st.session_state.chart_recommendation_engine.recommend_charts(df)
                )
                st.session_state.chart_recommendations = recommendations
            except Exception as e:
                st.error(f"Error generating recommendations: {e}")
                return

    if "chart_recommendations" in st.session_state:
        recommendations = st.session_state.chart_recommendations

        if recommendations:
            st.success(f"Generated {len(recommendations)} chart recommendations")

            for i, rec in enumerate(recommendations):
                with st.expander(
                    f"📊 Recommendation {i+1}: {rec.chart_type.value.title().replace('_', ' ')} (Score: {rec.score:.2f})"
                ):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.write(f"**Reason:** {rec.reason}")
                        st.write(f"**Columns Used:** {', '.join(rec.columns_used)}")
                        st.write(f"**Confidence Score:** {rec.score:.2f}")

                    with col2:
                        if st.button("Create This Chart", key=f"create_rec_{i}"):
                            # Create the recommended chart
                            st.session_state.selected_recommendation = rec
                            st.success(
                                "Chart configuration applied! Switch to 'Create Charts' tab to customize."
                            )
        else:
            st.info("No suitable chart recommendations found for this dataset.")


def render_dashboard_builder(df: pd.DataFrame):
    """Render dashboard builder interface."""
    st.subheader("🏗️ Dashboard Builder")

    # Dashboard layout builder
    layout_id = st.session_state.dashboard_manager.render_layout_builder()

    if layout_id:
        st.success(f"Dashboard layout created: {layout_id}")


def render_export_options():
    """Render chart export and sharing options."""
    st.subheader("📤 Export & Share Charts")

    # Check if there are any charts to export
    if not hasattr(st.session_state, "current_chart"):
        st.info("Create a chart first to enable export options")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Export Format**")
        export_format = st.selectbox(
            "Format", ["PNG", "SVG", "HTML", "JSON", "PDF"], key="export_format"
        )

    with col2:
        st.write("**Export Settings**")
        options = st.session_state.chart_export_manager.get_export_options(
            export_format.lower()
        )

        export_settings = {}
        for option_name, option_config in options.items():
            if option_config["type"] == "number":
                export_settings[option_name] = st.number_input(
                    option_name.title(),
                    value=option_config["default"],
                    min_value=option_config.get("min", 0),
                    max_value=option_config.get("max", 10000),
                )
            elif option_config["type"] == "boolean":
                export_settings[option_name] = st.checkbox(
                    option_name.title(), value=option_config["default"]
                )

    if st.button("📥 Export Chart", type="primary"):
        try:
            exported_data = st.session_state.chart_export_manager.export_chart(
                st.session_state.current_chart, export_format.lower(), export_settings
            )

            mime_type = st.session_state.chart_export_manager.get_mime_type(
                export_format.lower()
            )

            st.download_button(
                f"Download {export_format} File",
                data=exported_data,
                file_name=f"chart.{export_format.lower()}",
                mime=mime_type,
            )

            st.success("Chart exported successfully!")

        except Exception as e:
            st.error(f"Export failed: {e}")


def data_explorer_tab():
    """Enhanced interactive data exploration interface with advanced features."""
    st.header("🔍 Enhanced Data Explorer")

    if not st.session_state.registered_tables:
        st.info("📤 Please upload data files to explore")
        return

    # Table selection with metadata
    col1, col2 = st.columns([3, 1])

    with col1:
        table_name = st.selectbox(
            "Select Table to Explore",
            [t["name"] for t in st.session_state.registered_tables],
            format_func=lambda x: f"{x} ({next(t['rows'] for t in st.session_state.registered_tables if t['name'] == x):,} rows)",
        )

    with col2:
        if st.button("🔄 Refresh Data"):
            # Clear any cached data for this table
            cache_keys_to_clear = [
                key for key in st.session_state.keys() if table_name in str(key)
            ]
            for key in cache_keys_to_clear:
                if key.startswith(("pagination_", "column_stats_", "filter_")):
                    del st.session_state[key]
            st.rerun()

    if not table_name:
        return

    # Load data with error handling
    try:
        query = f"SELECT * FROM {table_name}"
        df = st.session_state.query_engine.execute_query(query)

        if df.empty:
            st.warning("⚠️ Selected table contains no data")
            return

    except Exception as e:
        st.error(f"❌ Error loading table data: {str(e)}")
        return

    # Initialize enhanced components
    try:
        from src.duckdb_analytics.ui.advanced_filters import AdvancedFilterBuilder
        from src.duckdb_analytics.ui.column_search import ColumnSearchManager
        from src.duckdb_analytics.ui.column_statistics import ColumnStatisticsManager
        from src.duckdb_analytics.ui.data_export import DataExporter
        from src.duckdb_analytics.ui.relationship_visualizer import (
            RelationshipVisualizer,
        )
        from src.duckdb_analytics.ui.smart_pagination import (
            PaginationPresets,
            SmartPagination,
        )

        # Initialize components
        if "advanced_filter_builder" not in st.session_state:
            st.session_state.advanced_filter_builder = AdvancedFilterBuilder()
        if "column_search_manager" not in st.session_state:
            st.session_state.column_search_manager = ColumnSearchManager()
        if "data_exporter" not in st.session_state:
            st.session_state.data_exporter = DataExporter()
        if "relationship_visualizer" not in st.session_state:
            st.session_state.relationship_visualizer = RelationshipVisualizer(
                st.session_state.db_connection, st.session_state.registered_tables
            )
        if "smart_pagination" not in st.session_state:
            st.session_state.smart_pagination = SmartPagination()
        if "column_statistics" not in st.session_state:
            st.session_state.column_statistics = ColumnStatisticsManager(
                st.session_state.db_connection
            )

    except ImportError as e:
        st.error(f"❌ Error importing enhanced components: {str(e)}")
        st.info("🔄 Using basic data explorer interface")
        # Fall back to basic interface
        _render_basic_data_explorer(df, table_name)
        return

    # Create tabs for different exploration features
    filter_tab, search_tab, stats_tab, pagination_tab, export_tab, relationships_tab = (
        st.tabs(
            [
                "🔧 Advanced Filters",
                "🔍 Column Search",
                "📊 Statistics",
                "📄 Pagination",
                "📥 Export Data",
                "🔗 Relationships",
            ]
        )
    )

    # Apply filters and searches first
    working_df = df.copy()

    with filter_tab:
        st.subheader("🔧 Advanced Filtering System")
        filter_config = st.session_state.advanced_filter_builder.render_filter_builder(
            df
        )

        if filter_config["filters"]:
            try:
                working_df = st.session_state.advanced_filter_builder.apply_filters(
                    working_df, filter_config
                )
                st.success(
                    f"✅ Filters applied: {len(working_df):,} rows remaining from {len(df):,} original rows"
                )
            except Exception as e:
                st.error(f"❌ Error applying filters: {str(e)}")

    with search_tab:
        st.subheader("🔍 Column-Level Search")
        search_config = st.session_state.column_search_manager.render_column_searches(
            working_df
        )

        if search_config["searches"]:
            try:
                working_df = (
                    st.session_state.column_search_manager.apply_column_searches(
                        working_df, search_config
                    )
                )
                st.success(
                    f"✅ Search applied: {len(working_df):,} rows match search criteria"
                )
            except Exception as e:
                st.error(f"❌ Error applying search: {str(e)}")

    with stats_tab:
        st.subheader("📊 Column Statistics & Data Quality")
        try:
            stats_result = (
                st.session_state.column_statistics.render_column_statistics_interface(
                    working_df, f"{table_name}_filtered"
                )
            )
        except Exception as e:
            st.error(f"❌ Error generating statistics: {str(e)}")

    with pagination_tab:
        st.subheader("📄 Smart Pagination")

        # Show pagination presets
        preset_config = PaginationPresets.render_preset_selector(len(working_df))

        if st.button("Apply Preset Configuration"):
            # Apply preset to session state
            st.session_state.pagination_settings.update(preset_config)
            st.success("✅ Pagination preset applied")
            st.rerun()

        try:
            pagination_result = (
                st.session_state.smart_pagination.render_pagination_interface(
                    working_df, f"{table_name}_paginated"
                )
            )

            # Display paginated data
            if not pagination_result["data"].empty:
                st.subheader("📋 Data View")
                st.dataframe(pagination_result["data"], use_container_width=True)

        except Exception as e:
            st.error(f"❌ Error in pagination: {str(e)}")
            # Fallback to simple display
            st.dataframe(working_df.head(100), use_container_width=True)

    with export_tab:
        st.subheader("📥 Export Data")
        try:
            st.session_state.data_exporter.render_export_interface(
                working_df, f"{table_name} Filtered Data"
            )
        except Exception as e:
            st.error(f"❌ Error in data export: {str(e)}")
            # Fallback export
            csv = working_df.to_csv(index=False)
            st.download_button(
                "📥 Download CSV (Basic)", csv, f"{table_name}_filtered.csv", "text/csv"
            )

    with relationships_tab:
        st.subheader("🔗 Table Relationships")
        try:
            relationship_result = (
                st.session_state.relationship_visualizer.render_relationship_interface()
            )
        except Exception as e:
            st.error(f"❌ Error in relationship analysis: {str(e)}")
            st.info("Relationship analysis requires multiple tables")

    # Summary information
    st.divider()
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Original Rows", f"{len(df):,}")

    with col2:
        st.metric("Filtered Rows", f"{len(working_df):,}")

    with col3:
        reduction_pct = (1 - len(working_df) / len(df)) * 100 if len(df) > 0 else 0
        st.metric("Reduction", f"{reduction_pct:.1f}%")

    with col4:
        st.metric("Columns", len(df.columns))


def _render_basic_data_explorer(df: pd.DataFrame, table_name: str):
    """Fallback basic data explorer interface."""
    st.subheader("🔍 Basic Filters")

    filters = {}
    columns = df.columns.tolist()

    # Dynamic filter creation
    for col in columns:
        col_type = df[col].dtype

        if col_type in ["int64", "float64"]:
            col1, col2 = st.columns(2)
            with col1:
                min_val = st.number_input(f"{col} (min)", value=float(df[col].min()))
            with col2:
                max_val = st.number_input(f"{col} (max)", value=float(df[col].max()))
            filters[col] = (min_val, max_val)

        elif col_type == "object":
            unique_vals = df[col].unique().tolist()
            if len(unique_vals) <= 20:
                selected = st.multiselect(f"{col}", unique_vals, default=unique_vals)
                filters[col] = selected

    # Apply filters
    filtered_df = df.copy()
    for col, filter_val in filters.items():
        if isinstance(filter_val, tuple):
            filtered_df = filtered_df[
                (filtered_df[col] >= filter_val[0])
                & (filtered_df[col] <= filter_val[1])
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
            "📥 Download Filtered Data", csv, f"{table_name}_filtered.csv", "text/csv"
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
FROM table_name""",
    }
    return templates.get(template, "")


def execute_query(query: str, use_streaming: bool = True):
    """Execute SQL query with optional streaming and store results."""
    try:
        import time

        # Validate and clean the query
        if not query or not query.strip():
            st.error("❌ Query is empty")
            return

        # Clean up the query - remove any extra whitespace
        query = query.strip()

        # Log the query for debugging
        logger.info(f"Executing query: {query}")

        # Estimate query time for progress indication
        estimated_time = st.session_state.optimized_executor.estimate_query_time(query)

        # Use streaming for large results or long queries
        if use_streaming and estimated_time > 2.0:
            # Show progress indicators for long queries
            progress_container = st.container()
            with progress_container:
                st.info(f"⏱️ Estimated execution time: {estimated_time:.1f}s")

                # Create streaming display
                streamer = StreamingQueryDisplay()

                # Define cancel callback
                def cancel_callback():
                    st.session_state.optimized_executor.cancel_query()

                # Stream results with progress
                start_time = time.time()
                chunks = st.session_state.optimized_executor.execute_streaming(
                    query,
                    chunk_size=1000,
                    use_cache=True,
                    progress_callback=lambda info: None,  # Progress handled by streamer
                )

                # Stream and display results
                df = streamer.stream_dataframe(chunks, max_display_rows=10000)
                execution_time = time.time() - start_time

                st.session_state.query_result = df
                st.session_state.execution_time = execution_time

                # Show completion message
                if not streamer.state.is_cancelled:
                    st.success(
                        f"✅ Query completed in {execution_time:.3f}s ({len(df):,} rows)"
                    )
        else:
            # Regular execution for small/fast queries
            start_time = time.time()
            df = st.session_state.optimized_executor.execute_query(query)
            execution_time = time.time() - start_time

            st.session_state.query_result = df
            st.session_state.execution_time = execution_time

            st.success(f"✅ Query executed successfully in {execution_time:.3f}s")
    except Exception as e:
        # Enhanced error handling with more details
        error_msg = str(e)
        logger.error(f"Query execution failed: {error_msg}")
        logger.error(f"Failed query: {query}")

        st.error("❌ Query failed:")
        st.error(error_msg)

        # Provide helpful suggestions based on error type
        if "Catalog Error" in error_msg or "does not exist" in error_msg:
            st.info("💡 Suggestions:")
            st.info("• Check table names (case-sensitive)")
            st.info("• Verify column names exist")
            st.info("• Use the schema explorer to see available tables")
        elif "Parser Error" in error_msg or "syntax" in error_msg.lower():
            st.info("💡 Suggestions:")
            st.info("• Check SQL syntax")
            st.info("• Remove any invalid characters")
            st.info("• Ensure quotes are properly closed")
        else:
            st.info("💡 Unknown error occurred")
            st.info("Suggestions:")
            st.info("• Check query syntax")
            st.info("• Verify table and column names")


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

    missing_df = pd.DataFrame(
        {
            "Column": missing.index,
            "Missing Count": missing.values,
            "Missing %": missing_pct.values,
        }
    )

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
            ", ".join(group_by_cols)
            + f", {agg_func}({agg_col}) as {agg_func.lower()}_{agg_col}"
        )
        query = f"SELECT {select_str} FROM {table_name} GROUP BY {group_by_str}"

    execute_query(query)


if __name__ == "__main__":
    main()
