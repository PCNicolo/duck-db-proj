"""DuckDB Analytics Dashboard - Local data analytics made simple."""

__version__ = "0.1.0"

from .core.connection import DuckDBConnection
from .core.query_engine import QueryEngine
from .data.file_manager import FileManager

__all__ = ["DuckDBConnection", "QueryEngine", "FileManager"]