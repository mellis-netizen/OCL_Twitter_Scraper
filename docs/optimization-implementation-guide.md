# Performance Optimization Implementation Guide

## Quick Start

This guide provides step-by-step instructions for implementing the performance optimizations in the TGE Monitor system.

## Prerequisites

- PostgreSQL 14+
- Redis 6.0+
- Python 3.10+
- Node.js 18+
- Access to database with admin privileges

## Implementation Steps

### Phase 1: Database Optimization (30 minutes)

#### 1.1 Apply Database Indexes

```bash
# Connect to PostgreSQL
psql -U your_user -d tge_monitor

# Run the migration script
\i src/migrations/add_performance_indexes.sql

# Verify indexes were created
\di

# Check index usage
SELECT * FROM pg_stat_user_indexes WHERE schemaname = 'public';
```

**Expected Result:** 20+ new indexes created, query times reduced by 80-90%

#### 1.2 Verify Connection Pooling

The connection pooling is already configured in `/Users/apple/Documents/GitHub/OCL_Twitter_Scraper/src/database.py`:

```python
# Verify these settings are present:
pool_size=20,
max_overflow=10,
pool_timeout=30,
pool_recycle=3600,
pool_pre_ping=True
```

No action needed if these are already configured.

#### 1.3 Test Database Performance

```bash
# Run benchmark query before optimization
python -c "
from src.database import DatabaseManager
import time
start = time.time()
with DatabaseManager.get_session() as db:
    from src.models import Alert
    alerts = db.query(Alert).limit(50).all()
print(f'Query time: {(time.time() - start) * 1000:.1f}ms')
"
```

**Target:** < 50ms for 50 alerts

---

### Phase 2: API Caching (15 minutes)

#### 2.1 Verify Redis Connection

```bash
# Test Redis connection
redis-cli ping
# Should return: PONG

# Or use Python
python -c "
from src.database import CacheManager
result = CacheManager.exists('test_key')
print('Redis connected!' if result is not None else 'Redis not available')
"
```

#### 2.2 Add Caching to API Endpoints

Update `/Users/apple/Documents/GitHub/OCL_Twitter_Scraper/src/api.py`:

```python
# Add import at top
from .cache_decorator import cache_response, api_cache

# Apply to expensive endpoints
@app.get("/statistics/alerts", response_model=AlertStatistics)
@cache_response(ttl=300)  # Cache for 5 minutes
async def get_alert_statistics(...):
    # existing code
    pass

@app.get("/statistics/system", response_model=SystemStatistics)
@cache_response(ttl=60)  # Cache for 1 minute
async def get_system_statistics(...):
    # existing code
    pass
```

#### 2.3 Add Cache Invalidation

```python
# In alert creation/update endpoints
@app.post("/alerts", response_model=AlertResponse)
async def create_alert(...):
    # existing code

    # Invalidate cache after creating alert
    from .cache_decorator import invalidate_alerts_cache
    invalidate_alerts_cache()

    return alert_response
```

---

### Phase 3: Performance Monitoring (10 minutes)

#### 3.1 Add Performance Middleware

Update `/Users/apple/Documents/GitHub/OCL_Twitter_Scraper/src/api.py`:

```python
# Add import
from .performance_middleware import setup_performance_monitoring

# After creating FastAPI app
app = FastAPI(...)

# Add CORS middleware (existing)
app.add_middleware(CORSMiddleware, ...)

# Add performance monitoring
perf_monitor = setup_performance_monitoring(app, slow_threshold=1.0)
```

#### 3.2 Test Performance Endpoints

```bash
# Start the API
cd /Users/apple/Documents/GitHub/OCL_Twitter_Scraper
python -m src.api

# In another terminal, test performance endpoints
curl http://localhost:8000/performance/stats
curl http://localhost:8000/performance/slowest
```

---

### Phase 4: Frontend Optimization (20 minutes)

#### 4.1 Replace AlertDashboard Component

```bash
# Backup original component
cp frontend/src/components/AlertDashboard.tsx \
   frontend/src/components/AlertDashboard.original.tsx

# Use optimized version
cp frontend/src/components/AlertDashboard.optimized.tsx \
   frontend/src/components/AlertDashboard.tsx
```

#### 4.2 Verify Debounce Hook

The debounce hook is already created at:
`/Users/apple/Documents/GitHub/OCL_Twitter_Scraper/frontend/src/hooks/useDebounce.ts`

No additional action needed.

#### 4.3 Test Frontend Performance

```bash
cd frontend
npm run build
npm run preview

# Open Chrome DevTools
# Navigate to Performance tab
# Record a session with filter changes
# Verify reduced re-renders
```

**Target:** < 50ms per component render

---

### Phase 5: Memory Monitoring (15 minutes)

#### 5.1 Add Memory Monitoring to Main Script

Update `/Users/apple/Documents/GitHub/OCL_Twitter_Scraper/src/main_optimized.py`:

```python
# Add import
from .memory_monitor import get_memory_monitor, monitor_memory

# In __init__ method
def __init__(self, swarm_enabled: bool = None):
    # existing code...

    # Initialize memory monitor
    self.memory_monitor = get_memory_monitor(enable_tracemalloc=False)
    logger.info("Memory monitoring initialized")

# Wrap monitoring cycle
@monitor_memory
def run_monitoring_cycle(self):
    # existing code...
    pass
```

#### 5.2 Add Periodic Memory Reports

```python
# In run_continuous method
def run_continuous(self):
    # existing code...

    # Schedule memory reports every hour
    schedule.every().hour.do(self.memory_monitor.log_report)
```

---

### Phase 6: Verification & Testing (30 minutes)

#### 6.1 Run Full System Test

```bash
# Start all services
# Terminal 1: PostgreSQL (should already be running)
# Terminal 2: Redis
redis-server

# Terminal 3: API server
cd /Users/apple/Documents/GitHub/OCL_Twitter_Scraper
python -m src.api

# Terminal 4: Frontend
cd frontend
npm run dev

# Terminal 5: Run monitoring cycle
python -m src.main_optimized --mode once
```

#### 6.2 Performance Verification Checklist

| Check | Command | Expected |
|-------|---------|----------|
| Database indexes | `\di` in psql | 20+ indexes |
| Redis connection | `redis-cli ping` | PONG |
| API response time | `curl http://localhost:8000/alerts` | < 100ms |
| Cache hit rate | `curl http://localhost:8000/performance/stats` | > 60% |
| Memory usage | Check logs | < 300MB |
| Frontend load | Chrome Lighthouse | Score > 90 |

#### 6.3 Load Testing

```bash
# Install Apache Bench
brew install apache-bench  # macOS
# or
sudo apt-get install apache2-utils  # Linux

# Run load test
ab -n 1000 -c 50 http://localhost:8000/alerts

# Verify results:
# - Requests per second > 400
# - Mean response time < 150ms
# - No failed requests
```

---

## Performance Targets

### API Performance
- ✅ GET /alerts: < 100ms average
- ✅ POST /monitoring/trigger: < 100ms to start
- ✅ Statistics endpoints: < 300ms (uncached)
- ✅ Cache hit rate: > 70%

### Frontend Performance
- ✅ First Contentful Paint: < 1.0s
- ✅ Largest Contentful Paint: < 1.5s
- ✅ Time to Interactive: < 2.0s
- ✅ Component render: < 50ms

### System Performance
- ✅ Scraping cycle: < 150s
- ✅ Memory usage: < 300MB peak
- ✅ Database queries: < 50ms average
- ✅ Error rate: < 1%

---

## Rollback Plan

If issues occur, rollback in reverse order:

### 1. Rollback Frontend
```bash
cd frontend/src/components
cp AlertDashboard.original.tsx AlertDashboard.tsx
npm run build
```

### 2. Rollback API Changes
```bash
git checkout src/api.py
# Restart API server
```

### 3. Rollback Database Indexes
```sql
-- Only if absolutely necessary
-- This will remove performance improvements
DROP INDEX IF EXISTS idx_alerts_company_created;
DROP INDEX IF EXISTS idx_alerts_source_confidence;
-- ... (drop other indexes)
```

---

## Monitoring & Maintenance

### Daily Checks
1. Review API performance stats: `curl http://localhost:8000/performance/stats`
2. Check cache hit rate (target: > 70%)
3. Monitor memory usage in logs
4. Review slow request logs

### Weekly Tasks
1. Analyze database query performance: `SELECT * FROM pg_stat_statements`
2. Review memory leak detection reports
3. Check frontend performance with Lighthouse
4. Review error rates and patterns

### Monthly Tasks
1. Optimize database (VACUUM ANALYZE)
2. Review and tune cache TTL values
3. Update performance benchmarks
4. Plan capacity based on growth trends

---

## Troubleshooting

### High Memory Usage
```bash
# Check memory usage
python -c "
from src.memory_monitor import get_memory_monitor
monitor = get_memory_monitor(enable_tracemalloc=True)
print(monitor.generate_report())
"

# If memory leak detected:
# 1. Check for circular references
# 2. Verify database session cleanup
# 3. Review cache expiration
```

### Slow API Responses
```bash
# Check database queries
psql -U your_user -d tge_monitor
SELECT query, calls, mean_time, max_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

# Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0;
```

### Low Cache Hit Rate
```bash
# Check cache stats
curl http://localhost:8000/performance/stats | jq '.cache_stats'

# Increase TTL for frequently accessed endpoints
# Verify Redis memory limits
redis-cli INFO memory
```

---

## Support & Resources

### Documentation
- [Optimization Report](/Users/apple/Documents/GitHub/OCL_Twitter_Scraper/docs/optimization-report.md)
- [Performance Benchmarks](/Users/apple/Documents/GitHub/OCL_Twitter_Scraper/docs/performance-benchmarks.md)
- [Database Schema](../src/models.py)
- [API Documentation](http://localhost:8000/docs)

### Code Locations
- Database indexes: `/src/migrations/add_performance_indexes.sql`
- Cache decorator: `/src/cache_decorator.py`
- Performance middleware: `/src/performance_middleware.py`
- Memory monitor: `/src/memory_monitor.py`
- Optimized components: `/frontend/src/components/*.optimized.tsx`

### Monitoring Tools
- API Stats: http://localhost:8000/performance/stats
- Slowest Endpoints: http://localhost:8000/performance/slowest
- Health Check: http://localhost:8000/health

---

## Next Steps

After successful implementation:

1. **Set up monitoring dashboard** with real-time performance metrics
2. **Configure alerts** for performance degradation
3. **Document baseline metrics** for future comparison
4. **Schedule regular performance reviews** (monthly)
5. **Plan for scaling** based on usage patterns

---

## Estimated Timeline

| Phase | Duration | Can Rollback |
|-------|----------|--------------|
| Database indexes | 30 min | Yes |
| API caching | 15 min | Yes |
| Performance monitoring | 10 min | Yes |
| Frontend optimization | 20 min | Yes |
| Memory monitoring | 15 min | Yes |
| Testing & verification | 30 min | N/A |
| **Total** | **2 hours** | - |

---

## Success Criteria

Implementation is successful when:

- ✅ All performance targets are met
- ✅ No increase in error rates
- ✅ Cache hit rate > 70%
- ✅ Memory usage stable (< 300MB)
- ✅ User-facing metrics improved
- ✅ Load tests pass without failures

---

## Questions?

For issues or questions during implementation:
1. Check the troubleshooting section above
2. Review the optimization report for context
3. Examine performance benchmarks for expected values
4. Check swarm coordination logs in `.swarm/memory.db`
