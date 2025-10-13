# Frontend Quick Start Guide

## Overview

The TGE Monitor frontend is now fully built and ready to use! This is a production-grade React application for monitoring cryptocurrency Token Generation Events in real-time.

## What's Included

### ✅ Core Features

1. **Authentication System**
   - JWT token-based authentication
   - Login/logout functionality
   - Automatic session management

2. **Dashboard Overview**
   - System health monitoring
   - Real-time statistics
   - Quick action buttons
   - Resource usage metrics

3. **Alert Management**
   - Real-time WebSocket alerts
   - Advanced filtering
   - Confidence scoring
   - Urgency level indicators

4. **Company Management**
   - Add/edit/delete companies
   - Token symbol tracking
   - Priority levels
   - Twitter integration

5. **Feed Management**
   - RSS/Atom feed configuration
   - Success rate monitoring
   - Feed health tracking
   - Priority settings

6. **Manual Controls**
   - Trigger immediate scraping
   - Send email summaries
   - Real-time operation status

### 🎨 Technical Stack

- **React 18** with TypeScript
- **Vite** for blazing-fast builds
- **Tailwind CSS** for responsive styling
- **TanStack Query** for data fetching
- **React Hook Form** + **Zod** for forms
- **WebSocket** for real-time updates

## Getting Started

### 1. Start the Backend

First, ensure the FastAPI backend is running:

```bash
# In the project root
python -m uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

### 2. Start the Frontend

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (already done)
npm install

# Start development server
npm run dev
```

The app will open at **http://localhost:5173**

### 3. Login

Use the default credentials:
- **Username:** `admin`
- **Password:** `adminpassword`

(Configure in backend `.env` file)

## Available Scripts

```bash
# Development server with hot reload
npm run dev

# Production build
npm run build

# Preview production build
npm run preview

# Run linter
npm run lint
```

## Environment Configuration

Edit `frontend/.env` to configure:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

For production, update these URLs to your deployed backend.

## Project Structure

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── AlertDashboard.tsx    # Alerts view with filters
│   │   ├── CompanyManager.tsx    # Company CRUD operations
│   │   ├── Dashboard.tsx         # Overview & statistics
│   │   ├── FeedManager.tsx       # RSS feed management
│   │   ├── Login.tsx             # Authentication
│   │   └── ManualControls.tsx    # Manual triggers
│   ├── hooks/              # Custom React hooks
│   │   ├── useAlerts.ts         # Alert fetching + WebSocket
│   │   └── useAuth.tsx          # Authentication context
│   ├── services/           # API clients
│   │   ├── api.ts              # REST API client
│   │   └── websocket.ts        # WebSocket client
│   ├── types/              # TypeScript definitions
│   │   └── api.ts              # API type definitions
│   ├── utils/              # Utility functions
│   │   ├── helpers.ts          # Helper functions
│   │   └── validation.ts       # Zod schemas
│   ├── styles/             # CSS files
│   │   └── index.css          # Global styles
│   ├── App.tsx             # Main app component
│   ├── main.tsx            # Entry point
│   └── vite-env.d.ts       # Vite type definitions
├── dist/                   # Production build output
├── index.html              # HTML entry point
├── package.json            # Dependencies
├── vite.config.ts          # Vite configuration
└── tailwind.config.js      # Tailwind configuration
```

## Features Walkthrough

### 📊 Dashboard
- View system status at a glance
- Monitor active feeds and companies
- Track alert statistics (24h, 7d)
- Check system resource usage

### 🚨 Alerts
- Real-time notifications via WebSocket
- Filter by source, urgency, confidence
- View detailed alert information
- Access source links directly

### 🏢 Companies
- Add companies to monitor
- Set priority levels (HIGH/MEDIUM/LOW)
- Configure token symbols
- Add Twitter handles
- Set exclusion keywords

### 📰 Feeds
- Add RSS/Atom news feeds
- Monitor feed health
- Track success rates
- Enable/disable feeds

### ⚙️ Controls
- Manually trigger scraping cycles
- Send email summaries
- View operation status

## Production Deployment

### Build for Production

```bash
cd frontend
npm run build
```

The optimized build will be in `frontend/dist/`

### Deploy with Nginx

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    root /var/www/tge-monitor/frontend/dist;
    index index.html;

    # Frontend routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Proxy WebSocket
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Environment Variables for Production

Update `frontend/.env`:

```env
VITE_API_URL=https://api.yourdomain.com
VITE_WS_URL=wss://api.yourdomain.com
```

Then rebuild:

```bash
npm run build
```

## Troubleshooting

### Frontend won't start

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

### API connection fails

1. Check backend is running on port 8000
2. Verify `VITE_API_URL` in `.env`
3. Check CORS settings in backend

### WebSocket disconnects

1. Check `VITE_WS_URL` configuration
2. Verify JWT token is valid
3. Check browser console for errors

### Build fails

```bash
# Check TypeScript errors
npx tsc --noEmit

# Run linter
npm run lint
```

## Next Steps

1. **Customize Styling** - Edit `tailwind.config.js` and CSS files
2. **Add More Features** - Extend components and hooks
3. **Implement Testing** - Add Jest/Vitest tests
4. **Set up CI/CD** - Automate builds and deployments
5. **Enable Analytics** - Add Google Analytics or similar

## Support

- **Documentation:** See `frontend/README.md` for detailed docs
- **API Docs:** http://localhost:8000/docs (when backend is running)
- **GitHub Issues:** Report bugs or request features

## Performance Tips

- Use production build for deployment
- Enable Gzip compression on server
- Configure CDN for static assets
- Implement code splitting for large apps
- Use React.lazy() for route-based splitting

---

**Built with ❤️ using React, TypeScript, and Vite**

The frontend is fully functional and production-ready! 🚀
