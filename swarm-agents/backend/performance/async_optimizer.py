#!/usr/bin/env python3
"""
Async/Await Optimization Framework for TGE Swarm
Provides advanced async optimizations, concurrency patterns, and performance monitoring
"""

import asyncio
import concurrent.futures
import logging
import time
import threading
import multiprocessing
from typing import Dict, List, Any, Optional, Callable, TypeVar, Awaitable, Union
from dataclasses import dataclass, field
from functools import wraps, partial
from collections import defaultdict, deque
from datetime import datetime, timedelta
import weakref
import inspect


T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


@dataclass
class AsyncMetrics:
    """Async operation metrics"""
    total_operations: int = 0
    total_execution_time: float = 0.0
    avg_execution_time: float = 0.0
    concurrent_operations: int = 0
    max_concurrent_operations: int = 0
    semaphore_waits: int = 0
    timeout_errors: int = 0
    cancelled_operations: int = 0
    thread_pool_tasks: int = 0
    process_pool_tasks: int = 0


class AsyncSemaphoreManager:
    """Manages semaphores for controlling concurrency"""
    
    def __init__(self):
        self.semaphores: Dict[str, asyncio.Semaphore] = {}
        self.metrics: Dict[str, AsyncMetrics] = defaultdict(AsyncMetrics)
        self.lock = asyncio.Lock()
        self.logger = logging.getLogger("AsyncSemaphoreManager")
    
    async def get_semaphore(self, name: str, limit: int) -> asyncio.Semaphore:
        """Get or create semaphore with specified limit"""
        async with self.lock:
            if name not in self.semaphores:
                self.semaphores[name] = asyncio.Semaphore(limit)
                self.logger.debug(f"Created semaphore '{name}' with limit {limit}")
            return self.semaphores[name]
    
    async def acquire_with_metrics(self, name: str, limit: int):
        """Acquire semaphore with metrics tracking"""
        semaphore = await self.get_semaphore(name, limit)
        
        start_time = time.time()
        await semaphore.acquire()
        wait_time = time.time() - start_time
        
        if wait_time > 0.001:  # Only count significant waits
            self.metrics[name].semaphore_waits += 1
        
        return semaphore
    
    def release_semaphore(self, name: str, semaphore: asyncio.Semaphore):
        """Release semaphore"""
        semaphore.release()
    
    def get_metrics(self, name: str) -> AsyncMetrics:
        """Get metrics for semaphore"""
        return self.metrics[name]


class TaskBatcher:
    """Batches async tasks for efficient execution"""
    
    def __init__(self, 
                 batch_size: int = 10,
                 batch_timeout: float = 0.1,
                 max_concurrent_batches: int = 5):
        
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.max_concurrent_batches = max_concurrent_batches
        
        self.pending_tasks: List[asyncio.Task] = []
        self.batch_semaphore = asyncio.Semaphore(max_concurrent_batches)
        self.batch_timer: Optional[asyncio.Task] = None
        self.running = False
        
        self.logger = logging.getLogger("TaskBatcher")
    
    async def add_task(self, coro: Awaitable[T]) -> asyncio.Task[T]:
        """Add task to batch"""
        task = asyncio.create_task(coro)
        self.pending_tasks.append(task)
        
        # Start batch timer if this is the first task
        if len(self.pending_tasks) == 1 and not self.batch_timer:
            self.batch_timer = asyncio.create_task(self._batch_timeout_handler())
        
        # Process batch if it's full
        if len(self.pending_tasks) >= self.batch_size:
            await self._process_batch()
        
        return task
    
    async def _batch_timeout_handler(self):
        """Handle batch timeout"""
        try:
            await asyncio.sleep(self.batch_timeout)
            if self.pending_tasks:
                await self._process_batch()
        except asyncio.CancelledError:
            pass
    
    async def _process_batch(self):
        """Process current batch of tasks"""
        if not self.pending_tasks:
            return
        
        # Cancel timer
        if self.batch_timer:
            self.batch_timer.cancel()
            self.batch_timer = None
        
        # Get tasks to process
        tasks_to_process = self.pending_tasks.copy()
        self.pending_tasks.clear()
        
        # Process batch with concurrency control
        async with self.batch_semaphore:
            try:
                # Wait for all tasks in batch
                results = await asyncio.gather(*tasks_to_process, return_exceptions=True)
                
                # Log any exceptions
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self.logger.error(f"Task {i} in batch failed: {result}")
                
            except Exception as e:
                self.logger.error(f"Batch processing error: {e}")


class AsyncOptimizer:
    """Advanced async optimization framework"""
    
    def __init__(self,
                 max_workers: int = None,
                 thread_pool_size: int = 10,
                 process_pool_size: int = None):
        
        self.max_workers = max_workers or min(32, (multiprocessing.cpu_count() or 1) + 4)
        self.thread_pool_size = thread_pool_size
        self.process_pool_size = process_pool_size or multiprocessing.cpu_count()
        
        # Execution pools
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.thread_pool_size,
            thread_name_prefix="AsyncOpt"
        )
        self.process_pool = concurrent.futures.ProcessPoolExecutor(
            max_workers=self.process_pool_size
        )
        
        # Async management
        self.semaphore_manager = AsyncSemaphoreManager()
        self.task_batcher = TaskBatcher()
        
        # Metrics and monitoring
        self.metrics = AsyncMetrics()
        self.operation_history: deque = deque(maxlen=1000)
        self.active_operations: weakref.WeakSet = weakref.WeakSet()
        
        # Task tracking
        self.background_tasks: List[asyncio.Task] = []
        self.running = False
        
        self.logger = logging.getLogger("AsyncOptimizer")
        self.setup_logging()
    
    def setup_logging(self):
        """Setup async optimizer logging"""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    async def initialize(self):
        """Initialize async optimizer"""
        self.running = True
        
        # Start background monitoring
        monitor_task = asyncio.create_task(self._monitoring_loop())
        self.background_tasks.append(monitor_task)
        
        self.logger.info("Async optimizer initialized")
    
    def optimize_async(self, 
                      concurrency_limit: int = None,
                      timeout: float = None,
                      retry_count: int = 0,
                      cache_results: bool = False,
                      batch_execution: bool = False):
        """Decorator for optimizing async functions"""
        
        def decorator(func: F) -> F:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await self._execute_optimized(
                    func, args, kwargs,
                    concurrency_limit=concurrency_limit,
                    timeout=timeout,
                    retry_count=retry_count,
                    cache_results=cache_results,
                    batch_execution=batch_execution
                )
            return wrapper
        
        return decorator
    
    async def _execute_optimized(self, 
                               func: Callable,
                               args: tuple,
                               kwargs: dict,
                               concurrency_limit: int = None,
                               timeout: float = None,
                               retry_count: int = 0,
                               cache_results: bool = False,
                               batch_execution: bool = False) -> Any:
        """Execute function with optimizations"""
        
        start_time = time.time()
        semaphore = None
        
        try:
            # Update metrics
            self.metrics.total_operations += 1
            self.metrics.concurrent_operations += 1
            self.metrics.max_concurrent_operations = max(
                self.metrics.max_concurrent_operations,
                self.metrics.concurrent_operations
            )
            
            # Apply concurrency limiting
            if concurrency_limit:
                semaphore_name = f"{func.__name__}_concurrency"
                semaphore = await self.semaphore_manager.acquire_with_metrics(
                    semaphore_name, concurrency_limit
                )
            
            # Execute with retry logic
            result = await self._execute_with_retry(
                func, args, kwargs, retry_count, timeout, batch_execution
            )
            
            # Cache results if requested
            if cache_results:
                # Simple caching implementation
                cache_key = self._generate_cache_key(func, args, kwargs)
                # TODO: Implement actual caching
            
            return result
            
        except asyncio.TimeoutError:
            self.metrics.timeout_errors += 1
            raise
        except asyncio.CancelledError:
            self.metrics.cancelled_operations += 1
            raise
        except Exception as e:
            self.logger.error(f"Error in optimized execution of {func.__name__}: {e}")
            raise
        finally:
            # Release semaphore
            if semaphore and concurrency_limit:
                semaphore_name = f"{func.__name__}_concurrency"
                self.semaphore_manager.release_semaphore(semaphore_name, semaphore)
            
            # Update metrics
            execution_time = time.time() - start_time
            self.metrics.concurrent_operations -= 1
            self.metrics.total_execution_time += execution_time
            self.metrics.avg_execution_time = (
                self.metrics.total_execution_time / self.metrics.total_operations
            )
            
            # Record operation
            self.operation_history.append({
                'function': func.__name__,
                'execution_time': execution_time,
                'timestamp': datetime.now(),
                'success': True  # We only reach here if no exception
            })
    
    async def _execute_with_retry(self,
                                func: Callable,
                                args: tuple,
                                kwargs: dict,
                                retry_count: int,
                                timeout: float,
                                batch_execution: bool) -> Any:
        """Execute function with retry logic"""
        
        last_exception = None
        
        for attempt in range(retry_count + 1):
            try:
                if batch_execution:
                    # Execute in batch
                    coro = func(*args, **kwargs)
                    task = await self.task_batcher.add_task(coro)
                    
                    if timeout:
                        result = await asyncio.wait_for(task, timeout=timeout)
                    else:
                        result = await task
                else:
                    # Direct execution
                    if timeout:
                        result = await asyncio.wait_for(
                            func(*args, **kwargs), timeout=timeout
                        )
                    else:
                        result = await func(*args, **kwargs)
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if attempt < retry_count:
                    # Wait before retry with exponential backoff
                    wait_time = 2 ** attempt * 0.1
                    await asyncio.sleep(wait_time)
                    self.logger.warning(f"Retry {attempt + 1}/{retry_count} for {func.__name__}")
                else:
                    break
        
        # All retries failed
        raise last_exception
    
    def _generate_cache_key(self, func: Callable, args: tuple, kwargs: dict) -> str:
        """Generate cache key for function call"""
        import hashlib
        
        # Create a string representation of the call
        call_str = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
        
        # Hash it for consistent key
        return hashlib.md5(call_str.encode()).hexdigest()
    
    async def run_in_thread(self, func: Callable, *args, **kwargs) -> Any:
        """Run blocking function in thread pool"""
        loop = asyncio.get_event_loop()
        
        self.metrics.thread_pool_tasks += 1
        
        try:
            result = await loop.run_in_executor(
                self.thread_pool, partial(func, *args, **kwargs)
            )
            return result
        except Exception as e:
            self.logger.error(f"Error in thread pool execution: {e}")
            raise
    
    async def run_in_process(self, func: Callable, *args, **kwargs) -> Any:
        """Run CPU-intensive function in process pool"""
        loop = asyncio.get_event_loop()
        
        self.metrics.process_pool_tasks += 1
        
        try:
            result = await loop.run_in_executor(
                self.process_pool, partial(func, *args, **kwargs)
            )
            return result
        except Exception as e:
            self.logger.error(f"Error in process pool execution: {e}")
            raise
    
    async def gather_with_limit(self, 
                              *coros: Awaitable[T],
                              limit: int = 10,
                              return_exceptions: bool = False) -> List[T]:
        """Gather coroutines with concurrency limit"""
        
        semaphore = asyncio.Semaphore(limit)
        
        async def limited_coro(coro):
            async with semaphore:
                return await coro
        
        # Wrap all coroutines with semaphore
        limited_coros = [limited_coro(coro) for coro in coros]
        
        # Execute with gather
        return await asyncio.gather(*limited_coros, return_exceptions=return_exceptions)
    
    async def map_async(self,
                       func: Callable[[T], Awaitable[Any]],
                       items: List[T],
                       concurrency_limit: int = 10,
                       chunk_size: int = None,
                       timeout: float = None) -> List[Any]:
        """Async map with concurrency control"""
        
        if chunk_size is None:
            chunk_size = min(100, len(items))
        
        results = []
        
        # Process items in chunks
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i + chunk_size]
            
            # Create coroutines for chunk
            chunk_coros = [func(item) for item in chunk]
            
            # Execute chunk with concurrency limit
            try:
                if timeout:
                    chunk_results = await asyncio.wait_for(
                        self.gather_with_limit(*chunk_coros, limit=concurrency_limit),
                        timeout=timeout
                    )
                else:
                    chunk_results = await self.gather_with_limit(
                        *chunk_coros, limit=concurrency_limit
                    )
                
                results.extend(chunk_results)
                
            except asyncio.TimeoutError:
                self.logger.error(f"Timeout processing chunk {i//chunk_size + 1}")
                raise
            except Exception as e:
                self.logger.error(f"Error processing chunk {i//chunk_size + 1}: {e}")
                raise
        
        return results
    
    async def debounce(self, 
                      func: Callable[..., Awaitable[T]],
                      delay: float,
                      *args, **kwargs) -> T:
        """Debounce async function calls"""
        
        # Simple debouncing - wait for delay then execute
        await asyncio.sleep(delay)
        return await func(*args, **kwargs)
    
    async def throttle(self,
                      func: Callable[..., Awaitable[T]],
                      rate_limit: float,  # calls per second
                      *args, **kwargs) -> T:
        """Throttle async function calls"""
        
        # Calculate delay based on rate limit
        delay = 1.0 / rate_limit
        
        # Execute with delay
        start_time = time.time()
        result = await func(*args, **kwargs)
        
        # Wait remaining time if execution was fast
        elapsed = time.time() - start_time
        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)
        
        return result
    
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.running:
            try:
                await asyncio.sleep(60)  # Monitor every minute
                
                # Log performance metrics
                self.logger.info(f"Async metrics: "
                               f"ops={self.metrics.total_operations}, "
                               f"avg_time={self.metrics.avg_execution_time:.3f}s, "
                               f"concurrent={self.metrics.concurrent_operations}, "
                               f"max_concurrent={self.metrics.max_concurrent_operations}")
                
                # Check for performance issues
                if self.metrics.avg_execution_time > 5.0:
                    self.logger.warning("High average execution time detected")
                
                if self.metrics.timeout_errors > self.metrics.total_operations * 0.1:
                    self.logger.warning("High timeout error rate detected")
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive async metrics"""
        return {
            'total_operations': self.metrics.total_operations,
            'total_execution_time': self.metrics.total_execution_time,
            'avg_execution_time': self.metrics.avg_execution_time,
            'concurrent_operations': self.metrics.concurrent_operations,
            'max_concurrent_operations': self.metrics.max_concurrent_operations,
            'semaphore_waits': self.metrics.semaphore_waits,
            'timeout_errors': self.metrics.timeout_errors,
            'cancelled_operations': self.metrics.cancelled_operations,
            'thread_pool_tasks': self.metrics.thread_pool_tasks,
            'process_pool_tasks': self.metrics.process_pool_tasks,
            'thread_pool_active': len(self.thread_pool._threads),
            'process_pool_active': len(self.process_pool._processes) if hasattr(self.process_pool, '_processes') else 0,
            'background_tasks': len(self.background_tasks)
        }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get detailed performance report"""
        # Analyze operation history
        recent_ops = list(self.operation_history)[-100:]  # Last 100 operations
        
        if recent_ops:
            execution_times = [op['execution_time'] for op in recent_ops]
            function_stats = defaultdict(list)
            
            for op in recent_ops:
                function_stats[op['function']].append(op['execution_time'])
            
            # Calculate statistics
            avg_time = sum(execution_times) / len(execution_times)
            min_time = min(execution_times)
            max_time = max(execution_times)
            
            # Function-specific stats
            func_stats = {}
            for func_name, times in function_stats.items():
                func_stats[func_name] = {
                    'call_count': len(times),
                    'avg_time': sum(times) / len(times),
                    'min_time': min(times),
                    'max_time': max(times)
                }
        else:
            avg_time = min_time = max_time = 0.0
            func_stats = {}
        
        return {
            'metrics': self.get_metrics(),
            'recent_performance': {
                'operation_count': len(recent_ops),
                'avg_execution_time': avg_time,
                'min_execution_time': min_time,
                'max_execution_time': max_time
            },
            'function_statistics': func_stats,
            'semaphore_metrics': {
                name: metrics.__dict__ 
                for name, metrics in self.semaphore_manager.metrics.items()
            }
        }
    
    async def shutdown(self):
        """Shutdown async optimizer"""
        self.running = False
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # Shutdown executors
        self.thread_pool.shutdown(wait=True)
        self.process_pool.shutdown(wait=True)
        
        self.logger.info("Async optimizer shutdown complete")


# Utility decorators for common optimizations
def async_cache(ttl_seconds: int = 300, max_size: int = 1000):
    """Simple async function result caching"""
    cache = {}
    cache_times = {}
    
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            current_time = time.time()
            
            # Check cache
            if (key in cache and 
                key in cache_times and 
                current_time - cache_times[key] < ttl_seconds):
                return cache[key]
            
            # Execute and cache
            result = await func(*args, **kwargs)
            
            # Manage cache size
            if len(cache) >= max_size:
                # Remove oldest entries
                oldest_key = min(cache_times.keys(), key=cache_times.get)
                del cache[oldest_key]
                del cache_times[oldest_key]
            
            cache[key] = result
            cache_times[key] = current_time
            
            return result
        
        return wrapper
    
    return decorator


def async_retry(max_retries: int = 3, backoff_factor: float = 1.0):
    """Async function retry decorator"""
    
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        wait_time = backoff_factor * (2 ** attempt)
                        await asyncio.sleep(wait_time)
                    else:
                        break
            
            raise last_exception
        
        return wrapper
    
    return decorator


def async_timeout(timeout_seconds: float):
    """Async function timeout decorator"""
    
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await asyncio.wait_for(
                func(*args, **kwargs), 
                timeout=timeout_seconds
            )
        
        return wrapper
    
    return decorator