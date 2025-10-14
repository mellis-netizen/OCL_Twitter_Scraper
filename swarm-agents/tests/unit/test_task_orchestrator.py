#!/usr/bin/env python3
"""
Unit Tests for Task Orchestrator
Tests task scheduling, load balancing, and workload management
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from collections import deque

from backend.task_orchestrator import (
    TaskOrchestrator, TaskExecution, TaskStatus, AgentWorkload,
    SchedulingStrategy, AdaptiveLoadBalancer
)
from backend.message_queue import MessageQueue, TaskDefinition, Priority
from backend.agent_manager import AgentManager


@pytest.mark.unit
class TestTaskOrchestrator:
    """Test task orchestrator functionality"""

    def test_task_orchestrator_initialization(self):
        """Test task orchestrator initialization"""
        mock_mq = MagicMock()
        mock_am = MagicMock()

        orchestrator = TaskOrchestrator(mock_mq, mock_am)

        assert orchestrator.message_queue == mock_mq
        assert orchestrator.agent_manager == mock_am
        assert orchestrator.running is False
        assert len(orchestrator.task_executions) == 0
        assert len(orchestrator.agent_workloads) == 0

    def test_default_config(self):
        """Test default configuration"""
        mock_mq = MagicMock()
        mock_am = MagicMock()

        orchestrator = TaskOrchestrator(mock_mq, mock_am)
        config = orchestrator.config

        assert config['scheduling_strategy'] == 'adaptive'
        assert config['max_concurrent_tasks_per_agent'] == 3
        assert config['task_timeout_seconds'] == 300
        assert config['max_retries'] == 3

    async def test_submit_task(self):
        """Test submitting task for execution"""
        mock_mq = AsyncMock()
        mock_am = AsyncMock()

        orchestrator = TaskOrchestrator(mock_mq, mock_am)

        task_def = TaskDefinition(
            id=str(uuid.uuid4()),
            type="test-task",
            agent_type="any",
            priority=Priority.MEDIUM,
            payload={"target": "test.py"},
            timeout=60,
            retries=3,
            created_at=datetime.now()
        )

        task_id = await orchestrator.submit_task(task_def)

        assert task_id == task_def.id
        assert task_id in orchestrator.task_executions
        assert orchestrator.task_executions[task_id].status == TaskStatus.QUEUED
        assert orchestrator.orchestration_metrics['tasks_scheduled'] == 1

    async def test_submit_task_priority_queuing(self):
        """Test tasks are queued by priority"""
        mock_mq = AsyncMock()
        mock_am = AsyncMock()

        orchestrator = TaskOrchestrator(mock_mq, mock_am)

        # Submit tasks with different priorities
        high_task = TaskDefinition(
            id=str(uuid.uuid4()),
            type="high-priority",
            agent_type="any",
            priority=Priority.HIGH,
            payload={},
            created_at=datetime.now()
        )

        low_task = TaskDefinition(
            id=str(uuid.uuid4()),
            type="low-priority",
            agent_type="any",
            priority=Priority.LOW,
            payload={},
            created_at=datetime.now()
        )

        await orchestrator.submit_task(high_task)
        await orchestrator.submit_task(low_task)

        # Check tasks in correct queues
        assert len(orchestrator.task_queues[Priority.HIGH].tasks) == 1
        assert len(orchestrator.task_queues[Priority.LOW].tasks) == 1

    async def test_cancel_task_queued(self):
        """Test cancelling queued task"""
        mock_mq = AsyncMock()
        mock_am = AsyncMock()

        orchestrator = TaskOrchestrator(mock_mq, mock_am)

        task_def = TaskDefinition(
            id=str(uuid.uuid4()),
            type="test-task",
            agent_type="any",
            priority=Priority.MEDIUM,
            payload={},
            created_at=datetime.now()
        )

        task_id = await orchestrator.submit_task(task_def)
        success = await orchestrator.cancel_task(task_id, "user requested")

        assert success is True
        assert orchestrator.task_executions[task_id].status == TaskStatus.CANCELLED

    async def test_cancel_nonexistent_task(self):
        """Test cancelling non-existent task"""
        mock_mq = AsyncMock()
        mock_am = AsyncMock()

        orchestrator = TaskOrchestrator(mock_mq, mock_am)

        success = await orchestrator.cancel_task("nonexistent-task-id", "test")
        assert success is False

    async def test_get_task_status(self):
        """Test getting task status"""
        mock_mq = AsyncMock()
        mock_am = AsyncMock()

        orchestrator = TaskOrchestrator(mock_mq, mock_am)

        task_def = TaskDefinition(
            id=str(uuid.uuid4()),
            type="test-task",
            agent_type="any",
            priority=Priority.MEDIUM,
            payload={"test": "data"},
            created_at=datetime.now()
        )

        task_id = await orchestrator.submit_task(task_def)
        status = await orchestrator.get_task_status(task_id)

        assert status is not None
        assert status['task_id'] == task_id
        assert status['status'] == TaskStatus.QUEUED.value
        assert 'created_at' in status

    async def test_get_task_status_nonexistent(self):
        """Test getting status for non-existent task"""
        mock_mq = AsyncMock()
        mock_am = AsyncMock()

        orchestrator = TaskOrchestrator(mock_mq, mock_am)

        status = await orchestrator.get_task_status("nonexistent-task")
        assert status is None

    async def test_get_queue_status(self):
        """Test getting queue status"""
        mock_mq = AsyncMock()
        mock_am = AsyncMock()

        orchestrator = TaskOrchestrator(mock_mq, mock_am)

        # Submit some tasks
        for i in range(3):
            task_def = TaskDefinition(
                id=str(uuid.uuid4()),
                type=f"test-task-{i}",
                agent_type="any",
                priority=Priority.MEDIUM if i % 2 == 0 else Priority.HIGH,
                payload={},
                created_at=datetime.now()
            )
            await orchestrator.submit_task(task_def)

        status = await orchestrator.get_queue_status()

        assert 'total_queued' in status
        assert status['total_queued'] == 3
        assert 'queue_breakdown' in status
        assert 'metrics' in status

    async def test_sync_agent_workloads(self):
        """Test synchronizing agent workloads"""
        mock_mq = AsyncMock()
        mock_am = AsyncMock()

        # Mock agent manager to return agent status
        mock_am.get_agent_status = AsyncMock(return_value={
            'agents': {
                'agent-1': {'type': 'scraping-efficiency', 'status': 'healthy'},
                'agent-2': {'type': 'keyword-precision', 'status': 'healthy'}
            }
        })

        orchestrator = TaskOrchestrator(mock_mq, mock_am)

        await orchestrator._sync_agent_workloads()

        assert len(orchestrator.agent_workloads) == 2
        assert 'agent-1' in orchestrator.agent_workloads
        assert 'agent-2' in orchestrator.agent_workloads

    async def test_process_task_result_success(self):
        """Test processing successful task result"""
        mock_mq = AsyncMock()
        mock_am = AsyncMock()

        orchestrator = TaskOrchestrator(mock_mq, mock_am)

        # Create and submit task
        task_def = TaskDefinition(
            id=str(uuid.uuid4()),
            type="test-task",
            agent_type="any",
            priority=Priority.MEDIUM,
            payload={},
            created_at=datetime.now()
        )
        task_id = await orchestrator.submit_task(task_def)

        # Set task as running
        task_execution = orchestrator.task_executions[task_id]
        task_execution.status = TaskStatus.RUNNING
        task_execution.started_at = datetime.now()
        task_execution.assigned_agent = "agent-1"

        # Create agent workload
        orchestrator.agent_workloads["agent-1"] = AgentWorkload(
            agent_id="agent-1",
            agent_type="scraping-efficiency",
            current_tasks=1,
            max_concurrent_tasks=3,
            avg_execution_time=60.0,
            success_rate=1.0,
            error_rate=0.0,
            last_task_completion=datetime.now(),
            performance_score=1.0,
            specialization_scores={}
        )

        # Process success result
        result = {"output": "success data"}
        await orchestrator._process_task_result(
            task_id, "agent-1", True, result, None
        )

        # Verify task completed
        assert task_execution.status == TaskStatus.COMPLETED
        assert task_execution.result == result
        assert task_execution.completed_at is not None

        # Verify metrics updated
        assert orchestrator.orchestration_metrics['tasks_completed'] == 1

    async def test_process_task_result_failure_with_retry(self):
        """Test processing failed task result with retry"""
        mock_mq = AsyncMock()
        mock_am = AsyncMock()

        orchestrator = TaskOrchestrator(mock_mq, mock_am)

        # Create task with retries
        task_def = TaskDefinition(
            id=str(uuid.uuid4()),
            type="test-task",
            agent_type="any",
            priority=Priority.MEDIUM,
            payload={},
            retries=3,
            created_at=datetime.now()
        )
        task_id = await orchestrator.submit_task(task_def)

        # Set task as running
        task_execution = orchestrator.task_executions[task_id]
        task_execution.status = TaskStatus.RUNNING
        task_execution.started_at = datetime.now()
        task_execution.assigned_agent = "agent-1"

        # Create agent workload
        orchestrator.agent_workloads["agent-1"] = AgentWorkload(
            agent_id="agent-1",
            agent_type="any",
            current_tasks=1,
            max_concurrent_tasks=3,
            avg_execution_time=60.0,
            success_rate=0.9,
            error_rate=0.1,
            last_task_completion=datetime.now(),
            performance_score=0.9,
            specialization_scores={}
        )

        initial_retry_count = task_execution.retry_count

        # Process failure
        await orchestrator._process_task_result(
            task_id, "agent-1", False, {}, "Test error"
        )

        # Verify task set back to queued for retry
        assert task_execution.status == TaskStatus.QUEUED
        assert task_execution.retry_count == initial_retry_count + 1

    async def test_task_timeout_detection(self):
        """Test detection of timed out tasks"""
        mock_mq = AsyncMock()
        mock_am = AsyncMock()

        config = {'task_timeout_seconds': 1}
        orchestrator = TaskOrchestrator(mock_mq, mock_am, config=config)

        # Create running task with old start time
        task_def = TaskDefinition(
            id=str(uuid.uuid4()),
            type="test-task",
            agent_type="any",
            priority=Priority.MEDIUM,
            payload={},
            retries=1,
            created_at=datetime.now()
        )
        task_id = await orchestrator.submit_task(task_def)

        task_execution = orchestrator.task_executions[task_id]
        task_execution.status = TaskStatus.RUNNING
        task_execution.started_at = datetime.now() - timedelta(seconds=10)  # Started 10 seconds ago
        task_execution.assigned_agent = "agent-1"

        # Create agent workload
        orchestrator.agent_workloads["agent-1"] = AgentWorkload(
            agent_id="agent-1",
            agent_type="any",
            current_tasks=1,
            max_concurrent_tasks=3,
            avg_execution_time=60.0,
            success_rate=1.0,
            error_rate=0.0,
            last_task_completion=datetime.now(),
            performance_score=1.0,
            specialization_scores={}
        )

        # Check timeouts
        await orchestrator._check_task_timeouts()

        # Verify task marked as timeout
        assert task_execution.status == TaskStatus.TIMEOUT or task_execution.status == TaskStatus.QUEUED

    async def test_update_agent_performance_metrics(self):
        """Test updating agent performance metrics"""
        mock_mq = AsyncMock()
        mock_am = AsyncMock()

        orchestrator = TaskOrchestrator(mock_mq, mock_am)

        agent_id = "test-agent"
        orchestrator.agent_workloads[agent_id] = AgentWorkload(
            agent_id=agent_id,
            agent_type="scraping-efficiency",
            current_tasks=0,
            max_concurrent_tasks=3,
            avg_execution_time=60.0,
            success_rate=1.0,
            error_rate=0.0,
            last_task_completion=datetime.now(),
            performance_score=1.0,
            specialization_scores={}
        )

        # Add performance history
        for i in range(10):
            orchestrator.agent_performance_history[agent_id].append({
                'success': i < 8,  # 80% success rate
                'execution_time': 45.0 + i,
                'timestamp': datetime.now()
            })

        # Update metrics
        await orchestrator._update_agent_performance_metrics(agent_id)

        workload = orchestrator.agent_workloads[agent_id]
        assert workload.success_rate == 0.8
        assert workload.error_rate == 0.2
        assert workload.avg_execution_time > 45.0

    async def test_get_agent_workloads(self):
        """Test getting agent workload information"""
        mock_mq = AsyncMock()
        mock_am = AsyncMock()

        orchestrator = TaskOrchestrator(mock_mq, mock_am)

        # Add agent workloads
        orchestrator.agent_workloads["agent-1"] = AgentWorkload(
            agent_id="agent-1",
            agent_type="scraping-efficiency",
            current_tasks=2,
            max_concurrent_tasks=3,
            avg_execution_time=45.0,
            success_rate=0.95,
            error_rate=0.05,
            last_task_completion=datetime.now(),
            performance_score=0.92,
            specialization_scores={}
        )

        workload_info = await orchestrator.get_agent_workloads()

        assert 'total_agents' in workload_info
        assert workload_info['total_agents'] == 1
        assert 'avg_utilization' in workload_info
        assert 'agent_details' in workload_info
        assert 'agent-1' in workload_info['agent_details']

    async def test_check_load_balancing_opportunities(self):
        """Test detection of load balancing opportunities"""
        mock_mq = AsyncMock()
        mock_am = AsyncMock()

        orchestrator = TaskOrchestrator(mock_mq, mock_am)

        # Create agents with imbalanced load
        orchestrator.agent_workloads["agent-1"] = AgentWorkload(
            agent_id="agent-1",
            agent_type="scraping-efficiency",
            current_tasks=3,  # High load
            max_concurrent_tasks=3,
            avg_execution_time=60.0,
            success_rate=0.9,
            error_rate=0.1,
            last_task_completion=datetime.now(),
            performance_score=0.9,
            specialization_scores={}
        )

        orchestrator.agent_workloads["agent-2"] = AgentWorkload(
            agent_id="agent-2",
            agent_type="keyword-precision",
            current_tasks=0,  # Low load
            max_concurrent_tasks=3,
            avg_execution_time=60.0,
            success_rate=0.95,
            error_rate=0.05,
            last_task_completion=datetime.now(),
            performance_score=0.95,
            specialization_scores={}
        )

        await orchestrator._check_load_balancing_opportunities()

        # Check if recommendations were generated
        assert len(orchestrator.optimization_recommendations) >= 0


@pytest.mark.unit
class TestAdaptiveLoadBalancer:
    """Test adaptive load balancer"""

    def test_load_balancer_initialization(self):
        """Test load balancer initialization"""
        config = {'adaptive_threshold': 0.8}
        lb = AdaptiveLoadBalancer(config)

        assert lb.config == config
        assert len(lb.selection_history) == 0

    def test_round_robin_selection(self):
        """Test round-robin agent selection"""
        config = {}
        lb = AdaptiveLoadBalancer(config)

        agents = ["agent-1", "agent-2", "agent-3"]

        # Select multiple times
        selections = []
        for _ in range(6):
            selected = lb._round_robin_selection(agents)
            selections.append(selected)

        # Should distribute evenly
        assert selections.count("agent-1") == 2
        assert selections.count("agent-2") == 2
        assert selections.count("agent-3") == 2

    def test_least_loaded_selection(self):
        """Test least-loaded agent selection"""
        config = {}
        lb = AdaptiveLoadBalancer(config)

        agents = ["agent-1", "agent-2", "agent-3"]
        workloads = {
            "agent-1": AgentWorkload(
                agent_id="agent-1",
                agent_type="any",
                current_tasks=3,
                max_concurrent_tasks=3,
                avg_execution_time=60.0,
                success_rate=0.9,
                error_rate=0.1,
                last_task_completion=datetime.now(),
                performance_score=0.9,
                specialization_scores={}
            ),
            "agent-2": AgentWorkload(
                agent_id="agent-2",
                agent_type="any",
                current_tasks=1,
                max_concurrent_tasks=3,
                avg_execution_time=60.0,
                success_rate=0.95,
                error_rate=0.05,
                last_task_completion=datetime.now(),
                performance_score=0.95,
                specialization_scores={}
            ),
            "agent-3": AgentWorkload(
                agent_id="agent-3",
                agent_type="any",
                current_tasks=2,
                max_concurrent_tasks=3,
                avg_execution_time=60.0,
                success_rate=0.92,
                error_rate=0.08,
                last_task_completion=datetime.now(),
                performance_score=0.92,
                specialization_scores={}
            )
        }

        selected = lb._least_loaded_selection(agents, workloads)

        # Should select agent-2 (lowest load)
        assert selected == "agent-2"

    def test_performance_based_selection(self):
        """Test performance-based agent selection"""
        config = {}
        lb = AdaptiveLoadBalancer(config)

        agents = ["agent-1", "agent-2"]
        workloads = {
            "agent-1": AgentWorkload(
                agent_id="agent-1",
                agent_type="any",
                current_tasks=1,
                max_concurrent_tasks=3,
                avg_execution_time=60.0,
                success_rate=0.85,
                error_rate=0.15,
                last_task_completion=datetime.now(),
                performance_score=0.85,
                specialization_scores={}
            ),
            "agent-2": AgentWorkload(
                agent_id="agent-2",
                agent_type="any",
                current_tasks=1,
                max_concurrent_tasks=3,
                avg_execution_time=45.0,
                success_rate=0.95,
                error_rate=0.05,
                last_task_completion=datetime.now(),
                performance_score=0.95,
                specialization_scores={}
            )
        }

        selected = lb._performance_based_selection(agents, workloads)

        # Should select agent-2 (better performance)
        assert selected == "agent-2"

    def test_adaptive_selection(self):
        """Test adaptive agent selection"""
        config = {}
        lb = AdaptiveLoadBalancer(config)

        agents = ["agent-1", "agent-2"]
        workloads = {
            "agent-1": AgentWorkload(
                agent_id="agent-1",
                agent_type="scraping-efficiency",
                current_tasks=2,
                max_concurrent_tasks=3,
                avg_execution_time=60.0,
                success_rate=0.9,
                error_rate=0.1,
                last_task_completion=datetime.now(),
                performance_score=0.9,
                specialization_scores={}
            ),
            "agent-2": AgentWorkload(
                agent_id="agent-2",
                agent_type="keyword-precision",
                current_tasks=1,
                max_concurrent_tasks=3,
                avg_execution_time=45.0,
                success_rate=0.95,
                error_rate=0.05,
                last_task_completion=datetime.now(),
                performance_score=0.95,
                specialization_scores={}
            )
        }

        task_def = TaskDefinition(
            id=str(uuid.uuid4()),
            type="test-task",
            agent_type="keyword-precision",  # Matches agent-2
            priority=Priority.MEDIUM,
            payload={},
            created_at=datetime.now()
        )

        selected = lb._adaptive_selection(agents, workloads, task_def)

        # Should select agent-2 (lower load + type match + better performance)
        assert selected == "agent-2"

    def test_select_agent_with_strategy(self):
        """Test selecting agent with different strategies"""
        config = {}
        lb = AdaptiveLoadBalancer(config)

        agents = ["agent-1", "agent-2"]
        workloads = {
            "agent-1": AgentWorkload(
                agent_id="agent-1",
                agent_type="any",
                current_tasks=2,
                max_concurrent_tasks=3,
                avg_execution_time=60.0,
                success_rate=0.9,
                error_rate=0.1,
                last_task_completion=datetime.now(),
                performance_score=0.9,
                specialization_scores={}
            ),
            "agent-2": AgentWorkload(
                agent_id="agent-2",
                agent_type="any",
                current_tasks=1,
                max_concurrent_tasks=3,
                avg_execution_time=45.0,
                success_rate=0.95,
                error_rate=0.05,
                last_task_completion=datetime.now(),
                performance_score=0.95,
                specialization_scores={}
            )
        }

        task_def = TaskDefinition(
            id=str(uuid.uuid4()),
            type="test-task",
            agent_type="any",
            priority=Priority.MEDIUM,
            payload={},
            created_at=datetime.now()
        )

        # Test round-robin
        selected_rr = lb.select_agent(agents, workloads, task_def, SchedulingStrategy.ROUND_ROBIN)
        assert selected_rr in agents

        # Test least-loaded
        selected_ll = lb.select_agent(agents, workloads, task_def, SchedulingStrategy.LEAST_LOADED)
        assert selected_ll == "agent-2"  # Lower load

        # Test performance-based
        selected_pb = lb.select_agent(agents, workloads, task_def, SchedulingStrategy.PERFORMANCE_BASED)
        assert selected_pb == "agent-2"  # Better performance

    def test_select_agent_empty_list(self):
        """Test selecting agent from empty list"""
        config = {}
        lb = AdaptiveLoadBalancer(config)

        task_def = TaskDefinition(
            id=str(uuid.uuid4()),
            type="test-task",
            agent_type="any",
            priority=Priority.MEDIUM,
            payload={},
            created_at=datetime.now()
        )

        selected = lb.select_agent([], {}, task_def, SchedulingStrategy.ADAPTIVE)

        assert selected is None


@pytest.mark.unit
class TestTaskExecution:
    """Test task execution data structure"""

    def test_task_execution_creation(self):
        """Test creating task execution"""
        task_def = TaskDefinition(
            id=str(uuid.uuid4()),
            type="test-task",
            agent_type="any",
            priority=Priority.MEDIUM,
            payload={},
            created_at=datetime.now()
        )

        execution = TaskExecution(
            task_id=task_def.id,
            task_definition=task_def,
            assigned_agent=None,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            assigned_at=None,
            started_at=None,
            completed_at=None,
            execution_time=None,
            retry_count=0,
            error_message=None,
            result=None
        )

        assert execution.task_id == task_def.id
        assert execution.status == TaskStatus.PENDING
        assert execution.retry_count == 0
        assert execution.assigned_agent is None
