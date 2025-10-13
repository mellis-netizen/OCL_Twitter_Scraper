# 🚀 Quick Deploy Guide - Get Your App Live in 15 Minutes!

This guide will help you deploy both the backend and frontend quickly using free tiers.

## Prerequisites

- GitHub account
- Railway.app account (for backend)
- Netlify account (for frontend)
- Twitter API Bearer Token (optional)

---

## Step 1: Deploy Backend to Railway (5 minutes)

### A. Sign Up & Connect GitHub

1. Go to [railway.app](https://railway.app) and sign up with GitHub
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your `OCL_Twitter_Scraper` repository

### B. Add Database Services

1. In your Railway project, click **"+ New"**
2. Select **"Database"** → **"PostgreSQL"**
3. Click **"+ New"** again
4. Select **"Database"** → **"Redis"**

### C. Configure Environment Variables

**Important:** You now have 3 services in Railway:
1. **Your WEB SERVICE** (FastAPI app) - has your repo name
2. **PostgreSQL** (database) - managed automatically
3. **Redis** (cache) - managed automatically

**Click on YOUR WEB SERVICE** (the one with your repository name, NOT PostgreSQL or Redis!)

Then click the **"Variables"** tab and add these variables:

⚠️ **Note:** Railway already added `DATABASE_URL` and `REDIS_URL` automatically - don't delete them!

**Click "+ New Variable" and add each of these:**

```bash
# Required Variables
SECRET_KEY=<click "Generate Random String" or use: openssl rand -hex 32>
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<choose a strong password>

# Twitter API (optional - for Twitter monitoring)
TWITTER_BEARER_TOKEN=<your-twitter-token>

# Email (optional - for email alerts)
EMAIL_ENABLED=true
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=<your-gmail-app-password>
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587

# CORS (we'll update this after Netlify deployment)
CORS_ORIGINS=*
```

💡 **See `docs/RAILWAY_SETUP_DETAILED.md` for step-by-step screenshots and detailed explanations!**

### D. Wait for Deployment

Railway will automatically deploy. Wait for the green checkmark.

### E. Get Your API URL

1. **Make sure you're on YOUR WEB SERVICE** (not PostgreSQL or Redis)
2. Click the **"Settings"** tab
3. Scroll down to **"Networking"** section
4. Under **"Domains"**, click **"Generate Domain"** button
5. Railway creates a URL like: `https://your-app-production-xxxx.up.railway.app`
6. **Copy this URL!**

**This is your:**
- `VITE_API_URL` = `https://your-app.up.railway.app`
- `VITE_WS_URL` = `wss://your-app.up.railway.app` (same URL, just wss instead of https)

**Save this URL! You'll need it for the frontend.**

### F. Verify It Works

Open in browser:
- Health check: `https://your-app.up.railway.app/health`
- API docs: `https://your-app.up.railway.app/docs`

You should see JSON/documentation pages. If you do, backend is live! ✅

---

## Step 2: Deploy Frontend to Netlify (5 minutes)

### A. Prepare Frontend

1. **Update environment variables** in `frontend/.env`:
   ```env
   VITE_API_URL=https://your-app.up.railway.app
   VITE_WS_URL=wss://your-app.up.railway.app
   ```
   ⚠️ Replace with YOUR Railway URL from Step 1E!

2. **Commit changes** (if not already committed):
   ```bash
   git add frontend/.env frontend/netlify.toml
   git commit -m "Configure for deployment"
   git push origin main
   ```

### B. Deploy to Netlify

1. Go to [netlify.com](https://netlify.com) and sign up with GitHub
2. Click **"Add new site"** → **"Import an existing project"**
3. Choose **"Deploy with GitHub"**
4. Select your `OCL_Twitter_Scraper` repository
5. Configure build settings:
   ```
   Base directory:    frontend
   Build command:     npm run build
   Publish directory: frontend/dist
   ```

### C. Add Environment Variables in Netlify

Before deploying, add environment variables:

1. Click **"Site settings"** → **"Environment variables"**
2. Add these variables:
   ```
   VITE_API_URL    = https://your-app.up.railway.app
   VITE_WS_URL     = wss://your-app.up.railway.app
   ```
   ⚠️ Use YOUR Railway URL!

3. Click **"Deploy site"**

### D. Get Your Frontend URL

After deployment completes, you'll see:
```
https://random-name-12345.netlify.app
```

**Save this URL!**

---

## Step 3: Update CORS Settings (2 minutes)

Now that you have your Netlify URL, update the backend CORS settings:

1. Go back to **Railway**
2. Click on your web service
3. Go to **"Variables"**
4. Update `CORS_ORIGINS`:
   ```
   CORS_ORIGINS=https://random-name-12345.netlify.app
   ```
   ⚠️ Use YOUR Netlify URL!

5. Railway will automatically redeploy

---

## Step 4: Test Your Deployment (3 minutes)

### A. Access Your App

1. Open your Netlify URL: `https://random-name-12345.netlify.app`
2. You should see the login page

### B. Login

Use the credentials you set in Railway:
- **Username:** `admin`
- **Password:** (the ADMIN_PASSWORD you set)

### C. Verify Everything Works

1. **Dashboard** - Should show system statistics
2. **WebSocket** - Sidebar should show "WebSocket: Live" (green dot)
3. **Add a Company** - Go to Companies → Add Company
4. **Add a Feed** - Go to Feeds → Add Feed
5. **Check Alerts** - Go to Alerts → Should load without errors

---

## 🎉 You're Live!

Your TGE Monitor is now deployed and accessible worldwide!

**Your URLs:**
- 🌐 **Frontend:** `https://your-app.netlify.app`
- 🔧 **Backend API:** `https://your-app.up.railway.app`
- 📚 **API Docs:** `https://your-app.up.railway.app/docs`

---

## Optional: Custom Domain

### For Frontend (Netlify)

1. Go to **Site settings** → **Domain management**
2. Click **"Add custom domain"**
3. Follow DNS configuration instructions
4. Example: `tge-monitor.yourdomain.com`

### For Backend (Railway)

1. Go to your service → **Settings** → **Domains**
2. Click **"Custom Domain"**
3. Add your domain (e.g., `api.yourdomain.com`)
4. Update your DNS with the CNAME record

**Don't forget to update CORS_ORIGINS in Railway after adding custom domain!**

---

## Troubleshooting

### ❌ "CORS Error" in browser console

**Solution:** Make sure CORS_ORIGINS in Railway includes your Netlify URL

### ❌ "WebSocket Disconnected"

**Solution:** Verify VITE_WS_URL uses `wss://` (not `ws://`)

### ❌ "Login Failed"

**Solution:** Check ADMIN_USERNAME and ADMIN_PASSWORD in Railway match what you're entering

### ❌ "API Connection Failed"

**Solution:**
1. Check Railway deployment is successful (green checkmark)
2. Visit `https://your-app.up.railway.app/health` - should return JSON
3. Verify VITE_API_URL in Netlify environment variables

### ❌ Build fails on Netlify

**Solution:**
1. Check build logs in Netlify dashboard
2. Ensure `netlify.toml` is committed
3. Verify Node version is 18+

---

## Free Tier Limitations

### Railway
- **$5 credit/month** (usually enough for small apps)
- Services sleep after inactivity
- 1GB PostgreSQL storage
- 100MB Redis storage

### Netlify
- **100GB bandwidth/month**
- 300 build minutes/month
- Unlimited sites
- No sleeping (always online!)

**Combined: Perfect for personal projects and MVPs! 🎉**

---

## Upgrade When Needed

### When to upgrade Railway?
- Your app gets consistent traffic
- You need more database storage
- You want guaranteed uptime

### When to upgrade Netlify?
- You exceed 100GB bandwidth
- You need team collaboration features
- You want advanced deployment features

---

## What's Next?

1. ✅ **Add companies to monitor**
2. ✅ **Configure RSS feeds**
3. ✅ **Set up Twitter API** (if you haven't)
4. ✅ **Test alert generation**
5. ✅ **Share your app with friends!**

---

## Cost Summary

**Starting Out (Free Tier):**
- Backend (Railway): $0 (with $5 free credit)
- Frontend (Netlify): $0
- Database & Redis: $0 (included in Railway)
- SSL Certificates: $0 (automatic)
- **Total: $0/month** 💰

**Small Production App:**
- Railway Pro: $5-10/month
- Netlify Pro: $19/month (optional)
- **Total: ~$5-30/month**

---

## Support

- **Deployment Issues:** Check Railway/Netlify status pages
- **App Issues:** Check browser console and Railway logs
- **API Docs:** Visit `https://your-app.up.railway.app/docs`

---

**Happy Deploying! 🚀**

Your TGE Monitor is now live and ready to track cryptocurrency token generation events!
