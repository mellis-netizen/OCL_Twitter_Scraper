#!/usr/bin/env python3
"""
Advanced Performance Monitoring and Metrics Collection for TGE Swarm
Provides real-time performance monitoring, alerting, and auto-scaling capabilities
"""

import asyncio
import logging
import time
import psutil
import threading
from typing import Dict, List, Any, Optional, Callable, NamedTuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import statistics
import json
import weakref


@dataclass
class MetricPoint:
    """Single metric data point"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""


@dataclass
class AlertRule:
    """Performance alert rule"""
    name: str
    metric_name: str
    condition: str  # 'gt', 'lt', 'eq', 'ge', 'le'
    threshold: float
    duration: int  # seconds
    callback: Optional[Callable] = None
    enabled: bool = True


@dataclass
class PerformanceThresholds:
    """Performance threshold configuration"""
    cpu_warning: float = 70.0
    cpu_critical: float = 90.0
    memory_warning: float = 75.0
    memory_critical: float = 90.0
    response_time_warning: float = 1.0
    response_time_critical: float = 5.0
    error_rate_warning: float = 0.05
    error_rate_critical: float = 0.10
    throughput_min: float = 10.0


class MetricsCollector:
    """High-performance metrics collection system"""
    
    def __init__(self, retention_hours: int = 24, sample_interval: float = 1.0):
        self.retention_hours = retention_hours
        self.sample_interval = sample_interval
        
        # Metric storage
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=int(retention_hours * 3600 / sample_interval)))
        self.gauges: Dict[str, float] = {}
        self.counters: Dict[str, int] = defaultdict(int)
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Background collection
        self.running = False
        self.collection_tasks: List[asyncio.Task] = []
        
        self.logger = logging.getLogger("MetricsCollector")
    
    async def initialize(self):
        """Initialize metrics collector"""
        self.running = True
        
        # Start system metrics collection
        system_task = asyncio.create_task(self._collect_system_metrics())
        self.collection_tasks.append(system_task)
        
        self.logger.info("Metrics collector initialized")
    
    def record_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record gauge metric"""
        with self.lock:
            self.gauges[name] = value
            
            # Store in time series
            metric_point = MetricPoint(
                name=name,
                value=value,
                timestamp=datetime.now(),
                tags=tags or {}
            )
            self.metrics[name].append(metric_point)
    
    def increment_counter(self, name: str, value: int = 1, tags: Dict[str, str] = None):
        """Increment counter metric"""
        with self.lock:
            self.counters[name] += value
            
            # Store increment event
            metric_point = MetricPoint(
                name=name,
                value=value,
                timestamp=datetime.now(),
                tags=tags or {}
            )
            self.metrics[f"{name}_increments"].append(metric_point)
    
    def record_timing(self, name: str, duration: float, tags: Dict[str, str] = None):
        """Record timing metric"""
        with self.lock:
            self.histograms[name].append(duration)
            
            # Keep histogram size manageable
            if len(self.histograms[name]) > 1000:
                self.histograms[name] = self.histograms[name][-1000:]
            
            # Store timing event
            metric_point = MetricPoint(
                name=name,
                value=duration,
                timestamp=datetime.now(),
                tags=tags or {},
                unit="seconds"
            )
            self.metrics[name].append(metric_point)
    
    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record histogram value"""
        with self.lock:
            self.histograms[name].append(value)
            
            # Keep histogram size manageable
            if len(self.histograms[name]) > 1000:
                self.histograms[name] = self.histograms[name][-1000:]
    
    async def _collect_system_metrics(self):
        """Collect system-level metrics"""
        while self.running:
            try:
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=None)
                self.record_gauge("system.cpu.percent", cpu_percent)
                
                # Memory metrics
                memory = psutil.virtual_memory()
                self.record_gauge("system.memory.percent", memory.percent)
                self.record_gauge("system.memory.used_gb", memory.used / 1024**3)
                self.record_gauge("system.memory.available_gb", memory.available / 1024**3)
                
                # Disk metrics
                disk = psutil.disk_usage('/')
                self.record_gauge("system.disk.percent", disk.percent)
                
                # Network metrics (if available)
                try:
                    network = psutil.net_io_counters()
                    self.record_gauge("system.network.bytes_sent", network.bytes_sent)
                    self.record_gauge("system.network.bytes_recv", network.bytes_recv)
                except:
                    pass  # Network stats might not be available
                
                # Process metrics
                process = psutil.Process()
                self.record_gauge("process.cpu.percent", process.cpu_percent())
                self.record_gauge("process.memory.rss_mb", process.memory_info().rss / 1024**2)
                self.record_gauge("process.memory.vms_mb", process.memory_info().vms / 1024**2)
                self.record_gauge("process.threads", process.num_threads())
                
                await asyncio.sleep(self.sample_interval)
                
            except Exception as e:
                self.logger.error(f"Error collecting system metrics: {e}")
                await asyncio.sleep(5)
    
    def get_gauge(self, name: str) -> Optional[float]:
        """Get current gauge value"""
        with self.lock:
            return self.gauges.get(name)
    
    def get_counter(self, name: str) -> int:
        """Get current counter value"""
        with self.lock:
            return self.counters.get(name, 0)
    
    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """Get histogram statistics"""
        with self.lock:
            values = self.histograms.get(name, [])
            
            if not values:
                return {}
            
            return {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'mean': statistics.mean(values),
                'median': statistics.median(values),
                'p95': statistics.quantiles(values, n=20)[18] if len(values) > 5 else max(values),
                'p99': statistics.quantiles(values, n=100)[98] if len(values) > 10 else max(values)
            }
    
    def get_metric_history(self, name: str, since: datetime = None) -> List[MetricPoint]:
        """Get metric history"""
        with self.lock:
            history = list(self.metrics.get(name, []))
            
            if since:
                history = [point for point in history if point.timestamp >= since]
            
            return history
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metrics"""
        with self.lock:
            return {
                'gauges': self.gauges.copy(),
                'counters': dict(self.counters),
                'histogram_stats': {
                    name: self.get_histogram_stats(name)
                    for name in self.histograms.keys()
                },
                'timestamp': datetime.now().isoformat()
            }
    
    async def shutdown(self):
        """Shutdown metrics collector"""
        self.running = False
        
        # Cancel collection tasks
        for task in self.collection_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.collection_tasks:
            await asyncio.gather(*self.collection_tasks, return_exceptions=True)
        
        self.logger.info("Metrics collector shutdown complete")


class PerformanceMonitor:
    """Advanced performance monitoring with alerting"""
    
    def __init__(self, 
                 thresholds: PerformanceThresholds = None,
                 alert_check_interval: int = 30):
        
        self.thresholds = thresholds or PerformanceThresholds()
        self.alert_check_interval = alert_check_interval
        
        # Components
        self.metrics_collector = MetricsCollector()
        
        # Alerting
        self.alert_rules: List[AlertRule] = []
        self.active_alerts: Dict[str, datetime] = {}
        self.alert_callbacks: List[Callable] = []
        
        # Performance tracking
        self.timers: Dict[str, float] = {}
        self.timer_lock = threading.RLock()
        
        # Background monitoring
        self.running = False
        self.monitor_tasks: List[asyncio.Task] = []
        
        self.logger = logging.getLogger("PerformanceMonitor")
        self.setup_logging()
        
        # Setup default alert rules
        self._setup_default_alerts()
    
    def setup_logging(self):
        """Setup performance monitor logging"""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def _setup_default_alerts(self):
        """Setup default performance alerts"""
        # CPU alerts
        self.add_alert_rule(AlertRule(
            name="high_cpu_warning",
            metric_name="system.cpu.percent",
            condition="gt",
            threshold=self.thresholds.cpu_warning,
            duration=60
        ))
        
        self.add_alert_rule(AlertRule(
            name="high_cpu_critical",
            metric_name="system.cpu.percent",
            condition="gt",
            threshold=self.thresholds.cpu_critical,
            duration=30
        ))
        
        # Memory alerts
        self.add_alert_rule(AlertRule(
            name="high_memory_warning",
            metric_name="system.memory.percent",
            condition="gt",
            threshold=self.thresholds.memory_warning,
            duration=60
        ))
        
        self.add_alert_rule(AlertRule(
            name="high_memory_critical",
            metric_name="system.memory.percent",
            condition="gt",
            threshold=self.thresholds.memory_critical,
            duration=30
        ))
    
    async def initialize(self):
        """Initialize performance monitor"""
        await self.metrics_collector.initialize()
        
        self.running = True
        
        # Start monitoring loops
        alert_task = asyncio.create_task(self._alert_monitoring_loop())
        self.monitor_tasks.append(alert_task)
        
        # Start performance analysis
        analysis_task = asyncio.create_task(self._performance_analysis_loop())
        self.monitor_tasks.append(analysis_task)
        
        self.logger.info("Performance monitor initialized")
    
    def add_alert_rule(self, rule: AlertRule):
        """Add performance alert rule"""
        self.alert_rules.append(rule)
        self.logger.info(f"Added alert rule: {rule.name}")
    
    def add_alert_callback(self, callback: Callable[[str, AlertRule, float], None]):
        """Add alert callback function"""
        self.alert_callbacks.append(callback)
    
    def start_timer(self, name: str) -> str:
        """Start performance timer"""
        timer_id = f"{name}_{int(time.time() * 1000000)}"
        
        with self.timer_lock:
            self.timers[timer_id] = time.time()
        
        return timer_id
    
    def end_timer(self, timer_id: str) -> float:
        """End performance timer and record metric"""
        with self.timer_lock:
            if timer_id not in self.timers:
                return 0.0
            
            start_time = self.timers.pop(timer_id)
            duration = time.time() - start_time
            
            # Extract metric name from timer ID
            metric_name = timer_id.rsplit('_', 1)[0]
            self.metrics_collector.record_timing(metric_name, duration)
            
            return duration
    
    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record performance metric"""
        self.metrics_collector.record_gauge(name, value, tags)
    
    def increment_counter(self, name: str, value: int = 1, tags: Dict[str, str] = None):
        """Increment performance counter"""
        self.metrics_collector.increment_counter(name, value, tags)
    
    def record_timing(self, name: str, duration: float, tags: Dict[str, str] = None):
        """Record timing metric"""
        self.metrics_collector.record_timing(name, duration, tags)
    
    async def _alert_monitoring_loop(self):
        """Monitor metrics for alert conditions"""
        while self.running:
            try:
                await asyncio.sleep(self.alert_check_interval)
                
                current_time = datetime.now()
                
                for rule in self.alert_rules:
                    if not rule.enabled:
                        continue
                    
                    # Get current metric value
                    current_value = self.metrics_collector.get_gauge(rule.metric_name)
                    
                    if current_value is None:
                        continue
                    
                    # Check alert condition
                    is_triggered = self._check_alert_condition(rule, current_value)
                    
                    if is_triggered:
                        # Check if alert should fire based on duration
                        if rule.name not in self.active_alerts:
                            self.active_alerts[rule.name] = current_time
                        elif (current_time - self.active_alerts[rule.name]).total_seconds() >= rule.duration:
                            # Fire alert
                            await self._fire_alert(rule, current_value)
                    else:
                        # Clear alert if condition is no longer met
                        if rule.name in self.active_alerts:
                            del self.active_alerts[rule.name]
                
            except Exception as e:
                self.logger.error(f"Error in alert monitoring loop: {e}")
    
    def _check_alert_condition(self, rule: AlertRule, value: float) -> bool:
        """Check if alert condition is met"""
        if rule.condition == "gt":
            return value > rule.threshold
        elif rule.condition == "lt":
            return value < rule.threshold
        elif rule.condition == "ge":
            return value >= rule.threshold
        elif rule.condition == "le":
            return value <= rule.threshold
        elif rule.condition == "eq":
            return abs(value - rule.threshold) < 0.001
        else:
            return False
    
    async def _fire_alert(self, rule: AlertRule, value: float):
        """Fire performance alert"""
        self.logger.warning(f"ALERT: {rule.name} - {rule.metric_name} = {value:.2f} (threshold: {rule.threshold})")
        
        # Call rule-specific callback
        if rule.callback:
            try:
                if asyncio.iscoroutinefunction(rule.callback):
                    await rule.callback(rule.name, rule, value)
                else:
                    rule.callback(rule.name, rule, value)
            except Exception as e:
                self.logger.error(f"Error in alert callback for {rule.name}: {e}")
        
        # Call general alert callbacks
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(rule.name, rule, value)
                else:
                    callback(rule.name, rule, value)
            except Exception as e:
                self.logger.error(f"Error in general alert callback: {e}")
    
    async def _performance_analysis_loop(self):
        """Analyze performance trends and patterns"""
        while self.running:
            try:
                await asyncio.sleep(300)  # Analyze every 5 minutes
                
                # Analyze response time trends
                await self._analyze_response_times()
                
                # Analyze throughput patterns
                await self._analyze_throughput()
                
                # Analyze resource utilization
                await self._analyze_resource_utilization()
                
            except Exception as e:
                self.logger.error(f"Error in performance analysis loop: {e}")
    
    async def _analyze_response_times(self):
        """Analyze response time patterns"""
        try:
            # Get recent response time data
            since = datetime.now() - timedelta(minutes=15)
            
            for metric_name in ['task_processing_time', 'message_publish_time', 'query_time']:
                history = self.metrics_collector.get_metric_history(metric_name, since)
                
                if len(history) < 10:
                    continue
                
                # Calculate statistics
                values = [point.value for point in history]
                avg_time = statistics.mean(values)
                p95_time = statistics.quantiles(values, n=20)[18] if len(values) > 5 else max(values)
                
                # Record derived metrics
                self.metrics_collector.record_gauge(f"{metric_name}.avg_15min", avg_time)
                self.metrics_collector.record_gauge(f"{metric_name}.p95_15min", p95_time)
                
                # Check for performance degradation
                if avg_time > self.thresholds.response_time_warning:
                    self.logger.warning(f"High average {metric_name}: {avg_time:.3f}s")
        
        except Exception as e:
            self.logger.error(f"Error analyzing response times: {e}")
    
    async def _analyze_throughput(self):
        """Analyze throughput patterns"""
        try:
            # Calculate message throughput
            message_count = self.metrics_collector.get_counter('messages_processed')
            
            # Record throughput metric
            current_time = time.time()
            if hasattr(self, '_last_throughput_check'):
                time_diff = current_time - self._last_throughput_check
                message_diff = message_count - getattr(self, '_last_message_count', 0)
                
                if time_diff > 0:
                    throughput = message_diff / time_diff
                    self.metrics_collector.record_gauge('throughput.messages_per_second', throughput)
                    
                    if throughput < self.thresholds.throughput_min:
                        self.logger.warning(f"Low throughput detected: {throughput:.2f} msg/s")
            
            self._last_throughput_check = current_time
            self._last_message_count = message_count
            
        except Exception as e:
            self.logger.error(f"Error analyzing throughput: {e}")
    
    async def _analyze_resource_utilization(self):
        """Analyze resource utilization patterns"""
        try:
            # Get resource metrics
            cpu_usage = self.metrics_collector.get_gauge('system.cpu.percent')
            memory_usage = self.metrics_collector.get_gauge('system.memory.percent')
            
            if cpu_usage is not None and memory_usage is not None:
                # Calculate resource pressure score
                resource_pressure = max(cpu_usage / 100.0, memory_usage / 100.0)
                self.metrics_collector.record_gauge('resource_pressure_score', resource_pressure)
                
                # Analyze trends
                history = self.metrics_collector.get_metric_history(
                    'resource_pressure_score',
                    datetime.now() - timedelta(minutes=30)
                )
                
                if len(history) > 10:
                    values = [point.value for point in history]
                    trend = statistics.linear_regression(range(len(values)), values).slope
                    
                    self.metrics_collector.record_gauge('resource_pressure_trend', trend)
                    
                    if trend > 0.01:  # Increasing pressure
                        self.logger.warning("Increasing resource pressure trend detected")
        
        except Exception as e:
            self.logger.error(f"Error analyzing resource utilization: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        all_metrics = self.metrics_collector.get_all_metrics()
        
        # Add alert information
        all_metrics['alerts'] = {
            'active_alerts': list(self.active_alerts.keys()),
            'alert_rules_count': len(self.alert_rules),
            'enabled_rules': len([r for r in self.alert_rules if r.enabled])
        }
        
        # Add performance analysis
        all_metrics['performance_analysis'] = {
            'response_time_stats': self.metrics_collector.get_histogram_stats('task_processing_time'),
            'throughput_current': self.metrics_collector.get_gauge('throughput.messages_per_second'),
            'resource_pressure': self.metrics_collector.get_gauge('resource_pressure_score')
        }
        
        return all_metrics
    
    def export_metrics_prometheus(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        timestamp = int(time.time() * 1000)
        
        # Export gauges
        for name, value in self.metrics_collector.gauges.items():
            prometheus_name = name.replace('.', '_').replace('-', '_')
            lines.append(f"# TYPE {prometheus_name} gauge")
            lines.append(f"{prometheus_name} {value} {timestamp}")
        
        # Export counters
        for name, value in self.metrics_collector.counters.items():
            prometheus_name = name.replace('.', '_').replace('-', '_')
            lines.append(f"# TYPE {prometheus_name} counter")
            lines.append(f"{prometheus_name} {value} {timestamp}")
        
        return '\n'.join(lines)
    
    async def shutdown(self):
        """Shutdown performance monitor"""
        self.running = False
        
        # Cancel monitor tasks
        for task in self.monitor_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.monitor_tasks:
            await asyncio.gather(*self.monitor_tasks, return_exceptions=True)
        
        # Shutdown metrics collector
        await self.metrics_collector.shutdown()
        
        self.logger.info("Performance monitor shutdown complete")


# Context manager for easy timing
class TimerContext:
    """Context manager for measuring execution time"""
    
    def __init__(self, monitor: PerformanceMonitor, name: str):
        self.monitor = monitor
        self.name = name
        self.timer_id = None
        self.start_time = None
    
    def __enter__(self):
        self.timer_id = self.monitor.start_timer(self.name)
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.timer_id:
            duration = self.monitor.end_timer(self.timer_id)
            return duration
        return 0.0


# Decorator for automatic timing
def monitor_performance(monitor: PerformanceMonitor, metric_name: str = None):
    """Decorator for automatic performance monitoring"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            name = metric_name or f"{func.__module__}.{func.__name__}"
            
            with TimerContext(monitor, name):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Async decorator for automatic timing
def monitor_async_performance(monitor: PerformanceMonitor, metric_name: str = None):
    """Decorator for automatic async performance monitoring"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            name = metric_name or f"{func.__module__}.{func.__name__}"
            
            with TimerContext(monitor, name):
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator