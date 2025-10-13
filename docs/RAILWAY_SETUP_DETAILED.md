# Railway Deployment - Super Detailed Step-by-Step Guide

## What You'll Create in Railway

Railway projects have **3 separate services**:
1. **Web Service** (your FastAPI application) - the main API server
2. **PostgreSQL Database** - stores companies, alerts, feeds
3. **Redis** - caching and rate limiting

Each service is configured separately!

---

## Step-by-Step Railway Setup

### Part 1: Create Project & Connect GitHub (2 minutes)

1. **Go to [railway.app](https://railway.app)**

2. **Sign up/Login** with your GitHub account

3. **Click "New Project"** (big purple button in top right)

4. **Select "Deploy from GitHub repo"**
   - If this is your first time: Click "Configure GitHub App" to authorize Railway
   - Select your GitHub account
   - Choose which repositories Railway can access (select your `OCL_Twitter_Scraper` repo)

5. **Select your repository**: `OCL_Twitter_Scraper`

6. **Railway will automatically detect it's a Python app** and start deploying

   You should now see ONE service card that says something like:
   ```
   OCL_Twitter_Scraper
   (or main, or master - depending on your branch name)
   ```

   ⚠️ **This is your WEB SERVICE** (FastAPI app)

---

### Part 2: Add PostgreSQL Database (1 minute)

Now you need to add a database. Your web service needs data storage!

1. **In your Railway project dashboard**, click the **"+ New"** button (top right)

2. **Select "Database"**

3. **Click "Add PostgreSQL"**

4. Railway creates a new service card:
   ```
   PostgreSQL
   ```

5. **That's it for PostgreSQL!** Railway automatically:
   - Creates the database
   - Generates a `DATABASE_URL` environment variable
   - Makes it available to all services in this project

**You don't need to configure anything in PostgreSQL service.** Railway handles it automatically.

---

### Part 3: Add Redis (1 minute)

Your app also needs Redis for caching and rate limiting.

1. **Click the "+ New" button again** (top right)

2. **Select "Database"**

3. **Click "Add Redis"**

4. Railway creates another service card:
   ```
   Redis
   ```

5. **That's it for Redis!** Railway automatically:
   - Creates the Redis instance
   - Generates a `REDIS_URL` environment variable
   - Makes it available to all services

**You don't need to configure anything in Redis service.**

---

### Part 4: Configure YOUR WEB SERVICE (5 minutes)

Now you have 3 service cards in Railway:
```
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│ OCL_Twitter_Scraper │  │    PostgreSQL        │  │       Redis         │
│  (Web Service)      │  │    (Database)        │  │      (Cache)        │
│  ← CLICK THIS ONE   │  │                      │  │                     │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

**Click on the WEB SERVICE card** (the one with your repo name, NOT PostgreSQL or Redis)

#### A. Go to Variables Tab

After clicking your web service, you'll see tabs at the top:
```
Deployments | Metrics | Settings | Variables | Observability
```

**Click "Variables"**

#### B. Add Environment Variables

You'll see that Railway already added some variables automatically:
- `DATABASE_URL` (from PostgreSQL)
- `REDIS_URL` (from Redis)
- Maybe some others like `PORT`

**DO NOT DELETE THESE!** They're automatically managed by Railway.

Now, click **"+ New Variable"** and add each of these ONE BY ONE:

**Variable 1: SECRET_KEY**
```
Variable Name:  SECRET_KEY
Value:          <click "Generate Random String" button OR paste output of: openssl rand -hex 32>
```

**Variable 2: ADMIN_USERNAME**
```
Variable Name:  ADMIN_USERNAME
Value:          admin
```

**Variable 3: ADMIN_PASSWORD**
```
Variable Name:  ADMIN_PASSWORD
Value:          <choose a strong password, like: MySecurePass123!>
```

**Variable 4: CORS_ORIGINS** (we'll update this later)
```
Variable Name:  CORS_ORIGINS
Value:          *
```

**Variable 5: TWITTER_BEARER_TOKEN** (optional)
```
Variable Name:  TWITTER_BEARER_TOKEN
Value:          <your Twitter API bearer token - or skip if you don't have one>
```

**Variable 6: EMAIL_ENABLED** (optional)
```
Variable Name:  EMAIL_ENABLED
Value:          true
```

**Variable 7: EMAIL_USER** (optional)
```
Variable Name:  EMAIL_USER
Value:          your-email@gmail.com
```

**Variable 8: EMAIL_PASSWORD** (optional)
```
Variable Name:  EMAIL_PASSWORD
Value:          <your Gmail app password - not your regular password!>
```

**Variable 9: EMAIL_SMTP_HOST** (optional)
```
Variable Name:  EMAIL_SMTP_HOST
Value:          smtp.gmail.com
```

**Variable 10: EMAIL_SMTP_PORT** (optional)
```
Variable Name:  EMAIL_SMTP_PORT
Value:          587
```

#### C. Your Variables Should Look Like This:

After adding all variables, you should see:
```
DATABASE_URL              postgresql://default:xxx@xxx.railway.app:5432/railway  [Railway managed]
REDIS_URL                 redis://default:xxx@xxx.railway.app:6379               [Railway managed]
PORT                      8000                                                   [Railway managed]
SECRET_KEY                a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0              [You added]
ADMIN_USERNAME            admin                                                  [You added]
ADMIN_PASSWORD            MySecurePass123!                                       [You added]
CORS_ORIGINS              *                                                      [You added]
TWITTER_BEARER_TOKEN      AAAAAAAAAAAAAAAAAxxxxxxxxxx                            [You added - optional]
EMAIL_ENABLED             true                                                   [You added - optional]
EMAIL_USER                your-email@gmail.com                                   [You added - optional]
EMAIL_PASSWORD            your-app-password                                      [You added - optional]
EMAIL_SMTP_HOST           smtp.gmail.com                                         [You added - optional]
EMAIL_SMTP_PORT           587                                                    [You added - optional]
```

**After adding each variable**, Railway will automatically redeploy your app.

---

### Part 5: Get Your API URL (1 minute)

After deployment finishes (green checkmark), get your URL:

1. **Make sure you're still on the WEB SERVICE** (not PostgreSQL or Redis)

2. **Click the "Settings" tab**

3. **Scroll down to the "Networking" section**

4. **Look for "Domains"**

5. **Click "Generate Domain"** button

   Railway will create a URL like:
   ```
   https://ocl-twitter-scraper-production-xxxx.up.railway.app
   ```

6. **Copy this URL!** This is your:
   - `VITE_API_URL` for the frontend
   - `VITE_WS_URL` for the frontend (just change https to wss)

**Example:**
```env
# If Railway gives you:
https://tge-monitor-production-a1b2.up.railway.app

# Then use:
VITE_API_URL=https://tge-monitor-production-a1b2.up.railway.app
VITE_WS_URL=wss://tge-monitor-production-a1b2.up.railway.app
```

---

### Part 6: Verify Deployment

1. **Visit your Railway URL** in a browser:
   ```
   https://your-app.up.railway.app/health
   ```

   You should see JSON response like:
   ```json
   {
     "status": "healthy",
     "database": true,
     "redis": true
   }
   ```

2. **Check API documentation:**
   ```
   https://your-app.up.railway.app/docs
   ```

   You should see the FastAPI Swagger UI.

If both work, **your backend is live!** 🎉

---

## Visual Guide: What's What in Railway

```
YOUR RAILWAY PROJECT
├─────────────────────────────────────────────────────────────┐
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  WEB SERVICE (FastAPI App)                          │    │
│  │  ← THIS IS WHERE YOU ADD ENVIRONMENT VARIABLES      │    │
│  │                                                      │    │
│  │  Variables Tab:                                      │    │
│  │  - DATABASE_URL (auto-added)                         │    │
│  │  - REDIS_URL (auto-added)                            │    │
│  │  - SECRET_KEY (YOU add this)                         │    │
│  │  - ADMIN_USERNAME (YOU add this)                     │    │
│  │  - ADMIN_PASSWORD (YOU add this)                     │    │
│  │  - CORS_ORIGINS (YOU add this)                       │    │
│  │  - etc...                                            │    │
│  │                                                      │    │
│  │  Settings Tab:                                       │    │
│  │  - Generate Domain (get your URL here)              │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  PostgreSQL (Database)                               │    │
│  │  ← YOU DON'T NEED TO CONFIGURE THIS                 │    │
│  │  Railway manages it automatically                    │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Redis (Cache)                                       │    │
│  │  ← YOU DON'T NEED TO CONFIGURE THIS                 │    │
│  │  Railway manages it automatically                    │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Common Questions

### Q: Where do I add environment variables?
**A:** In the **WEB SERVICE** (the one with your repo name), click **Variables** tab.

### Q: Do I need to configure PostgreSQL or Redis?
**A:** NO! Railway automatically manages them. Just add them to your project and Railway handles the rest.

### Q: How do I know which service is which?
**A:**
- **Web Service** = Has your repository name (e.g., "OCL_Twitter_Scraper")
- **PostgreSQL** = Says "PostgreSQL" with a database icon
- **Redis** = Says "Redis" with a Redis icon

### Q: What if I don't have a Twitter API token?
**A:** Skip the `TWITTER_BEARER_TOKEN` variable. The app will work but won't monitor Twitter.

### Q: What's a Gmail "app password"?
**A:**
1. Go to your Google Account settings
2. Security → 2-Step Verification → App passwords
3. Generate a new app password
4. Use that (NOT your regular Gmail password)

### Q: Railway says "Build failed"?
**A:** Check that:
1. `railway.json` is in your project root
2. `requirements.txt` exists and has all dependencies
3. Your code is pushed to GitHub

### Q: Where do I see logs?
**A:** Click your **Web Service** → **Deployments** tab → Click latest deployment → View logs

---

## After Railway Setup

Once you have:
- ✅ Web service deployed
- ✅ PostgreSQL added
- ✅ Redis added
- ✅ Environment variables configured
- ✅ Domain generated
- ✅ URL copied

You're ready to deploy the frontend to Netlify!

**Next:** Use the URL you got in Part 5 to configure your frontend's `.env` file, then deploy to Netlify.

---

## Troubleshooting

### Problem: "I don't see the Variables tab"
**Solution:** Make sure you clicked on the **WEB SERVICE** card, not PostgreSQL or Redis.

### Problem: "DATABASE_URL is not appearing"
**Solution:**
1. Make sure PostgreSQL is added to the same project
2. Railway auto-adds it - wait a few seconds and refresh

### Problem: "My app won't start"
**Solution:**
1. Click Web Service → Deployments → View logs
2. Common issues:
   - Missing `railway.json` file
   - Missing dependencies in `requirements.txt`
   - Python version mismatch

### Problem: "I can't generate a domain"
**Solution:**
1. Make sure deployment is successful (green checkmark)
2. Go to Settings tab → Networking section
3. Click "Generate Domain"

---

## Cost & Free Tier

**Railway Free Tier:**
- $5 credit per month
- Enough for small apps
- Includes:
  - 1 web service
  - 1 PostgreSQL database (1GB)
  - 1 Redis instance (100MB)

**When you'll need to upgrade:**
- Consistent traffic 24/7
- Larger database (>1GB)
- More than basic usage

Most hobby projects stay within free tier! 🎉

---

**Ready for the next step?** Once Railway is set up, follow the Netlify deployment guide to get your frontend live!
