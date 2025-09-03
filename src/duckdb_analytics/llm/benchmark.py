"""Benchmarking and testing suite for LLM context loading performance."""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Tuple

import duckdb
import pandas as pd

from .context_manager import ContextWindowManager
from .enhanced_sql_generator import EnhancedSQLGenerator
from .optimized_context_manager import OptimizedContextManager
from .optimized_schema_extractor import OptimizedSchemaExtractor
from .schema_extractor import SchemaExtractor
from .sql_generator import SQLGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerformanceBenchmark:
    """Benchmark suite for LLM context loading performance."""
    
    def __init__(self, duckdb_conn):
        """Initialize benchmark suite."""
        self.conn = duckdb_conn
        self.results = []
        self.test_queries = [
            "Show all customers",
            "Count total orders by month",
            "Find products with price over 100",
            "Calculate average order value by customer",
            "Show top 10 customers by revenue",
            "Find orders with multiple products",
            "Show inventory levels by category",
            "Calculate year-over-year growth",
            "Find customers who haven't ordered recently",
            "Show product sales trends over time"
        ]
    
    def setup_test_database(self):
        """Create test database with sample tables."""
        logger.info("Setting up test database...")
        
        # Create sample tables
        queries = [
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY,
                name VARCHAR,
                email VARCHAR,
                created_at TIMESTAMP,
                country VARCHAR,
                segment VARCHAR
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                name VARCHAR,
                category VARCHAR,
                price DECIMAL(10,2),
                cost DECIMAL(10,2),
                stock_quantity INTEGER
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                order_date DATE,
                status VARCHAR,
                total_amount DECIMAL(10,2),
                shipping_address VARCHAR
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY,
                order_id INTEGER,
                product_id INTEGER,
                quantity INTEGER,
                unit_price DECIMAL(10,2),
                discount DECIMAL(5,2)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY,
                product_id INTEGER,
                warehouse_id INTEGER,
                quantity INTEGER,
                last_updated TIMESTAMP
            )
            """
        ]
        
        for query in queries:
            self.conn.execute(query)
        
        # Insert sample data
        logger.info("Inserting sample data...")
        
        # Customers
        self.conn.execute("""
            INSERT INTO customers SELECT 
                rowid as id,
                'Customer ' || rowid as name,
                'customer' || rowid || '@example.com' as email,
                NOW() - INTERVAL (rowid || ' days') as created_at,
                CASE (rowid % 5)
                    WHEN 0 THEN 'USA'
                    WHEN 1 THEN 'UK'
                    WHEN 2 THEN 'Germany'
                    WHEN 3 THEN 'France'
                    ELSE 'Japan'
                END as country,
                CASE (rowid % 3)
                    WHEN 0 THEN 'Enterprise'
                    WHEN 1 THEN 'SMB'
                    ELSE 'Consumer'
                END as segment
            FROM generate_series(1, 1000) as g(rowid)
        """)
        
        # Products
        self.conn.execute("""
            INSERT INTO products SELECT
                rowid as id,
                'Product ' || rowid as name,
                CASE (rowid % 4)
                    WHEN 0 THEN 'Electronics'
                    WHEN 1 THEN 'Clothing'
                    WHEN 2 THEN 'Books'
                    ELSE 'Food'
                END as category,
                (rowid * 10 + random() * 100)::DECIMAL(10,2) as price,
                (rowid * 5 + random() * 50)::DECIMAL(10,2) as cost,
                (random() * 1000)::INTEGER as stock_quantity
            FROM generate_series(1, 500) as g(rowid)
        """)
        
        # Orders
        self.conn.execute("""
            INSERT INTO orders SELECT
                rowid as id,
                (random() * 1000 + 1)::INTEGER as customer_id,
                DATE '2024-01-01' + INTERVAL (rowid % 365 || ' days') as order_date,
                CASE (rowid % 4)
                    WHEN 0 THEN 'completed'
                    WHEN 1 THEN 'processing'
                    WHEN 2 THEN 'shipped'
                    ELSE 'pending'
                END as status,
                (random() * 1000 + 50)::DECIMAL(10,2) as total_amount,
                'Address ' || rowid as shipping_address
            FROM generate_series(1, 5000) as g(rowid)
        """)
        
        logger.info("Test database setup complete")
    
    def benchmark_schema_extraction(self) -> Dict:
        """Benchmark schema extraction performance."""
        logger.info("Benchmarking schema extraction...")
        results = {}
        
        # Benchmark original extractor
        logger.info("Testing original schema extractor...")
        original_extractor = SchemaExtractor(self.conn)
        
        start_time = time.perf_counter()
        original_schema = original_extractor.get_schema(force_refresh=True)
        original_time = time.perf_counter() - start_time
        
        results["original"] = {
            "time": original_time,
            "tables": len(original_schema),
            "cached": False
        }
        
        # Test cached performance
        start_time = time.perf_counter()
        cached_schema = original_extractor.get_schema()
        cached_time = time.perf_counter() - start_time
        
        results["original_cached"] = {
            "time": cached_time,
            "tables": len(cached_schema),
            "cached": True
        }
        
        # Benchmark optimized extractor
        logger.info("Testing optimized schema extractor...")
        optimized_extractor = OptimizedSchemaExtractor(self.conn)
        
        start_time = time.perf_counter()
        optimized_schema = optimized_extractor.extract_schema_optimized(force_refresh=True)
        optimized_time = time.perf_counter() - start_time
        
        results["optimized"] = {
            "time": optimized_time,
            "tables": len(optimized_schema),
            "cached": False
        }
        
        # Test optimized cached performance
        start_time = time.perf_counter()
        optimized_cached = optimized_extractor.extract_schema_optimized()
        optimized_cached_time = time.perf_counter() - start_time
        
        results["optimized_cached"] = {
            "time": optimized_cached_time,
            "tables": len(optimized_cached),
            "cached": True
        }
        
        # Calculate improvements
        results["improvement"] = {
            "extraction": f"{((original_time - optimized_time) / original_time * 100):.1f}%",
            "cached": f"{((cached_time - optimized_cached_time) / cached_time * 100):.1f}%"
        }
        
        return results
    
    def benchmark_context_building(self) -> Dict:
        """Benchmark context building performance."""
        logger.info("Benchmarking context building...")
        results = {}
        
        # Get schema for testing
        schema_extractor = OptimizedSchemaExtractor(self.conn)
        schema = schema_extractor.extract_schema_optimized()
        
        # Convert to format expected by original context manager
        schema_dict = {}
        for table_name, table_schema in schema.items():
            schema_dict[table_name] = table_schema
        
        # Benchmark original context manager
        logger.info("Testing original context manager...")
        original_manager = ContextWindowManager()
        
        times = []
        for query in self.test_queries[:5]:  # Test subset
            start_time = time.perf_counter()
            
            # Original prioritization
            prioritized = original_manager.prioritize_tables(query, schema_dict)
            
            # Build prompt
            prompt, metadata = original_manager.build_dynamic_prompt(
                SQL_SYSTEM_PROMPT,
                query,
                "schema context placeholder"
            )
            
            elapsed = time.perf_counter() - start_time
            times.append(elapsed)
        
        results["original"] = {
            "avg_time": sum(times) / len(times),
            "min_time": min(times),
            "max_time": max(times)
        }
        
        # Benchmark optimized context manager
        logger.info("Testing optimized context manager...")
        optimized_manager = OptimizedContextManager()
        optimized_manager.build_indexes(schema)
        
        times = []
        for query in self.test_queries[:5]:
            start_time = time.perf_counter()
            
            # Optimized context building
            prompt, metadata = optimized_manager.build_optimized_context(
                query,
                schema,
                SQL_SYSTEM_PROMPT,
                "standard"
            )
            
            elapsed = time.perf_counter() - start_time
            times.append(elapsed)
        
        results["optimized"] = {
            "avg_time": sum(times) / len(times),
            "min_time": min(times),
            "max_time": max(times)
        }
        
        # Calculate improvement
        avg_improvement = (
            (results["original"]["avg_time"] - results["optimized"]["avg_time"]) 
            / results["original"]["avg_time"] * 100
        )
        results["improvement"] = f"{avg_improvement:.1f}%"
        
        return results
    
    def benchmark_end_to_end(self) -> Dict:
        """Benchmark end-to-end SQL generation."""
        logger.info("Benchmarking end-to-end SQL generation...")
        results = {}
        
        # Note: This requires LM Studio to be running
        try:
            # Test enhanced generator
            logger.info("Testing enhanced SQL generator...")
            enhanced_gen = EnhancedSQLGenerator(
                self.conn,
                warm_cache=True
            )
            
            if not enhanced_gen.is_available():
                logger.warning("LM Studio not available, skipping LLM benchmarks")
                return {"error": "LM Studio not available"}
            
            times = []
            cache_hits = 0
            
            for query in self.test_queries:
                sql, metadata = enhanced_gen.generate_sql(
                    query,
                    return_metrics=True
                )
                
                if metadata.get("cache_hit"):
                    cache_hits += 1
                
                times.append(metadata.get("generation_time", 0))
            
            results["enhanced"] = {
                "avg_time": sum(times) / len(times) if times else 0,
                "cache_hits": cache_hits,
                "queries_tested": len(self.test_queries)
            }
            
            # Get performance report
            perf_report = enhanced_gen.get_performance_report()
            results["performance_report"] = perf_report
            
        except Exception as e:
            logger.error(f"End-to-end benchmark failed: {e}")
            results["error"] = str(e)
        
        return results
    
    def run_all_benchmarks(self) -> Dict:
        """Run all benchmarks and generate report."""
        logger.info("Starting comprehensive benchmark suite...")
        
        # Setup test database
        self.setup_test_database()
        
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "benchmarks": {}
        }
        
        # Run benchmarks
        report["benchmarks"]["schema_extraction"] = self.benchmark_schema_extraction()
        report["benchmarks"]["context_building"] = self.benchmark_context_building()
        report["benchmarks"]["end_to_end"] = self.benchmark_end_to_end()
        
        # Generate summary
        report["summary"] = self._generate_summary(report["benchmarks"])
        
        return report
    
    def _generate_summary(self, benchmarks: Dict) -> Dict:
        """Generate benchmark summary."""
        summary = {
            "schema_extraction": {
                "improvement": benchmarks["schema_extraction"].get("improvement", {})
            },
            "context_building": {
                "improvement": benchmarks["context_building"].get("improvement", "N/A")
            }
        }
        
        # Overall assessment
        improvements = []
        if "extraction" in benchmarks["schema_extraction"].get("improvement", {}):
            imp = benchmarks["schema_extraction"]["improvement"]["extraction"]
            improvements.append(f"Schema extraction: {imp}")
        
        if "improvement" in benchmarks["context_building"]:
            imp = benchmarks["context_building"]["improvement"]
            improvements.append(f"Context building: {imp}")
        
        summary["overall"] = " | ".join(improvements) if improvements else "No improvements measured"
        
        return summary
    
    def save_report(self, report: Dict, filepath: str = "benchmark_report.json"):
        """Save benchmark report to file."""
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Report saved to {filepath}")


def run_benchmark():
    """Run the benchmark suite."""
    # Create in-memory database for testing
    conn = duckdb.connect(":memory:")
    
    # Run benchmarks
    benchmark = PerformanceBenchmark(conn)
    report = benchmark.run_all_benchmarks()
    
    # Print summary
    print("\n" + "="*50)
    print("BENCHMARK RESULTS")
    print("="*50)
    
    print("\n📊 Schema Extraction:")
    schema_results = report["benchmarks"]["schema_extraction"]
    print(f"  Original: {schema_results['original']['time']:.3f}s")
    print(f"  Optimized: {schema_results['optimized']['time']:.3f}s")
    print(f"  Improvement: {schema_results['improvement']['extraction']}")
    
    print("\n🎯 Context Building:")
    context_results = report["benchmarks"]["context_building"]
    print(f"  Original avg: {context_results['original']['avg_time']:.3f}s")
    print(f"  Optimized avg: {context_results['optimized']['avg_time']:.3f}s")
    print(f"  Improvement: {context_results['improvement']}")
    
    if "enhanced" in report["benchmarks"].get("end_to_end", {}):
        print("\n🚀 End-to-End Generation:")
        e2e_results = report["benchmarks"]["end_to_end"]["enhanced"]
        print(f"  Avg generation time: {e2e_results['avg_time']:.3f}s")
        print(f"  Cache hits: {e2e_results['cache_hits']}/{e2e_results['queries_tested']}")
    
    print("\n" + "="*50)
    print(f"Overall: {report['summary']['overall']}")
    print("="*50)
    
    # Save detailed report
    benchmark.save_report(report)
    
    return report


if __name__ == "__main__":
    run_benchmark()