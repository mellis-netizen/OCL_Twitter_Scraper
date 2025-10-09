# TGE Swarm Dashboard

A real-time monitoring and control dashboard for the TGE Swarm Optimization System. This React-based dashboard provides comprehensive monitoring, performance analytics, and agent management capabilities.

## Features

### 🎯 Real-time Monitoring
- **Live Agent Status**: Monitor all 5 specialized agents in real-time
- **WebSocket Integration**: Real-time updates from the health monitoring system
- **System Health Overview**: Comprehensive system status at a glance

### 📊 Performance Analytics
- **TGE Detection Metrics**: Track detection accuracy, false positives, and efficiency
- **System Performance**: Monitor CPU, memory, and agent health trends
- **API Efficiency**: Visualize API call patterns and response times
- **Interactive Charts**: Powered by Recharts with customizable time ranges

### 🎮 Agent Control
- **Agent Management**: Start, stop, and restart agents remotely
- **Configuration Viewer**: View detailed agent configurations and goals
- **Status Indicators**: Visual health indicators with color-coded status

### 📝 Log Management
- **Live Log Viewer**: Real-time log streaming with filtering capabilities
- **Advanced Search**: Filter by level, component, agent, and custom search terms
- **Export Functionality**: Download filtered logs for analysis

### ⚙️ Configuration Management
- **Settings Panel**: Configurable dashboard preferences and monitoring settings
- **Alert Rules**: Create and manage custom alert conditions
- **Theme Support**: Dark/light theme toggle

### 📱 Mobile Responsive
- **Responsive Design**: Optimized for desktop, tablet, and mobile devices
- **Touch-friendly**: Intuitive touch interactions for mobile users

## Architecture

### Frontend Stack
- **React 18** with TypeScript for type safety
- **Material-UI (MUI)** for consistent design system
- **Recharts** for data visualization
- **Socket.IO Client** for real-time WebSocket communication
- **React Router** for navigation

### Data Flow
- **WebSocket Connection**: Real-time data from health monitor
- **REST API Integration**: Fetches initial data and handles agent control
- **Context-based State Management**: Efficient state management with React Context

### Component Structure
```
src/
├── components/
│   ├── Layout/           # Main layout and navigation
│   └── Dashboard/        # Dashboard-specific components
├── contexts/             # React contexts for state management
├── pages/               # Main application pages
├── types/               # TypeScript type definitions
└── App.tsx              # Main application component
```

## Quick Start

### Prerequisites
- Node.js 16+ and npm/yarn
- TGE Swarm monitoring infrastructure running
- Health monitor API accessible

### Installation

1. **Install dependencies**:
   ```bash
   cd dashboard
   npm install
   ```

2. **Configure environment** (optional):
   ```bash
   # Create .env file
   REACT_APP_API_URL=http://localhost:8080/api
   REACT_APP_WS_URL=ws://localhost:8080
   ```

3. **Start development server**:
   ```bash
   npm start
   ```

4. **Access dashboard**: Open [http://localhost:3000](http://localhost:3000)

### Production Build

```bash
# Build for production
npm run build

# Serve static files
npx serve -s build -l 3000
```

## Integration with Monitoring Infrastructure

### Required Backend Services

1. **Health Monitor API** (`localhost:8080/api`):
   - `GET /health/summary` - Overall health status
   - `GET /agents/status` - Agent status information
   - `GET /metrics/performance` - Performance metrics
   - `POST /agents/{id}/{action}` - Agent control actions

2. **WebSocket Server** (`localhost:8080`):
   - Real-time health updates
   - Agent status changes
   - Log streaming
   - Metrics updates

### API Endpoints

```typescript
// Health Summary
GET /api/health/summary
Response: HealthSummary

// Agent Status
GET /api/agents/status
Response: AgentStatus[]

// Performance Metrics
GET /api/metrics/performance
Response: PerformanceMetrics

// Agent Control
POST /api/agents/{agentId}/start
POST /api/agents/{agentId}/stop
POST /api/agents/{agentId}/restart

// System Stats
GET /api/system/stats
Response: SystemStats

// Recent Logs
GET /api/logs/recent?limit=100
Response: LogEntry[]

// Swarm Configuration
GET /api/config/swarm
Response: SwarmConfig
```

### WebSocket Events

```typescript
// Incoming events
'health_update'    // Health status changes
'agent_status'     // Agent status updates
'metrics_update'   // Performance metrics
'log_entry'        // New log entries
'alert'           // System alerts

// Outgoing events
'message'         // General messages to server
```

## Dashboard Pages

### 1. Dashboard (/)
- System overview with key metrics
- Agent status grid with controls
- Real-time performance charts
- Recent activity feed

### 2. Agent Details (/agent/:id)
- Detailed agent information
- Performance history
- Configuration details
- Agent-specific logs

### 3. Performance Metrics (/metrics)
- Comprehensive performance analytics
- TGE detection trends
- System health monitoring
- API efficiency analysis

### 4. Log Viewer (/logs)
- Real-time log streaming
- Advanced filtering and search
- Export functionality
- Log level management

### 5. Settings (/settings)
- Dashboard preferences
- Monitoring configuration
- Agent settings
- Alert rule management

## Customization

### Theme Configuration
The dashboard uses a dark theme by default but supports customization:

```typescript
// src/index.tsx
const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#4fc3f7' },
    secondary: { main: '#81c784' },
    // ... customize colors
  },
});
```

### Adding New Metrics
To add new performance metrics:

1. Update `types/index.ts` with new metric types
2. Modify `HealthDataContext.tsx` to fetch new data
3. Create chart components in `components/Dashboard/`
4. Add to dashboard pages

### Custom Alert Rules
Alert rules are configurable through the Settings page:
- Define custom conditions
- Set thresholds and severity levels
- Enable/disable rules dynamically

## Development

### Available Scripts

```bash
npm start          # Development server
npm run build      # Production build
npm test           # Run tests
npm run lint       # ESLint checking
npm run lint:fix   # Fix ESLint issues
```

### Code Structure

- **TypeScript**: Full type safety with strict mode
- **ESLint**: Code quality and consistency
- **Material-UI**: Component library for consistent design
- **Context API**: State management for real-time data

### Adding New Features

1. **Create types** in `src/types/index.ts`
2. **Add context** if needed in `src/contexts/`
3. **Build components** in `src/components/`
4. **Create pages** in `src/pages/`
5. **Update routing** in `src/App.tsx`

## Monitoring Integration

### Health Monitor Integration
The dashboard integrates with the existing health monitor (`infrastructure/health/health_monitor.py`):

- Fetches health data via REST API
- Receives real-time updates via WebSocket
- Displays component health status
- Shows recovery statistics

### Prometheus Metrics
Performance metrics are sourced from Prometheus:

- TGE detection metrics
- System resource usage
- API call statistics
- Agent performance data

### Docker Integration
Agent control features integrate with Docker:

- Start/stop/restart containers
- Monitor container health
- Resource usage tracking

## Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**:
   - Check if health monitor WebSocket server is running
   - Verify `REACT_APP_WS_URL` environment variable
   - Check browser console for connection errors

2. **API Endpoints Not Found**:
   - Ensure health monitor API is accessible
   - Verify `REACT_APP_API_URL` configuration
   - Check CORS settings on backend

3. **No Data Displayed**:
   - Dashboard shows mock data if API is unavailable
   - Check browser network tab for failed requests
   - Verify backend services are running

### Debug Mode
Enable debug logging by setting localStorage:

```javascript
localStorage.setItem('debug', 'true');
```

## Performance Optimization

### Optimization Features
- **Virtualized Lists**: Efficient rendering of large log lists
- **Memoized Components**: Prevent unnecessary re-renders
- **Context Optimization**: Separate contexts for different data types
- **Lazy Loading**: Pages loaded on demand

### Memory Management
- **Connection Cleanup**: WebSocket connections properly closed
- **Event Listeners**: Removed when components unmount
- **Data Retention**: Configurable limits on stored metrics

## Security Considerations

- **API Authentication**: Ready for token-based authentication
- **CORS Configuration**: Backend should properly configure CORS
- **Input Validation**: All user inputs validated and sanitized
- **XSS Protection**: Material-UI components provide built-in protection

## Future Enhancements

### Planned Features
- **Historical Data Analysis**: Long-term trend analysis
- **Custom Dashboards**: User-configurable dashboard layouts
- **Alerting Integration**: Email/Slack notifications
- **Performance Optimization**: Advanced caching strategies
- **Multi-tenancy**: Support for multiple swarm instances

### Extension Points
- **Plugin System**: Framework for custom components
- **Custom Metrics**: User-defined performance metrics
- **Integration APIs**: Hooks for external systems
- **Theme Extensions**: Custom theme development

## License

This dashboard is part of the TGE Swarm Optimization System and follows the same licensing terms as the parent project.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review browser console for errors
3. Verify backend service status
4. Check network connectivity to monitoring services