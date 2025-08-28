"""Analytics module for DuckDB Analytics Dashboard."""

from .templates import AnalyticsTemplate, TemplateEngine, TemplateLibrary
from .profiler import DataProfiler, SummaryStatsGenerator
from .filter_builder import FilterBuilder
from .performance import AnalyticsOptimizer, ProgressiveLoader

__all__ = [
    "AnalyticsTemplate",
    "TemplateEngine", 
    "TemplateLibrary",
    "DataProfiler",
    "SummaryStatsGenerator",
    "FilterBuilder",
    "AnalyticsOptimizer",
    "ProgressiveLoader"
]