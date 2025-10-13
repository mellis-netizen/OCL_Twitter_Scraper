# How to Find Database URLs in Railway

## TL;DR - You Don't Need To!

Railway **automatically** provides database URLs to your web service. You don't need to copy/paste them manually!

---

## Visual Guide

### Your Railway Project Looks Like This:

```
┌──────────────────────────────────────────────────────────┐
│                    YOUR RAILWAY PROJECT                   │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  WEB SERVICE (OCL_Twitter_Scraper)              │    │
│  │                                                  │    │
│  │  Variables Tab:                                  │    │
│  │  ├─ DATABASE_URL = postgresql://default:xxx...  │ ← Auto-added! │
│  │  ├─ REDIS_URL = redis://default:xxx...          │ ← Auto-added! │
│  │  ├─ SECRET_KEY = abc123...         (you added)  │    │
│  │  ├─ ADMIN_USERNAME = admin         (you added)  │    │
│  │  └─ ADMIN_PASSWORD = pass123       (you added)  │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  PostgreSQL                                      │    │
│  │  (Database service)                              │    │
│  │                                                  │    │
│  │  Variables Tab:                                  │    │
│  │  ├─ DATABASE_URL = postgresql://...             │    │
│  │  ├─ PGHOST = containers-xxx.railway.app         │    │
│  │  ├─ PGPORT = 5432                                │    │
│  │  ├─ PGDATABASE = railway                         │    │
│  │  ├─ PGUSER = default                             │    │
│  │  └─ PGPASSWORD = xxx                             │    │
│  └─────────────────────────────────────────────────┘    │
│                       ↑                                   │
│                   These values                            │
│                   are also in your                        │
│                   web service!                            │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Redis                                           │    │
│  │  (Cache service)                                 │    │
│  │                                                  │    │
│  │  Variables Tab:                                  │    │
│  │  ├─ REDIS_URL = redis://...                     │    │
│  │  ├─ REDIS_HOST = containers-xxx.railway.app     │    │
│  │  ├─ REDIS_PORT = 6379                            │    │
│  │  └─ REDIS_PASSWORD = xxx                         │    │
│  └─────────────────────────────────────────────────┘    │
│                       ↑                                   │
│                   These values                            │
│                   are also in your                        │
│                   web service!                            │
└──────────────────────────────────────────────────────────┘
```

---

## Step-by-Step: Where to Find Database URLs

### Option 1: In Your Web Service (Recommended)

This is where your **FastAPI app** will read them from:

1. Click **"WEB SERVICE"** (OCL_Twitter_Scraper)
2. Click **"Variables"** tab
3. Scroll down - you'll see:
   ```
   DATABASE_URL = postgresql://default:abc123@containers-us-west-xxx.railway.app:5432/railway
   REDIS_URL = redis://default:xyz789@containers-us-west-xxx.railway.app:6379
   ```

**These are already available to your application!** Your code reads them automatically.

---

### Option 2: In PostgreSQL Service (If You Need Raw Values)

If you want to connect to the database directly (e.g., with a database client):

1. Click **"PostgreSQL"** service card
2. Click **"Connect"** tab
3. You'll see connection details:
   ```
   Connection String (DATABASE_URL):
   postgresql://default:abc123@containers-us-west-xxx.railway.app:5432/railway

   Individual values:
   Host:     containers-us-west-xxx.railway.app
   Port:     5432
   Database: railway
   Username: default
   Password: abc123...
   ```

4. Or click **"Variables"** tab to see all variables

---

### Option 3: In Redis Service (If You Need Raw Values)

Same process for Redis:

1. Click **"Redis"** service card
2. Click **"Connect"** tab
3. You'll see:
   ```
   Connection String (REDIS_URL):
   redis://default:xyz789@containers-us-west-xxx.railway.app:6379

   Individual values:
   Host:     containers-us-west-xxx.railway.app
   Port:     6379
   Password: xyz789...
   ```

---

## Do I Need to Copy These URLs Anywhere?

### NO! Here's why:

**Railway automatically:**
1. Creates these URLs when you add PostgreSQL/Redis
2. Injects them into your web service as environment variables
3. Makes them available to your Python code

**Your FastAPI code already uses them:**

```python
# In your code (config.py or similar):
import os

DATABASE_URL = os.getenv("DATABASE_URL")  # Railway provides this!
REDIS_URL = os.getenv("REDIS_URL")        # Railway provides this!
```

**You don't need to manually set these variables!**

---

## When You WOULD Need These URLs

### Use Case 1: Connecting with a Database Client

If you want to connect to your Railway database from your computer using:
- pgAdmin
- DBeaver
- TablePlus
- psql command line

**Then:**
1. Go to PostgreSQL service → Connect tab
2. Copy the connection details
3. Use them in your database client

### Use Case 2: Debugging Connection Issues

If your app can't connect to the database:
1. Check that DATABASE_URL exists in web service variables
2. Verify the URL format is correct
3. Test connection manually

### Use Case 3: External Services

If you want to connect from:
- A local development environment
- Another server
- A third-party service

**Then** you need to copy the URLs.

---

## Common Mistakes

### ❌ WRONG: Manually adding DATABASE_URL to web service

**Don't do this:**
```
Click "+ New Variable"
Variable Name: DATABASE_URL
Value: postgresql://...
```

Railway **already added this** when you created PostgreSQL!

### ✅ RIGHT: Let Railway manage it

**Just add PostgreSQL to your project** and Railway handles everything.

---

## Verification: Check If URLs Are Available

To verify your web service has access to database URLs:

1. Go to **WEB SERVICE**
2. Click **"Variables"** tab
3. Look for these (should already be there):
   ```
   DATABASE_URL = postgresql://...
   REDIS_URL = redis://...
   ```

If you **don't** see them:

**Solution:**
1. Make sure PostgreSQL and Redis are in the **same Railway project**
2. Railway might need a minute to sync - refresh the page
3. If still missing, delete and re-add the database services

---

## Quick Reference

### For Your Web Service (FastAPI App)

**Environment variables available:**
```bash
DATABASE_URL       # Full PostgreSQL connection string
REDIS_URL          # Full Redis connection string
PORT               # Port to run on (Railway provides this)
SECRET_KEY         # You added this
ADMIN_USERNAME     # You added this
ADMIN_PASSWORD     # You added this
# ... any other variables you added
```

### For Database Clients

**PostgreSQL connection:**
```
Host:     Check PostgreSQL → Connect tab
Port:     5432
Database: railway
Username: default
Password: Check PostgreSQL → Variables → PGPASSWORD
```

**Redis connection:**
```
Host:     Check Redis → Connect tab
Port:     6379
Password: Check Redis → Variables → REDIS_PASSWORD
```

---

## Summary

**You asked:** "How do I find the URLs for Redis and PostgreSQL?"

**Answer:** They're already in your web service variables! Railway automatically adds them when you create the database services.

**To see them:**
1. Click your **WEB SERVICE**
2. Click **"Variables"** tab
3. Look for `DATABASE_URL` and `REDIS_URL`

**You don't need to do anything with these URLs** - your code already uses them via `os.getenv()`!

---

## Still Confused?

Think of it this way:

```
PostgreSQL Service → Creates database → Generates DATABASE_URL
                                             ↓
                              Railway automatically shares this
                                             ↓
                              Your Web Service receives it
                                             ↓
                              Your Python code reads it
```

**It's automatic!** You just need to make sure all services are in the same Railway project.
