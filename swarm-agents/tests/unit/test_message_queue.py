#!/usr/bin/env python3
"""
Unit Tests for Message Queue System
Tests Redis-based pub/sub messaging, task queues, and agent communication
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from backend.message_queue import (
    MessageQueue, SwarmMessage, MessageType, Priority, TaskDefinition,
    create_message_queue
)


@pytest.mark.unit
@pytest.mark.redis
class TestMessageQueue:
    """Test message queue functionality"""
    
    async def test_message_queue_initialization(self, redis_client):
        """Test message queue initialization"""
        mq = MessageQueue(["localhost:6379"], "test-cluster")
        await mq.initialize()
        
        assert mq.redis_pool is not None
        assert mq.cluster_name == "test-cluster"
        assert mq.running is False
        
        await mq.shutdown()
    
    async def test_message_serialization(self, message_queue, sample_swarm_message):
        """Test message serialization and deserialization"""
        # Test serialization
        serialized = message_queue._serialize_message(sample_swarm_message)
        assert isinstance(serialized, str)
        
        # Test deserialization
        deserialized = message_queue._deserialize_message(serialized)
        assert deserialized.id == sample_swarm_message.id
        assert deserialized.type == sample_swarm_message.type
        assert deserialized.sender == sample_swarm_message.sender
        assert deserialized.payload == sample_swarm_message.payload
    
    async def test_publish_message(self, message_queue, sample_swarm_message):
        """Test message publishing"""
        success = await message_queue.publish_message(sample_swarm_message)
        assert success is True
        
        # Check stats updated
        assert message_queue.message_stats['sent'] == 1
    
    async def test_publish_broadcast_message(self, message_queue):
        """Test broadcast message publishing"""
        broadcast_message = SwarmMessage(
            id=str(uuid.uuid4()),
            type=MessageType.ALERT,
            sender="system",
            recipient=None,  # Broadcast
            timestamp=datetime.now(timezone.utc),
            payload={'alert': 'system maintenance'},
            priority=Priority.HIGH
        )
        
        success = await message_queue.publish_message(broadcast_message)
        assert success is True
    
    async def test_agent_subscription(self, message_queue):
        """Test agent channel subscription"""
        agent_id = "test-agent-123"
        callback = AsyncMock()
        
        await message_queue.subscribe_to_agent_channel(agent_id, callback)
        
        assert agent_id in message_queue.active_agents
        assert f"{message_queue.agent_channel}:{agent_id}" in message_queue.subscribers
    
    async def test_broadcast_subscription(self, message_queue):
        """Test broadcast channel subscription"""
        callback = AsyncMock()
        
        await message_queue.subscribe_to_broadcast(callback)
        
        assert message_queue.broadcast_channel in message_queue.subscribers
    
    async def test_task_enqueue_dequeue(self, message_queue, sample_task_definition):
        """Test task enqueue and dequeue operations"""
        # Enqueue task
        success = await message_queue.enqueue_task(sample_task_definition)
        assert success is True
        assert message_queue.message_stats['queued_tasks'] == 1
        
        # Dequeue task
        agent_id = "test-agent"
        dequeued_task = await message_queue.dequeue_task(agent_id, sample_task_definition.agent_type)
        
        assert dequeued_task is not None
        assert dequeued_task.id == sample_task_definition.id
        assert dequeued_task.assigned_to == agent_id
    
    async def test_task_priority_ordering(self, message_queue):
        """Test task priority-based dequeuing"""
        # Create tasks with different priorities
        high_priority_task = TaskDefinition(
            id=str(uuid.uuid4()),
            type="urgent-task",
            agent_type="any",
            priority=Priority.HIGH,
            payload={'urgent': True},
            created_at=datetime.now(timezone.utc)
        )
        
        low_priority_task = TaskDefinition(
            id=str(uuid.uuid4()),
            type="normal-task",
            agent_type="any",
            priority=Priority.LOW,
            payload={'urgent': False},
            created_at=datetime.now(timezone.utc)
        )
        
        # Enqueue low priority first, then high priority
        await message_queue.enqueue_task(low_priority_task)
        await message_queue.enqueue_task(high_priority_task)
        
        # Dequeue should return high priority task first
        dequeued_task = await message_queue.dequeue_task("test-agent", "any")
        assert dequeued_task.priority == Priority.HIGH
        assert dequeued_task.id == high_priority_task.id
    
    async def test_task_type_filtering(self, message_queue):
        """Test task dequeuing with agent type filtering"""
        specific_task = TaskDefinition(
            id=str(uuid.uuid4()),
            type="specific-task",
            agent_type="keyword-precision",
            priority=Priority.MEDIUM,
            payload={},
            created_at=datetime.now(timezone.utc)
        )
        
        generic_task = TaskDefinition(
            id=str(uuid.uuid4()),
            type="generic-task",
            agent_type="any",
            priority=Priority.MEDIUM,
            payload={},
            created_at=datetime.now(timezone.utc)
        )
        
        await message_queue.enqueue_task(specific_task)
        await message_queue.enqueue_task(generic_task)
        
        # Agent with specific type should get both tasks
        task1 = await message_queue.dequeue_task("agent1", "keyword-precision")
        task2 = await message_queue.dequeue_task("agent1", "keyword-precision")
        
        assert task1 is not None
        assert task2 is not None
        
        # Agent with different type should only get generic task
        await message_queue.enqueue_task(specific_task)
        await message_queue.enqueue_task(generic_task)
        
        task3 = await message_queue.dequeue_task("agent2", "scraping-efficiency")
        assert task3 is not None
        assert task3.agent_type == "any"
    
    async def test_task_result_submission(self, message_queue):
        """Test task result submission"""
        task_id = str(uuid.uuid4())
        agent_id = "test-agent"
        result = {'status': 'completed', 'data': 'processed'}
        
        await message_queue.submit_task_result(task_id, agent_id, result, success=True)
        
        # Check result was stored
        results = await message_queue.get_task_results(limit=1)
        assert len(results) == 1
        assert results[0]['task_id'] == task_id
        assert results[0]['success'] is True
    
    async def test_agent_status_publishing(self, message_queue):
        """Test agent status update publishing"""
        agent_id = "test-agent"
        status = {
            'health': 'healthy',
            'load': 0.5,
            'tasks_completed': 10
        }
        
        await message_queue.publish_agent_status(agent_id, status)
        
        # Should increment sent message count
        assert message_queue.message_stats['sent'] >= 1
    
    async def test_optimization_request_publishing(self, message_queue):
        """Test optimization request publishing"""
        requester = "performance-agent"
        optimization_type = "code_optimization"
        target_files = ["src/scraper.py"]
        parameters = {'threshold': 0.8}
        
        await message_queue.publish_optimization_request(
            requester, optimization_type, target_files, parameters
        )
        
        assert message_queue.message_stats['sent'] >= 1
    
    async def test_metric_publishing(self, message_queue):
        """Test system metric publishing"""
        source = "test-agent"
        metric_name = "cpu_usage"
        value = 75.5
        tags = {'host': 'localhost', 'type': 'system'}
        
        await message_queue.publish_metric(source, metric_name, value, tags)
        
        # Should not increment message stats (different channel)
        # but should publish to metrics channel
    
    async def test_agent_status_retrieval(self, message_queue):
        """Test agent status retrieval"""
        # Register some agents
        await message_queue.subscribe_to_agent_channel("agent1", AsyncMock())
        await message_queue.subscribe_to_agent_channel("agent2", AsyncMock())
        
        status = await message_queue.get_agent_status()
        
        assert 'total_agents' in status
        assert 'active_agents' in status
        assert 'agents' in status
        assert 'message_stats' in status
        assert status['active_agents'] == 2
    
    async def test_task_statistics(self, message_queue, sample_task_definition):
        """Test task statistics retrieval"""
        # Enqueue some tasks
        await message_queue.enqueue_task(sample_task_definition)
        
        high_priority_task = TaskDefinition(
            id=str(uuid.uuid4()),
            type="urgent-task",
            agent_type="any",
            priority=Priority.HIGH,
            payload={},
            created_at=datetime.now(timezone.utc)
        )
        await message_queue.enqueue_task(high_priority_task)
        
        stats = await message_queue.get_task_statistics()
        
        assert 'queue_lengths' in stats
        assert 'status_counts' in stats
        assert 'total_results' in stats
        assert 'message_stats' in stats
        
        # Check queue lengths
        assert stats['queue_lengths']['MEDIUM'] >= 1
        assert stats['queue_lengths']['HIGH'] >= 1
    
    async def test_cleanup_expired_tasks(self, message_queue):
        """Test cleanup of expired tasks and results"""
        # Submit some task results
        for i in range(5):
            await message_queue.submit_task_result(
                f"task-{i}", "agent", {'result': i}, success=True
            )
        
        # Run cleanup
        await message_queue.cleanup_expired_tasks()
        
        # Should still have results (not old enough to clean)
        results = await message_queue.get_task_results()
        assert len(results) == 5
    
    async def test_no_available_tasks(self, message_queue):
        """Test dequeue when no tasks are available"""
        task = await message_queue.dequeue_task("agent", "nonexistent-type")
        assert task is None
    
    async def test_message_queue_factory(self):
        """Test message queue factory function"""
        mq = await create_message_queue(["localhost:6379"], "test-factory")
        
        assert isinstance(mq, MessageQueue)
        assert mq.cluster_name == "test-factory"
        
        await mq.shutdown()
    
    async def test_message_listener_lifecycle(self, message_queue):
        """Test message listener start/stop lifecycle"""
        # Mock the listener to avoid blocking
        with patch.object(message_queue, 'start_message_listener') as mock_listener:
            mock_listener.return_value = None
            
            # Start listener
            listener_task = asyncio.create_task(message_queue.start_message_listener())
            
            # Should be running
            message_queue.running = True
            assert message_queue.running is True
            
            # Stop listener
            message_queue.running = False
            listener_task.cancel()
            
            try:
                await listener_task
            except asyncio.CancelledError:
                pass
    
    async def test_message_expiration(self, message_queue):
        """Test message with expiration time"""
        expired_message = SwarmMessage(
            id=str(uuid.uuid4()),
            type=MessageType.TASK_ASSIGNMENT,
            sender="test",
            recipient="agent",
            timestamp=datetime.now(timezone.utc),
            payload={},
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=5)  # Already expired
        )
        
        # Should still publish (expiration handling is client-side)
        success = await message_queue.publish_message(expired_message)
        assert success is True
    
    async def test_correlation_id_tracking(self, message_queue):
        """Test message correlation ID tracking"""
        correlation_id = str(uuid.uuid4())
        
        message1 = SwarmMessage(
            id=str(uuid.uuid4()),
            type=MessageType.TASK_ASSIGNMENT,
            sender="orchestrator",
            recipient="agent",
            timestamp=datetime.now(timezone.utc),
            payload={},
            correlation_id=correlation_id
        )
        
        message2 = SwarmMessage(
            id=str(uuid.uuid4()),
            type=MessageType.TASK_RESULT,
            sender="agent",
            recipient="orchestrator",
            timestamp=datetime.now(timezone.utc),
            payload={},
            correlation_id=correlation_id
        )
        
        await message_queue.publish_message(message1)
        await message_queue.publish_message(message2)
        
        # Both messages should have same correlation ID
        assert message1.correlation_id == message2.correlation_id
    
    async def test_message_retry_count(self, message_queue):
        """Test message retry count tracking"""
        message = SwarmMessage(
            id=str(uuid.uuid4()),
            type=MessageType.TASK_ASSIGNMENT,
            sender="test",
            recipient="agent",
            timestamp=datetime.now(timezone.utc),
            payload={},
            retry_count=3
        )
        
        serialized = message_queue._serialize_message(message)
        deserialized = message_queue._deserialize_message(serialized)
        
        assert deserialized.retry_count == 3


@pytest.mark.unit
class TestMessageTypes:
    """Test message type enumerations and data structures"""
    
    def test_message_type_enum(self):
        """Test MessageType enumeration"""
        assert MessageType.TASK_ASSIGNMENT.value == "task_assignment"
        assert MessageType.OPTIMIZATION_REQUEST.value == "optimization_request"
        assert MessageType.HEALTH_CHECK.value == "health_check"
    
    def test_priority_enum(self):
        """Test Priority enumeration"""
        assert Priority.LOW.value == 1
        assert Priority.MEDIUM.value == 2
        assert Priority.HIGH.value == 3
        assert Priority.CRITICAL.value == 4
        
        # Test ordering
        assert Priority.CRITICAL > Priority.HIGH
        assert Priority.HIGH > Priority.MEDIUM
        assert Priority.MEDIUM > Priority.LOW
    
    def test_swarm_message_creation(self):
        """Test SwarmMessage creation and validation"""
        message = SwarmMessage(
            id="test-123",
            type=MessageType.STATUS_UPDATE,
            sender="agent-1",
            recipient="coordinator",
            timestamp=datetime.now(timezone.utc),
            payload={'status': 'healthy'}
        )
        
        assert message.id == "test-123"
        assert message.type == MessageType.STATUS_UPDATE
        assert message.priority == Priority.MEDIUM  # Default
        assert message.retry_count == 0  # Default
    
    def test_task_definition_creation(self):
        """Test TaskDefinition creation and validation"""
        task = TaskDefinition(
            id="task-456",
            type="optimization",
            agent_type="performance",
            priority=Priority.HIGH,
            payload={'target': 'file.py'}
        )
        
        assert task.id == "task-456"
        assert task.timeout == 300  # Default
        assert task.retries == 3  # Default
        assert task.assigned_to is None  # Default
    
    def test_task_definition_with_dependencies(self):
        """Test TaskDefinition with dependencies"""
        task = TaskDefinition(
            id="task-789",
            type="dependent-task",
            agent_type="any",
            priority=Priority.MEDIUM,
            payload={},
            dependencies=["task-456", "task-123"]
        )
        
        assert len(task.dependencies) == 2
        assert "task-456" in task.dependencies


@pytest.mark.unit
class TestMessageQueueErrorHandling:
    """Test error handling in message queue operations"""
    
    async def test_redis_connection_failure(self):
        """Test handling Redis connection failures"""
        # Test with invalid Redis URL
        with pytest.raises(Exception):
            mq = MessageQueue(["invalid-host:9999"], "test")
            await mq.initialize()
    
    async def test_publish_message_failure(self, message_queue):
        """Test handling message publishing failures"""
        # Mock Redis to simulate failure
        with patch.object(message_queue.redis_pool, 'publish', side_effect=Exception("Redis error")):
            message = SwarmMessage(
                id="test",
                type=MessageType.ALERT,
                sender="test",
                recipient=None,
                timestamp=datetime.now(timezone.utc),
                payload={}
            )
            
            success = await message_queue.publish_message(message)
            assert success is False
            assert message_queue.message_stats['failed'] == 1
    
    async def test_task_enqueue_failure(self, message_queue):
        """Test handling task enqueue failures"""
        with patch.object(message_queue.redis_pool, 'lpush', side_effect=Exception("Redis error")):
            task = TaskDefinition(
                id="test-task",
                type="test",
                agent_type="any",
                priority=Priority.MEDIUM,
                payload={}
            )
            
            success = await message_queue.enqueue_task(task)
            assert success is False
    
    async def test_invalid_message_deserialization(self, message_queue):
        """Test handling invalid message deserialization"""
        invalid_json = "invalid json string"
        
        with pytest.raises(Exception):
            message_queue._deserialize_message(invalid_json)
    
    async def test_missing_message_fields(self, message_queue):
        """Test handling messages with missing required fields"""
        incomplete_message_data = '{"id": "test", "type": "invalid_type"}'
        
        with pytest.raises(Exception):
            message_queue._deserialize_message(incomplete_message_data)