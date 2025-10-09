#!/usr/bin/env python3
"""
Advanced Performance Profiler for TGE Swarm
Provides detailed profiling capabilities, bottleneck detection, and optimization recommendations
"""

import asyncio
import cProfile
import functools
import inspect
import io
import logging
import pstats
import sys
import time
import threading
import traceback
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import weakref
import linecache
import gc


@dataclass
class ProfileData:
    """Profile execution data"""
    function_name: str
    module_name: str
    filename: str
    line_number: int
    call_count: int
    total_time: float
    cumulative_time: float
    avg_time: float
    max_time: float
    min_time: float
    callers: List[str] = field(default_factory=list)
    callees: List[str] = field(default_factory=list)


@dataclass
class BottleneckInfo:
    """Performance bottleneck information"""
    function_name: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    impact_score: float
    total_time: float
    call_count: int
    avg_time: float
    recommendation: str
    file_location: str


class FunctionProfiler:
    """Individual function profiler"""
    
    def __init__(self, func_name: str):
        self.func_name = func_name
        self.call_count = 0
        self.total_time = 0.0
        self.times = deque(maxlen=1000)  # Keep last 1000 calls
        self.start_times = {}
        self.call_stack = []
        self.lock = threading.RLock()
    
    def start_call(self, call_id: str):
        """Start timing a function call"""
        with self.lock:
            self.start_times[call_id] = time.time()
            self.call_stack.append((call_id, time.time()))
    
    def end_call(self, call_id: str) -> float:
        """End timing a function call"""
        with self.lock:
            if call_id not in self.start_times:
                return 0.0
            
            duration = time.time() - self.start_times.pop(call_id)
            self.call_count += 1
            self.total_time += duration
            self.times.append(duration)
            
            # Remove from call stack
            self.call_stack = [(cid, start) for cid, start in self.call_stack if cid != call_id]
            
            return duration
    
    def get_stats(self) -> Dict[str, Any]:
        """Get profiling statistics"""
        with self.lock:
            if not self.times:
                return {
                    'call_count': 0,
                    'total_time': 0.0,
                    'avg_time': 0.0,
                    'min_time': 0.0,
                    'max_time': 0.0,
                    'active_calls': 0
                }
            
            times_list = list(self.times)
            
            return {
                'call_count': self.call_count,
                'total_time': self.total_time,
                'avg_time': self.total_time / self.call_count if self.call_count > 0 else 0.0,
                'min_time': min(times_list),
                'max_time': max(times_list),
                'recent_avg': sum(times_list) / len(times_list),
                'active_calls': len(self.call_stack)
            }


class SystemProfiler:
    """System-wide performance profiler"""
    
    def __init__(self, 
                 sample_interval: float = 0.1,
                 max_stack_depth: int = 30,
                 enable_line_profiling: bool = False):
        
        self.sample_interval = sample_interval
        self.max_stack_depth = max_stack_depth
        self.enable_line_profiling = enable_line_profiling
        
        # Profiling data
        self.function_profiles: Dict[str, FunctionProfiler] = {}
        self.call_graph: Dict[str, Set[str]] = defaultdict(set)
        self.line_profiles: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        
        # Sampling profiler
        self.sampling_enabled = False
        self.sample_data: List[List[str]] = []
        self.sample_counts: Dict[tuple, int] = defaultdict(int)
        
        # Background profiling
        self.running = False
        self.profiler_tasks: List[asyncio.Task] = []
        
        self.logger = logging.getLogger("SystemProfiler")
        self.setup_logging()
    
    def setup_logging(self):
        """Setup profiler logging"""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    async def initialize(self):
        """Initialize system profiler"""
        self.running = True
        
        # Start sampling profiler if enabled
        if self.sampling_enabled:
            sample_task = asyncio.create_task(self._sampling_loop())
            self.profiler_tasks.append(sample_task)
        
        self.logger.info("System profiler initialized")
    
    def enable_sampling(self):
        """Enable statistical sampling profiler"""
        self.sampling_enabled = True
        if self.running:
            sample_task = asyncio.create_task(self._sampling_loop())
            self.profiler_tasks.append(sample_task)
    
    def disable_sampling(self):
        """Disable statistical sampling profiler"""
        self.sampling_enabled = False
    
    def profile_function(self, func: Callable = None, name: str = None):
        """Decorator for profiling functions"""
        def decorator(f):
            func_name = name or f"{f.__module__}.{f.__qualname__}"
            
            if asyncio.iscoroutinefunction(f):
                @functools.wraps(f)
                async def async_wrapper(*args, **kwargs):
                    return await self._profile_async_call(f, func_name, args, kwargs)
                return async_wrapper
            else:
                @functools.wraps(f)
                def wrapper(*args, **kwargs):
                    return self._profile_sync_call(f, func_name, args, kwargs)
                return wrapper
        
        if func is None:
            return decorator
        else:
            return decorator(func)
    
    def _profile_sync_call(self, func: Callable, func_name: str, args: tuple, kwargs: dict):
        """Profile synchronous function call"""
        call_id = f"{func_name}_{id(threading.current_thread())}_{time.time()}"
        
        # Get or create profiler
        if func_name not in self.function_profiles:
            self.function_profiles[func_name] = FunctionProfiler(func_name)
        
        profiler = self.function_profiles[func_name]
        
        # Record call stack for call graph
        current_frame = inspect.currentframe()
        caller_info = self._get_caller_info(current_frame)
        if caller_info:
            self.call_graph[caller_info].add(func_name)
        
        try:
            profiler.start_call(call_id)
            
            # Line profiling if enabled
            if self.enable_line_profiling:
                return self._profile_with_line_tracing(func, func_name, args, kwargs)
            else:
                return func(*args, **kwargs)
        
        finally:
            profiler.end_call(call_id)
    
    async def _profile_async_call(self, func: Callable, func_name: str, args: tuple, kwargs: dict):
        """Profile asynchronous function call"""
        call_id = f"{func_name}_{id(asyncio.current_task())}_{time.time()}"
        
        # Get or create profiler
        if func_name not in self.function_profiles:
            self.function_profiles[func_name] = FunctionProfiler(func_name)
        
        profiler = self.function_profiles[func_name]
        
        # Record call stack for call graph
        current_frame = inspect.currentframe()
        caller_info = self._get_caller_info(current_frame)
        if caller_info:
            self.call_graph[caller_info].add(func_name)
        
        try:
            profiler.start_call(call_id)
            
            # Line profiling if enabled
            if self.enable_line_profiling:
                return await self._profile_async_with_line_tracing(func, func_name, args, kwargs)
            else:
                return await func(*args, **kwargs)
        
        finally:
            profiler.end_call(call_id)
    
    def _profile_with_line_tracing(self, func: Callable, func_name: str, args: tuple, kwargs: dict):
        """Profile function with line-by-line tracing"""
        filename = inspect.getfile(func)
        
        def trace_calls(frame, event, arg):
            if event == 'line' and frame.f_code.co_filename == filename:
                lineno = frame.f_lineno
                self.line_profiles[func_name][lineno] += 1
            return trace_calls
        
        old_trace = sys.gettrace()
        try:
            sys.settrace(trace_calls)
            return func(*args, **kwargs)
        finally:
            sys.settrace(old_trace)
    
    async def _profile_async_with_line_tracing(self, func: Callable, func_name: str, args: tuple, kwargs: dict):
        """Profile async function with line-by-line tracing"""
        filename = inspect.getfile(func)
        
        def trace_calls(frame, event, arg):
            if event == 'line' and frame.f_code.co_filename == filename:
                lineno = frame.f_lineno
                self.line_profiles[func_name][lineno] += 1
            return trace_calls
        
        old_trace = sys.gettrace()
        try:
            sys.settrace(trace_calls)
            return await func(*args, **kwargs)
        finally:
            sys.settrace(old_trace)
    
    def _get_caller_info(self, frame) -> Optional[str]:
        """Get caller function information"""
        try:
            caller_frame = frame.f_back.f_back  # Skip wrapper frames
            if caller_frame:
                code = caller_frame.f_code
                return f"{code.co_filename}:{code.co_name}"
        except:
            pass
        return None
    
    async def _sampling_loop(self):
        """Statistical sampling profiler loop"""
        while self.running and self.sampling_enabled:
            try:
                # Get all threads
                for thread_id, frame in sys._current_frames().items():
                    stack = self._extract_stack(frame)
                    if stack:
                        stack_tuple = tuple(stack[:self.max_stack_depth])
                        self.sample_counts[stack_tuple] += 1
                        self.sample_data.append(stack)
                
                # Keep sample data manageable
                if len(self.sample_data) > 10000:
                    self.sample_data = self.sample_data[-5000:]
                
                await asyncio.sleep(self.sample_interval)
                
            except Exception as e:
                self.logger.error(f"Error in sampling loop: {e}")
                await asyncio.sleep(1)
    
    def _extract_stack(self, frame) -> List[str]:
        """Extract stack trace from frame"""
        stack = []
        current_frame = frame
        depth = 0
        
        while current_frame and depth < self.max_stack_depth:
            code = current_frame.f_code
            filename = code.co_filename
            function_name = code.co_name
            lineno = current_frame.f_lineno
            
            # Skip profiler frames
            if 'profiler.py' not in filename:
                stack.append(f"{filename}:{function_name}:{lineno}")
            
            current_frame = current_frame.f_back
            depth += 1
        
        return stack
    
    def get_profile_report(self) -> Dict[str, Any]:
        """Get comprehensive profiling report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'function_profiles': {},
            'call_graph': {},
            'sampling_data': {},
            'bottlenecks': [],
            'recommendations': []
        }
        
        # Function profiles
        for func_name, profiler in self.function_profiles.items():
            stats = profiler.get_stats()
            report['function_profiles'][func_name] = stats
        
        # Call graph
        for caller, callees in self.call_graph.items():
            report['call_graph'][caller] = list(callees)
        
        # Sampling data analysis
        if self.sample_counts:
            # Top hot paths
            hot_paths = sorted(
                self.sample_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:20]
            
            report['sampling_data'] = {
                'total_samples': sum(self.sample_counts.values()),
                'unique_stacks': len(self.sample_counts),
                'hot_paths': [
                    {'stack': list(stack), 'count': count}
                    for stack, count in hot_paths
                ]
            }
        
        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks()
        report['bottlenecks'] = [
            {
                'function_name': b.function_name,
                'severity': b.severity,
                'impact_score': b.impact_score,
                'total_time': b.total_time,
                'call_count': b.call_count,
                'avg_time': b.avg_time,
                'recommendation': b.recommendation,
                'file_location': b.file_location
            }
            for b in bottlenecks
        ]
        
        # Generate recommendations
        recommendations = self._generate_recommendations(bottlenecks)
        report['recommendations'] = recommendations
        
        return report
    
    def _identify_bottlenecks(self) -> List[BottleneckInfo]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        # Analyze function profiles
        for func_name, profiler in self.function_profiles.items():
            stats = profiler.get_stats()
            
            if stats['call_count'] == 0:
                continue
            
            # Calculate impact score
            impact_score = stats['total_time'] * stats['call_count'] * stats['avg_time']
            
            # Determine severity
            severity = "low"
            if stats['avg_time'] > 1.0:  # > 1 second average
                severity = "critical"
            elif stats['avg_time'] > 0.5:  # > 500ms average
                severity = "high"
            elif stats['avg_time'] > 0.1:  # > 100ms average
                severity = "medium"
            elif stats['total_time'] > 10.0:  # > 10 seconds total
                severity = "medium"
            
            # Generate recommendation
            recommendation = self._generate_function_recommendation(func_name, stats)
            
            bottleneck = BottleneckInfo(
                function_name=func_name,
                severity=severity,
                impact_score=impact_score,
                total_time=stats['total_time'],
                call_count=stats['call_count'],
                avg_time=stats['avg_time'],
                recommendation=recommendation,
                file_location=func_name.split('.')[0] if '.' in func_name else "unknown"
            )
            
            bottlenecks.append(bottleneck)
        
        # Sort by impact score
        bottlenecks.sort(key=lambda x: x.impact_score, reverse=True)
        
        return bottlenecks[:10]  # Top 10 bottlenecks
    
    def _generate_function_recommendation(self, func_name: str, stats: Dict[str, Any]) -> str:
        """Generate optimization recommendation for function"""
        recommendations = []
        
        if stats['avg_time'] > 1.0:
            recommendations.append("Consider breaking this function into smaller parts")
        
        if stats['call_count'] > 1000 and stats['avg_time'] > 0.01:
            recommendations.append("High call frequency - consider caching or memoization")
        
        if stats['max_time'] > stats['avg_time'] * 10:
            recommendations.append("High time variance - investigate edge cases")
        
        if stats['active_calls'] > 10:
            recommendations.append("High concurrency - check for lock contention")
        
        if not recommendations:
            recommendations.append("Monitor for optimization opportunities")
        
        return "; ".join(recommendations)
    
    def _generate_recommendations(self, bottlenecks: List[BottleneckInfo]) -> List[str]:
        """Generate system-wide optimization recommendations"""
        recommendations = []
        
        # High-level recommendations based on bottlenecks
        critical_bottlenecks = [b for b in bottlenecks if b.severity == "critical"]
        if critical_bottlenecks:
            recommendations.append(
                f"Address {len(critical_bottlenecks)} critical performance bottlenecks immediately"
            )
        
        high_bottlenecks = [b for b in bottlenecks if b.severity == "high"]
        if high_bottlenecks:
            recommendations.append(
                f"Optimize {len(high_bottlenecks)} high-impact functions"
            )
        
        # Analyze call patterns
        total_calls = sum(b.call_count for b in bottlenecks)
        if total_calls > 10000:
            recommendations.append("Consider implementing function call batching")
        
        # Analyze time distribution
        total_time = sum(b.total_time for b in bottlenecks)
        if total_time > 60:  # More than 1 minute total
            recommendations.append("Significant time spent in tracked functions - review algorithms")
        
        # Sampling-based recommendations
        if self.sample_counts:
            # Look for hot paths in sampling data
            hot_functions = defaultdict(int)
            for stack, count in self.sample_counts.items():
                for frame in stack:
                    if ':' in frame:
                        func_part = frame.split(':')[1]
                        hot_functions[func_part] += count
            
            top_hot = sorted(hot_functions.items(), key=lambda x: x[1], reverse=True)[:5]
            if top_hot:
                recommendations.append(
                    f"Hot functions from sampling: {', '.join([f[0] for f in top_hot])}"
                )
        
        return recommendations
    
    def get_line_profile_report(self, func_name: str) -> Dict[str, Any]:
        """Get line-by-line profile report for function"""
        if func_name not in self.line_profiles:
            return {}
        
        line_data = self.line_profiles[func_name]
        
        # Get source code if available
        try:
            # Extract filename from function name
            if '.' in func_name:
                module_name = func_name.split('.')[0]
                func_obj = None
                
                # Try to find the function object
                for name, profiler in self.function_profiles.items():
                    if name == func_name:
                        # This is a simplified approach
                        # In practice, you'd need more sophisticated function lookup
                        break
                
                # Get source lines
                source_lines = {}
                if func_obj:
                    filename = inspect.getfile(func_obj)
                    source, start_line = inspect.getsourcelines(func_obj)
                    
                    for i, line in enumerate(source):
                        line_num = start_line + i
                        hit_count = line_data.get(line_num, 0)
                        source_lines[line_num] = {
                            'source': line.rstrip(),
                            'hits': hit_count
                        }
                
                return {
                    'function_name': func_name,
                    'total_lines': len(source_lines),
                    'executed_lines': len([l for l in line_data.values() if l > 0]),
                    'source_lines': source_lines
                }
        
        except Exception as e:
            self.logger.error(f"Error getting line profile for {func_name}: {e}")
        
        return {
            'function_name': func_name,
            'line_hits': dict(line_data)
        }
    
    def export_profile_data(self, format: str = "json") -> str:
        """Export profile data in specified format"""
        report = self.get_profile_report()
        
        if format == "json":
            import json
            return json.dumps(report, indent=2, default=str)
        
        elif format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write function profiles
            writer.writerow(['Function', 'Call Count', 'Total Time', 'Avg Time', 'Max Time'])
            for func_name, stats in report['function_profiles'].items():
                writer.writerow([
                    func_name,
                    stats['call_count'],
                    stats['total_time'],
                    stats['avg_time'],
                    stats.get('max_time', 0)
                ])
            
            return output.getvalue()
        
        elif format == "text":
            lines = ["Performance Profile Report", "=" * 50, ""]
            
            # Function profiles
            lines.append("Function Profiles:")
            lines.append("-" * 20)
            for func_name, stats in report['function_profiles'].items():
                lines.append(f"{func_name}:")
                lines.append(f"  Calls: {stats['call_count']}")
                lines.append(f"  Total: {stats['total_time']:.3f}s")
                lines.append(f"  Average: {stats['avg_time']:.3f}s")
                lines.append("")
            
            # Bottlenecks
            if report['bottlenecks']:
                lines.append("Top Bottlenecks:")
                lines.append("-" * 15)
                for bottleneck in report['bottlenecks'][:5]:
                    lines.append(f"{bottleneck['function_name']} ({bottleneck['severity']})")
                    lines.append(f"  Impact: {bottleneck['impact_score']:.2f}")
                    lines.append(f"  Recommendation: {bottleneck['recommendation']}")
                    lines.append("")
            
            # Recommendations
            if report['recommendations']:
                lines.append("Recommendations:")
                lines.append("-" * 15)
                for rec in report['recommendations']:
                    lines.append(f"• {rec}")
                lines.append("")
            
            return "\n".join(lines)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    async def shutdown(self):
        """Shutdown system profiler"""
        self.running = False
        self.sampling_enabled = False
        
        # Cancel profiler tasks
        for task in self.profiler_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.profiler_tasks:
            await asyncio.gather(*self.profiler_tasks, return_exceptions=True)
        
        self.logger.info("System profiler shutdown complete")


class PerformanceProfiler:
    """High-level performance profiler interface"""
    
    def __init__(self):
        self.system_profiler = SystemProfiler()
        self.cprofile_data = {}
        self.running = False
        
        self.logger = logging.getLogger("PerformanceProfiler")
    
    async def initialize(self):
        """Initialize performance profiler"""
        await self.system_profiler.initialize()
        self.running = True
        self.logger.info("Performance profiler initialized")
    
    def profile_function(self, func: Callable = None, name: str = None):
        """Decorator for profiling functions"""
        return self.system_profiler.profile_function(func, name)
    
    def start_sampling(self):
        """Start statistical sampling"""
        self.system_profiler.enable_sampling()
    
    def stop_sampling(self):
        """Stop statistical sampling"""
        self.system_profiler.disable_sampling()
    
    def run_cprofile(self, func: Callable, *args, **kwargs):
        """Run function with cProfile"""
        profiler = cProfile.Profile()
        
        try:
            profiler.enable()
            result = func(*args, **kwargs)
            profiler.disable()
            
            # Store profile data
            func_name = f"{func.__module__}.{func.__name__}"
            stats = pstats.Stats(profiler)
            
            # Convert to string for storage
            stream = io.StringIO()
            stats.print_stats(stream=stream)
            self.cprofile_data[func_name] = {
                'timestamp': datetime.now(),
                'stats_text': stream.getvalue(),
                'total_time': stats.total_tt
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in cProfile run: {e}")
            raise
    
    async def run_async_cprofile(self, func: Callable, *args, **kwargs):
        """Run async function with cProfile"""
        profiler = cProfile.Profile()
        
        try:
            profiler.enable()
            result = await func(*args, **kwargs)
            profiler.disable()
            
            # Store profile data
            func_name = f"{func.__module__}.{func.__name__}"
            stats = pstats.Stats(profiler)
            
            # Convert to string for storage
            stream = io.StringIO()
            stats.print_stats(stream=stream)
            self.cprofile_data[func_name] = {
                'timestamp': datetime.now(),
                'stats_text': stream.getvalue(),
                'total_time': stats.total_tt
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in async cProfile run: {e}")
            raise
    
    def get_comprehensive_report(self) -> Dict[str, Any]:
        """Get comprehensive profiling report"""
        system_report = self.system_profiler.get_profile_report()
        
        # Add cProfile data
        system_report['cprofile_data'] = {}
        for func_name, data in self.cprofile_data.items():
            system_report['cprofile_data'][func_name] = {
                'timestamp': data['timestamp'].isoformat(),
                'total_time': data['total_time'],
                'stats_available': True
            }
        
        return system_report
    
    def get_cprofile_stats(self, func_name: str) -> Optional[str]:
        """Get cProfile statistics for function"""
        return self.cprofile_data.get(func_name, {}).get('stats_text')
    
    async def shutdown(self):
        """Shutdown performance profiler"""
        self.running = False
        await self.system_profiler.shutdown()
        self.logger.info("Performance profiler shutdown complete")


# Context manager for profiling code blocks
class ProfileContext:
    """Context manager for profiling code blocks"""
    
    def __init__(self, profiler: PerformanceProfiler, name: str):
        self.profiler = profiler
        self.name = name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            # Could record this timing if profiler had a method for it
            pass


# Memory profiler integration
class MemoryProfiler:
    """Memory usage profiler"""
    
    def __init__(self):
        self.snapshots = []
        self.enabled = False
        
        try:
            import tracemalloc
            self.tracemalloc = tracemalloc
            self.tracemalloc_available = True
        except ImportError:
            self.tracemalloc_available = False
    
    def start(self):
        """Start memory profiling"""
        if self.tracemalloc_available:
            self.tracemalloc.start()
            self.enabled = True
    
    def stop(self):
        """Stop memory profiling"""
        if self.tracemalloc_available and self.enabled:
            self.tracemalloc.stop()
            self.enabled = False
    
    def take_snapshot(self, name: str = None):
        """Take memory snapshot"""
        if self.tracemalloc_available and self.enabled:
            snapshot = self.tracemalloc.take_snapshot()
            self.snapshots.append({
                'name': name or f"snapshot_{len(self.snapshots)}",
                'timestamp': datetime.now(),
                'snapshot': snapshot
            })
    
    def get_top_stats(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top memory allocations"""
        if not self.snapshots:
            return []
        
        latest = self.snapshots[-1]['snapshot']
        top_stats = latest.statistics('lineno')[:limit]
        
        return [
            {
                'filename': stat.traceback.format()[0].split(':')[0],
                'lineno': stat.traceback.format()[0].split(':')[1],
                'size_mb': stat.size / 1024 / 1024,
                'count': stat.count
            }
            for stat in top_stats
        ]