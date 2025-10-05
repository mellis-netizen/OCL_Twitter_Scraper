"""
WebSocket service for real-time TGE alert notifications
Enhanced WebSocket management with authentication and room-based subscriptions
"""

import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
import jwt
from enum import Enum

from .database import DatabaseManager
from .models import User, Alert, Company
from .auth import AuthManager
from .schemas import AlertNotification, WebSocketMessage

logger = logging.getLogger(__name__)

# WebSocket message types
class MessageType(str, Enum):
    ALERT = "alert"
    STATUS = "status"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    AUTH = "auth"
    HEARTBEAT = "heartbeat"
    SYSTEM_STATUS = "system_status"
    FEED_UPDATE = "feed_update"


class SubscriptionType(str, Enum):
    ALL_ALERTS = "all_alerts"
    HIGH_CONFIDENCE = "high_confidence"
    COMPANY_SPECIFIC = "company_specific"
    SOURCE_SPECIFIC = "source_specific"
    SYSTEM_STATUS = "system_status"


class WebSocketConnection:
    """Individual WebSocket connection with user context and subscriptions"""
    
    def __init__(self, websocket: WebSocket, user: Optional[User] = None):
        self.websocket = websocket
        self.user = user
        self.user_id = user.id if user else None
        self.subscriptions: Set[str] = set()
        self.connection_time = datetime.now(timezone.utc)
        self.last_ping = datetime.now(timezone.utc)
        self.is_authenticated = user is not None
        self.company_filters: Set[int] = set()  # Company IDs to filter
        self.confidence_threshold: float = 0.0
        self.source_filters: Set[str] = set()
    
    async def send_message(self, message_type: MessageType, data: Any):
        """Send message to WebSocket client"""
        try:
            message = WebSocketMessage(
                type=message_type.value,
                data=data,
                timestamp=datetime.now(timezone.utc)
            )
            await self.websocket.send_text(message.json())
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            raise WebSocketDisconnect()
    
    async def send_alert(self, alert: Alert):
        """Send alert notification if it matches user's filters"""
        # Check filters
        if not self._should_send_alert(alert):
            return
        
        # Create notification
        notification = AlertNotification(
            alert_id=alert.id,
            title=alert.title,
            company_name=alert.company.name if alert.company else None,
            confidence=alert.confidence,
            urgency_level=alert.urgency_level,
            source=alert.source,
            created_at=alert.created_at
        )
        
        await self.send_message(MessageType.ALERT, notification.dict())
    
    def _should_send_alert(self, alert: Alert) -> bool:
        """Check if alert should be sent based on user's subscriptions and filters"""
        # Check confidence threshold
        if alert.confidence < self.confidence_threshold:
            return False
        
        # Check company filters
        if self.company_filters and (not alert.company_id or alert.company_id not in self.company_filters):
            return False
        
        # Check source filters
        if self.source_filters and alert.source not in self.source_filters:
            return False
        
        # Check subscription types
        if SubscriptionType.ALL_ALERTS.value in self.subscriptions:
            return True
        
        if SubscriptionType.HIGH_CONFIDENCE.value in self.subscriptions and alert.confidence >= 0.7:
            return True
        
        if SubscriptionType.COMPANY_SPECIFIC.value in self.subscriptions and alert.company_id:
            return alert.company_id in self.company_filters
        
        if SubscriptionType.SOURCE_SPECIFIC.value in self.subscriptions:
            return alert.source in self.source_filters
        
        return False
    
    def add_subscription(self, subscription: str, **filters):
        """Add subscription with optional filters"""
        self.subscriptions.add(subscription)
        
        # Apply filters
        if 'companies' in filters:
            self.company_filters.update(filters['companies'])
        
        if 'confidence_threshold' in filters:
            self.confidence_threshold = max(self.confidence_threshold, filters['confidence_threshold'])
        
        if 'sources' in filters:
            self.source_filters.update(filters['sources'])
    
    def remove_subscription(self, subscription: str):
        """Remove subscription"""
        self.subscriptions.discard(subscription)
    
    def update_last_ping(self):
        """Update last ping time"""
        self.last_ping = datetime.now(timezone.utc)


class WebSocketManager:
    """Advanced WebSocket connection manager with authentication and rooms"""
    
    def __init__(self):
        self.connections: List[WebSocketConnection] = []
        self.user_connections: Dict[int, List[WebSocketConnection]] = {}
        self.rooms: Dict[str, Set[WebSocketConnection]] = {}
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'authenticated_connections': 0,
            'messages_sent': 0,
            'alerts_broadcast': 0
        }
    
    async def connect(self, websocket: WebSocket, user: Optional[User] = None) -> WebSocketConnection:
        """Accept new WebSocket connection"""
        await websocket.accept()
        
        connection = WebSocketConnection(websocket, user)
        self.connections.append(connection)
        
        # Track user connections
        if user:
            if user.id not in self.user_connections:
                self.user_connections[user.id] = []
            self.user_connections[user.id].append(connection)
            self.stats['authenticated_connections'] += 1
        
        self.stats['total_connections'] += 1
        self.stats['active_connections'] += 1
        
        logger.info(f"New WebSocket connection: user_id={user.id if user else 'anonymous'}")
        
        # Send welcome message
        await connection.send_message(MessageType.STATUS, {
            "status": "connected",
            "authenticated": connection.is_authenticated,
            "server_time": datetime.now(timezone.utc).isoformat()
        })
        
        return connection
    
    def disconnect(self, connection: WebSocketConnection):
        """Remove WebSocket connection"""
        try:
            if connection in self.connections:
                self.connections.remove(connection)
                self.stats['active_connections'] -= 1
            
            # Remove from user connections
            if connection.user_id and connection.user_id in self.user_connections:
                if connection in self.user_connections[connection.user_id]:
                    self.user_connections[connection.user_id].remove(connection)
                
                if not self.user_connections[connection.user_id]:
                    del self.user_connections[connection.user_id]
                
                self.stats['authenticated_connections'] -= 1
            
            # Remove from rooms
            for room_connections in self.rooms.values():
                room_connections.discard(connection)
            
            logger.info(f"WebSocket disconnected: user_id={connection.user_id}")
            
        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {e}")
    
    async def authenticate_connection(self, connection: WebSocketConnection, token: str) -> bool:
        """Authenticate WebSocket connection with JWT token"""
        try:
            token_data = AuthManager.verify_token(token)
            if not token_data:
                await connection.send_message(MessageType.ERROR, {
                    "error": "Invalid token",
                    "code": "AUTH_FAILED"
                })
                return False
            
            # Get user from database
            with DatabaseManager.get_session() as db:
                user = db.query(User).filter(User.id == token_data.user_id).first()
                
                if not user or not user.is_active:
                    await connection.send_message(MessageType.ERROR, {
                        "error": "User not found or inactive",
                        "code": "USER_INVALID"
                    })
                    return False
                
                # Update connection with user info
                connection.user = user
                connection.user_id = user.id
                connection.is_authenticated = True
                
                # Track authenticated connection
                if user.id not in self.user_connections:
                    self.user_connections[user.id] = []
                self.user_connections[user.id].append(connection)
                self.stats['authenticated_connections'] += 1
                
                await connection.send_message(MessageType.STATUS, {
                    "status": "authenticated",
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "is_admin": user.is_admin
                    }
                })
                
                logger.info(f"WebSocket authenticated: user_id={user.id}")
                return True
                
        except Exception as e:
            logger.error(f"WebSocket authentication error: {e}")
            await connection.send_message(MessageType.ERROR, {
                "error": "Authentication failed",
                "code": "AUTH_ERROR"
            })
            return False
    
    async def handle_subscription(self, connection: WebSocketConnection, subscription_data: Dict[str, Any]):
        """Handle subscription request"""
        try:
            subscription_type = subscription_data.get('type')
            action = subscription_data.get('action', 'subscribe')  # subscribe or unsubscribe
            filters = subscription_data.get('filters', {})
            
            if action == 'subscribe':
                connection.add_subscription(subscription_type, **filters)
                
                # Add to room if applicable
                room_name = f"subscription_{subscription_type}"
                if room_name not in self.rooms:
                    self.rooms[room_name] = set()
                self.rooms[room_name].add(connection)
                
                await connection.send_message(MessageType.STATUS, {
                    "action": "subscribed",
                    "subscription": subscription_type,
                    "filters": filters
                })
                
            elif action == 'unsubscribe':
                connection.remove_subscription(subscription_type)
                
                # Remove from room
                room_name = f"subscription_{subscription_type}"
                if room_name in self.rooms:
                    self.rooms[room_name].discard(connection)
                
                await connection.send_message(MessageType.STATUS, {
                    "action": "unsubscribed",
                    "subscription": subscription_type
                })
            
            logger.debug(f"Subscription {action}: {subscription_type} for user {connection.user_id}")
            
        except Exception as e:
            logger.error(f"Subscription handling error: {e}")
            await connection.send_message(MessageType.ERROR, {
                "error": "Subscription failed",
                "code": "SUBSCRIPTION_ERROR"
            })
    
    async def broadcast_alert(self, alert: Alert):
        """Broadcast alert to all relevant connections"""
        if not self.connections:
            return
        
        broadcast_count = 0
        
        for connection in self.connections.copy():  # Copy to avoid modification during iteration
            try:
                await connection.send_alert(alert)
                broadcast_count += 1
            except WebSocketDisconnect:
                self.disconnect(connection)
            except Exception as e:
                logger.error(f"Error broadcasting alert to connection: {e}")
        
        self.stats['alerts_broadcast'] += 1
        self.stats['messages_sent'] += broadcast_count
        
        logger.info(f"Broadcasted alert {alert.id} to {broadcast_count} connections")
    
    async def send_to_user(self, user_id: int, message_type: MessageType, data: Any):
        """Send message to specific user's connections"""
        if user_id not in self.user_connections:
            return
        
        for connection in self.user_connections[user_id].copy():
            try:
                await connection.send_message(message_type, data)
            except WebSocketDisconnect:
                self.disconnect(connection)
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
    
    async def send_to_room(self, room_name: str, message_type: MessageType, data: Any):
        """Send message to all connections in a room"""
        if room_name not in self.rooms:
            return
        
        for connection in self.rooms[room_name].copy():
            try:
                await connection.send_message(message_type, data)
            except WebSocketDisconnect:
                self.disconnect(connection)
            except Exception as e:
                logger.error(f"Error sending message to room {room_name}: {e}")
    
    async def broadcast_system_status(self, status_data: Dict[str, Any]):
        """Broadcast system status update"""
        for connection in self.connections.copy():
            if SubscriptionType.SYSTEM_STATUS.value in connection.subscriptions:
                try:
                    await connection.send_message(MessageType.SYSTEM_STATUS, status_data)
                except WebSocketDisconnect:
                    self.disconnect(connection)
                except Exception as e:
                    logger.error(f"Error broadcasting system status: {e}")
    
    async def send_heartbeat(self):
        """Send heartbeat to all connections"""
        heartbeat_data = {
            "server_time": datetime.now(timezone.utc).isoformat(),
            "active_connections": self.stats['active_connections']
        }
        
        for connection in self.connections.copy():
            try:
                await connection.send_message(MessageType.HEARTBEAT, heartbeat_data)
            except WebSocketDisconnect:
                self.disconnect(connection)
            except Exception as e:
                logger.error(f"Error sending heartbeat: {e}")
    
    async def cleanup_stale_connections(self):
        """Remove stale connections that haven't pinged recently"""
        now = datetime.now(timezone.utc)
        stale_threshold = 300  # 5 minutes
        
        stale_connections = []
        
        for connection in self.connections:
            if (now - connection.last_ping).total_seconds() > stale_threshold:
                stale_connections.append(connection)
        
        for connection in stale_connections:
            logger.info(f"Removing stale WebSocket connection: user_id={connection.user_id}")
            self.disconnect(connection)
            try:
                await connection.websocket.close()
            except:
                pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics"""
        return {
            **self.stats,
            "rooms": {room: len(connections) for room, connections in self.rooms.items()},
            "subscriptions": self._get_subscription_stats()
        }
    
    def _get_subscription_stats(self) -> Dict[str, int]:
        """Get subscription statistics"""
        subscription_counts = {}
        
        for connection in self.connections:
            for subscription in connection.subscriptions:
                subscription_counts[subscription] = subscription_counts.get(subscription, 0) + 1
        
        return subscription_counts


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


# WebSocket message handler
async def handle_websocket_message(connection: WebSocketConnection, message_data: Dict[str, Any]):
    """Handle incoming WebSocket message"""
    try:
        message_type = message_data.get('type')
        data = message_data.get('data', {})
        
        if message_type == MessageType.PING.value:
            connection.update_last_ping()
            await connection.send_message(MessageType.PONG, {"timestamp": datetime.now(timezone.utc).isoformat()})
        
        elif message_type == MessageType.AUTH.value:
            token = data.get('token')
            if token:
                await websocket_manager.authenticate_connection(connection, token)
            else:
                await connection.send_message(MessageType.ERROR, {
                    "error": "Token required for authentication",
                    "code": "TOKEN_MISSING"
                })
        
        elif message_type == MessageType.SUBSCRIBE.value:
            if not connection.is_authenticated:
                await connection.send_message(MessageType.ERROR, {
                    "error": "Authentication required for subscriptions",
                    "code": "AUTH_REQUIRED"
                })
                return
            
            await websocket_manager.handle_subscription(connection, data)
        
        elif message_type == MessageType.UNSUBSCRIBE.value:
            await websocket_manager.handle_subscription(connection, {**data, 'action': 'unsubscribe'})
        
        else:
            await connection.send_message(MessageType.ERROR, {
                "error": f"Unknown message type: {message_type}",
                "code": "UNKNOWN_MESSAGE_TYPE"
            })
    
    except Exception as e:
        logger.error(f"Error handling WebSocket message: {e}")
        await connection.send_message(MessageType.ERROR, {
            "error": "Message processing failed",
            "code": "PROCESSING_ERROR"
        })


# Background tasks
async def websocket_background_tasks():
    """Background tasks for WebSocket management"""
    while True:
        try:
            # Send heartbeat every 30 seconds
            await websocket_manager.send_heartbeat()
            
            # Cleanup stale connections every 5 minutes
            await websocket_manager.cleanup_stale_connections()
            
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"WebSocket background task error: {e}")
            await asyncio.sleep(60)


# Integration with alert system
async def notify_new_alert(alert: Alert):
    """Notify WebSocket clients of new alert"""
    try:
        await websocket_manager.broadcast_alert(alert)
    except Exception as e:
        logger.error(f"Failed to notify WebSocket clients of new alert: {e}")


async def notify_system_status(status_data: Dict[str, Any]):
    """Notify WebSocket clients of system status change"""
    try:
        await websocket_manager.broadcast_system_status(status_data)
    except Exception as e:
        logger.error(f"Failed to notify WebSocket clients of system status: {e}")


# Utility functions for integration
def get_websocket_stats() -> Dict[str, Any]:
    """Get WebSocket statistics"""
    return websocket_manager.get_stats()


def get_active_connections_count() -> int:
    """Get number of active WebSocket connections"""
    return websocket_manager.stats['active_connections']


def get_authenticated_connections_count() -> int:
    """Get number of authenticated WebSocket connections"""
    return websocket_manager.stats['authenticated_connections']


if __name__ == "__main__":
    # Test WebSocket service
    import asyncio
    
    async def test_websocket_service():
        """Test WebSocket service functionality"""
        print("Testing WebSocket service...")
        
        # Test manager initialization
        manager = WebSocketManager()
        print(f"✓ WebSocket manager initialized")
        
        # Test statistics
        stats = manager.get_stats()
        print(f"✓ Initial stats: {stats}")
        
        print("WebSocket service test completed")
    
    asyncio.run(test_websocket_service())