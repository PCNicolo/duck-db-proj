"""Query metrics collection and logging system."""

import json
import logging
import threading
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configure logger
logger = logging.getLogger(__name__)


@dataclass
class QueryMetric:
    """Detailed metrics for a single query execution."""

    query_id: str
    query_text: str
    start_time: datetime
    end_time: Optional[datetime] = None
    execution_time: float = 0.0
    rows_returned: int = 0
    bytes_processed: int = 0
    cache_hit: bool = False
    error: Optional[str] = None
    query_type: str = "SELECT"  # SELECT, INSERT, UPDATE, DELETE, DDL
    table_names: List[str] = field(default_factory=list)
    memory_peak_mb: float = 0.0
    cpu_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["start_time"] = self.start_time.isoformat()
        if self.end_time:
            data["end_time"] = self.end_time.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryMetric":
        """Create from dictionary."""
        data["start_time"] = datetime.fromisoformat(data["start_time"])
        if data.get("end_time"):
            data["end_time"] = datetime.fromisoformat(data["end_time"])
        return cls(**data)


class QueryMetricsCollector:
    """Collects and manages query execution metrics."""

    def __init__(
        self,
        max_history: int = 1000,
        slow_query_threshold_ms: float = 2000,
        log_slow_queries: bool = True,
        persist_to_file: Optional[str] = None,
    ):
        """
        Initialize metrics collector.

        Args:
            max_history: Maximum number of queries to keep in history
            slow_query_threshold_ms: Threshold for slow query logging
            log_slow_queries: Whether to log slow queries
            persist_to_file: Optional file path for persistence
        """
        self.max_history = max_history
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self.log_slow_queries = log_slow_queries
        self.persist_to_file = persist_to_file

        # Metrics storage
        self.query_history: deque = deque(maxlen=max_history)
        self.active_queries: Dict[str, QueryMetric] = {}
        self._lock = threading.Lock()

        # Aggregated statistics
        self.total_queries = 0
        self.total_execution_time = 0.0
        self.total_rows = 0
        self.cache_hits = 0
        self.errors = 0

        # Load persisted metrics if specified
        if persist_to_file:
            self._load_persisted_metrics()

    def start_query(self, query_id: str, query_text: str) -> QueryMetric:
        """
        Start tracking a new query.

        Args:
            query_id: Unique query identifier
            query_text: SQL query text

        Returns:
            QueryMetric object
        """
        with self._lock:
            metric = QueryMetric(
                query_id=query_id,
                query_text=query_text[:1000],  # Truncate long queries
                start_time=datetime.now(),
                query_type=self._detect_query_type(query_text),
                table_names=self._extract_table_names(query_text),
            )
            self.active_queries[query_id] = metric
            return metric

    def end_query(
        self,
        query_id: str,
        rows_returned: int = 0,
        cache_hit: bool = False,
        error: Optional[str] = None,
        memory_peak_mb: float = 0.0,
    ):
        """
        Mark query as completed and record metrics.

        Args:
            query_id: Query identifier
            rows_returned: Number of rows returned
            cache_hit: Whether result was from cache
            error: Error message if query failed
            memory_peak_mb: Peak memory usage
        """
        with self._lock:
            if query_id not in self.active_queries:
                logger.warning(f"Query {query_id} not found in active queries")
                return

            metric = self.active_queries.pop(query_id)
            metric.end_time = datetime.now()
            metric.execution_time = (
                metric.end_time - metric.start_time
            ).total_seconds() * 1000
            metric.rows_returned = rows_returned
            metric.cache_hit = cache_hit
            metric.error = error
            metric.memory_peak_mb = memory_peak_mb

            # Add to history
            self.query_history.append(metric)

            # Update statistics
            self.total_queries += 1
            self.total_execution_time += metric.execution_time
            self.total_rows += rows_returned
            if cache_hit:
                self.cache_hits += 1
            if error:
                self.errors += 1

            # Log slow queries
            if (
                self.log_slow_queries
                and metric.execution_time > self.slow_query_threshold_ms
            ):
                self._log_slow_query(metric)

            # Persist if configured
            if self.persist_to_file:
                self._persist_metric(metric)

    def _detect_query_type(self, query: str) -> str:
        """Detect the type of SQL query."""
        query_upper = query.strip().upper()

        if query_upper.startswith("SELECT"):
            return "SELECT"
        elif query_upper.startswith("INSERT"):
            return "INSERT"
        elif query_upper.startswith("UPDATE"):
            return "UPDATE"
        elif query_upper.startswith("DELETE"):
            return "DELETE"
        elif any(query_upper.startswith(cmd) for cmd in ["CREATE", "ALTER", "DROP"]):
            return "DDL"
        else:
            return "OTHER"

    def _extract_table_names(self, query: str) -> List[str]:
        """Extract table names from query (simple implementation)."""
        import re

        # Simple regex to find table names after FROM and JOIN
        tables = set()
        query_upper = query.upper()

        # Find tables after FROM
        from_matches = re.findall(r"FROM\s+(\w+)", query_upper)
        tables.update(from_matches)

        # Find tables after JOIN
        join_matches = re.findall(r"JOIN\s+(\w+)", query_upper)
        tables.update(join_matches)

        return list(tables)

    def _log_slow_query(self, metric: QueryMetric):
        """Log slow query details."""
        logger.warning(
            f"Slow query detected: {metric.execution_time:.0f}ms\n"
            f"Query: {metric.query_text[:200]}...\n"
            f"Rows: {metric.rows_returned}, Cache: {metric.cache_hit}"
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get aggregated statistics."""
        with self._lock:
            recent_queries = list(self.query_history)[-100:]  # Last 100 queries

            if recent_queries:
                recent_exec_times = [
                    q.execution_time for q in recent_queries if not q.cache_hit
                ]
                avg_exec_time = (
                    sum(recent_exec_times) / len(recent_exec_times)
                    if recent_exec_times
                    else 0
                )

                query_types = {}
                for q in recent_queries:
                    query_types[q.query_type] = query_types.get(q.query_type, 0) + 1
            else:
                avg_exec_time = 0
                query_types = {}

            return {
                "total_queries": self.total_queries,
                "total_execution_time_ms": self.total_execution_time,
                "avg_execution_time_ms": avg_exec_time,
                "total_rows": self.total_rows,
                "cache_hits": self.cache_hits,
                "cache_hit_rate": (
                    self.cache_hits / self.total_queries
                    if self.total_queries > 0
                    else 0
                ),
                "errors": self.errors,
                "error_rate": (
                    self.errors / self.total_queries if self.total_queries > 0 else 0
                ),
                "query_types": query_types,
                "active_queries": len(self.active_queries),
                "history_size": len(self.query_history),
            }

    def get_slow_queries(self, limit: int = 10) -> List[QueryMetric]:
        """Get the slowest queries."""
        with self._lock:
            queries = sorted(
                self.query_history, key=lambda q: q.execution_time, reverse=True
            )
            return queries[:limit]

    def get_recent_queries(self, limit: int = 10) -> List[QueryMetric]:
        """Get recent queries."""
        with self._lock:
            return list(self.query_history)[-limit:]

    def get_query_performance_by_table(self) -> Dict[str, Dict[str, Any]]:
        """Get performance statistics grouped by table."""
        with self._lock:
            table_stats = {}

            for metric in self.query_history:
                for table in metric.table_names:
                    if table not in table_stats:
                        table_stats[table] = {
                            "count": 0,
                            "total_time_ms": 0,
                            "avg_time_ms": 0,
                            "total_rows": 0,
                        }

                    stats = table_stats[table]
                    stats["count"] += 1
                    stats["total_time_ms"] += metric.execution_time
                    stats["total_rows"] += metric.rows_returned
                    stats["avg_time_ms"] = stats["total_time_ms"] / stats["count"]

            return table_stats

    def _persist_metric(self, metric: QueryMetric):
        """Persist metric to file."""
        if not self.persist_to_file:
            return

        try:
            with open(self.persist_to_file, "a") as f:
                f.write(json.dumps(metric.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"Failed to persist metric: {e}")

    def _load_persisted_metrics(self):
        """Load persisted metrics from file."""
        if not self.persist_to_file or not Path(self.persist_to_file).exists():
            return

        try:
            with open(self.persist_to_file, "r") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        metric = QueryMetric.from_dict(data)
                        self.query_history.append(metric)

                        # Update statistics
                        self.total_queries += 1
                        self.total_execution_time += metric.execution_time
                        self.total_rows += metric.rows_returned
                        if metric.cache_hit:
                            self.cache_hits += 1
                        if metric.error:
                            self.errors += 1
        except Exception as e:
            logger.error(f"Failed to load persisted metrics: {e}")

    def export_to_dataframe(self):
        """Export metrics to pandas DataFrame."""
        import pandas as pd

        with self._lock:
            data = [m.to_dict() for m in self.query_history]

        if data:
            return pd.DataFrame(data)
        return pd.DataFrame()


class QueryProfiler:
    """Profile query execution for detailed performance analysis."""

    def __init__(self):
        """Initialize profiler."""
        self.profiles: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def profile_query(self, query_id: str, query: str, connection) -> Dict[str, Any]:
        """
        Profile a query execution.

        Args:
            query_id: Unique query identifier
            query: SQL query to profile
            connection: Database connection

        Returns:
            Profile information
        """
        profile = {
            "query_id": query_id,
            "query": query[:500],
            "timestamp": datetime.now().isoformat(),
        }

        try:
            # Get query plan
            explain_result = connection.execute(f"EXPLAIN {query}")
            profile["query_plan"] = explain_result.fetchall()[0][1]

            # Get analyze plan (with timing)
            analyze_result = connection.execute(f"EXPLAIN ANALYZE {query}")
            profile["analyze_plan"] = analyze_result.fetchall()[0][1]

            # Parse timing information from analyze plan
            import re

            timing_match = re.search(r"Total Time: ([\d.]+)ms", profile["analyze_plan"])
            if timing_match:
                profile["execution_time_ms"] = float(timing_match.group(1))

            # Store profile
            with self._lock:
                self.profiles[query_id] = profile

        except Exception as e:
            logger.error(f"Failed to profile query: {e}")
            profile["error"] = str(e)

        return profile

    def get_profile(self, query_id: str) -> Optional[Dict[str, Any]]:
        """Get profile for a specific query."""
        with self._lock:
            return self.profiles.get(query_id)

    def get_optimization_suggestions(self, query_id: str) -> List[str]:
        """Get optimization suggestions based on profile."""
        profile = self.get_profile(query_id)
        if not profile or "analyze_plan" not in profile:
            return []

        suggestions = []
        plan = profile["analyze_plan"]

        # Check for full table scans
        if "FULL SCAN" in plan.upper():
            suggestions.append("Consider adding indexes to avoid full table scans")

        # Check for missing statistics
        if "NO STATISTICS" in plan.upper():
            suggestions.append("Update table statistics for better query planning")

        # Check for expensive operations
        if "SORT" in plan.upper() and "INDEX" not in plan.upper():
            suggestions.append("Consider adding indexes on ORDER BY columns")

        if "HASH JOIN" in plan.upper():
            suggestions.append(
                "Large hash joins detected - consider optimizing join conditions"
            )

        return suggestions


class SlowQueryLogger:
    """Specialized logger for slow queries."""

    def __init__(
        self,
        threshold_ms: float = 2000,
        log_file: Optional[str] = None,
        max_queries: int = 100,
    ):
        """
        Initialize slow query logger.

        Args:
            threshold_ms: Threshold for slow queries in milliseconds
            log_file: Optional file path for slow query log
            max_queries: Maximum number of slow queries to keep
        """
        self.threshold_ms = threshold_ms
        self.log_file = log_file
        self.max_queries = max_queries
        self.slow_queries: deque = deque(maxlen=max_queries)

        # Setup file logger if specified
        if log_file:
            self._setup_file_logger()

    def _setup_file_logger(self):
        """Setup file-based logging for slow queries."""
        handler = logging.FileHandler(self.log_file)
        handler.setLevel(logging.WARNING)
        formatter = logging.Formatter("%(asctime)s - SLOW_QUERY - %(message)s")
        handler.setFormatter(formatter)

        self.file_logger = logging.getLogger("slow_query")
        self.file_logger.addHandler(handler)
        self.file_logger.setLevel(logging.WARNING)

    def log_slow_query(
        self,
        query: str,
        execution_time_ms: float,
        rows: int = 0,
        additional_info: Optional[Dict[str, Any]] = None,
    ):
        """
        Log a slow query.

        Args:
            query: SQL query text
            execution_time_ms: Execution time in milliseconds
            rows: Number of rows returned
            additional_info: Additional information to log
        """
        if execution_time_ms < self.threshold_ms:
            return

        # Create log entry
        entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query[:500],  # Truncate long queries
            "execution_time_ms": execution_time_ms,
            "rows": rows,
            "threshold_ms": self.threshold_ms,
        }

        if additional_info:
            entry.update(additional_info)

        # Add to memory storage
        self.slow_queries.append(entry)

        # Log to file if configured
        if hasattr(self, "file_logger"):
            self.file_logger.warning(
                f"Execution: {execution_time_ms:.0f}ms, "
                f"Rows: {rows}, "
                f"Query: {query[:200]}"
            )

    def get_slow_queries(self) -> List[Dict[str, Any]]:
        """Get list of slow queries."""
        return list(self.slow_queries)

    def analyze_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in slow queries."""
        if not self.slow_queries:
            return {}

        # Analyze common patterns
        patterns = {
            "total_slow_queries": len(self.slow_queries),
            "avg_execution_time_ms": sum(
                q["execution_time_ms"] for q in self.slow_queries
            )
            / len(self.slow_queries),
            "max_execution_time_ms": max(
                q["execution_time_ms"] for q in self.slow_queries
            ),
            "common_operations": {},
        }

        # Count query types
        for query_info in self.slow_queries:
            query = query_info["query"].upper()
            if "JOIN" in query:
                patterns["common_operations"]["joins"] = (
                    patterns["common_operations"].get("joins", 0) + 1
                )
            if "GROUP BY" in query:
                patterns["common_operations"]["group_by"] = (
                    patterns["common_operations"].get("group_by", 0) + 1
                )
            if "ORDER BY" in query:
                patterns["common_operations"]["order_by"] = (
                    patterns["common_operations"].get("order_by", 0) + 1
                )

        return patterns
