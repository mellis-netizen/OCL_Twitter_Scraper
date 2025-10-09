#!/usr/bin/env python3
"""
Performance Benchmark Script for TGE Swarm Optimizations
Validates performance improvements and generates comparison reports
"""

import asyncio
import time
import statistics
import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any
import concurrent.futures
from dataclasses import dataclass
import uuid

# Import both original and optimized components
from backend.message_queue import create_message_queue as create_original_queue
from backend.optimized_message_queue import create_optimized_message_queue
from backend.message_queue import SwarmMessage, MessageType, Priority, TaskDefinition
from backend.performance.monitoring import PerformanceMonitor, PerformanceThresholds
from backend.performance.profiler import PerformanceProfiler


@dataclass
class BenchmarkResult:
    """Benchmark test result"""
    test_name: str
    implementation: str  # 'original' or 'optimized'
    operation_count: int
    total_time: float
    operations_per_second: float
    avg_latency: float
    min_latency: float
    max_latency: float
    p95_latency: float
    memory_usage_mb: float
    success_rate: float
    errors: int


class PerformanceBenchmark:
    """Comprehensive performance benchmark suite"""
    
    def __init__(self):
        self.redis_urls = ["localhost:6379"]
        self.cluster_name = "benchmark-test"
        self.results: List[BenchmarkResult] = []
        
        # Performance monitoring
        self.monitor = PerformanceMonitor(
            thresholds=PerformanceThresholds(
                cpu_warning=80.0,
                memory_warning=80.0
            )
        )
        
        self.profiler = PerformanceProfiler()
        
        print("Performance Benchmark Suite for TGE Swarm")
        print("=" * 50)
    
    async def initialize(self):
        """Initialize benchmark environment"""
        await self.monitor.initialize()
        await self.profiler.initialize()
        print("✓ Benchmark environment initialized")
    
    async def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run complete benchmark suite"""
        print("\nRunning comprehensive performance benchmarks...")
        
        # Message publishing benchmarks
        await self.benchmark_message_publishing()
        
        # Task queue benchmarks
        await self.benchmark_task_queuing()
        
        # Concurrent operations benchmarks
        await self.benchmark_concurrent_operations()
        
        # Memory efficiency benchmarks
        await self.benchmark_memory_efficiency()
        
        # Sustained load benchmarks
        await self.benchmark_sustained_load()
        
        # Generate comparison report
        return self.generate_comparison_report()
    
    async def benchmark_message_publishing(self):
        """Benchmark message publishing performance"""
        print("\n1. Message Publishing Benchmark")
        print("-" * 30)
        
        test_configs = [
            {"count": 100, "name": "Small Load"},
            {"count": 1000, "name": "Medium Load"},
            {"count": 5000, "name": "Large Load"}
        ]
        
        for config in test_configs:
            print(f"\nTesting {config['name']} ({config['count']} messages)")
            
            # Test original implementation
            original_result = await self._test_message_publishing_original(
                config['count'], f"message_publish_{config['name'].lower().replace(' ', '_')}"
            )
            self.results.append(original_result)
            
            # Test optimized implementation
            optimized_result = await self._test_message_publishing_optimized(
                config['count'], f"message_publish_{config['name'].lower().replace(' ', '_')}"
            )
            self.results.append(optimized_result)
            
            # Print comparison
            improvement = (optimized_result.operations_per_second / original_result.operations_per_second - 1) * 100
            print(f"  Original:  {original_result.operations_per_second:.1f} ops/sec")
            print(f"  Optimized: {optimized_result.operations_per_second:.1f} ops/sec")
            print(f"  Improvement: {improvement:.1f}%")
    
    async def _test_message_publishing_original(self, count: int, test_name: str) -> BenchmarkResult:
        """Test original message publishing implementation"""
        queue = await create_original_queue(self.redis_urls, f"{self.cluster_name}_orig")
        
        try:
            messages = [
                SwarmMessage(
                    id=f"bench-msg-{i}",
                    type=MessageType.STATUS_UPDATE,
                    sender=f"benchmark-agent-{i % 10}",
                    recipient=None,
                    timestamp=datetime.now(),
                    payload={"index": i, "data": "x" * 100},
                    priority=Priority.MEDIUM
                )
                for i in range(count)
            ]
            
            # Measure memory before
            import psutil
            process = psutil.Process()
            memory_before = process.memory_info().rss / 1024 / 1024
            
            # Time the operations
            latencies = []
            errors = 0
            
            start_time = time.time()
            
            for message in messages:
                op_start = time.time()
                try:
                    success = await queue.publish_message(message)
                    if not success:
                        errors += 1
                except Exception:
                    errors += 1
                
                latencies.append(time.time() - op_start)
            
            total_time = time.time() - start_time
            
            # Measure memory after
            memory_after = process.memory_info().rss / 1024 / 1024
            memory_used = memory_after - memory_before
            
            return BenchmarkResult(
                test_name=test_name,
                implementation="original",
                operation_count=count,
                total_time=total_time,
                operations_per_second=count / total_time,
                avg_latency=statistics.mean(latencies),
                min_latency=min(latencies),
                max_latency=max(latencies),
                p95_latency=statistics.quantiles(latencies, n=20)[18] if len(latencies) > 5 else max(latencies),
                memory_usage_mb=memory_used,
                success_rate=(count - errors) / count,
                errors=errors
            )
        
        finally:
            await queue.shutdown()
    
    async def _test_message_publishing_optimized(self, count: int, test_name: str) -> BenchmarkResult:
        """Test optimized message publishing implementation"""
        queue = await create_optimized_message_queue(self.redis_urls, f"{self.cluster_name}_opt")
        
        try:
            messages = [
                SwarmMessage(
                    id=f"bench-msg-opt-{i}",
                    type=MessageType.STATUS_UPDATE,
                    sender=f"benchmark-agent-{i % 10}",
                    recipient=None,
                    timestamp=datetime.now(),
                    payload={"index": i, "data": "x" * 100},
                    priority=Priority.MEDIUM
                )
                for i in range(count)
            ]
            
            # Measure memory before
            import psutil
            process = psutil.Process()
            memory_before = process.memory_info().rss / 1024 / 1024
            
            # Time the operations
            latencies = []
            errors = 0
            
            start_time = time.time()
            
            for message in messages:
                op_start = time.time()
                try:
                    success = await queue.publish_message(message)
                    if not success:
                        errors += 1
                except Exception:
                    errors += 1
                
                latencies.append(time.time() - op_start)
            
            # Wait for batches to flush
            await asyncio.sleep(0.2)
            
            total_time = time.time() - start_time
            
            # Measure memory after
            memory_after = process.memory_info().rss / 1024 / 1024
            memory_used = memory_after - memory_before
            
            return BenchmarkResult(
                test_name=test_name,
                implementation="optimized",
                operation_count=count,
                total_time=total_time,
                operations_per_second=count / total_time,
                avg_latency=statistics.mean(latencies),
                min_latency=min(latencies),
                max_latency=max(latencies),
                p95_latency=statistics.quantiles(latencies, n=20)[18] if len(latencies) > 5 else max(latencies),
                memory_usage_mb=memory_used,
                success_rate=(count - errors) / count,
                errors=errors
            )
        
        finally:
            await queue.shutdown()
    
    async def benchmark_task_queuing(self):
        """Benchmark task queue operations"""
        print("\n2. Task Queue Benchmark")
        print("-" * 25)
        
        test_configs = [
            {"count": 200, "name": "Small Queue"},
            {"count": 1000, "name": "Medium Queue"},
            {"count": 3000, "name": "Large Queue"}
        ]
        
        for config in test_configs:
            print(f"\nTesting {config['name']} ({config['count']} tasks)")
            
            # Test original implementation
            original_result = await self._test_task_queuing_original(
                config['count'], f"task_queue_{config['name'].lower().replace(' ', '_')}"
            )
            self.results.append(original_result)
            
            # Test optimized implementation
            optimized_result = await self._test_task_queuing_optimized(
                config['count'], f"task_queue_{config['name'].lower().replace(' ', '_')}"
            )
            self.results.append(optimized_result)
            
            # Print comparison
            improvement = (optimized_result.operations_per_second / original_result.operations_per_second - 1) * 100
            print(f"  Original:  {original_result.operations_per_second:.1f} ops/sec")
            print(f"  Optimized: {optimized_result.operations_per_second:.1f} ops/sec")
            print(f"  Improvement: {improvement:.1f}%")
    
    async def _test_task_queuing_original(self, count: int, test_name: str) -> BenchmarkResult:
        """Test original task queuing implementation"""
        queue = await create_original_queue(self.redis_urls, f"{self.cluster_name}_task_orig")
        
        try:
            tasks = [
                TaskDefinition(
                    id=f"bench-task-{i}",
                    type="benchmark-task",
                    agent_type="any",
                    priority=Priority.MEDIUM,
                    payload={"index": i, "data": "x" * 50},
                    created_at=datetime.now()
                )
                for i in range(count)
            ]
            
            # Measure enqueue performance
            enqueue_latencies = []
            enqueue_errors = 0
            
            start_time = time.time()
            
            for task in tasks:
                op_start = time.time()
                try:
                    success = await queue.enqueue_task(task)
                    if not success:
                        enqueue_errors += 1
                except Exception:
                    enqueue_errors += 1
                
                enqueue_latencies.append(time.time() - op_start)
            
            enqueue_time = time.time() - start_time
            
            # Measure dequeue performance
            dequeue_latencies = []
            dequeue_errors = 0
            dequeued_count = 0
            
            start_time = time.time()
            
            for _ in range(count):
                op_start = time.time()
                try:
                    task = await queue.dequeue_task("benchmark-agent", "any")
                    if task:
                        dequeued_count += 1
                    else:
                        break
                except Exception:
                    dequeue_errors += 1
                
                dequeue_latencies.append(time.time() - op_start)
            
            dequeue_time = time.time() - start_time
            
            total_time = enqueue_time + dequeue_time
            total_operations = count * 2  # enqueue + dequeue
            all_latencies = enqueue_latencies + dequeue_latencies
            
            return BenchmarkResult(
                test_name=test_name,
                implementation="original",
                operation_count=total_operations,
                total_time=total_time,
                operations_per_second=total_operations / total_time,
                avg_latency=statistics.mean(all_latencies),
                min_latency=min(all_latencies),
                max_latency=max(all_latencies),
                p95_latency=statistics.quantiles(all_latencies, n=20)[18] if len(all_latencies) > 5 else max(all_latencies),
                memory_usage_mb=0,  # Not measured for this test
                success_rate=(total_operations - enqueue_errors - dequeue_errors) / total_operations,
                errors=enqueue_errors + dequeue_errors
            )
        
        finally:
            await queue.shutdown()
    
    async def _test_task_queuing_optimized(self, count: int, test_name: str) -> BenchmarkResult:
        """Test optimized task queuing implementation"""
        queue = await create_optimized_message_queue(self.redis_urls, f"{self.cluster_name}_task_opt")
        
        try:
            tasks = [
                TaskDefinition(
                    id=f"bench-task-opt-{i}",
                    type="benchmark-task",
                    agent_type="any",
                    priority=Priority.MEDIUM,
                    payload={"index": i, "data": "x" * 50},
                    created_at=datetime.now()
                )
                for i in range(count)
            ]
            
            # Measure enqueue performance
            enqueue_latencies = []
            enqueue_errors = 0
            
            start_time = time.time()
            
            for task in tasks:
                op_start = time.time()
                try:
                    success = await queue.enqueue_task(task)
                    if not success:
                        enqueue_errors += 1
                except Exception:
                    enqueue_errors += 1
                
                enqueue_latencies.append(time.time() - op_start)
            
            enqueue_time = time.time() - start_time
            
            # Measure dequeue performance
            dequeue_latencies = []
            dequeue_errors = 0
            dequeued_count = 0
            
            start_time = time.time()
            
            for _ in range(count):
                op_start = time.time()
                try:
                    task = await queue.dequeue_task("benchmark-agent", "any")
                    if task:
                        dequeued_count += 1
                    else:
                        break
                except Exception:
                    dequeue_errors += 1
                
                dequeue_latencies.append(time.time() - op_start)
            
            dequeue_time = time.time() - start_time
            
            total_time = enqueue_time + dequeue_time
            total_operations = count * 2  # enqueue + dequeue
            all_latencies = enqueue_latencies + dequeue_latencies
            
            return BenchmarkResult(
                test_name=test_name,
                implementation="optimized",
                operation_count=total_operations,
                total_time=total_time,
                operations_per_second=total_operations / total_time,
                avg_latency=statistics.mean(all_latencies),
                min_latency=min(all_latencies),
                max_latency=max(all_latencies),
                p95_latency=statistics.quantiles(all_latencies, n=20)[18] if len(all_latencies) > 5 else max(all_latencies),
                memory_usage_mb=0,  # Not measured for this test
                success_rate=(total_operations - enqueue_errors - dequeue_errors) / total_operations,
                errors=enqueue_errors + dequeue_errors
            )
        
        finally:
            await queue.shutdown()
    
    async def benchmark_concurrent_operations(self):
        """Benchmark concurrent operation performance"""
        print("\n3. Concurrent Operations Benchmark")
        print("-" * 35)
        
        concurrency_levels = [10, 50, 100]
        operations_per_worker = 100
        
        for concurrency in concurrency_levels:
            print(f"\nTesting {concurrency} concurrent workers ({operations_per_worker} ops each)")
            
            # Test original implementation
            original_result = await self._test_concurrent_operations_original(
                concurrency, operations_per_worker, f"concurrent_{concurrency}"
            )
            self.results.append(original_result)
            
            # Test optimized implementation
            optimized_result = await self._test_concurrent_operations_optimized(
                concurrency, operations_per_worker, f"concurrent_{concurrency}"
            )
            self.results.append(optimized_result)
            
            # Print comparison
            improvement = (optimized_result.operations_per_second / original_result.operations_per_second - 1) * 100
            print(f"  Original:  {original_result.operations_per_second:.1f} ops/sec")
            print(f"  Optimized: {optimized_result.operations_per_second:.1f} ops/sec")
            print(f"  Improvement: {improvement:.1f}%")
    
    async def _test_concurrent_operations_original(self, workers: int, ops_per_worker: int, test_name: str) -> BenchmarkResult:
        """Test concurrent operations with original implementation"""
        queue = await create_original_queue(self.redis_urls, f"{self.cluster_name}_conc_orig")
        
        try:
            async def worker(worker_id: int):
                latencies = []
                errors = 0
                
                for i in range(ops_per_worker):
                    message = SwarmMessage(
                        id=f"conc-msg-{worker_id}-{i}",
                        type=MessageType.STATUS_UPDATE,
                        sender=f"worker-{worker_id}",
                        recipient=None,
                        timestamp=datetime.now(),
                        payload={"worker": worker_id, "op": i},
                        priority=Priority.MEDIUM
                    )
                    
                    op_start = time.time()
                    try:
                        success = await queue.publish_message(message)
                        if not success:
                            errors += 1
                    except Exception:
                        errors += 1
                    
                    latencies.append(time.time() - op_start)
                
                return latencies, errors
            
            # Run concurrent workers
            start_time = time.time()
            
            tasks = [worker(i) for i in range(workers)]
            results = await asyncio.gather(*tasks)
            
            total_time = time.time() - start_time
            
            # Aggregate results
            all_latencies = []
            total_errors = 0
            
            for latencies, errors in results:
                all_latencies.extend(latencies)
                total_errors += errors
            
            total_operations = workers * ops_per_worker
            
            return BenchmarkResult(
                test_name=test_name,
                implementation="original",
                operation_count=total_operations,
                total_time=total_time,
                operations_per_second=total_operations / total_time,
                avg_latency=statistics.mean(all_latencies),
                min_latency=min(all_latencies),
                max_latency=max(all_latencies),
                p95_latency=statistics.quantiles(all_latencies, n=20)[18] if len(all_latencies) > 5 else max(all_latencies),
                memory_usage_mb=0,
                success_rate=(total_operations - total_errors) / total_operations,
                errors=total_errors
            )
        
        finally:
            await queue.shutdown()
    
    async def _test_concurrent_operations_optimized(self, workers: int, ops_per_worker: int, test_name: str) -> BenchmarkResult:
        """Test concurrent operations with optimized implementation"""
        queue = await create_optimized_message_queue(self.redis_urls, f"{self.cluster_name}_conc_opt")
        
        try:
            async def worker(worker_id: int):
                latencies = []
                errors = 0
                
                for i in range(ops_per_worker):
                    message = SwarmMessage(
                        id=f"conc-msg-opt-{worker_id}-{i}",
                        type=MessageType.STATUS_UPDATE,
                        sender=f"worker-{worker_id}",
                        recipient=None,
                        timestamp=datetime.now(),
                        payload={"worker": worker_id, "op": i},
                        priority=Priority.MEDIUM
                    )
                    
                    op_start = time.time()
                    try:
                        success = await queue.publish_message(message)
                        if not success:
                            errors += 1
                    except Exception:
                        errors += 1
                    
                    latencies.append(time.time() - op_start)
                
                return latencies, errors
            
            # Run concurrent workers
            start_time = time.time()
            
            tasks = [worker(i) for i in range(workers)]
            results = await asyncio.gather(*tasks)
            
            # Wait for batches to flush
            await asyncio.sleep(0.2)
            
            total_time = time.time() - start_time
            
            # Aggregate results
            all_latencies = []
            total_errors = 0
            
            for latencies, errors in results:
                all_latencies.extend(latencies)
                total_errors += errors
            
            total_operations = workers * ops_per_worker
            
            return BenchmarkResult(
                test_name=test_name,
                implementation="optimized",
                operation_count=total_operations,
                total_time=total_time,
                operations_per_second=total_operations / total_time,
                avg_latency=statistics.mean(all_latencies),
                min_latency=min(all_latencies),
                max_latency=max(all_latencies),
                p95_latency=statistics.quantiles(all_latencies, n=20)[18] if len(all_latencies) > 5 else max(all_latencies),
                memory_usage_mb=0,
                success_rate=(total_operations - total_errors) / total_operations,
                errors=total_errors
            )
        
        finally:
            await queue.shutdown()
    
    async def benchmark_memory_efficiency(self):
        """Benchmark memory efficiency"""
        print("\n4. Memory Efficiency Benchmark")
        print("-" * 30)
        
        test_count = 2000
        print(f"\nTesting memory usage with {test_count} operations")
        
        # Test original implementation
        original_memory = await self._test_memory_usage_original(test_count)
        
        # Test optimized implementation  
        optimized_memory = await self._test_memory_usage_optimized(test_count)
        
        print(f"  Original Memory Usage:  {original_memory:.1f} MB")
        print(f"  Optimized Memory Usage: {optimized_memory:.1f} MB")
        print(f"  Memory Reduction: {(1 - optimized_memory / original_memory) * 100:.1f}%")
    
    async def _test_memory_usage_original(self, count: int) -> float:
        """Test memory usage with original implementation"""
        import psutil
        process = psutil.Process()
        
        # Baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024
        
        queue = await create_original_queue(self.redis_urls, f"{self.cluster_name}_mem_orig")
        
        try:
            # Create many objects
            messages = []
            for i in range(count):
                message = SwarmMessage(
                    id=f"mem-test-{i}",
                    type=MessageType.STATUS_UPDATE,
                    sender=f"mem-agent-{i % 10}",
                    recipient=None,
                    timestamp=datetime.now(),
                    payload={"index": i, "data": "x" * 200},
                    priority=Priority.MEDIUM
                )
                messages.append(message)
                
                # Publish some messages
                if i % 100 == 0:
                    await queue.publish_message(message)
            
            # Measure peak memory
            peak_memory = process.memory_info().rss / 1024 / 1024
            return peak_memory - baseline_memory
        
        finally:
            await queue.shutdown()
            del messages  # Clean up
    
    async def _test_memory_usage_optimized(self, count: int) -> float:
        """Test memory usage with optimized implementation"""
        import psutil
        process = psutil.Process()
        
        # Baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024
        
        queue = await create_optimized_message_queue(self.redis_urls, f"{self.cluster_name}_mem_opt")
        
        try:
            # Create many objects
            messages = []
            for i in range(count):
                message = SwarmMessage(
                    id=f"mem-test-opt-{i}",
                    type=MessageType.STATUS_UPDATE,
                    sender=f"mem-agent-{i % 10}",
                    recipient=None,
                    timestamp=datetime.now(),
                    payload={"index": i, "data": "x" * 200},
                    priority=Priority.MEDIUM
                )
                messages.append(message)
                
                # Publish some messages
                if i % 100 == 0:
                    await queue.publish_message(message)
            
            # Wait for processing
            await asyncio.sleep(0.5)
            
            # Measure peak memory
            peak_memory = process.memory_info().rss / 1024 / 1024
            return peak_memory - baseline_memory
        
        finally:
            await queue.shutdown()
            del messages  # Clean up
    
    async def benchmark_sustained_load(self):
        """Benchmark sustained load performance"""
        print("\n5. Sustained Load Benchmark")
        print("-" * 30)
        
        duration_seconds = 30
        target_rate = 100  # messages per second
        
        print(f"\nTesting sustained load ({target_rate} ops/sec for {duration_seconds}s)")
        
        # Test optimized implementation only (as it's the focus)
        result = await self._test_sustained_load_optimized(duration_seconds, target_rate)
        self.results.append(result)
        
        print(f"  Achieved Rate: {result.operations_per_second:.1f} ops/sec")
        print(f"  Success Rate: {result.success_rate * 100:.1f}%")
        print(f"  Average Latency: {result.avg_latency * 1000:.1f}ms")
    
    async def _test_sustained_load_optimized(self, duration: int, target_rate: int) -> BenchmarkResult:
        """Test sustained load with optimized implementation"""
        queue = await create_optimized_message_queue(self.redis_urls, f"{self.cluster_name}_sustained")
        
        try:
            latencies = []
            errors = 0
            operations = 0
            
            interval = 1.0 / target_rate
            start_time = time.time()
            end_time = start_time + duration
            
            while time.time() < end_time:
                op_start = time.time()
                
                message = SwarmMessage(
                    id=f"sustained-{operations}",
                    type=MessageType.STATUS_UPDATE,
                    sender=f"sustained-agent-{operations % 5}",
                    recipient=None,
                    timestamp=datetime.now(),
                    payload={"index": operations},
                    priority=Priority.MEDIUM
                )
                
                try:
                    success = await queue.publish_message(message)
                    if not success:
                        errors += 1
                except Exception:
                    errors += 1
                
                operations += 1
                op_latency = time.time() - op_start
                latencies.append(op_latency)
                
                # Rate limiting
                elapsed = time.time() - op_start
                if elapsed < interval:
                    await asyncio.sleep(interval - elapsed)
            
            total_time = time.time() - start_time
            
            # Wait for any pending operations
            await asyncio.sleep(1)
            
            return BenchmarkResult(
                test_name="sustained_load",
                implementation="optimized",
                operation_count=operations,
                total_time=total_time,
                operations_per_second=operations / total_time,
                avg_latency=statistics.mean(latencies),
                min_latency=min(latencies),
                max_latency=max(latencies),
                p95_latency=statistics.quantiles(latencies, n=20)[18] if len(latencies) > 5 else max(latencies),
                memory_usage_mb=0,
                success_rate=(operations - errors) / operations,
                errors=errors
            )
        
        finally:
            await queue.shutdown()
    
    def generate_comparison_report(self) -> Dict[str, Any]:
        """Generate comprehensive comparison report"""
        print("\n" + "=" * 60)
        print("PERFORMANCE COMPARISON REPORT")
        print("=" * 60)
        
        # Group results by test name
        test_groups = {}
        for result in self.results:
            test_name = result.test_name
            if test_name not in test_groups:
                test_groups[test_name] = {}
            test_groups[test_name][result.implementation] = result
        
        improvements = {}
        
        print("\nPerformance Improvements:")
        print("-" * 40)
        
        for test_name, implementations in test_groups.items():
            if 'original' in implementations and 'optimized' in implementations:
                original = implementations['original']
                optimized = implementations['optimized']
                
                throughput_improvement = (optimized.operations_per_second / original.operations_per_second - 1) * 100
                latency_improvement = (1 - optimized.avg_latency / original.avg_latency) * 100
                
                improvements[test_name] = {
                    'throughput_improvement_percent': throughput_improvement,
                    'latency_improvement_percent': latency_improvement,
                    'original_throughput': original.operations_per_second,
                    'optimized_throughput': optimized.operations_per_second,
                    'original_latency_ms': original.avg_latency * 1000,
                    'optimized_latency_ms': optimized.avg_latency * 1000
                }
                
                print(f"\n{test_name.replace('_', ' ').title()}:")
                print(f"  Throughput: {throughput_improvement:+.1f}% ({original.operations_per_second:.1f} → {optimized.operations_per_second:.1f} ops/sec)")
                print(f"  Latency: {latency_improvement:+.1f}% ({original.avg_latency*1000:.1f} → {optimized.avg_latency*1000:.1f} ms)")
                print(f"  Success Rate: {optimized.success_rate*100:.1f}%")
        
        # Overall summary
        if improvements:
            avg_throughput_improvement = statistics.mean([imp['throughput_improvement_percent'] for imp in improvements.values()])
            avg_latency_improvement = statistics.mean([imp['latency_improvement_percent'] for imp in improvements.values()])
            
            print(f"\nOVERALL PERFORMANCE GAINS:")
            print(f"  Average Throughput Improvement: {avg_throughput_improvement:.1f}%")
            print(f"  Average Latency Improvement: {avg_latency_improvement:.1f}%")
            
            # Performance tier assessment
            if avg_throughput_improvement > 300:
                tier = "EXCEPTIONAL (>300% improvement)"
            elif avg_throughput_improvement > 200:
                tier = "EXCELLENT (200-300% improvement)"
            elif avg_throughput_improvement > 100:
                tier = "VERY GOOD (100-200% improvement)"
            elif avg_throughput_improvement > 50:
                tier = "GOOD (50-100% improvement)"
            else:
                tier = "MODERATE (<50% improvement)"
            
            print(f"  Performance Tier: {tier}")
        
        # Generate detailed report
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': len(self.results),
                'improvements': improvements,
                'avg_throughput_improvement': avg_throughput_improvement if improvements else 0,
                'avg_latency_improvement': avg_latency_improvement if improvements else 0
            },
            'detailed_results': [
                {
                    'test_name': r.test_name,
                    'implementation': r.implementation,
                    'operations_per_second': r.operations_per_second,
                    'avg_latency_ms': r.avg_latency * 1000,
                    'p95_latency_ms': r.p95_latency * 1000,
                    'success_rate': r.success_rate,
                    'memory_usage_mb': r.memory_usage_mb
                }
                for r in self.results
            ]
        }
        
        # Save report to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"benchmark_report_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nDetailed report saved to: {report_file}")
        
        return report
    
    async def shutdown(self):
        """Shutdown benchmark environment"""
        await self.monitor.shutdown()
        await self.profiler.shutdown()


async def main():
    """Main benchmark execution"""
    parser = argparse.ArgumentParser(description='TGE Swarm Performance Benchmark')
    parser.add_argument('--quick', action='store_true', help='Run quick benchmark (reduced operations)')
    parser.add_argument('--output', default='benchmark_results.json', help='Output file for results')
    
    args = parser.parse_args()
    
    benchmark = PerformanceBenchmark()
    
    try:
        await benchmark.initialize()
        
        if args.quick:
            print("Running quick benchmark mode...")
            # Reduce operation counts for quick testing
            benchmark.quick_mode = True
        
        report = await benchmark.run_all_benchmarks()
        
        # Save results
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nBenchmark complete! Results saved to {args.output}")
        
    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user")
    except Exception as e:
        print(f"\nBenchmark failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await benchmark.shutdown()


if __name__ == "__main__":
    asyncio.run(main())