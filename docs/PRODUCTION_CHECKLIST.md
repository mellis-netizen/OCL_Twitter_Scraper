# Production Deployment Checklist

## Pre-Deployment Overview

This checklist ensures all critical components are properly configured, secured, and tested before deploying the OCL Twitter Scraper to production.

**Deployment Targets:**
- Backend: Railway
- Frontend: AWS Amplify
- Database: PostgreSQL (Railway)
- Cache: Redis (Railway)

---

## 1. Environment Configuration

### Backend Environment Variables

#### Required Configuration
- [ ] `DATABASE_URL` - PostgreSQL connection string (Railway auto-generated)
- [ ] `REDIS_URL` - Redis connection string (Railway auto-generated)
- [ ] `SECRET_KEY` - Strong random secret (min 32 characters)
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- [ ] `FRONTEND_URL` - Production frontend URL (e.g., https://app.yourdomain.com)
- [ ] `BACKEND_URL` - Production backend URL (e.g., https://api.yourdomain.com)

#### Security Configuration
- [ ] `ADMIN_USERNAME` - Admin username (DO NOT use 'admin')
- [ ] `ADMIN_PASSWORD` - Strong admin password (min 16 characters, mixed case, numbers, symbols)
- [ ] `CORS_ORIGINS` - Exact frontend URL(s), comma-separated
  ```
  Example: https://app.yourdomain.com,https://www.yourdomain.com
  ```
- [ ] `USE_SQLITE` - Set to `false` (or remove entirely)

#### Email Configuration (Required for notifications)
- [ ] `SMTP_HOST` - SMTP server hostname
- [ ] `SMTP_PORT` - SMTP port (typically 587 for TLS)
- [ ] `SMTP_USER` - SMTP username
- [ ] `SMTP_PASSWORD` - SMTP password
- [ ] `SMTP_FROM` - From email address

#### Optional Configuration
- [ ] `MAX_WORKERS` - Number of worker threads (default: 4)
- [ ] `LOG_LEVEL` - Logging level (default: INFO)
- [ ] `RATE_LIMIT` - API rate limit (default: 100/minute)

### Frontend Environment Variables

- [ ] `VITE_API_URL` - Backend API URL (e.g., https://api.yourdomain.com)
- [ ] `VITE_WS_URL` - WebSocket URL (e.g., wss://api.yourdomain.com)

### Verification Commands

```bash
# Backend - Verify all required variables are set
cd /Users/apple/Documents/GitHub/OCL_Twitter_Scraper
python3 << EOF
import os
required = ['DATABASE_URL', 'REDIS_URL', 'SECRET_KEY', 'FRONTEND_URL', 'ADMIN_PASSWORD']
missing = [v for v in required if not os.getenv(v)]
if missing:
    print(f"❌ Missing: {', '.join(missing)}")
else:
    print("✅ All required variables set")
EOF

# Frontend - Verify build-time variables
cd frontend
grep -E "VITE_API_URL|VITE_WS_URL" .env.production || echo "❌ Missing frontend env vars"
```

---

## 2. Security Hardening

### CORS Configuration
- [ ] Verify CORS origins match exact frontend URLs (no wildcards in production)
  ```bash
  # Check backend CORS configuration
  grep -A 5 "CORS" src/api.py
  ```
- [ ] Test CORS with production URLs
  ```bash
  curl -H "Origin: https://app.yourdomain.com" \
       -H "Access-Control-Request-Method: POST" \
       -X OPTIONS https://api.yourdomain.com/health
  ```

### Authentication & Authorization
- [ ] Admin password is strong and unique (NOT auto-generated)
- [ ] Verify admin account creation on startup
  ```bash
  # Check logs for admin creation
  railway logs | grep "Admin user"
  ```
- [ ] Test login with admin credentials
- [ ] Verify JWT token expiration (default: 1 hour)
- [ ] Confirm password hashing is enabled (bcrypt)

### Database Security
- [ ] SQLite is disabled (`USE_SQLITE=false` or not set)
- [ ] PostgreSQL password is strong
- [ ] Database backups are enabled on Railway
- [ ] Verify SSL connection to database
  ```bash
  # Check database connection uses SSL
  psql "$DATABASE_URL" -c "SHOW ssl;"
  ```

### API Security
- [ ] Rate limiting is configured and tested
  ```bash
  # Test rate limiting
  for i in {1..105}; do curl -s https://api.yourdomain.com/health; done | grep -c "429"
  ```
- [ ] All endpoints require authentication (except /health, /auth/login)
- [ ] Input validation is enabled on all endpoints
- [ ] SQL injection prevention verified (parameterized queries)

### Security Headers
- [ ] HTTPS is enforced (HTTP redirects to HTTPS)
- [ ] Security headers are set:
  ```bash
  curl -I https://api.yourdomain.com/health | grep -E "Strict-Transport|X-Content-Type|X-Frame"
  ```
  - `Strict-Transport-Security`
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Content-Security-Policy`

### Secrets Management
- [ ] No secrets in source code
- [ ] No secrets in git history
  ```bash
  git log --all --full-history -- "**/.*env*" | grep -v "not found"
  ```
- [ ] Environment variables stored in Railway/Amplify (not in .env files)
- [ ] API keys rotated from defaults

---

## 3. Database Preparation

### Schema & Migrations
- [ ] All migrations are applied
  ```bash
  # Check migration status
  python -c "from src.database import init_db; init_db()"
  ```
- [ ] Database schema matches models
- [ ] Foreign key constraints are enabled
- [ ] Check constraints are validated

### Indexes & Performance
- [ ] Indexes created on frequently queried columns
  ```sql
  -- Verify indexes exist
  SELECT tablename, indexname FROM pg_indexes
  WHERE schemaname = 'public'
  ORDER BY tablename, indexname;
  ```
- [ ] Query plans analyzed for slow queries
- [ ] Database statistics are up to date
  ```sql
  ANALYZE;
  ```

### Data Integrity
- [ ] Audit logging tables exist (user_audit_log, scraping_audit_log)
- [ ] Triggers are active for audit logging
  ```sql
  SELECT trigger_name, event_manipulation, event_object_table
  FROM information_schema.triggers;
  ```
- [ ] Test data is removed from production database
- [ ] Data validation rules are enforced

### Backup Strategy
- [ ] Automated backups enabled on Railway (daily recommended)
- [ ] Backup retention policy configured (30 days minimum)
- [ ] Test backup restoration process
  ```bash
  # Create test backup
  pg_dump "$DATABASE_URL" > backup_test.sql
  # Verify backup can be read
  head -n 50 backup_test.sql
  ```
- [ ] Document backup/restore procedures

---

## 4. Performance Optimization

### Database Optimization
- [ ] Connection pooling configured (recommended: 10-20 connections)
  ```python
  # Check pool size in src/database.py
  grep "pool_size" src/database.py
  ```
- [ ] Query result caching enabled via Redis
- [ ] Slow query logging enabled
- [ ] Database vacuum scheduled (PostgreSQL maintenance)

### Redis Caching
- [ ] Redis connection verified
  ```bash
  redis-cli -u "$REDIS_URL" ping
  ```
- [ ] Cache hit rate monitoring enabled
- [ ] TTL configured for cached data (recommended: 5-15 minutes)
- [ ] Cache invalidation strategy implemented

### API Performance
- [ ] Response times under 200ms for cached queries
  ```bash
  # Test API response time
  time curl -H "Authorization: Bearer $TOKEN" https://api.yourdomain.com/jobs
  ```
- [ ] Pagination implemented for large result sets
- [ ] Bulk operations optimized (batch inserts)
- [ ] Async operations used for I/O-bound tasks

### Frontend Optimization
- [ ] Production build created with optimizations
  ```bash
  cd frontend
  npm run build
  # Check bundle size
  ls -lh dist/assets/*.js
  ```
- [ ] Code splitting enabled
- [ ] Assets minified and compressed
- [ ] Static assets cached (CDN or browser cache)
- [ ] Lazy loading implemented for routes

### CDN Configuration (Optional)
- [ ] Static assets served via CDN
- [ ] Cache headers configured
  ```
  Cache-Control: public, max-age=31536000, immutable
  ```
- [ ] CDN purge strategy documented

---

## 5. Monitoring & Logging

### Health Checks
- [ ] Backend health endpoint responding
  ```bash
  curl https://api.yourdomain.com/health
  # Expected: {"status":"healthy","database":"connected","redis":"connected"}
  ```
- [ ] Frontend loads successfully
- [ ] WebSocket connections established
- [ ] Database connectivity verified
- [ ] Redis connectivity verified

### Application Metrics
- [ ] Metrics endpoint configured
  ```bash
  curl -H "Authorization: Bearer $TOKEN" https://api.yourdomain.com/metrics
  ```
- [ ] Key metrics tracked:
  - Request count and rate
  - Response times (p50, p95, p99)
  - Error rates
  - Active scraping jobs
  - Database query times
  - Redis cache hit/miss ratio

### Logging Infrastructure
- [ ] Structured logging enabled (JSON format)
- [ ] Log levels configured appropriately (INFO in production)
- [ ] Sensitive data filtered from logs (passwords, tokens)
- [ ] Log aggregation configured (Railway logs retained)
- [ ] Log search and filtering tested

### Error Tracking
- [ ] Error tracking service integrated (optional: Sentry, Rollbar)
- [ ] Error notifications configured
- [ ] Error grouping and deduplication enabled
- [ ] Source maps uploaded for frontend debugging

### Alerting
- [ ] Alerts configured for:
  - API downtime (health check failures)
  - High error rates (>5%)
  - Slow response times (>1s p95)
  - Database connection failures
  - Redis connection failures
  - Disk space low (<10%)
  - Memory usage high (>90%)
- [ ] Alert notification channels configured (email, Slack, PagerDuty)
- [ ] On-call rotation documented

---

## 6. Testing

### Unit & Integration Tests
- [ ] Backend tests passing
  ```bash
  cd /Users/apple/Documents/GitHub/OCL_Twitter_Scraper
  python -m pytest tests/ -v --cov=src --cov-report=term-missing
  # Target: >80% coverage
  ```
- [ ] Frontend tests passing
  ```bash
  cd frontend
  npm test
  ```
- [ ] Critical path coverage verified (auth, scraping, job management)

### API Endpoint Testing
- [ ] Authentication endpoints tested
  ```bash
  # Login
  curl -X POST https://api.yourdomain.com/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"your_password"}'
  ```
- [ ] Job creation and management tested
- [ ] Scraping endpoints tested
- [ ] User management tested (admin only)
- [ ] Error handling tested (invalid inputs, unauthorized access)

### WebSocket Functionality
- [ ] WebSocket connection established
- [ ] Real-time updates received
- [ ] Connection recovery tested (disconnect/reconnect)
- [ ] Multiple concurrent connections tested

### Load Testing
- [ ] Load tests performed with realistic traffic
  ```bash
  # Example with Apache Bench
  ab -n 1000 -c 10 -H "Authorization: Bearer $TOKEN" \
    https://api.yourdomain.com/jobs
  ```
- [ ] Sustained load tested (30+ minutes)
- [ ] Peak load tested (2-3x normal traffic)
- [ ] System behavior under load verified:
  - No crashes or timeouts
  - Response times remain acceptable
  - Error rates stay low
  - Database/Redis connections stable

### Security Scanning
- [ ] Dependency vulnerabilities scanned
  ```bash
  # Backend
  pip install safety
  safety check

  # Frontend
  cd frontend
  npm audit --production
  ```
- [ ] OWASP Top 10 vulnerabilities tested
- [ ] Penetration testing completed (if required)
- [ ] SSL/TLS configuration tested
  ```bash
  # SSL Labs test (manual)
  https://www.ssllabs.com/ssltest/analyze.html?d=api.yourdomain.com
  ```

### Browser Compatibility (Frontend)
- [ ] Chrome/Edge (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Mobile browsers (iOS Safari, Chrome Mobile)

---

## 7. Deployment

### Railway Backend Deployment

#### Initial Setup
- [ ] Railway project created
- [ ] PostgreSQL addon provisioned
- [ ] Redis addon provisioned
- [ ] Custom domain configured (optional)
  ```
  Settings → Networking → Custom Domain
  ```

#### Environment Variables
- [ ] All required environment variables set in Railway dashboard
  ```
  Settings → Variables
  ```
- [ ] Variables verified after deployment
  ```bash
  railway logs | grep "Environment:"
  ```

#### Deployment Process
- [ ] Code pushed to GitHub main branch
- [ ] Railway auto-deployment triggered
  ```bash
  git push origin main
  ```
- [ ] Deployment logs reviewed for errors
  ```bash
  railway logs --tail
  ```
- [ ] Health check passes after deployment
  ```bash
  curl https://your-app.railway.app/health
  ```

#### Post-Deployment Verification
- [ ] Database migrations applied automatically
- [ ] Admin user created (check logs)
- [ ] All endpoints responding
- [ ] WebSocket connections working

### AWS Amplify Frontend Deployment

#### Initial Setup
- [ ] Amplify app created and linked to GitHub repository
- [ ] Build settings configured
  ```yaml
  version: 1
  frontend:
    phases:
      preBuild:
        commands:
          - cd frontend
          - npm ci
      build:
        commands:
          - npm run build
    artifacts:
      baseDirectory: frontend/dist
      files:
        - '**/*'
    cache:
      paths:
        - frontend/node_modules/**/*
  ```
- [ ] Environment variables set in Amplify console
  ```
  App settings → Environment variables
  VITE_API_URL=https://api.yourdomain.com
  VITE_WS_URL=wss://api.yourdomain.com
  ```

#### Custom Domain (Optional)
- [ ] Custom domain added in Amplify
- [ ] DNS records configured
  ```
  CNAME: app.yourdomain.com → <amplify-url>
  ```
- [ ] SSL certificate validated and active

#### Deployment Process
- [ ] Code pushed to GitHub main branch
- [ ] Amplify auto-build triggered
- [ ] Build logs reviewed for errors
- [ ] Preview deployment tested (if enabled)

#### Post-Deployment Verification
- [ ] Frontend loads successfully
- [ ] API connectivity verified (check browser console)
- [ ] WebSocket connection established
- [ ] All pages and routes working

### DNS Configuration

#### Backend
- [ ] A/CNAME record for api.yourdomain.com
  ```
  Type: CNAME
  Name: api
  Value: your-app.railway.app
  TTL: 300
  ```
- [ ] DNS propagation verified
  ```bash
  dig api.yourdomain.com
  nslookup api.yourdomain.com
  ```

#### Frontend
- [ ] A/CNAME record for app.yourdomain.com
  ```
  Handled by Amplify or manual CNAME
  ```
- [ ] DNS propagation verified
  ```bash
  dig app.yourdomain.com
  ```

### SSL Certificates
- [ ] Railway SSL certificate active (auto-provisioned)
- [ ] Amplify SSL certificate active (auto-provisioned)
- [ ] Certificate expiration monitoring enabled
- [ ] HTTPS redirects working
  ```bash
  curl -I http://api.yourdomain.com
  # Should redirect to https://
  ```

---

## 8. Post-Deployment

### Smoke Tests
- [ ] Login with admin credentials
- [ ] Create a test scraping job
- [ ] Verify real-time updates appear
- [ ] Check job appears in job list
- [ ] Verify job details page loads
- [ ] Test manual controls (pause, resume, stop)
- [ ] Create a test user (admin)
- [ ] Logout and login with test user

### Monitoring Activation
- [ ] Health check monitoring active
  ```bash
  # Set up external monitoring (e.g., UptimeRobot, Pingdom)
  curl -X POST https://api.uptimerobot.com/v2/newMonitor \
    -d "api_key=YOUR_KEY" \
    -d "friendly_name=OCL API" \
    -d "url=https://api.yourdomain.com/health" \
    -d "type=1"
  ```
- [ ] Metrics dashboard reviewed
- [ ] Log aggregation working
- [ ] Alerts tested (trigger test alert)
- [ ] First 24-hour metrics baseline established

### Backup Verification
- [ ] First automated backup completed
- [ ] Backup integrity verified
  ```bash
  # Download and inspect backup
  railway backup list
  railway backup download <backup-id>
  ```
- [ ] Backup restoration tested (in staging environment)
- [ ] Backup schedule documented

### Rollback Plan
- [ ] Previous deployment version documented
- [ ] Rollback procedure documented
  ```bash
  # Railway rollback
  railway deployment list
  railway deployment rollback <deployment-id>

  # Amplify rollback
  # Via Amplify Console: Deployments → Select previous → Redeploy
  ```
- [ ] Database rollback strategy documented (migrations)
- [ ] Rollback contact list created

### Documentation
- [ ] Production URLs documented
- [ ] Admin credentials securely stored (password manager)
- [ ] Deployment procedures documented
- [ ] Monitoring dashboards linked
- [ ] Emergency contacts listed
- [ ] Runbook created for common issues

### Team Notification
- [ ] Deployment announcement sent
- [ ] Production access granted to team
- [ ] Monitoring alerts configured for team
- [ ] Support procedures communicated
- [ ] Incident response plan reviewed

---

## 9. Ongoing Maintenance

### Daily Monitoring
- [ ] Review health check status
- [ ] Check error rates and logs
- [ ] Monitor resource usage (CPU, memory, disk)
- [ ] Verify backup completion

### Weekly Tasks
- [ ] Review application metrics trends
- [ ] Analyze slow queries and optimize
- [ ] Review and rotate logs
- [ ] Check for dependency updates
  ```bash
  # Backend
  pip list --outdated

  # Frontend
  cd frontend
  npm outdated
  ```

### Monthly Tasks
- [ ] Security patch review and application
- [ ] Performance optimization review
- [ ] Backup restoration test
- [ ] Access audit (remove inactive users)
- [ ] Cost optimization review (Railway/Amplify)

### Quarterly Tasks
- [ ] Full security audit
- [ ] Disaster recovery drill
- [ ] Capacity planning review
- [ ] Documentation update
- [ ] Dependencies major version upgrades

---

## 10. Rollback Procedures

### Backend Rollback (Railway)

```bash
# 1. List recent deployments
railway deployment list

# 2. Identify last working deployment
railway deployment list | grep SUCCESS

# 3. Rollback to specific deployment
railway deployment rollback <deployment-id>

# 4. Verify rollback
curl https://api.yourdomain.com/health

# 5. Check logs for errors
railway logs --tail

# 6. If database migration rollback needed
railway run python -c "from src.database import rollback_migration; rollback_migration()"
```

### Frontend Rollback (Amplify)

```bash
# Via Amplify Console:
# 1. Go to Amplify Console → Your App → Deployments
# 2. Find previous successful deployment
# 3. Click "Redeploy this version"
# 4. Wait for build to complete
# 5. Verify frontend loads correctly

# Via AWS CLI (alternative):
aws amplify start-deployment \
  --app-id <app-id> \
  --branch-name main \
  --source-url <previous-commit-url>
```

### Database Rollback

```bash
# Only if migrations cause issues
# 1. Connect to database
psql "$DATABASE_URL"

# 2. Check migration history
SELECT * FROM alembic_version;

# 3. Rollback one migration (if using Alembic)
alembic downgrade -1

# 4. Verify database state
# Run application health check
```

---

## Quick Reference

### Essential URLs
- **Backend API**: https://api.yourdomain.com
- **Frontend App**: https://app.yourdomain.com
- **Health Check**: https://api.yourdomain.com/health
- **Railway Dashboard**: https://railway.app/project/<project-id>
- **Amplify Console**: https://console.aws.amazon.com/amplify/

### Essential Commands

```bash
# Check backend health
curl https://api.yourdomain.com/health

# View Railway logs
railway logs --tail

# View Amplify logs
# Via Amplify Console → App → Monitoring

# Test API authentication
curl -X POST https://api.yourdomain.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}'

# Database connection
psql "$DATABASE_URL"

# Redis connection
redis-cli -u "$REDIS_URL"
```

### Emergency Contacts
- **DevOps Lead**: [Name] - [Email] - [Phone]
- **Backend Developer**: [Name] - [Email] - [Phone]
- **Database Admin**: [Name] - [Email] - [Phone]
- **Security Contact**: [Name] - [Email] - [Phone]

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| **DevOps Engineer** | | | |
| **Backend Developer** | | | |
| **Security Engineer** | | | |
| **Project Manager** | | | |

---

**Deployment Date**: _________________

**Deployment Lead**: _________________

**Status**: ⬜ Approved for Production / ⬜ Needs Revision

**Notes**:
____________________________________________
____________________________________________
____________________________________________
