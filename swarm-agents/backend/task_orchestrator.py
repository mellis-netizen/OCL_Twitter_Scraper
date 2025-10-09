#!/usr/bin/env python3
"""
Task Distribution and Load Balancing System for TGE Swarm
Intelligent task orchestration with adaptive load balancing and optimization
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import heapq
from collections import defaultdict, deque
import statistics

from message_queue import MessageQueue, SwarmMessage, MessageType, Priority, TaskDefinition
from agent_manager import AgentManager, AgentInstance, AgentStatus


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    QUEUED = "queued"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class SchedulingStrategy(Enum):
    """Task scheduling strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    CAPABILITY_MATCH = "capability_match"
    PRIORITY_WEIGHTED = "priority_weighted"
    PERFORMANCE_BASED = "performance_based"
    ADAPTIVE = "adaptive"


@dataclass
class TaskExecution:
    """Task execution tracking"""
    task_id: str
    task_definition: TaskDefinition
    assigned_agent: Optional[str]
    status: TaskStatus
    created_at: datetime
    assigned_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    execution_time: Optional[float]
    retry_count: int
    error_message: Optional[str]
    result: Optional[Dict[str, Any]]


@dataclass
class AgentWorkload:
    """Agent workload tracking"""
    agent_id: str
    agent_type: str
    current_tasks: int
    max_concurrent_tasks: int
    avg_execution_time: float
    success_rate: float
    error_rate: float
    last_task_completion: datetime
    performance_score: float
    specialization_scores: Dict[str, float]


@dataclass
class TaskQueue:
    """Priority task queue"""
    priority: Priority
    tasks: List[TaskExecution]
    max_size: int = 1000


class TaskOrchestrator:
    """Advanced task distribution and load balancing system"""
    
    def __init__(self, message_queue: MessageQueue, agent_manager: AgentManager,
                 config: Dict[str, Any] = None):
        self.message_queue = message_queue
        self.agent_manager = agent_manager
        self.config = config or self._default_config()
        
        # Task management
        self.task_executions: Dict[str, TaskExecution] = {}
        self.task_queues: Dict[Priority, TaskQueue] = {
            Priority.CRITICAL: TaskQueue(Priority.CRITICAL, []),
            Priority.HIGH: TaskQueue(Priority.HIGH, []),
            Priority.MEDIUM: TaskQueue(Priority.MEDIUM, []),
            Priority.LOW: TaskQueue(Priority.LOW, [])
        }
        
        # Agent workload tracking
        self.agent_workloads: Dict[str, AgentWorkload] = {}
        self.agent_performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Load balancing
        self.scheduling_strategy = SchedulingStrategy(self.config.get('scheduling_strategy', 'adaptive'))
        self.load_balancer = AdaptiveLoadBalancer(self.config)
        
        # Performance tracking
        self.orchestration_metrics = {
            'tasks_scheduled': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'avg_queue_time': 0.0,
            'avg_execution_time': 0.0,
            'throughput_per_minute': 0.0,
            'agent_utilization': 0.0
        }
        
        # Optimization patterns
        self.task_patterns = defaultdict(list)
        self.optimization_recommendations = []
        
        self.running = False
        self.setup_logging()
    
    def setup_logging(self):
        """Setup task orchestrator logging"""
        self.logger = logging.getLogger("TaskOrchestrator")
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for task orchestrator"""
        return {
            'scheduling_strategy': 'adaptive',
            'max_concurrent_tasks_per_agent': 3,
            'task_timeout_seconds': 300,
            'max_retries': 3,
            'queue_size_threshold': 50,
            'performance_window_minutes': 30,
            'adaptive_threshold': 0.8,
            'load_balancing_interval': 30,
            'optimization_analysis_interval': 300,
            'agent_health_check_interval': 60
        }
    
    async def initialize(self):
        """Initialize task orchestrator"""
        # Subscribe to task results
        await self.message_queue.subscribe_to_broadcast(self._handle_task_result_message)
        
        # Start orchestration loops
        self.running = True
        asyncio.create_task(self._task_scheduling_loop())
        asyncio.create_task(self._workload_monitoring_loop())
        asyncio.create_task(self._optimization_analysis_loop())
        asyncio.create_task(self._health_monitoring_loop())
        
        self.logger.info("Task orchestrator initialized")
    
    async def submit_task(self, task_definition: TaskDefinition) -> str:
        """Submit task for execution"""
        try:
            # Create task execution record
            task_execution = TaskExecution(
                task_id=task_definition.id,
                task_definition=task_definition,
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
            
            # Store task execution
            self.task_executions[task_definition.id] = task_execution
            
            # Add to appropriate priority queue
            priority_queue = self.task_queues[task_definition.priority]
            priority_queue.tasks.append(task_execution)
            
            # Update task status
            task_execution.status = TaskStatus.QUEUED
            
            # Update metrics
            self.orchestration_metrics['tasks_scheduled'] += 1
            
            # Analyze task pattern
            await self._analyze_task_pattern(task_definition)
            
            self.logger.info(f"Submitted task {task_definition.id} with priority {task_definition.priority.name}")
            return task_definition.id
            
        except Exception as e:
            self.logger.error(f"Failed to submit task {task_definition.id}: {e}")
            return ""
    
    async def cancel_task(self, task_id: str, reason: str = "cancelled") -> bool:
        """Cancel pending or running task"""
        try:
            if task_id not in self.task_executions:
                return False
            
            task_execution = self.task_executions[task_id]
            
            if task_execution.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return False
            
            # Remove from queue if still queued
            if task_execution.status == TaskStatus.QUEUED:
                for queue in self.task_queues.values():
                    queue.tasks = [t for t in queue.tasks if t.task_id != task_id]
            
            # Notify agent if task is running
            if task_execution.status == TaskStatus.RUNNING and task_execution.assigned_agent:
                cancel_message = SwarmMessage(
                    id=str(uuid.uuid4()),
                    type=MessageType.TASK_ASSIGNMENT,
                    sender="task-orchestrator",
                    recipient=task_execution.assigned_agent,
                    timestamp=datetime.now(),
                    payload={
                        'action': 'cancel',
                        'task_id': task_id,
                        'reason': reason
                    },
                    priority=Priority.HIGH
                )
                
                await self.message_queue.publish_message(cancel_message)
            
            # Update task status
            task_execution.status = TaskStatus.CANCELLED
            task_execution.completed_at = datetime.now()
            task_execution.error_message = reason
            
            self.logger.info(f"Cancelled task {task_id}: {reason}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cancel task {task_id}: {e}")
            return False
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task execution status"""
        if task_id not in self.task_executions:
            return None
        
        task_execution = self.task_executions[task_id]
        
        return {
            'task_id': task_execution.task_id,
            'status': task_execution.status.value,
            'created_at': task_execution.created_at.isoformat(),
            'assigned_at': task_execution.assigned_at.isoformat() if task_execution.assigned_at else None,
            'started_at': task_execution.started_at.isoformat() if task_execution.started_at else None,
            'completed_at': task_execution.completed_at.isoformat() if task_execution.completed_at else None,
            'assigned_agent': task_execution.assigned_agent,
            'execution_time': task_execution.execution_time,
            'retry_count': task_execution.retry_count,
            'error_message': task_execution.error_message,
            'result': task_execution.result
        }
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        queue_status = {}
        total_queued = 0
        
        for priority, queue in self.task_queues.items():
            queued_count = len(queue.tasks)
            total_queued += queued_count
            
            queue_status[priority.name] = {
                'queued_tasks': queued_count,
                'max_size': queue.max_size,
                'oldest_task': min(t.created_at for t in queue.tasks).isoformat() if queue.tasks else None
            }
        
        # Calculate queue statistics
        running_tasks = len([t for t in self.task_executions.values() if t.status == TaskStatus.RUNNING])
        completed_tasks = len([t for t in self.task_executions.values() if t.status == TaskStatus.COMPLETED])
        failed_tasks = len([t for t in self.task_executions.values() if t.status == TaskStatus.FAILED])
        
        return {
            'total_queued': total_queued,
            'running_tasks': running_tasks,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'queue_breakdown': queue_status,
            'metrics': self.orchestration_metrics
        }
    
    async def get_agent_workloads(self) -> Dict[str, Any]:
        """Get current agent workload information"""
        workload_summary = {}
        
        for agent_id, workload in self.agent_workloads.items():
            workload_summary[agent_id] = {
                'agent_type': workload.agent_type,
                'current_tasks': workload.current_tasks,
                'max_concurrent_tasks': workload.max_concurrent_tasks,
                'utilization': workload.current_tasks / workload.max_concurrent_tasks,
                'avg_execution_time': workload.avg_execution_time,
                'success_rate': workload.success_rate,
                'error_rate': workload.error_rate,
                'performance_score': workload.performance_score,
                'last_task_completion': workload.last_task_completion.isoformat() if workload.last_task_completion else None
            }
        
        # Calculate overall metrics
        total_agents = len(self.agent_workloads)
        if total_agents > 0:
            avg_utilization = sum(w.current_tasks / w.max_concurrent_tasks for w in self.agent_workloads.values()) / total_agents
            avg_performance = sum(w.performance_score for w in self.agent_workloads.values()) / total_agents
        else:
            avg_utilization = 0.0
            avg_performance = 0.0
        
        return {
            'total_agents': total_agents,
            'avg_utilization': avg_utilization,
            'avg_performance_score': avg_performance,
            'agent_details': workload_summary
        }
    
    async def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get current optimization recommendations"""
        return self.optimization_recommendations
    
    async def _task_scheduling_loop(self):
        """Main task scheduling loop"""
        while self.running:
            try:
                # Process tasks in priority order
                for priority in [Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM, Priority.LOW]:
                    queue = self.task_queues[priority]
                    
                    # Process pending tasks in this queue
                    tasks_to_remove = []
                    for task_execution in queue.tasks:
                        if task_execution.status == TaskStatus.QUEUED:
                            # Try to assign task to agent
                            assigned_agent = await self._assign_task_to_agent(task_execution)
                            
                            if assigned_agent:
                                task_execution.assigned_agent = assigned_agent
                                task_execution.status = TaskStatus.ASSIGNED
                                task_execution.assigned_at = datetime.now()
                                
                                # Send task to agent
                                await self._send_task_to_agent(task_execution, assigned_agent)
                                
                                tasks_to_remove.append(task_execution)
                    
                    # Remove assigned tasks from queue
                    for task_execution in tasks_to_remove:
                        queue.tasks.remove(task_execution)
                
                # Check for task timeouts
                await self._check_task_timeouts()
                
                # Update load balancing metrics
                await self._update_load_balancing_metrics()
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                self.logger.error(f"Error in task scheduling loop: {e}")
                await asyncio.sleep(5)
    
    async def _assign_task_to_agent(self, task_execution: TaskExecution) -> Optional[str]:
        """Assign task to best available agent"""
        try:
            # Get available agents
            agent_status = await self.agent_manager.get_agent_status()
            available_agents = []
            
            for agent_id, agent_info in agent_status.get('agents', {}).items():
                if (agent_info['status'] == 'healthy' and 
                    agent_id in self.agent_workloads):
                    
                    workload = self.agent_workloads[agent_id]
                    
                    # Check if agent can handle more tasks
                    if workload.current_tasks < workload.max_concurrent_tasks:
                        # Check if agent can handle this task type
                        if (task_execution.task_definition.agent_type == "any" or
                            workload.agent_type == task_execution.task_definition.agent_type):
                            available_agents.append(agent_id)
            
            if not available_agents:
                return None
            
            # Use load balancer to select best agent
            selected_agent = self.load_balancer.select_agent(
                available_agents,
                self.agent_workloads,
                task_execution.task_definition,
                self.scheduling_strategy
            )
            
            return selected_agent
            
        except Exception as e:
            self.logger.error(f"Error assigning task to agent: {e}")
            return None
    
    async def _send_task_to_agent(self, task_execution: TaskExecution, agent_id: str):
        """Send task to assigned agent"""
        try:
            # Create task assignment message
            message = SwarmMessage(
                id=str(uuid.uuid4()),
                type=MessageType.TASK_ASSIGNMENT,
                sender="task-orchestrator",
                recipient=agent_id,
                timestamp=datetime.now(),
                payload={
                    'action': 'execute',
                    'task': asdict(task_execution.task_definition)
                },
                priority=task_execution.task_definition.priority
            )
            
            # Send message
            await self.message_queue.publish_message(message)
            
            # Update agent workload
            if agent_id in self.agent_workloads:
                self.agent_workloads[agent_id].current_tasks += 1
            
            self.logger.info(f"Sent task {task_execution.task_id} to agent {agent_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to send task to agent {agent_id}: {e}")
            # Reset task status to queued for retry
            task_execution.status = TaskStatus.QUEUED
            task_execution.assigned_agent = None
    
    async def _handle_task_result_message(self, message: SwarmMessage):
        """Handle task result messages from agents"""
        try:
            if message.type == MessageType.TASK_RESULT:
                payload = message.payload
                task_id = payload.get('task_id')
                success = payload.get('success', False)
                result = payload.get('result', {})
                error_message = payload.get('error_message')
                
                if task_id and task_id in self.task_executions:
                    await self._process_task_result(
                        task_id, message.sender, success, result, error_message
                    )
            
            elif message.type == MessageType.STATUS_UPDATE:
                # Handle agent status updates
                agent_id = message.sender
                status = message.payload
                await self._update_agent_status(agent_id, status)
                
        except Exception as e:
            self.logger.error(f"Error handling task result message: {e}")
    
    async def _process_task_result(self, task_id: str, agent_id: str, success: bool,
                                 result: Dict[str, Any], error_message: Optional[str]):
        """Process task execution result"""
        try:
            task_execution = self.task_executions[task_id]
            
            # Update task execution
            task_execution.completed_at = datetime.now()
            task_execution.execution_time = (
                task_execution.completed_at - task_execution.started_at
            ).total_seconds() if task_execution.started_at else 0.0
            
            if success:
                task_execution.status = TaskStatus.COMPLETED
                task_execution.result = result
                self.orchestration_metrics['tasks_completed'] += 1
            else:
                task_execution.status = TaskStatus.FAILED
                task_execution.error_message = error_message
                self.orchestration_metrics['tasks_failed'] += 1
                
                # Check if retry is needed
                if (task_execution.retry_count < task_execution.task_definition.retries and
                    task_execution.retry_count < self.config['max_retries']):
                    await self._retry_task(task_execution)
            
            # Update agent workload
            if agent_id in self.agent_workloads:
                workload = self.agent_workloads[agent_id]
                workload.current_tasks = max(0, workload.current_tasks - 1)
                workload.last_task_completion = datetime.now()
                
                # Update performance metrics
                performance_data = {
                    'success': success,
                    'execution_time': task_execution.execution_time,
                    'timestamp': datetime.now()
                }
                
                self.agent_performance_history[agent_id].append(performance_data)
                await self._update_agent_performance_metrics(agent_id)
            
            # Update orchestration metrics
            await self._update_orchestration_metrics()
            
            self.logger.info(f"Processed task result {task_id} from {agent_id}: {'success' if success else 'failed'}")
            
        except Exception as e:
            self.logger.error(f"Error processing task result for {task_id}: {e}")
    
    async def _retry_task(self, task_execution: TaskExecution):
        """Retry failed task"""
        try:
            task_execution.retry_count += 1
            task_execution.status = TaskStatus.QUEUED
            task_execution.assigned_agent = None
            task_execution.assigned_at = None
            task_execution.started_at = None
            task_execution.completed_at = None
            
            # Add back to appropriate queue
            priority_queue = self.task_queues[task_execution.task_definition.priority]
            priority_queue.tasks.append(task_execution)
            
            self.logger.info(f"Retrying task {task_execution.task_id} (attempt {task_execution.retry_count})")
            
        except Exception as e:
            self.logger.error(f"Error retrying task {task_execution.task_id}: {e}")
    
    async def _check_task_timeouts(self):
        """Check for timed out tasks"""
        current_time = datetime.now()
        timeout_threshold = timedelta(seconds=self.config['task_timeout_seconds'])
        
        for task_execution in self.task_executions.values():
            if (task_execution.status == TaskStatus.RUNNING and
                task_execution.started_at and
                current_time - task_execution.started_at > timeout_threshold):
                
                # Mark task as timed out
                task_execution.status = TaskStatus.TIMEOUT
                task_execution.completed_at = current_time
                task_execution.error_message = "Task execution timeout"
                
                # Update agent workload
                if task_execution.assigned_agent and task_execution.assigned_agent in self.agent_workloads:
                    self.agent_workloads[task_execution.assigned_agent].current_tasks -= 1
                
                # Retry if possible
                if task_execution.retry_count < task_execution.task_definition.retries:
                    await self._retry_task(task_execution)
                
                self.logger.warning(f"Task {task_execution.task_id} timed out")
    
    async def _workload_monitoring_loop(self):
        """Monitor agent workloads and update metrics"""
        while self.running:
            try:
                # Update agent workloads based on current agent status
                await self._sync_agent_workloads()
                
                # Check for load balancing opportunities
                await self._check_load_balancing_opportunities()
                
                await asyncio.sleep(self.config['load_balancing_interval'])
                
            except Exception as e:
                self.logger.error(f"Error in workload monitoring loop: {e}")
                await asyncio.sleep(30)
    
    async def _sync_agent_workloads(self):
        """Synchronize agent workloads with current agent status"""
        try:
            agent_status = await self.agent_manager.get_agent_status()
            current_agents = set(agent_status.get('agents', {}).keys())
            tracked_agents = set(self.agent_workloads.keys())
            
            # Add new agents
            for agent_id in current_agents - tracked_agents:
                agent_info = agent_status['agents'][agent_id]
                
                workload = AgentWorkload(
                    agent_id=agent_id,
                    agent_type=agent_info['type'],
                    current_tasks=0,
                    max_concurrent_tasks=self.config['max_concurrent_tasks_per_agent'],
                    avg_execution_time=60.0,  # Default 1 minute
                    success_rate=1.0,
                    error_rate=0.0,
                    last_task_completion=datetime.now(),
                    performance_score=1.0,
                    specialization_scores={}
                )
                
                self.agent_workloads[agent_id] = workload
                self.logger.info(f"Added workload tracking for agent {agent_id}")
            
            # Remove defunct agents
            for agent_id in tracked_agents - current_agents:
                del self.agent_workloads[agent_id]
                if agent_id in self.agent_performance_history:
                    del self.agent_performance_history[agent_id]
                self.logger.info(f"Removed workload tracking for agent {agent_id}")
            
        except Exception as e:
            self.logger.error(f"Error syncing agent workloads: {e}")
    
    async def _update_agent_performance_metrics(self, agent_id: str):
        """Update performance metrics for agent"""
        try:
            if agent_id not in self.agent_workloads:
                return
            
            workload = self.agent_workloads[agent_id]
            history = self.agent_performance_history[agent_id]
            
            if not history:
                return
            
            # Calculate metrics from recent performance data
            recent_data = list(history)[-50:]  # Last 50 tasks
            
            if recent_data:
                # Success rate
                successes = sum(1 for d in recent_data if d['success'])
                workload.success_rate = successes / len(recent_data)
                workload.error_rate = 1.0 - workload.success_rate
                
                # Average execution time
                exec_times = [d['execution_time'] for d in recent_data if d['execution_time']]
                if exec_times:
                    workload.avg_execution_time = statistics.mean(exec_times)
                
                # Performance score (composite metric)
                time_score = max(0, 1.0 - (workload.avg_execution_time / 300.0))  # Normalized to 5 minutes
                workload.performance_score = (workload.success_rate * 0.6 + time_score * 0.4)
            
        except Exception as e:
            self.logger.error(f"Error updating performance metrics for {agent_id}: {e}")
    
    async def _update_agent_status(self, agent_id: str, status: Dict[str, Any]):
        """Update agent status from status message"""
        try:
            if agent_id in self.agent_workloads:
                workload = self.agent_workloads[agent_id]
                
                # Update metrics from status
                if 'task_count' in status:
                    workload.current_tasks = status['task_count']
                
                if 'performance_metrics' in status:
                    metrics = status['performance_metrics']
                    if 'avg_execution_time' in metrics:
                        workload.avg_execution_time = metrics['avg_execution_time']
                    if 'success_rate' in metrics:
                        workload.success_rate = metrics['success_rate']
                    if 'error_rate' in metrics:
                        workload.error_rate = metrics['error_rate']
            
        except Exception as e:
            self.logger.error(f"Error updating agent status for {agent_id}: {e}")
    
    async def _check_load_balancing_opportunities(self):
        """Check for load balancing opportunities"""
        try:
            if not self.agent_workloads:
                return
            
            # Calculate utilization statistics
            utilizations = []
            for workload in self.agent_workloads.values():
                utilization = workload.current_tasks / workload.max_concurrent_tasks
                utilizations.append(utilization)
            
            if utilizations:
                avg_utilization = statistics.mean(utilizations)
                max_utilization = max(utilizations)
                min_utilization = min(utilizations)
                
                # Update global utilization metric
                self.orchestration_metrics['agent_utilization'] = avg_utilization
                
                # Check for imbalance
                utilization_variance = statistics.variance(utilizations) if len(utilizations) > 1 else 0
                
                if utilization_variance > 0.1:  # Significant imbalance
                    self.logger.info(f"Load imbalance detected: variance={utilization_variance:.3f}")
                    
                    # Suggest optimization
                    optimization = {
                        'type': 'load_balancing',
                        'severity': 'medium' if utilization_variance > 0.2 else 'low',
                        'description': f"Load imbalance detected across agents (variance: {utilization_variance:.3f})",
                        'recommendations': [
                            f"Consider redistributing tasks from high-utilization agents",
                            f"Evaluate agent scaling for consistently overloaded agents"
                        ],
                        'metrics': {
                            'avg_utilization': avg_utilization,
                            'max_utilization': max_utilization,
                            'min_utilization': min_utilization,
                            'variance': utilization_variance
                        },
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    self.optimization_recommendations.append(optimization)
                    
                    # Keep only recent recommendations
                    cutoff_time = datetime.now() - timedelta(hours=1)
                    self.optimization_recommendations = [
                        opt for opt in self.optimization_recommendations
                        if datetime.fromisoformat(opt['timestamp']) > cutoff_time
                    ]
            
        except Exception as e:
            self.logger.error(f"Error checking load balancing opportunities: {e}")
    
    async def _optimization_analysis_loop(self):
        """Analyze task patterns and generate optimization recommendations"""
        while self.running:
            try:
                await asyncio.sleep(self.config['optimization_analysis_interval'])
                
                # Analyze task patterns
                await self._analyze_task_execution_patterns()
                
                # Generate optimization recommendations
                await self._generate_optimization_recommendations()
                
            except Exception as e:
                self.logger.error(f"Error in optimization analysis loop: {e}")
                await asyncio.sleep(60)
    
    async def _analyze_task_pattern(self, task_definition: TaskDefinition):
        """Analyze individual task pattern"""
        pattern_key = f"{task_definition.type}:{task_definition.agent_type}"
        self.task_patterns[pattern_key].append({
            'task_id': task_definition.id,
            'priority': task_definition.priority.value,
            'timeout': task_definition.timeout,
            'timestamp': datetime.now()
        })
        
        # Keep only recent patterns
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.task_patterns[pattern_key] = [
            p for p in self.task_patterns[pattern_key]
            if p['timestamp'] > cutoff_time
        ]
    
    async def _analyze_task_execution_patterns(self):
        """Analyze task execution patterns for optimization opportunities"""
        try:
            # Analyze completed tasks from last hour
            recent_tasks = [
                t for t in self.task_executions.values()
                if (t.completed_at and 
                    datetime.now() - t.completed_at < timedelta(hours=1))
            ]
            
            if len(recent_tasks) < 10:  # Need sufficient data
                return
            
            # Analyze execution times by task type
            task_type_times = defaultdict(list)
            for task in recent_tasks:
                if task.execution_time:
                    key = f"{task.task_definition.type}:{task.task_definition.agent_type}"
                    task_type_times[key].append(task.execution_time)
            
            # Find slow task types
            for task_type, times in task_type_times.items():
                if len(times) >= 5:  # Minimum sample size
                    avg_time = statistics.mean(times)
                    if avg_time > 180:  # More than 3 minutes average
                        optimization = {
                            'type': 'task_performance',
                            'severity': 'high' if avg_time > 300 else 'medium',
                            'description': f"Task type {task_type} has high average execution time",
                            'recommendations': [
                                f"Optimize {task_type} implementation",
                                f"Consider task decomposition for {task_type}",
                                f"Review resource allocation for {task_type} agents"
                            ],
                            'metrics': {
                                'task_type': task_type,
                                'avg_execution_time': avg_time,
                                'sample_size': len(times)
                            },
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        self.optimization_recommendations.append(optimization)
            
        except Exception as e:
            self.logger.error(f"Error analyzing task execution patterns: {e}")
    
    async def _generate_optimization_recommendations(self):
        """Generate optimization recommendations based on current state"""
        try:
            recommendations = []
            
            # Queue size analysis
            total_queued = sum(len(q.tasks) for q in self.task_queues.values())
            if total_queued > self.config['queue_size_threshold']:
                recommendations.append({
                    'type': 'queue_management',
                    'severity': 'high',
                    'description': f"High queue size detected: {total_queued} tasks queued",
                    'recommendations': [
                        "Consider scaling up agents",
                        "Optimize task execution efficiency",
                        "Review task prioritization strategy"
                    ],
                    'metrics': {'total_queued': total_queued},
                    'timestamp': datetime.now().isoformat()
                })
            
            # Agent utilization analysis
            if self.agent_workloads:
                high_utilization_agents = [
                    agent_id for agent_id, workload in self.agent_workloads.items()
                    if workload.current_tasks / workload.max_concurrent_tasks > 0.9
                ]
                
                if len(high_utilization_agents) > len(self.agent_workloads) * 0.7:
                    recommendations.append({
                        'type': 'agent_scaling',
                        'severity': 'medium',
                        'description': f"Most agents are highly utilized ({len(high_utilization_agents)}/{len(self.agent_workloads)})",
                        'recommendations': [
                            "Consider scaling up agent instances",
                            "Review task distribution strategy",
                            "Optimize agent resource allocation"
                        ],
                        'metrics': {
                            'high_utilization_agents': high_utilization_agents,
                            'utilization_percentage': len(high_utilization_agents) / len(self.agent_workloads)
                        },
                        'timestamp': datetime.now().isoformat()
                    })
            
            # Add new recommendations
            self.optimization_recommendations.extend(recommendations)
            
        except Exception as e:
            self.logger.error(f"Error generating optimization recommendations: {e}")
    
    async def _health_monitoring_loop(self):
        """Monitor task orchestrator health"""
        while self.running:
            try:
                await asyncio.sleep(self.config['agent_health_check_interval'])
                
                # Check for stuck tasks
                await self._check_stuck_tasks()
                
                # Update throughput metrics
                await self._update_throughput_metrics()
                
            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _check_stuck_tasks(self):
        """Check for tasks that appear to be stuck"""
        current_time = datetime.now()
        stuck_threshold = timedelta(minutes=10)
        
        stuck_tasks = []
        for task_execution in self.task_executions.values():
            if (task_execution.status == TaskStatus.ASSIGNED and
                task_execution.assigned_at and
                current_time - task_execution.assigned_at > stuck_threshold):
                
                stuck_tasks.append(task_execution)
        
        for task_execution in stuck_tasks:
            self.logger.warning(f"Task {task_execution.task_id} appears stuck, resetting to queued")
            
            # Reset task to queued status
            task_execution.status = TaskStatus.QUEUED
            task_execution.assigned_agent = None
            task_execution.assigned_at = None
            
            # Add back to queue
            priority_queue = self.task_queues[task_execution.task_definition.priority]
            priority_queue.tasks.append(task_execution)
    
    async def _update_load_balancing_metrics(self):
        """Update load balancing metrics"""
        if not self.task_executions:
            return
        
        # Calculate average queue time
        completed_tasks = [
            t for t in self.task_executions.values()
            if t.status == TaskStatus.COMPLETED and t.assigned_at and t.created_at
        ]
        
        if completed_tasks:
            queue_times = [
                (t.assigned_at - t.created_at).total_seconds()
                for t in completed_tasks
                if t.assigned_at and t.created_at
            ]
            
            if queue_times:
                self.orchestration_metrics['avg_queue_time'] = statistics.mean(queue_times)
        
        # Calculate average execution time
        if completed_tasks:
            exec_times = [t.execution_time for t in completed_tasks if t.execution_time]
            if exec_times:
                self.orchestration_metrics['avg_execution_time'] = statistics.mean(exec_times)
    
    async def _update_throughput_metrics(self):
        """Update throughput metrics"""
        current_time = datetime.now()
        one_minute_ago = current_time - timedelta(minutes=1)
        
        # Count tasks completed in last minute
        recent_completions = len([
            t for t in self.task_executions.values()
            if (t.status == TaskStatus.COMPLETED and 
                t.completed_at and t.completed_at > one_minute_ago)
        ])
        
        self.orchestration_metrics['throughput_per_minute'] = recent_completions
    
    async def _update_orchestration_metrics(self):
        """Update general orchestration metrics"""
        await self._update_load_balancing_metrics()
        await self._update_throughput_metrics()
    
    async def shutdown(self):
        """Shutdown task orchestrator gracefully"""
        self.running = False
        
        # Cancel all pending tasks
        for task_execution in self.task_executions.values():
            if task_execution.status in [TaskStatus.QUEUED, TaskStatus.ASSIGNED]:
                await self.cancel_task(task_execution.task_id, "System shutdown")
        
        self.logger.info("Task orchestrator shutdown complete")


class AdaptiveLoadBalancer:
    """Adaptive load balancer for intelligent agent selection"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.selection_history = defaultdict(int)
        self.performance_weights = {
            'utilization': 0.3,
            'performance_score': 0.3,
            'success_rate': 0.2,
            'avg_execution_time': 0.2
        }
    
    def select_agent(self, available_agents: List[str], agent_workloads: Dict[str, AgentWorkload],
                    task_definition: TaskDefinition, strategy: SchedulingStrategy) -> Optional[str]:
        """Select best agent using specified strategy"""
        if not available_agents:
            return None
        
        if strategy == SchedulingStrategy.ROUND_ROBIN:
            return self._round_robin_selection(available_agents)
        elif strategy == SchedulingStrategy.LEAST_LOADED:
            return self._least_loaded_selection(available_agents, agent_workloads)
        elif strategy == SchedulingStrategy.PERFORMANCE_BASED:
            return self._performance_based_selection(available_agents, agent_workloads)
        elif strategy == SchedulingStrategy.ADAPTIVE:
            return self._adaptive_selection(available_agents, agent_workloads, task_definition)
        else:
            # Default to least loaded
            return self._least_loaded_selection(available_agents, agent_workloads)
    
    def _round_robin_selection(self, available_agents: List[str]) -> str:
        """Simple round-robin selection"""
        # Find agent with least selections
        min_selections = min(self.selection_history[agent] for agent in available_agents)
        candidates = [agent for agent in available_agents 
                     if self.selection_history[agent] == min_selections]
        
        selected = candidates[0]  # Take first if tie
        self.selection_history[selected] += 1
        return selected
    
    def _least_loaded_selection(self, available_agents: List[str], 
                               agent_workloads: Dict[str, AgentWorkload]) -> str:
        """Select agent with lowest current load"""
        def load_score(agent_id):
            if agent_id in agent_workloads:
                workload = agent_workloads[agent_id]
                return workload.current_tasks / workload.max_concurrent_tasks
            return 0.0
        
        selected = min(available_agents, key=load_score)
        self.selection_history[selected] += 1
        return selected
    
    def _performance_based_selection(self, available_agents: List[str],
                                   agent_workloads: Dict[str, AgentWorkload]) -> str:
        """Select agent based on performance metrics"""
        def performance_score(agent_id):
            if agent_id in agent_workloads:
                workload = agent_workloads[agent_id]
                return workload.performance_score
            return 0.0
        
        selected = max(available_agents, key=performance_score)
        self.selection_history[selected] += 1
        return selected
    
    def _adaptive_selection(self, available_agents: List[str], agent_workloads: Dict[str, AgentWorkload],
                           task_definition: TaskDefinition) -> str:
        """Adaptive selection based on multiple factors"""
        agent_scores = {}
        
        for agent_id in available_agents:
            if agent_id not in agent_workloads:
                agent_scores[agent_id] = 0.0
                continue
            
            workload = agent_workloads[agent_id]
            
            # Calculate composite score
            utilization_score = 1.0 - (workload.current_tasks / workload.max_concurrent_tasks)
            performance_score = workload.performance_score
            success_rate_score = workload.success_rate
            time_score = max(0, 1.0 - (workload.avg_execution_time / 300.0))  # Normalized to 5 minutes
            
            # Weighted combination
            composite_score = (
                utilization_score * self.performance_weights['utilization'] +
                performance_score * self.performance_weights['performance_score'] +
                success_rate_score * self.performance_weights['success_rate'] +
                time_score * self.performance_weights['avg_execution_time']
            )
            
            # Bonus for exact agent type match
            if workload.agent_type == task_definition.agent_type:
                composite_score += 0.1
            
            # Priority task bonus for high-performance agents
            if task_definition.priority in [Priority.CRITICAL, Priority.HIGH]:
                composite_score += performance_score * 0.1
            
            agent_scores[agent_id] = composite_score
        
        # Select agent with highest score
        selected = max(agent_scores, key=agent_scores.get)
        self.selection_history[selected] += 1
        return selected


# CLI interface for testing
if __name__ == "__main__":
    import sys
    
    async def test_task_orchestrator():
        # Initialize components
        from message_queue import create_message_queue
        from agent_manager import AgentManager
        
        message_queue = await create_message_queue(["localhost:6379"])
        agent_manager = AgentManager()
        await agent_manager.initialize(message_queue)
        
        # Initialize task orchestrator
        orchestrator = TaskOrchestrator(message_queue, agent_manager)
        await orchestrator.initialize()
        
        # Submit test task
        test_task = TaskDefinition(
            id=str(uuid.uuid4()),
            type="test-optimization",
            agent_type="any",
            priority=Priority.MEDIUM,
            payload={"target": "test.py"},
            timeout=60,
            retries=3,
            created_at=datetime.now()
        )
        
        task_id = await orchestrator.submit_task(test_task)
        print(f"Submitted task: {task_id}")
        
        # Get status
        await asyncio.sleep(2)
        
        task_status = await orchestrator.get_task_status(task_id)
        print(f"Task status: {task_status}")
        
        queue_status = await orchestrator.get_queue_status()
        print(f"Queue status: {json.dumps(queue_status, indent=2, default=str)}")
        
        await orchestrator.shutdown()
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        asyncio.run(test_task_orchestrator())
    else:
        print("Use 'python task_orchestrator.py test' to run tests")