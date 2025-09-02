"""Table relationship visualizer with ERD-style diagrams."""

import math
import re
from typing import Any, Dict, List, Optional

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


class RelationshipVisualizer:
    """Table relationship visualizer with interactive diagrams."""

    def __init__(self, db_connection, registered_tables: List[Dict]):
        """Initialize relationship visualizer."""
        self.db_connection = db_connection
        self.registered_tables = registered_tables
        self.relationships = []
        self.foreign_keys = []

        # Initialize session state
        if "detected_relationships" not in st.session_state:
            st.session_state.detected_relationships = []
        if "manual_relationships" not in st.session_state:
            st.session_state.manual_relationships = []
        if "relationship_validation_results" not in st.session_state:
            st.session_state.relationship_validation_results = {}

    def render_relationship_interface(self) -> Dict[str, Any]:
        """
        Render the relationship visualization interface.

        Returns:
            Dictionary containing relationship analysis results
        """
        st.subheader("🔗 Table Relationship Visualizer")

        if not self.registered_tables:
            st.info("📤 Please load data tables to analyze relationships")
            return {}

        # Create tabs for different functionality
        detection_tab, visualization_tab, validation_tab, manual_tab = st.tabs(
            [
                "🔍 Detect Relationships",
                "📊 Visualize Schema",
                "✅ Validate Relations",
                "✏️ Manual Relations",
            ]
        )

        with detection_tab:
            self._render_relationship_detection()

        with visualization_tab:
            self._render_schema_visualization()

        with validation_tab:
            self._render_relationship_validation()

        with manual_tab:
            self._render_manual_relationships()

        return {
            "detected_relationships": st.session_state.detected_relationships,
            "manual_relationships": st.session_state.manual_relationships,
            "validation_results": st.session_state.relationship_validation_results,
        }

    def _render_relationship_detection(self):
        """Render relationship detection interface."""
        st.subheader("🔍 Automatic Relationship Detection")

        col1, col2, col3 = st.columns(3)

        with col1:
            detection_method = st.selectbox(
                "Detection Method",
                ["Name Pattern Matching", "Data Analysis", "Combined Analysis"],
                help="Choose how to detect relationships between tables",
            )

        with col2:
            confidence_threshold = st.slider(
                "Confidence Threshold",
                min_value=0.1,
                max_value=1.0,
                value=0.7,
                step=0.1,
                help="Minimum confidence level for relationship suggestions",
            )

        with col3:
            if st.button("🔍 Detect Relationships", type="primary"):
                with st.spinner("Analyzing table relationships..."):
                    self._detect_relationships(detection_method, confidence_threshold)
                    st.rerun()

        # Display detected relationships
        if st.session_state.detected_relationships:
            st.subheader("📋 Detected Relationships")

            for i, rel in enumerate(st.session_state.detected_relationships):
                with st.expander(
                    f"{rel['source_table']}.{rel['source_column']} → {rel['target_table']}.{rel['target_column']} "
                    f"(Confidence: {rel['confidence']:.2f})",
                    expanded=False,
                ):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.write(f"**Detection Method:** {rel['detection_method']}")
                        st.write(f"**Relationship Type:** {rel['relationship_type']}")

                    with col2:
                        st.write(f"**Confidence Score:** {rel['confidence']:.3f}")
                        st.write(
                            f"**Sample Match Rate:** {rel.get('match_rate', 'N/A')}"
                        )

                    with col3:
                        if st.button("✅ Accept", key=f"accept_{i}"):
                            self._accept_relationship(i)
                            st.rerun()

                        if st.button("❌ Reject", key=f"reject_{i}"):
                            self._reject_relationship(i)
                            st.rerun()

                    # Show evidence
                    if rel.get("evidence"):
                        st.write("**Evidence:**")
                        for evidence_item in rel["evidence"]:
                            st.write(f"- {evidence_item}")
        else:
            st.info(
                "No relationships detected. Try adjusting the detection method or confidence threshold."
            )

    def _render_schema_visualization(self):
        """Render schema visualization interface."""
        st.subheader("📊 Schema Diagram")

        col1, col2, col3 = st.columns(3)

        with col1:
            layout_algorithm = st.selectbox(
                "Layout Algorithm",
                ["Spring", "Circular", "Shell", "Kamada-Kawai"],
                help="Choose the graph layout algorithm",
            )

        with col2:
            show_columns = st.checkbox("Show Column Details", value=True)

        with col3:
            highlight_relationships = st.checkbox("Highlight Relationships", value=True)

        # Generate and display the diagram
        if st.button("🎨 Generate Diagram", type="primary"):
            with st.spinner("Generating schema diagram..."):
                diagram_fig = self._generate_schema_diagram(
                    layout_algorithm, show_columns, highlight_relationships
                )

                if diagram_fig:
                    st.plotly_chart(diagram_fig, use_container_width=True)

                    # Export options
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("💾 Save as PNG"):
                            self._export_diagram(diagram_fig, "png")
                    with col2:
                        if st.button("💾 Save as SVG"):
                            self._export_diagram(diagram_fig, "svg")
                    with col3:
                        if st.button("💾 Save as HTML"):
                            self._export_diagram(diagram_fig, "html")
                else:
                    st.warning(
                        "Unable to generate diagram. Please ensure tables are loaded."
                    )

        # Table statistics
        self._render_table_statistics()

    def _render_relationship_validation(self):
        """Render relationship validation interface."""
        st.subheader("✅ Relationship Validation")

        all_relationships = (
            st.session_state.detected_relationships
            + st.session_state.manual_relationships
        )

        if not all_relationships:
            st.info(
                "No relationships to validate. Please detect or add relationships first."
            )
            return

        # Validation options
        col1, col2 = st.columns(2)

        with col1:
            validation_method = st.selectbox(
                "Validation Method",
                [
                    "Data Integrity Check",
                    "Referential Integrity",
                    "Statistical Analysis",
                ],
                help="Choose validation approach",
            )

        with col2:
            sample_size = st.number_input(
                "Sample Size for Validation",
                min_value=100,
                max_value=10000,
                value=1000,
                step=100,
            )

        if st.button("🔍 Validate Relationships", type="primary"):
            with st.spinner("Validating relationships..."):
                self._validate_relationships(validation_method, sample_size)
                st.rerun()

        # Display validation results
        if st.session_state.relationship_validation_results:
            st.subheader("📋 Validation Results")

            for (
                rel_key,
                result,
            ) in st.session_state.relationship_validation_results.items():
                status_emoji = "✅" if result["valid"] else "❌"

                with st.expander(f"{status_emoji} {rel_key}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(
                            f"**Status:** {'Valid' if result['valid'] else 'Invalid'}"
                        )
                        st.write(
                            f"**Integrity Score:** {result['integrity_score']:.3f}"
                        )

                    with col2:
                        st.write(f"**Match Rate:** {result['match_rate']:.1%}")
                        st.write(f"**Null Rate:** {result['null_rate']:.1%}")

                    if result["issues"]:
                        st.write("**Issues Found:**")
                        for issue in result["issues"]:
                            st.write(f"- {issue}")

                    if result["recommendations"]:
                        st.write("**Recommendations:**")
                        for rec in result["recommendations"]:
                            st.write(f"- {rec}")

    def _render_manual_relationships(self):
        """Render manual relationship creation interface."""
        st.subheader("✏️ Manual Relationship Definition")

        table_names = [table["name"] for table in self.registered_tables]

        # Add new relationship form
        with st.form("add_relationship"):
            col1, col2 = st.columns(2)

            with col1:
                st.write("**Source Table**")
                source_table = st.selectbox(
                    "Source Table", table_names, key="source_table"
                )

                if source_table:
                    source_columns = self._get_table_columns(source_table)
                    source_column = st.selectbox(
                        "Source Column", source_columns, key="source_column"
                    )

            with col2:
                st.write("**Target Table**")
                target_table = st.selectbox(
                    "Target Table", table_names, key="target_table"
                )

                if target_table:
                    target_columns = self._get_table_columns(target_table)
                    target_column = st.selectbox(
                        "Target Column", target_columns, key="target_column"
                    )

            # Relationship properties
            col1, col2, col3 = st.columns(3)

            with col1:
                relationship_type = st.selectbox(
                    "Relationship Type",
                    ["One-to-Many", "Many-to-One", "One-to-One", "Many-to-Many"],
                )

            with col2:
                cardinality = st.selectbox("Cardinality", ["1:N", "N:1", "1:1", "N:M"])

            with col3:
                enforce_referential_integrity = st.checkbox(
                    "Enforce Referential Integrity"
                )

            # Description
            description = st.text_area("Description (Optional)")

            if st.form_submit_button("➕ Add Relationship", type="primary"):
                if all([source_table, source_column, target_table, target_column]):
                    self._add_manual_relationship(
                        source_table,
                        source_column,
                        target_table,
                        target_column,
                        relationship_type,
                        cardinality,
                        enforce_referential_integrity,
                        description,
                    )
                    st.success("✅ Relationship added successfully!")
                    st.rerun()
                else:
                    st.error("❌ Please fill in all required fields")

        # Display existing manual relationships
        if st.session_state.manual_relationships:
            st.subheader("📋 Manual Relationships")

            for i, rel in enumerate(st.session_state.manual_relationships):
                with st.expander(
                    f"{rel['source_table']}.{rel['source_column']} → "
                    f"{rel['target_table']}.{rel['target_column']} ({rel['cardinality']})"
                ):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.write(f"**Type:** {rel['relationship_type']}")
                        st.write(f"**Cardinality:** {rel['cardinality']}")

                    with col2:
                        st.write(
                            f"**Enforce Integrity:** {'Yes' if rel['enforce_referential_integrity'] else 'No'}"
                        )
                        st.write(f"**Added:** {rel['created_at']}")

                    with col3:
                        if st.button("🗑️ Remove", key=f"remove_manual_{i}"):
                            self._remove_manual_relationship(i)
                            st.rerun()

                    if rel["description"]:
                        st.write(f"**Description:** {rel['description']}")

    def _detect_relationships(self, method: str, confidence_threshold: float):
        """Detect relationships between tables."""
        detected_relationships = []

        if method in ["Name Pattern Matching", "Combined Analysis"]:
            detected_relationships.extend(
                self._detect_relationships_by_name_patterns(confidence_threshold)
            )

        if method in ["Data Analysis", "Combined Analysis"]:
            detected_relationships.extend(
                self._detect_relationships_by_data_analysis(confidence_threshold)
            )

        # Remove duplicates and filter by confidence
        unique_relationships = []
        seen_relationships = set()

        for rel in detected_relationships:
            rel_key = (
                rel["source_table"],
                rel["source_column"],
                rel["target_table"],
                rel["target_column"],
            )
            if (
                rel_key not in seen_relationships
                and rel["confidence"] >= confidence_threshold
            ):
                unique_relationships.append(rel)
                seen_relationships.add(rel_key)

        st.session_state.detected_relationships = unique_relationships

    def _detect_relationships_by_name_patterns(
        self, confidence_threshold: float
    ) -> List[Dict]:
        """Detect relationships using column name pattern matching."""
        relationships = []

        # Common foreign key patterns
        fk_patterns = [
            r"^(.+)_id$",  # table_id
            r"^(.+)Id$",  # tableId
            r"^id_(.+)$",  # id_table
            r"^(.+)_key$",  # table_key
            r"^fk_(.+)$",  # fk_table
        ]

        for source_table in self.registered_tables:
            source_columns = self._get_table_columns(source_table["name"])

            for source_col in source_columns:
                # Check if column name matches FK patterns
                for pattern in fk_patterns:
                    match = re.match(pattern, source_col, re.IGNORECASE)
                    if match:
                        referenced_table = match.group(1)

                        # Look for matching table
                        for target_table in self.registered_tables:
                            if (
                                target_table["name"].lower() == referenced_table.lower()
                                or referenced_table.lower()
                                in target_table["name"].lower()
                            ):

                                # Look for primary key column in target table
                                target_columns = self._get_table_columns(
                                    target_table["name"]
                                )
                                for target_col in target_columns:
                                    if target_col.lower() in [
                                        "id",
                                        "pk",
                                        f"{target_table['name']}_id".lower(),
                                    ]:
                                        confidence = (
                                            self._calculate_name_pattern_confidence(
                                                source_col, target_col, pattern
                                            )
                                        )

                                        if confidence >= confidence_threshold:
                                            relationships.append(
                                                {
                                                    "source_table": source_table[
                                                        "name"
                                                    ],
                                                    "source_column": source_col,
                                                    "target_table": target_table[
                                                        "name"
                                                    ],
                                                    "target_column": target_col,
                                                    "relationship_type": "Many-to-One",
                                                    "confidence": confidence,
                                                    "detection_method": "Name Pattern Matching",
                                                    "evidence": [
                                                        f"Column '{source_col}' matches pattern '{pattern}'",
                                                        f"Referenced table '{target_table['name']}' found",
                                                        f"Target column '{target_col}' appears to be primary key",
                                                    ],
                                                }
                                            )

        return relationships

    def _detect_relationships_by_data_analysis(
        self, confidence_threshold: float
    ) -> List[Dict]:
        """Detect relationships using data analysis."""
        relationships = []

        for source_table in self.registered_tables:
            for target_table in self.registered_tables:
                if source_table["name"] == target_table["name"]:
                    continue

                source_columns = self._get_table_columns(source_table["name"])
                target_columns = self._get_table_columns(target_table["name"])

                # Compare columns for potential relationships
                for source_col in source_columns:
                    for target_col in target_columns:
                        # Skip if column names are too different
                        if not self._columns_potentially_related(
                            source_col, target_col
                        ):
                            continue

                        try:
                            # Sample data from both columns
                            source_data = self._sample_column_data(
                                source_table["name"], source_col
                            )
                            target_data = self._sample_column_data(
                                target_table["name"], target_col
                            )

                            if source_data is None or target_data is None:
                                continue

                            # Calculate relationship metrics
                            match_rate = self._calculate_match_rate(
                                source_data, target_data
                            )
                            cardinality = self._analyze_cardinality(
                                source_data, target_data
                            )

                            if match_rate >= 0.1:  # At least 10% match rate
                                confidence = self._calculate_data_analysis_confidence(
                                    match_rate, cardinality, source_col, target_col
                                )

                                if confidence >= confidence_threshold:
                                    relationships.append(
                                        {
                                            "source_table": source_table["name"],
                                            "source_column": source_col,
                                            "target_table": target_table["name"],
                                            "target_column": target_col,
                                            "relationship_type": self._infer_relationship_type(
                                                cardinality
                                            ),
                                            "confidence": confidence,
                                            "detection_method": "Data Analysis",
                                            "match_rate": f"{match_rate:.1%}",
                                            "evidence": [
                                                f"Match rate: {match_rate:.1%}",
                                                f"Cardinality analysis: {cardinality}",
                                                f"Column similarity score: {self._calculate_column_similarity(source_col, target_col):.2f}",
                                            ],
                                        }
                                    )

                        except Exception:
                            # Skip this column pair if analysis fails
                            continue

        return relationships

    def _generate_schema_diagram(
        self, layout_algorithm: str, show_columns: bool, highlight_relationships: bool
    ):
        """Generate interactive schema diagram."""
        try:
            # Create graph
            G = nx.Graph()

            # Add table nodes
            for table in self.registered_tables:
                table_info = self._get_table_info(table["name"])
                G.add_node(
                    table["name"],
                    type="table",
                    columns=table_info["columns"] if show_columns else [],
                    row_count=table["rows"],
                )

            # Add relationship edges
            all_relationships = (
                st.session_state.detected_relationships
                + st.session_state.manual_relationships
            )

            for rel in all_relationships:
                if G.has_node(rel["source_table"]) and G.has_node(rel["target_table"]):
                    G.add_edge(
                        rel["source_table"],
                        rel["target_table"],
                        source_column=rel["source_column"],
                        target_column=rel["target_column"],
                        relationship_type=rel.get("relationship_type", "Unknown"),
                    )

            if len(G.nodes()) == 0:
                return None

            # Calculate layout
            if layout_algorithm == "Spring":
                pos = nx.spring_layout(G, k=3, iterations=50)
            elif layout_algorithm == "Circular":
                pos = nx.circular_layout(G)
            elif layout_algorithm == "Shell":
                pos = nx.shell_layout(G)
            elif layout_algorithm == "Kamada-Kawai":
                pos = nx.kamada_kawai_layout(G)
            else:
                pos = nx.spring_layout(G)

            # Create plotly figure
            fig = go.Figure()

            # Add edges (relationships)
            if highlight_relationships:
                for edge in G.edges():
                    x0, y0 = pos[edge[0]]
                    x1, y1 = pos[edge[1]]

                    fig.add_trace(
                        go.Scatter(
                            x=[x0, x1, None],
                            y=[y0, y1, None],
                            mode="lines",
                            line=dict(width=2, color="rgba(125, 125, 125, 0.8)"),
                            hoverinfo="none",
                            showlegend=False,
                        )
                    )

                    # Add relationship label
                    edge_data = G.edges[edge]
                    mid_x, mid_y = (x0 + x1) / 2, (y0 + y1) / 2

                    fig.add_trace(
                        go.Scatter(
                            x=[mid_x],
                            y=[mid_y],
                            mode="text",
                            text=[
                                f"{edge_data['source_column']}→{edge_data['target_column']}"
                            ],
                            textposition="middle center",
                            textfont=dict(size=8, color="gray"),
                            showlegend=False,
                            hoverinfo="text",
                            hovertext=f"Relationship: {edge_data['relationship_type']}",
                        )
                    )

            # Add nodes (tables)
            node_x = []
            node_y = []
            node_text = []
            node_info = []
            node_size = []
            node_color = []

            for node in G.nodes():
                x, y = pos[node]
                node_x.append(x)
                node_y.append(y)

                node_data = G.nodes[node]

                # Node text
                if show_columns:
                    columns_text = "<br>".join(
                        [f"• {col}" for col in node_data["columns"][:10]]
                    )
                    if len(node_data["columns"]) > 10:
                        columns_text += (
                            f"<br>... and {len(node_data['columns']) - 10} more"
                        )
                    text = f"<b>{node}</b><br>{columns_text}"
                else:
                    text = f"<b>{node}</b>"

                node_text.append(text)

                # Hover info
                info = f"Table: {node}<br>Rows: {node_data['row_count']:,}<br>Columns: {len(node_data['columns'])}"
                node_info.append(info)

                # Node size based on row count
                size = max(20, min(60, math.log10(max(1, node_data["row_count"])) * 10))
                node_size.append(size)

                # Node color based on number of relationships
                relationship_count = len(
                    [
                        rel
                        for rel in all_relationships
                        if rel["source_table"] == node or rel["target_table"] == node
                    ]
                )
                node_color.append(relationship_count)

            fig.add_trace(
                go.Scatter(
                    x=node_x,
                    y=node_y,
                    mode="markers+text",
                    marker=dict(
                        size=node_size,
                        color=node_color,
                        colorscale="Viridis",
                        showscale=True,
                        colorbar=dict(title="Relationships Count"),
                        line=dict(width=2, color="white"),
                    ),
                    text=node_text,
                    textposition="middle center",
                    hoverinfo="text",
                    hovertext=node_info,
                    showlegend=False,
                )
            )

            # Update layout
            fig.update_layout(
                title="Database Schema Diagram",
                showlegend=False,
                hovermode="closest",
                margin=dict(b=20, l=5, r=5, t=40),
                annotations=[
                    dict(
                        text="Node size represents row count, color represents relationship count",
                        showarrow=False,
                        xref="paper",
                        yref="paper",
                        x=0.005,
                        y=-0.002,
                        xanchor="left",
                        yanchor="bottom",
                        font=dict(size=12, color="gray"),
                    )
                ],
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                plot_bgcolor="white",
            )

            return fig

        except Exception as e:
            st.error(f"Error generating schema diagram: {str(e)}")
            return None

    def _validate_relationships(self, method: str, sample_size: int):
        """Validate relationships using specified method."""
        all_relationships = (
            st.session_state.detected_relationships
            + st.session_state.manual_relationships
        )

        validation_results = {}

        for rel in all_relationships:
            rel_key = f"{rel['source_table']}.{rel['source_column']} → {rel['target_table']}.{rel['target_column']}"

            try:
                if method == "Data Integrity Check":
                    result = self._validate_data_integrity(rel, sample_size)
                elif method == "Referential Integrity":
                    result = self._validate_referential_integrity(rel, sample_size)
                elif method == "Statistical Analysis":
                    result = self._validate_statistical_relationship(rel, sample_size)
                else:
                    result = {"valid": False, "error": "Unknown validation method"}

                validation_results[rel_key] = result

            except Exception as e:
                validation_results[rel_key] = {
                    "valid": False,
                    "error": str(e),
                    "integrity_score": 0.0,
                    "match_rate": 0.0,
                    "null_rate": 1.0,
                    "issues": [f"Validation error: {str(e)}"],
                    "recommendations": ["Check table and column names for accuracy"],
                }

        st.session_state.relationship_validation_results = validation_results

    def _validate_data_integrity(self, relationship: Dict, sample_size: int) -> Dict:
        """Validate data integrity of a relationship."""
        try:
            # Sample data from both columns
            source_query = f"SELECT {relationship['source_column']} FROM {relationship['source_table']} WHERE {relationship['source_column']} IS NOT NULL LIMIT {sample_size}"
            target_query = f"SELECT DISTINCT {relationship['target_column']} FROM {relationship['target_table']} WHERE {relationship['target_column']} IS NOT NULL"

            source_data = self.db_connection.execute_query(source_query)
            target_data = self.db_connection.execute_query(target_query)

            if source_data.empty or target_data.empty:
                return {
                    "valid": False,
                    "integrity_score": 0.0,
                    "match_rate": 0.0,
                    "null_rate": 1.0,
                    "issues": ["No data found in one or both columns"],
                    "recommendations": ["Check if tables contain data"],
                }

            source_values = set(source_data.iloc[:, 0].dropna())
            target_values = set(target_data.iloc[:, 0].dropna())

            # Calculate metrics
            matches = len(source_values.intersection(target_values))
            match_rate = matches / len(source_values) if source_values else 0
            null_rate = (
                (len(source_data) - len(source_values)) / len(source_data)
                if len(source_data) > 0
                else 0
            )

            # Calculate integrity score
            integrity_score = match_rate * (
                1 - null_rate * 0.5
            )  # Penalize high null rates

            # Identify issues
            issues = []
            recommendations = []

            if match_rate < 0.8:
                issues.append(f"Low match rate: {match_rate:.1%}")
                recommendations.append(
                    "Check for data inconsistencies or missing references"
                )

            if null_rate > 0.2:
                issues.append(f"High null rate: {null_rate:.1%}")
                recommendations.append(
                    "Consider allowing NULL values or filling missing data"
                )

            orphaned_values = source_values - target_values
            if orphaned_values:
                issues.append(f"{len(orphaned_values)} orphaned values found")
                recommendations.append(
                    "Review orphaned records and fix referential integrity"
                )

            return {
                "valid": integrity_score >= 0.7,
                "integrity_score": integrity_score,
                "match_rate": match_rate,
                "null_rate": null_rate,
                "issues": issues,
                "recommendations": recommendations,
            }

        except Exception as e:
            return {
                "valid": False,
                "integrity_score": 0.0,
                "match_rate": 0.0,
                "null_rate": 1.0,
                "issues": [f"Validation failed: {str(e)}"],
                "recommendations": ["Check table and column existence"],
            }

    def _validate_referential_integrity(
        self, relationship: Dict, sample_size: int
    ) -> Dict:
        """Validate referential integrity of a relationship."""
        # This would implement more sophisticated referential integrity checks
        # For now, use the data integrity validation as a base
        return self._validate_data_integrity(relationship, sample_size)

    def _validate_statistical_relationship(
        self, relationship: Dict, sample_size: int
    ) -> Dict:
        """Validate relationship using statistical analysis."""
        # This would implement statistical tests for relationships
        # For now, use the data integrity validation as a base
        return self._validate_data_integrity(relationship, sample_size)

    def _render_table_statistics(self):
        """Render table statistics."""
        st.subheader("📊 Table Statistics")

        stats_data = []
        for table in self.registered_tables:
            table_info = self._get_table_info(table["name"])
            relationship_count = len(
                [
                    rel
                    for rel in st.session_state.detected_relationships
                    + st.session_state.manual_relationships
                    if rel["source_table"] == table["name"]
                    or rel["target_table"] == table["name"]
                ]
            )

            stats_data.append(
                {
                    "Table": table["name"],
                    "Rows": table["rows"],
                    "Columns": len(table_info["columns"]),
                    "Relationships": relationship_count,
                    "Memory (MB)": f"{table['rows'] * len(table_info['columns']) * 8 / 1024 / 1024:.2f}",
                }
            )

        if stats_data:
            stats_df = pd.DataFrame(stats_data)
            st.dataframe(stats_df, use_container_width=True)

    # Helper methods
    def _get_table_columns(self, table_name: str) -> List[str]:
        """Get column names for a table."""
        try:
            table_info = self.db_connection.get_table_info(table_name)
            return [col["name"] for col in table_info["columns"]]
        except:
            return []

    def _get_table_info(self, table_name: str) -> Dict:
        """Get comprehensive table information."""
        try:
            return self.db_connection.get_table_info(table_name)
        except:
            return {"columns": []}

    def _sample_column_data(
        self, table_name: str, column_name: str, sample_size: int = 1000
    ) -> Optional[pd.Series]:
        """Sample data from a column."""
        try:
            query = f"SELECT {column_name} FROM {table_name} WHERE {column_name} IS NOT NULL LIMIT {sample_size}"
            df = self.db_connection.execute_query(query)
            return df.iloc[:, 0] if not df.empty else None
        except:
            return None

    def _calculate_name_pattern_confidence(
        self, source_col: str, target_col: str, pattern: str
    ) -> float:
        """Calculate confidence score for name pattern matching."""
        base_confidence = 0.8  # Base confidence for pattern match

        # Boost confidence for exact name matches
        if (
            source_col.lower().replace("_id", "").replace("id", "")
            == target_col.lower()
        ):
            base_confidence += 0.15

        # Boost for common FK naming conventions
        if any(
            keyword in source_col.lower() for keyword in ["_id", "id_", "_key", "fk_"]
        ):
            base_confidence += 0.05

        return min(1.0, base_confidence)

    def _columns_potentially_related(self, col1: str, col2: str) -> bool:
        """Check if two columns could potentially be related."""
        col1_lower = col1.lower()
        col2_lower = col2.lower()

        # Check for common relationship patterns
        patterns = [
            (col1_lower.endswith("_id") and col2_lower in ["id", "pk"]),
            (col2_lower.endswith("_id") and col1_lower in ["id", "pk"]),
            (col1_lower == col2_lower),
            (col1_lower.replace("_", "") == col2_lower.replace("_", "")),
            (
                any(keyword in col1_lower for keyword in ["id", "key", "ref"])
                and any(keyword in col2_lower for keyword in ["id", "key", "ref"])
            ),
        ]

        return any(patterns)

    def _calculate_match_rate(
        self, source_data: pd.Series, target_data: pd.Series
    ) -> float:
        """Calculate the match rate between two data series."""
        source_values = set(source_data.dropna())
        target_values = set(target_data.dropna())

        if not source_values:
            return 0.0

        matches = len(source_values.intersection(target_values))
        return matches / len(source_values)

    def _analyze_cardinality(
        self, source_data: pd.Series, target_data: pd.Series
    ) -> str:
        """Analyze the cardinality of the relationship."""
        source_unique = source_data.nunique()
        target_unique = target_data.nunique()
        source_total = len(source_data)
        target_total = len(target_data)

        source_uniqueness = source_unique / source_total if source_total > 0 else 0
        target_uniqueness = target_unique / target_total if target_total > 0 else 0

        if source_uniqueness > 0.9 and target_uniqueness > 0.9:
            return "One-to-One"
        elif source_uniqueness > 0.9:
            return "One-to-Many"
        elif target_uniqueness > 0.9:
            return "Many-to-One"
        else:
            return "Many-to-Many"

    def _calculate_data_analysis_confidence(
        self, match_rate: float, cardinality: str, source_col: str, target_col: str
    ) -> float:
        """Calculate confidence score for data analysis."""
        base_confidence = match_rate * 0.8  # Match rate is primary factor

        # Boost for good cardinality patterns
        cardinality_boost = {
            "One-to-One": 0.1,
            "One-to-Many": 0.15,
            "Many-to-One": 0.15,
            "Many-to-Many": 0.05,
        }
        base_confidence += cardinality_boost.get(cardinality, 0)

        # Boost for column name similarity
        name_similarity = self._calculate_column_similarity(source_col, target_col)
        base_confidence += name_similarity * 0.1

        return min(1.0, base_confidence)

    def _calculate_column_similarity(self, col1: str, col2: str) -> float:
        """Calculate similarity between column names."""
        col1_clean = col1.lower().replace("_", "").replace("id", "")
        col2_clean = col2.lower().replace("_", "").replace("id", "")

        if col1_clean == col2_clean:
            return 1.0
        elif col1_clean in col2_clean or col2_clean in col1_clean:
            return 0.8
        else:
            # Simple character similarity
            common_chars = set(col1_clean).intersection(set(col2_clean))
            total_chars = set(col1_clean).union(set(col2_clean))
            return len(common_chars) / len(total_chars) if total_chars else 0.0

    def _infer_relationship_type(self, cardinality: str) -> str:
        """Infer relationship type from cardinality analysis."""
        return cardinality  # For now, use cardinality as relationship type

    def _accept_relationship(self, index: int):
        """Accept a detected relationship."""
        if 0 <= index < len(st.session_state.detected_relationships):
            relationship = st.session_state.detected_relationships.pop(index)
            relationship["status"] = "accepted"
            relationship["created_at"] = pd.Timestamp.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            st.session_state.manual_relationships.append(relationship)

    def _reject_relationship(self, index: int):
        """Reject a detected relationship."""
        if 0 <= index < len(st.session_state.detected_relationships):
            st.session_state.detected_relationships.pop(index)

    def _add_manual_relationship(
        self,
        source_table: str,
        source_column: str,
        target_table: str,
        target_column: str,
        relationship_type: str,
        cardinality: str,
        enforce_integrity: bool,
        description: str,
    ):
        """Add a manual relationship."""
        relationship = {
            "source_table": source_table,
            "source_column": source_column,
            "target_table": target_table,
            "target_column": target_column,
            "relationship_type": relationship_type,
            "cardinality": cardinality,
            "enforce_referential_integrity": enforce_integrity,
            "description": description,
            "detection_method": "Manual",
            "confidence": 1.0,
            "created_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        st.session_state.manual_relationships.append(relationship)

    def _remove_manual_relationship(self, index: int):
        """Remove a manual relationship."""
        if 0 <= index < len(st.session_state.manual_relationships):
            st.session_state.manual_relationships.pop(index)

    def _export_diagram(self, fig, format_type: str):
        """Export diagram in specified format."""
        try:
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"schema_diagram_{timestamp}.{format_type}"

            if format_type == "png":
                img_bytes = fig.to_image(format="png", width=1200, height=800)
                st.download_button("📥 Download PNG", img_bytes, filename, "image/png")
            elif format_type == "svg":
                img_bytes = fig.to_image(format="svg", width=1200, height=800)
                st.download_button(
                    "📥 Download SVG", img_bytes, filename, "image/svg+xml"
                )
            elif format_type == "html":
                html_str = fig.to_html(include_plotlyjs="cdn")
                st.download_button("📥 Download HTML", html_str, filename, "text/html")

            st.success(f"✅ Diagram exported as {format_type.upper()}")

        except Exception as e:
            st.error(f"❌ Export failed: {str(e)}")
