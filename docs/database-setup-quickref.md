# Database Setup Quick Reference

**For Hive Mind Coordination**
**Railway PostgreSQL Configuration**

---

## Production Database Connection

**Railway Service:** ocltwitterscraper-production.up.railway.app
**Database Type:** PostgreSQL
**Connection Pool:** 20 base + 10 overflow = 30 max concurrent

### Environment Variable

```bash
DATABASE_URL=postgresql://user:password@host.railway.internal:5432/railway
```

**Location in code:**
- `/Users/apple/Documents/GitHub/OCL_Twitter_Scraper/src/database.py` (Line 19-22)

---

## Database Tables Schema

### 1. monitoring_sessions
**Purpose:** Track real-time scraping cycle progress

```sql
CREATE TABLE monitoring_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(50) UNIQUE NOT NULL,
    status VARCHAR(20),  -- 'running', 'completed', 'failed'
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,

    -- Real-time counters (updated during scraping)
    articles_processed INTEGER DEFAULT 0,
    tweets_processed INTEGER DEFAULT 0,
    feeds_processed INTEGER DEFAULT 0,
    alerts_generated INTEGER DEFAULT 0,
    errors_encountered INTEGER DEFAULT 0,

    -- Phase tracking
    performance_metrics JSON,  -- {"phase": "scraping_news", ...}
    error_log JSON
);
```

**Key Usage:**
- Frontend polls `GET /monitoring/session/{session_id}/progress`
- Backend updates this table after each scraping phase
- `performance_metrics['phase']` indicates current progress step

---

### 2. feeds
**Purpose:** RSS/News feed configuration and statistics

```sql
CREATE TABLE feeds (
    id SERIAL PRIMARY KEY,
    url VARCHAR(500) UNIQUE NOT NULL,
    title VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,

    -- Statistics (updated after each cycle)
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    tge_alerts_found INTEGER DEFAULT 0,

    -- Timestamps
    last_fetch TIMESTAMP WITH TIME ZONE,
    last_success TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Key Usage:**
- Loaded by `OptimizedNewsScraper` at initialization
- Updated by `update_feed_statistics()` after each cycle
- Dashboard displays feed health metrics

---

### 3. alerts
**Purpose:** Detected TGE alerts from news and Twitter

```sql
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500),
    content TEXT,
    source VARCHAR(50),  -- 'news' or 'twitter'
    source_url VARCHAR(1000),
    confidence REAL,  -- 0.0 to 1.0
    urgency_level VARCHAR(20),  -- 'critical', 'high', 'medium', 'low'
    status VARCHAR(20) DEFAULT 'active',

    -- Foreign keys
    company_id INTEGER REFERENCES companies(id),

    -- Analysis data
    keywords_matched JSON,
    tokens_mentioned JSON,
    analysis_data JSON,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Key Usage:**
- Created by `save_alerts_to_database()` during scraping cycle
- Queried by `GET /alerts` with filtering
- Displayed in dashboard alert list

---

### 4. companies
**Purpose:** Tracked crypto companies and their tokens

```sql
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) UNIQUE NOT NULL,
    tokens JSON,  -- ["CAL", "FHE"]
    priority VARCHAR(20),  -- 'HIGH', 'MEDIUM', 'LOW'
    status VARCHAR(50),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Key Usage:**
- Referenced by alerts (company_id foreign key)
- Queried by `GET /companies`
- Priority affects confidence threshold in matching

---

## Connection Management

### SQLAlchemy Engine Configuration

```python
# Production PostgreSQL settings
engine = create_engine(
    DATABASE_URL,
    pool_size=20,              # Base pool
    max_overflow=10,           # Extra under load
    pool_timeout=30,           # Wait time (seconds)
    pool_recycle=3600,         # Recycle after 1 hour
    pool_pre_ping=True,        # Health check before use
    pool_reset_on_return='rollback',
    echo=False                 # Set True for SQL debugging
)
```

### Session Factory

```python
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency injection for FastAPI
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Context manager for direct use
@contextmanager
def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## Initialization Sequence

### 1. Database Tables Creation
```python
# Runs automatically on FastAPI startup (api.py Line 120)
from src.database import init_db
init_db()  # Creates all tables if not exist
```

### 2. Seed Initial Data
```bash
# One-time setup: populate companies and feeds
curl -X POST https://ocltwitterscraper-production.up.railway.app/seed-data
```

**What it seeds:**
- Companies from `config.py` COMPANIES list
- Feeds from `config.py` NEWS_SOURCES list
- Default admin user

### 3. Verify Setup
```bash
# Check database health
curl https://ocltwitterscraper-production.up.railway.app/health

# Expected response:
{
  "status": "healthy",
  "database": true,
  "redis": true,
  "feeds_health": {
    "total": 15,
    "active": 15,
    "inactive": 0
  }
}
```

---

## Critical Patterns for Other Agents

### Pattern 1: Real-Time Updates During Scraping

```python
# In main_optimized.py (Scraping cycle)
def _update_progress(self, status: str, details: Dict = None):
    if self.session_id and self.db_session:
        session = self.db_session.query(MonitoringSession).filter(
            MonitoringSession.session_id == self.session_id
        ).first()

        if session:
            session.articles_processed = self.current_cycle_stats['articles_processed']
            session.performance_metrics['phase'] = details['phase']
            self.db_session.commit()  # CRITICAL: Writes immediately
```

**Why This Matters:**
- Frontend polls every 2 seconds for progress
- Must commit after each phase update
- Uses separate DB session in background thread

### Pattern 2: Querying with Filters

```python
# Get recent alerts with confidence > 70%
with DatabaseManager.get_session() as db:
    alerts = db.query(Alert).filter(
        Alert.confidence >= 0.7,
        Alert.created_at >= datetime.now(timezone.utc) - timedelta(hours=24)
    ).order_by(Alert.created_at.desc()).all()
```

### Pattern 3: Batch Updates

```python
# Update multiple feeds efficiently
with DatabaseManager.get_session() as db:
    for feed_url, stats in feed_stats.items():
        db_feed = db.query(Feed).filter(Feed.url == feed_url).first()
        if db_feed:
            db_feed.success_count = stats['success_count']
            db_feed.last_fetch = datetime.now(timezone.utc)

    db.commit()  # Single commit for all updates
```

---

## Troubleshooting Commands

### Test Database Connection
```bash
python -c "
from src.database import DatabaseManager
print('Healthy' if DatabaseManager.check_connection() else 'Failed')
"
```

### Check Environment Variable
```bash
echo $DATABASE_URL
# Should output: postgresql://...railway...
```

### View Recent Sessions
```bash
curl https://ocltwitterscraper-production.up.railway.app/monitoring/sessions/recent?limit=5
```

### Manual Database Query (Railway CLI)
```bash
railway link  # Link to project
railway postgres  # Open psql shell

# Inside psql:
SELECT session_id, status, articles_processed, created_at
FROM monitoring_sessions
ORDER BY created_at DESC
LIMIT 10;
```

---

## Performance Notes

### Connection Pool Sizing
- **20 base connections:** Handles 20 concurrent API requests
- **30 max (20+10 overflow):** Burst capacity for high load
- **1-hour recycle:** Prevents stale connections

### Query Optimization
- Indexes on: `session_id` (monitoring_sessions), `url` (feeds), `company_id` (alerts)
- Use `filter()` instead of `all()` then Python filtering
- Batch commits when updating multiple records

### Memory Considerations
- Background thread maintains dedicated session
- Sessions auto-close in `finally` blocks
- Old monitoring sessions should be cleaned up periodically (not implemented yet)

---

## Redis Cache (Optional)

**Connection:** `redis://host.railway.app:6379/0`

**Used For:**
- Rate limiting (login attempts, API calls)
- Health check temporary storage
- Future: WebSocket session management

**Not Required:** System works without Redis, just disables caching

---

## Summary for Agent Coordination

**What Coder Agent Needs:**
- Database models in `/src/models.py`
- Session factory: `DatabaseManager.get_session()`
- Always commit after updates in scraping cycle

**What Tester Agent Needs:**
- Mock database with in-memory SQLite for tests
- Seed test data: companies, feeds, sample alerts
- Test session lifecycle: create → update → complete

**What Reviewer Agent Needs:**
- Verify all queries use ORM (no raw SQL)
- Check session cleanup in exception handlers
- Review connection pool settings for production load

**Stored in Memory:**
- Key: `hive/research/database_setup`
- Location: `/Users/apple/Documents/GitHub/OCL_Twitter_Scraper/docs/database-setup-quickref.md`
