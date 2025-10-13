"""
Production-Grade Structured Logging and Observability
Provides structured logging, request tracing, and performance metrics
"""

import logging
import json
import time
import sys
import traceback
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from contextlib import contextmanager
from enum import Enum
import threading
import uuid

# Type alias for trace context
TraceContext = Dict[str, str]


class LogLevel(Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class StructuredLogEntry:
    """Structured log entry"""
    timestamp: str
    level: str
    message: str
    logger_name: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)
    exception: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            'timestamp': self.timestamp,
            'level': self.level,
            'message': self.message,
            'logger': self.logger_name
        }

        # Add optional fields if present
        if self.trace_id:
            result['trace_id'] = self.trace_id
        if self.span_id:
            result['span_id'] = self.span_id
        if self.user_id:
            result['user_id'] = self.user_id
        if self.request_id:
            result['request_id'] = self.request_id
        if self.extra_data:
            result['extra'] = self.extra_data
        if self.exception:
            result['exception'] = self.exception

        return result

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())


class StructuredLogger:
    """Structured logger with context support"""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)
        self._context_storage = threading.local()

    def set_context(self, **kwargs):
        """Set context for current thread"""
        if not hasattr(self._context_storage, 'context'):
            self._context_storage.context = {}
        self._context_storage.context.update(kwargs)

    def clear_context(self):
        """Clear context for current thread"""
        if hasattr(self._context_storage, 'context'):
            self._context_storage.context = {}

    def get_context(self) -> Dict[str, Any]:
        """Get context for current thread"""
        if not hasattr(self._context_storage, 'context'):
            return {}
        return self._context_storage.context.copy()

    def _create_entry(
        self,
        level: str,
        message: str,
        extra_data: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Exception] = None
    ) -> StructuredLogEntry:
        """Create structured log entry"""
        context = self.get_context()

        exception_data = None
        if exc_info:
            exception_data = {
                'type': type(exc_info).__name__,
                'message': str(exc_info),
                'traceback': traceback.format_exc()
            }

        return StructuredLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level,
            message=message,
            logger_name=self.name,
            trace_id=context.get('trace_id'),
            span_id=context.get('span_id'),
            user_id=context.get('user_id'),
            request_id=context.get('request_id'),
            extra_data=extra_data or {},
            exception=exception_data
        )

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        entry = self._create_entry('DEBUG', message, kwargs)
        self.logger.debug(entry.to_json())

    def info(self, message: str, **kwargs):
        """Log info message"""
        entry = self._create_entry('INFO', message, kwargs)
        self.logger.info(entry.to_json())

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        entry = self._create_entry('WARNING', message, kwargs)
        self.logger.warning(entry.to_json())

    def error(self, message: str, exc_info: Optional[Exception] = None, **kwargs):
        """Log error message"""
        entry = self._create_entry('ERROR', message, kwargs, exc_info)
        self.logger.error(entry.to_json())

    def critical(self, message: str, exc_info: Optional[Exception] = None, **kwargs):
        """Log critical message"""
        entry = self._create_entry('CRITICAL', message, kwargs, exc_info)
        self.logger.critical(entry.to_json())

    @contextmanager
    def with_context(self, **context):
        """Context manager for temporary context"""
        original_context = self.get_context()
        try:
            self.set_context(**context)
            yield
        finally:
            self.clear_context()
            self.set_context(**original_context)


class RequestTracer:
    """Distributed request tracing"""

    def __init__(self):
        self._storage = threading.local()

    def start_trace(self, trace_id: Optional[str] = None) -> str:
        """Start a new trace"""
        if trace_id is None:
            trace_id = str(uuid.uuid4())

        if not hasattr(self._storage, 'traces'):
            self._storage.traces = []

        self._storage.traces.append({
            'trace_id': trace_id,
            'start_time': time.time(),
            'spans': []
        })

        return trace_id

    def end_trace(self, trace_id: str):
        """End a trace"""
        if not hasattr(self._storage, 'traces'):
            return

        for trace in self._storage.traces:
            if trace['trace_id'] == trace_id:
                trace['end_time'] = time.time()
                trace['duration'] = trace['end_time'] - trace['start_time']
                break

    def start_span(self, operation: str, trace_id: Optional[str] = None) -> str:
        """Start a new span within a trace"""
        span_id = str(uuid.uuid4())

        if not hasattr(self._storage, 'traces') or not self._storage.traces:
            # No active trace, create one
            if trace_id is None:
                trace_id = self.start_trace()

        if hasattr(self._storage, 'traces') and self._storage.traces:
            # Find the trace
            for trace in self._storage.traces:
                if trace_id is None or trace['trace_id'] == trace_id:
                    trace['spans'].append({
                        'span_id': span_id,
                        'operation': operation,
                        'start_time': time.time(),
                        'trace_id': trace['trace_id']
                    })
                    break

        return span_id

    def end_span(self, span_id: str, **metadata):
        """End a span"""
        if not hasattr(self._storage, 'traces'):
            return

        for trace in self._storage.traces:
            for span in trace['spans']:
                if span['span_id'] == span_id:
                    span['end_time'] = time.time()
                    span['duration'] = span['end_time'] - span['start_time']
                    span['metadata'] = metadata
                    return

    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get trace by ID"""
        if not hasattr(self._storage, 'traces'):
            return None

        for trace in self._storage.traces:
            if trace['trace_id'] == trace_id:
                return trace.copy()

        return None

    def get_current_trace_id(self) -> Optional[str]:
        """Get current trace ID"""
        if not hasattr(self._storage, 'traces') or not self._storage.traces:
            return None
        return self._storage.traces[-1]['trace_id']

    @contextmanager
    def trace(self, operation: str, trace_id: Optional[str] = None):
        """Context manager for tracing"""
        if trace_id is None:
            trace_id = self.start_trace()

        span_id = self.start_span(operation, trace_id)

        try:
            yield {'trace_id': trace_id, 'span_id': span_id}
        finally:
            self.end_span(span_id)


class PerformanceMetrics:
    """Tracks performance metrics"""

    def __init__(self):
        self.metrics: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def record_operation(
        self,
        operation: str,
        duration: float,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record operation metrics"""
        with self._lock:
            self.metrics.append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'operation': operation,
                'duration': duration,
                'success': success,
                'metadata': metadata or {}
            })

            # Keep only last 10000 metrics
            if len(self.metrics) > 10000:
                self.metrics = self.metrics[-10000:]

    def get_operation_stats(self, operation: str) -> Dict[str, Any]:
        """Get statistics for an operation"""
        with self._lock:
            op_metrics = [m for m in self.metrics if m['operation'] == operation]

            if not op_metrics:
                return {}

            durations = [m['duration'] for m in op_metrics]
            successes = sum(1 for m in op_metrics if m['success'])

            return {
                'operation': operation,
                'count': len(op_metrics),
                'success_count': successes,
                'failure_count': len(op_metrics) - successes,
                'success_rate': successes / len(op_metrics),
                'avg_duration': sum(durations) / len(durations),
                'min_duration': min(durations),
                'max_duration': max(durations),
                'p50_duration': sorted(durations)[len(durations) // 2],
                'p95_duration': sorted(durations)[int(len(durations) * 0.95)],
                'p99_duration': sorted(durations)[int(len(durations) * 0.99)]
            }

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all operations"""
        with self._lock:
            operations = set(m['operation'] for m in self.metrics)
            return {
                op: self.get_operation_stats(op)
                for op in operations
            }

    @contextmanager
    def track_operation(self, operation: str, metadata: Optional[Dict[str, Any]] = None):
        """Context manager for tracking operation performance"""
        start_time = time.time()
        success = True

        try:
            yield
        except Exception:
            success = False
            raise
        finally:
            duration = time.time() - start_time
            self.record_operation(operation, duration, success, metadata)


class ObservabilitySystem:
    """Complete observability system"""

    def __init__(self, app_name: str):
        self.app_name = app_name
        self.tracer = RequestTracer()
        self.performance = PerformanceMetrics()
        self.loggers: Dict[str, StructuredLogger] = {}

    def get_logger(self, name: str) -> StructuredLogger:
        """Get or create structured logger"""
        if name not in self.loggers:
            self.loggers[name] = StructuredLogger(f"{self.app_name}.{name}")
        return self.loggers[name]

    @contextmanager
    def trace_request(self, operation: str, **context):
        """Trace a request with logging and metrics"""
        logger = self.get_logger(operation)

        # Start trace
        trace_id = self.tracer.start_trace()
        span_id = self.tracer.start_span(operation, trace_id)

        # Set logger context
        logger.set_context(trace_id=trace_id, span_id=span_id, **context)

        # Log start
        logger.info(f"Starting {operation}", **context)

        start_time = time.time()
        success = True

        try:
            yield {'trace_id': trace_id, 'span_id': span_id, 'logger': logger}
        except Exception as e:
            success = False
            logger.error(f"Error in {operation}", exc_info=e, **context)
            raise
        finally:
            # Calculate duration
            duration = time.time() - start_time

            # End span and trace
            self.tracer.end_span(span_id, duration=duration, success=success)
            self.tracer.end_trace(trace_id)

            # Record metrics
            self.performance.record_operation(operation, duration, success, context)

            # Log completion
            logger.info(
                f"Completed {operation}",
                duration=duration,
                success=success,
                **context
            )

            # Clear logger context
            logger.clear_context()

    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        return {
            'app_name': self.app_name,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'operation_stats': self.performance.get_all_stats()
        }

    def export_traces(self, trace_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Export traces for analysis"""
        # In production, this would send to a tracing backend (Jaeger, Zipkin, etc.)
        traces = []

        if trace_ids:
            for trace_id in trace_ids:
                trace = self.tracer.get_trace(trace_id)
                if trace:
                    traces.append(trace)
        else:
            # Export all traces (not recommended in production)
            if hasattr(self.tracer._storage, 'traces'):
                traces = self.tracer._storage.traces.copy()

        return traces


# Global observability system instance
observability_system: Optional[ObservabilitySystem] = None


def initialize_observability(app_name: str) -> ObservabilitySystem:
    """Initialize global observability system"""
    global observability_system
    observability_system = ObservabilitySystem(app_name)
    return observability_system


def get_observability() -> Optional[ObservabilitySystem]:
    """Get global observability system"""
    return observability_system


# JSON formatter for standard logging
class JsonFormatter(logging.Formatter):
    """JSON formatter for standard Python logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }

        return json.dumps(log_data)


def setup_json_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    console_output: bool = True
):
    """Setup JSON logging for the application"""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    root_logger.handlers = []

    formatter = JsonFormatter()

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler
    if log_file:
        import os
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
