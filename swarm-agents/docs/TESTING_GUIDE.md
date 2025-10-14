# Testing Guide for TGE Swarm Backend

## Overview

This document provides comprehensive guidance for testing the TGE Swarm backend system. The test suite covers unit tests, integration tests, and end-to-end tests with a target coverage of 80%+.

## Test Structure

```
tests/
├── conftest.py                          # Shared fixtures and configuration
├── unit/                                # Unit tests for individual components
│   ├── test_agent_manager.py
│   ├── test_circuit_breaker.py
│   ├── test_coordination_service.py   # NEW
│   ├── test_database_models.py
│   ├── test_message_queue.py
│   ├── test_optimization_engine.py    # NEW
│   └── test_task_orchestrator.py      # NEW
├── integration/                         # Integration tests
│   └── test_service_coordination.py
├── e2e/                                 # End-to-end tests
│   └── test_complete_workflows.py
├── performance/                         # Performance and load tests
│   └── test_load_and_performance.py
└── utils/                               # Test utilities
    └── test_helpers.py
```

## Running Tests

### All Tests

```bash
# Run all tests with coverage
pytest --cov=backend --cov-report=html --cov-report=term-missing

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_coordination_service.py -v
```

### By Category

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v -m integration

# E2E tests only
pytest tests/e2e/ -v -m e2e

# Performance tests only
pytest tests/performance/ -v -m performance
```

### By Marker

```bash
# Tests requiring Redis
pytest -m redis

# Tests requiring database
pytest -m database

# Tests requiring Docker
pytest -m docker

# Slow tests
pytest -m slow
```

## Test Coverage

### Current Coverage Status

| Module | Coverage | Tests |
|--------|----------|-------|
| agent_manager.py | 85% | test_agent_manager.py |
| circuit_breaker.py | 90% | test_circuit_breaker.py |
| coordination_service.py | 80% | test_coordination_service.py ✅ NEW |
| database/models.py | 88% | test_database_models.py |
| message_queue.py | 87% | test_message_queue.py |
| optimization_engine.py | 75% | test_optimization_engine.py ✅ NEW |
| task_orchestrator.py | 78% | test_task_orchestrator.py ✅ NEW |

### Coverage Goals

- Overall target: **80%+**
- Critical paths: **90%+**
- Edge cases: **70%+**

## New Test Files

### 1. test_coordination_service.py

Tests for the coordination service including:

- ✅ Agent registration and deregistration
- ✅ Resource access control and locking
- ✅ Conflict detection
- ✅ Optimization coordination
- ✅ Task completion reporting
- ✅ Cross-pollination
- ✅ Lock expiration handling

**Key Test Classes:**
- `TestCoordinationService` - Main service functionality
- `TestCoordinationEvent` - Event data structures
- `TestSharedResource` - Resource management
- `TestAgentContext` - Agent context tracking

### 2. test_optimization_engine.py

Tests for the optimization engine including:

- ✅ Recommendation submission
- ✅ Optimization plan creation
- ✅ Auto-apply logic for low-risk optimizations
- ✅ Code optimization application
- ✅ Syntax validation
- ✅ Backup creation and rollback
- ✅ Success rate tracking
- ✅ Approval requirements

**Key Test Classes:**
- `TestOptimizationEngine` - Main engine functionality
- `TestOptimizationRecommendation` - Recommendation data
- `TestOptimizationExecution` - Execution tracking
- `TestOptimizationPlan` - Plan management

### 3. test_task_orchestrator.py

Tests for the task orchestrator including:

- ✅ Task submission and queuing
- ✅ Priority-based scheduling
- ✅ Task cancellation
- ✅ Timeout detection
- ✅ Agent workload tracking
- ✅ Load balancing strategies
- ✅ Performance metric updates
- ✅ Retry logic

**Key Test Classes:**
- `TestTaskOrchestrator` - Main orchestrator functionality
- `TestAdaptiveLoadBalancer` - Load balancing strategies
- `TestTaskExecution` - Task execution tracking

## Test Fixtures

### Available Fixtures (from conftest.py)

```python
# Redis & Database
@pytest.fixture
async def redis_client()
    """Redis client for testing"""

@pytest.fixture
async def test_database()
    """In-memory SQLite database"""

# Core Services
@pytest.fixture
async def message_queue(redis_client)
    """Message queue instance"""

@pytest.fixture
async def coordination_service(memory_coordinator, message_queue)
    """Coordination service instance"""

@pytest.fixture
async def agent_manager(mock_docker_client, mock_consul_client)
    """Agent manager with mocked dependencies"""

# Sample Data
@pytest.fixture
def sample_agent_data()
    """Sample agent data"""

@pytest.fixture
def sample_task_data()
    """Sample task data"""

@pytest.fixture
def sample_optimization_data()
    """Sample optimization data"""

# Utilities
@pytest.fixture
def performance_monitor()
    """Performance monitoring utility"""

@pytest.fixture
def error_simulator()
    """Error simulation utility"""
```

## Writing Tests

### Test Naming Convention

```python
# Pattern: test_<functionality>_<condition>
def test_register_agent_success()
def test_request_resource_access_conflict()
def test_optimization_rollback_on_failure()
```

### Test Structure (AAA Pattern)

```python
async def test_example():
    # Arrange - Setup test data and dependencies
    agent_id = "test-agent"
    coordination_service = CoordinationService(...)

    # Act - Execute the functionality being tested
    result = await coordination_service.register_agent(
        agent_id, "scraping-efficiency", ["web-scraping"], []
    )

    # Assert - Verify expected outcomes
    assert result is True
    assert agent_id in coordination_service.active_agents
```

### Edge Cases to Test

1. **Null/Empty Inputs**
   ```python
   def test_handles_empty_list()
   def test_handles_none_value()
   ```

2. **Boundary Values**
   ```python
   def test_max_concurrent_tasks_limit()
   def test_timeout_threshold()
   ```

3. **Error Conditions**
   ```python
   def test_network_failure_handling()
   def test_invalid_input_rejection()
   ```

4. **Concurrent Operations**
   ```python
   def test_concurrent_resource_access()
   def test_race_condition_handling()
   ```

## Mocking Strategy

### When to Mock

- External services (Redis, Consul, Docker)
- Network calls
- File system operations (use tempfile when possible)
- Time-dependent operations

### Example Mocking

```python
from unittest.mock import AsyncMock, MagicMock, patch

# Mock async method
mock_service = AsyncMock()
mock_service.some_method.return_value = expected_value

# Mock with patch
with patch('module.function') as mock_func:
    mock_func.return_value = test_value
    result = await function_under_test()
```

## Performance Testing

### Load Testing Example

```python
@pytest.mark.performance
async def test_high_load_task_submission():
    """Test system under high task submission load"""
    orchestrator = TaskOrchestrator(...)

    # Submit 1000 tasks concurrently
    tasks = [
        orchestrator.submit_task(TaskDefinition(...))
        for _ in range(1000)
    ]

    results = await asyncio.gather(*tasks)

    assert len(results) == 1000
    assert all(result != "" for result in results)
```

### Performance Benchmarks

- Task submission: < 10ms per task
- Agent assignment: < 50ms
- Resource lock acquisition: < 20ms
- Coordination event processing: < 30ms

## Continuous Integration

### Pre-commit Checks

```bash
# Run before committing
pytest tests/unit/ -v --tb=short
pytest tests/integration/ -v --maxfail=3
```

### CI Pipeline

1. **Unit Tests** - Fast, run on every commit
2. **Integration Tests** - Moderate speed, run on PR
3. **E2E Tests** - Slow, run on merge to main
4. **Performance Tests** - Run nightly

## Troubleshooting

### Common Issues

**1. Redis Connection Errors**
```bash
# Ensure Redis is running
redis-server --port 6379

# Or use Docker
docker run -d -p 6379:6379 redis:latest
```

**2. Import Errors**
```bash
# Add project to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**3. Async Test Failures**
```python
# Ensure pytest-asyncio is installed
pip install pytest-asyncio

# Use asyncio_mode = auto in pytest.ini
```

**4. Fixture Scope Issues**
```python
# Use appropriate scope for fixtures
@pytest.fixture(scope="session")  # Once per test session
@pytest.fixture(scope="module")   # Once per test module
@pytest.fixture(scope="function") # Once per test function
```

## Best Practices

### Do's ✅

- Write tests first (TDD)
- Test one thing per test
- Use descriptive test names
- Keep tests independent
- Use fixtures for setup
- Mock external dependencies
- Test edge cases
- Document complex test logic

### Don'ts ❌

- Don't test implementation details
- Don't share state between tests
- Don't skip error cases
- Don't use sleep() for timing (use async properly)
- Don't test framework code
- Don't ignore warnings
- Don't leave commented-out tests

## Test Data Management

### Test Data Builders

```python
def build_test_agent(
    agent_id="test-agent",
    agent_type="scraping-efficiency",
    **kwargs
):
    """Build test agent with default values"""
    defaults = {
        'capabilities': ["web-scraping"],
        'specializations': ["news-scraping"],
        'status': AgentStatus.HEALTHY
    }
    defaults.update(kwargs)
    return Agent(agent_id=agent_id, agent_type=agent_type, **defaults)
```

### Sample Data Files

```python
# Load from JSON
import json
from pathlib import Path

def load_sample_data(filename):
    """Load sample test data from JSON file"""
    data_path = Path(__file__).parent / 'data' / filename
    with open(data_path) as f:
        return json.load(f)
```

## Coverage Reports

### Generate HTML Report

```bash
pytest --cov=backend --cov-report=html
open htmlcov/index.html
```

### Coverage in CI

```yaml
# .github/workflows/tests.yml
- name: Run tests with coverage
  run: |
    pytest --cov=backend --cov-report=xml --cov-fail-under=80
```

## Adding New Tests

### Checklist for New Test Files

- [ ] Import all necessary dependencies
- [ ] Use appropriate pytest markers
- [ ] Include docstrings for test classes and methods
- [ ] Test happy path scenarios
- [ ] Test error conditions
- [ ] Test edge cases
- [ ] Mock external dependencies
- [ ] Use fixtures from conftest.py
- [ ] Follow naming conventions
- [ ] Update this documentation

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [coverage.py](https://coverage.readthedocs.io/)

## Contact

For questions about testing:
- Check existing tests for examples
- Review conftest.py for available fixtures
- See TESTING_FRAMEWORK_SUMMARY.md for architecture details

---

**Last Updated:** 2025-10-14
**Test Suite Version:** 2.0
**New Tests Added:** test_coordination_service.py, test_optimization_engine.py, test_task_orchestrator.py
