# Debug Progress Bar Issue

## Steps to Debug

### 1. Check Backend Logs
```bash
# Watch the logs in real-time
railway logs

# Look for these messages:
# - "Initial progress updated for {session_id}"
# - "Monitor configured with session tracking"  
# - "Forced progress update sent"
# - "Updated session {session_id} progress: running, phase: starting"
```

### 2. Check Database Updates
```bash
# Connect to database
railway run psql $DATABASE_URL

# Check if session is being created and updated
SELECT session_id, status, performance_metrics 
FROM monitoring_sessions 
ORDER BY start_time DESC 
LIMIT 1;

# Should see performance_metrics with 'phase' field updating
```

### 3. Test API Directly
```bash
# Trigger scraping
curl -X POST https://ocltwitterscraper-production.up.railway.app/monitoring/trigger

# Get the session_id from response, then check progress
curl https://ocltwitterscraper-production.up.railway.app/monitoring/session/{session_id}/progress

# Should see progress_percentage increasing
```

### 4. Common Issues

**If stuck at "initializing":**
- Check if monitor is hanging during initialization
- Look for errors in railway logs
- Verify DATABASE_URL is set correctly

**If progress_percentage is 0:**
- Check if performance_metrics.phase is being set
- Verify flag_modified is working
- Check database connection

**If API calls work but UI doesn't update:**
- Check browser console for errors
- Verify polling is happening every 2 seconds
- Check if phase mapping is correct in frontend
