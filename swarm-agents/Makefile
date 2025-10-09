# Makefile for TGE Swarm Testing
# Provides convenient commands for running tests, linting, and CI operations

.PHONY: help test test-unit test-integration test-e2e test-performance test-all
.PHONY: test-coverage test-fast test-slow lint format clean setup
.PHONY: test-redis test-database test-docker test-websocket
.PHONY: test-ci test-report install-test-deps

# Default target
help:
	@echo "TGE Swarm Testing Commands"
	@echo "=========================="
	@echo ""
	@echo "Test Execution:"
	@echo "  test              - Run all tests"
	@echo "  test-unit         - Run unit tests only"
	@echo "  test-integration  - Run integration tests only"
	@echo "  test-e2e          - Run end-to-end tests only"
	@echo "  test-performance  - Run performance tests only"
	@echo "  test-fast         - Run fast tests (exclude slow markers)"
	@echo "  test-slow         - Run slow tests only"
	@echo ""
	@echo "Test Categories:"
	@echo "  test-redis        - Run Redis-dependent tests"
	@echo "  test-database     - Run database tests"
	@echo "  test-docker       - Run Docker-dependent tests"
	@echo "  test-websocket    - Run WebSocket tests"
	@echo ""
	@echo "Coverage and Reporting:"
	@echo "  test-coverage     - Run tests with coverage report"
	@echo "  test-report       - Generate HTML test report"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint              - Run all linting checks"
	@echo "  format            - Format code with black and isort"
	@echo ""
	@echo "Setup and Maintenance:"
	@echo "  install-test-deps - Install test dependencies"
	@echo "  clean             - Clean test artifacts"
	@echo "  setup             - Setup test environment"

# Test execution targets
test:
	pytest tests/ --maxfail=5

test-unit:
	pytest tests/unit/ -m "unit" --maxfail=3

test-integration:
	pytest tests/integration/ -m "integration" --maxfail=2

test-e2e:
	pytest tests/e2e/ -m "e2e" --maxfail=1

test-performance:
	pytest tests/performance/ -m "performance" --maxfail=1

test-all: test-unit test-integration test-e2e
	@echo "All test suites completed"

# Speed-based test filtering
test-fast:
	pytest tests/ -m "not slow" --maxfail=5

test-slow:
	pytest tests/ -m "slow" --maxfail=2

# Dependency-based test filtering
test-redis:
	pytest tests/ -m "redis" --maxfail=3

test-database:
	pytest tests/ -m "database" --maxfail=3

test-docker:
	pytest tests/ -m "docker" --maxfail=2

test-websocket:
	pytest tests/ -m "websocket" --maxfail=2

# Coverage and reporting
test-coverage:
	pytest tests/ --cov=backend --cov-report=html --cov-report=term-missing --cov-report=xml

test-report:
	pytest tests/ --html=reports/test_report.html --self-contained-html

# Parallel test execution
test-parallel:
	pytest tests/ -n auto --dist worksteal

# CI-specific test commands
test-ci:
	pytest tests/ \
		--maxfail=1 \
		--cov=backend \
		--cov-report=xml \
		--cov-report=term \
		--junit-xml=reports/junit.xml \
		--html=reports/test_report.html \
		--self-contained-html

# Code quality targets
lint:
	@echo "Running flake8..."
	flake8 backend/ tests/ --max-line-length=100 --exclude=__pycache__
	@echo "Running mypy..."
	mypy backend/ --ignore-missing-imports
	@echo "Running bandit security checks..."
	bandit -r backend/ -f json -o reports/bandit-report.json || true
	@echo "Running isort check..."
	isort --check-only backend/ tests/
	@echo "Running black check..."
	black --check backend/ tests/

format:
	@echo "Formatting with isort..."
	isort backend/ tests/
	@echo "Formatting with black..."
	black backend/ tests/

# Setup and maintenance
install-test-deps:
	pip install -r tests/requirements.txt
	pip install -e .

setup: install-test-deps
	@echo "Setting up test environment..."
	mkdir -p reports logs
	@echo "Creating test configuration..."
	@if [ ! -f tests/test_config.yaml ]; then \
		cp tests/test_config.yaml.example tests/test_config.yaml 2>/dev/null || \
		echo "log_level: DEBUG\nredis_url: redis://localhost:6379/15\ndatabase_url: sqlite:///test.db" > tests/test_config.yaml; \
	fi
	@echo "Test environment ready!"

clean:
	@echo "Cleaning test artifacts..."
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf reports/
	rm -rf logs/test_*.log
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage*" -delete
	@echo "Cleanup complete!"

# Development helpers
test-watch:
	@echo "Starting test watcher (requires pytest-watch)..."
	ptw tests/ -- --maxfail=1

test-debug:
	pytest tests/ -vvv -s --tb=long --capture=no

test-profile:
	pytest tests/performance/ --profile --profile-svg

# Docker-based testing
test-docker-env:
	@echo "Running tests in Docker environment..."
	docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
	docker-compose -f docker-compose.test.yml down

# Database testing helpers
test-db-setup:
	@echo "Setting up test database..."
	python -c "from backend.database.models import initialize_database; initialize_database('sqlite:///test.db', drop_existing=True)"

test-db-cleanup:
	rm -f test.db test.db-*

# Load testing
load-test:
	@echo "Running load tests with Locust..."
	locust -f tests/load/locustfile.py --host=http://localhost:8080

# Test data management
generate-test-data:
	python tests/utils/generate_test_data.py

# Benchmark tests
benchmark:
	pytest tests/performance/ --benchmark-only --benchmark-sort=mean

# Security testing
security-test:
	bandit -r backend/ -f json -o reports/security-report.json
	safety check --json --output reports/safety-report.json || true

# API testing
test-api:
	pytest tests/integration/test_api_endpoints.py -v

# Performance profiling
profile-tests:
	python -m cProfile -o reports/test_profile.prof -m pytest tests/performance/
	python -c "import pstats; p = pstats.Stats('reports/test_profile.prof'); p.sort_stats('cumulative').print_stats(20)"

# Memory testing
test-memory:
	pytest tests/performance/ --memray --memray-bin-path=reports/

# Test environment validation
validate-test-env:
	@echo "Validating test environment..."
	@python -c "import redis; r = redis.Redis(host='localhost', port=6379, db=15); r.ping(); print('Redis: OK')" || echo "Redis: FAILED"
	@python -c "import docker; docker.from_env().ping(); print('Docker: OK')" || echo "Docker: FAILED"
	@python -c "import sqlalchemy; print('SQLAlchemy: OK')" || echo "SQLAlchemy: FAILED"
	@python -c "import pytest; print(f'Pytest: OK (version {pytest.__version__})')" || echo "Pytest: FAILED"

# Continuous testing
test-continuous:
	@echo "Starting continuous testing..."
	while true; do \
		make test-fast; \
		sleep 30; \
	done

# Test metrics collection
test-metrics:
	pytest tests/ --benchmark-json=reports/benchmark.json
	python tests/utils/analyze_metrics.py reports/benchmark.json