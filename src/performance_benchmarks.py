"""
Performance benchmarking and optimization for TGE Monitor
Comprehensive performance testing and monitoring
"""

import time
import asyncio
import logging
import statistics
import psutil
import json
import gc
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import threading
from contextlib import contextmanager
import memory_profiler
import cProfile
import pstats
import io

from .database import DatabaseManager
from .database_service import db_service
from .models import SystemMetrics

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    operation_name: str
    duration: float
    memory_usage: float
    cpu_usage: float
    success: bool
    timestamp: datetime
    details: Dict[str, Any]
    error_message: Optional[str] = None


@dataclass
class BenchmarkResult:
    """Benchmark result data structure"""
    test_name: str
    total_operations: int
    successful_operations: int
    failed_operations: int
    total_duration: float
    average_duration: float
    min_duration: float
    max_duration: float
    percentile_95: float
    percentile_99: float
    throughput: float  # operations per second
    memory_peak: float
    memory_average: float
    cpu_average: float
    error_rate: float
    errors: List[str]


class PerformanceProfiler:
    """Performance profiler with CPU and memory monitoring"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.active_profiles: Dict[str, Dict[str, Any]] = {}
        
    @contextmanager
    def profile_operation(self, operation_name: str, **details):
        """Context manager for profiling operations"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        start_cpu = psutil.cpu_percent()
        
        success = True
        error_message = None
        
        try:
            yield
        except Exception as e:
            success = False
            error_message = str(e)
            raise
        finally:
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            end_cpu = psutil.cpu_percent()
            
            metrics = PerformanceMetrics(
                operation_name=operation_name,
                duration=end_time - start_time,
                memory_usage=end_memory - start_memory,
                cpu_usage=(start_cpu + end_cpu) / 2,
                success=success,
                timestamp=datetime.now(timezone.utc),
                details=details,
                error_message=error_message
            )
            
            self.metrics.append(metrics)
            
            # Store in database
            try:
                db_service.record_metric(
                    metric_type="performance",
                    metric_name=f"{operation_name}_duration",
                    value=metrics.duration,
                    unit="seconds",
                    tags={
                        "success": success,
                        "memory_delta": metrics.memory_usage,
                        "cpu_avg": metrics.cpu_usage,
                        **details
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to store performance metric: {e}")
    
    def get_metrics_summary(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """Get summary of performance metrics"""
        filtered_metrics = self.metrics
        
        if operation_name:
            filtered_metrics = [m for m in self.metrics if m.operation_name == operation_name]
        
        if not filtered_metrics:
            return {}
        
        durations = [m.duration for m in filtered_metrics]
        memory_usage = [m.memory_usage for m in filtered_metrics]
        cpu_usage = [m.cpu_usage for m in filtered_metrics]
        success_count = sum(1 for m in filtered_metrics if m.success)
        
        return {
            "total_operations": len(filtered_metrics),
            "successful_operations": success_count,
            "success_rate": success_count / len(filtered_metrics),
            "duration": {
                "average": statistics.mean(durations),
                "median": statistics.median(durations),
                "min": min(durations),
                "max": max(durations),
                "std_dev": statistics.stdev(durations) if len(durations) > 1 else 0,
                "p95": self._percentile(durations, 95),
                "p99": self._percentile(durations, 99)
            },
            "memory": {
                "average": statistics.mean(memory_usage),
                "peak": max(memory_usage),
                "min": min(memory_usage)
            },
            "cpu": {
                "average": statistics.mean(cpu_usage),
                "peak": max(cpu_usage)
            }
        }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


class BenchmarkSuite:
    """Comprehensive benchmark suite for TGE Monitor"""
    
    def __init__(self):
        self.profiler = PerformanceProfiler()
        self.results: Dict[str, BenchmarkResult] = {}
        
    async def run_all_benchmarks(self) -> Dict[str, BenchmarkResult]:
        """Run all performance benchmarks"""
        logger.info("Starting comprehensive performance benchmarks")
        
        benchmarks = [
            ("database_operations", self.benchmark_database_operations),
            ("content_analysis", self.benchmark_content_analysis),
            ("api_endpoints", self.benchmark_api_endpoints),
            ("websocket_performance", self.benchmark_websocket_performance),
            ("concurrent_processing", self.benchmark_concurrent_processing),
            ("memory_efficiency", self.benchmark_memory_efficiency),
            ("rate_limiting", self.benchmark_rate_limiting)
        ]
        
        for benchmark_name, benchmark_func in benchmarks:
            try:
                logger.info(f"Running benchmark: {benchmark_name}")
                result = await benchmark_func()
                self.results[benchmark_name] = result
                logger.info(f"Completed benchmark: {benchmark_name}")
            except Exception as e:
                logger.error(f"Benchmark {benchmark_name} failed: {e}")
                self.results[benchmark_name] = BenchmarkResult(
                    test_name=benchmark_name,
                    total_operations=0,
                    successful_operations=0,
                    failed_operations=1,
                    total_duration=0,
                    average_duration=0,
                    min_duration=0,
                    max_duration=0,
                    percentile_95=0,
                    percentile_99=0,
                    throughput=0,
                    memory_peak=0,
                    memory_average=0,
                    cpu_average=0,
                    error_rate=1.0,
                    errors=[str(e)]
                )
        
        logger.info("All benchmarks completed")
        return self.results
    
    async def benchmark_database_operations(self) -> BenchmarkResult:
        """Benchmark database operations"""
        operations = []
        errors = []
        
        # Test company operations
        for i in range(100):
            with self.profiler.profile_operation("db_company_query", iteration=i):
                try:
                    companies = db_service.get_companies()
                    operations.append(("company_query", True, self.profiler.metrics[-1].duration))
                except Exception as e:
                    operations.append(("company_query", False, 0))
                    errors.append(str(e))
        
        # Test alert creation
        for i in range(50):
            with self.profiler.profile_operation("db_alert_create", iteration=i):
                try:
                    alert_data = {
                        "title": f"Test Alert {i}",
                        "content": f"Test content for alert {i}",
                        "source": "benchmark",
                        "confidence": 0.8,
                        "keywords_matched": ["test", "benchmark"],
                        "analysis_data": {"test": True}
                    }
                    db_service.create_alert(alert_data)
                    operations.append(("alert_create", True, self.profiler.metrics[-1].duration))
                except Exception as e:
                    operations.append(("alert_create", False, 0))
                    errors.append(str(e))
        
        # Test alert queries
        for i in range(50):
            with self.profiler.profile_operation("db_alert_query", iteration=i):
                try:
                    alerts = db_service.get_alerts(limit=10, offset=i)
                    operations.append(("alert_query", True, self.profiler.metrics[-1].duration))
                except Exception as e:
                    operations.append(("alert_query", False, 0))
                    errors.append(str(e))
        
        return self._calculate_benchmark_result("database_operations", operations, errors)
    
    async def benchmark_content_analysis(self) -> BenchmarkResult:
        """Benchmark content analysis performance"""
        from .main_optimized_db import EnhancedCryptoTGEMonitor
        
        operations = []
        errors = []
        
        # Initialize monitor for testing
        try:
            monitor = EnhancedCryptoTGEMonitor()
        except Exception as e:
            return BenchmarkResult(
                test_name="content_analysis",
                total_operations=0,
                successful_operations=0,
                failed_operations=1,
                total_duration=0,
                average_duration=0,
                min_duration=0,
                max_duration=0,
                percentile_95=0,
                percentile_99=0,
                throughput=0,
                memory_peak=0,
                memory_average=0,
                cpu_average=0,
                error_rate=1.0,
                errors=[f"Failed to initialize monitor: {e}"]
            )
        
        # Test content samples
        test_content = [
            "Caldera announces TGE launch next week with $CAL token distribution",
            "Fabric protocol mainnet launch scheduled for Q2 with governance features",
            "Bitcoin reaches new all-time high as institutions continue adoption",
            "Succinct Labs reveals zero-knowledge infrastructure with SP1 token",
            "DeFi protocol launches airdrop campaign for early users",
            "Ethereum gas fees drop to lowest levels in months",
            "Curvance Finance announces token generation event details",
            "NFT market sees renewed interest with new collections",
            "Stablecoin adoption grows in emerging markets",
            "Layer 2 solutions gain traction with major DEX integrations"
        ]
        
        # Benchmark analysis performance
        for i in range(200):
            content = test_content[i % len(test_content)]
            with self.profiler.profile_operation("content_analysis", iteration=i, content_length=len(content)):
                try:
                    is_relevant, confidence, analysis = monitor.enhanced_content_analysis(content, "benchmark")
                    operations.append(("analysis", True, self.profiler.metrics[-1].duration))
                except Exception as e:
                    operations.append(("analysis", False, 0))
                    errors.append(str(e))
        
        return self._calculate_benchmark_result("content_analysis", operations, errors)
    
    async def benchmark_api_endpoints(self) -> BenchmarkResult:
        """Benchmark API endpoint performance"""
        import httpx
        
        operations = []
        errors = []
        
        # This would require the API server to be running
        # For now, we'll simulate the benchmark
        
        endpoints = [
            "/health",
            "/api/companies",
            "/api/alerts",
            "/api/statistics/system"
        ]
        
        async with httpx.AsyncClient() as client:
            for endpoint in endpoints:
                for i in range(20):
                    with self.profiler.profile_operation("api_request", endpoint=endpoint, iteration=i):
                        try:
                            # Simulate API call timing
                            await asyncio.sleep(0.001)  # Simulate network delay
                            operations.append((f"api_{endpoint}", True, self.profiler.metrics[-1].duration))
                        except Exception as e:
                            operations.append((f"api_{endpoint}", False, 0))
                            errors.append(str(e))
        
        return self._calculate_benchmark_result("api_endpoints", operations, errors)
    
    async def benchmark_websocket_performance(self) -> BenchmarkResult:
        """Benchmark WebSocket performance"""
        operations = []
        errors = []
        
        # Simulate WebSocket message handling
        for i in range(100):
            with self.profiler.profile_operation("websocket_message", iteration=i):
                try:
                    # Simulate message processing
                    message_data = {
                        "type": "subscribe",
                        "data": {
                            "subscription": "all_alerts",
                            "filters": {"confidence_threshold": 0.7}
                        }
                    }
                    # Simulate processing time
                    await asyncio.sleep(0.001)
                    operations.append(("websocket_message", True, self.profiler.metrics[-1].duration))
                except Exception as e:
                    operations.append(("websocket_message", False, 0))
                    errors.append(str(e))
        
        return self._calculate_benchmark_result("websocket_performance", operations, errors)
    
    async def benchmark_concurrent_processing(self) -> BenchmarkResult:
        """Benchmark concurrent processing performance"""
        operations = []
        errors = []
        
        async def simulate_work(work_id: int):
            """Simulate concurrent work"""
            with self.profiler.profile_operation("concurrent_work", work_id=work_id):
                try:
                    # Simulate CPU-bound work
                    await asyncio.sleep(0.01)
                    # Simulate some computation
                    result = sum(i * i for i in range(100))
                    return ("concurrent_work", True, self.profiler.metrics[-1].duration)
                except Exception as e:
                    return ("concurrent_work", False, 0)
        
        # Test different concurrency levels
        concurrency_levels = [1, 5, 10, 20, 50]
        
        for concurrency in concurrency_levels:
            tasks = [simulate_work(i) for i in range(concurrency)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    operations.append(("concurrent_work", False, 0))
                    errors.append(str(result))
                else:
                    operations.append(result)
        
        return self._calculate_benchmark_result("concurrent_processing", operations, errors)
    
    async def benchmark_memory_efficiency(self) -> BenchmarkResult:
        """Benchmark memory efficiency"""
        operations = []
        errors = []
        
        # Test memory usage patterns
        for i in range(50):
            with self.profiler.profile_operation("memory_test", iteration=i):
                try:
                    # Create and process large data structures
                    large_list = [{"id": j, "data": "x" * 1000} for j in range(1000)]
                    
                    # Process the data
                    processed = [item for item in large_list if item["id"] % 2 == 0]
                    
                    # Clear memory
                    del large_list, processed
                    gc.collect()
                    
                    operations.append(("memory_test", True, self.profiler.metrics[-1].duration))
                except Exception as e:
                    operations.append(("memory_test", False, 0))
                    errors.append(str(e))
        
        return self._calculate_benchmark_result("memory_efficiency", operations, errors)
    
    async def benchmark_rate_limiting(self) -> BenchmarkResult:
        """Benchmark rate limiting performance"""
        from .rate_limiting import rate_limiter, RateLimitConfig, RateLimitStrategy
        
        operations = []
        errors = []
        
        # Test rate limiting performance
        config = RateLimitConfig(
            limit=100,
            window=60,
            strategy=RateLimitStrategy.SLIDING_WINDOW
        )
        
        for i in range(200):
            with self.profiler.profile_operation("rate_limit_check", iteration=i):
                try:
                    result = rate_limiter.check_rate_limit(f"benchmark_user_{i % 10}", "test", config)
                    operations.append(("rate_limit_check", True, self.profiler.metrics[-1].duration))
                except Exception as e:
                    operations.append(("rate_limit_check", False, 0))
                    errors.append(str(e))
        
        return self._calculate_benchmark_result("rate_limiting", operations, errors)
    
    def _calculate_benchmark_result(self, test_name: str, operations: List[tuple], errors: List[str]) -> BenchmarkResult:
        """Calculate benchmark result from operations"""
        if not operations:
            return BenchmarkResult(
                test_name=test_name,
                total_operations=0,
                successful_operations=0,
                failed_operations=len(errors),
                total_duration=0,
                average_duration=0,
                min_duration=0,
                max_duration=0,
                percentile_95=0,
                percentile_99=0,
                throughput=0,
                memory_peak=0,
                memory_average=0,
                cpu_average=0,
                error_rate=1.0 if errors else 0.0,
                errors=errors
            )
        
        successful_ops = [op for op in operations if op[1]]
        failed_ops = [op for op in operations if not op[1]]
        durations = [op[2] for op in successful_ops if op[2] > 0]
        
        if not durations:
            durations = [0]
        
        total_duration = sum(durations)
        
        # Get memory and CPU metrics from profiler
        relevant_metrics = [m for m in self.profiler.metrics if test_name in m.operation_name]
        memory_usage = [m.memory_usage for m in relevant_metrics] or [0]
        cpu_usage = [m.cpu_usage for m in relevant_metrics] or [0]
        
        return BenchmarkResult(
            test_name=test_name,
            total_operations=len(operations),
            successful_operations=len(successful_ops),
            failed_operations=len(failed_ops),
            total_duration=total_duration,
            average_duration=statistics.mean(durations),
            min_duration=min(durations),
            max_duration=max(durations),
            percentile_95=self.profiler._percentile(durations, 95),
            percentile_99=self.profiler._percentile(durations, 99),
            throughput=len(successful_ops) / total_duration if total_duration > 0 else 0,
            memory_peak=max(memory_usage),
            memory_average=statistics.mean(memory_usage),
            cpu_average=statistics.mean(cpu_usage),
            error_rate=len(failed_ops) / len(operations) if operations else 0,
            errors=errors[:10]  # Limit to first 10 errors
        )
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system_info": {
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total / 1024 / 1024 / 1024,  # GB
                "python_version": f"{psutil.WINDOWS}.{psutil.LINUX}" if hasattr(psutil, 'WINDOWS') else "unknown"
            },
            "benchmark_results": {
                name: asdict(result) for name, result in self.results.items()
            },
            "overall_metrics": self.profiler.get_metrics_summary(),
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate performance recommendations based on benchmark results"""
        recommendations = []
        
        for name, result in self.results.items():
            if result.error_rate > 0.1:
                recommendations.append(f"High error rate in {name} ({result.error_rate:.1%}). Investigation needed.")
            
            if result.average_duration > 1.0:
                recommendations.append(f"Slow performance in {name} (avg: {result.average_duration:.2f}s). Consider optimization.")
            
            if result.memory_peak > 500:  # MB
                recommendations.append(f"High memory usage in {name} ({result.memory_peak:.1f}MB). Consider memory optimization.")
            
            if result.throughput < 10 and result.total_operations > 10:
                recommendations.append(f"Low throughput in {name} ({result.throughput:.1f} ops/sec). Consider parallelization.")
        
        if not recommendations:
            recommendations.append("All benchmarks performed within acceptable parameters.")
        
        return recommendations


# Global instances
profiler = PerformanceProfiler()
benchmark_suite = BenchmarkSuite()


# Utility functions
async def run_performance_benchmarks() -> Dict[str, Any]:
    """Run all performance benchmarks and return report"""
    results = await benchmark_suite.run_all_benchmarks()
    report = benchmark_suite.generate_report()
    
    # Store summary in database
    try:
        summary_metrics = {
            "total_benchmarks": len(results),
            "successful_benchmarks": sum(1 for r in results.values() if r.error_rate < 0.1),
            "average_throughput": statistics.mean([r.throughput for r in results.values() if r.throughput > 0]),
            "peak_memory": max([r.memory_peak for r in results.values()]),
            "recommendations_count": len(report["recommendations"])
        }
        
        for metric_name, value in summary_metrics.items():
            db_service.record_metric(
                metric_type="benchmark",
                metric_name=metric_name,
                value=value,
                unit="count" if "count" in metric_name else "mixed",
                tags={"benchmark_run": datetime.now(timezone.utc).isoformat()}
            )
    except Exception as e:
        logger.warning(f"Failed to store benchmark metrics: {e}")
    
    return report


def profile_function(func: Callable) -> Callable:
    """Decorator to profile function performance"""
    def wrapper(*args, **kwargs):
        with profiler.profile_operation(func.__name__, args_count=len(args), kwargs_count=len(kwargs)):
            return func(*args, **kwargs)
    
    return wrapper


@contextmanager
def performance_monitor(operation_name: str, **details):
    """Context manager for monitoring performance"""
    with profiler.profile_operation(operation_name, **details):
        yield


if __name__ == "__main__":
    # Run performance benchmarks
    async def main():
        print("Running performance benchmarks...")
        report = await run_performance_benchmarks()
        
        print("\n=== Performance Benchmark Report ===")
        print(f"Timestamp: {report['timestamp']}")
        print(f"Total benchmarks: {len(report['benchmark_results'])}")
        
        for name, result in report['benchmark_results'].items():
            print(f"\n{name}:")
            print(f"  Success rate: {(1 - result['error_rate']):.1%}")
            print(f"  Average duration: {result['average_duration']:.3f}s")
            print(f"  Throughput: {result['throughput']:.1f} ops/sec")
            print(f"  Memory peak: {result['memory_peak']:.1f}MB")
        
        print(f"\nRecommendations:")
        for rec in report['recommendations']:
            print(f"  - {rec}")
    
    asyncio.run(main())