#!/usr/bin/env python3
"""
Enhanced WebSocket Manager for TGE Swarm Real-time Dashboard Updates
Provides real-time communication between backend services and dashboard
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import weakref
from aiohttp import web, WSMsgType, WSServer
import aiohttp_cors

from message_queue import MessageQueue, SwarmMessage, MessageType, Priority


class UpdateType(Enum):
    """Types of real-time updates"""
    AGENT_STATUS = "agent_status"
    TASK_UPDATE = "task_update"
    METRICS = "metrics"
    HEALTH_STATUS = "health_status"
    OPTIMIZATION_RESULT = "optimization_result"
    SYSTEM_ALERT = "system_alert"
    COORDINATION_EVENT = "coordination_event"
    PERFORMANCE_DATA = "performance_data"


class SubscriptionType(Enum):
    """Subscription types for clients"""
    ALL = "all"
    AGENTS_ONLY = "agents_only"
    METRICS_ONLY = "metrics_only"
    ALERTS_ONLY = "alerts_only"
    TASKS_ONLY = "tasks_only"


@dataclass
class WebSocketClient:
    """WebSocket client connection"""
    id: str
    websocket: WSServer
    subscriptions: Set[SubscriptionType]
    connected_at: datetime
    last_ping: datetime
    client_info: Dict[str, Any]


@dataclass
class RealTimeUpdate:
    """Real-time update message"""
    id: str
    type: UpdateType
    timestamp: datetime
    data: Dict[str, Any]
    target_clients: Optional[List[str]] = None  # None means broadcast to all
    expires_at: Optional[datetime] = None


class WebSocketManager:
    """Enhanced WebSocket manager for real-time dashboard updates"""
    
    def __init__(self, message_queue: MessageQueue = None):
        self.message_queue = message_queue
        self.clients: Dict[str, WebSocketClient] = {}
        self.update_queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        
        # Subscription filters
        self.subscription_filters = {
            SubscriptionType.ALL: lambda update: True,
            SubscriptionType.AGENTS_ONLY: lambda update: update.type in [
                UpdateType.AGENT_STATUS, UpdateType.COORDINATION_EVENT
            ],
            SubscriptionType.METRICS_ONLY: lambda update: update.type in [
                UpdateType.METRICS, UpdateType.PERFORMANCE_DATA
            ],
            SubscriptionType.ALERTS_ONLY: lambda update: update.type in [
                UpdateType.SYSTEM_ALERT, UpdateType.HEALTH_STATUS
            ],
            SubscriptionType.TASKS_ONLY: lambda update: update.type in [
                UpdateType.TASK_UPDATE, UpdateType.OPTIMIZATION_RESULT
            ]
        }
        
        # Performance tracking
        self.websocket_metrics = {
            'total_connections': 0,
            'active_connections': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'disconnections': 0,
            'errors': 0
        }
        
        # Rate limiting
        self.client_rate_limits: Dict[str, List[datetime]] = {}
        self.rate_limit_window = 60  # seconds
        self.rate_limit_max_messages = 100  # per window
        
        # Update batching for performance
        self.update_batch: List[RealTimeUpdate] = []
        self.batch_size = 10
        self.batch_timeout = 0.5  # seconds
        
        self.setup_logging()
    
    def setup_logging(self):
        """Setup WebSocket manager logging"""
        self.logger = logging.getLogger("WebSocketManager")
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    async def initialize(self):
        """Initialize WebSocket manager"""
        if self.message_queue:
            # Subscribe to relevant message types
            await self.message_queue.subscribe_to_broadcast(self._handle_backend_message)
        
        # Start background tasks
        self.running = True
        asyncio.create_task(self._update_broadcaster())
        asyncio.create_task(self._health_checker())
        asyncio.create_task(self._metrics_reporter())
        asyncio.create_task(self._update_batcher())
        
        self.logger.info("WebSocket manager initialized")
    
    async def handle_websocket_connection(self, request):
        """Handle new WebSocket connection"""
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)
        
        # Create client record
        client_id = str(uuid.uuid4())
        client = WebSocketClient(
            id=client_id,
            websocket=ws,
            subscriptions={SubscriptionType.ALL},  # Default to all updates
            connected_at=datetime.now(),
            last_ping=datetime.now(),
            client_info={
                'user_agent': request.headers.get('User-Agent', ''),
                'remote_addr': request.remote,
                'query_params': dict(request.query)
            }
        )
        
        self.clients[client_id] = client
        self.websocket_metrics['total_connections'] += 1
        self.websocket_metrics['active_connections'] += 1
        
        self.logger.info(f"WebSocket client connected: {client_id} from {request.remote}")
        
        # Send welcome message
        await self._send_to_client(client_id, {
            'type': 'welcome',
            'client_id': client_id,
            'server_time': datetime.now().isoformat(),
            'supported_subscriptions': [sub.value for sub in SubscriptionType]
        })
        
        try:
            # Handle messages from client
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await self._handle_client_message(client_id, msg.data)
                elif msg.type == WSMsgType.ERROR:
                    self.logger.error(f'WebSocket error for client {client_id}: {ws.exception()}')
                    break
                elif msg.type == WSMsgType.CLOSE:
                    break
        
        except Exception as e:
            self.logger.error(f"Error handling WebSocket client {client_id}: {e}")
        
        finally:
            # Clean up client
            await self._disconnect_client(client_id)
        
        return ws
    
    async def _handle_client_message(self, client_id: str, message_data: str):
        """Handle message from WebSocket client"""
        try:
            # Rate limiting check
            if not self._check_rate_limit(client_id):
                await self._send_to_client(client_id, {
                    'type': 'error',
                    'message': 'Rate limit exceeded'
                })
                return
            
            data = json.loads(message_data)
            message_type = data.get('type')
            
            self.websocket_metrics['messages_received'] += 1
            
            if message_type == 'ping':
                # Handle ping
                await self._handle_ping(client_id, data)
            
            elif message_type == 'subscribe':
                # Handle subscription changes
                await self._handle_subscription(client_id, data)
            
            elif message_type == 'request_data':
                # Handle data request
                await self._handle_data_request(client_id, data)
            
            elif message_type == 'agent_action':
                # Handle agent management actions
                await self._handle_agent_action(client_id, data)
            
            else:
                await self._send_to_client(client_id, {
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                })
        
        except json.JSONDecodeError:
            await self._send_to_client(client_id, {
                'type': 'error',
                'message': 'Invalid JSON format'
            })
        except Exception as e:
            self.logger.error(f"Error handling client message from {client_id}: {e}")
            await self._send_to_client(client_id, {
                'type': 'error',
                'message': 'Internal server error'
            })
    
    async def _handle_ping(self, client_id: str, data: Dict[str, Any]):
        """Handle ping message from client"""
        if client_id in self.clients:
            self.clients[client_id].last_ping = datetime.now()
            
            await self._send_to_client(client_id, {
                'type': 'pong',
                'timestamp': datetime.now().isoformat(),
                'client_timestamp': data.get('timestamp')
            })
    
    async def _handle_subscription(self, client_id: str, data: Dict[str, Any]):
        """Handle subscription change from client"""
        try:
            if client_id not in self.clients:
                return
            
            client = self.clients[client_id]
            subscription_types = data.get('subscriptions', [])
            
            # Validate and convert subscription types
            new_subscriptions = set()
            for sub_type in subscription_types:
                try:
                    subscription = SubscriptionType(sub_type)
                    new_subscriptions.add(subscription)
                except ValueError:
                    await self._send_to_client(client_id, {
                        'type': 'error',
                        'message': f'Invalid subscription type: {sub_type}'
                    })
                    return
            
            # Update client subscriptions
            client.subscriptions = new_subscriptions
            
            await self._send_to_client(client_id, {
                'type': 'subscription_updated',
                'subscriptions': [sub.value for sub in new_subscriptions]
            })
            
            self.logger.info(f"Updated subscriptions for client {client_id}: {subscription_types}")
        
        except Exception as e:
            self.logger.error(f"Error handling subscription for {client_id}: {e}")
    
    async def _handle_data_request(self, client_id: str, data: Dict[str, Any]):
        """Handle data request from client"""
        try:
            request_type = data.get('request_type')
            
            if request_type == 'agent_status':
                # Get current agent status
                if self.message_queue and hasattr(self.message_queue, 'get_agent_status'):
                    agent_status = await self.message_queue.get_agent_status()
                    await self._send_to_client(client_id, {
                        'type': 'data_response',
                        'request_type': request_type,
                        'data': agent_status
                    })
            
            elif request_type == 'task_statistics':
                # Get task statistics
                if self.message_queue and hasattr(self.message_queue, 'get_task_statistics'):
                    task_stats = await self.message_queue.get_task_statistics()
                    await self._send_to_client(client_id, {
                        'type': 'data_response',
                        'request_type': request_type,
                        'data': task_stats
                    })
            
            elif request_type == 'metrics_snapshot':
                # Get current metrics snapshot
                metrics = await self._get_current_metrics()
                await self._send_to_client(client_id, {
                    'type': 'data_response',
                    'request_type': request_type,
                    'data': metrics
                })
            
            else:
                await self._send_to_client(client_id, {
                    'type': 'error',
                    'message': f'Unknown request type: {request_type}'
                })
        
        except Exception as e:
            self.logger.error(f"Error handling data request from {client_id}: {e}")
            await self._send_to_client(client_id, {
                'type': 'error',
                'message': 'Failed to fetch requested data'
            })
    
    async def _handle_agent_action(self, client_id: str, data: Dict[str, Any]):
        """Handle agent management action from client"""
        try:
            action = data.get('action')
            agent_id = data.get('agent_id')
            
            if not action or not agent_id:
                await self._send_to_client(client_id, {
                    'type': 'error',
                    'message': 'Missing action or agent_id'
                })
                return
            
            # Forward action to message queue for processing
            if self.message_queue:
                message = {
                    'type': 'agent_management',
                    'action': action,
                    'agent_id': agent_id,
                    'client_id': client_id,
                    'timestamp': datetime.now().isoformat()
                }
                
                # This would be handled by the agent manager
                self.logger.info(f"Agent action from client {client_id}: {action} on {agent_id}")
                
                await self._send_to_client(client_id, {
                    'type': 'action_acknowledged',
                    'action': action,
                    'agent_id': agent_id
                })
        
        except Exception as e:
            self.logger.error(f"Error handling agent action from {client_id}: {e}")
    
    async def _handle_backend_message(self, message):
        """Handle messages from backend message queue"""
        try:
            # Convert backend messages to real-time updates
            update_type = None
            update_data = message.payload
            
            if message.type == MessageType.STATUS_UPDATE:
                update_type = UpdateType.AGENT_STATUS
            elif message.type == MessageType.TASK_RESULT:
                update_type = UpdateType.TASK_UPDATE
            elif message.type == MessageType.METRIC:
                update_type = UpdateType.METRICS
            elif message.type == MessageType.ALERT:
                update_type = UpdateType.SYSTEM_ALERT
            elif message.type == MessageType.COORDINATION_EVENT:
                update_type = UpdateType.COORDINATION_EVENT
            elif message.type == MessageType.OPTIMIZATION_RESULT:
                update_type = UpdateType.OPTIMIZATION_RESULT
            
            if update_type:
                update = RealTimeUpdate(
                    id=str(uuid.uuid4()),
                    type=update_type,
                    timestamp=datetime.now(),
                    data={
                        'source': message.sender,
                        'original_message': update_data
                    }
                )
                
                await self.queue_update(update)
        
        except Exception as e:
            self.logger.error(f"Error handling backend message: {e}")
    
    async def queue_update(self, update: RealTimeUpdate):
        """Queue update for broadcasting"""
        await self.update_queue.put(update)
    
    async def broadcast_update(self, update: RealTimeUpdate):
        """Broadcast update to relevant clients"""
        try:
            message = {
                'id': update.id,
                'type': update.type.value,
                'timestamp': update.timestamp.isoformat(),
                'data': update.data
            }
            
            # Determine target clients
            target_clients = []
            
            if update.target_clients:
                # Specific clients
                target_clients = [
                    client_id for client_id in update.target_clients
                    if client_id in self.clients
                ]
            else:
                # Filter by subscriptions
                for client_id, client in self.clients.items():
                    should_send = any(
                        self.subscription_filters[subscription](update)
                        for subscription in client.subscriptions
                    )
                    
                    if should_send:
                        target_clients.append(client_id)
            
            # Send to target clients
            send_tasks = []
            for client_id in target_clients:
                task = asyncio.create_task(self._send_to_client(client_id, message))
                send_tasks.append(task)
            
            if send_tasks:
                await asyncio.gather(*send_tasks, return_exceptions=True)
                self.websocket_metrics['messages_sent'] += len(send_tasks)
        
        except Exception as e:
            self.logger.error(f"Error broadcasting update: {e}")
    
    async def _update_broadcaster(self):
        """Background task to broadcast queued updates"""
        while self.running:
            try:
                # Get update from queue
                update = await asyncio.wait_for(self.update_queue.get(), timeout=1.0)
                
                # Check if update has expired
                if update.expires_at and datetime.now() > update.expires_at:
                    continue
                
                # Broadcast update
                await self.broadcast_update(update)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error in update broadcaster: {e}")
                await asyncio.sleep(1)
    
    async def _update_batcher(self):
        """Background task to batch updates for performance"""
        while self.running:
            try:
                await asyncio.sleep(self.batch_timeout)
                
                if self.update_batch:
                    # Process batched updates
                    batch = self.update_batch.copy()
                    self.update_batch.clear()
                    
                    # Group updates by type
                    grouped_updates = {}
                    for update in batch:
                        if update.type not in grouped_updates:
                            grouped_updates[update.type] = []
                        grouped_updates[update.type].append(update)
                    
                    # Send batched updates
                    for update_type, updates in grouped_updates.items():
                        if len(updates) > 1:
                            # Create batched update
                            batched_update = RealTimeUpdate(
                                id=str(uuid.uuid4()),
                                type=update_type,
                                timestamp=datetime.now(),
                                data={
                                    'batch': True,
                                    'count': len(updates),
                                    'updates': [update.data for update in updates]
                                }
                            )
                            await self.queue_update(batched_update)
                        else:
                            # Single update
                            await self.queue_update(updates[0])
            
            except Exception as e:
                self.logger.error(f"Error in update batcher: {e}")
                await asyncio.sleep(1)
    
    async def _health_checker(self):
        """Background task to check client health and clean up stale connections"""
        while self.running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                current_time = datetime.now()
                stale_clients = []
                
                for client_id, client in self.clients.items():
                    # Check if client hasn't pinged in a while (5 minutes)
                    if current_time - client.last_ping > timedelta(minutes=5):
                        stale_clients.append(client_id)
                
                # Disconnect stale clients
                for client_id in stale_clients:
                    await self._disconnect_client(client_id, reason="Stale connection")
            
            except Exception as e:
                self.logger.error(f"Error in health checker: {e}")
                await asyncio.sleep(30)
    
    async def _metrics_reporter(self):
        """Background task to report WebSocket metrics"""
        while self.running:
            try:
                await asyncio.sleep(60)  # Report every minute
                
                # Create metrics update
                metrics_update = RealTimeUpdate(
                    id=str(uuid.uuid4()),
                    type=UpdateType.METRICS,
                    timestamp=datetime.now(),
                    data={
                        'websocket_metrics': self.websocket_metrics.copy(),
                        'active_clients': len(self.clients),
                        'subscription_breakdown': self._get_subscription_breakdown()
                    }
                )
                
                await self.queue_update(metrics_update)
            
            except Exception as e:
                self.logger.error(f"Error in metrics reporter: {e}")
                await asyncio.sleep(60)
    
    async def _send_to_client(self, client_id: str, message: Dict[str, Any]):
        """Send message to specific client"""
        try:
            if client_id not in self.clients:
                return False
            
            client = self.clients[client_id]
            
            # Check if WebSocket is still open
            if client.websocket.closed:
                await self._disconnect_client(client_id)
                return False
            
            # Send message
            await client.websocket.send_str(json.dumps(message, default=str))
            return True
        
        except Exception as e:
            self.logger.error(f"Error sending message to client {client_id}: {e}")
            await self._disconnect_client(client_id, reason="Send error")
            return False
    
    async def _disconnect_client(self, client_id: str, reason: str = "Normal disconnect"):
        """Disconnect and clean up client"""
        try:
            if client_id in self.clients:
                client = self.clients[client_id]
                
                if not client.websocket.closed:
                    await client.websocket.close()
                
                del self.clients[client_id]
                
                # Clean up rate limiting
                if client_id in self.client_rate_limits:
                    del self.client_rate_limits[client_id]
                
                self.websocket_metrics['active_connections'] -= 1
                self.websocket_metrics['disconnections'] += 1
                
                self.logger.info(f"WebSocket client disconnected: {client_id} ({reason})")
        
        except Exception as e:
            self.logger.error(f"Error disconnecting client {client_id}: {e}")
    
    def _check_rate_limit(self, client_id: str) -> bool:
        """Check if client is within rate limits"""
        current_time = datetime.now()
        
        if client_id not in self.client_rate_limits:
            self.client_rate_limits[client_id] = []
        
        # Clean old entries
        cutoff_time = current_time - timedelta(seconds=self.rate_limit_window)
        self.client_rate_limits[client_id] = [
            msg_time for msg_time in self.client_rate_limits[client_id]
            if msg_time > cutoff_time
        ]
        
        # Check rate limit
        if len(self.client_rate_limits[client_id]) >= self.rate_limit_max_messages:
            return False
        
        # Add current message
        self.client_rate_limits[client_id].append(current_time)
        return True
    
    def _get_subscription_breakdown(self) -> Dict[str, int]:
        """Get breakdown of client subscriptions"""
        breakdown = {}
        
        for subscription_type in SubscriptionType:
            count = sum(
                1 for client in self.clients.values()
                if subscription_type in client.subscriptions
            )
            breakdown[subscription_type.value] = count
        
        return breakdown
    
    async def _get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        return {
            'websocket_metrics': self.websocket_metrics.copy(),
            'active_clients': len(self.clients),
            'subscription_breakdown': self._get_subscription_breakdown(),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_client_info(self) -> Dict[str, Any]:
        """Get information about connected clients"""
        client_info = {}
        
        for client_id, client in self.clients.items():
            client_info[client_id] = {
                'connected_at': client.connected_at.isoformat(),
                'last_ping': client.last_ping.isoformat(),
                'subscriptions': [sub.value for sub in client.subscriptions],
                'remote_addr': client.client_info.get('remote_addr'),
                'user_agent': client.client_info.get('user_agent')
            }
        
        return client_info
    
    async def shutdown(self):
        """Shutdown WebSocket manager gracefully"""
        self.running = False
        
        # Disconnect all clients
        disconnect_tasks = []
        for client_id in list(self.clients.keys()):
            task = asyncio.create_task(
                self._disconnect_client(client_id, reason="Server shutdown")
            )
            disconnect_tasks.append(task)
        
        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        
        self.logger.info("WebSocket manager shutdown complete")


# Enhanced Dashboard API Server with integrated WebSocket manager
class EnhancedDashboardAPIServer:
    """Enhanced API server with integrated WebSocket support"""
    
    def __init__(self, host='localhost', port=8080, message_queue=None, 
                 agent_manager=None, task_orchestrator=None, coordination_service=None):
        self.host = host
        self.port = port
        self.app = web.Application()
        
        # Backend services
        self.message_queue = message_queue
        self.agent_manager = agent_manager
        self.task_orchestrator = task_orchestrator
        self.coordination_service = coordination_service
        
        # WebSocket manager
        self.websocket_manager = WebSocketManager(message_queue)
        
        self.setup_logging()
        self.setup_routes()
        self.setup_cors()
    
    def setup_logging(self):
        """Setup logging configuration"""
        self.logger = logging.getLogger('EnhancedDashboardAPI')
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def setup_routes(self):
        """Setup API routes"""
        # WebSocket endpoint
        self.app.router.add_get('/ws', self.websocket_manager.handle_websocket_connection)
        
        # Enhanced API endpoints with real-time capabilities
        self.app.router.add_get('/api/health', self.health_check)
        self.app.router.add_get('/api/agents/status', self.get_agent_status)
        self.app.router.add_post('/api/agents/{agent_id}/{action}', self.agent_action)
        self.app.router.add_get('/api/tasks/status', self.get_task_status)
        self.app.router.add_get('/api/tasks/queue', self.get_task_queue)
        self.app.router.add_get('/api/coordination/status', self.get_coordination_status)
        self.app.router.add_get('/api/metrics/system', self.get_system_metrics)
        self.app.router.add_get('/api/websocket/clients', self.get_websocket_clients)
        
        # Static file serving
        self.app.router.add_static('/', path='dashboard/build', name='static')
    
    def setup_cors(self):
        """Setup CORS for API"""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Add CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    async def health_check(self, request):
        """Enhanced health check with real-time capabilities"""
        try:
            health_status = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'services': {
                    'websocket_manager': 'healthy' if self.websocket_manager.running else 'stopped',
                    'message_queue': 'healthy' if self.message_queue else 'not_available',
                    'agent_manager': 'healthy' if self.agent_manager else 'not_available',
                    'task_orchestrator': 'healthy' if self.task_orchestrator else 'not_available',
                    'coordination_service': 'healthy' if self.coordination_service else 'not_available'
                },
                'websocket_stats': {
                    'active_connections': len(self.websocket_manager.clients),
                    'total_connections': self.websocket_manager.websocket_metrics['total_connections']
                }
            }
            
            return web.json_response(health_status)
        
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_agent_status(self, request):
        """Get agent status with real-time update broadcasting"""
        try:
            if self.agent_manager:
                status = await self.agent_manager.get_agent_status()
            else:
                status = {'error': 'Agent manager not available'}
            
            # Broadcast update to WebSocket clients
            update = RealTimeUpdate(
                id=str(uuid.uuid4()),
                type=UpdateType.AGENT_STATUS,
                timestamp=datetime.now(),
                data=status
            )
            await self.websocket_manager.queue_update(update)
            
            return web.json_response(status)
        
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def agent_action(self, request):
        """Perform agent action with real-time notifications"""
        try:
            agent_id = request.match_info['agent_id']
            action = request.match_info['action']
            
            result = {'success': False, 'message': 'Agent manager not available'}
            
            if self.agent_manager:
                if action == 'start':
                    result['success'] = await self.agent_manager.restart_agent(agent_id)
                elif action == 'stop':
                    result['success'] = await self.agent_manager.stop_agent(agent_id)
                elif action == 'restart':
                    result['success'] = await self.agent_manager.restart_agent(agent_id)
                else:
                    result['message'] = f'Unknown action: {action}'
                
                if result['success']:
                    result['message'] = f'Agent {action} successful'
            
            # Broadcast real-time update
            update = RealTimeUpdate(
                id=str(uuid.uuid4()),
                type=UpdateType.AGENT_STATUS,
                timestamp=datetime.now(),
                data={
                    'agent_id': agent_id,
                    'action': action,
                    'success': result['success'],
                    'message': result['message']
                }
            )
            await self.websocket_manager.queue_update(update)
            
            return web.json_response(result)
        
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_task_status(self, request):
        """Get task status"""
        try:
            if self.task_orchestrator:
                status = await self.task_orchestrator.get_queue_status()
            else:
                status = {'error': 'Task orchestrator not available'}
            
            return web.json_response(status)
        
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_task_queue(self, request):
        """Get task queue information"""
        try:
            if self.task_orchestrator:
                queue_info = await self.task_orchestrator.get_queue_status()
                workloads = await self.task_orchestrator.get_agent_workloads()
                
                result = {
                    'queue_status': queue_info,
                    'agent_workloads': workloads
                }
            else:
                result = {'error': 'Task orchestrator not available'}
            
            return web.json_response(result)
        
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_coordination_status(self, request):
        """Get coordination service status"""
        try:
            if self.coordination_service:
                status = await self.coordination_service.get_coordination_status()
            else:
                status = {'error': 'Coordination service not available'}
            
            return web.json_response(status)
        
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_system_metrics(self, request):
        """Get comprehensive system metrics"""
        try:
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'websocket': await self.websocket_manager._get_current_metrics()
            }
            
            if self.agent_manager:
                metrics['agents'] = await self.agent_manager.get_agent_status()
            
            if self.task_orchestrator:
                metrics['tasks'] = await self.task_orchestrator.get_queue_status()
                metrics['workloads'] = await self.task_orchestrator.get_agent_workloads()
            
            if self.coordination_service:
                metrics['coordination'] = await self.coordination_service.get_coordination_status()
            
            if self.message_queue:
                metrics['message_queue'] = await self.message_queue.get_task_statistics()
            
            return web.json_response(metrics)
        
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_websocket_clients(self, request):
        """Get WebSocket client information"""
        try:
            client_info = self.websocket_manager.get_client_info()
            return web.json_response(client_info)
        
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def start_server(self):
        """Start the enhanced API server"""
        # Initialize WebSocket manager
        await self.websocket_manager.initialize()
        
        # Start web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        self.logger.info(f"Enhanced Dashboard API Server running at http://{self.host}:{self.port}")
        self.logger.info(f"WebSocket endpoint: ws://{self.host}:{self.port}/ws")
        
        return runner
    
    async def shutdown(self):
        """Shutdown server gracefully"""
        await self.websocket_manager.shutdown()
        self.logger.info("Enhanced Dashboard API Server shutdown complete")


# CLI interface for testing
if __name__ == "__main__":
    import sys
    
    async def test_websocket_manager():
        # Create test WebSocket manager
        websocket_manager = WebSocketManager()
        await websocket_manager.initialize()
        
        # Simulate some updates
        test_updates = [
            RealTimeUpdate(
                id=str(uuid.uuid4()),
                type=UpdateType.AGENT_STATUS,
                timestamp=datetime.now(),
                data={'agent_id': 'test-agent', 'status': 'healthy'}
            ),
            RealTimeUpdate(
                id=str(uuid.uuid4()),
                type=UpdateType.METRICS,
                timestamp=datetime.now(),
                data={'cpu_usage': 75.5, 'memory_usage': 68.2}
            )
        ]
        
        for update in test_updates:
            await websocket_manager.queue_update(update)
        
        print(f"WebSocket manager metrics: {await websocket_manager._get_current_metrics()}")
        
        await websocket_manager.shutdown()
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        asyncio.run(test_websocket_manager())
    else:
        print("Use 'python websocket_manager.py test' to run tests")