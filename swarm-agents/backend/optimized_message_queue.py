#!/usr/bin/env python3
"""
High-Performance Optimized Message Queue for TGE Swarm
Enhanced with connection pooling, batching, and async optimizations
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

# Import our performance optimizations
from performance.connection_pool import RedisConnectionPool
from performance.message_batching import MessageBatcher, BatchedMessage
from performance.async_optimizer import AsyncOptimizer, async_cache, async_retry, async_timeout
from performance.memory_manager import MemoryManager

# Import original classes for compatibility
from message_queue import MessageType, Priority, SwarmMessage, TaskDefinition


class OptimizedMessageQueue:
    """High-performance message queue with advanced optimizations"""
    
    def __init__(self, redis_cluster_urls: List[str], cluster_name: str = "tge-swarm"):
        self.cluster_urls = redis_cluster_urls
        self.cluster_name = cluster_name
        
        # Performance components
        self.connection_pool = RedisConnectionPool(
            redis_cluster_urls,
            min_connections=10,
            max_connections=100,
            connection_timeout=10,
            retry_on_timeout=True
        )
        
        self.message_batcher = MessageBatcher(
            max_batch_size=50,
            max_batch_delay=0.1,
            compression_threshold=1024
        )
        
        self.async_optimizer = AsyncOptimizer(
            max_workers=20,
            thread_pool_size=10
        )
        
        self.memory_manager = MemoryManager(
            gc_threshold_mb=200.0,
            monitoring_interval=120
        )
        
        # Message patterns (optimized with connection pooling)
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
        
        # State tracking with memory optimization
        self.active_agents: Set[str] = set()
        self.subscribers: Dict[str, Callable] = {}
        self.running = False
        
        # Performance metrics
        self.message_stats = {
            'sent': 0,
            'received': 0,
            'failed': 0,
            'queued_tasks': 0,
            'completed_tasks': 0,
            'batched_messages': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Caching for frequent operations
        self._agent_status_cache = {}
        self._cache_ttl = 30  # seconds
        
        self.logger = logging.getLogger(f"OptimizedMessageQueue.{cluster_name}")
        self.setup_logging()
    
    def setup_logging(self):
        """Setup optimized message queue logging"""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    async def initialize(self):
        """Initialize optimized message queue"""
        try:
            # Initialize performance components
            await self.connection_pool.initialize()
            await self.message_batcher.initialize()
            await self.async_optimizer.initialize()
            await self.memory_manager.initialize()
            
            # Register batch processors
            self.message_batcher.register_processor(
                "broadcast", self._process_broadcast_batch
            )
            self.message_batcher.register_processor(
                "agent_specific", self._process_agent_batch
            )
            
            # Initialize system keys
            await self._initialize_system_keys()
            
            # Create object pools for common operations
            self._create_object_pools()
            
            self.logger.info(f"Optimized message queue initialized with {len(self.cluster_urls)} Redis nodes")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize optimized message queue: {e}")
            raise
    
    def _create_object_pools(self):
        """Create object pools for memory optimization"""
        # Pool for dictionaries (message payloads)
        self.dict_pool = self.memory_manager.create_object_pool(
            "message_dicts",
            factory=lambda: {},
            reset_func=lambda d: d.clear(),
            max_size=200,
            min_size=20
        )
        
        # Pool for lists (batch collections)
        self.list_pool = self.memory_manager.create_object_pool(
            "message_lists",
            factory=lambda: [],
            reset_func=lambda l: l.clear(),
            max_size=100,
            min_size=10
        )
    
    async def _initialize_system_keys(self):
        """Initialize system keys with connection pooling"""
        async with self.connection_pool.get_connection() as connection:
            # Initialize agent registry
            await connection.hset(f"{self.cluster_name}:agents", mapping={})
            
            # Initialize metrics
            await connection.hset(f"{self.cluster_name}:metrics", mapping={
                'system_start': datetime.now().isoformat(),
                'total_messages': '0',
                'total_tasks': '0'
            })
        
        self.logger.info("System keys initialized with connection pooling")
    
    @async_retry(max_retries=3, backoff_factor=0.5)
    @async_timeout(10.0)
    async def publish_message(self, message: SwarmMessage) -> bool:
        """Publish message with optimizations"""
        try:
            # Use message batching for non-critical messages
            if message.priority in [Priority.LOW, Priority.MEDIUM]:
                return await self._publish_message_batched(message)
            else:
                # Direct publish for critical messages
                return await self._publish_message_direct(message)
                
        except Exception as e:
            self.logger.error(f"Failed to publish message {message.id}: {e}")
            self.message_stats['failed'] += 1
            return False
    
    async def _publish_message_direct(self, message: SwarmMessage) -> bool:
        """Direct message publishing for critical messages"""
        try:
            message_data = self._serialize_message_optimized(message)
            
            # Determine channel based on recipient
            if message.recipient:
                channel = f"{self.agent_channel}:{message.recipient}"
                batch_type = "agent_specific"
            else:
                channel = self.broadcast_channel
                batch_type = "broadcast"
            
            # Publish directly using connection pool
            async with self.connection_pool.get_connection() as connection:
                await connection.publish(channel, message_data)
            
            # Update stats
            self.message_stats['sent'] += 1
            await self._update_message_metrics_optimized('sent')
            
            return True
            
        except Exception as e:
            self.logger.error(f"Direct publish failed for message {message.id}: {e}")
            raise
    
    async def _publish_message_batched(self, message: SwarmMessage) -> bool:
        """Batched message publishing for performance"""
        try:
            # Determine batch type
            if message.recipient:
                batch_type = "agent_specific"
            else:
                batch_type = "broadcast"
            
            # Convert to dict for batching
            message_dict = {
                'id': message.id,
                'type': message.type.value,
                'sender': message.sender,
                'recipient': message.recipient,
                'timestamp': message.timestamp.isoformat(),
                'payload': message.payload,
                'priority': message.priority.value
            }
            
            # Add to batch
            await self.message_batcher.add_message(message_dict, batch_type)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Batched publish failed for message {message.id}: {e}")
            raise
    
    async def _process_broadcast_batch(self, batch: BatchedMessage):
        """Process broadcast message batch"""
        try:
            async with self.connection_pool.get_connection() as connection:
                # Use Redis pipeline for batch operations
                async with connection.pipeline() as pipe:
                    for message_dict in batch.messages:
                        message_data = json.dumps(message_dict, default=str)
                        pipe.publish(self.broadcast_channel, message_data)
                    
                    # Execute all publishes at once
                    await pipe.execute()
            
            # Update stats
            self.message_stats['sent'] += len(batch.messages)
            self.message_stats['batched_messages'] += 1
            
            self.logger.debug(f"Processed broadcast batch with {batch.message_count} messages")
            
        except Exception as e:
            self.logger.error(f"Error processing broadcast batch: {e}")
            raise
    
    async def _process_agent_batch(self, batch: BatchedMessage):
        """Process agent-specific message batch"""
        try:
            # Group messages by recipient
            recipient_groups = {}
            for message_dict in batch.messages:
                recipient = message_dict.get('recipient')
                if recipient:
                    if recipient not in recipient_groups:
                        recipient_groups[recipient] = []
                    recipient_groups[recipient].append(message_dict)
            
            # Send batched messages per recipient
            async with self.connection_pool.get_connection() as connection:
                async with connection.pipeline() as pipe:
                    for recipient, messages in recipient_groups.items():
                        channel = f"{self.agent_channel}:{recipient}"
                        
                        for message_dict in messages:
                            message_data = json.dumps(message_dict, default=str)
                            pipe.publish(channel, message_data)
                    
                    # Execute all publishes
                    await pipe.execute()
            
            # Update stats
            self.message_stats['sent'] += len(batch.messages)
            self.message_stats['batched_messages'] += 1
            
            self.logger.debug(f"Processed agent batch with {batch.message_count} messages for {len(recipient_groups)} recipients")
            
        except Exception as e:
            self.logger.error(f"Error processing agent batch: {e}")
            raise
    
    @async_cache(ttl_seconds=300, max_size=100)
    async def subscribe_to_agent_channel(self, agent_id: str, callback: Callable):
        """Subscribe to agent-specific channel with caching"""
        channel = f"{self.agent_channel}:{agent_id}"
        self.subscribers[channel] = callback
        
        # Register agent as active
        self.active_agents.add(agent_id)
        
        # Use connection pool for registration
        async with self.connection_pool.get_connection() as connection:
            await connection.hset(f"{self.cluster_name}:agents", agent_id, json.dumps({
                'status': 'active',
                'last_seen': datetime.now().isoformat(),
                'subscribed_at': datetime.now().isoformat()
            }))
        
        self.logger.info(f"Agent {agent_id} subscribed to channel {channel}")
    
    async def subscribe_to_broadcast(self, callback: Callable):
        """Subscribe to broadcast channel"""
        self.subscribers[self.broadcast_channel] = callback
        self.logger.info("Subscribed to broadcast channel")
    
    @async_timeout(30.0)
    async def enqueue_task(self, task: TaskDefinition) -> bool:
        """Enqueue task with optimizations"""
        try:
            # Use optimized serialization
            task_data = self._serialize_task_optimized(task)
            
            # Add to priority queue using connection pool
            priority_queue = self.priority_queues[task.priority]
            
            async with self.connection_pool.get_connection() as connection:
                # Use pipeline for atomic operations
                async with connection.pipeline() as pipe:
                    pipe.lpush(priority_queue, task_data)
                    pipe.hset(f"{self.cluster_name}:task_status", task.id, json.dumps({
                        'status': 'queued',
                        'created_at': task.created_at.isoformat() if task.created_at else datetime.now().isoformat(),
                        'priority': task.priority.name,
                        'type': task.type
                    }))
                    
                    await pipe.execute()
            
            self.message_stats['queued_tasks'] += 1
            await self._update_message_metrics_optimized('queued_tasks')
            
            self.logger.info(f"Enqueued task {task.id} with priority {task.priority.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to enqueue task {task.id}: {e}")
            return False
    
    @async_retry(max_retries=2, backoff_factor=0.1)
    async def dequeue_task(self, agent_id: str, agent_type: str = None) -> Optional[TaskDefinition]:
        """Dequeue task with connection pooling and retries"""
        try:
            async with self.connection_pool.get_connection() as connection:
                # Check priority queues in order
                for priority in [Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM, Priority.LOW]:
                    queue_name = self.priority_queues[priority]
                    
                    # Non-blocking pop to avoid connection holding
                    result = await connection.rpop(queue_name)
                    
                    if result:
                        task_dict = json.loads(result)
                        
                        # Convert back to TaskDefinition
                        task = self._deserialize_task_optimized(task_dict)
                        
                        # Check agent type compatibility
                        if agent_type and task.agent_type != agent_type and task.agent_type != "any":
                            # Put it back and continue
                            await connection.lpush(queue_name, result)
                            continue
                        
                        # Assign task to agent using pipeline
                        async with connection.pipeline() as pipe:
                            pipe.hset(f"{self.cluster_name}:task_status", task.id, json.dumps({
                                'status': 'assigned',
                                'assigned_to': agent_id,
                                'assigned_at': datetime.now().isoformat(),
                                'priority': task.priority.name,
                                'type': task.type
                            }))
                            
                            await pipe.execute()
                        
                        task.assigned_to = agent_id
                        self.logger.info(f"Assigned task {task.id} to agent {agent_id}")
                        return task
                
                return None  # No tasks available
                
        except Exception as e:
            self.logger.error(f"Failed to dequeue task for agent {agent_id}: {e}")
            return None
    
    async def submit_task_result(self, task_id: str, agent_id: str, 
                               result: Dict[str, Any], success: bool = True):
        """Submit task result with batching"""
        try:
            result_data = {
                'task_id': task_id,
                'agent_id': agent_id,
                'timestamp': datetime.now().isoformat(),
                'success': success,
                'result': result
            }
            
            # Use connection pool for result storage
            async with self.connection_pool.get_connection() as connection:
                async with connection.pipeline() as pipe:
                    # Store result
                    pipe.lpush(self.result_queue, json.dumps(result_data))
                    
                    # Update task status
                    status = 'completed' if success else 'failed'
                    pipe.hset(f"{self.cluster_name}:task_status", task_id, json.dumps({
                        'status': status,
                        'completed_at': datetime.now().isoformat(),
                        'agent_id': agent_id,
                        'success': success
                    }))
                    
                    await pipe.execute()
            
            if success:
                self.message_stats['completed_tasks'] += 1
                await self._update_message_metrics_optimized('completed_tasks')
            
            self.logger.info(f"Task {task_id} completed by {agent_id} with status: {'success' if success else 'failed'}")
            
        except Exception as e:
            self.logger.error(f"Failed to submit task result for {task_id}: {e}")
    
    @async_cache(ttl_seconds=60, max_size=50)
    async def get_task_results(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get task results with caching"""
        try:
            async with self.connection_pool.get_connection() as connection:
                results = await connection.lrange(self.result_queue, 0, limit - 1)
                return [json.loads(result) for result in results]
        except Exception as e:
            self.logger.error(f"Failed to get task results: {e}")
            return []
    
    async def start_message_listener(self):
        """Start optimized message listener"""
        self.running = True
        
        try:
            # Get dedicated connection for listening
            async with self.connection_pool.get_connection() as connection:
                pubsub = connection.pubsub()
                
                # Subscribe to all registered channels
                for channel in self.subscribers.keys():
                    await pubsub.subscribe(channel)
                    self.logger.info(f"Listening on channel: {channel}")
                
                # Optimized message processing loop
                while self.running:
                    try:
                        # Use shorter timeout for better responsiveness
                        message = await pubsub.get_message(timeout=0.1)
                        if message and message['type'] == 'message':
                            # Process message asynchronously
                            asyncio.create_task(self._handle_received_message_optimized(message))
                            
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        self.logger.error(f"Error processing message: {e}")
                        await asyncio.sleep(0.1)
                
        except Exception as e:
            self.logger.error(f"Message listener error: {e}")
        finally:
            if 'pubsub' in locals():
                await pubsub.close()
    
    async def _handle_received_message_optimized(self, redis_message):
        """Handle received message with optimizations"""
        try:
            channel = redis_message['channel']
            data = redis_message['data']
            
            # Deserialize message with optimization
            message = self._deserialize_message_optimized(data)
            
            # Find and call appropriate callback
            if channel in self.subscribers:
                callback = self.subscribers[channel]
                
                # Execute callback with async optimizer
                await self.async_optimizer._execute_optimized(
                    callback, (message,), {},
                    concurrency_limit=10,
                    timeout=30.0
                )
                
                self.message_stats['received'] += 1
                await self._update_message_metrics_optimized('received')
            
        except Exception as e:
            self.logger.error(f"Error handling received message: {e}")
    
    @async_cache(ttl_seconds=30, max_size=20)
    async def get_agent_status(self) -> Dict[str, Any]:
        """Get agent status with caching and connection pooling"""
        try:
            cache_key = f"agent_status_{int(time.time() // self._cache_ttl)}"
            
            if cache_key in self._agent_status_cache:
                self.message_stats['cache_hits'] += 1
                return self._agent_status_cache[cache_key]
            
            async with self.connection_pool.get_connection() as connection:
                agents_data = await connection.hgetall(f"{self.cluster_name}:agents")
                agents = {}
                
                for agent_id, data_str in agents_data.items():
                    agent_info = json.loads(data_str)
                    agents[agent_id] = agent_info
                
                result = {
                    'total_agents': len(agents),
                    'active_agents': len(self.active_agents),
                    'agents': agents,
                    'message_stats': self.message_stats.copy()
                }
                
                # Cache result
                self._agent_status_cache[cache_key] = result
                self.message_stats['cache_misses'] += 1
                
                return result
                
        except Exception as e:
            self.logger.error(f"Failed to get agent status: {e}")
            return {}
    
    async def get_task_statistics(self) -> Dict[str, Any]:
        """Get task statistics with connection pooling"""
        try:
            async with self.connection_pool.get_connection() as connection:
                # Use pipeline for multiple operations
                async with connection.pipeline() as pipe:
                    # Get queue lengths
                    for queue_name in self.priority_queues.values():
                        pipe.llen(queue_name)
                    
                    # Get task status data
                    pipe.hgetall(f"{self.cluster_name}:task_status")
                    pipe.llen(self.result_queue)
                    
                    results = await pipe.execute()
                
                # Parse results
                queue_lengths = {}
                for i, priority in enumerate([Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM, Priority.LOW]):
                    queue_lengths[priority.name] = results[i]
                
                task_statuses = results[4]  # Task status hash
                status_counts = {'queued': 0, 'assigned': 0, 'completed': 0, 'failed': 0}
                
                for task_id, status_data in task_statuses.items():
                    status_info = json.loads(status_data)
                    status = status_info.get('status', 'unknown')
                    if status in status_counts:
                        status_counts[status] += 1
                
                return {
                    'queue_lengths': queue_lengths,
                    'status_counts': status_counts,
                    'total_results': results[5],  # Result queue length
                    'message_stats': self.message_stats.copy(),
                    'connection_pool_metrics': self.connection_pool.get_metrics(),
                    'batcher_metrics': self.message_batcher.get_metrics(),
                    'async_metrics': self.async_optimizer.get_metrics()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get task statistics: {e}")
            return {}
    
    async def cleanup_expired_tasks(self):
        """Cleanup with optimized batch operations"""
        try:
            current_time = datetime.now()
            
            async with self.connection_pool.get_connection() as connection:
                # Clean up old results (keep last 1000)
                result_count = await connection.llen(self.result_queue)
                if result_count > 1000:
                    await connection.ltrim(self.result_queue, 0, 999)
                    self.logger.info(f"Cleaned up {result_count - 1000} old task results")
                
                # Get all task statuses
                task_statuses = await connection.hgetall(f"{self.cluster_name}:task_status")
                expired_tasks = []
                
                for task_id, status_data in task_statuses.items():
                    try:
                        status_info = json.loads(status_data)
                        task_time = datetime.fromisoformat(status_info.get('created_at', current_time.isoformat()))
                        
                        if current_time - task_time > timedelta(hours=24):
                            expired_tasks.append(task_id)
                    except Exception:
                        expired_tasks.append(task_id)  # Remove invalid entries
                
                # Batch delete expired tasks
                if expired_tasks:
                    # Use pipeline for batch deletion
                    async with connection.pipeline() as pipe:
                        for task_id in expired_tasks:
                            pipe.hdel(f"{self.cluster_name}:task_status", task_id)
                        await pipe.execute()
                    
                    self.logger.info(f"Cleaned up {len(expired_tasks)} expired task status entries")
                
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def _serialize_message_optimized(self, message: SwarmMessage) -> str:
        """Optimized message serialization"""
        # Use object pool for the dictionary
        message_dict = self.dict_pool.get()
        
        try:
            message_dict.update({
                'id': message.id,
                'type': message.type.value,
                'sender': message.sender,
                'recipient': message.recipient,
                'timestamp': message.timestamp.isoformat(),
                'payload': message.payload,
                'priority': message.priority.value
            })
            
            if message.expires_at:
                message_dict['expires_at'] = message.expires_at.isoformat()
            if message.correlation_id:
                message_dict['correlation_id'] = message.correlation_id
            
            result = json.dumps(message_dict, default=str)
            
        finally:
            # Return dictionary to pool
            self.dict_pool.return_object(message_dict)
        
        return result
    
    def _deserialize_message_optimized(self, data: str) -> SwarmMessage:
        """Optimized message deserialization"""
        message_dict = json.loads(data)
        
        # Convert string timestamps back to datetime
        message_dict['timestamp'] = datetime.fromisoformat(message_dict['timestamp'])
        if message_dict.get('expires_at'):
            message_dict['expires_at'] = datetime.fromisoformat(message_dict['expires_at'])
        
        # Convert enum strings back to enums
        message_dict['type'] = MessageType(message_dict['type'])
        message_dict['priority'] = Priority(message_dict['priority'])
        
        return SwarmMessage(**message_dict)
    
    def _serialize_task_optimized(self, task: TaskDefinition) -> str:
        """Optimized task serialization"""
        return json.dumps({
            'id': task.id,
            'type': task.type,
            'agent_type': task.agent_type,
            'priority': task.priority.value,
            'payload': task.payload,
            'timeout': task.timeout,
            'retries': task.retries,
            'created_at': task.created_at.isoformat() if task.created_at else datetime.now().isoformat(),
            'assigned_to': task.assigned_to,
            'dependencies': task.dependencies
        }, default=str)
    
    def _deserialize_task_optimized(self, task_dict: Dict[str, Any]) -> TaskDefinition:
        """Optimized task deserialization"""
        # Handle datetime conversion
        if 'created_at' in task_dict and task_dict['created_at']:
            task_dict['created_at'] = datetime.fromisoformat(task_dict['created_at'])
        
        # Convert priority back to enum
        task_dict['priority'] = Priority(task_dict['priority'])
        
        return TaskDefinition(**task_dict)
    
    async def _update_message_metrics_optimized(self, metric_name: str):
        """Update metrics with batching"""
        # Batch metric updates to reduce Redis load
        await self.message_batcher.add_message(
            {'metric': metric_name, 'timestamp': time.time()},
            'metrics'
        )
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        return {
            'message_stats': self.message_stats.copy(),
            'connection_pool': self.connection_pool.get_metrics(),
            'message_batcher': self.message_batcher.get_metrics(),
            'async_optimizer': self.async_optimizer.get_performance_report(),
            'memory_manager': self.memory_manager.get_memory_report(),
            'cache_stats': {
                'agent_status_cache_size': len(self._agent_status_cache),
                'cache_hit_rate': (
                    self.message_stats['cache_hits'] / 
                    max(1, self.message_stats['cache_hits'] + self.message_stats['cache_misses'])
                )
            }
        }
    
    async def shutdown(self):
        """Shutdown optimized message queue"""
        self.running = False
        
        # Flush all pending batches
        await self.message_batcher.flush_all_batches()
        
        # Shutdown components
        await self.message_batcher.shutdown()
        await self.async_optimizer.shutdown()
        await self.memory_manager.shutdown()
        await self.connection_pool.close()
        
        self.logger.info("Optimized message queue shutdown complete")


# Factory function for easy initialization
async def create_optimized_message_queue(redis_urls: List[str], 
                                       cluster_name: str = "tge-swarm") -> OptimizedMessageQueue:
    """Create and initialize optimized message queue"""
    mq = OptimizedMessageQueue(redis_urls, cluster_name)
    await mq.initialize()
    return mq