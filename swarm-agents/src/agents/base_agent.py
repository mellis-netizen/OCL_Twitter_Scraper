#!/usr/bin/env python3
"""
Base Agent Implementation for TGE Detection Swarm
Provides common functionality for all specialized agents
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Set
import uuid
import sys
import os

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.message_queue import MessageQueue, SwarmMessage, MessageType, Priority
from swarm_memory_coordinator import SwarmMemoryCoordinator


class AgentStatus(Enum):
    """Agent operational status"""
    INITIALIZING = "initializing"
    READY = "ready"
    WORKING = "working"
    IDLE = "idle"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


class AgentCapability(Enum):
    """Agent capabilities enumeration"""
    WEB_SCRAPING = "web-scraping"
    API_OPTIMIZATION = "api-optimization"
    PERFORMANCE_TUNING = "performance-tuning"
    NLP_ANALYSIS = "nlp"
    ERROR_HANDLING = "error-handling"
    CIRCUIT_BREAKERS = "circuit-breakers"
    PROFILING = "profiling"
    VALIDATION = "validation"


@dataclass
class AgentMetrics:
    """Agent performance metrics"""
    tasks_completed: int = 0
    tasks_failed: int = 0
    average_execution_time: float = 0.0
    total_execution_time: float = 0.0
    optimizations_found: int = 0
    errors_encountered: int = 0
    last_activity: Optional[datetime] = None
    uptime_seconds: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0


@dataclass
class TaskResult:
    """Result of agent task execution"""
    task_id: str
    success: bool
    execution_time: float
    findings: List[Dict[str, Any]] = field(default_factory=list)
    optimizations: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TGEAgent(ABC):
    """Base class for all TGE detection agents"""

    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: List[AgentCapability],
        specializations: List[str],
        config: Dict[str, Any] = None
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.capabilities = capabilities
        self.specializations = specializations
        self.config = config or {}

        # Status and metrics
        self.status = AgentStatus.INITIALIZING
        self.metrics = AgentMetrics()
        self.start_time = time.time()

        # Communication
        self.message_queue: Optional[MessageQueue] = None
        self.memory_coordinator: Optional[SwarmMemoryCoordinator] = None

        # Task management
        self.current_task: Optional[str] = None
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.running = False

        # Setup logging
        self.setup_logging()

        self.logger.info(f"Initialized {self.agent_type} agent: {self.agent_id}")

    def setup_logging(self):
        """Setup agent logging"""
        self.logger = logging.getLogger(f"TGEAgent.{self.agent_type}.{self.agent_id}")
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    async def initialize(
        self,
        message_queue: MessageQueue,
        memory_coordinator: SwarmMemoryCoordinator
    ):
        """Initialize agent with communication systems"""
        self.message_queue = message_queue
        self.memory_coordinator = memory_coordinator

        # Subscribe to relevant message topics
        await self.message_queue.subscribe(
            subscriber_id=self.agent_id,
            callback=self._handle_message
        )

        # Register with coordination service
        await self._register_with_coordination()

        # Start background tasks
        self.running = True
        asyncio.create_task(self._task_processor_loop())
        asyncio.create_task(self._health_check_loop())
        asyncio.create_task(self._metrics_update_loop())

        self.status = AgentStatus.READY
        self.logger.info(f"Agent {self.agent_id} initialized and ready")

    async def _register_with_coordination(self):
        """Register agent with coordination service"""
        try:
            memory_data = {
                'agent_id': self.agent_id,
                'agent_type': self.agent_type,
                'capabilities': [cap.value for cap in self.capabilities],
                'specializations': self.specializations,
                'status': self.status.value,
                'registered_at': datetime.now().isoformat()
            }

            self.memory_coordinator.store_memory(
                self.agent_id,
                "agent_registration",
                memory_data
            )

            self.logger.info(f"Registered with coordination service")
        except Exception as e:
            self.logger.error(f"Failed to register with coordination: {e}")

    async def _task_processor_loop(self):
        """Main task processing loop"""
        while self.running:
            try:
                # Get task from queue with timeout
                try:
                    task = await asyncio.wait_for(
                        self.task_queue.get(),
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    self.status = AgentStatus.IDLE
                    continue

                # Process task
                self.status = AgentStatus.WORKING
                self.current_task = task.get('task_id')

                result = await self._execute_task(task)

                # Report results
                await self._report_task_completion(result)

                # Update metrics
                self._update_metrics(result)

                self.current_task = None
                self.status = AgentStatus.READY

            except Exception as e:
                self.logger.error(f"Error in task processor loop: {e}")
                self.status = AgentStatus.ERROR
                await asyncio.sleep(5)

    async def _execute_task(self, task: Dict[str, Any]) -> TaskResult:
        """Execute a task"""
        task_id = task.get('task_id', str(uuid.uuid4()))
        start_time = time.time()

        try:
            self.logger.info(f"Executing task: {task_id}")

            # Call agent-specific task implementation
            findings, optimizations = await self.execute_specialized_task(task)

            execution_time = time.time() - start_time

            return TaskResult(
                task_id=task_id,
                success=True,
                execution_time=execution_time,
                findings=findings,
                optimizations=optimizations,
                errors=[],
                metadata={'agent_type': self.agent_type}
            )

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Task {task_id} failed: {e}")

            return TaskResult(
                task_id=task_id,
                success=False,
                execution_time=execution_time,
                findings=[],
                optimizations=[],
                errors=[str(e)],
                metadata={'agent_type': self.agent_type}
            )

    @abstractmethod
    async def execute_specialized_task(
        self,
        task: Dict[str, Any]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Execute agent-specific task logic
        Must be implemented by specialized agents

        Returns:
            (findings, optimizations) tuple
        """
        pass

    async def _report_task_completion(self, result: TaskResult):
        """Report task completion via message queue and memory"""
        try:
            # Store in memory coordinator
            completion_data = {
                'task_id': result.task_id,
                'agent_id': self.agent_id,
                'agent_type': self.agent_type,
                'success': result.success,
                'execution_time': result.execution_time,
                'findings_count': len(result.findings),
                'optimizations_count': len(result.optimizations),
                'errors': result.errors,
                'completed_at': datetime.now().isoformat()
            }

            self.memory_coordinator.store_memory(
                self.agent_id,
                "task_completion",
                completion_data
            )

            # Publish via message queue
            message = SwarmMessage(
                id=str(uuid.uuid4()),
                type=MessageType.TASK_COMPLETE,
                sender=self.agent_id,
                recipient=None,  # Broadcast
                timestamp=datetime.now(),
                payload={
                    'task_id': result.task_id,
                    'success': result.success,
                    'execution_time': result.execution_time,
                    'findings': result.findings,
                    'optimizations': result.optimizations
                },
                priority=Priority.MEDIUM
            )

            await self.message_queue.publish_message(message)

            self.logger.info(f"Reported completion of task {result.task_id}")

        except Exception as e:
            self.logger.error(f"Failed to report task completion: {e}")

    def _update_metrics(self, result: TaskResult):
        """Update agent metrics based on task result"""
        if result.success:
            self.metrics.tasks_completed += 1
        else:
            self.metrics.tasks_failed += 1

        self.metrics.total_execution_time += result.execution_time
        self.metrics.average_execution_time = (
            self.metrics.total_execution_time /
            (self.metrics.tasks_completed + self.metrics.tasks_failed)
        )

        self.metrics.optimizations_found += len(result.optimizations)
        self.metrics.errors_encountered += len(result.errors)
        self.metrics.last_activity = datetime.now()
        self.metrics.uptime_seconds = time.time() - self.start_time

    async def _health_check_loop(self):
        """Periodic health check reporting"""
        while self.running:
            try:
                await asyncio.sleep(30)

                health_data = {
                    'agent_id': self.agent_id,
                    'status': self.status.value,
                    'current_task': self.current_task,
                    'metrics': {
                        'tasks_completed': self.metrics.tasks_completed,
                        'tasks_failed': self.metrics.tasks_failed,
                        'avg_execution_time': self.metrics.average_execution_time,
                        'uptime': self.metrics.uptime_seconds
                    },
                    'timestamp': datetime.now().isoformat()
                }

                # Send health check message
                message = SwarmMessage(
                    id=str(uuid.uuid4()),
                    type=MessageType.AGENT_STATUS,
                    sender=self.agent_id,
                    recipient=None,
                    timestamp=datetime.now(),
                    payload=health_data,
                    priority=Priority.LOW
                )

                await self.message_queue.publish_message(message)

            except Exception as e:
                self.logger.error(f"Health check loop error: {e}")

    async def _metrics_update_loop(self):
        """Periodic metrics update"""
        while self.running:
            try:
                await asyncio.sleep(60)

                # Update resource usage metrics
                import psutil
                process = psutil.Process()
                self.metrics.memory_usage_mb = process.memory_info().rss / 1024 / 1024
                self.metrics.cpu_usage_percent = process.cpu_percent(interval=1)

            except Exception as e:
                self.logger.error(f"Metrics update error: {e}")

    async def _handle_message(self, message: SwarmMessage):
        """Handle incoming messages"""
        try:
            if message.type == MessageType.TASK_ASSIGNMENT:
                # Add task to queue
                await self.task_queue.put(message.payload)
                self.logger.info(f"Received task assignment: {message.payload.get('task_id')}")

            elif message.type == MessageType.COORDINATION_EVENT:
                # Handle coordination events
                await self._handle_coordination_event(message.payload)

        except Exception as e:
            self.logger.error(f"Error handling message: {e}")

    async def _handle_coordination_event(self, event_data: Dict[str, Any]):
        """Handle coordination events"""
        event_type = event_data.get('type')
        self.logger.debug(f"Received coordination event: {event_type}")

        # Subclasses can override to handle specific events

    async def shutdown(self):
        """Graceful agent shutdown"""
        self.running = False
        self.status = AgentStatus.SHUTTING_DOWN

        # Wait for current task to complete
        if self.current_task:
            self.logger.info(f"Waiting for current task {self.current_task} to complete...")
            await asyncio.sleep(5)

        # Deregister from coordination
        try:
            memory_data = {
                'agent_id': self.agent_id,
                'status': 'shutdown',
                'final_metrics': {
                    'tasks_completed': self.metrics.tasks_completed,
                    'tasks_failed': self.metrics.tasks_failed,
                    'optimizations_found': self.metrics.optimizations_found,
                    'uptime': self.metrics.uptime_seconds
                },
                'shutdown_at': datetime.now().isoformat()
            }

            self.memory_coordinator.store_memory(
                self.agent_id,
                "agent_shutdown",
                memory_data
            )
        except Exception as e:
            self.logger.error(f"Failed to record shutdown: {e}")

        self.logger.info(f"Agent {self.agent_id} shutdown complete")

    def get_metrics(self) -> Dict[str, Any]:
        """Get agent metrics"""
        return {
            'agent_id': self.agent_id,
            'agent_type': self.agent_type,
            'status': self.status.value,
            'metrics': {
                'tasks_completed': self.metrics.tasks_completed,
                'tasks_failed': self.metrics.tasks_failed,
                'average_execution_time': self.metrics.average_execution_time,
                'optimizations_found': self.metrics.optimizations_found,
                'errors_encountered': self.metrics.errors_encountered,
                'uptime_seconds': self.metrics.uptime_seconds,
                'memory_usage_mb': self.metrics.memory_usage_mb,
                'cpu_usage_percent': self.metrics.cpu_usage_percent
            },
            'current_task': self.current_task,
            'capabilities': [cap.value for cap in self.capabilities],
            'specializations': self.specializations
        }
