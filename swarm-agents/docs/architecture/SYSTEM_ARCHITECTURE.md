# TGE News Sweeper - System Architecture Design

**Version:** 2.0
**Last Updated:** 2025-10-13
**Status:** Architecture Phase - SPARC Methodology

---

## Executive Summary

The TGE (Token Generation Event) News Sweeper is a distributed, real-time monitoring and scraping system designed to detect token launch announcements from multiple news sources with production-grade reliability, optimal performance, and high accuracy.

### Key Architecture Principles

1. **Microservices Architecture** - Modular, independently scalable components
2. **Event-Driven Design** - Asynchronous message-based communication
3. **Resilience First** - Circuit breakers, retry logic, graceful degradation
4. **Performance Optimized** - Caching, connection pooling, async operations
5. **Scalability** - Horizontal scaling with adaptive load balancing
6. **Observability** - Comprehensive logging, metrics, and monitoring

---

## 1. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  Dashboard UI (React/TS)  │  Monitoring Clients  │  Alert Subscribers   │
└────────────┬────────────────────────┬────────────────────────┬──────────┘
             │                        │                        │
             └────────────────────────┼────────────────────────┘
                                      │
                          ┌───────────▼───────────┐
                          │   API Gateway Layer    │
                          │  (WebSocket + REST)    │
                          └───────────┬───────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                    APPLICATION LAYER                       │
        ├────────────────────────────────────────────────────────────┤
        │                                                            │
        │  ┌─────────────────────────────────────────────────────┐ │
        │  │         Queen Coordinator (Hierarchical)            │ │
        │  │  - Task Distribution  - Priority Management         │ │
        │  │  - Adaptive Learning  - Optimization Orchestration  │ │
        │  └───────────┬──────────────────────────┬──────────────┘ │
        │              │                          │                 │
        │  ┌───────────▼──────────┐   ┌──────────▼─────────────┐  │
        │  │  Coordination Service │   │  Task Orchestrator     │  │
        │  │  - Resource Sync      │   │  - Load Balancing      │  │
        │  │  - State Management   │   │  - Task Scheduling     │  │
        │  └───────────┬──────────┘   └──────────┬─────────────┘  │
        │              │                          │                 │
        │  ┌───────────▼──────────────────────────▼─────────────┐ │
        │  │            Message Queue (Redis Pub/Sub)           │ │
        │  │  - Priority Queues  - Event Broadcasting           │ │
        │  └───────────┬──────────────────────────┬─────────────┘ │
        │              │                          │                 │
        │  ┌───────────▼──────────────────────────▼─────────────┐ │
        │  │              Specialized Worker Agents              │ │
        │  ├────────────────────────────────────────────────────┤ │
        │  │ Scraping      │ Keyword      │ API          │ Perf  │ │
        │  │ Efficiency    │ Precision    │ Reliability  │ Opt   │ │
        │  │ Specialist    │ Specialist   │ Guardian     │ Agent │ │
        │  └───────────┬──────────────────────────┬─────────────┘ │
        └──────────────┼──────────────────────────┼────────────────┘
                       │                          │
        ┌──────────────▼──────────────────────────▼────────────────┐
        │                    DATA LAYER                             │
        ├───────────────────────────────────────────────────────────┤
        │  PostgreSQL  │  Redis Cache  │  Memory Store  │  Metrics │
        │  (Persistent)│  (Session)    │  (SAFLA)       │  (Time)  │
        └───────────────────────────────────────────────────────────┘
                                      │
        ┌──────────────────────────────▼────────────────────────────┐
        │                INFRASTRUCTURE LAYER                        │
        ├───────────────────────────────────────────────────────────┤
        │  Docker    │  Consul     │  Prometheus  │  Grafana       │
        │  Containers│  Discovery  │  Metrics     │  Dashboard     │
        └───────────────────────────────────────────────────────────┘
```

---

## 2. Component Architecture

### 2.1 Core Components

#### A. Queen Coordinator
**Location:** `/backend/queen_coordinator.py`

```python
class QueenCoordinator:
    """
    Hierarchical coordinator managing all agent activities
    """
    responsibilities:
        - Strategic task distribution
        - Adaptive priority management
        - Cross-agent optimization
        - Real-time performance tuning
        - Bottleneck detection and resolution

    interfaces:
        REST:
            - POST /api/queen/assign-task
            - GET /api/queen/status
            - POST /api/queen/optimize

        Events:
            publishes:
                - task.assigned
                - optimization.requested
                - priority.escalated
            subscribes:
                - agent.completed
                - agent.failed
                - metrics.threshold_exceeded

    dependencies:
        - CoordinationService (state sync)
        - TaskOrchestrator (scheduling)
        - MessageQueue (communication)
        - OptimizationEngine (improvements)
```

#### B. Scraping Components

**Location:** `/src/scrapers/`

```python
# Twitter/X Scraper
class TwitterMonitor:
    """
    Real-time Twitter monitoring with rate limit optimization
    """
    features:
        - Tweet streaming with filters
        - Rate limit-aware polling
        - Connection pooling
        - Retry with exponential backoff
        - Circuit breaker protection

    performance_targets:
        - API calls: < 50% of rate limit
        - Latency: < 2s per request
        - Memory: < 100MB per instance
        - Uptime: > 99.5%

# News Source Scraper
class NewsScraperOptimized:
    """
    Multi-source news scraping with intelligent caching
    """
    features:
        - RSS feed parsing
        - Web scraping with Beautiful Soup
        - Content deduplication
        - Intelligent cache invalidation
        - Concurrent request batching

    sources:
        - CoinDesk RSS
        - Cointelegraph API
        - CryptoSlate web scraping
        - Custom sources via configuration
```

#### C. Keyword Matching Engine

**Location:** `/src/keyword_engine/`

```python
class KeywordMatchingEngine:
    """
    High-precision keyword matching with context awareness
    """
    features:
        - Multi-pattern matching (regex + fuzzy)
        - Company name disambiguation
        - Token symbol detection
        - Context scoring algorithm
        - False positive filtering

    algorithms:
        - TF-IDF for relevance scoring
        - Named Entity Recognition (NER)
        - Contextual proximity scoring
        - Sentiment analysis integration

    performance_targets:
        - Precision: > 95%
        - Recall: > 90%
        - False positive rate: < 5%
        - Processing: < 100ms per document
```

#### D. Data Persistence Layer

**Location:** `/backend/database/`

```sql
-- Schema Design
CREATE TABLE tge_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(255) NOT NULL,
    token_symbol VARCHAR(50),
    announcement_date TIMESTAMP NOT NULL,
    source_type VARCHAR(50) NOT NULL, -- 'twitter', 'news', etc.
    source_url TEXT NOT NULL,
    content TEXT NOT NULL,
    confidence_score DECIMAL(3,2) NOT NULL,
    metadata JSONB,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending',

    INDEX idx_company_name (company_name),
    INDEX idx_token_symbol (token_symbol),
    INDEX idx_announcement_date (announcement_date),
    INDEX idx_confidence_score (confidence_score),
    INDEX idx_detected_at (detected_at)
);

CREATE TABLE scraping_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(100) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    items_scraped INTEGER DEFAULT 0,
    items_matched INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    duration_ms INTEGER,
    metadata JSONB
);

-- Partitioning for performance
CREATE TABLE tge_events_archive (
    LIKE tge_events INCLUDING ALL
) PARTITION BY RANGE (detected_at);
```

---

## 3. Technology Stack

### 3.1 Backend Services

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Runtime | Python | 3.11+ | Primary application runtime |
| API Framework | FastAPI | 0.104+ | REST API and WebSocket server |
| Async Framework | asyncio | stdlib | Asynchronous operations |
| Database | PostgreSQL | 15+ | Persistent data storage |
| Cache/Queue | Redis | 7.0+ | Caching and message queue |
| ORM | SQLAlchemy | 2.0+ | Database abstraction |
| Migration | Alembic | 1.12+ | Database migrations |

### 3.2 Scraping & Processing

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| HTTP Client | aiohttp | 3.9+ | Async HTTP requests |
| Twitter API | tweepy | 4.14+ | Twitter/X integration |
| HTML Parsing | Beautiful Soup | 4.12+ | Web scraping |
| RSS Parsing | feedparser | 6.0+ | RSS feed processing |
| NLP | spaCy | 3.7+ | Named entity recognition |
| Text Analysis | nltk | 3.8+ | Text processing utilities |

### 3.3 Infrastructure

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Containerization | Docker | 24+ | Container runtime |
| Orchestration | Docker Compose | 2.23+ | Local orchestration |
| Service Discovery | Consul | 1.17+ | Service registry |
| Monitoring | Prometheus | 2.48+ | Metrics collection |
| Visualization | Grafana | 10.2+ | Metrics dashboards |
| Load Balancing | Nginx | 1.25+ | Reverse proxy |

### 3.4 Frontend Dashboard

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | React | 18+ | UI framework |
| Language | TypeScript | 5+ | Type-safe JavaScript |
| Build Tool | Vite | 5+ | Fast build tooling |
| State Management | Zustand | 4+ | State management |
| Styling | TailwindCSS | 3+ | Utility-first CSS |
| WebSocket | Socket.io-client | 4+ | Real-time updates |

---

## 4. Design Patterns

### 4.1 Resilience Patterns

#### Circuit Breaker
```python
@circuit_breaker("twitter-api",
    failure_threshold=5,
    recovery_timeout=60,
    timeout=30.0
)
async def fetch_tweets(query: str):
    """Protected API call with circuit breaker"""
    pass
```

#### Retry with Backoff
```python
@retry("news-scraper",
    max_attempts=3,
    base_delay=1.0,
    backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER
)
async def scrape_news_source(url: str):
    """Retry transient failures with exponential backoff"""
    pass
```

#### Bulkhead
```python
class ScraperPool:
    """Isolate failures with connection pooling"""
    twitter_pool: asyncio.Semaphore(max_connections=10)
    news_pool: asyncio.Semaphore(max_connections=20)
```

### 4.2 Performance Patterns

#### Connection Pooling
```python
class ConnectionPoolManager:
    """Reuse connections across requests"""

    pools = {
        "twitter": aiohttp.TCPConnector(limit=10, limit_per_host=5),
        "news": aiohttp.TCPConnector(limit=20, limit_per_host=10)
    }
```

#### Caching Strategy
```python
class CacheManager:
    """Multi-level caching with TTL"""

    layers:
        - L1: In-memory LRU cache (< 1ms)
        - L2: Redis cache (< 10ms)
        - L3: Database query cache (< 100ms)

    policies:
        - tweet_metadata: 5 minutes
        - company_info: 1 hour
        - keyword_patterns: 24 hours
```

#### Batch Processing
```python
class BatchProcessor:
    """Process items in optimized batches"""

    config:
        batch_size: 50
        max_wait_time: 5s
        max_memory: 100MB
```

### 4.3 Architectural Patterns

#### Repository Pattern
```python
class TGEEventRepository:
    """Abstract data access layer"""

    def create_event(self, event: TGEEvent) -> UUID
    def get_by_id(self, event_id: UUID) -> TGEEvent
    def find_by_company(self, company: str) -> List[TGEEvent]
    def mark_processed(self, event_id: UUID) -> bool
```

#### Service Layer
```python
class TGEDetectionService:
    """Business logic encapsulation"""

    def __init__(self,
                 repository: TGEEventRepository,
                 keyword_engine: KeywordMatchingEngine,
                 notification_service: NotificationService):
        pass

    async def process_content(self, content: str, source: str) -> Optional[TGEEvent]
```

#### Event-Driven Architecture
```python
class EventBus:
    """Publish-subscribe event system"""

    events = {
        "tge.detected": [NotificationHandler, DatabaseHandler, MetricsHandler],
        "scraping.completed": [CoordinationHandler, OptimizationHandler],
        "error.occurred": [AlertHandler, LogHandler]
    }
```

---

## 5. File Structure & Organization

```
/Users/apple/Documents/GitHub/OCL_Twitter_Scraper/swarm-agents/

├── src/                                    # Source code (NEW)
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── twitter_monitor.py             # Twitter/X monitoring
│   │   ├── news_scraper_optimized.py      # News source scraping
│   │   ├── scraper_base.py                # Base scraper class
│   │   └── rate_limiter.py                # Rate limiting logic
│   │
│   ├── keyword_engine/
│   │   ├── __init__.py
│   │   ├── matcher.py                     # Keyword matching engine
│   │   ├── context_scorer.py              # Context analysis
│   │   ├── entity_recognizer.py           # NER for companies/tokens
│   │   └── false_positive_filter.py       # FP elimination
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── tge_detection_service.py       # Core detection logic
│   │   ├── notification_service.py        # Alert notifications
│   │   ├── deduplication_service.py       # Duplicate detection
│   │   └── validation_service.py          # Data validation
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── tge_event.py                   # TGE event model
│   │   ├── scraping_session.py            # Session model
│   │   └── keyword_pattern.py             # Pattern model
│   │
│   └── utils/
│       ├── __init__.py
│       ├── text_processing.py             # Text utilities
│       ├── date_parsing.py                # Date extraction
│       └── url_validator.py               # URL utilities
│
├── backend/                                # Backend services (EXISTING)
│   ├── swarm_backend.py                   # Main backend entry
│   ├── agent_manager.py                   # Agent lifecycle
│   ├── coordination_service.py            # Coordination
│   ├── task_orchestrator.py               # Task distribution
│   ├── optimization_engine.py             # Optimization
│   ├── message_queue.py                   # Message queue
│   ├── websocket_manager.py               # WebSocket server
│   │
│   ├── database/
│   │   ├── models.py                      # SQLAlchemy models
│   │   ├── repositories.py                # Data access (NEW)
│   │   └── migrations/                    # Alembic migrations (NEW)
│   │
│   ├── performance/
│   │   ├── monitoring.py                  # Performance monitoring
│   │   ├── profiler.py                    # Profiling utilities
│   │   ├── memory_manager.py              # Memory optimization
│   │   └── connection_pool.py             # Connection pooling
│   │
│   └── resilience/
│       ├── circuit_breaker.py             # Circuit breaker
│       └── retry_handler.py               # Retry logic
│
├── config/                                 # Configuration (NEW)
│   ├── default_config.yaml                # Default settings
│   ├── production_config.yaml             # Production overrides
│   ├── keywords_config.yaml               # Keyword patterns
│   └── sources_config.yaml                # Scraping sources
│
├── tests/                                  # Test suite (EXISTING)
│   ├── unit/                              # Unit tests
│   ├── integration/                       # Integration tests
│   ├── e2e/                               # End-to-end tests
│   └── performance/                       # Performance tests
│
├── docs/                                   # Documentation (NEW)
│   ├── architecture/
│   │   ├── SYSTEM_ARCHITECTURE.md         # This document
│   │   ├── COMPONENT_DESIGN.md            # Component details (TBD)
│   │   └── SEQUENCE_DIAGRAMS.md           # Interaction flows (TBD)
│   │
│   ├── api/
│   │   ├── REST_API.md                    # REST API documentation
│   │   └── WEBSOCKET_API.md               # WebSocket API docs
│   │
│   └── guides/
│       ├── DEPLOYMENT_GUIDE.md            # Deployment instructions
│       ├── DEVELOPMENT_GUIDE.md           # Developer guide
│       └── OPERATIONS_GUIDE.md            # Operations manual
│
├── scripts/                                # Utility scripts (NEW)
│   ├── setup_dev_env.sh                   # Dev environment setup
│   ├── run_migrations.sh                  # Database migrations
│   └── seed_test_data.py                  # Test data seeding
│
├── dashboard/                              # Frontend dashboard (EXISTING)
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── types/
│   └── package.json
│
├── infrastructure/                         # Infrastructure (EXISTING)
│   ├── docker/
│   │   ├── Dockerfile.scraper             # Scraper container (NEW)
│   │   ├── Dockerfile.backend             # Backend container
│   │   └── Dockerfile.dashboard           # Dashboard container
│   │
│   ├── k8s/                               # Kubernetes configs (NEW)
│   │   ├── namespace.yaml
│   │   ├── deployments/
│   │   ├── services/
│   │   └── ingress/
│   │
│   └── monitoring/
│       ├── prometheus/
│       └── grafana/
│
├── docker-compose.yml                      # Local development
├── docker-compose.swarm.yml                # Swarm deployment
├── requirements.txt                        # Python dependencies
├── package.json                            # Node dependencies
├── pytest.ini                              # Pytest configuration
├── .env.example                            # Environment template
└── README.md                               # Project overview
```

---

## 6. Data Flow Architecture

### 6.1 TGE Detection Flow

```
┌───────────────────────────────────────────────────────────────┐
│                    TGE Detection Pipeline                      │
└───────────────────────────────────────────────────────────────┘

1. SCRAPING PHASE
   ┌──────────────┐
   │ Twitter API  │──┐
   └──────────────┘  │
   ┌──────────────┐  │    ┌─────────────────┐
   │ News RSS     │──┼───▶│ Scraper Manager │
   └──────────────┘  │    └────────┬────────┘
   ┌──────────────┐  │             │
   │ Web Scrapers │──┘             │
   └──────────────┘                │
                                   ▼
2. FILTERING PHASE                 │
   ┌─────────────────────────────┐│
   │  Rate Limiter               ││
   │  - Check limits             ││
   │  - Queue if needed          ││
   └──────────────┬──────────────┘│
                  │                │
                  ▼                │
   ┌─────────────────────────────┐│
   │  Deduplication Service      ││
   │  - Content hash check       ││
   │  - URL deduplication        ││
   │  - Time window filtering    ││
   └──────────────┬──────────────┘│
                  │                │
3. ANALYSIS PHASE │                │
                  ▼                │
   ┌─────────────────────────────┐│
   │  Keyword Matching Engine    ││
   │  - Pattern matching         ││
   │  - Entity recognition       ││
   │  - Context scoring          ││
   └──────────────┬──────────────┘│
                  │                │
                  ▼                │
   ┌─────────────────────────────┐│
   │  False Positive Filter      ││
   │  - Confidence threshold     ││
   │  - Context validation       ││
   │  - Sentiment check          ││
   └──────────────┬──────────────┘│
                  │                │
4. STORAGE PHASE  │                │
                  ▼                │
   ┌─────────────────────────────┐│
   │  TGE Event Repository       ││
   │  - Save to PostgreSQL       ││
   │  - Cache in Redis           ││
   │  - Update metrics           ││
   └──────────────┬──────────────┘│
                  │                │
5. NOTIFICATION   │                │
                  ▼                │
   ┌─────────────────────────────┐│
   │  Notification Service       ││
   │  - WebSocket broadcast      ││
   │  - Email alerts             ││
   │  - Webhook triggers         ││
   └─────────────────────────────┘│
```

### 6.2 Agent Coordination Flow

```
┌────────────────────────────────────────────────────────┐
│              Agent Coordination Sequence                │
└────────────────────────────────────────────────────────┘

Queen Coordinator
    │
    │ 1. Assess system state
    ├──────────────────────────────────────────────────┐
    │                                                   │
    ▼                                                   ▼
Task Orchestrator                          Coordination Service
    │                                                   │
    │ 2. Schedule tasks                                │ 2. Sync state
    ├────────────────────────┐                         │
    │                        │                         │
    ▼                        ▼                         ▼
Priority Queue          Load Balancer            Shared Memory
    │                        │                         │
    │ 3. Queue by priority   │ 3. Select agent         │ 3. Update context
    │                        │                         │
    └────────────┬───────────┴─────────────────────────┘
                 │
                 ▼
         Message Queue (Redis)
                 │
                 │ 4. Distribute messages
    ┌────────────┼────────────┬────────────┐
    │            │            │            │
    ▼            ▼            ▼            ▼
Scraping     Keyword      API         Performance
Specialist   Specialist   Guardian    Optimizer
    │            │            │            │
    │ 5. Execute task          │            │
    │            │            │            │
    └────────────┼────────────┴────────────┘
                 │
                 ▼
         Message Queue (Redis)
                 │
                 │ 6. Report results
                 ▼
         Queen Coordinator
                 │
                 │ 7. Evaluate performance
                 │    Adjust priorities
                 │    Trigger optimizations
                 ▼
         [Repeat cycle]
```

---

## 7. API Specifications

### 7.1 REST API Endpoints

#### TGE Events
```yaml
GET /api/v1/tge-events
  description: List TGE events with filtering
  parameters:
    - company: string (optional)
    - token_symbol: string (optional)
    - from_date: datetime (optional)
    - to_date: datetime (optional)
    - min_confidence: float (optional)
    - limit: int (default: 50)
    - offset: int (default: 0)
  response: 200 OK
    body:
      events: TGEEvent[]
      total: int
      page: int

GET /api/v1/tge-events/{event_id}
  description: Get specific TGE event details
  response: 200 OK
    body: TGEEvent

POST /api/v1/tge-events/search
  description: Advanced search with complex filters
  body:
    filters: {
      keywords: string[]
      companies: string[]
      date_range: {from: datetime, to: datetime}
      confidence_min: float
    }
  response: 200 OK
    body:
      events: TGEEvent[]
      total: int
```

#### System Monitoring
```yaml
GET /api/v1/system/health
  description: System health check
  response: 200 OK
    body:
      status: "healthy" | "degraded" | "unhealthy"
      services: {
        scrapers: ServiceStatus
        database: ServiceStatus
        cache: ServiceStatus
        queue: ServiceStatus
      }

GET /api/v1/system/metrics
  description: System performance metrics
  response: 200 OK
    body:
      scraping:
        items_per_hour: int
        avg_latency_ms: float
        error_rate: float
      detection:
        events_detected: int
        precision: float
        false_positive_rate: float
      system:
        cpu_usage: float
        memory_usage: float
        active_connections: int
```

#### Agent Management
```yaml
GET /api/v1/agents
  description: List all agents and their status
  response: 200 OK
    body:
      agents: Agent[]

GET /api/v1/agents/{agent_id}
  description: Get agent details and metrics
  response: 200 OK
    body: Agent

POST /api/v1/agents/{agent_id}/action
  description: Control agent (start/stop/restart)
  body:
    action: "start" | "stop" | "restart"
  response: 200 OK
```

### 7.2 WebSocket API

```javascript
// Connection
ws://localhost:8080/ws

// Subscribe to events
{
  "type": "subscribe",
  "subscriptions": ["tge_detected", "metrics", "agent_status"]
}

// Server messages
{
  "type": "tge_detected",
  "data": {
    "event_id": "uuid",
    "company": "Example Corp",
    "token_symbol": "EXMP",
    "confidence": 0.95,
    "timestamp": "2025-10-13T12:00:00Z"
  }
}

{
  "type": "metrics",
  "data": {
    "timestamp": "2025-10-13T12:00:00Z",
    "scraping_rate": 120,
    "detection_rate": 5,
    "system_health": "healthy"
  }
}
```

---

## 8. Deployment Architecture

### 8.1 Docker Compose Deployment

```yaml
version: '3.8'

services:
  # Backend API
  backend:
    build: ./infrastructure/docker/Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/tge_swarm
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1'
          memory: 512M

  # Scraper Workers
  scraper-twitter:
    build: ./infrastructure/docker/Dockerfile.scraper
    environment:
      - SCRAPER_TYPE=twitter
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '0.5'
          memory: 256M

  scraper-news:
    build: ./infrastructure/docker/Dockerfile.scraper
    environment:
      - SCRAPER_TYPE=news
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '0.5'
          memory: 256M

  # Database
  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=tge_swarm
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass

  # Cache & Message Queue
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  # Dashboard
  dashboard:
    build: ./infrastructure/docker/Dockerfile.dashboard
    ports:
      - "3000:3000"
    depends_on:
      - backend

  # Monitoring
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./infrastructure/monitoring/prometheus:/etc/prometheus
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:
```

### 8.2 Kubernetes Deployment (Production)

```yaml
# Namespace
apiVersion: v1
kind: Namespace
metadata:
  name: tge-swarm

---
# Backend Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tge-backend
  namespace: tge-swarm
spec:
  replicas: 3
  selector:
    matchLabels:
      app: tge-backend
  template:
    metadata:
      labels:
        app: tge-backend
    spec:
      containers:
      - name: backend
        image: tge-swarm/backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
# Scraper Deployment (Twitter)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tge-scraper-twitter
  namespace: tge-swarm
spec:
  replicas: 2
  selector:
    matchLabels:
      app: tge-scraper-twitter
  template:
    metadata:
      labels:
        app: tge-scraper-twitter
    spec:
      containers:
      - name: scraper
        image: tge-swarm/scraper:latest
        env:
        - name: SCRAPER_TYPE
          value: "twitter"
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: tge-config
              key: redis_url
        resources:
          requests:
            memory: "128Mi"
            cpu: "125m"
          limits:
            memory: "256Mi"
            cpu: "250m"

---
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: tge-backend-hpa
  namespace: tge-swarm
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: tge-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## 9. Security Architecture

### 9.1 Authentication & Authorization

```python
# JWT-based authentication
class AuthenticationService:
    """
    Token-based authentication with role-based access control
    """

    def generate_token(self, user: User) -> str:
        """Generate JWT token with user claims"""
        payload = {
            "user_id": user.id,
            "roles": user.roles,
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    def verify_token(self, token: str) -> Dict:
        """Verify and decode JWT token"""
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

# Role-based access control
class RBACMiddleware:
    """
    Middleware for role-based authorization
    """

    roles = {
        "admin": ["*"],
        "operator": ["read:*", "write:events", "write:config"],
        "viewer": ["read:*"]
    }
```

### 9.2 Data Protection

```python
# Encryption at rest
class DataEncryption:
    """
    Encrypt sensitive data before storage
    """

    def encrypt(self, data: str) -> str:
        """AES-256 encryption"""
        cipher = AES.new(settings.ENCRYPTION_KEY, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(data.encode())
        return base64.b64encode(cipher.nonce + tag + ciphertext).decode()

# API key management
class APIKeyManager:
    """
    Secure API key storage and rotation
    """

    def store_key(self, service: str, key: str):
        """Store API key in encrypted vault"""
        encrypted = self.encrypt(key)
        self.vault.set(f"api_keys/{service}", encrypted)

    def rotate_key(self, service: str, new_key: str):
        """Rotate API key with zero downtime"""
        self.store_key(f"{service}_new", new_key)
        # Gradual transition...
        self.remove_key(service)
        self.store_key(service, new_key)
```

### 9.3 Input Validation

```python
# Request validation
class RequestValidator:
    """
    Validate and sanitize all input data
    """

    @staticmethod
    def validate_search_query(query: str) -> str:
        """Prevent SQL injection and XSS"""
        # Remove special characters
        sanitized = re.sub(r'[^\w\s-]', '', query)
        # Limit length
        return sanitized[:200]

    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format and domain"""
        parsed = urlparse(url)
        return (
            parsed.scheme in ['http', 'https'] and
            parsed.netloc and
            not any(malicious in url for malicious in BLOCKED_DOMAINS)
        )
```

---

## 10. Scalability & Performance

### 10.1 Horizontal Scaling Strategy

```yaml
scaling_rules:
  backend_api:
    min_instances: 2
    max_instances: 10
    scale_up_threshold:
      cpu: "> 70%"
      memory: "> 80%"
      request_rate: "> 1000 req/min"
      response_time: "> 500ms p95"
    scale_down_threshold:
      cpu: "< 30%"
      memory: "< 40%"
      request_rate: "< 200 req/min"
    cooldown_period: 300s

  scraper_workers:
    min_instances: 3
    max_instances: 20
    scale_up_threshold:
      queue_depth: "> 100"
      processing_lag: "> 5 minutes"
      error_rate: "> 5%"
    scale_down_threshold:
      queue_depth: "< 10"
      processing_lag: "< 30 seconds"
    cooldown_period: 180s
```

### 10.2 Caching Strategy

```python
class MultiLevelCache:
    """
    Three-tier caching for optimal performance
    """

    def __init__(self):
        # L1: In-memory cache (fastest, smallest)
        self.l1_cache = LRUCache(maxsize=1000)

        # L2: Redis cache (fast, medium size)
        self.l2_cache = RedisCache(ttl=3600)

        # L3: Database query cache (slower, largest)
        self.l3_cache = DatabaseQueryCache()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from multi-level cache"""
        # Check L1
        if key in self.l1_cache:
            return self.l1_cache[key]

        # Check L2
        value = await self.l2_cache.get(key)
        if value:
            self.l1_cache[key] = value
            return value

        # Check L3
        value = await self.l3_cache.get(key)
        if value:
            await self.l2_cache.set(key, value)
            self.l1_cache[key] = value
            return value

        return None
```

### 10.3 Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Response Time | < 100ms p50, < 500ms p95 | Prometheus |
| Scraping Latency | < 2s per source | Application logs |
| Detection Latency | < 100ms per document | Application logs |
| Throughput | > 1000 documents/min | Prometheus |
| Error Rate | < 0.1% | Prometheus |
| Uptime | > 99.5% | Prometheus |
| Memory per Service | < 512MB | Kubernetes metrics |
| CPU per Service | < 0.5 cores | Kubernetes metrics |

---

## 11. Monitoring & Observability

### 11.1 Metrics Collection

```python
# Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge

# Scraping metrics
scraping_requests_total = Counter(
    'scraping_requests_total',
    'Total scraping requests',
    ['source', 'status']
)

scraping_latency_seconds = Histogram(
    'scraping_latency_seconds',
    'Scraping request latency',
    ['source']
)

# Detection metrics
tge_events_detected_total = Counter(
    'tge_events_detected_total',
    'Total TGE events detected',
    ['confidence_level']
)

keyword_matches_total = Counter(
    'keyword_matches_total',
    'Total keyword matches',
    ['pattern_type']
)

false_positive_rate = Gauge(
    'false_positive_rate',
    'Current false positive rate'
)

# System metrics
active_connections = Gauge(
    'active_connections',
    'Current active connections',
    ['service']
)

queue_depth = Gauge(
    'message_queue_depth',
    'Current message queue depth',
    ['queue_name']
)
```

### 11.2 Logging Strategy

```python
# Structured logging
import structlog

logger = structlog.get_logger()

# Application logging
logger.info(
    "tge_detected",
    event_id=event.id,
    company=event.company,
    confidence=event.confidence,
    source=event.source,
    timestamp=event.timestamp
)

logger.error(
    "scraping_failed",
    source=source,
    error=str(e),
    retry_count=retry_count,
    timestamp=datetime.utcnow()
)

# Performance logging
logger.debug(
    "performance_metric",
    operation="keyword_matching",
    duration_ms=duration,
    items_processed=count,
    memory_mb=memory_usage
)
```

### 11.3 Alert Rules

```yaml
# Prometheus alert rules
groups:
  - name: tge_swarm_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(scraping_requests_total{status="error"}[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} for {{ $labels.source }}"

      - alert: ScraperDown
        expr: up{job="scraper"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Scraper instance down"
          description: "{{ $labels.instance }} has been down for 2 minutes"

      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "{{ $labels.pod }} is using {{ $value }}% memory"

      - alert: QueueBacklog
        expr: message_queue_depth > 1000
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Message queue backlog"
          description: "Queue {{ $labels.queue_name }} has {{ $value }} messages"
```

---

## 12. Disaster Recovery & Business Continuity

### 12.1 Backup Strategy

```yaml
backup_schedule:
  database:
    full_backup:
      frequency: daily
      time: "02:00 UTC"
      retention: "30 days"
    incremental_backup:
      frequency: hourly
      retention: "7 days"
    point_in_time_recovery: enabled

  redis:
    snapshot:
      frequency: "every 6 hours"
      retention: "7 days"
    append_only_file: enabled

  configuration:
    git_backup: continuous
    s3_backup:
      frequency: hourly
      retention: "90 days"
```

### 12.2 Failover Procedures

```python
class FailoverManager:
    """
    Automatic failover for critical services
    """

    async def monitor_health(self):
        """Monitor service health and trigger failover"""
        while True:
            for service in self.services:
                health = await self.check_health(service)

                if not health.is_healthy:
                    logger.warning(f"Service {service.name} unhealthy")

                    if health.consecutive_failures >= 3:
                        await self.initiate_failover(service)

            await asyncio.sleep(10)

    async def initiate_failover(self, service: Service):
        """Failover to backup instance"""
        logger.critical(f"Initiating failover for {service.name}")

        # 1. Stop unhealthy instance
        await service.stop()

        # 2. Promote backup
        backup = await self.get_backup_instance(service)
        await backup.promote_to_primary()

        # 3. Update service discovery
        await self.update_service_registry(service, backup)

        # 4. Verify new primary
        health = await self.check_health(backup)
        if not health.is_healthy:
            logger.critical(f"Failover failed for {service.name}")
            await self.alert_ops_team(service)
```

---

## 13. Next Steps

### 13.1 Implementation Phases

**Phase 1: Core Infrastructure (Week 1-2)**
- Set up database schema and migrations
- Implement message queue infrastructure
- Create base scraper framework
- Develop keyword matching engine core

**Phase 2: Scraping Components (Week 3-4)**
- Implement Twitter monitor
- Build news scrapers
- Add rate limiting and retry logic
- Implement caching layer

**Phase 3: Detection & Processing (Week 5-6)**
- Complete keyword matching engine
- Build false positive filter
- Implement deduplication service
- Add notification system

**Phase 4: Agent Coordination (Week 7-8)**
- Integrate Queen coordinator
- Implement task orchestration
- Add optimization engine
- Build agent management

**Phase 5: Monitoring & Operations (Week 9-10)**
- Set up Prometheus metrics
- Configure Grafana dashboards
- Implement alerting rules
- Create operational runbooks

**Phase 6: Testing & Optimization (Week 11-12)**
- Comprehensive unit tests
- Integration test suite
- Performance testing and tuning
- Security audit

### 13.2 Success Criteria

- **Performance**: Scraping cycle < 60s, API response < 100ms p50
- **Accuracy**: TGE detection precision > 95%, false positive rate < 5%
- **Reliability**: Uptime > 99.5%, error rate < 0.1%
- **Scalability**: Handle 10,000+ documents/hour
- **Efficiency**: API calls reduced by 30% vs baseline

### 13.3 Risk Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| API rate limits | High | Medium | Intelligent caching, request batching |
| False positives | Medium | High | Context scoring, confidence thresholds |
| Data quality issues | Medium | Medium | Validation layer, sanitization |
| Performance degradation | High | Low | Connection pooling, caching, monitoring |
| Service downtime | High | Low | Circuit breakers, failover, redundancy |

---

## 14. Architecture Decision Records (ADRs)

### ADR-001: Microservices Architecture
**Status:** Accepted
**Decision:** Use microservices architecture with specialized agents
**Rationale:** Enables independent scaling, fault isolation, and specialized optimization
**Consequences:** Increased complexity but better scalability and maintainability

### ADR-002: Redis for Message Queue
**Status:** Accepted
**Decision:** Use Redis Pub/Sub for message queue
**Rationale:** Low latency, high throughput, simple deployment
**Consequences:** In-memory storage requires careful memory management

### ADR-003: PostgreSQL for Persistence
**Status:** Accepted
**Decision:** Use PostgreSQL for primary data store
**Rationale:** ACID compliance, JSON support, strong ecosystem
**Consequences:** Need to implement proper indexing and partitioning for scale

### ADR-004: Event-Driven Architecture
**Status:** Accepted
**Decision:** Use event-driven architecture for agent coordination
**Rationale:** Loose coupling, scalability, real-time capabilities
**Consequences:** Need robust error handling and event replay mechanisms

### ADR-005: Multi-Level Caching
**Status:** Accepted
**Decision:** Implement three-tier caching (memory, Redis, DB)
**Rationale:** Optimize for different access patterns and data sizes
**Consequences:** Cache invalidation complexity, memory management

---

## Appendix

### A. Glossary

- **TGE**: Token Generation Event - cryptocurrency token launch announcement
- **Queen Coordinator**: Hierarchical supervisor agent managing all workers
- **Circuit Breaker**: Resilience pattern preventing cascading failures
- **SAFLA**: System-Adaptive Focused Learning Architecture
- **Backpressure**: Flow control mechanism to prevent system overload
- **Bulkhead**: Isolation pattern separating system resources

### B. References

- SPARC Methodology: https://github.com/ruvnet/sparc
- Claude Flow: https://github.com/ruvnet/claude-flow
- Redis Documentation: https://redis.io/docs
- PostgreSQL Best Practices: https://www.postgresql.org/docs
- Microservices Patterns: https://microservices.io/patterns

### C. Contact & Support

- Architecture Team: architecture@example.com
- Operations Team: ops@example.com
- Security Team: security@example.com

---

**Document Status:** Draft
**Review Date:** 2025-10-20
**Next Review:** 2025-11-13
**Approval Required:** Yes

**Author:** System Architect Agent
**Contributors:** Research Agent, Claude Flow Swarm
**Reviewers:** [To be assigned]

---

*This architecture document is a living document and will be updated as the system evolves.*
