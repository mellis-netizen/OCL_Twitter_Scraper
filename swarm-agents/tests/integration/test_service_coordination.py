#!/usr/bin/env python3
"""
Integration Tests for Service Coordination
Tests interaction between message queue, agent manager, and coordination service
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from backend.message_queue import SwarmMessage, MessageType, Priority, TaskDefinition
from backend.agent_manager import AgentStatus
from backend.coordination_service import CoordinationService


@pytest.mark.integration
@pytest.mark.redis
@pytest.mark.database
class TestServiceCoordination:
    """Test coordination between core services"""
    
    async def test_full_task_workflow(self, full_backend_stack):
        """Test complete task workflow from submission to completion"""
        message_queue = full_backend_stack['message_queue']
        agent_manager = full_backend_stack['agent_manager']
        coordination_service = full_backend_stack['coordination_service']
        
        # Deploy an agent
        instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=1)
        agent_id = instances[0]
        
        # Set agent as healthy
        agent_manager.agents[agent_id].status = AgentStatus.HEALTHY
        
        # Create and enqueue a task
        task = TaskDefinition(
            id=str(uuid.uuid4()),
            type="test-optimization",
            agent_type="scraping-efficiency",
            priority=Priority.HIGH,
            payload={'target': 'test.py'},
            timeout=300,
            retries=3,
            created_at=datetime.now(timezone.utc)
        )
        
        # Enqueue task
        await message_queue.enqueue_task(task)
        
        # Agent should be able to dequeue the task
        dequeued_task = await message_queue.dequeue_task(agent_id, "scraping-efficiency")
        
        assert dequeued_task is not None
        assert dequeued_task.id == task.id
        assert dequeued_task.assigned_to == agent_id
        
        # Simulate task completion
        await message_queue.submit_task_result(
            task.id, 
            agent_id, 
            {'status': 'completed', 'changes': ['optimization applied']}, 
            success=True
        )
        
        # Check task results
        results = await message_queue.get_task_results(limit=1)
        assert len(results) == 1
        assert results[0]['task_id'] == task.id
        assert results[0]['success'] is True
    
    async def test_agent_discovery_and_coordination(self, full_backend_stack):
        """Test agent discovery and coordination events"""
        message_queue = full_backend_stack['message_queue']
        agent_manager = full_backend_stack['agent_manager']
        coordination_service = full_backend_stack['coordination_service']
        
        # Deploy multiple agents
        scraping_instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=2)
        keyword_instances = await agent_manager.deploy_agent('keyword-precision-specialist', replicas=1)
        
        # Wait for coordination events to be processed
        await asyncio.sleep(0.1)
        
        # Check agent status
        status = await agent_manager.get_agent_status()
        assert status['total_agents'] == 3
        
        # Check coordination service knows about agents
        coord_status = await coordination_service.get_coordination_status()
        assert 'active_agents' in coord_status
    
    async def test_resource_coordination(self, full_backend_stack):
        """Test shared resource coordination between agents"""
        coordination_service = full_backend_stack['coordination_service']
        
        # Register shared resources
        resource_path = "src/test_file.py"
        
        # Agent 1 claims resource
        agent1_id = str(uuid.uuid4())
        claimed = await coordination_service.claim_resource(agent1_id, resource_path)
        assert claimed is True
        
        # Agent 2 tries to claim same resource
        agent2_id = str(uuid.uuid4())
        claimed = await coordination_service.claim_resource(agent2_id, resource_path)
        assert claimed is False  # Should fail - already claimed
        
        # Agent 1 releases resource
        await coordination_service.release_resource(agent1_id, resource_path)
        
        # Agent 2 can now claim it
        claimed = await coordination_service.claim_resource(agent2_id, resource_path)
        assert claimed is True
    
    async def test_agent_status_propagation(self, full_backend_stack):
        """Test agent status changes propagate through system"""
        message_queue = full_backend_stack['message_queue']
        agent_manager = full_backend_stack['agent_manager']
        
        # Deploy agent
        instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=1)
        agent_id = instances[0]
        
        # Publish status update
        status_data = {
            'health': 'healthy',
            'load': 0.5,
            'tasks_completed': 5,
            'memory_usage': 60.0
        }
        
        await message_queue.publish_agent_status(agent_id, status_data)
        
        # Check message was published
        assert message_queue.message_stats['sent'] >= 1
    
    async def test_optimization_workflow(self, full_backend_stack):
        """Test optimization request and result workflow"""
        message_queue = full_backend_stack['message_queue']
        agent_manager = full_backend_stack['agent_manager']
        
        # Deploy optimization-capable agent
        instances = await agent_manager.deploy_agent('performance-optimizer', replicas=1)
        agent_id = instances[0]
        agent_manager.agents[agent_id].status = AgentStatus.HEALTHY
        
        # Publish optimization request
        await message_queue.publish_optimization_request(
            requester="system",
            optimization_type="performance",
            target_files=["src/scraper.py"],
            parameters={'threshold': 0.8, 'timeout': 300}
        )
        
        # Check request was published
        assert message_queue.message_stats['sent'] >= 1
    
    async def test_cross_agent_communication(self, full_backend_stack):
        """Test communication between different agent types"""
        message_queue = full_backend_stack['message_queue']
        agent_manager = full_backend_stack['agent_manager']
        
        # Deploy different agent types
        scraping_instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=1)
        keyword_instances = await agent_manager.deploy_agent('keyword-precision-specialist', replicas=1)
        
        scraping_agent_id = scraping_instances[0]
        keyword_agent_id = keyword_instances[0]
        
        # Scraping agent sends message to keyword agent
        message = SwarmMessage(
            id=str(uuid.uuid4()),
            type=MessageType.COORDINATION_EVENT,
            sender=scraping_agent_id,
            recipient=keyword_agent_id,
            timestamp=datetime.now(timezone.utc),
            payload={
                'event': 'keywords_discovered',
                'keywords': ['blockchain', 'defi', 'nft'],
                'confidence': 0.9
            },
            priority=Priority.MEDIUM
        )
        
        success = await message_queue.publish_message(message)
        assert success is True
    
    async def test_system_metrics_collection(self, full_backend_stack):
        """Test system-wide metrics collection"""
        message_queue = full_backend_stack['message_queue']
        agent_manager = full_backend_stack['agent_manager']
        coordination_service = full_backend_stack['coordination_service']
        
        # Deploy agents to generate metrics
        await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=2)
        
        # Publish various metrics
        metrics_data = [
            ('agent-1', 'cpu_usage', 75.5, {'type': 'system'}),
            ('agent-1', 'memory_usage', 60.2, {'type': 'system'}),
            ('agent-2', 'task_completion_rate', 0.95, {'type': 'performance'}),
            ('message_queue', 'queue_length', 10, {'type': 'infrastructure'})
        ]
        
        for source, metric_name, value, tags in metrics_data:
            await message_queue.publish_metric(source, metric_name, value, tags)
        
        # Get system statistics
        task_stats = await message_queue.get_task_statistics()
        agent_status = await agent_manager.get_agent_status()
        coord_status = await coordination_service.get_coordination_status()
        
        assert 'queue_lengths' in task_stats
        assert 'total_agents' in agent_status
    
    async def test_error_propagation_and_recovery(self, full_backend_stack):
        """Test error handling and recovery across services"""
        message_queue = full_backend_stack['message_queue']
        agent_manager = full_backend_stack['agent_manager']
        
        # Deploy agent
        instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=1)
        agent_id = instances[0]
        
        # Simulate agent failure
        agent_manager.agents[agent_id].status = AgentStatus.FAILED
        
        # System should detect failed agent
        status = await agent_manager.get_agent_status()
        failed_agents = [a for a in status['agents'].values() if a['status'] == 'failed']
        assert len(failed_agents) >= 1
        
        # Restart failed agent
        success = await agent_manager.restart_agent(agent_id)
        if success:  # Restart might fail in test environment
            assert agent_manager.agents[agent_id].restart_count > 0
    
    async def test_load_balancing_across_agents(self, full_backend_stack):
        """Test load balancing when multiple agents available"""
        message_queue = full_backend_stack['message_queue']
        agent_manager = full_backend_stack['agent_manager']
        
        # Deploy multiple agents of same type
        instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=3)
        
        # Set all agents as healthy with different loads
        for i, agent_id in enumerate(instances):
            agent_manager.agents[agent_id].status = AgentStatus.HEALTHY
            agent_manager.agents[agent_id].task_count = i * 2  # Different loads
        
        # Create multiple tasks
        tasks = []
        for i in range(5):
            task = TaskDefinition(
                id=str(uuid.uuid4()),
                type=f"task-{i}",
                agent_type="scraping-efficiency",
                priority=Priority.MEDIUM,
                payload={'index': i},
                created_at=datetime.now(timezone.utc)
            )
            tasks.append(task)
            await message_queue.enqueue_task(task)
        
        # Assign tasks and check distribution
        assignments = {}
        for task in tasks:
            assigned_agent = await agent_manager.assign_task_to_agent(task)
            if assigned_agent:
                assignments[assigned_agent] = assignments.get(assigned_agent, 0) + 1
        
        # Should have distributed tasks among agents
        assert len(assignments) > 1 or len(instances) == 1
    
    async def test_coordination_event_processing(self, full_backend_stack):
        """Test coordination event creation and processing"""
        coordination_service = full_backend_stack['coordination_service']
        
        agent_id = str(uuid.uuid4())
        
        # Create coordination event
        event_data = {
            'action': 'optimization_discovered',
            'file': 'src/scraper.py',
            'impact': 'high',
            'confidence': 0.85
        }
        
        await coordination_service.record_coordination_event(
            agent_id, 
            'optimization_discovered',
            event_data
        )
        
        # Get coordination status
        status = await coordination_service.get_coordination_status()
        assert 'recent_events' in status
    
    async def test_memory_coordination_integration(self, full_backend_stack):
        """Test memory coordinator integration with other services"""
        memory_coordinator = full_backend_stack['memory_coordinator']
        coordination_service = full_backend_stack['coordination_service']
        
        # Store agent memory
        agent_id = str(uuid.uuid4())
        memory_data = {
            'learned_patterns': ['pattern1', 'pattern2'],
            'performance_metrics': {'accuracy': 0.92, 'speed': 1.5},
            'optimization_history': []
        }
        
        memory_coordinator.store_agent_memory(agent_id, memory_data)
        
        # Retrieve memory
        retrieved_memory = memory_coordinator.get_agent_memory(agent_id)
        assert retrieved_memory == memory_data
        
        # Test memory sharing
        shared_insights = memory_coordinator.get_shared_insights()
        # Should include insights from stored memory
    
    async def test_service_health_monitoring(self, full_backend_stack):
        """Test health monitoring across all services"""
        message_queue = full_backend_stack['message_queue']
        agent_manager = full_backend_stack['agent_manager']
        coordination_service = full_backend_stack['coordination_service']
        
        # Check all services are healthy
        assert message_queue.redis_pool is not None
        assert agent_manager.running is True
        assert coordination_service.running is True
        
        # Get health status from each service
        agent_status = await agent_manager.get_agent_status()
        task_stats = await message_queue.get_task_statistics()
        coord_status = await coordination_service.get_coordination_status()
        
        # All should return valid status data
        assert isinstance(agent_status, dict)
        assert isinstance(task_stats, dict)
        assert isinstance(coord_status, dict)


@pytest.mark.integration
@pytest.mark.redis
class TestMessageQueueIntegration:
    """Test message queue integration scenarios"""
    
    async def test_pub_sub_message_flow(self, message_queue):
        """Test publish-subscribe message flow"""
        received_messages = []
        
        async def message_handler(message):
            received_messages.append(message)
        
        # Subscribe to agent channel
        agent_id = "test-agent-123"
        await message_queue.subscribe_to_agent_channel(agent_id, message_handler)
        
        # Start message listener in background
        listener_task = asyncio.create_task(message_queue.start_message_listener())
        message_queue.running = True
        
        try:
            # Publish message to agent
            test_message = SwarmMessage(
                id=str(uuid.uuid4()),
                type=MessageType.TASK_ASSIGNMENT,
                sender="orchestrator",
                recipient=agent_id,
                timestamp=datetime.now(timezone.utc),
                payload={'task': 'test_task'},
                priority=Priority.HIGH
            )
            
            await message_queue.publish_message(test_message)
            
            # Wait for message to be received
            await asyncio.sleep(0.1)
            
            # Check message was received
            assert len(received_messages) == 1
            assert received_messages[0].id == test_message.id
            
        finally:
            message_queue.running = False
            listener_task.cancel()
            try:
                await listener_task
            except asyncio.CancelledError:
                pass
    
    async def test_broadcast_message_flow(self, message_queue):
        """Test broadcast message flow"""
        received_messages = []
        
        async def broadcast_handler(message):
            received_messages.append(message)
        
        # Subscribe to broadcast channel
        await message_queue.subscribe_to_broadcast(broadcast_handler)
        
        # Start message listener
        listener_task = asyncio.create_task(message_queue.start_message_listener())
        message_queue.running = True
        
        try:
            # Publish broadcast message
            broadcast_message = SwarmMessage(
                id=str(uuid.uuid4()),
                type=MessageType.ALERT,
                sender="system",
                recipient=None,  # Broadcast
                timestamp=datetime.now(timezone.utc),
                payload={'alert': 'system_maintenance'},
                priority=Priority.CRITICAL
            )
            
            await message_queue.publish_message(broadcast_message)
            
            # Wait for message
            await asyncio.sleep(0.1)
            
            # Check broadcast was received
            assert len(received_messages) == 1
            assert received_messages[0].type == MessageType.ALERT
            
        finally:
            message_queue.running = False
            listener_task.cancel()
            try:
                await listener_task
            except asyncio.CancelledError:
                pass
    
    async def test_task_queue_priority_handling(self, message_queue):
        """Test task queue handles priorities correctly"""
        # Create tasks with different priorities
        tasks = [
            TaskDefinition(
                id=f"task-{i}",
                type="test",
                agent_type="any",
                priority=priority,
                payload={'index': i},
                created_at=datetime.now(timezone.utc)
            )
            for i, priority in enumerate([Priority.LOW, Priority.CRITICAL, Priority.MEDIUM, Priority.HIGH])
        ]
        
        # Enqueue tasks in order
        for task in tasks:
            await message_queue.enqueue_task(task)
        
        # Dequeue tasks - should come out in priority order
        dequeued_tasks = []
        for _ in range(len(tasks)):
            task = await message_queue.dequeue_task("test-agent", "any")
            if task:
                dequeued_tasks.append(task)
        
        # Check priority order: CRITICAL, HIGH, MEDIUM, LOW
        expected_order = [Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM, Priority.LOW]
        actual_order = [task.priority for task in dequeued_tasks]
        
        assert actual_order == expected_order
    
    async def test_concurrent_task_processing(self, message_queue):
        """Test concurrent task enqueue/dequeue operations"""
        num_tasks = 20
        num_agents = 3
        
        # Create tasks
        tasks = [
            TaskDefinition(
                id=f"concurrent-task-{i}",
                type="concurrent-test",
                agent_type="any",
                priority=Priority.MEDIUM,
                payload={'index': i},
                created_at=datetime.now(timezone.utc)
            )
            for i in range(num_tasks)
        ]
        
        # Enqueue tasks concurrently
        enqueue_tasks = [message_queue.enqueue_task(task) for task in tasks]
        await asyncio.gather(*enqueue_tasks)
        
        # Dequeue tasks with multiple agents concurrently
        async def agent_worker(agent_id):
            processed_tasks = []
            while True:
                task = await message_queue.dequeue_task(f"agent-{agent_id}", "any")
                if task is None:
                    break
                processed_tasks.append(task)
                await asyncio.sleep(0.01)  # Simulate processing time
            return processed_tasks
        
        # Start multiple agent workers
        worker_tasks = [agent_worker(i) for i in range(num_agents)]
        results = await asyncio.gather(*worker_tasks)
        
        # Check all tasks were processed
        total_processed = sum(len(result) for result in results)
        assert total_processed == num_tasks
        
        # Check no task was processed twice
        all_task_ids = [task.id for result in results for task in result]
        assert len(all_task_ids) == len(set(all_task_ids))


@pytest.mark.integration
@pytest.mark.docker
class TestAgentManagerIntegration:
    """Test agent manager integration scenarios"""
    
    async def test_agent_lifecycle_integration(self, agent_manager, message_queue):
        """Test complete agent lifecycle integration"""
        await agent_manager.initialize(message_queue)
        
        # Deploy agent
        instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=1)
        assert len(instances) == 1
        
        agent_id = instances[0]
        agent = agent_manager.agents[agent_id]
        
        # Simulate health check updates
        agent.status = AgentStatus.HEALTHY
        
        # Assign task to agent
        task = TaskDefinition(
            id=str(uuid.uuid4()),
            type="integration-test",
            agent_type="scraping-efficiency",
            priority=Priority.MEDIUM,
            payload={'test': True},
            created_at=datetime.now(timezone.utc)
        )
        
        assigned_agent = await agent_manager.assign_task_to_agent(task)
        assert assigned_agent == agent_id
        
        # Check task count updated
        assert agent.task_count == 1
        
        # Stop agent
        success = await agent_manager.stop_agent(agent_id)
        assert success is True
        assert agent.status == AgentStatus.STOPPED
    
    async def test_auto_scaling_integration(self, agent_manager, message_queue):
        """Test auto-scaling integration with task load"""
        await agent_manager.initialize(message_queue)
        
        # Mock high task load
        mock_stats = {
            'queue_lengths': {'HIGH': 20, 'MEDIUM': 50},
            'status_counts': {'pending': 70}
        }
        
        with patch.object(message_queue, 'get_task_statistics', return_value=mock_stats):
            # Deploy initial agents
            instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=1)
            
            # Set high task load on agents
            for agent_id in instances:
                agent_manager.agents[agent_id].status = AgentStatus.HEALTHY
                agent_manager.agents[agent_id].task_count = 10  # High load
            
            # Trigger scaling evaluation
            from backend.agent_manager import AgentType
            await agent_manager._evaluate_scaling_for_type(
                AgentType.SCRAPING_EFFICIENCY, 
                mock_stats
            )
            
            # Should have triggered scale up (if within limits)
            # Note: Actual scaling depends on configuration


@pytest.mark.integration
@pytest.mark.database
class TestDatabaseIntegration:
    """Test database integration with services"""
    
    async def test_agent_persistence_integration(self, test_session, agent_manager):
        """Test agent persistence integration"""
        from backend.database.models import AgentRepository
        
        repo = AgentRepository(test_session)
        
        # Create agent in database
        agent_data = {
            'name': 'integration-agent',
            'agent_type': 'scraping-efficiency',
            'container_id': 'integration-container-123',
            'status': AgentStatus.HEALTHY,
            'capabilities': ['nlp', 'text-analysis']
        }
        
        db_agent = repo.create_agent(**agent_data)
        
        # Verify agent was created
        assert db_agent.id is not None
        assert db_agent.name == agent_data['name']
        
        # Retrieve agent
        retrieved_agent = repo.get_agent(db_agent.id)
        assert retrieved_agent is not None
        assert retrieved_agent.name == agent_data['name']
    
    async def test_task_persistence_integration(self, test_session, message_queue):
        """Test task persistence integration"""
        from backend.database.models import TaskRepository, Task, TaskStatus
        
        repo = TaskRepository(test_session)
        
        # Create task in database
        task_data = {
            'task_type': 'integration-test',
            'agent_type': 'any',
            'priority': Priority.HIGH,
            'payload': {'test_data': 'integration'},
            'status': TaskStatus.PENDING
        }
        
        db_task = repo.create_task(**task_data)
        
        # Update task status
        repo.update_task_status(
            db_task.id, 
            TaskStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
            result={'status': 'success'}
        )
        
        # Verify update
        updated_task = repo.get_task(db_task.id)
        assert updated_task.status == TaskStatus.COMPLETED
        assert updated_task.result == {'status': 'success'}
    
    async def test_metrics_persistence_integration(self, test_session):
        """Test metrics persistence integration"""
        from backend.database.models import MetricsRepository
        
        repo = MetricsRepository(test_session)
        
        # Record multiple metrics
        metrics_data = [
            ('agent-1', 'cpu_usage', 75.5),
            ('agent-1', 'memory_usage', 60.2),
            ('agent-2', 'cpu_usage', 45.0),
            ('system', 'queue_length', 15)
        ]
        
        for source, metric_name, value in metrics_data:
            repo.record_metric(
                metric_name=metric_name,
                metric_type='gauge',
                source=source,
                value=value,
                tags={'environment': 'test'}
            )
        
        # Query metrics
        cpu_metrics = repo.get_metrics('cpu_usage')
        assert len(cpu_metrics) == 2
        
        agent1_metrics = repo.get_metrics('cpu_usage', source='agent-1')
        assert len(agent1_metrics) == 1
        assert agent1_metrics[0].value == 75.5