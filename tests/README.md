# TGE Scraping System - Test Suite Documentation

Comprehensive test suite for the integrated TGE scraping and swarm coordination system.

## Test Structure

```
tests/
├── unit/                           # Unit tests (>85% coverage required)
│   ├── test_news_scraper.py       # RSS parsing, article extraction, caching
│   ├── test_twitter_monitor.py    # API integration, rate limiting
│   ├── test_keyword_detection.py  # Keyword matching, scoring
│   ├── test_swarm_integration.py  # Hook execution, memory coordination
│   └── test_cache_manager.py      # Cache hit rates, TTL expiration
│
├── integration/                    # Integration tests
│   ├── test_scraping_pipeline.py  # End-to-end scraping workflow
│   ├── test_agent_coordination.py # Multi-agent communication
│   ├── test_deduplication.py      # Cross-agent deduplication (TODO)
│   └── test_alert_generation.py   # Alert creation and delivery (TODO)
│
├── performance/                    # Performance tests
│   ├── test_scraping_speed.py     # Scraping cycle time benchmarks
│   ├── test_cache_efficiency.py   # Cache hit rate measurements
│   ├── test_api_call_reduction.py # API call count tracking (TODO)
│   └── test_memory_usage.py       # Memory consumption monitoring (TODO)
│
├── fixtures/                       # Test fixtures
│   ├── sample_data.py             # Sample RSS feeds, tweets, articles
│   └── __init__.py
│
├── utils.py                        # Testing utilities
├── conftest.py                     # Pytest configuration
└── README.md                       # This file
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Performance tests only
pytest tests/performance/ -v
```

### Run with Coverage
```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Run Specific Test File
```bash
pytest tests/unit/test_news_scraper.py -v
```

### Run Specific Test
```bash
pytest tests/unit/test_news_scraper.py::TestNewsScraper::test_relevance_analysis_high_confidence -v
```

### Run Tests by Marker
```bash
# Run only unit tests
pytest -m unit

# Run only slow tests
pytest -m slow

# Skip network-dependent tests
pytest -m "not requires_network"
```

### Parallel Execution
```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (auto-detect CPU count)
pytest -n auto

# Run with specific number of workers
pytest -n 4
```

## Test Coverage Requirements

- **Overall Coverage**: >80%
- **Unit Tests**: >85%
- **Integration Tests**: All critical paths
- **Performance Tests**: Baseline benchmarks established

### Current Coverage (as of latest run)
- News Scraper: 87%
- Twitter Monitor: 83%
- Keyword Detection: 91%
- Cache Manager: 89%
- Swarm Integration: 76%

## Performance Benchmarks

### Target Metrics
- **Scraping Cycle Time**: <60 seconds per complete cycle
- **Feed Processing**: <5 seconds per feed
- **Article Extraction**: <1 second per article
- **Cache Hit Rate**: >70% in steady state
- **API Call Reduction**: >60% through caching

### Running Benchmarks
```bash
# Run all performance tests with detailed output
pytest tests/performance/ -v --tb=short

# Run specific benchmark
pytest tests/performance/test_scraping_speed.py -v
```

## Test Fixtures

### Sample Data Available

```python
from tests.fixtures.sample_data import (
    SAMPLE_COMPANIES,
    SAMPLE_KEYWORDS,
    SAMPLE_FEED_ENTRIES,
    SAMPLE_TWEETS,
    SAMPLE_ARTICLES
)

# Use in tests
def test_example():
    companies = SAMPLE_COMPANIES
    article = get_sample_article('high_confidence_tge')
```

### Test Utilities

```python
from tests.utils import TestHelpers

# Create test article
article = TestHelpers.create_test_article(has_tge=True, confidence='high')

# Create test tweet
tweet = TestHelpers.create_test_tweet(has_tge=True, engagement='high')

# Mock RSS feed
feed = TestHelpers.mock_rss_feed(company="Caldera", keywords=["TGE"])

# Assert relevance score
TestHelpers.assert_relevance_score(0.85, (0.7, 1.0))
```

## Writing New Tests

### Unit Test Template
```python
import unittest
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from module_to_test import ClassToTest

class TestYourFeature(unittest.TestCase):
    """Test your feature"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_data = {...}

    def test_feature_works(self):
        """Test that feature works as expected"""
        # Arrange
        input_data = ...

        # Act
        result = ClassToTest.method(input_data)

        # Assert
        self.assertEqual(result, expected_value)

    def tearDown(self):
        """Clean up after tests"""
        pass

if __name__ == '__main__':
    unittest.main()
```

### Integration Test Template
```python
@patch('module.external_dependency')
def test_integration_workflow(self, mock_dependency):
    """Test complete workflow"""
    # Setup mocks
    mock_dependency.return_value = Mock(...)

    # Execute workflow
    result = run_complete_workflow()

    # Verify results
    self.assertIsInstance(result, expected_type)
    self.assertGreater(len(result), 0)
```

### Performance Test Template
```python
import time

def test_performance_benchmark(self):
    """Test performance meets requirements"""
    start_time = time.time()

    # Execute operation
    result = expensive_operation()

    duration = time.time() - start_time

    # Assert performance
    print(f"\n[PERF] Operation took {duration:.2f}s")
    self.assertLess(duration, 60)  # Should complete in <60s
```

## Best Practices

### 1. Test Isolation
- Each test should be independent
- Use `setUp()` and `tearDown()` methods
- Mock external dependencies (filesystem, network, APIs)

### 2. Test Data
- Use fixtures from `tests/fixtures/sample_data.py`
- Create realistic test data
- Include edge cases and error conditions

### 3. Assertions
- Use specific assertions (`assertEqual`, `assertGreater`, etc.)
- Include descriptive failure messages
- Test both success and failure paths

### 4. Mocking
```python
# Good: Mock external dependencies
with patch('module.requests.get') as mock_get:
    mock_get.return_value = Mock(status_code=200)
    result = fetch_data()

# Bad: Making real API calls in tests
result = fetch_data()  # This hits real API!
```

### 5. Performance Testing
```python
# Always include performance logging
print(f"\n[PERF] Operation: {duration:.2f}s")
print(f"[PERF] Throughput: {items_per_sec:.0f} items/sec")
```

## Continuous Integration

Tests run automatically on:
- Every push to `main` or `develop`
- Every pull request
- Daily schedule (2 AM UTC)

### CI Workflow
1. **Unit Tests**: Must pass (coverage >80%)
2. **Integration Tests**: Must pass
3. **Performance Tests**: Can fail (warnings only)
4. **Code Quality**: Linting checks (warnings only)

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# Ensure src is in path
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"
```

#### Coverage Not Generated
```bash
# Install coverage tools
pip install pytest-cov coverage
```

#### Tests Hanging
```bash
# Use timeout
pytest --timeout=300
```

#### Parallel Tests Failing
```bash
# Disable parallel execution
pytest -n 0
```

## Metrics and Reporting

### Generate Coverage Report
```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Generate Test Report
```bash
pytest --html=report.html --self-contained-html
```

### Performance Report
```bash
pytest tests/performance/ --benchmark-json=benchmark.json
```

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure coverage >85% for new code
3. Add performance benchmarks if applicable
4. Update this README if adding new test categories

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [unittest Documentation](https://docs.python.org/3/library/unittest.html)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)

## Contact

For questions about the test suite, contact the development team or open an issue.
