# Where to Deploy What - Railway vs Netlify

## Quick Answer

**Railway = Backend API (Deploy from ROOT)**
- Deploy from: **Root of repository** (`/`)
- Contains: Python/FastAPI code

**Netlify = Frontend React App (Deploy from FRONTEND)**
- Deploy from: **`frontend/` directory**
- Contains: React/TypeScript code

---

## Visual Guide

```
Your Repository Structure:
OCL_Twitter_Scraper/              ← ROOT (Railway deploys THIS)
├── src/                          ← Backend API code
│   ├── __init__.py
│   ├── api.py                    ← FastAPI application
│   ├── models.py
│   ├── database.py
│   └── ...
├── requirements.txt              ← Python dependencies
├── runtime.txt                   ← Python version
├── Procfile                      ← Railway start command
├── railway.json                  ← Railway config (optional)
├── nixpacks.toml                 ← Railway config (optional)
├── .env.example                  ← Backend environment template
└── frontend/                     ← FRONTEND DIR (Netlify deploys THIS)
    ├── src/                      ← React code
    │   ├── App.tsx
    │   ├── main.tsx
    │   └── components/
    ├── package.json              ← Node dependencies
    ├── vite.config.ts            ← Vite config
    ├── netlify.toml              ← Netlify config
    └── .env                      ← Frontend environment
```

---

## Railway Setup (Backend)

### What Railway Deploys:
**Location:** Root of repository (`/`)

**Files it uses:**
- `src/api.py` - FastAPI application
- `requirements.txt` - Python packages
- `runtime.txt` - Python version
- `Procfile` - Start command
- All files in `src/` directory

**Files it IGNORES:**
- `frontend/` directory (not needed for backend)

### Railway Configuration:

**When connecting your repo:**
```
Root Directory:  /                    ← Leave this as default!
                 (or leave blank)

Build Command:   (auto-detected)      ← Railway handles this
Start Command:   (from Procfile)      ← Railway uses this
```

**DO NOT** set root directory to `frontend/` in Railway!

---

## Netlify Setup (Frontend)

### What Netlify Deploys:
**Location:** `frontend/` directory

**Files it uses:**
- `frontend/src/` - React components
- `frontend/package.json` - Node packages
- `frontend/vite.config.ts` - Build config
- `frontend/netlify.toml` - Netlify config

**Files it IGNORES:**
- Root level Python files (not needed for frontend)
- `src/` directory (that's backend code)

### Netlify Configuration:

**When connecting your repo:**
```
Base Directory:     frontend          ← SET THIS!
Build Command:      npm run build     ← SET THIS!
Publish Directory:  frontend/dist     ← SET THIS!
                    (or just: dist)
```

**DO** set base directory to `frontend/` in Netlify!

---

## Side-by-Side Comparison

| Setting           | Railway (Backend)          | Netlify (Frontend)         |
|-------------------|----------------------------|----------------------------|
| **Deploy From**   | Root of repo (`/`)         | `frontend/` directory      |
| **Technology**    | Python/FastAPI             | React/TypeScript/Vite      |
| **Dependencies**  | `requirements.txt`         | `package.json`             |
| **Build**         | `pip install -r ...`       | `npm run build`            |
| **Start Command** | `uvicorn src.api:app ...`  | Static files served        |
| **Output**        | Running API server         | Static HTML/JS/CSS files   |
| **Base Directory**| `/` (root)                 | `frontend/`                |

---

## Step-by-Step: Railway Deployment

### 1. Connect Repository to Railway

1. Go to [railway.app](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose `OCL_Twitter_Scraper` repository
5. **Railway automatically detects root as deployment location** ✅

### 2. Verify Railway Settings

1. Click on your web service
2. Go to "Settings" tab
3. Check "Source Code":
   ```
   Repository: OCL_Twitter_Scraper
   Branch: main
   Root Directory: /              ← Should be empty or "/"
   ```

**If it shows `frontend/` - CHANGE IT BACK TO `/` or leave blank!**

### 3. What Railway Does

When deploying from root:
1. Finds `requirements.txt` → Installs Python packages
2. Finds `runtime.txt` → Uses Python 3.11
3. Finds `Procfile` → Runs `uvicorn src.api:app`
4. Exposes API at `https://your-app.up.railway.app`

---

## Step-by-Step: Netlify Deployment

### 1. Connect Repository to Netlify

1. Go to [netlify.com](https://netlify.com)
2. Click "Add new site" → "Import an existing project"
3. Choose "Deploy with GitHub"
4. Select `OCL_Twitter_Scraper` repository

### 2. Configure Build Settings

**IMPORTANT:** Set base directory to `frontend/`

```
Base directory:     frontend          ← MUST SET THIS!
Build command:      npm run build
Publish directory:  frontend/dist     ← Or just: dist
```

### 3. What Netlify Does

When deploying from `frontend/`:
1. Changes to `frontend/` directory
2. Finds `package.json` → Installs Node packages
3. Runs `npm run build` → Creates `dist/` folder
4. Serves static files from `dist/`
5. Exposes frontend at `https://your-app.netlify.app`

---

## Common Mistakes

### ❌ WRONG: Deploying Frontend to Railway

```
Railway Settings:
Root Directory: frontend/          ← WRONG!
```

**Problem:** Railway expects Python code, will fail trying to run React app

### ❌ WRONG: Deploying Backend to Netlify

```
Netlify Settings:
Base Directory: /                  ← WRONG!
```

**Problem:** Netlify expects static files, can't run Python/FastAPI

### ✅ CORRECT: Each Platform Gets Its Code

```
Railway:
- Deploys from: / (root)
- Runs: Python FastAPI backend

Netlify:
- Deploys from: frontend/
- Serves: React frontend
```

---

## Quick Test: Am I in the Right Place?

### Railway Dashboard:

**Check "Deployments" tab logs. You should see:**
```
✓ Installing Python 3.11...
✓ pip install -r requirements.txt
✓ Starting uvicorn...
✓ Application startup complete
```

**If you see Node/npm stuff - YOU'RE IN THE WRONG DIRECTORY!**

### Netlify Dashboard:

**Check "Deploys" tab logs. You should see:**
```
✓ Installing Node.js...
✓ npm install
✓ npm run build
✓ Site is live
```

**If you see Python/pip stuff - YOU'RE IN THE WRONG DIRECTORY!**

---

## Environment Variables

### Railway (Backend):
```env
DATABASE_URL         ← Auto-added by Railway
REDIS_URL            ← Auto-added by Railway
SECRET_KEY           ← You add this
ADMIN_USERNAME       ← You add this
ADMIN_PASSWORD       ← You add this
CORS_ORIGINS         ← You add this (set to Netlify URL)
```

### Netlify (Frontend):
```env
VITE_API_URL         ← You add this (Railway URL)
VITE_WS_URL          ← You add this (Railway URL with wss://)
```

---

## Full Deployment Flow

```
1. Deploy Backend to Railway (from ROOT):
   ↓
   Railway builds Python app from root
   ↓
   Get URL: https://your-app.up.railway.app
   ↓

2. Update Frontend .env with Railway URL:
   ↓
   VITE_API_URL=https://your-app.up.railway.app
   ↓

3. Deploy Frontend to Netlify (from frontend/):
   ↓
   Netlify builds React app from frontend/
   ↓
   Get URL: https://your-app.netlify.app
   ↓

4. Update Backend CORS with Netlify URL:
   ↓
   Railway → Variables → CORS_ORIGINS=https://your-app.netlify.app
   ↓

5. Done! Frontend talks to Backend ✅
```

---

## Troubleshooting

### Railway: "No start command found"

**Problem:** You set root directory to `frontend/`
**Solution:** Go to Settings → Change root directory to `/` or leave blank

### Railway: "Module not found: package.json"

**Problem:** Railway is looking in root but you have it in `frontend/`
**Solution:** This is correct! Railway should deploy from root.

### Netlify: "Build failed: no package.json"

**Problem:** Base directory not set to `frontend/`
**Solution:** Go to Site settings → Build & deploy → Set base directory to `frontend/`

### Netlify: "Error: python: command not found"

**Problem:** Netlify is trying to build backend
**Solution:** Set base directory to `frontend/`, not root

---

## Summary

| What          | Deploy Where     | Platform | Base Directory |
|---------------|------------------|----------|----------------|
| **Backend**   | Root (`/`)       | Railway  | `/` or blank   |
| **Frontend**  | `frontend/` dir  | Netlify  | `frontend/`    |

**Remember:**
- Railway = Backend = Root directory
- Netlify = Frontend = `frontend/` directory

---

## Need Help?

If you're confused about which directory to use:

**Are you deploying the API (Python/FastAPI)?**
→ Use Railway from ROOT

**Are you deploying the UI (React/TypeScript)?**
→ Use Netlify from `frontend/`

Both need to be deployed separately to different platforms!
