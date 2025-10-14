# Quick Fix: Progress Bar & Zero Results

## Problem 1: Progress Bar Stuck at 0%
**Cause:** SQLAlchemy doesn't detect JSON field changes
**Status:** ✅ FIXED with flag_modified()

## Problem 2: All Metrics Show 0
**Cause:** Database has no feeds seeded!

### Solution: Seed the Database

```bash
# Method 1: Via API (RECOMMENDED)
curl -X POST https://ocltwitterscraper-production.up.railway.app/seed-data

# Method 2: Via Frontend
# Visit: https://main.d3auorpmwvvmu9.amplifyapp.com
# Open browser console and run:
fetch('https://ocltwitterscraper-production.up.railway.app/seed-data', {
  method: 'POST'
}).then(r => r.json()).then(console.log)

# Method 3: Via Railway CLI
railway run python -c "from src.seed_data import seed_all_data; seed_all_data()"
```

### What /seed-data Does
1. Creates sample companies (Caldera, Fhenix, Fabric, etc.)
2. Creates 10+ active RSS feed sources
3. Initializes database tables
4. Returns confirmation

### After Seeding
1. Click "Start Scraping Cycle" again
2. Progress bar should now move through phases
3. Metrics should show actual counts (articles, tweets, feeds, alerts)

### Verify Seeding Worked
```bash
# Check feed count
curl https://ocltwitterscraper-production.up.railway.app/feeds | jq 'length'

# Should return > 0 (e.g., 10)

# Check company count  
curl https://ocltwitterscraper-production.up.railway.app/companies | jq 'length'

# Should return > 0 (e.g., 5)
```

## Deployment Checklist

```bash
# 1. Set environment variable
export DATABASE_URL="your_railway_postgres_url"

# 2. Deploy code changes
git add .
git commit -m "fix: add flag_modified for progress tracking and fallback for empty feeds"
git push

# 3. Seed the database (CRITICAL!)
curl -X POST https://your-backend-url/seed-data

# 4. Test scraping cycle
curl -X POST https://your-backend-url/monitoring/trigger

# 5. Check progress
curl https://your-backend-url/monitoring/session/{session_id}/progress
```

## Expected Results After Fix

### Progress Bar
- 5% - Initializing
- 15% - Scraping news feeds
- 35% - Processing news
- 55% - Scraping Twitter
- 75% - Processing tweets
- 85% - Updating feed stats
- 90% - Processing alerts
- 95% - Saving to database
- 100% - Complete

### Metrics
- Articles Processed: 10-50+
- Feeds Processed: 10+
- Tweets Processed: 0-20 (if Twitter configured)
- Alerts Generated: 0-10 (depends on TGE mentions found)

## Troubleshooting

**Still showing 0 articles:**
- Verify feeds are seeded: `curl /feeds`
- Check Railway logs for errors
- Verify feeds are actually active RSS feeds

**Still stuck at 0%:**
- Check if flag_modified import works
- Verify database session is not read-only
- Check Railway logs for SQL errors

**Progress moves but no dashboard update:**
- Frontend issue - check browser console
- Verify refetchQueries is being called
- Clear browser cache
