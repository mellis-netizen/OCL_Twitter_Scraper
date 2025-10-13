# Frontend Not Loading Data - SOLUTION

## Problem
Frontend shows "No companies" and "No feeds" even though Railway database has all data.

## Root Cause
Deployed frontend is using `http://localhost:8000` instead of `https://ocltwitterscraper-production.up.railway.app` because the `VITE_API_URL` environment variable is not set during build.

## ✅ VERIFIED: Backend Works
```bash
curl https://ocltwitterscraper-production.up.railway.app/companies
# Returns 15 companies ✅

curl https://ocltwitterscraper-production.up.railway.app/feeds
# Returns 54 feeds ✅
```

## Solution: Set Environment Variables in Your Deployment Platform

### Option 1: AWS Amplify

1. Go to AWS Amplify Console
2. Select your app
3. Click **Environment variables** in left menu
4. Add these variables:
   ```
   VITE_API_URL = https://ocltwitterscraper-production.up.railway.app
   VITE_WS_URL = wss://ocltwitterscraper-production.up.railway.app
   ```
5. Click **Redeploy this version**

### Option 2: Vercel

1. Go to Vercel Dashboard → Your Project → Settings
2. Click **Environment Variables**
3. Add these variables for **Production**:
   ```
   VITE_API_URL = https://ocltwitterscraper-production.up.railway.app
   VITE_WS_URL = wss://ocltwitterscraper-production.up.railway.app
   ```
4. Go to **Deployments** tab
5. Click **Redeploy** on latest deployment

### Option 3: Netlify

1. Go to Netlify Dashboard → Your Site → Site settings
2. Click **Environment variables**
3. Add these variables:
   ```
   VITE_API_URL = https://ocltwitterscraper-production.up.railway.app
   VITE_WS_URL = wss://ocltwitterscraper-production.up.railway.app
   ```
4. Go to **Deploys** tab
5. Click **Trigger deploy** → **Deploy site**

## Alternative: Use .env.production File

I've created `frontend/.env.production` with the correct values.

**Commit and push it:**
```bash
git add frontend/.env.production
git commit -m "Add production environment variables"
git push origin main
```

Then your deployment platform will automatically use these values during build.

## How to Verify After Deployment

1. Open browser developer console (F12)
2. Go to **Network** tab
3. Reload your frontend
4. Look for API calls to `/companies` and `/feeds`
5. Check the **Request URL** - it should be:
   ```
   https://ocltwitterscraper-production.up.railway.app/companies
   ```
   NOT:
   ```
   http://localhost:8000/companies
   ```

## Test Locally

To test if the fix works locally:
```bash
cd frontend
npm run build
npm run preview
```

Open http://localhost:4173 and check if data loads.

## Still Not Working?

Check browser console for errors:
1. Press F12 → Console tab
2. Look for CORS errors or network failures
3. If you see CORS errors, the backend CORS settings are wrong
4. If you see 404 errors, the API URL is still wrong

## Quick Debug Commands

```bash
# Test backend API directly
curl https://ocltwitterscraper-production.up.railway.app/companies | jq 'length'
# Should return: 15

curl https://ocltwitterscraper-production.up.railway.app/feeds | jq 'length'
# Should return: 54

# Check what API URL your frontend is using (in browser console)
console.log(import.meta.env.VITE_API_URL)
# Should show: https://ocltwitterscraper-production.up.railway.app
```
