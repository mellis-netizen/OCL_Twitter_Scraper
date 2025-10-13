# Railway Deployment Fix - "Invalid Input" Error

## The Error You Saw

```
Failed to parse your service config.
Error: deploy.restartPolicyType: Invalid input
```

## What Caused It

The `railway.json` file had configuration fields that Railway doesn't support:
- `restartPolicyType` ❌ (doesn't exist)
- `restartPolicyMaxRetries` ❌ (doesn't exist)
- `numReplicas` ❌ (not for Hobby tier)

## The Fix

I've updated `railway.json` to only use valid fields.

### Option 1: Use Updated railway.json (Recommended)

**I already fixed it for you!** The file now contains:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "nixpacks"
  },
  "deploy": {
    "startCommand": "uvicorn src.api:app --host 0.0.0.0 --port $PORT --workers 2",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100
  }
}
```

**Just commit and push:**
```bash
git add railway.json
git commit -m "Fix Railway configuration"
git push origin main
```

Railway will automatically redeploy with the corrected config! ✅

---

### Option 2: Delete railway.json Entirely (Also Works)

Railway can work without `railway.json` if you have:
- ✅ `Procfile` (we have this)
- ✅ `nixpacks.toml` (we have this)
- ✅ `requirements.txt` (we have this)

**To use this option:**
```bash
# Remove railway.json
rm railway.json

# Commit and push
git add .
git commit -m "Remove railway.json, use nixpacks.toml instead"
git push origin main
```

Railway will use `nixpacks.toml` and `Procfile` for configuration.

---

### Option 3: Minimal railway.json (Simplest)

If you want the absolute minimum:

```json
{
  "build": {
    "builder": "nixpacks"
  },
  "deploy": {
    "startCommand": "uvicorn src.api:app --host 0.0.0.0 --port $PORT"
  }
}
```

---

## What Should You Do Right Now?

### Quick Fix (30 seconds)

```bash
# The file is already fixed, just push it
git add railway.json
git commit -m "Fix Railway deployment config"
git push origin main
```

That's it! Railway will redeploy automatically.

---

## What Railway Actually Supports

### Valid railway.json Fields:

```json
{
  "build": {
    "builder": "nixpacks" | "dockerfile",
    "dockerfilePath": "Dockerfile"  // Only if builder is dockerfile
  },
  "deploy": {
    "startCommand": "your start command",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100
  }
}
```

### NOT Supported (These Don't Exist):
- ❌ `restartPolicyType`
- ❌ `restartPolicyMaxRetries`
- ❌ `numReplicas` (on Hobby plan)
- ❌ `buildCommand` (use nixpacks.toml instead)

---

## Alternative: Use Only nixpacks.toml

Railway prefers `nixpacks.toml` over `railway.json`. You can delete `railway.json` and just use:

**nixpacks.toml** (already created):
```toml
[phases.setup]
nixPkgs = ["python311", "postgresql", "openssl"]
aptPkgs = ["libpq-dev", "build-essential"]

[phases.install]
cmds = ["pip install --upgrade pip", "pip install -r requirements.txt"]

[start]
cmd = "uvicorn src.api:app --host 0.0.0.0 --port $PORT --workers 2"
```

**Procfile** (already created):
```
web: uvicorn src.api:app --host 0.0.0.0 --port $PORT --workers 2
```

Railway will read these files automatically!

---

## Troubleshooting Next Errors

After fixing this, you might see other errors. Here are solutions:

### Error: "ModuleNotFoundError"
**Solution:** Make sure `src/__init__.py` exists
```bash
touch src/__init__.py
git add src/__init__.py
git commit -m "Add __init__.py"
git push
```

### Error: "Database connection failed"
**Solution:** Add PostgreSQL to your Railway project:
1. Click "+ New"
2. Select "Database" → "PostgreSQL"
3. Wait for it to provision
4. Redeploy your web service

### Error: "Redis connection failed"
**Solution:** Add Redis to your Railway project:
1. Click "+ New"
2. Select "Database" → "Redis"
3. Wait for it to provision
4. Redeploy your web service

### Error: "Build timeout"
**Solution:** Comment out pandas in requirements.txt (it's slow to install):
```python
# pandas>=2.0.0  # Commented out for faster builds
```

---

## Summary

**Problem:** Railway config had invalid fields
**Solution:** I fixed `railway.json` with only valid fields
**Action:** Just `git push` the updated file!

```bash
git add railway.json
git commit -m "Fix Railway configuration"
git push origin main
```

Railway will automatically redeploy in ~2-5 minutes. Watch the logs in Railway dashboard to see progress! 🚀
