#!/usr/bin/env python3
"""
Test Helper Utilities
Provides common utilities and helpers for testing
"""

import asyncio
import random
import string
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Callable, AsyncGenerator
import tempfile
import shutil
from pathlib import Path
from contextlib import asynccontextmanager

from backend.message_queue import SwarmMessage, MessageType, Priority, TaskDefinition
from backend.agent_manager import AgentSpec, AgentType, AgentStatus
from backend.database.models import Agent, Task, OptimizationRecommendation


class DataGenerators:
    """Utility class for generating test data"""
    
    @staticmethod
    def random_string(length: int = 10) -> str:
        """Generate random string of specified length"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def random_uuid() -> str:
        """Generate random UUID string"""
        return str(uuid.uuid4())
    
    @staticmethod
    def random_timestamp(days_ago: int = 0) -> datetime:
        """Generate random timestamp"""
        base_time = datetime.now(timezone.utc) - timedelta(days=days_ago)
        random_offset = timedelta(
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )
        return base_time + random_offset
    
    @staticmethod
    def generate_agent_data(override: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate test agent data"""
        data = {
            'name': f'test-agent-{DataGenerators.random_string(6)}',
            'agent_type': random.choice(['scraping-efficiency', 'keyword-precision', 'performance-optimizer']),
            'container_id': f'container-{DataGenerators.random_string(8)}',
            'status': random.choice(list(AgentStatus)),
            'host': 'localhost',
            'port': random.randint(8000, 9000),
            'version': f'1.{random.randint(0, 9)}.{random.randint(0, 9)}',
            'cpu_limit': round(random.uniform(0.5, 2.0), 1),
            'memory_limit': f'{random.randint(256, 2048)}m',
            'capabilities': random.sample(['nlp', 'text-analysis', 'optimization', 'scraping'], k=2),
            'specializations': [f'spec-{DataGenerators.random_string(4)}'],
            'environment': {
                'LOG_LEVEL': 'DEBUG',
                'REDIS_URL': 'redis://localhost:6379'
            },
            'health_checks': [],
            'performance_metrics': {
                'avg_response_time': round(random.uniform(0.1, 2.0), 2),
                'success_rate': round(random.uniform(0.8, 1.0), 2)
            }
        }
        
        if override:
            data.update(override)
        
        return data
    
    @staticmethod
    def generate_task_data(override: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate test task data"""
        data = {
            'task_type': random.choice(['optimization', 'analysis', 'scraping', 'keyword-extraction']),
            'agent_type': random.choice(['scraping-efficiency', 'keyword-precision', 'any']),
            'priority': random.choice(list(Priority)),
            'payload': {
                'target_files': [f'src/file_{i}.py' for i in range(random.randint(1, 3))],
                'parameters': {
                    'threshold': round(random.uniform(0.1, 1.0), 2),
                    'timeout': random.randint(60, 600)
                }
            },
            'timeout': random.randint(120, 600),
            'retries': random.randint(1, 5),
            'dependencies': [DataGenerators.random_uuid() for _ in range(random.randint(0, 2))]
        }
        
        if override:
            data.update(override)
        
        return data
    
    @staticmethod
    def generate_optimization_data(override: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate test optimization recommendation data"""
        data = {
            'title': f'Optimization: {DataGenerators.random_string(10)}',
            'description': f'Improve performance by optimizing {DataGenerators.random_string(8)}',
            'optimization_type': random.choice(['code_optimization', 'performance_tuning', 'memory_optimization']),
            'severity': random.choice(['low', 'medium', 'high', 'critical']),
            'target_files': [f'src/{DataGenerators.random_string(6)}.py'],
            'proposed_changes': [
                {
                    'file': f'src/{DataGenerators.random_string(6)}.py',
                    'line': random.randint(1, 100),
                    'old_code': f'old_code_{DataGenerators.random_string(8)}',
                    'new_code': f'new_code_{DataGenerators.random_string(8)}'
                }
            ],
            'expected_benefits': ['Improved performance', 'Better efficiency'],
            'risk_assessment': {
                'level': 'low',
                'factors': ['minimal_change', 'well_tested']
            },
            'confidence_score': round(random.uniform(0.5, 1.0), 2),
            'validation_requirements': ['syntax_check', 'unit_tests']
        }
        
        if override:
            data.update(override)
        
        return data
    
    @staticmethod
    def generate_swarm_message(override: Dict[str, Any] = None) -> SwarmMessage:
        """Generate test swarm message"""
        data = {
            'id': DataGenerators.random_uuid(),
            'type': random.choice(list(MessageType)),
            'sender': f'agent-{DataGenerators.random_string(6)}',
            'recipient': f'agent-{DataGenerators.random_string(6)}' if random.choice([True, False]) else None,
            'timestamp': DataGenerators.random_timestamp(),
            'payload': {
                'action': f'action_{DataGenerators.random_string(6)}',
                'data': DataGenerators.random_string(20)
            },
            'priority': random.choice(list(Priority))
        }
        
        if override:
            data.update(override)
        
        return SwarmMessage(**data)
    
    @staticmethod
    def generate_task_definition(override: Dict[str, Any] = None) -> TaskDefinition:
        """Generate test task definition"""
        data = {
            'id': DataGenerators.random_uuid(),
            'type': random.choice(['optimization', 'analysis', 'scraping']),
            'agent_type': random.choice(['scraping-efficiency', 'keyword-precision', 'any']),
            'priority': random.choice(list(Priority)),
            'payload': {'test': True, 'data': DataGenerators.random_string(10)},
            'timeout': random.randint(120, 600),
            'retries': random.randint(1, 3),
            'created_at': DataGenerators.random_timestamp()
        }
        
        if override:
            data.update(override)
        
        return TaskDefinition(**data)


class TestEnvironment:
    """Test environment management utilities"""
    
    def __init__(self):
        self.temp_dirs: List[Path] = []
        self.cleanup_functions: List[Callable] = []
    
    def create_temp_directory(self) -> Path:
        """Create temporary directory for testing"""
        temp_dir = Path(tempfile.mkdtemp())
        self.temp_dirs.append(temp_dir)
        return temp_dir
    
    def create_temp_file(self, content: str = "", suffix: str = ".py") -> Path:
        """Create temporary file with content"""
        temp_dir = self.create_temp_directory()
        temp_file = temp_dir / f"test_file_{DataGenerators.random_string(6)}{suffix}"
        temp_file.write_text(content)
        return temp_file
    
    def register_cleanup(self, cleanup_func: Callable):
        """Register cleanup function"""
        self.cleanup_functions.append(cleanup_func)
    
    def cleanup(self):
        """Clean up test environment"""
        # Run cleanup functions
        for cleanup_func in reversed(self.cleanup_functions):
            try:
                cleanup_func()
            except Exception as e:
                print(f"Cleanup error: {e}")
        
        # Remove temporary directories
        for temp_dir in self.temp_dirs:
            try:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Error removing temp dir {temp_dir}: {e}")
        
        self.temp_dirs.clear()
        self.cleanup_functions.clear()


class AsyncTestHelpers:
    """Helpers for async testing"""
    
    @staticmethod
    async def wait_for_condition(
        condition_func: Callable[[], bool], 
        timeout: float = 5.0, 
        interval: float = 0.1
    ) -> bool:
        """Wait for condition to become true"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if condition_func():
                return True
            await asyncio.sleep(interval)
        
        return False
    
    @staticmethod
    async def wait_for_async_condition(
        condition_func: Callable[[], bool], 
        timeout: float = 5.0, 
        interval: float = 0.1
    ) -> bool:
        """Wait for async condition to become true"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if await condition_func():
                return True
            await asyncio.sleep(interval)
        
        return False
    
    @staticmethod
    @asynccontextmanager
    async def timeout_context(timeout: float):
        """Context manager for operations with timeout"""
        try:
            await asyncio.wait_for(asyncio.sleep(0), timeout=timeout)
            yield
        except asyncio.TimeoutError:
            raise TimeoutError(f"Operation timed out after {timeout} seconds")
    
    @staticmethod
    async def run_with_timeout(coro, timeout: float):
        """Run coroutine with timeout"""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Coroutine timed out after {timeout} seconds")


class PerformanceTracker:
    """Track performance metrics during tests"""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.start_times: Dict[str, float] = {}
    
    def start_timing(self, metric_name: str):
        """Start timing a metric"""
        self.start_times[metric_name] = time.time()
    
    def end_timing(self, metric_name: str) -> float:
        """End timing and record metric"""
        if metric_name not in self.start_times:
            raise ValueError(f"No start time recorded for metric: {metric_name}")
        
        duration = time.time() - self.start_times[metric_name]
        
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        
        self.metrics[metric_name].append(duration)
        del self.start_times[metric_name]
        
        return duration
    
    def record_value(self, metric_name: str, value: float):
        """Record a metric value"""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append(value)
    
    def get_stats(self, metric_name: str) -> Dict[str, float]:
        """Get statistics for a metric"""
        if metric_name not in self.metrics:
            return {}
        
        values = self.metrics[metric_name]
        if not values:
            return {}
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'total': sum(values)
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all metrics"""
        return {metric: self.get_stats(metric) for metric in self.metrics.keys()}


class MockDataStore:
    """In-memory data store for testing"""
    
    def __init__(self):
        self.data: Dict[str, Any] = {}
        self.lists: Dict[str, List[Any]] = {}
        self.counters: Dict[str, int] = {}
    
    def set(self, key: str, value: Any):
        """Set a value"""
        self.data[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value"""
        return self.data.get(key, default)
    
    def append(self, list_key: str, value: Any):
        """Append to a list"""
        if list_key not in self.lists:
            self.lists[list_key] = []
        self.lists[list_key].append(value)
    
    def get_list(self, list_key: str) -> List[Any]:
        """Get a list"""
        return self.lists.get(list_key, [])
    
    def increment(self, counter_key: str, amount: int = 1) -> int:
        """Increment a counter"""
        self.counters[counter_key] = self.counters.get(counter_key, 0) + amount
        return self.counters[counter_key]
    
    def get_counter(self, counter_key: str) -> int:
        """Get counter value"""
        return self.counters.get(counter_key, 0)
    
    def clear(self):
        """Clear all data"""
        self.data.clear()
        self.lists.clear()
        self.counters.clear()


class TestScenarios:
    """Pre-defined test scenarios"""
    
    @staticmethod
    def create_agent_fleet_scenario() -> List[Dict[str, Any]]:
        """Create a diverse agent fleet scenario"""
        agents = []
        
        # Scraping specialists
        for i in range(3):
            agents.append(DataGenerators.generate_agent_data({
                'agent_type': 'scraping-efficiency',
                'name': f'scraping-agent-{i}',
                'status': AgentStatus.HEALTHY,
                'specializations': ['twitter', 'telegram', 'discord']
            }))
        
        # Keyword specialists
        for i in range(2):
            agents.append(DataGenerators.generate_agent_data({
                'agent_type': 'keyword-precision',
                'name': f'keyword-agent-{i}',
                'status': AgentStatus.HEALTHY,
                'specializations': ['nlp', 'sentiment-analysis']
            }))
        
        # Performance optimizers
        agents.append(DataGenerators.generate_agent_data({
            'agent_type': 'performance-optimizer',
            'name': 'performance-agent-0',
            'status': AgentStatus.HEALTHY,
            'specializations': ['code-optimization', 'performance-tuning']
        }))
        
        return agents
    
    @staticmethod
    def create_optimization_workflow_scenario() -> Dict[str, Any]:
        """Create optimization workflow scenario"""
        return {
            'discovery_task': DataGenerators.generate_task_data({
                'type': 'code_analysis',
                'agent_type': 'scraping-efficiency',
                'priority': Priority.HIGH,
                'payload': {
                    'target_files': ['src/scraper.py', 'src/analyzer.py'],
                    'analysis_type': 'performance_bottlenecks'
                }
            }),
            'validation_task': DataGenerators.generate_task_data({
                'type': 'optimization_validation',
                'agent_type': 'performance-optimizer',
                'priority': Priority.HIGH,
                'payload': {
                    'optimization_type': 'code_optimization',
                    'safety_checks': ['syntax', 'functionality', 'performance']
                }
            }),
            'implementation_task': DataGenerators.generate_task_data({
                'type': 'optimization_implementation',
                'agent_type': 'scraping-efficiency',
                'priority': Priority.CRITICAL,
                'payload': {
                    'implementation_plan': 'apply_optimization',
                    'backup_required': True
                }
            })
        }
    
    @staticmethod
    def create_high_load_scenario(num_tasks: int = 100) -> List[TaskDefinition]:
        """Create high load testing scenario"""
        tasks = []
        
        for i in range(num_tasks):
            priority = Priority.HIGH if i % 10 == 0 else Priority.MEDIUM
            agent_type = random.choice(['scraping-efficiency', 'keyword-precision', 'performance-optimizer'])
            
            task = DataGenerators.generate_task_definition({
                'type': f'load_test_task_{i}',
                'agent_type': agent_type,
                'priority': priority,
                'payload': {
                    'task_index': i,
                    'batch_id': i // 10,
                    'load_test': True
                }
            })
            tasks.append(task)
        
        return tasks


# Utility functions
def assert_eventually(condition_func: Callable[[], bool], timeout: float = 5.0, message: str = "Condition not met"):
    """Assert that condition eventually becomes true"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if condition_func():
            return
        time.sleep(0.1)
    
    raise AssertionError(f"{message} within {timeout} seconds")


async def assert_eventually_async(
    condition_func: Callable[[], bool], 
    timeout: float = 5.0, 
    message: str = "Condition not met"
):
    """Async version of assert_eventually"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if await condition_func() if asyncio.iscoroutinefunction(condition_func) else condition_func():
            return
        await asyncio.sleep(0.1)
    
    raise AssertionError(f"{message} within {timeout} seconds")


def create_test_file_with_content(content: str, suffix: str = ".py") -> Path:
    """Create temporary test file with specified content"""
    temp_file = Path(tempfile.mktemp(suffix=suffix))
    temp_file.write_text(content)
    return temp_file