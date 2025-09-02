# DuckDB Analytics Dashboard Project Overview

## Purpose
A powerful local data analytics dashboard built on DuckDB for analyzing CSV and Parquet files with zero-copy SQL queries. The project provides both a web-based Streamlit dashboard and a CLI tool for data exploration and analytics.

## Tech Stack
- **Database**: DuckDB (embedded analytical database) v0.9.0+
- **Backend**: Python 3.10+
- **Web Framework**: Streamlit v1.28.0+
- **Visualization**: Plotly v5.17.0+, Altair v5.0.0+
- **CLI**: Click v8.1.0+
- **Data Processing**: Pandas v2.0.0+, PyArrow v14.0.0+

## Main Features
1. Zero-copy analytics - query files directly without loading into memory
2. Interactive Streamlit web dashboard for data exploration
3. CLI tool for command-line queries and operations
4. Support for CSV and Parquet file formats
5. Full SQL editor with query templates and execution plans
6. Built-in visualizations using Plotly
7. Data management with file upload, conversion, and catalog management
8. Sample data generator for testing and demos

## Design Principles
- **Zero-Copy Analytics**: Query files directly without loading into memory
- **Local-First**: No external dependencies or cloud services
- **Performance**: Leverage DuckDB's columnar engine for fast queries
- **Simplicity**: Minimal setup, intuitive interface
- **Extensibility**: Plugin architecture for custom analytics