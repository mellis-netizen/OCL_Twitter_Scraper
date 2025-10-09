#!/usr/bin/env python3
"""
Redis Message Queue System for TGE Swarm Agent Communication
Provides pub/sub messaging, task queues, and real-time communication
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, asdict
from enum import Enum
import redis.asyncio as redis
from redis.exceptions import ConnectionError, RedisError


class MessageType(Enum):
    """Message types for agent communication"""
    TASK_ASSIGNMENT = "task_assignment"
    TASK_RESULT = "task_result"
    STATUS_UPDATE = "status_update"
    HEALTH_CHECK = "health_check"
    OPTIMIZATION_REQUEST = "optimization_request"
    OPTIMIZATION_RESULT = "optimization_result"
    AGENT_DISCOVERY = "agent_discovery"
    COORDINATION_EVENT = "coordination_event"
    ALERT = "alert"
    METRIC = "metric"


class Priority(Enum):
    """Task priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class SwarmMessage:
    """Standard message format for swarm communication"""
    id: str
    type: MessageType
    sender: str
    recipient: Optional[str]  # None for broadcast
    timestamp: datetime
    payload: Dict[str, Any]
    priority: Priority = Priority.MEDIUM
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    correlation_id: Optional[str] = None


@dataclass
class TaskDefinition:
    """Task definition for agent execution"""
    id: str
    type: str
    agent_type: str
    priority: Priority
    payload: Dict[str, Any]
    timeout: int = 300  # 5 minutes default
    retries: int = 3
    created_at: datetime = None
    assigned_to: Optional[str] = None
    dependencies: List[str] = None


class MessageQueue:
    """Redis-based message queue for swarm agent communication"""
    
    def __init__(self, redis_cluster_urls: List[str], cluster_name: str = "tge-swarm"):
        self.cluster_urls = redis_cluster_urls
        self.cluster_name = cluster_name
        self.redis_pool = None
        self.subscribers: Dict[str, Callable] = {}
        self.running = False
        
        # Message patterns
        self.agent_channel = f"{cluster_name}:agents"
        self.broadcast_channel = f"{cluster_name}:broadcast"
        self.task_queue = f"{cluster_name}:tasks"
        self.priority_queues = {
            Priority.CRITICAL: f"{cluster_name}:tasks:critical",
            Priority.HIGH: f"{cluster_name}:tasks:high",
            Priority.MEDIUM: f"{cluster_name}:tasks:medium",
            Priority.LOW: f"{cluster_name}:tasks:low"
        }
        self.result_queue = f"{cluster_name}:results"
        self.metrics_channel = f"{cluster_name}:metrics"
        
        # State tracking
        self.active_agents: Set[str] = set()
        self.message_stats = {
            'sent': 0,
            'received': 0,
            'failed': 0,
            'queued_tasks': 0,
            'completed_tasks': 0
        }
        
        self.setup_logging()
    
    def setup_logging(self):
        """Setup message queue logging"""
        self.logger = logging.getLogger(f"MessageQueue.{self.cluster_name}")
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    async def initialize(self):
        """Initialize Redis connection pool"""
        try:
            # Create Redis cluster connection
            self.redis_pool = redis.Redis(
                host=self.cluster_urls[0].split(':')[0],
                port=int(self.cluster_urls[0].split(':')[1]),
                decode_responses=True,
                health_check_interval=30,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            
            # Test connection
            await self.redis_pool.ping()
            self.logger.info(f"Connected to Redis cluster: {self.cluster_urls[0]}")
            
            # Initialize system keys
            await self._initialize_system_keys()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis connection: {e}")
            raise
    
    async def _initialize_system_keys(self):
        """Initialize system keys and data structures"""
        # Initialize agent registry
        await self.redis_pool.hset(f"{self.cluster_name}:agents", mapping={})
        
        # Initialize metrics
        await self.redis_pool.hset(f"{self.cluster_name}:metrics", mapping={
            'system_start': datetime.now().isoformat(),
            'total_messages': '0',
            'total_tasks': '0'
        })
        
        self.logger.info("System keys initialized")
    
    async def publish_message(self, message: SwarmMessage) -> bool:
        """Publish a message to the appropriate channel"""
        try:
            message_data = self._serialize_message(message)
            
            # Determine channel based on recipient
            if message.recipient:
                channel = f"{self.agent_channel}:{message.recipient}"
            else:
                channel = self.broadcast_channel
            
            # Publish message
            await self.redis_pool.publish(channel, message_data)
            
            # Update stats
            self.message_stats['sent'] += 1
            await self._update_message_metrics('sent')
            
            self.logger.debug(f"Published message {message.id} to {channel}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to publish message {message.id}: {e}")
            self.message_stats['failed'] += 1
            return False
    
    async def subscribe_to_agent_channel(self, agent_id: str, callback: Callable):
        """Subscribe to agent-specific channel"""
        channel = f"{self.agent_channel}:{agent_id}"
        self.subscribers[channel] = callback
        
        # Register agent as active
        self.active_agents.add(agent_id)
        await self.redis_pool.hset(f"{self.cluster_name}:agents", agent_id, json.dumps({
            'status': 'active',
            'last_seen': datetime.now().isoformat(),
            'subscribed_at': datetime.now().isoformat()
        }))
        
        self.logger.info(f"Agent {agent_id} subscribed to channel {channel}")
    
    async def subscribe_to_broadcast(self, callback: Callable):
        """Subscribe to broadcast channel"""
        self.subscribers[self.broadcast_channel] = callback
        self.logger.info("Subscribed to broadcast channel")
    
    async def enqueue_task(self, task: TaskDefinition) -> bool:
        """Enqueue a task for agent processing"""
        try:
            # Serialize task
            task_data = json.dumps(asdict(task), default=str)
            
            # Add to priority queue
            priority_queue = self.priority_queues[task.priority]
            await self.redis_pool.lpush(priority_queue, task_data)
            
            # Add to general task tracking
            await self.redis_pool.hset(f"{self.cluster_name}:task_status", task.id, json.dumps({
                'status': 'queued',
                'created_at': task.created_at.isoformat() if task.created_at else datetime.now().isoformat(),
                'priority': task.priority.name,
                'type': task.type
            }))
            
            self.message_stats['queued_tasks'] += 1
            await self._update_message_metrics('queued_tasks')
            
            self.logger.info(f"Enqueued task {task.id} with priority {task.priority.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to enqueue task {task.id}: {e}")
            return False
    
    async def dequeue_task(self, agent_id: str, agent_type: str = None) -> Optional[TaskDefinition]:
        """Dequeue next available task for agent"""
        try:
            # Check priority queues in order
            for priority in [Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM, Priority.LOW]:
                queue_name = self.priority_queues[priority]
                
                # Blocking pop with timeout
                result = await self.redis_pool.brpop(queue_name, timeout=1)
                if result:
                    _, task_data = result
                    task_dict = json.loads(task_data)
                    
                    # Convert back to TaskDefinition
                    task = TaskDefinition(**task_dict)
                    
                    # Check if agent can handle this task type
                    if agent_type and task.agent_type != agent_type and task.agent_type != "any":
                        # Put it back and continue
                        await self.redis_pool.lpush(queue_name, task_data)
                        continue
                    
                    # Assign task to agent
                    task.assigned_to = agent_id
                    await self.redis_pool.hset(f"{self.cluster_name}:task_status", task.id, json.dumps({
                        'status': 'assigned',
                        'assigned_to': agent_id,
                        'assigned_at': datetime.now().isoformat(),
                        'priority': task.priority.name,
                        'type': task.type
                    }))
                    
                    self.logger.info(f"Assigned task {task.id} to agent {agent_id}")
                    return task
            
            return None  # No tasks available
            
        except Exception as e:
            self.logger.error(f"Failed to dequeue task for agent {agent_id}: {e}")
            return None
    
    async def submit_task_result(self, task_id: str, agent_id: str, result: Dict[str, Any], success: bool = True):
        """Submit task execution result"""
        try:
            result_data = {
                'task_id': task_id,
                'agent_id': agent_id,
                'timestamp': datetime.now().isoformat(),
                'success': success,
                'result': result
            }
            
            # Store result
            await self.redis_pool.lpush(self.result_queue, json.dumps(result_data))
            
            # Update task status
            status = 'completed' if success else 'failed'
            await self.redis_pool.hset(f"{self.cluster_name}:task_status", task_id, json.dumps({
                'status': status,
                'completed_at': datetime.now().isoformat(),
                'agent_id': agent_id,
                'success': success
            }))
            
            if success:
                self.message_stats['completed_tasks'] += 1
                await self._update_message_metrics('completed_tasks')
            
            self.logger.info(f"Task {task_id} completed by {agent_id} with status: {status}")
            
        except Exception as e:
            self.logger.error(f"Failed to submit task result for {task_id}: {e}")
    
    async def get_task_results(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent task results"""
        try:
            results = await self.redis_pool.lrange(self.result_queue, 0, limit - 1)
            return [json.loads(result) for result in results]
        except Exception as e:
            self.logger.error(f"Failed to get task results: {e}")
            return []
    
    async def start_message_listener(self):
        """Start listening for messages"""
        self.running = True
        
        try:
            # Create pubsub instance
            pubsub = self.redis_pool.pubsub()
            
            # Subscribe to all registered channels
            for channel in self.subscribers.keys():
                await pubsub.subscribe(channel)
                self.logger.info(f"Listening on channel: {channel}")
            
            # Message processing loop
            while self.running:
                try:
                    message = await pubsub.get_message(timeout=1.0)
                    if message and message['type'] == 'message':
                        await self._handle_received_message(message)
                        
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")
                    await asyncio.sleep(1)
            
        except Exception as e:
            self.logger.error(f"Message listener error: {e}")
        finally:
            if 'pubsub' in locals():
                await pubsub.close()
    
    async def _handle_received_message(self, redis_message):
        """Handle received Redis message"""
        try:
            channel = redis_message['channel']
            data = redis_message['data']
            
            # Deserialize message
            message = self._deserialize_message(data)
            
            # Find and call appropriate callback
            if channel in self.subscribers:
                callback = self.subscribers[channel]
                await callback(message)
                
                self.message_stats['received'] += 1
                await self._update_message_metrics('received')
            
        except Exception as e:
            self.logger.error(f"Error handling received message: {e}")
    
    async def publish_agent_status(self, agent_id: str, status: Dict[str, Any]):
        """Publish agent status update"""
        message = SwarmMessage(
            id=str(uuid.uuid4()),
            type=MessageType.STATUS_UPDATE,
            sender=agent_id,
            recipient=None,  # Broadcast
            timestamp=datetime.now(),
            payload=status,
            priority=Priority.LOW
        )
        
        await self.publish_message(message)
    
    async def publish_optimization_request(self, requester: str, optimization_type: str, 
                                         target_files: List[str], parameters: Dict[str, Any]):
        """Publish optimization request"""
        message = SwarmMessage(
            id=str(uuid.uuid4()),
            type=MessageType.OPTIMIZATION_REQUEST,
            sender=requester,
            recipient=None,  # Broadcast to find capable agents
            timestamp=datetime.now(),
            payload={
                'optimization_type': optimization_type,
                'target_files': target_files,
                'parameters': parameters
            },
            priority=Priority.HIGH
        )
        
        await self.publish_message(message)
    
    async def publish_metric(self, source: str, metric_name: str, value: Any, tags: Dict[str, str] = None):
        """Publish system metric"""
        metric_data = {
            'source': source,
            'metric': metric_name,
            'value': value,
            'timestamp': datetime.now().isoformat(),
            'tags': tags or {}
        }
        
        await self.redis_pool.publish(self.metrics_channel, json.dumps(metric_data))
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        try:
            agents_data = await self.redis_pool.hgetall(f"{self.cluster_name}:agents")
            agents = {}
            
            for agent_id, data_str in agents_data.items():
                agent_info = json.loads(data_str)
                agents[agent_id] = agent_info
            
            return {
                'total_agents': len(agents),
                'active_agents': len(self.active_agents),
                'agents': agents,
                'message_stats': self.message_stats
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get agent status: {e}")
            return {}
    
    async def get_task_statistics(self) -> Dict[str, Any]:
        """Get task execution statistics"""
        try:
            # Get queue lengths
            queue_lengths = {}
            for priority, queue_name in self.priority_queues.items():
                length = await self.redis_pool.llen(queue_name)
                queue_lengths[priority.name] = length
            
            # Get task status counts
            task_statuses = await self.redis_pool.hgetall(f"{self.cluster_name}:task_status")
            status_counts = {'queued': 0, 'assigned': 0, 'completed': 0, 'failed': 0}
            
            for task_id, status_data in task_statuses.items():
                status_info = json.loads(status_data)
                status = status_info.get('status', 'unknown')
                if status in status_counts:
                    status_counts[status] += 1
            
            return {
                'queue_lengths': queue_lengths,
                'status_counts': status_counts,
                'total_results': await self.redis_pool.llen(self.result_queue),
                'message_stats': self.message_stats
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get task statistics: {e}")
            return {}
    
    async def cleanup_expired_tasks(self):
        """Clean up expired tasks and results"""
        try:
            current_time = datetime.now()
            
            # Clean up old results (keep last 1000)
            result_count = await self.redis_pool.llen(self.result_queue)
            if result_count > 1000:
                await self.redis_pool.ltrim(self.result_queue, 0, 999)
                self.logger.info(f"Cleaned up {result_count - 1000} old task results")
            
            # Clean up old task status entries (older than 24 hours)
            task_statuses = await self.redis_pool.hgetall(f"{self.cluster_name}:task_status")
            expired_tasks = []
            
            for task_id, status_data in task_statuses.items():
                try:
                    status_info = json.loads(status_data)
                    task_time = datetime.fromisoformat(status_info.get('created_at', current_time.isoformat()))
                    
                    if current_time - task_time > timedelta(hours=24):
                        expired_tasks.append(task_id)
                except Exception:
                    expired_tasks.append(task_id)  # Remove invalid entries
            
            if expired_tasks:
                await self.redis_pool.hdel(f"{self.cluster_name}:task_status", *expired_tasks)
                self.logger.info(f"Cleaned up {len(expired_tasks)} expired task status entries")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    async def shutdown(self):
        """Shutdown message queue gracefully"""
        self.running = False
        
        if self.redis_pool:
            await self.redis_pool.close()
        
        self.logger.info("Message queue shutdown complete")
    
    def _serialize_message(self, message: SwarmMessage) -> str:
        """Serialize message to JSON"""
        message_dict = asdict(message)
        message_dict['timestamp'] = message.timestamp.isoformat()
        if message.expires_at:
            message_dict['expires_at'] = message.expires_at.isoformat()
        message_dict['type'] = message.type.value
        message_dict['priority'] = message.priority.value
        
        return json.dumps(message_dict)
    
    def _deserialize_message(self, data: str) -> SwarmMessage:
        """Deserialize JSON to message"""
        message_dict = json.loads(data)
        
        # Convert string timestamps back to datetime
        message_dict['timestamp'] = datetime.fromisoformat(message_dict['timestamp'])
        if message_dict.get('expires_at'):
            message_dict['expires_at'] = datetime.fromisoformat(message_dict['expires_at'])
        
        # Convert enum strings back to enums
        message_dict['type'] = MessageType(message_dict['type'])
        message_dict['priority'] = Priority(message_dict['priority'])
        
        return SwarmMessage(**message_dict)
    
    async def _update_message_metrics(self, metric_name: str):
        """Update message metrics in Redis"""
        try:
            await self.redis_pool.hincrby(f"{self.cluster_name}:metrics", metric_name, 1)
        except Exception as e:
            self.logger.error(f"Failed to update metric {metric_name}: {e}")


# Factory function for easy initialization
async def create_message_queue(redis_urls: List[str], cluster_name: str = "tge-swarm") -> MessageQueue:
    """Create and initialize message queue"""
    mq = MessageQueue(redis_urls, cluster_name)
    await mq.initialize()
    return mq


# CLI interface for testing
if __name__ == "__main__":
    import sys
    
    async def test_message_queue():
        # Test with local Redis
        mq = await create_message_queue(["localhost:6379"])
        
        # Test basic functionality
        test_message = SwarmMessage(
            id=str(uuid.uuid4()),
            type=MessageType.HEALTH_CHECK,
            sender="test-agent",
            recipient=None,
            timestamp=datetime.now(),
            payload={"status": "healthy"},
            priority=Priority.LOW
        )
        
        # Publish test message
        success = await mq.publish_message(test_message)
        print(f"Message published: {success}")
        
        # Test task queue
        test_task = TaskDefinition(
            id=str(uuid.uuid4()),
            type="test-optimization",
            agent_type="any",
            priority=Priority.MEDIUM,
            payload={"target": "test.py"},
            created_at=datetime.now()
        )
        
        # Enqueue test task
        success = await mq.enqueue_task(test_task)
        print(f"Task enqueued: {success}")
        
        # Get statistics
        stats = await mq.get_task_statistics()
        print(f"Task statistics: {stats}")
        
        await mq.shutdown()
    
    asyncio.run(test_message_queue())