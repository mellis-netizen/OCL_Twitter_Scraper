#!/usr/bin/env python3
"""
Performance and Load Tests for TGE Swarm Backend
Tests system performance under load, throughput, and scalability
"""

import asyncio
import pytest
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import uuid
from typing import List, Dict, Any

from backend.message_queue import TaskDefinition, Priority
from backend.agent_manager import AgentStatus


@pytest.mark.performance
@pytest.mark.slow
class TestMessageQueuePerformance:
    """Test message queue performance characteristics"""
    
    async def test_message_throughput(self, message_queue, performance_monitor):
        """Test message publishing throughput"""
        num_messages = 1000
        batch_size = 100
        
        performance_monitor.start_timer("message_throughput")
        
        # Publish messages in batches
        for batch in range(0, num_messages, batch_size):
            batch_tasks = []
            for i in range(batch, min(batch + batch_size, num_messages)):
                from backend.message_queue import SwarmMessage, MessageType
                message = SwarmMessage(
                    id=f"perf-msg-{i}",
                    type=MessageType.STATUS_UPDATE,
                    sender=f"agent-{i % 10}",
                    recipient=None,
                    timestamp=datetime.now(timezone.utc),
                    payload={'index': i, 'batch': batch},
                    priority=Priority.MEDIUM
                )
                batch_tasks.append(message_queue.publish_message(message))
            
            await asyncio.gather(*batch_tasks)
        
        duration = performance_monitor.end_timer("message_throughput")
        
        # Calculate throughput
        throughput = num_messages / duration
        print(f"Message throughput: {throughput:.2f} messages/second")
        
        # Performance assertion
        assert throughput > 100, f"Message throughput too low: {throughput:.2f} msg/s"
        assert duration < 30, f"Total time too high: {duration:.2f}s"
    
    async def test_task_queue_performance(self, message_queue, performance_monitor):
        """Test task queue enqueue/dequeue performance"""
        num_tasks = 500
        num_agents = 5
        
        # Create tasks
        tasks = [
            TaskDefinition(
                id=f"perf-task-{i}",
                type="performance-test",
                agent_type="any",
                priority=Priority.MEDIUM,
                payload={'index': i},
                created_at=datetime.now(timezone.utc)
            )
            for i in range(num_tasks)
        ]
        
        # Test enqueue performance
        performance_monitor.start_timer("task_enqueue")
        enqueue_tasks = [message_queue.enqueue_task(task) for task in tasks]
        await asyncio.gather(*enqueue_tasks)
        enqueue_duration = performance_monitor.end_timer("task_enqueue")
        
        # Test dequeue performance
        performance_monitor.start_timer("task_dequeue")
        
        async def dequeue_worker(agent_id):
            dequeued = []
            while True:
                task = await message_queue.dequeue_task(f"perf-agent-{agent_id}", "any")
                if task is None:
                    break
                dequeued.append(task)
            return dequeued
        
        worker_tasks = [dequeue_worker(i) for i in range(num_agents)]
        results = await asyncio.gather(*worker_tasks)
        dequeue_duration = performance_monitor.end_timer("task_dequeue")
        
        # Calculate metrics
        total_dequeued = sum(len(result) for result in results)
        enqueue_rate = num_tasks / enqueue_duration
        dequeue_rate = total_dequeued / dequeue_duration
        
        print(f"Task enqueue rate: {enqueue_rate:.2f} tasks/second")
        print(f"Task dequeue rate: {dequeue_rate:.2f} tasks/second")
        print(f"Total tasks processed: {total_dequeued}/{num_tasks}")
        
        # Performance assertions
        assert enqueue_rate > 50, f"Enqueue rate too low: {enqueue_rate:.2f}"
        assert dequeue_rate > 50, f"Dequeue rate too low: {dequeue_rate:.2f}"
        assert total_dequeued == num_tasks, f"Not all tasks processed: {total_dequeued}/{num_tasks}"
    
    async def test_concurrent_message_handling(self, message_queue, performance_monitor):
        """Test concurrent message handling performance"""
        num_publishers = 10
        messages_per_publisher = 50
        
        performance_monitor.start_timer("concurrent_messaging")
        
        async def publisher_worker(publisher_id):
            published_count = 0
            for i in range(messages_per_publisher):
                from backend.message_queue import SwarmMessage, MessageType
                message = SwarmMessage(
                    id=f"concurrent-{publisher_id}-{i}",
                    type=MessageType.METRIC,
                    sender=f"publisher-{publisher_id}",
                    recipient=None,
                    timestamp=datetime.now(timezone.utc),
                    payload={'data': f'value-{i}'},
                    priority=Priority.LOW
                )
                
                success = await message_queue.publish_message(message)
                if success:
                    published_count += 1
                
                # Small delay to simulate realistic load
                await asyncio.sleep(0.01)
            
            return published_count
        
        # Run publishers concurrently
        publisher_tasks = [publisher_worker(i) for i in range(num_publishers)]
        results = await asyncio.gather(*publisher_tasks)
        
        duration = performance_monitor.end_timer("concurrent_messaging")
        
        total_published = sum(results)
        expected_total = num_publishers * messages_per_publisher
        throughput = total_published / duration
        
        print(f"Concurrent messaging throughput: {throughput:.2f} messages/second")
        print(f"Messages published: {total_published}/{expected_total}")
        print(f"Success rate: {(total_published/expected_total)*100:.1f}%")
        
        # Performance assertions
        assert total_published == expected_total, f"Some messages failed to publish"
        assert throughput > 30, f"Concurrent throughput too low: {throughput:.2f}"
    
    async def test_memory_usage_under_load(self, message_queue, test_metrics_collector):
        """Test memory usage under sustained load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Sustained load test
        num_rounds = 10
        messages_per_round = 100
        
        memory_samples = [initial_memory]
        
        for round_num in range(num_rounds):
            # Publish messages
            tasks = []
            for i in range(messages_per_round):
                from backend.message_queue import SwarmMessage, MessageType
                message = SwarmMessage(
                    id=f"memory-test-{round_num}-{i}",
                    type=MessageType.STATUS_UPDATE,
                    sender=f"load-agent-{i % 5}",
                    recipient=None,
                    timestamp=datetime.now(timezone.utc),
                    payload={'round': round_num, 'index': i, 'data': 'x' * 100},
                    priority=Priority.MEDIUM
                )
                tasks.append(message_queue.publish_message(message))
            
            await asyncio.gather(*tasks)
            
            # Sample memory usage
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)
            test_metrics_collector.set_gauge(f'memory_usage_round_{round_num}', current_memory)
            
            # Small delay between rounds
            await asyncio.sleep(0.1)
        
        final_memory = memory_samples[-1]
        memory_growth = final_memory - initial_memory
        max_memory = max(memory_samples)
        
        print(f"Initial memory: {initial_memory:.2f} MB")
        print(f"Final memory: {final_memory:.2f} MB")
        print(f"Memory growth: {memory_growth:.2f} MB")
        print(f"Peak memory: {max_memory:.2f} MB")
        
        # Memory usage assertions
        assert memory_growth < 100, f"Memory growth too high: {memory_growth:.2f} MB"
        assert max_memory < initial_memory + 150, f"Peak memory too high: {max_memory:.2f} MB"


@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.docker
class TestAgentManagerPerformance:
    """Test agent manager performance characteristics"""
    
    async def test_agent_deployment_performance(self, agent_manager, message_queue, performance_monitor):
        """Test agent deployment performance"""
        await agent_manager.initialize(message_queue)
        
        num_deployments = 5  # Reduced for test environment
        
        performance_monitor.start_timer("agent_deployment")
        
        deployment_tasks = []
        for i in range(num_deployments):
            task = agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=1)
            deployment_tasks.append(task)
        
        results = await asyncio.gather(*deployment_tasks, return_exceptions=True)
        duration = performance_monitor.end_timer("agent_deployment")
        
        # Count successful deployments
        successful = sum(1 for result in results if not isinstance(result, Exception))
        deployment_rate = successful / duration if duration > 0 else 0
        
        print(f"Agent deployment rate: {deployment_rate:.2f} deployments/second")
        print(f"Successful deployments: {successful}/{num_deployments}")
        
        # Performance assertions (relaxed for test environment)
        assert successful >= num_deployments * 0.5, f"Too many deployment failures"
        
        # Cleanup deployed agents
        for result in results:
            if not isinstance(result, Exception) and result:
                for agent_id in result:
                    await agent_manager.stop_agent(agent_id, force=True)
    
    async def test_agent_status_query_performance(self, agent_manager, message_queue, performance_monitor):
        """Test agent status query performance"""
        await agent_manager.initialize(message_queue)
        
        # Deploy some agents for testing
        instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=3)
        
        try:
            num_queries = 100
            
            performance_monitor.start_timer("status_queries")
            
            query_tasks = []
            for i in range(num_queries):
                if i % 2 == 0:
                    # Query all agents
                    task = agent_manager.get_agent_status()
                else:
                    # Query specific agent
                    agent_id = instances[i % len(instances)]
                    task = agent_manager.get_agent_status(agent_id)
                query_tasks.append(task)
            
            await asyncio.gather(*query_tasks)
            duration = performance_monitor.end_timer("status_queries")
            
            query_rate = num_queries / duration
            
            print(f"Agent status query rate: {query_rate:.2f} queries/second")
            
            # Performance assertions
            assert query_rate > 10, f"Query rate too low: {query_rate:.2f}"
            
        finally:
            # Cleanup
            for agent_id in instances:
                await agent_manager.stop_agent(agent_id, force=True)
    
    async def test_task_assignment_performance(self, agent_manager, message_queue, performance_monitor):
        """Test task assignment performance"""
        await agent_manager.initialize(message_queue)
        
        # Deploy agents
        instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=3)
        
        # Set agents as healthy
        for agent_id in instances:
            agent_manager.agents[agent_id].status = AgentStatus.HEALTHY
        
        try:
            num_tasks = 50
            
            # Create tasks
            tasks = [
                TaskDefinition(
                    id=f"assign-perf-{i}",
                    type="assignment-test",
                    agent_type="scraping-efficiency",
                    priority=Priority.MEDIUM,
                    payload={'index': i},
                    created_at=datetime.now(timezone.utc)
                )
                for i in range(num_tasks)
            ]
            
            performance_monitor.start_timer("task_assignment")
            
            assignment_tasks = []
            for task in tasks:
                assignment_tasks.append(agent_manager.assign_task_to_agent(task))
            
            assignments = await asyncio.gather(*assignment_tasks)
            duration = performance_monitor.end_timer("task_assignment")
            
            successful_assignments = sum(1 for assignment in assignments if assignment is not None)
            assignment_rate = successful_assignments / duration
            
            print(f"Task assignment rate: {assignment_rate:.2f} assignments/second")
            print(f"Successful assignments: {successful_assignments}/{num_tasks}")
            
            # Performance assertions
            assert assignment_rate > 5, f"Assignment rate too low: {assignment_rate:.2f}"
            assert successful_assignments >= num_tasks * 0.8, f"Too many assignment failures"
            
        finally:
            # Cleanup
            for agent_id in instances:
                await agent_manager.stop_agent(agent_id, force=True)


@pytest.mark.performance
@pytest.mark.slow
class TestSystemPerformance:
    """Test overall system performance"""
    
    async def test_end_to_end_workflow_performance(self, full_backend_stack, performance_monitor):
        """Test end-to-end workflow performance"""
        message_queue = full_backend_stack['message_queue']
        agent_manager = full_backend_stack['agent_manager']
        
        # Deploy agents
        instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=2)
        
        # Set agents as healthy
        for agent_id in instances:
            agent_manager.agents[agent_id].status = AgentStatus.HEALTHY
        
        try:
            num_workflows = 20
            
            performance_monitor.start_timer("e2e_workflow")
            
            workflow_tasks = []
            for i in range(num_workflows):
                task = self._execute_workflow(message_queue, agent_manager, i)
                workflow_tasks.append(task)
            
            results = await asyncio.gather(*workflow_tasks, return_exceptions=True)
            duration = performance_monitor.end_timer("e2e_workflow")
            
            successful_workflows = sum(1 for result in results if not isinstance(result, Exception))
            workflow_rate = successful_workflows / duration
            
            print(f"End-to-end workflow rate: {workflow_rate:.2f} workflows/second")
            print(f"Successful workflows: {successful_workflows}/{num_workflows}")
            
            # Performance assertions
            assert workflow_rate > 1, f"Workflow rate too low: {workflow_rate:.2f}"
            assert successful_workflows >= num_workflows * 0.7, f"Too many workflow failures"
            
        finally:
            # Cleanup
            for agent_id in instances:
                await agent_manager.stop_agent(agent_id, force=True)
    
    async def _execute_workflow(self, message_queue, agent_manager, workflow_id):
        """Execute a single end-to-end workflow"""
        # Create task
        task = TaskDefinition(
            id=f"e2e-workflow-{workflow_id}",
            type="end-to-end-test",
            agent_type="scraping-efficiency",
            priority=Priority.MEDIUM,
            payload={'workflow_id': workflow_id},
            created_at=datetime.now(timezone.utc)
        )
        
        # Enqueue task
        await message_queue.enqueue_task(task)
        
        # Assign to agent
        assigned_agent = await agent_manager.assign_task_to_agent(task)
        if not assigned_agent:
            raise Exception(f"Failed to assign task {task.id}")
        
        # Simulate task execution and completion
        await message_queue.submit_task_result(
            task.id,
            assigned_agent,
            {'status': 'completed', 'workflow_id': workflow_id},
            success=True
        )
        
        return workflow_id
    
    async def test_concurrent_system_load(self, full_backend_stack, performance_monitor, test_metrics_collector):
        """Test system performance under concurrent load"""
        message_queue = full_backend_stack['message_queue']
        agent_manager = full_backend_stack['agent_manager']
        coordination_service = full_backend_stack['coordination_service']
        
        # Deploy agents
        instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=3)
        
        # Set agents as healthy
        for agent_id in instances:
            agent_manager.agents[agent_id].status = AgentStatus.HEALTHY
        
        try:
            performance_monitor.start_timer("concurrent_load")
            
            # Create concurrent load generators
            load_tasks = [
                self._message_load_generator(message_queue, 100, "msg_load"),
                self._task_load_generator(message_queue, 50, "task_load"),
                self._status_query_load_generator(agent_manager, 30, "status_load"),
                self._coordination_load_generator(coordination_service, 20, "coord_load")
            ]
            
            # Run all load generators concurrently
            results = await asyncio.gather(*load_tasks, return_exceptions=True)
            duration = performance_monitor.end_timer("concurrent_load")
            
            # Analyze results
            successful_loads = sum(1 for result in results if not isinstance(result, Exception))
            
            print(f"Concurrent load test duration: {duration:.2f} seconds")
            print(f"Successful load generators: {successful_loads}/{len(load_tasks)}")
            
            # Collect final metrics
            metrics_summary = test_metrics_collector.get_summary()
            print(f"Metrics summary: {metrics_summary}")
            
            # Performance assertions
            assert successful_loads >= len(load_tasks) * 0.75, f"Too many load generator failures"
            
        finally:
            # Cleanup
            for agent_id in instances:
                await agent_manager.stop_agent(agent_id, force=True)
    
    async def _message_load_generator(self, message_queue, num_messages, load_id):
        """Generate message publishing load"""
        for i in range(num_messages):
            from backend.message_queue import SwarmMessage, MessageType
            message = SwarmMessage(
                id=f"{load_id}-{i}",
                type=MessageType.STATUS_UPDATE,
                sender=f"load-agent-{i % 5}",
                recipient=None,
                timestamp=datetime.now(timezone.utc),
                payload={'load_id': load_id, 'index': i},
                priority=Priority.LOW
            )
            await message_queue.publish_message(message)
            await asyncio.sleep(0.01)  # Small delay
        return num_messages
    
    async def _task_load_generator(self, message_queue, num_tasks, load_id):
        """Generate task queue load"""
        for i in range(num_tasks):
            task = TaskDefinition(
                id=f"{load_id}-task-{i}",
                type="load-test",
                agent_type="any",
                priority=Priority.MEDIUM,
                payload={'load_id': load_id, 'index': i},
                created_at=datetime.now(timezone.utc)
            )
            await message_queue.enqueue_task(task)
            await asyncio.sleep(0.02)  # Small delay
        return num_tasks
    
    async def _status_query_load_generator(self, agent_manager, num_queries, load_id):
        """Generate agent status query load"""
        for i in range(num_queries):
            await agent_manager.get_agent_status()
            await asyncio.sleep(0.05)  # Small delay
        return num_queries
    
    async def _coordination_load_generator(self, coordination_service, num_events, load_id):
        """Generate coordination event load"""
        for i in range(num_events):
            await coordination_service.record_coordination_event(
                f"load-agent-{i % 3}",
                f"load_event_{load_id}",
                {'index': i, 'load_id': load_id}
            )
            await asyncio.sleep(0.03)  # Small delay
        return num_events


@pytest.mark.performance
class TestResourceUtilization:
    """Test resource utilization characteristics"""
    
    async def test_cpu_utilization_under_load(self, message_queue, test_metrics_collector):
        """Test CPU utilization under sustained load"""
        import psutil
        
        # Monitor CPU usage during load test
        cpu_samples = []
        
        async def cpu_monitor():
            for _ in range(20):  # Monitor for 20 intervals
                cpu_percent = psutil.cpu_percent(interval=0.1)
                cpu_samples.append(cpu_percent)
                test_metrics_collector.set_gauge('cpu_utilization', cpu_percent)
                await asyncio.sleep(0.1)
        
        async def load_generator():
            # Generate sustained load
            for i in range(200):
                from backend.message_queue import SwarmMessage, MessageType
                message = SwarmMessage(
                    id=f"cpu-load-{i}",
                    type=MessageType.METRIC,
                    sender=f"cpu-test-{i % 3}",
                    recipient=None,
                    timestamp=datetime.now(timezone.utc),
                    payload={'data': 'x' * 500},  # Larger payload
                    priority=Priority.MEDIUM
                )
                await message_queue.publish_message(message)
                await asyncio.sleep(0.01)
        
        # Run monitoring and load generation concurrently
        await asyncio.gather(cpu_monitor(), load_generator())
        
        # Analyze CPU usage
        avg_cpu = statistics.mean(cpu_samples)
        max_cpu = max(cpu_samples)
        
        print(f"Average CPU utilization: {avg_cpu:.2f}%")
        print(f"Peak CPU utilization: {max_cpu:.2f}%")
        
        # Resource utilization assertions
        assert avg_cpu < 80, f"Average CPU too high: {avg_cpu:.2f}%"
        assert max_cpu < 95, f"Peak CPU too high: {max_cpu:.2f}%"
    
    async def test_response_time_distribution(self, message_queue, performance_monitor):
        """Test response time distribution under load"""
        num_operations = 100
        response_times = []
        
        for i in range(num_operations):
            start_time = time.time()
            
            # Perform operation
            from backend.message_queue import SwarmMessage, MessageType
            message = SwarmMessage(
                id=f"response-time-{i}",
                type=MessageType.STATUS_UPDATE,
                sender=f"response-agent-{i % 5}",
                recipient=None,
                timestamp=datetime.now(timezone.utc),
                payload={'index': i},
                priority=Priority.MEDIUM
            )
            
            await message_queue.publish_message(message)
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            response_times.append(response_time)
            
            performance_monitor.record_timing('message_publish_time', response_time)
        
        # Calculate statistics
        avg_response = statistics.mean(response_times)
        p50_response = statistics.median(response_times)
        p95_response = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 5 else max(response_times)
        p99_response = statistics.quantiles(response_times, n=100)[98] if len(response_times) > 10 else max(response_times)
        
        print(f"Average response time: {avg_response:.2f}ms")
        print(f"P50 response time: {p50_response:.2f}ms")
        print(f"P95 response time: {p95_response:.2f}ms")
        print(f"P99 response time: {p99_response:.2f}ms")
        
        # Response time assertions
        assert avg_response < 50, f"Average response time too high: {avg_response:.2f}ms"
        assert p95_response < 100, f"P95 response time too high: {p95_response:.2f}ms"
        assert p99_response < 200, f"P99 response time too high: {p99_response:.2f}ms"


@pytest.mark.performance
class TestScalabilityLimits:
    """Test scalability limits and bottlenecks"""
    
    async def test_connection_limit_handling(self, message_queue, test_metrics_collector):
        """Test handling of connection limits"""
        max_connections = 50  # Reasonable limit for testing
        
        # Simulate many concurrent connections
        connection_tasks = []
        
        async def simulate_connection(conn_id):
            try:
                # Simulate connection activity
                for i in range(5):
                    from backend.message_queue import SwarmMessage, MessageType
                    message = SwarmMessage(
                        id=f"conn-{conn_id}-{i}",
                        type=MessageType.STATUS_UPDATE,
                        sender=f"conn-agent-{conn_id}",
                        recipient=None,
                        timestamp=datetime.now(timezone.utc),
                        payload={'conn_id': conn_id, 'index': i},
                        priority=Priority.LOW
                    )
                    await message_queue.publish_message(message)
                    await asyncio.sleep(0.01)
                return True
            except Exception as e:
                print(f"Connection {conn_id} failed: {e}")
                return False
        
        # Create many concurrent connections
        for i in range(max_connections):
            task = simulate_connection(i)
            connection_tasks.append(task)
        
        # Wait for all connections to complete
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        successful_connections = sum(1 for result in results if result is True)
        success_rate = successful_connections / max_connections
        
        print(f"Successful connections: {successful_connections}/{max_connections}")
        print(f"Connection success rate: {success_rate:.2f}")
        
        test_metrics_collector.set_gauge('connection_success_rate', success_rate)
        
        # Scalability assertions
        assert success_rate > 0.8, f"Connection success rate too low: {success_rate:.2f}"
    
    async def test_queue_capacity_limits(self, message_queue, test_metrics_collector):
        """Test behavior at queue capacity limits"""
        # Fill queue to capacity
        queue_limit = 1000  # Test with reasonable limit
        
        # Enqueue many tasks quickly
        enqueue_tasks = []
        for i in range(queue_limit):
            task = TaskDefinition(
                id=f"capacity-task-{i}",
                type="capacity-test",
                agent_type="any",
                priority=Priority.MEDIUM,
                payload={'index': i},
                created_at=datetime.now(timezone.utc)
            )
            enqueue_tasks.append(message_queue.enqueue_task(task))
        
        # Execute all enqueue operations
        results = await asyncio.gather(*enqueue_tasks, return_exceptions=True)
        
        successful_enqueues = sum(1 for result in results if result is True)
        enqueue_success_rate = successful_enqueues / queue_limit
        
        print(f"Successful enqueues: {successful_enqueues}/{queue_limit}")
        print(f"Enqueue success rate: {enqueue_success_rate:.2f}")
        
        # Get queue statistics
        stats = await message_queue.get_task_statistics()
        total_queued = sum(stats['queue_lengths'].values())
        
        print(f"Total tasks in queues: {total_queued}")
        
        test_metrics_collector.set_gauge('queue_capacity_utilization', total_queued / queue_limit)
        
        # Capacity assertions
        assert enqueue_success_rate > 0.9, f"Enqueue success rate too low: {enqueue_success_rate:.2f}"
        assert total_queued >= successful_enqueues * 0.9, f"Queue count mismatch"


# Utility functions for performance testing
def generate_load_profile(duration_seconds: int, target_rps: int) -> List[float]:
    """Generate load profile with specified RPS over duration"""
    intervals = []
    interval_duration = 1.0 / target_rps  # Time between requests
    
    current_time = 0.0
    while current_time < duration_seconds:
        intervals.append(current_time)
        current_time += interval_duration
    
    return intervals


async def measure_latency(operation_func, *args, **kwargs) -> float:
    """Measure latency of an async operation in milliseconds"""
    start_time = time.time()
    await operation_func(*args, **kwargs)
    end_time = time.time()
    return (end_time - start_time) * 1000  # Convert to milliseconds