# Railway Deployment Troubleshooting Guide

## How to Check Deployment Logs

1. **Go to Railway dashboard**
2. **Click on your WEB SERVICE** (OCL_Twitter_Scraper)
3. **Click "Deployments" tab** at the top
4. **Click on the failed deployment** (will have a red X or error icon)
5. **Scroll through the logs** to find the error message

---

## Common Errors & Solutions

### Error 1: "No Python version specified"

**Error message:**
```
ERROR: Could not find a version that satisfies the requirement...
```

**Solution:** Add `runtime.txt` file (already created for you!)

**What I did:**
- Created `runtime.txt` with Python 3.11.9
- Created `nixpacks.toml` for Railway configuration

---

### Error 2: "Module not found" or "ImportError"

**Error message:**
```
ModuleNotFoundError: No module named 'src'
ImportError: cannot import name 'app' from 'src.api'
```

**Solution:** Verify your project structure

**Check that you have:**
```
OCL_Twitter_Scraper/
├── src/
│   ├── __init__.py  ← MUST exist!
│   ├── api.py
│   ├── models.py
│   └── ...
├── requirements.txt
├── railway.json
└── nixpacks.toml
```

**If `src/__init__.py` is missing:**
```bash
touch src/__init__.py
git add src/__init__.py
git commit -m "Add __init__.py"
git push
```

---

### Error 3: "Port already in use" or "Address in use"

**Error message:**
```
ERROR: [Errno 48] Address already in use
```

**Solution:** Railway automatically provides `$PORT` environment variable.

**Make sure your start command uses `$PORT`:**
```bash
uvicorn src.api:app --host 0.0.0.0 --port $PORT
```

This is already configured in `railway.json` ✅

---

### Error 4: "Database connection failed"

**Error message:**
```
sqlalchemy.exc.OperationalError: could not connect to server
FATAL: database "tge_monitor" does not exist
```

**Solution:** Make sure PostgreSQL is added to your Railway project

**Steps:**
1. In Railway project, click "+ New"
2. Select "Database" → "PostgreSQL"
3. Railway auto-creates `DATABASE_URL` variable
4. Redeploy your web service

---

### Error 5: "psycopg2 build error"

**Error message:**
```
Error: pg_config executable not found
could not build psycopg2
```

**Solution:** Use `psycopg2-binary` (already in requirements.txt ✅)

**If you see this error, make sure `requirements.txt` has:**
```
psycopg2-binary==2.9.9
```
NOT just `psycopg2`

---

### Error 6: "Redis connection failed"

**Error message:**
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**Solution:** Make sure Redis is added to your Railway project

**Steps:**
1. In Railway project, click "+ New"
2. Select "Database" → "Redis"
3. Railway auto-creates `REDIS_URL` variable
4. Redeploy your web service

---

### Error 7: "Build timeout" or "Build failed"

**Error message:**
```
Build failed: timeout exceeded
```

**Solution:** Some packages take a long time to install

**Try:**
1. Simplify `requirements.txt` (remove optional dependencies)
2. Use Railway's Pro plan (more build time)
3. Check if any packages are incompatible

**Temporary fix - comment out heavy packages:**
```python
# Optional dependencies (not required for core functionality)
beautifulsoup4==4.12.2
# selenium==4.15.2  ← Already commented
# pytz==2023.3  ← Already commented
lxml==4.9.3
newspaper3k==0.2.8
nltk==3.8.1
# textblob==0.17.1  ← Already commented
# pandas>=2.0.0  ← Comment this out temporarily
# webdriver-manager==4.0.1  ← Already commented
```

---

### Error 8: "Healthcheck failed"

**Error message:**
```
Healthcheck failed: GET /health returned 404
```

**Solution:** Make sure your API has a `/health` endpoint

**Check `src/api.py` has:**
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

---

### Error 9: "Environment variable not set"

**Error message:**
```
KeyError: 'SECRET_KEY'
Configuration error: SECRET_KEY is required
```

**Solution:** Add missing environment variables

**Required variables in Railway:**
- `SECRET_KEY`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `DATABASE_URL` (auto-added by PostgreSQL)
- `REDIS_URL` (auto-added by Redis)

---

## Step-by-Step Fix Process

### Step 1: Check What Broke

1. Go to Railway → Your Web Service → Deployments
2. Click the failed deployment
3. Read the error logs carefully
4. Note the exact error message

### Step 2: Apply the Fix

Based on the error, apply one of the solutions above.

### Step 3: Redeploy

**Option A: Automatic redeploy (if you push to GitHub)**
```bash
git add .
git commit -m "Fix Railway deployment"
git push origin main
```
Railway auto-deploys on push.

**Option B: Manual redeploy in Railway**
1. Click "Deployments" tab
2. Click "Deploy" button (top right)
3. Select your branch
4. Click "Deploy"

---

## Quick Diagnostic Commands

Run these locally to catch errors before deploying:

```bash
# Test if Python version is correct
python --version  # Should be 3.11+

# Test if all dependencies install
pip install -r requirements.txt

# Test if the API starts locally
uvicorn src.api:app --host 0.0.0.0 --port 8000

# Test health endpoint
curl http://localhost:8000/health
```

---

## Most Common Issue: Missing src/__init__.py

**90% of deployment failures are due to missing `__init__.py`**

**Quick fix:**
```bash
# Create the file
touch src/__init__.py

# Commit and push
git add src/__init__.py
git commit -m "Add __init__.py to src package"
git push origin main
```

Railway will automatically redeploy.

---

## Files Required for Deployment

Make sure these files exist in your repo:

✅ `requirements.txt` - Python dependencies
✅ `railway.json` - Railway configuration
✅ `nixpacks.toml` - Build configuration
✅ `runtime.txt` - Python version
✅ `Procfile` - Alternative start command
✅ `src/__init__.py` - Makes src a package
✅ `src/api.py` - FastAPI application
✅ `.env.example` - Example environment variables

---

## Still Not Working?

### Get Help from Railway Logs

1. **Copy the full error log** from Railway
2. **Look for lines with "ERROR"** or "FAILED"
3. **Share the error here** and I'll help debug

### Common Questions

**Q: Why does it work locally but not on Railway?**
A: Usually environment variables or missing system dependencies.

**Q: How do I see real-time logs?**
A: Railway → Web Service → Deployments → Click deployment → Logs update live

**Q: Can I SSH into Railway to debug?**
A: No, but you can add debug print statements and redeploy to see logs

**Q: How long should deployment take?**
A: Usually 2-5 minutes. If it takes longer, there might be an issue.

---

## Emergency: Start Fresh

If nothing works, recreate from scratch:

1. **Delete the Railway project**
2. **Create a new Railway project**
3. **Add PostgreSQL and Redis**
4. **Set environment variables**
5. **Deploy again**

---

## Contact Me with This Info

If deployment still fails, tell me:

1. ✅ **The exact error message** from Railway logs
2. ✅ **Which step failed** (build, install, start, healthcheck)
3. ✅ **Screenshot** of the error (optional but helpful)
4. ✅ **What you've tried** to fix it

I'll help you debug! 🚀
