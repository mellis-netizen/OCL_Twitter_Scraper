# Progress Bar Debugging Guide

## Problem: Progress bar stuck at 0% on "Initializing scraping cycle"

## Steps to Debug

### 1. Check Railway Logs (CRITICAL)
```bash
railway logs --follow

# Look for these specific log messages:
# "[session_id] Database session created"
# "[session_id] Progress set to 'starting' (5%)"
# "[session_id] Found X active feeds in database"
# "[session_id] Creating monitor instance..."
# "[session_id] Monitor instance created successfully"
# "[session_id] Starting monitoring cycle NOW"
```

### 2. Common Issues

#### Issue A: Database Not Seeded
**Symptoms:**
- Log shows: "Found 0 active feeds in database"
- Log shows: "NO FEEDS SEEDED! Please call POST /seed-data first"

**Fix:**
```bash
curl -X POST https://ocltwitterscraper-production.up.railway.app/seed-data
```

#### Issue B: Monitor Initialization Hanging
**Symptoms:**
- Log shows: "Creating monitor instance..."
- But NEVER shows: "Monitor instance created successfully"
- Progress stays at 0% or 10%

**Possible Causes:**
- Database connection timeout
- NLTK data download hanging
- Twitter API initialization hanging
- Feed loading from database taking too long

**Fix:**
```bash
# Check if DATABASE_URL is set correctly
railway variables

# Restart the application
railway restart
```

#### Issue C: Database Session Not Committing
**Symptoms:**
- Logs show progress updates happening
- But frontend still shows 0%

**Fix:**
- Already fixed with flag_modified()
- If still happening, check database connection

### 3. Test Progress Endpoint Directly

```bash
# 1. Trigger scraping
RESPONSE=$(curl -s -X POST https://ocltwitterscraper-production.up.railway.app/monitoring/trigger)
SESSION_ID=$(echo $RESPONSE | jq -r '.session_id')
echo "Session ID: $SESSION_ID"

# 2. Check progress (multiple times)
for i in {1..5}; do
  echo "Check $i:"
  curl -s "https://ocltwitterscraper-production.up.railway.app/monitoring/session/$SESSION_ID/progress" | jq '{progress: .progress_percentage, phase: .current_phase, status: .status}'
  sleep 3
done
```

**Expected Output:**
```json
Check 1:
{"progress": 5, "phase": "starting", "status": "running"}

Check 2:
{"progress": 10, "phase": "initializing_monitor", "status": "running"}

Check 3:
{"progress": 15, "phase": "scraping_news", "status": "running"}
```

**If stuck at 0:**
- Phase is not in the phase_progress mapping
- performance_metrics is null/empty
- Database changes not committed

**If stuck at 5% or 10:**
- Monitor initialization is hanging
- Check Railway logs for errors

### 4. Check Database Directly

```bash
railway run psql $DATABASE_URL

# Check if session exists and has performance_metrics
SELECT session_id, status, performance_metrics, start_time 
FROM monitoring_sessions 
ORDER BY start_time DESC 
LIMIT 1;

# Should show something like:
# performance_metrics: {"phase": "starting", "timestamp": "2025-..."}
```

### 5. Quick Fixes

#### If nothing is seeded:
```bash
curl -X POST https://ocltwitterscraper-production.up.railway.app/seed-data
```

#### If Railway is hanging:
```bash
railway restart
```

#### If logs show errors:
```bash
# Check for common errors:
railway logs | grep -i "error\|exception\|failed"
```

## Expected Timeline

A full scraping cycle should take 60-180 seconds:
- 0s: starting (5%)
- 5s: initializing_monitor (10%)
- 10s: scraping_news (15%)
- 30-90s: processing_news (35%)
- 95s: scraping_twitter (55%)
- 120s: processing_twitter (75%)
- 130s: updating_feeds (85%)
- 140s: processing_alerts (90%)
- 150s: saving_alerts (95%)
- 160s: completed (100%)

If stuck at ANY phase for >30 seconds, check Railway logs!
