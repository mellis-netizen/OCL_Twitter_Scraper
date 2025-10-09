#!/usr/bin/env python3
"""
PyTest Configuration and Fixtures for TGE Swarm Testing
Provides comprehensive test fixtures, mocks, and utilities for backend testing
"""

import asyncio
import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import redis.asyncio as redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import docker
import yaml

# Add backend to path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from backend.message_queue import MessageQueue, SwarmMessage, MessageType, Priority, TaskDefinition
from backend.agent_manager import AgentManager, AgentSpec, AgentType, AgentStatus
from backend.coordination_service import CoordinationService
from backend.database.models import Base, DatabaseManager, Agent, Task, OptimizationRecommendation
from backend.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from swarm_memory_coordinator import SwarmMemoryCoordinator


# Test configuration
TEST_CONFIG = {
    'redis_url': 'redis://localhost:6379/15',  # Use test database
    'database_url': 'sqlite:///:memory:',  # In-memory SQLite for tests
    'consul_host': 'localhost',
    'consul_port': 8500,
    'log_level': 'DEBUG'
}


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def redis_client():
    """Redis client fixture for testing"""
    client = redis.Redis.from_url(TEST_CONFIG['redis_url'], decode_responses=True)
    
    # Clear test database
    await client.flushdb()
    
    yield client
    
    # Cleanup
    await client.flushdb()
    await client.close()


@pytest.fixture
async def test_database():
    """Test database fixture with in-memory SQLite"""
    db_manager = DatabaseManager(TEST_CONFIG['database_url'])
    db_manager.create_tables()
    
    yield db_manager
    
    db_manager.close()


@pytest.fixture
async def test_session(test_database):
    """Database session fixture"""
    session = test_database.get_session()
    yield session
    session.close()


@pytest.fixture
def temp_memory_path():
    """Temporary directory for memory coordinator testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
async def mock_docker_client():
    """Mock Docker client for agent manager testing"""
    with patch('docker.from_env') as mock_docker:
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        # Mock container operations
        mock_container = MagicMock()
        mock_container.id = 'mock_container_id'
        mock_container.status = 'running'
        mock_container.attrs = {
            'State': {
                'Health': {'Status': 'healthy'}
            }
        }
        
        mock_client.containers.run.return_value = mock_container
        mock_client.containers.get.return_value = mock_container
        
        yield mock_client


@pytest.fixture
async def mock_consul_client():
    """Mock Consul client for service discovery testing"""
    with patch('consul.Consul') as mock_consul:
        mock_client = MagicMock()
        mock_consul.return_value = mock_client
        
        # Mock service registration
        mock_client.agent.service.register.return_value = None
        mock_client.agent.service.deregister.return_value = None
        
        yield mock_client


@pytest.fixture
async def message_queue(redis_client):
    """Message queue fixture for testing"""
    mq = MessageQueue([TEST_CONFIG['redis_url'].replace('redis://', '').replace('/15', '')], "test-swarm")
    await mq.initialize()
    yield mq
    await mq.shutdown()


@pytest.fixture
async def memory_coordinator(temp_memory_path):
    """Memory coordinator fixture"""
    coordinator = SwarmMemoryCoordinator(temp_memory_path)
    yield coordinator


@pytest.fixture
async def coordination_service(memory_coordinator, message_queue):
    """Coordination service fixture"""
    service = CoordinationService(
        memory_coordinator,
        message_queue,
        TEST_CONFIG['redis_url']
    )
    await service.initialize()
    yield service
    await service.shutdown()


@pytest.fixture
async def agent_manager(mock_docker_client, mock_consul_client):
    """Agent manager fixture with mocked dependencies"""
    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        config = {
            'consul_host': 'localhost',
            'consul_port': 8500,
            'docker_network': 'test-network',
            'max_agents_per_type': 3,
            'health_check_interval': 5
        }
        yaml.dump(config, f)
        config_file = f.name
    
    try:
        manager = AgentManager(config_file)
        yield manager
    finally:
        os.unlink(config_file)
        if manager.running:
            await manager.shutdown()


@pytest.fixture
def circuit_breaker_config():
    """Circuit breaker configuration for testing"""
    return CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=5,
        timeout=1.0,
        window_size=10,
        minimum_requests=5
    )


@pytest.fixture
def circuit_breaker(circuit_breaker_config):
    """Circuit breaker fixture"""
    breaker = CircuitBreaker("test-service", circuit_breaker_config)
    yield breaker
    breaker.reset()


# Sample data generators
@pytest.fixture
def sample_agent_data():
    """Sample agent data for testing"""
    return {
        'name': 'test-agent',
        'agent_type': 'scraping-efficiency',
        'container_id': 'test-container-123',
        'status': AgentStatus.HEALTHY,
        'host': 'localhost',
        'port': 8080,
        'version': '1.0.0',
        'cpu_limit': 1.0,
        'memory_limit': '512m',
        'capabilities': ['nlp', 'text-analysis'],
        'specializations': ['twitter-scraping']
    }


@pytest.fixture
def sample_task_data():
    """Sample task data for testing"""
    return {
        'task_type': 'keyword-optimization',
        'agent_type': 'keyword-precision',
        'priority': Priority.HIGH,
        'payload': {
            'target_files': ['config.py'],
            'parameters': {'threshold': 0.8}
        },
        'timeout': 300,
        'retries': 3
    }


@pytest.fixture
def sample_optimization_data():
    """Sample optimization recommendation data"""
    return {
        'title': 'Improve keyword matching efficiency',
        'description': 'Optimize keyword matching algorithm for better performance',
        'optimization_type': 'code_optimization',
        'severity': 'medium',
        'target_files': ['src/news_scraper.py'],
        'proposed_changes': [
            {
                'file': 'src/news_scraper.py',
                'line': 45,
                'old_code': 'for keyword in keywords:',
                'new_code': 'for keyword in compiled_keywords:'
            }
        ],
        'expected_benefits': ['Improved performance', 'Better accuracy'],
        'confidence_score': 0.85
    }


@pytest.fixture
def sample_swarm_message():
    """Sample swarm message for testing"""
    return SwarmMessage(
        id=str(uuid.uuid4()),
        type=MessageType.TASK_ASSIGNMENT,
        sender="test-orchestrator",
        recipient="test-agent",
        timestamp=datetime.now(timezone.utc),
        payload={'task_id': 'test-task-123'},
        priority=Priority.MEDIUM
    )


@pytest.fixture
def sample_task_definition():
    """Sample task definition for testing"""
    return TaskDefinition(
        id=str(uuid.uuid4()),
        type="test-optimization",
        agent_type="any",
        priority=Priority.MEDIUM,
        payload={'target': 'test.py'},
        timeout=300,
        retries=3,
        created_at=datetime.now(timezone.utc)
    )


# Async test utilities
class AsyncContextManager:
    """Utility class for testing async context managers"""
    
    def __init__(self, async_func):
        self.async_func = async_func
        self.result = None
    
    async def __aenter__(self):
        self.result = await self.async_func()
        return self.result
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def async_mock():
    """Create an AsyncMock for testing async functions"""
    return AsyncMock()


# Performance testing utilities
@pytest.fixture
def performance_monitor():
    """Performance monitoring utility for tests"""
    class PerformanceMonitor:
        def __init__(self):
            self.metrics = {}
            self.start_times = {}
        
        def start_timer(self, name: str):
            self.start_times[name] = datetime.now()
        
        def end_timer(self, name: str):
            if name in self.start_times:
                duration = (datetime.now() - self.start_times[name]).total_seconds()
                self.metrics[name] = duration
                del self.start_times[name]
                return duration
            return None
        
        def get_metrics(self):
            return self.metrics.copy()
    
    return PerformanceMonitor()


# Test data validation utilities
def validate_agent_data(agent_data: Dict[str, Any]) -> bool:
    """Validate agent data structure"""
    required_fields = ['name', 'agent_type', 'status']
    return all(field in agent_data for field in required_fields)


def validate_task_data(task_data: Dict[str, Any]) -> bool:
    """Validate task data structure"""
    required_fields = ['task_type', 'agent_type', 'priority']
    return all(field in task_data for field in required_fields)


def validate_optimization_data(opt_data: Dict[str, Any]) -> bool:
    """Validate optimization recommendation data"""
    required_fields = ['title', 'optimization_type', 'severity']
    return all(field in opt_data for field in required_fields)


# Test environment setup
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment with proper logging and isolation"""
    # Set test environment variables
    os.environ['TESTING'] = 'true'
    os.environ['LOG_LEVEL'] = 'DEBUG'
    
    yield
    
    # Cleanup environment
    if 'TESTING' in os.environ:
        del os.environ['TESTING']


# Integration test fixtures
@pytest.fixture
async def full_backend_stack(
    redis_client,
    test_database,
    memory_coordinator,
    message_queue,
    coordination_service,
    agent_manager
):
    """Complete backend stack for integration testing"""
    # Initialize agent manager with message queue
    await agent_manager.initialize(message_queue)
    
    stack = {
        'redis_client': redis_client,
        'database': test_database,
        'memory_coordinator': memory_coordinator,
        'message_queue': message_queue,
        'coordination_service': coordination_service,
        'agent_manager': agent_manager
    }
    
    yield stack
    
    # Cleanup
    await agent_manager.shutdown()


# Load testing utilities
@pytest.fixture
def load_test_config():
    """Configuration for load testing"""
    return {
        'concurrent_users': 10,
        'test_duration': 30,  # seconds
        'ramp_up_time': 5,    # seconds
        'target_rps': 100,    # requests per second
        'error_threshold': 0.05  # 5% error rate threshold
    }


# Error simulation utilities
@pytest.fixture
def error_simulator():
    """Utility for simulating various error conditions"""
    class ErrorSimulator:
        def __init__(self):
            self.failure_rate = 0.0
            self.timeout_rate = 0.0
            self.slow_response_rate = 0.0
        
        def set_failure_rate(self, rate: float):
            self.failure_rate = max(0.0, min(1.0, rate))
        
        def set_timeout_rate(self, rate: float):
            self.timeout_rate = max(0.0, min(1.0, rate))
        
        def set_slow_response_rate(self, rate: float):
            self.slow_response_rate = max(0.0, min(1.0, rate))
        
        async def simulate_call(self, func, *args, **kwargs):
            import random
            
            # Simulate timeout
            if random.random() < self.timeout_rate:
                await asyncio.sleep(10)  # Simulate timeout
                raise asyncio.TimeoutError("Simulated timeout")
            
            # Simulate slow response
            if random.random() < self.slow_response_rate:
                await asyncio.sleep(2)  # Simulate slow response
            
            # Simulate failure
            if random.random() < self.failure_rate:
                raise Exception("Simulated failure")
            
            # Normal execution
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
    
    return ErrorSimulator()


# Metrics collection for testing
@pytest.fixture
def test_metrics_collector():
    """Collect metrics during test execution"""
    class TestMetricsCollector:
        def __init__(self):
            self.metrics = {}
            self.counters = {}
            self.timings = {}
        
        def increment(self, metric_name: str, value: int = 1):
            self.counters[metric_name] = self.counters.get(metric_name, 0) + value
        
        def record_timing(self, metric_name: str, duration: float):
            if metric_name not in self.timings:
                self.timings[metric_name] = []
            self.timings[metric_name].append(duration)
        
        def set_gauge(self, metric_name: str, value: float):
            self.metrics[metric_name] = value
        
        def get_summary(self):
            summary = {
                'counters': self.counters.copy(),
                'gauges': self.metrics.copy(),
                'timings': {}
            }
            
            for name, times in self.timings.items():
                if times:
                    summary['timings'][name] = {
                        'count': len(times),
                        'min': min(times),
                        'max': max(times),
                        'avg': sum(times) / len(times)
                    }
            
            return summary
    
    return TestMetricsCollector()


# Test markers for categorizing tests
pytest_plugins = []

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "redis: mark test as requiring Redis"
    )
    config.addinivalue_line(
        "markers", "database: mark test as requiring database"
    )
    config.addinivalue_line(
        "markers", "docker: mark test as requiring Docker"
    )


# Test data cleanup utilities
@pytest.fixture
def test_cleanup():
    """Utility for cleaning up test data"""
    cleanup_functions = []
    
    def register_cleanup(func):
        cleanup_functions.append(func)
    
    yield register_cleanup
    
    # Execute cleanup functions in reverse order
    for cleanup_func in reversed(cleanup_functions):
        try:
            if asyncio.iscoroutinefunction(cleanup_func):
                asyncio.create_task(cleanup_func())
            else:
                cleanup_func()
        except Exception as e:
            print(f"Error during cleanup: {e}")