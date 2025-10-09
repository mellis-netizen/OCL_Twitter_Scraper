# TGE Swarm Backend System

A comprehensive backend service architecture for the TGE (Token Generation Event) Detection Swarm system. This backend provides scalable microservices, real-time coordination, task orchestration, and optimization capabilities for managing intelligent agents that monitor cryptocurrency token launches.

## Architecture Overview

The TGE Swarm Backend is built on a microservices architecture with the following core components:

### Core Services

1. **Message Queue System** (`message_queue.py`)
   - Redis-based pub/sub messaging
   - Task queue management with priority support
   - Agent-to-agent communication
   - Real-time event broadcasting

2. **Agent Manager** (`agent_manager.py`)
   - Docker-based agent lifecycle management
   - Auto-scaling and load balancing
   - Health monitoring and recovery
   - Service discovery integration

3. **Coordination Service** (`coordination_service.py`)
   - Shared resource management
   - Agent synchronization
   - Conflict detection and resolution
   - Cross-pollination of insights

4. **Task Orchestrator** (`task_orchestrator.py`)
   - Intelligent task distribution
   - Adaptive load balancing
   - Performance-based scheduling
   - Task execution tracking

5. **Optimization Engine** (`optimization_engine.py`)
   - Agent recommendation processing
   - Automated code optimization
   - Validation and testing pipeline
   - Rollback capabilities

6. **WebSocket Manager** (`websocket_manager.py`)
   - Real-time dashboard updates
   - Client subscription management
   - Performance monitoring
   - Rate limiting and security

### Supporting Infrastructure

7. **Database Models** (`database/models.py`)
   - SQLAlchemy-based data persistence
   - Agent state tracking
   - Task execution history
   - Performance metrics storage

8. **Resilience Patterns** (`resilience/`)
   - Circuit breakers for fault tolerance
   - Retry handlers with exponential backoff
   - Timeout management
   - Error handling strategies

## Getting Started

### Prerequisites

- Python 3.9+
- Redis server
- PostgreSQL database
- Docker and Docker Compose

### Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup Redis cluster:**
   ```bash
   cd infrastructure/redis
   ./redis-cluster-setup.sh
   ```

3. **Initialize database:**
   ```bash
   python -m backend.database.models --database-url postgresql://user:pass@localhost/tge_swarm --init
   ```

4. **Configure services:**
   ```bash
   cp config/swarm_backend.yaml.example config/swarm_backend.yaml
   # Edit configuration as needed
   ```

### Running the Backend

**Start all services:**
```bash
python -m backend.swarm_backend
```

**Start individual services:**
```bash
# Message queue only
python -m backend.message_queue

# Agent manager API
python -m backend.agent_manager api

# Dashboard with WebSocket support
python -m backend.websocket_manager
```

**Check system status:**
```bash
python -m backend.swarm_backend --status
```

## Configuration

### Main Configuration (`config/swarm_backend.yaml`)

```yaml
log_level: INFO
redis_cluster:
  - localhost:6379

message_queue:
  cluster_name: tge-swarm

coordination_service:
  redis_url: redis://localhost:6379
  sync_interval: 90

agent_manager:
  max_agents_per_type: 5
  health_check_interval: 30

task_orchestrator:
  scheduling_strategy: adaptive
  max_concurrent_tasks_per_agent: 3

optimization_engine:
  auto_apply_low_risk: false
  require_approval_threshold: medium

dashboard_server:
  host: localhost
  port: 8080
```

## Core Components

### Message Queue System

The message queue provides reliable communication between agents and services:

```python
from backend.message_queue import create_message_queue, SwarmMessage, MessageType, Priority

# Create message queue
message_queue = await create_message_queue(["localhost:6379"])

# Publish message
message = SwarmMessage(
    id="unique-id",
    type=MessageType.TASK_ASSIGNMENT,
    sender="orchestrator",
    recipient="agent-1",
    timestamp=datetime.now(),
    payload={"task_data": "..."},
    priority=Priority.HIGH
)

await message_queue.publish_message(message)
```

### Agent Management

Deploy and manage agent containers:

```python
from backend.agent_manager import AgentManager

agent_manager = AgentManager()
await agent_manager.initialize(message_queue)

# Deploy agents
instances = await agent_manager.deploy_agent("scraping-efficiency-specialist", replicas=2)

# Scale agent type
await agent_manager.scale_agent_type("keyword-precision", target_replicas=3)

# Get agent status
status = await agent_manager.get_agent_status()
```

### Task Orchestration

Distribute tasks intelligently across agents:

```python
from backend.task_orchestrator import TaskOrchestrator, TaskDefinition, Priority

orchestrator = TaskOrchestrator(message_queue, agent_manager)
await orchestrator.initialize()

# Submit task
task = TaskDefinition(
    id="task-123",
    type="keyword-optimization",
    agent_type="keyword-precision",
    priority=Priority.HIGH,
    payload={"target_files": ["config.py"]},
    timeout=300
)

task_id = await orchestrator.submit_task(task)
```

### Optimization Engine

Process agent recommendations and apply optimizations:

```python
from backend.optimization_engine import OptimizationEngine, OptimizationRecommendation

engine = OptimizationEngine(message_queue, coordination_service, websocket_manager)
await engine.initialize()

# Submit optimization recommendation
recommendation = OptimizationRecommendation(
    id="opt-123",
    agent_id="agent-1",
    type=OptimizationType.CODE_OPTIMIZATION,
    severity=OptimizationSeverity.LOW,
    title="Improve keyword matching",
    description="Optimize keyword matching algorithm",
    target_files=["src/news_scraper.py"],
    proposed_changes=[...],
    expected_benefits=["Improved accuracy", "Better performance"],
    confidence_score=0.85
)

await engine.submit_recommendation(recommendation)
```

### Real-time Dashboard

WebSocket-based real-time updates:

```python
from backend.websocket_manager import EnhancedDashboardAPIServer

# Start dashboard server
server = EnhancedDashboardAPIServer(
    host="localhost",
    port=8080,
    message_queue=message_queue,
    agent_manager=agent_manager,
    task_orchestrator=orchestrator,
    coordination_service=coordination_service
)

await server.start_server()
```

**WebSocket Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8080/ws');

// Subscribe to specific updates
ws.send(JSON.stringify({
    type: 'subscribe',
    subscriptions: ['agents_only', 'metrics_only']
}));

// Handle real-time updates
ws.onmessage = (event) => {
    const update = JSON.parse(event.data);
    console.log('Real-time update:', update);
};
```

## Resilience Patterns

### Circuit Breakers

Protect against cascading failures:

```python
from backend.resilience import circuit_breaker, CircuitBreakerConfig

# Configure circuit breaker
config = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60,
    timeout=30.0
)

@circuit_breaker("external-api", config)
async def call_external_api():
    # API call that might fail
    pass
```

### Retry Logic

Handle transient failures with intelligent backoff:

```python
from backend.resilience import retry, RetryConfig, BackoffStrategy

config = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER,
    retryable_exceptions=(ConnectionError, TimeoutError)
)

@retry("database-operation", config)
async def database_operation():
    # Database operation that might fail transiently
    pass
```

## Database Schema

The system uses PostgreSQL with SQLAlchemy models:

### Key Tables

- **agents**: Agent instance information and status
- **tasks**: Task definitions and execution tracking
- **optimization_recommendations**: Agent optimization suggestions
- **optimization_executions**: Optimization execution history
- **coordination_events**: Agent coordination events
- **system_metrics**: Performance metrics and monitoring data

### Example Queries

```python
from backend.database.models import DatabaseManager, AgentRepository

# Initialize database
db_manager = DatabaseManager("postgresql://user:pass@localhost/tge_swarm")
session = db_manager.get_session()

# Use repositories
agent_repo = AgentRepository(session)

# Get healthy agents
healthy_agents = agent_repo.get_healthy_agents()

# Create new agent
agent = agent_repo.create_agent(
    name="keyword-agent-1",
    agent_type="keyword-precision",
    status=AgentStatus.HEALTHY,
    capabilities=["nlp", "text-analysis"]
)
```

## API Endpoints

### Agent Management
- `GET /api/agents/status` - Get all agents status
- `POST /api/agents/{agent_id}/{action}` - Control agent (start/stop/restart)
- `GET /api/agents/{agent_id}` - Get specific agent details

### Task Management
- `GET /api/tasks/status` - Get task queue status
- `GET /api/tasks/queue` - Get detailed queue information

### System Monitoring
- `GET /api/health` - System health check
- `GET /api/metrics/system` - Comprehensive system metrics
- `GET /api/coordination/status` - Coordination service status

### WebSocket Events
- `agent_status` - Agent status changes
- `task_update` - Task execution updates
- `metrics` - System metrics updates
- `optimization_result` - Optimization completions
- `system_alert` - System alerts and warnings

## Monitoring and Metrics

### Performance Metrics

The system collects comprehensive metrics:

- **Agent Metrics**: CPU, memory, task count, error rates
- **Task Metrics**: Queue lengths, execution times, success rates
- **System Metrics**: Throughput, latency, resource utilization
- **Optimization Metrics**: Success rates, performance improvements

### Health Monitoring

Automated health monitoring includes:

- Agent container health checks
- Service connectivity tests
- Resource utilization monitoring
- Performance threshold alerts
- Automatic recovery actions

### Alerting

The system provides real-time alerts for:

- Agent failures and recoveries
- Task execution problems
- Resource exhaustion
- Performance degradation
- System errors

## Development

### Running Tests

```bash
# Run all tests
python -m pytest backend/tests/

# Run specific test modules
python -m pytest backend/tests/test_message_queue.py
python -m pytest backend/tests/test_agent_manager.py

# Run with coverage
python -m pytest --cov=backend backend/tests/
```

### Adding New Services

1. Create service module in `backend/`
2. Implement service class with `initialize()` and `shutdown()` methods
3. Add service to `swarm_backend.py` startup sequence
4. Update configuration schema
5. Add tests and documentation

### Contributing

1. Follow Python PEP 8 style guidelines
2. Add comprehensive tests for new features
3. Update documentation and README
4. Use type hints and docstrings
5. Test with multiple Python versions

## Production Deployment

### Docker Deployment

Use the provided Docker Compose configuration:

```bash
docker-compose -f docker-compose.swarm.yml up -d
```

### Kubernetes Deployment

Helm charts are available in the `infrastructure/k8s/` directory:

```bash
helm install tge-swarm infrastructure/k8s/helm-chart/
```

### Monitoring Stack

The system integrates with:

- **Prometheus** for metrics collection
- **Grafana** for visualization
- **Consul** for service discovery
- **Redis Cluster** for high availability

## Security Considerations

- **Authentication**: JWT-based authentication for API endpoints
- **Authorization**: Role-based access control for administrative functions
- **Network Security**: TLS encryption for all communications
- **Container Security**: Minimal base images and security scanning
- **Data Protection**: Encryption at rest for sensitive data

## Troubleshooting

### Common Issues

1. **Redis Connection Errors**
   - Check Redis cluster configuration
   - Verify network connectivity
   - Check authentication credentials

2. **Agent Deployment Failures**
   - Verify Docker daemon is running
   - Check container image availability
   - Review resource allocation

3. **Database Connection Issues**
   - Verify PostgreSQL server status
   - Check connection string format
   - Review database permissions

4. **WebSocket Connection Problems**
   - Check firewall settings
   - Verify proxy configuration
   - Review CORS settings

### Debug Mode

Enable debug logging:

```yaml
log_level: DEBUG
```

### Performance Tuning

Optimize performance by adjusting:

- Redis connection pool sizes
- Task queue batch sizes
- Circuit breaker thresholds
- Retry attempt limits
- WebSocket message batching

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:

- Create an issue in the GitHub repository
- Check the documentation wiki
- Review troubleshooting guides
- Contact the development team

---

**Built with ❤️ for the TGE Detection Community**