#!/usr/bin/env python3
"""
Memory Management and Object Pooling for High-Performance TGE Swarm
Optimizes memory usage through object pooling, weak references, and garbage collection tuning
"""

import asyncio
import gc
import logging
import psutil
import sys
import time
import threading
import weakref
from typing import Dict, List, Any, Optional, Type, TypeVar, Generic, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import threading


T = TypeVar('T')


@dataclass
class MemoryMetrics:
    """Memory usage metrics"""
    total_memory_mb: float = 0.0
    used_memory_mb: float = 0.0
    available_memory_mb: float = 0.0
    memory_percent: float = 0.0
    gc_collections: Dict[int, int] = field(default_factory=dict)
    object_pools: Dict[str, int] = field(default_factory=dict)
    weak_references: int = 0
    memory_leaks_detected: int = 0


class ObjectPool(Generic[T]):
    """High-performance object pool for reducing allocations"""
    
    def __init__(self, 
                 factory: Callable[[], T],
                 reset_func: Optional[Callable[[T], None]] = None,
                 max_size: int = 100,
                 min_size: int = 10,
                 cleanup_interval: int = 300):
        
        self.factory = factory
        self.reset_func = reset_func
        self.max_size = max_size
        self.min_size = min_size
        self.cleanup_interval = cleanup_interval
        
        # Pool storage
        self.available: deque = deque()
        self.in_use: weakref.WeakSet = weakref.WeakSet()
        self.total_created = 0
        self.total_reused = 0
        
        # Threading
        self.lock = threading.RLock()
        
        # Cleanup task
        self.cleanup_task = None
        self.running = False
        
        self.logger = logging.getLogger(f"ObjectPool.{factory.__name__}")
        
        # Pre-populate pool
        self._populate_pool()
    
    def _populate_pool(self):
        """Pre-populate pool with minimum objects"""
        with self.lock:
            for _ in range(self.min_size):
                obj = self.factory()
                self.available.append(obj)
                self.total_created += 1
    
    def get(self) -> T:
        """Get object from pool"""
        with self.lock:
            if self.available:
                obj = self.available.popleft()
                self.in_use.add(obj)
                self.total_reused += 1
                return obj
            else:
                # Create new object if pool is empty
                obj = self.factory()
                self.in_use.add(obj)
                self.total_created += 1
                return obj
    
    def return_object(self, obj: T):
        """Return object to pool"""
        with self.lock:
            if obj in self.in_use:
                # Reset object state if reset function provided
                if self.reset_func:
                    try:
                        self.reset_func(obj)
                    except Exception as e:
                        self.logger.error(f"Error resetting object: {e}")
                        return  # Don't return broken objects to pool
                
                # Return to pool if not at max capacity
                if len(self.available) < self.max_size:
                    self.available.append(obj)
                
                # Remove from in-use set (WeakSet will handle it automatically)
    
    def start_cleanup(self):
        """Start background cleanup task"""
        if not self.running:
            self.running = True
            self.cleanup_task = threading.Thread(target=self._cleanup_loop, daemon=True)
            self.cleanup_task.start()
    
    def _cleanup_loop(self):
        """Background cleanup loop"""
        while self.running:
            try:
                time.sleep(self.cleanup_interval)
                
                with self.lock:
                    # Remove excess objects from pool
                    while len(self.available) > self.max_size:
                        self.available.pop()
                    
                    # Ensure minimum pool size
                    while len(self.available) < self.min_size:
                        obj = self.factory()
                        self.available.append(obj)
                        self.total_created += 1
                
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get pool metrics"""
        with self.lock:
            return {
                'available': len(self.available),
                'in_use': len(self.in_use),
                'total_created': self.total_created,
                'total_reused': self.total_reused,
                'reuse_rate': self.total_reused / max(1, self.total_created + self.total_reused),
                'max_size': self.max_size,
                'min_size': self.min_size
            }
    
    def shutdown(self):
        """Shutdown object pool"""
        self.running = False
        if self.cleanup_task and self.cleanup_task.is_alive():
            self.cleanup_task.join(timeout=5)


class WeakReferenceManager:
    """Manages weak references to prevent memory leaks"""
    
    def __init__(self):
        self.weak_refs: Dict[str, weakref.WeakKeyDictionary] = defaultdict(weakref.WeakKeyDictionary)
        self.callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self.lock = threading.RLock()
        
        self.logger = logging.getLogger("WeakReferenceManager")
    
    def register(self, obj: Any, category: str, data: Any = None, 
                callback: Optional[Callable] = None) -> str:
        """Register object with weak reference"""
        with self.lock:
            # Create weak reference with callback
            ref_id = f"{category}_{id(obj)}"
            
            def cleanup_callback(ref):
                self._handle_object_cleanup(ref_id, category, callback)
            
            self.weak_refs[category][obj] = {
                'id': ref_id,
                'data': data,
                'created_at': datetime.now()
            }
            
            return ref_id
    
    def _handle_object_cleanup(self, ref_id: str, category: str, callback: Optional[Callable]):
        """Handle object cleanup when weak reference is collected"""
        try:
            if callback:
                callback(ref_id, category)
            
            self.logger.debug(f"Object {ref_id} in category {category} was garbage collected")
            
        except Exception as e:
            self.logger.error(f"Error in cleanup callback for {ref_id}: {e}")
    
    def get_live_objects(self, category: str) -> List[Any]:
        """Get all live objects in category"""
        with self.lock:
            return list(self.weak_refs[category].keys())
    
    def get_reference_count(self, category: str) -> int:
        """Get count of live references in category"""
        with self.lock:
            return len(self.weak_refs[category])
    
    def get_all_metrics(self) -> Dict[str, int]:
        """Get metrics for all categories"""
        with self.lock:
            return {category: len(refs) for category, refs in self.weak_refs.items()}


class MemoryManager:
    """Comprehensive memory management system"""
    
    def __init__(self, 
                 gc_threshold_mb: float = 500.0,
                 monitoring_interval: int = 60,
                 alert_threshold_percent: float = 85.0):
        
        self.gc_threshold_mb = gc_threshold_mb
        self.monitoring_interval = monitoring_interval
        self.alert_threshold_percent = alert_threshold_percent
        
        # Component managers
        self.object_pools: Dict[str, ObjectPool] = {}
        self.weak_ref_manager = WeakReferenceManager()
        
        # Memory tracking
        self.metrics = MemoryMetrics()
        self.memory_history: deque = deque(maxlen=1000)
        self.gc_stats = defaultdict(int)
        
        # Monitoring
        self.running = False
        self.monitor_task = None
        
        # Callbacks
        self.memory_callbacks: List[Callable] = []
        
        self.logger = logging.getLogger("MemoryManager")
        self.setup_logging()
        
        # Configure garbage collection
        self._configure_gc()
    
    def setup_logging(self):
        """Setup memory manager logging"""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def _configure_gc(self):
        """Configure garbage collection for optimal performance"""
        # Increase GC thresholds for better performance
        gc.set_threshold(1000, 15, 15)  # More lenient thresholds
        
        # Enable automatic garbage collection
        gc.enable()
        
        self.logger.info("Garbage collection configured")
    
    async def initialize(self):
        """Initialize memory manager"""
        self.running = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        
        # Start object pool cleanup tasks
        for pool in self.object_pools.values():
            pool.start_cleanup()
        
        self.logger.info("Memory manager initialized")
    
    def create_object_pool(self, name: str, factory: Callable[[], T], 
                          reset_func: Optional[Callable[[T], None]] = None,
                          max_size: int = 100, min_size: int = 10) -> ObjectPool[T]:
        """Create and register object pool"""
        pool = ObjectPool(factory, reset_func, max_size, min_size)
        self.object_pools[name] = pool
        pool.start_cleanup()
        
        self.logger.info(f"Created object pool '{name}' with max_size={max_size}")
        return pool
    
    def get_object_pool(self, name: str) -> Optional[ObjectPool]:
        """Get object pool by name"""
        return self.object_pools.get(name)
    
    def register_weak_reference(self, obj: Any, category: str, 
                              data: Any = None, callback: Optional[Callable] = None) -> str:
        """Register object with weak reference tracking"""
        return self.weak_ref_manager.register(obj, category, data, callback)
    
    def add_memory_callback(self, callback: Callable[[MemoryMetrics], None]):
        """Add callback for memory threshold alerts"""
        self.memory_callbacks.append(callback)
    
    async def _monitoring_loop(self):
        """Memory monitoring loop"""
        while self.running:
            try:
                await asyncio.sleep(self.monitoring_interval)
                
                # Update memory metrics
                await self._update_memory_metrics()
                
                # Check for memory pressure
                await self._check_memory_pressure()
                
                # Periodic garbage collection
                await self._perform_maintenance_gc()
                
                # Update history
                self.memory_history.append({
                    'timestamp': datetime.now(),
                    'memory_percent': self.metrics.memory_percent,
                    'used_memory_mb': self.metrics.used_memory_mb
                })
                
            except Exception as e:
                self.logger.error(f"Error in memory monitoring loop: {e}")
    
    async def _update_memory_metrics(self):
        """Update memory usage metrics"""
        try:
            # Get system memory info
            memory = psutil.virtual_memory()
            
            self.metrics.total_memory_mb = memory.total / 1024 / 1024
            self.metrics.used_memory_mb = memory.used / 1024 / 1024
            self.metrics.available_memory_mb = memory.available / 1024 / 1024
            self.metrics.memory_percent = memory.percent
            
            # Get garbage collection stats
            for generation in range(3):
                self.metrics.gc_collections[generation] = gc.get_stats()[generation]['collections']
            
            # Get object pool metrics
            self.metrics.object_pools = {
                name: pool.get_metrics()['available'] + pool.get_metrics()['in_use']
                for name, pool in self.object_pools.items()
            }
            
            # Get weak reference counts
            self.metrics.weak_references = sum(self.weak_ref_manager.get_all_metrics().values())
            
        except Exception as e:
            self.logger.error(f"Error updating memory metrics: {e}")
    
    async def _check_memory_pressure(self):
        """Check for memory pressure and take action"""
        try:
            if self.metrics.memory_percent > self.alert_threshold_percent:
                self.logger.warning(f"High memory usage detected: {self.metrics.memory_percent:.1f}%")
                
                # Trigger memory callbacks
                for callback in self.memory_callbacks:
                    try:
                        await callback(self.metrics)
                    except Exception as e:
                        self.logger.error(f"Error in memory callback: {e}")
                
                # Aggressive garbage collection
                await self._aggressive_gc()
                
                # Clear object pools if memory is critically high
                if self.metrics.memory_percent > 95.0:
                    await self._emergency_memory_cleanup()
        
        except Exception as e:
            self.logger.error(f"Error checking memory pressure: {e}")
    
    async def _perform_maintenance_gc(self):
        """Perform maintenance garbage collection"""
        try:
            # Check if we should run GC based on memory usage
            if self.metrics.used_memory_mb > self.gc_threshold_mb:
                collected = gc.collect()
                self.logger.debug(f"Maintenance GC collected {collected} objects")
        
        except Exception as e:
            self.logger.error(f"Error in maintenance GC: {e}")
    
    async def _aggressive_gc(self):
        """Perform aggressive garbage collection"""
        try:
            self.logger.info("Performing aggressive garbage collection")
            
            # Force collection of all generations
            for generation in range(3):
                collected = gc.collect(generation)
                self.logger.debug(f"GC generation {generation}: {collected} objects collected")
            
            # Clear internal caches
            sys.intern.clear()  # Clear string interning cache
            
        except Exception as e:
            self.logger.error(f"Error in aggressive GC: {e}")
    
    async def _emergency_memory_cleanup(self):
        """Emergency memory cleanup procedures"""
        try:
            self.logger.warning("Performing emergency memory cleanup")
            
            # Clear object pools to minimum size
            for name, pool in self.object_pools.items():
                with pool.lock:
                    while len(pool.available) > pool.min_size:
                        pool.available.pop()
                
                self.logger.info(f"Cleared object pool '{name}' to minimum size")
            
            # Force aggressive GC
            await self._aggressive_gc()
            
            # Log memory leak detection
            await self._detect_memory_leaks()
        
        except Exception as e:
            self.logger.error(f"Error in emergency memory cleanup: {e}")
    
    async def _detect_memory_leaks(self):
        """Detect potential memory leaks"""
        try:
            # Check for unusual object growth
            if len(self.memory_history) >= 2:
                recent = self.memory_history[-1]
                previous = self.memory_history[-2]
                
                memory_growth = recent['used_memory_mb'] - previous['used_memory_mb']
                
                if memory_growth > 50:  # 50MB growth
                    self.metrics.memory_leaks_detected += 1
                    self.logger.warning(f"Potential memory leak detected: {memory_growth:.1f}MB growth")
                    
                    # Log top object counts for debugging
                    self._log_object_counts()
        
        except Exception as e:
            self.logger.error(f"Error detecting memory leaks: {e}")
    
    def _log_object_counts(self):
        """Log object counts for debugging"""
        try:
            import collections
            
            # Get object counts by type
            object_counts = collections.Counter()
            for obj in gc.get_objects():
                obj_type = type(obj).__name__
                object_counts[obj_type] += 1
            
            # Log top 10 object types
            self.logger.info("Top object counts:")
            for obj_type, count in object_counts.most_common(10):
                self.logger.info(f"  {obj_type}: {count}")
        
        except Exception as e:
            self.logger.error(f"Error logging object counts: {e}")
    
    def get_memory_report(self) -> Dict[str, Any]:
        """Get comprehensive memory report"""
        return {
            'current_metrics': {
                'total_memory_mb': self.metrics.total_memory_mb,
                'used_memory_mb': self.metrics.used_memory_mb,
                'available_memory_mb': self.metrics.available_memory_mb,
                'memory_percent': self.metrics.memory_percent,
                'weak_references': self.metrics.weak_references,
                'memory_leaks_detected': self.metrics.memory_leaks_detected
            },
            'gc_stats': dict(self.metrics.gc_collections),
            'object_pools': {
                name: pool.get_metrics() 
                for name, pool in self.object_pools.items()
            },
            'weak_references': self.weak_ref_manager.get_all_metrics(),
            'memory_history': [
                {
                    'timestamp': entry['timestamp'].isoformat(),
                    'memory_percent': entry['memory_percent'],
                    'used_memory_mb': entry['used_memory_mb']
                }
                for entry in list(self.memory_history)[-10:]  # Last 10 entries
            ]
        }
    
    async def shutdown(self):
        """Shutdown memory manager"""
        self.running = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown object pools
        for pool in self.object_pools.values():
            pool.shutdown()
        
        self.logger.info("Memory manager shutdown complete")


# Utility functions for common object types
def create_dict_pool(max_size: int = 100) -> ObjectPool[Dict]:
    """Create object pool for dictionaries"""
    def dict_factory() -> Dict:
        return {}
    
    def dict_reset(d: Dict):
        d.clear()
    
    return ObjectPool(dict_factory, dict_reset, max_size)


def create_list_pool(max_size: int = 100) -> ObjectPool[List]:
    """Create object pool for lists"""
    def list_factory() -> List:
        return []
    
    def list_reset(lst: List):
        lst.clear()
    
    return ObjectPool(list_factory, list_reset, max_size)


def create_set_pool(max_size: int = 100) -> ObjectPool[set]:
    """Create object pool for sets"""
    def set_factory() -> set:
        return set()
    
    def set_reset(s: set):
        s.clear()
    
    return ObjectPool(set_factory, set_reset, max_size)


# Memory-optimized data structures
class MemoryEfficientDict(dict):
    """Memory-efficient dictionary with automatic cleanup"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        super().__init__()
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.access_times: Dict[Any, float] = {}
        self.insertion_order: deque = deque()
    
    def __setitem__(self, key, value):
        current_time = time.time()
        
        # Remove old item if it exists
        if key in self:
            self.insertion_order.remove(key)
        
        # Add new item
        super().__setitem__(key, value)
        self.access_times[key] = current_time
        self.insertion_order.append(key)
        
        # Cleanup if necessary
        self._cleanup()
    
    def __getitem__(self, key):
        # Update access time
        self.access_times[key] = time.time()
        return super().__getitem__(key)
    
    def _cleanup(self):
        """Clean up old or excess items"""
        current_time = time.time()
        
        # Remove expired items
        expired_keys = [
            key for key, access_time in self.access_times.items()
            if current_time - access_time > self.ttl_seconds
        ]
        
        for key in expired_keys:
            self._remove_key(key)
        
        # Remove excess items (LRU)
        while len(self) > self.max_size:
            oldest_key = self.insertion_order.popleft()
            self._remove_key(oldest_key)
    
    def _remove_key(self, key):
        """Remove key from all data structures"""
        if key in self:
            del self[key]
        if key in self.access_times:
            del self.access_times[key]
        if key in self.insertion_order:
            self.insertion_order.remove(key)