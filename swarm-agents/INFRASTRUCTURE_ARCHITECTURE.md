# TGE Swarm Infrastructure Architecture

## Overview

This document describes the production-ready infrastructure architecture for the TGE (Token Generation Event) Swarm Orchestration System. The system is designed for scalability, fault tolerance, and high availability.

## Architecture Diagram (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           TGE SWARM INFRASTRUCTURE                              │
└─────────────────────────────────────────────────────────────────────────────────┘

                                   ┌─────────────┐
                                   │   Internet  │
                                   └─────┬───────┘
                                         │
                              ┌──────────▼──────────┐
                              │     HAProxy LB      │
                              │   (80/443/8404)     │
                              └──────────┬──────────┘
                                         │
          ┌──────────────────────────────┼──────────────────────────────┐
          │                              │                              │
          ▼                              ▼                              ▼
┌─────────────────┐           ┌─────────────────┐           ┌─────────────────┐
│   Swarm Queen   │           │    Prometheus   │           │     Grafana     │
│   :8080/:8001   │           │      :9090      │           │      :3000      │
└─────────┬───────┘           └─────────────────┘           └─────────────────┘
          │
          │ Orchestrates
          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            SWARM AGENT LAYER                                    │
├─────────────────┬─────────────────┬─────────────────┬─────────────────┬────────┤
│ Scraping Effic. │ Keyword Precis. │ API Reliability │ Performance     │ Data   │
│ Specialist      │ Specialist      │ Optimizer       │ Optimizer       │Quality │
│ :8010           │ :8011           │ :8012           │ :8013           │ :8014  │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┴────────┘
          │                              │                              │
          └──────────────────┬───────────────────────────────────────────┘
                             │
                             ▼
        ┌─────────────────────────────────────────────────────────────────┐
        │                 SERVICE DISCOVERY LAYER                        │
        ├─────────────────┬─────────────────┬─────────────────────────────┤
        │     Consul      │ Service Registry│   Memory Coordinator        │
        │     :8500       │     :8020       │        :8002                │
        └─────────────────┴─────────────────┴─────────────────────────────┘
                             │
                             ▼
        ┌─────────────────────────────────────────────────────────────────┐
        │                    DATA LAYER                                   │
        ├─────────────────┬─────────────────┬─────────────────────────────┤
        │   PostgreSQL    │  Redis Cluster  │      Backup Service         │
        │ Primary :5432   │ 3 Masters       │       S3/Local              │
        │                 │ :7001-7003      │                             │
        └─────────────────┴─────────────────┴─────────────────────────────┘
                             │
                             ▼
        ┌─────────────────────────────────────────────────────────────────┐
        │                MONITORING & HEALTH LAYER                       │
        ├─────────────────┬─────────────────┬─────────────────────────────┤
        │  Health Monitor │  AlertManager   │     Jaeger Tracing          │
        │   Auto-Recovery │     :9093       │       :16686               │
        └─────────────────┴─────────────────┴─────────────────────────────┘

NETWORK SEGMENTATION:
├── swarm-external   (172.26.0.0/24) - Public facing
├── swarm-internal   (172.20.0.0/24) - Service communication
├── swarm-agents     (172.23.0.0/24) - Agent communication
├── swarm-db         (172.21.0.0/24) - Database access
├── swarm-cache      (172.22.0.0/24) - Redis cluster
├── swarm-discovery  (172.24.0.0/24) - Service discovery
└── swarm-monitoring (172.25.0.0/24) - Monitoring stack
```

## Core Components

### 1. Swarm Queen Orchestrator
- **Role**: Central coordination and management
- **Port**: 8080 (API), 8001 (Metrics)
- **Resources**: 2GB RAM, 1 CPU
- **Responsibilities**:
  - Agent lifecycle management
  - Task distribution and prioritization
  - Real-time optimization decisions
  - Performance monitoring and reporting

### 2. Memory Coordinator
- **Role**: Shared memory and cross-agent communication
- **Port**: 8002
- **Resources**: 1GB RAM, 0.5 CPU
- **Responsibilities**:
  - SAFLA neural memory management
  - Cross-pollination between agents
  - Synthesis of findings
  - Memory persistence and retrieval

### 3. Swarm Agents (5 Specialists)
Each agent runs in dedicated containers with:
- **Resources**: 512MB RAM, 0.3 CPU per agent
- **Scaling**: Horizontal scaling supported
- **Health Checks**: Built-in health monitoring

#### Agent Types:
1. **Scraping Efficiency Specialist** (:8010)
   - API rate optimization
   - Concurrent request management
   - Cache strategy optimization

2. **TGE Keyword Precision Specialist** (:8011)
   - Keyword matching accuracy
   - False positive elimination
   - Company name disambiguation

3. **API Reliability Optimizer** (:8012)
   - Error handling robustness
   - Circuit breaker implementation
   - Intelligent retry mechanisms

4. **Performance Bottleneck Eliminator** (:8013)
   - CPU/memory optimization
   - Async pattern improvements
   - Database query efficiency

5. **Data Quality Enforcer** (:8014)
   - TGE data validation
   - Duplicate detection
   - Data sanitization

## Data Layer

### PostgreSQL Primary Database
- **Image**: postgres:15-alpine
- **Port**: 5432
- **Storage**: Persistent volume with backup
- **Configuration**:
  - Connection pooling
  - Replication ready
  - Automated backups
  - Performance monitoring

### Redis Cluster (3 Masters)
- **Ports**: 7001-7003, 17001-17003 (cluster bus)
- **Configuration**:
  - Cluster mode enabled
  - AOF + RDB persistence
  - Memory management (512MB per node)
  - Pub/Sub for agent communication

**Redis Channels**:
- `swarm:channels:agent-communication`
- `swarm:channels:queen-commands`
- `swarm:channels:memory-sync`
- `swarm:channels:health-checks`
- `swarm:memory:*` (memory coordination)
- `swarm:metrics:*` (performance monitoring)

## Service Discovery

### Consul Cluster
- **Port**: 8500 (HTTP), 8600 (DNS)
- **Features**:
  - Service registration and discovery
  - Health checking
  - Configuration management
  - Service mesh ready

### Service Registry
- **Port**: 8020
- **Integration**: Consul + PostgreSQL
- **Responsibilities**:
  - Automatic service registration
  - Health status tracking
  - Service metadata management

## Monitoring Stack

### Prometheus
- **Port**: 9090
- **Retention**: 15 days, 10GB max
- **Scrape Targets**:
  - All swarm components
  - Infrastructure services
  - System metrics (node_exporter)
  - Application metrics

### Grafana
- **Port**: 3000
- **Features**:
  - Pre-configured dashboards
  - TGE-specific metrics visualization
  - Alert visualization
  - User management

### AlertManager
- **Port**: 9093
- **Channels**: Webhook, Email, Console
- **Alert Rules**:
  - Agent health monitoring
  - Resource usage thresholds
  - Performance degradation
  - System failures

### Jaeger Tracing
- **Port**: 16686 (UI), 14268 (collector)
- **Purpose**: Distributed tracing for debugging and performance analysis

## Health Monitoring & Auto-Recovery

### Health Monitor
- **Comprehensive Health Checks**:
  - HTTP endpoint monitoring
  - Database connectivity
  - Redis cluster health
  - Agent responsiveness
  - Resource utilization

### Auto-Recovery Actions
- **RESTART**: Container restart for transient failures
- **RECREATE**: Full container recreation for persistent issues
- **SCALE_UP**: Horizontal scaling for capacity issues
- **FAILOVER**: Backup activation for critical failures
- **ALERT_ONLY**: Notification without automatic action

### Recovery Policies
- Maximum 3 recovery attempts per component
- 5-minute cooldown between attempts
- Circuit breaker for repeated failures

## Load Balancing & Proxy

### HAProxy
- **Ports**: 80 (HTTP), 443 (HTTPS), 8404 (Stats)
- **Features**:
  - SSL termination
  - Health-based routing
  - Statistics dashboard
  - Load distribution

**Routing Rules**:
- `/api/*` → Swarm Queen
- `/grafana/*` → Grafana
- `/prometheus/*` → Prometheus
- Default → Swarm Queen

## Backup & Disaster Recovery

### Backup Service
- **Schedule**: Daily at 2 AM
- **Retention**: 30 days
- **Storage**: Local + S3 (optional)
- **Components**:
  - PostgreSQL database dumps
  - Redis RDB snapshots
  - SAFLA memory state
  - Configuration files

### Disaster Recovery
- **RTO**: < 30 minutes (Recovery Time Objective)
- **RPO**: < 24 hours (Recovery Point Objective)
- **Automated restoration scripts**
- **Multi-AZ deployment support**

## Security

### Network Security
- **Segmented networks** for different layers
- **Internal-only networks** for sensitive communication
- **Firewall rules** via Docker networks

### Access Control
- **Service-to-service authentication**
- **API key management**
- **Role-based access control** (Consul ACLs)

### Data Protection
- **Encryption at rest** (PostgreSQL + Redis)
- **Encryption in transit** (TLS/SSL)
- **Secrets management** via environment variables

## Scalability

### Horizontal Scaling
- **Agent instances**: Scale up/down based on load
- **Redis cluster**: Add/remove nodes dynamically
- **Load balancer**: Multiple HAProxy instances

### Vertical Scaling
- **Resource allocation**: Adjustable per component
- **Memory limits**: Configurable per service
- **CPU quotas**: Fine-grained control

### Auto-Scaling Triggers
- **CPU usage** > 80% for 10+ minutes
- **Memory usage** > 90% for 5+ minutes
- **Response time** > 5 seconds consistently
- **Error rate** > 5% for 5+ minutes

## Deployment

### Infrastructure as Code
- **Docker Compose** for orchestration
- **Environment-based configuration**
- **Automated deployment scripts**
- **Version-controlled infrastructure**

### Deployment Strategies
- **Blue-Green**: Zero-downtime deployments
- **Rolling**: Gradual instance replacement
- **Canary**: Staged rollout with validation

### Environment Management
- **Development**: Single-node setup
- **Staging**: Reduced-scale production replica
- **Production**: Full high-availability setup

## Performance Characteristics

### Expected Performance
- **TGE Detection Latency**: < 30 seconds
- **API Response Time**: < 500ms (95th percentile)
- **Agent Health Check**: 30-second intervals
- **Memory Sync**: 90-second intervals
- **Monitoring Scrape**: 15-second intervals

### Resource Requirements
- **Minimum**: 8GB RAM, 4 CPU cores, 50GB storage
- **Recommended**: 16GB RAM, 8 CPU cores, 100GB SSD
- **Production**: 32GB RAM, 16 CPU cores, 500GB SSD

### Throughput Capacity
- **Concurrent Agents**: 5-50 (scalable)
- **API Requests**: 1000 req/sec
- **TGE Processing**: 100 events/minute
- **Memory Operations**: 10000 ops/sec

## Maintenance

### Regular Maintenance Tasks
- **Daily**: Log rotation, backup verification
- **Weekly**: Performance review, capacity planning
- **Monthly**: Security updates, configuration review
- **Quarterly**: Disaster recovery testing

### Monitoring & Alerting
- **Real-time**: Health status, performance metrics
- **Alerts**: Critical failures, performance degradation
- **Reports**: Daily summaries, weekly performance reports

### Update Procedures
- **Security patches**: Automated where possible
- **Component updates**: Staged with rollback capability
- **Configuration changes**: Version controlled and tested

## Troubleshooting

### Common Issues
1. **Agent Communication Failures**
   - Check Redis cluster health
   - Verify network connectivity
   - Review Consul service registration

2. **Performance Degradation**
   - Monitor resource utilization
   - Check database connection pools
   - Review API rate limiting

3. **Memory Coordinator Issues**
   - Verify SAFLA memory persistence
   - Check cross-agent communication
   - Review synthesis operations

### Debug Commands
```bash
# Check overall health
docker-compose -f docker-compose.swarm.yml ps

# View service logs
docker-compose -f docker-compose.swarm.yml logs -f [service]

# Health monitoring
python infrastructure/health/health_monitor.py status

# Redis cluster status
redis-cli -h redis-master-1 -p 7001 cluster nodes

# PostgreSQL connection test
psql $POSTGRES_URL -c "SELECT version();"

# Consul services
curl http://localhost:8500/v1/agent/services
```

---

