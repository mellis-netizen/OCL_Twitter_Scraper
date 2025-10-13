"""
Production-Grade Monitoring and Alerting System
Provides health checks, metrics collection, and alerting capabilities
"""

import os
import logging
import psutil
import time
import json
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    component: str
    status: HealthStatus
    message: str
    response_time_ms: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'component': self.component,
            'status': self.status.value,
            'message': self.message,
            'response_time_ms': self.response_time_ms,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }


@dataclass
class MetricPoint:
    """Single metric data point"""
    name: str
    value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'tags': self.tags
        }


@dataclass
class Alert:
    """System alert"""
    title: str
    message: str
    severity: AlertSeverity
    component: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'title': self.title,
            'message': self.message,
            'severity': self.severity.value,
            'component': self.component,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }


class HealthChecker:
    """Manages health checks for different system components"""

    def __init__(self):
        self.health_checks: Dict[str, Callable] = {}
        self.last_results: Dict[str, HealthCheckResult] = {}
        self.check_interval = 60  # seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def register_check(self, component: str, check_func: Callable[[], HealthCheckResult]):
        """Register a health check function"""
        self.health_checks[component] = check_func
        logger.info(f"Registered health check for: {component}")

    def run_check(self, component: str) -> HealthCheckResult:
        """Run health check for a specific component"""
        if component not in self.health_checks:
            return HealthCheckResult(
                component=component,
                status=HealthStatus.UNKNOWN,
                message=f"No health check registered for {component}",
                response_time_ms=0
            )

        start_time = time.time()
        try:
            result = self.health_checks[component]()
            result.response_time_ms = (time.time() - start_time) * 1000
            self.last_results[component] = result
            return result
        except Exception as e:
            logger.error(f"Health check failed for {component}: {str(e)}")
            result = HealthCheckResult(
                component=component,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check error: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000
            )
            self.last_results[component] = result
            return result

    def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks"""
        results = {}
        for component in self.health_checks:
            results[component] = self.run_check(component)
        return results

    def get_overall_status(self) -> HealthStatus:
        """Get overall system health status"""
        if not self.last_results:
            return HealthStatus.UNKNOWN

        statuses = [result.status for result in self.last_results.values()]

        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN

    def start_monitoring(self):
        """Start continuous health monitoring"""
        if self._running:
            logger.warning("Health monitoring already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._thread.start()
        logger.info("Health monitoring started")

    def stop_monitoring(self):
        """Stop continuous health monitoring"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Health monitoring stopped")

    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self._running:
            try:
                self.run_all_checks()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(self.check_interval)


class MetricsCollector:
    """Collects and aggregates system metrics"""

    def __init__(self, retention_period: int = 3600):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.retention_period = retention_period  # seconds
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self._lock = threading.Lock()

    def record(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a metric value"""
        with self._lock:
            metric = MetricPoint(name=name, value=value, tags=tags or {})
            self.metrics[name].append(metric)

    def increment(self, name: str, value: float = 1.0):
        """Increment a counter"""
        with self._lock:
            self.counters[name] += value

    def set_gauge(self, name: str, value: float):
        """Set a gauge value"""
        with self._lock:
            self.gauges[name] = value

    def get_metric_stats(self, name: str, window_seconds: int = 60) -> Dict[str, float]:
        """Get statistics for a metric within time window"""
        with self._lock:
            if name not in self.metrics:
                return {}

            cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
            recent_values = [
                m.value for m in self.metrics[name]
                if m.timestamp >= cutoff_time
            ]

            if not recent_values:
                return {}

            return {
                'count': len(recent_values),
                'min': min(recent_values),
                'max': max(recent_values),
                'mean': sum(recent_values) / len(recent_values),
                'sum': sum(recent_values)
            }

    def get_counter(self, name: str) -> float:
        """Get counter value"""
        with self._lock:
            return self.counters.get(name, 0.0)

    def get_gauge(self, name: str) -> Optional[float]:
        """Get gauge value"""
        with self._lock:
            return self.gauges.get(name)

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics"""
        with self._lock:
            return {
                'counters': dict(self.counters),
                'gauges': dict(self.gauges),
                'time_series': {
                    name: [m.to_dict() for m in list(values)[-100:]]
                    for name, values in self.metrics.items()
                }
            }

    def cleanup_old_metrics(self):
        """Remove metrics older than retention period"""
        with self._lock:
            cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=self.retention_period)

            for name in list(self.metrics.keys()):
                self.metrics[name] = deque(
                    [m for m in self.metrics[name] if m.timestamp >= cutoff_time],
                    maxlen=self.metrics[name].maxlen
                )


class SystemMonitor:
    """Monitors system resource usage"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.collection_interval = 10  # seconds

    def collect_system_metrics(self):
        """Collect current system metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics.set_gauge('system.cpu_percent', cpu_percent)

            # Memory usage
            memory = psutil.virtual_memory()
            self.metrics.set_gauge('system.memory_percent', memory.percent)
            self.metrics.set_gauge('system.memory_available_mb', memory.available / 1024 / 1024)

            # Disk usage
            disk = psutil.disk_usage('/')
            self.metrics.set_gauge('system.disk_percent', disk.percent)
            self.metrics.set_gauge('system.disk_free_gb', disk.free / 1024 / 1024 / 1024)

            # Process info
            process = psutil.Process()
            self.metrics.set_gauge('process.memory_mb', process.memory_info().rss / 1024 / 1024)
            self.metrics.set_gauge('process.cpu_percent', process.cpu_percent())
            self.metrics.set_gauge('process.num_threads', process.num_threads())

            # Network I/O
            net_io = psutil.net_io_counters()
            self.metrics.set_gauge('network.bytes_sent', net_io.bytes_sent)
            self.metrics.set_gauge('network.bytes_recv', net_io.bytes_recv)

        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}")

    def start_monitoring(self):
        """Start continuous system monitoring"""
        if self._running:
            logger.warning("System monitoring already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._thread.start()
        logger.info("System monitoring started")

    def stop_monitoring(self):
        """Stop continuous system monitoring"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("System monitoring stopped")

    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self._running:
            try:
                self.collect_system_metrics()
                time.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"Error in system monitoring loop: {str(e)}")
                time.sleep(self.collection_interval)


class AlertManager:
    """Manages system alerts and notifications"""

    def __init__(self, max_alerts: int = 1000):
        self.alerts: deque = deque(maxlen=max_alerts)
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        self.alert_counts: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

    def register_callback(self, callback: Callable[[Alert], None]):
        """Register callback to be called when alert is raised"""
        self.alert_callbacks.append(callback)
        logger.info(f"Registered alert callback: {callback.__name__}")

    def raise_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        component: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Raise a new alert"""
        alert = Alert(
            title=title,
            message=message,
            severity=severity,
            component=component,
            metadata=metadata or {}
        )

        with self._lock:
            self.alerts.append(alert)
            self.alert_counts[severity.value] += 1

        # Log alert
        log_msg = f"ALERT [{severity.value.upper()}] {component}: {title} - {message}"
        if severity == AlertSeverity.CRITICAL:
            logger.critical(log_msg)
        elif severity == AlertSeverity.ERROR:
            logger.error(log_msg)
        elif severity == AlertSeverity.WARNING:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        # Execute callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {str(e)}")

    def get_recent_alerts(self, count: int = 100) -> List[Alert]:
        """Get recent alerts"""
        with self._lock:
            return list(self.alerts)[-count:]

    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[Alert]:
        """Get alerts by severity"""
        with self._lock:
            return [a for a in self.alerts if a.severity == severity]

    def get_alerts_by_component(self, component: str) -> List[Alert]:
        """Get alerts by component"""
        with self._lock:
            return [a for a in self.alerts if a.component == component]

    def get_alert_counts(self) -> Dict[str, int]:
        """Get alert counts by severity"""
        with self._lock:
            return dict(self.alert_counts)

    def clear_alerts(self):
        """Clear all alerts"""
        with self._lock:
            self.alerts.clear()
            self.alert_counts.clear()
        logger.info("All alerts cleared")


class MonitoringSystem:
    """Complete monitoring and alerting system"""

    def __init__(self):
        self.health_checker = HealthChecker()
        self.metrics = MetricsCollector()
        self.system_monitor = SystemMonitor(self.metrics)
        self.alert_manager = AlertManager()

        # Register default health checks
        self._register_default_health_checks()

        logger.info("Monitoring system initialized")

    def _register_default_health_checks(self):
        """Register default health checks"""

        def check_system_resources() -> HealthCheckResult:
            """Check system resource availability"""
            cpu = psutil.cpu_percent()
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent

            if cpu > 90 or memory > 90 or disk > 90:
                status = HealthStatus.UNHEALTHY
                message = f"High resource usage: CPU={cpu}%, Memory={memory}%, Disk={disk}%"
            elif cpu > 70 or memory > 70 or disk > 80:
                status = HealthStatus.DEGRADED
                message = f"Elevated resource usage: CPU={cpu}%, Memory={memory}%, Disk={disk}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Resources OK: CPU={cpu}%, Memory={memory}%, Disk={disk}%"

            return HealthCheckResult(
                component="system_resources",
                status=status,
                message=message,
                response_time_ms=0,
                metadata={
                    'cpu_percent': cpu,
                    'memory_percent': memory,
                    'disk_percent': disk
                }
            )

        self.health_checker.register_check("system_resources", check_system_resources)

    def start(self):
        """Start all monitoring components"""
        self.health_checker.start_monitoring()
        self.system_monitor.start_monitoring()
        logger.info("Monitoring system started")

    def stop(self):
        """Stop all monitoring components"""
        self.health_checker.stop_monitoring()
        self.system_monitor.stop_monitoring()
        logger.info("Monitoring system stopped")

    def get_status_report(self) -> Dict[str, Any]:
        """Get comprehensive status report"""
        health_results = self.health_checker.run_all_checks()

        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overall_status': self.health_checker.get_overall_status().value,
            'health_checks': {
                name: result.to_dict()
                for name, result in health_results.items()
            },
            'metrics': self.metrics.get_all_metrics(),
            'alerts': {
                'recent': [a.to_dict() for a in self.alert_manager.get_recent_alerts(50)],
                'counts': self.alert_manager.get_alert_counts()
            }
        }

    def save_status_report(self, filepath: str):
        """Save status report to file"""
        try:
            report = self.get_status_report()
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Status report saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save status report: {str(e)}")


# Global monitoring system instance
monitoring_system = MonitoringSystem()
