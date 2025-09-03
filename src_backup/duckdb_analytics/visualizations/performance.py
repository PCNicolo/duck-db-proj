"""Performance optimization utilities for visualizations."""

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DataSampler:
    """Smart data sampling for large datasets."""

    def __init__(self, max_points: int = 10000, min_sample_ratio: float = 0.01):
        self.max_points = max_points
        self.min_sample_ratio = min_sample_ratio

    def should_sample(self, df: pd.DataFrame) -> bool:
        """Determine if data should be sampled."""
        return len(df) > self.max_points

    def smart_sample(
        self, df: pd.DataFrame, preserve_patterns: bool = True
    ) -> pd.DataFrame:
        """Apply smart sampling that preserves data patterns."""
        if not self.should_sample(df):
            return df

        sample_size = max(
            int(len(df) * self.min_sample_ratio), min(self.max_points, len(df))
        )

        if preserve_patterns:
            return self._stratified_sample(df, sample_size)
        else:
            return df.sample(n=sample_size, random_state=42)

    def _stratified_sample(self, df: pd.DataFrame, sample_size: int) -> pd.DataFrame:
        """Perform stratified sampling to preserve data distribution."""
        # Identify categorical columns for stratification
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns

        if len(categorical_cols) == 0:
            # No categorical columns, use random sampling
            return df.sample(n=sample_size, random_state=42)

        # Use first categorical column for stratification
        strat_col = categorical_cols[0]

        try:
            # Calculate samples per stratum
            value_counts = df[strat_col].value_counts()
            total_count = len(df)

            sampled_dfs = []
            remaining_samples = sample_size

            for i, (value, count) in enumerate(value_counts.items()):
                if i == len(value_counts) - 1:
                    # Last stratum gets all remaining samples
                    stratum_sample_size = remaining_samples
                else:
                    # Proportional sampling
                    proportion = count / total_count
                    stratum_sample_size = max(1, int(sample_size * proportion))
                    remaining_samples -= stratum_sample_size

                stratum_df = df[df[strat_col] == value]
                if len(stratum_df) > stratum_sample_size:
                    sampled_stratum = stratum_df.sample(
                        n=stratum_sample_size, random_state=42
                    )
                else:
                    sampled_stratum = stratum_df

                sampled_dfs.append(sampled_stratum)

                if remaining_samples <= 0:
                    break

            return pd.concat(sampled_dfs, ignore_index=True)

        except Exception as e:
            logger.warning(f"Stratified sampling failed: {e}, using random sampling")
            return df.sample(n=sample_size, random_state=42)


class ChartCache:
    """Cache for chart configurations and rendered charts."""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = {}
        self.access_times = {}

    def _generate_key(self, df: pd.DataFrame, chart_config: Dict[str, Any]) -> str:
        """Generate cache key from dataframe and config."""
        # Create hash from dataframe shape, columns, and first few rows
        df_info = {
            "shape": df.shape,
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.to_dict().items()},
            "sample_hash": hashlib.md5(str(df.head(10).to_csv()).encode()).hexdigest()[
                :16
            ],
        }

        # Combine with config
        cache_data = {
            "df_info": df_info,
            "config": (
                sorted(chart_config.items())
                if isinstance(chart_config, dict)
                else chart_config
            ),
        }

        return hashlib.md5(str(cache_data).encode()).hexdigest()

    def get(self, df: pd.DataFrame, chart_config: Dict[str, Any]) -> Optional[Any]:
        """Get cached chart if available."""
        key = self._generate_key(df, chart_config)

        if key in self.cache:
            entry = self.cache[key]

            # Check TTL
            if time.time() - entry["timestamp"] < self.ttl_seconds:
                self.access_times[key] = time.time()
                return entry["chart"]
            else:
                # Expired
                del self.cache[key]
                del self.access_times[key]

        return None

    def set(self, df: pd.DataFrame, chart_config: Dict[str, Any], chart: Any) -> None:
        """Store chart in cache."""
        key = self._generate_key(df, chart_config)

        # Evict if cache is full
        if len(self.cache) >= self.max_size:
            self._evict_lru()

        self.cache[key] = {"chart": chart, "timestamp": time.time()}
        self.access_times[key] = time.time()

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self.access_times:
            return

        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        del self.cache[lru_key]
        del self.access_times[lru_key]

    def clear(self) -> None:
        """Clear all cached entries."""
        self.cache.clear()
        self.access_times.clear()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hit_rate": getattr(self, "_hit_count", 0)
            / max(getattr(self, "_total_requests", 1), 1),
            "ttl_seconds": self.ttl_seconds,
        }


class PerformanceMonitor:
    """Monitor and optimize visualization performance."""

    def __init__(self):
        self.metrics = {}
        self.thresholds = {
            "render_time": 5.0,  # seconds
            "memory_usage": 500,  # MB
            "data_points": 50000,
        }

    def start_timing(self, operation: str) -> str:
        """Start timing an operation."""
        timer_id = f"{operation}_{int(time.time() * 1000)}"
        self.metrics[timer_id] = {"start_time": time.time(), "operation": operation}
        return timer_id

    def end_timing(self, timer_id: str) -> float:
        """End timing and return duration."""
        if timer_id in self.metrics:
            duration = time.time() - self.metrics[timer_id]["start_time"]
            self.metrics[timer_id]["duration"] = duration
            return duration
        return 0.0

    def log_performance(
        self, operation: str, duration: float, data_points: int, memory_mb: float
    ) -> Dict[str, Any]:
        """Log performance metrics."""
        perf_data = {
            "operation": operation,
            "duration": duration,
            "data_points": data_points,
            "memory_mb": memory_mb,
            "timestamp": time.time(),
        }

        # Check thresholds
        warnings = []
        if duration > self.thresholds["render_time"]:
            warnings.append(f"Slow render time: {duration:.2f}s")
        if memory_mb > self.thresholds["memory_usage"]:
            warnings.append(f"High memory usage: {memory_mb:.1f}MB")
        if data_points > self.thresholds["data_points"]:
            warnings.append(f"Large dataset: {data_points:,} points")

        perf_data["warnings"] = warnings

        if warnings:
            logger.warning(f"Performance issues in {operation}: {', '.join(warnings)}")

        return perf_data

    def get_recommendations(self, df: pd.DataFrame, chart_type: str) -> List[str]:
        """Get performance optimization recommendations."""
        recommendations = []

        row_count = len(df)
        col_count = len(df.columns)

        # Data size recommendations
        if row_count > 10000:
            recommendations.append(
                "Consider enabling data sampling for better performance"
            )

        if col_count > 20:
            recommendations.append("Select fewer columns to improve rendering speed")

        # Chart-specific recommendations
        if chart_type in ["scatter_matrix", "heatmap"] and row_count > 5000:
            recommendations.append(
                "Large datasets may cause slow rendering with this chart type"
            )

        if chart_type == "sankey" and row_count > 1000:
            recommendations.append(
                "Sankey diagrams perform best with < 1000 data points"
            )

        # Memory recommendations
        memory_estimate = self._estimate_memory_usage(df)
        if memory_estimate > 100:  # MB
            recommendations.append("Large dataset may cause high memory usage")

        return recommendations

    def _estimate_memory_usage(self, df: pd.DataFrame) -> float:
        """Estimate memory usage in MB."""
        return df.memory_usage(deep=True).sum() / (1024 * 1024)


class LazyRenderer:
    """Lazy loading and progressive rendering for charts."""

    def __init__(self, chunk_size: int = 1000):
        self.chunk_size = chunk_size

    def should_use_lazy_rendering(self, df: pd.DataFrame) -> bool:
        """Determine if lazy rendering should be used."""
        return len(df) > 5000

    def create_data_chunks(self, df: pd.DataFrame) -> List[pd.DataFrame]:
        """Split dataframe into chunks for progressive loading."""
        chunks = []
        for i in range(0, len(df), self.chunk_size):
            chunk = df.iloc[i : i + self.chunk_size]
            chunks.append(chunk)
        return chunks

    def render_progressively(
        self, df: pd.DataFrame, chart_func, *args, **kwargs
    ) -> List[Any]:
        """Render chart progressively in chunks."""
        if not self.should_use_lazy_rendering(df):
            return [chart_func(df, *args, **kwargs)]

        chunks = self.create_data_chunks(df)
        rendered_chunks = []

        for i, chunk in enumerate(chunks):
            try:
                chunk_chart = chart_func(chunk, *args, **kwargs)
                rendered_chunks.append(
                    {"chart": chunk_chart, "chunk_index": i, "row_count": len(chunk)}
                )
            except Exception as e:
                logger.error(f"Error rendering chunk {i}: {e}")
                continue

        return rendered_chunks


class VisualizationOptimizer:
    """Main optimization coordinator."""

    def __init__(self):
        self.sampler = DataSampler()
        self.cache = ChartCache()
        self.monitor = PerformanceMonitor()
        self.lazy_renderer = LazyRenderer()

    def optimize_data_for_chart(
        self, df: pd.DataFrame, chart_type: str
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Optimize data for specific chart type."""
        optimization_info = {"original_size": len(df), "optimizations_applied": []}

        optimized_df = df.copy()

        # Apply sampling if needed
        if self.sampler.should_sample(df):
            optimized_df = self.sampler.smart_sample(optimized_df)
            optimization_info["optimizations_applied"].append("data_sampling")
            optimization_info["sampled_size"] = len(optimized_df)

        # Chart-specific optimizations
        if chart_type in ["heatmap", "treemap"] and len(optimized_df) > 1000:
            # Aggregate data for better performance
            optimized_df = self._aggregate_for_heatmap(optimized_df)
            optimization_info["optimizations_applied"].append("data_aggregation")

        return optimized_df, optimization_info

    def _aggregate_for_heatmap(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate data for heatmap performance."""
        # Simple aggregation - could be made more sophisticated
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns

        if len(categorical_cols) >= 2 and len(numeric_cols) >= 1:
            # Group by first two categorical columns and sum numeric columns
            group_cols = categorical_cols[:2].tolist()
            agg_dict = {col: "sum" for col in numeric_cols}

            try:
                return df.groupby(group_cols).agg(agg_dict).reset_index()
            except Exception:
                return df

        return df

    def get_optimized_chart(
        self,
        df: pd.DataFrame,
        chart_func,
        chart_config: Dict[str, Any],
        *args,
        **kwargs,
    ):
        """Get optimized chart with caching and performance monitoring."""
        timer_id = self.monitor.start_timing(f"{chart_func.__name__}")

        # Check cache first
        cached_chart = self.cache.get(df, chart_config)
        if cached_chart is not None:
            self.monitor.end_timing(timer_id)
            return cached_chart

        try:
            # Optimize data
            optimized_df, opt_info = self.optimize_data_for_chart(
                df, chart_config.get("chart_type", "unknown")
            )

            # Create chart
            chart = chart_func(optimized_df, *args, **kwargs)

            # Cache result
            self.cache.set(df, chart_config, chart)

            # Log performance
            duration = self.monitor.end_timing(timer_id)
            memory_usage = self.monitor._estimate_memory_usage(optimized_df)

            self.monitor.log_performance(
                chart_func.__name__, duration, len(optimized_df), memory_usage
            )

            return chart

        except Exception as e:
            self.monitor.end_timing(timer_id)
            logger.error(f"Chart optimization failed: {e}")
            # Fallback to original function
            return chart_func(df, *args, **kwargs)
