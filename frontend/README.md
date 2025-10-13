# TGE Monitor Frontend

Production-grade React frontend for the TGE Monitor system - real-time cryptocurrency Token Generation Event monitoring.

## Features

- **Real-time Alerts** - WebSocket-based live alert notifications
- **Company Management** - Add and monitor cryptocurrency companies
- **Feed Management** - Configure RSS/Atom news sources
- **Manual Controls** - Trigger scraping and email summaries on-demand
- **Statistics Dashboard** - System metrics and health monitoring
- **Responsive Design** - Works on desktop, tablet, and mobile devices

## Tech Stack

- **React 18** - Modern React with hooks
- **TypeScript** - Type-safe development
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first styling
- **TanStack Query** - Data fetching and caching
- **React Hook Form** - Form validation
- **Zod** - Schema validation
- **Axios** - HTTP client
- **date-fns** - Date formatting

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend API running on port 8000

### Installation

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Update .env with your API URL
nano .env
```

### Development

```bash
# Start development server
npm run dev

# Open browser to http://localhost:5173
```

### Build for Production

```bash
# Create production build
npm run build

# Preview production build
npm run preview
```

### Linting

```bash
# Run ESLint
npm run lint
```

## Project Structure

```
frontend/
├── src/
│   ├── components/     # React components
│   │   ├── AlertDashboard.tsx
│   │   ├── CompanyManager.tsx
│   │   ├── Dashboard.tsx
│   │   ├── FeedManager.tsx
│   │   ├── Login.tsx
│   │   └── ManualControls.tsx
│   ├── hooks/          # Custom React hooks
│   │   ├── useAlerts.ts
│   │   └── useAuth.tsx
│   ├── services/       # API and WebSocket clients
│   │   ├── api.ts
│   │   └── websocket.ts
│   ├── types/          # TypeScript type definitions
│   │   └── api.ts
│   ├── utils/          # Utility functions
│   │   ├── helpers.ts
│   │   └── validation.ts
│   ├── styles/         # CSS files
│   │   └── index.css
│   ├── App.tsx         # Main application component
│   └── main.tsx        # Application entry point
├── public/             # Static assets
├── index.html          # HTML entry point
├── package.json        # Dependencies and scripts
├── tailwind.config.js  # Tailwind CSS configuration
├── tsconfig.json       # TypeScript configuration
├── vite.config.ts      # Vite configuration
└── README.md           # This file
```

## Features Detail

### Dashboard
- System health overview
- Real-time statistics
- Feed health monitoring
- System resource metrics
- Quick action shortcuts

### Alert Management
- Real-time alert feed
- Advanced filtering (source, urgency, confidence)
- Alert details with company information
- Source links to original content
- Keyword highlighting

### Company Management
- Add/edit/delete companies
- Set monitoring priorities
- Configure token symbols and aliases
- Twitter handle integration
- Exclusion keywords

### Feed Management
- RSS/Atom feed configuration
- Feed health monitoring
- Success/failure rate tracking
- Priority settings
- Enable/disable feeds

### Manual Controls
- Trigger immediate scraping cycles
- Send email summaries on-demand
- Real-time operation status
- Detailed operation descriptions

## API Integration

The frontend communicates with the FastAPI backend through:

- **REST API** - Standard CRUD operations at `http://localhost:8000/api/v1`
- **WebSocket** - Real-time alerts at `ws://localhost:8000/ws`

### Authentication

Uses JWT token-based authentication:
1. Login via `/api/v1/auth/login`
2. Token stored in localStorage
3. Automatic token refresh on API calls
4. Auto-logout on 401 responses

### WebSocket

Real-time features powered by WebSocket:
- Live alert notifications
- System status updates
- Automatic reconnection
- Ping/pong keep-alive

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `http://localhost:8000` |
| `VITE_WS_URL` | WebSocket URL | `ws://localhost:8000` |
| `VITE_ENABLE_ANALYTICS` | Enable analytics | `false` |
| `VITE_ENABLE_DEBUG` | Enable debug mode | `false` |

## Deployment

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    root /var/www/tge-monitor/frontend/dist;
    index index.html;

    # Serve static files
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Proxy WebSocket connections
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

### Docker Deployment

```dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Performance Optimization

- Code splitting with React.lazy
- Image optimization
- Tree shaking
- Minification
- Gzip compression
- CDN for static assets
- Service worker for offline support

## Browser Support

- Chrome/Edge (last 2 versions)
- Firefox (last 2 versions)
- Safari (last 2 versions)
- iOS Safari (last 2 versions)
- Chrome Android (last 2 versions)

## Troubleshooting

### API Connection Issues

```bash
# Check if backend is running
curl http://localhost:8000/health

# Verify CORS settings in backend
```

### WebSocket Connection Fails

```bash
# Check WebSocket endpoint
wscat -c ws://localhost:8000/ws?token=YOUR_TOKEN

# Verify firewall rules
```

### Build Errors

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf node_modules/.vite
```

## Contributing

1. Follow TypeScript strict mode
2. Use ESLint and Prettier
3. Write component tests
4. Update documentation
5. Submit pull requests

## License

MIT License - see [LICENSE.md](../LICENSE.md)

## Support

- GitHub Issues: [Report bugs](https://github.com/yourusername/tge-monitor/issues)
- Documentation: [Full docs](https://docs.yourdomain.com)
- Email: support@yourdomain.com
