#!/usr/bin/env python3
"""
TGE Swarm Dashboard API Server
Provides REST API and WebSocket endpoints for the React dashboard
Integrates with the existing health monitor and swarm infrastructure
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import aiohttp
from aiohttp import web, WSMsgType
from aiohttp_cors import setup as cors_setup, ResourceOptions
import aiofiles
import yaml
import sys
import os

# Add the infrastructure directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'infrastructure'))

try:
    from health.health_monitor import HealthMonitor
except ImportError:
    print("Warning: Could not import HealthMonitor. Using mock data.")
    HealthMonitor = None

class DashboardAPIServer:
    """API server for the TGE Swarm Dashboard"""
    
    def __init__(self, host='localhost', port=8080):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.health_monitor = None
        self.websocket_connections = set()
        self.setup_logging()
        self.setup_routes()
        self.setup_cors()
        
        # Initialize health monitor if available
        if HealthMonitor:
            try:
                self.health_monitor = HealthMonitor()
            except Exception as e:
                self.logger.warning(f"Could not initialize HealthMonitor: {e}")
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('dashboard-api.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('DashboardAPI')
    
    def setup_cors(self):
        """Setup CORS for frontend access"""
        cors = cors_setup(self.app, defaults={
            "*": ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Add CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    def setup_routes(self):
        """Setup API routes"""
        # Health endpoints
        self.app.router.add_get('/api/health/summary', self.get_health_summary)
        self.app.router.add_get('/api/agents/status', self.get_agent_status)
        self.app.router.add_post('/api/agents/{agent_id}/{action}', self.agent_action)
        
        # Metrics endpoints
        self.app.router.add_get('/api/metrics/performance', self.get_performance_metrics)
        self.app.router.add_get('/api/system/stats', self.get_system_stats)
        
        # Logs endpoints
        self.app.router.add_get('/api/logs/recent', self.get_recent_logs)
        
        # Configuration endpoints
        self.app.router.add_get('/api/config/swarm', self.get_swarm_config)
        
        # WebSocket endpoint
        self.app.router.add_get('/ws', self.websocket_handler)
        
        # Static file serving for the React app
        self.app.router.add_static('/', path='dashboard/build', name='static')
        
        # Catch-all for React router
        self.app.router.add_get('/{path:.*}', self.serve_react_app)
    
    async def get_health_summary(self, request):
        """Get overall health summary"""
        try:
            if self.health_monitor:
                summary = self.health_monitor.get_health_summary()
                return web.json_response(summary)
            else:
                # Mock data
                mock_summary = {
                    'timestamp': datetime.now().isoformat(),
                    'overallHealth': 'healthy',
                    'components': {
                        'swarm-queen': {
                            'componentName': 'swarm-queen',
                            'overallStatus': 'healthy',
                            'checks': [],
                            'recoveryCount': 0,
                            'failureStreak': 0,
                        },
                        'agents': {
                            'componentName': 'agents',
                            'overallStatus': 'healthy',
                            'checks': [],
                            'recoveryCount': 0,
                            'failureStreak': 0,
                        },
                    },
                    'recoveryStats': {
                        'totalRecoveries': 0,
                        'successfulRecoveries': 0,
                        'recentRecoveries': 0,
                    },
                }
                return web.json_response(mock_summary)
        except Exception as e:
            self.logger.error(f"Error getting health summary: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_agent_status(self, request):
        """Get status of all agents"""
        try:
            # Mock agent data for now
            agents = [
                {
                    'id': 'scraping-efficiency-1',
                    'name': 'Scraping Efficiency Specialist',
                    'type': 'scraping-efficiency',
                    'status': 'healthy',
                    'uptime': 86400,
                    'lastSeen': datetime.now().isoformat(),
                    'version': '1.0.0',
                    'memoryUsage': 85.2,
                    'cpuUsage': 25.1,
                    'tasksCompleted': 1250,
                    'tasksActive': 3,
                    'errorRate': 0.5,
                    'responseTime': 120,
                },
                {
                    'id': 'keyword-precision-1',
                    'name': 'TGE Keyword Precision Specialist',
                    'type': 'keyword-precision',
                    'status': 'healthy',
                    'uptime': 86400,
                    'lastSeen': datetime.now().isoformat(),
                    'version': '1.0.0',
                    'memoryUsage': 72.8,
                    'cpuUsage': 18.3,
                    'tasksCompleted': 890,
                    'tasksActive': 2,
                    'errorRate': 0.2,
                    'responseTime': 95,
                },
                {
                    'id': 'api-reliability-1',
                    'name': 'API Reliability Optimizer',
                    'type': 'api-reliability',
                    'status': 'warning',
                    'uptime': 82800,
                    'lastSeen': datetime.now().isoformat(),
                    'version': '1.0.0',
                    'memoryUsage': 95.1,
                    'cpuUsage': 35.7,
                    'tasksCompleted': 2100,
                    'tasksActive': 5,
                    'errorRate': 2.1,
                    'responseTime': 180,
                },
                {
                    'id': 'performance-1',
                    'name': 'Performance Bottleneck Eliminator',
                    'type': 'performance',
                    'status': 'healthy',
                    'uptime': 86400,
                    'lastSeen': datetime.now().isoformat(),
                    'version': '1.0.0',
                    'memoryUsage': 68.4,
                    'cpuUsage': 22.1,
                    'tasksCompleted': 1580,
                    'tasksActive': 1,
                    'errorRate': 0.3,
                    'responseTime': 75,
                },
                {
                    'id': 'data-quality-1',
                    'name': 'Data Quality Enforcer',
                    'type': 'data-quality',
                    'status': 'healthy',
                    'uptime': 86400,
                    'lastSeen': datetime.now().isoformat(),
                    'version': '1.0.0',
                    'memoryUsage': 78.9,
                    'cpuUsage': 20.5,
                    'tasksCompleted': 980,
                    'tasksActive': 2,
                    'errorRate': 0.1,
                    'responseTime': 110,
                },
            ]
            return web.json_response(agents)
        except Exception as e:
            self.logger.error(f"Error getting agent status: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def agent_action(self, request):
        """Perform action on agent (start/stop/restart)"""
        try:
            agent_id = request.match_info['agent_id']
            action = request.match_info['action']
            
            self.logger.info(f"Agent action: {action} on {agent_id}")
            
            # Here you would integrate with Docker or the agent management system
            # For now, just simulate the action
            await asyncio.sleep(1)  # Simulate processing time
            
            # Broadcast update to WebSocket clients
            await self.broadcast_to_websockets({
                'type': 'agent_status',
                'data': {
                    'id': agent_id,
                    'status': 'healthy' if action == 'start' else 'warning',
                    'lastSeen': datetime.now().isoformat(),
                },
                'timestamp': datetime.now().isoformat(),
            })
            
            return web.json_response({'success': True, 'message': f'Agent {action} successful'})
        except Exception as e:
            self.logger.error(f"Error performing agent action: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_performance_metrics(self, request):
        """Get performance metrics for charts"""
        try:
            # Generate mock time series data
            now = datetime.now()
            hours = 24
            
            def generate_time_series(base_value, variance=0.2):
                return [
                    {
                        'timestamp': (now - timedelta(hours=hours-i)).isoformat(),
                        'value': base_value + (base_value * variance * (0.5 - __import__('random').random())),
                    }
                    for i in range(hours)
                ]
            
            metrics = {
                'tgeDetectionTotal': generate_time_series(25, 0.4),
                'tgeFalsePositives': generate_time_series(2, 0.8),
                'apiCallsTotal': generate_time_series(750, 0.3),
                'scrapingDuration': generate_time_series(1200, 0.5),
                'keywordMatches': generate_time_series(120, 0.6),
                'memoryUsage': generate_time_series(75, 0.2),
                'cpuUsage': generate_time_series(25, 0.4),
                'agentHealthRatio': generate_time_series(95, 0.1),
                'detectionAccuracy': generate_time_series(94, 0.05),
                'apiEfficiency': generate_time_series(0.8, 0.2),
            }
            
            return web.json_response(metrics)
        except Exception as e:
            self.logger.error(f"Error getting performance metrics: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_system_stats(self, request):
        """Get system statistics"""
        try:
            stats = {
                'uptime': 86400,
                'totalAgents': 5,
                'healthyAgents': 4,
                'totalTgeDetected': 127,
                'accuracy': 94.5,
                'apiCallsToday': 15420,
                'memoryUsagePercent': 72.3,
                'cpuUsagePercent': 28.7,
            }
            return web.json_response(stats)
        except Exception as e:
            self.logger.error(f"Error getting system stats: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_recent_logs(self, request):
        """Get recent log entries"""
        try:
            limit = int(request.query.get('limit', 100))
            
            # Generate mock log entries
            levels = ['info', 'warn', 'error', 'debug']
            components = ['swarm-queen', 'agent-scraping', 'agent-keyword', 'agent-api']
            messages = [
                'TGE detection completed successfully',
                'API rate limit approaching threshold',
                'Keyword matching optimization applied',
                'Agent health check passed',
                'Performance bottleneck detected and resolved',
                'False positive rate decreased',
                'Memory usage optimized',
                'Connection pool refreshed',
                'Data quality validation completed',
                'Cache hit ratio improved',
            ]
            
            logs = []
            for i in range(min(limit, 50)):
                logs.append({
                    'timestamp': (datetime.now() - timedelta(seconds=i*30)).isoformat(),
                    'level': __import__('random').choice(levels),
                    'component': __import__('random').choice(components),
                    'agent': __import__('random').choice(['scraping-efficiency-1', 'keyword-precision-1', None]),
                    'message': __import__('random').choice(messages),
                    'metadata': {'iteration': i} if __import__('random').random() > 0.7 else None,
                })
            
            return web.json_response(logs)
        except Exception as e:
            self.logger.error(f"Error getting recent logs: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_swarm_config(self, request):
        """Get swarm configuration"""
        try:
            # Try to load actual config
            config_path = 'safla-swarm-config.yaml'
            if os.path.exists(config_path):
                async with aiofiles.open(config_path, 'r') as f:
                    content = await f.read()
                    config = yaml.safe_load(content)
                    return web.json_response(config)
            else:
                # Mock config
                config = {
                    'name': 'TGE-Detection-Efficiency-Swarm',
                    'version': '2.0-optimized',
                    'mode': 'queen-directed',
                    'maxWorkers': 5,
                    'workers': [
                        {
                            'name': 'scraping-efficiency-specialist',
                            'role': 'primary-optimizer',
                            'priority': 'critical',
                            'focus': ['scraper-performance-tuning', 'api-rate-limit-optimization'],
                            'files': ['src/news_scraper*.py', 'src/twitter_monitor*.py'],
                            'goals': ['reduce-api-calls-by-30-percent', 'increase-scraping-speed-by-50-percent'],
                        },
                        {
                            'name': 'tge-keyword-precision-specialist',
                            'role': 'accuracy-optimizer',
                            'priority': 'critical',
                            'focus': ['keyword-matching-precision', 'false-positive-elimination'],
                            'files': ['config.py', 'src/news_scraper*.py'],
                            'goals': ['achieve-95-percent-precision', 'reduce-false-positives-by-50-percent'],
                        },
                    ],
                    'coordination': {
                        'syncInterval': '90s',
                        'crossPollination': True,
                        'adaptiveFocus': True,
                    },
                    'optimization': {
                        'primaryGoal': 'maximize-tge-detection-efficiency',
                        'targetAreas': ['scraping-speed', 'tge-detection-accuracy'],
                        'successMetrics': ['tge-detection-precision-above-95-percent'],
                    },
                }
                return web.json_response(config)
        except Exception as e:
            self.logger.error(f"Error getting swarm config: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def websocket_handler(self, request):
        """Handle WebSocket connections"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websocket_connections.add(ws)
        self.logger.info(f"WebSocket connected. Total connections: {len(self.websocket_connections)}")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self.handle_websocket_message(ws, data)
                    except json.JSONDecodeError:
                        await ws.send_str(json.dumps({
                            'type': 'error',
                            'message': 'Invalid JSON format'
                        }))
                elif msg.type == WSMsgType.ERROR:
                    self.logger.error(f'WebSocket error: {ws.exception()}')
        except Exception as e:
            self.logger.error(f"WebSocket error: {e}")
        finally:
            self.websocket_connections.discard(ws)
            self.logger.info(f"WebSocket disconnected. Total connections: {len(self.websocket_connections)}")
        
        return ws
    
    async def handle_websocket_message(self, ws, data):
        """Handle incoming WebSocket messages"""
        msg_type = data.get('type')
        
        if msg_type == 'ping':
            await ws.send_str(json.dumps({
                'type': 'pong',
                'timestamp': datetime.now().isoformat()
            }))
        else:
            self.logger.info(f"Unknown WebSocket message type: {msg_type}")
    
    async def broadcast_to_websockets(self, message):
        """Broadcast message to all WebSocket connections"""
        if not self.websocket_connections:
            return
        
        message_str = json.dumps(message)
        disconnected = set()
        
        for ws in self.websocket_connections:
            try:
                await ws.send_str(message_str)
            except Exception as e:
                self.logger.error(f"Error sending to WebSocket: {e}")
                disconnected.add(ws)
        
        # Remove disconnected clients
        self.websocket_connections -= disconnected
    
    async def serve_react_app(self, request):
        """Serve React app for client-side routing"""
        try:
            build_path = 'dashboard/build'
            index_path = os.path.join(build_path, 'index.html')
            
            if os.path.exists(index_path):
                return web.FileResponse(index_path)
            else:
                return web.Response(
                    text="Dashboard not built. Run 'npm run build' in the dashboard directory.",
                    status=404
                )
        except Exception as e:
            self.logger.error(f"Error serving React app: {e}")
            return web.Response(text="Error serving dashboard", status=500)
    
    async def start_background_tasks(self):
        """Start background tasks for real-time updates"""
        asyncio.create_task(self.periodic_health_broadcast())
        asyncio.create_task(self.periodic_metrics_broadcast())
    
    async def periodic_health_broadcast(self):
        """Periodically broadcast health updates"""
        while True:
            try:
                await asyncio.sleep(30)  # Every 30 seconds
                
                if self.websocket_connections:
                    # Simulate health update
                    health_update = {
                        'type': 'health_update',
                        'data': {
                            'timestamp': datetime.now().isoformat(),
                            'overallHealth': 'healthy',
                            'components': {},
                        },
                        'timestamp': datetime.now().isoformat(),
                    }
                    await self.broadcast_to_websockets(health_update)
            except Exception as e:
                self.logger.error(f"Error in health broadcast: {e}")
    
    async def periodic_metrics_broadcast(self):
        """Periodically broadcast metrics updates"""
        while True:
            try:
                await asyncio.sleep(60)  # Every minute
                
                if self.websocket_connections:
                    # Simulate metrics update
                    metrics_update = {
                        'type': 'metrics_update',
                        'data': {
                            'tgeDetectionTotal': [{
                                'timestamp': datetime.now().isoformat(),
                                'value': 25 + (5 * __import__('random').random()),
                            }],
                        },
                        'timestamp': datetime.now().isoformat(),
                    }
                    await self.broadcast_to_websockets(metrics_update)
            except Exception as e:
                self.logger.error(f"Error in metrics broadcast: {e}")
    
    async def start_server(self):
        """Start the API server"""
        self.logger.info(f"Starting TGE Swarm Dashboard API Server on {self.host}:{self.port}")
        
        # Start background tasks
        await self.start_background_tasks()
        
        # Start the web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        self.logger.info(f"Dashboard API Server running at http://{self.host}:{self.port}")
        self.logger.info(f"WebSocket endpoint: ws://{self.host}:{self.port}/ws")
        
        return runner

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='TGE Swarm Dashboard API Server')
    parser.add_argument('--host', default='localhost', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    
    args = parser.parse_args()
    
    server = DashboardAPIServer(host=args.host, port=args.port)
    runner = await server.start_server()
    
    try:
        # Keep the server running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        await runner.cleanup()

if __name__ == '__main__':
    asyncio.run(main())