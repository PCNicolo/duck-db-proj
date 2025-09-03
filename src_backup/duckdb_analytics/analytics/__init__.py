"""Analytics module for DuckDB Analytics Dashboard."""

from .filter_builder import FilterBuilder
from .performance import AnalyticsOptimizer, ProgressiveLoader
from .profiler import DataProfiler, SummaryStatsGenerator
from .templates import AnalyticsTemplate, TemplateEngine, TemplateLibrary

__all__ = [
    "AnalyticsTemplate",
    "TemplateEngine",
    "TemplateLibrary",
    "DataProfiler",
    "SummaryStatsGenerator",
    "FilterBuilder",
    "AnalyticsOptimizer",
    "ProgressiveLoader",
]
