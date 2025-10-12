"""
Coordinator Agent
Manages task distribution, priority scheduling, and agent coordination
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict
import heapq

from src.agents.base_agent import BaseAgent


class CoordinatorAgent(BaseAgent):
    """
    Agent specialized in coordinating tasks across multiple agents
    """

    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, "coordinator", config)

        self.task_queue = []  # Priority queue of tasks
        self.agent_registry = {}  # Available agents by type
        self.agent_workloads = defaultdict(int)  # Current workload per agent
        self.task_history = []  # Completed task history
        self.max_workload_per_agent = config.get('max_workload_per_agent', 5)

    async def _do_initialize(self):
        """Initialize coordinator"""
        self.logger.info("Coordinator agent initialized")

        await self.store_memory('initialized', {
            'timestamp': datetime.now().isoformat(),
            'max_workload': self.max_workload_per_agent
        }, 'initialization')

    async def _execute_task_impl(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute coordination task"""
        task_type = task.get('type', 'distribute_tasks')

        if task_type == 'register_agent':
            return await self._register_agent(task)
        elif task_type == 'unregister_agent':
            return await self._unregister_agent(task)
        elif task_type == 'distribute_tasks':
            return await self._distribute_tasks(task)
        elif task_type == 'assign_task':
            return await self._assign_task(task)
        elif task_type == 'get_status':
            return await self._get_coordination_status(task)
        elif task_type == 'rebalance':
            return await self._rebalance_workloads(task)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def _register_agent(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Register an agent with the coordinator"""
        agent_id = task.get('agent_id')
        agent_type = task.get('agent_type')
        capabilities = task.get('capabilities', [])

        if not agent_id or not agent_type:
            raise ValueError("agent_id and agent_type are required")

        self.agent_registry[agent_id] = {
            'type': agent_type,
            'capabilities': capabilities,
            'registered_at': datetime.now().isoformat(),
            'status': 'active'
        }

        self.agent_workloads[agent_id] = 0

        # Store in memory
        await self.store_memory('agent_registry', self.agent_registry, 'coordination')

        self.logger.info(f"Registered agent {agent_id} of type {agent_type}")

        return {
            'agent_id': agent_id,
            'registered': True,
            'total_agents': len(self.agent_registry)
        }

    async def _unregister_agent(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Unregister an agent"""
        agent_id = task.get('agent_id')

        if agent_id in self.agent_registry:
            del self.agent_registry[agent_id]
            del self.agent_workloads[agent_id]

            await self.store_memory('agent_registry', self.agent_registry, 'coordination')

            self.logger.info(f"Unregistered agent {agent_id}")

            return {
                'agent_id': agent_id,
                'unregistered': True
            }

        return {
            'agent_id': agent_id,
            'unregistered': False,
            'error': 'agent not found'
        }

    async def _distribute_tasks(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Distribute tasks to available agents"""
        tasks_to_distribute = task.get('tasks', [])
        strategy = task.get('strategy', 'load_balanced')

        assignments = []
        unassigned = []

        for t in tasks_to_distribute:
            assigned = await self._assign_single_task(t, strategy)
            if assigned['success']:
                assignments.append(assigned)
            else:
                unassigned.append(t)

        # Store distribution results
        await self.store_memory(f'distribution_{int(datetime.now().timestamp())}', {
            'total_tasks': len(tasks_to_distribute),
            'assigned': len(assignments),
            'unassigned': len(unassigned),
            'timestamp': datetime.now().isoformat()
        }, 'distribution_results')

        # Update metrics
        await self.update_metrics({
            'tasks_distributed': self.state['metrics'].get('tasks_distributed', 0) + len(assignments),
            'tasks_unassigned': self.state['metrics'].get('tasks_unassigned', 0) + len(unassigned)
        })

        return {
            'assignments': assignments,
            'unassigned': unassigned,
            'stats': {
                'total_tasks': len(tasks_to_distribute),
                'assigned_count': len(assignments),
                'unassigned_count': len(unassigned),
                'assignment_rate': len(assignments) / len(tasks_to_distribute) if tasks_to_distribute else 0
            }
        }

    async def _assign_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Assign a single task to an agent"""
        strategy = task.get('strategy', 'load_balanced')
        return await self._assign_single_task(task, strategy)

    async def _assign_single_task(self, task: Dict[str, Any], strategy: str) -> Dict[str, Any]:
        """Core logic for assigning a task"""
        required_type = task.get('agent_type', 'any')
        priority = task.get('priority', 1)

        # Find suitable agents
        candidates = self._find_suitable_agents(required_type)

        if not candidates:
            return {
                'success': False,
                'task_id': task.get('id'),
                'error': f'no agents available for type {required_type}'
            }

        # Select agent based on strategy
        selected_agent = self._select_agent(candidates, strategy)

        # Assign task
        self.agent_workloads[selected_agent] += 1

        # Add to task history
        self.task_history.append({
            'task_id': task.get('id'),
            'assigned_to': selected_agent,
            'assigned_at': datetime.now().isoformat(),
            'priority': priority
        })

        return {
            'success': True,
            'task_id': task.get('id'),
            'assigned_to': selected_agent,
            'agent_type': self.agent_registry[selected_agent]['type'],
            'current_workload': self.agent_workloads[selected_agent]
        }

    def _find_suitable_agents(self, required_type: str) -> List[str]:
        """Find agents that can handle the task"""
        if required_type == 'any':
            return [
                agent_id for agent_id, info in self.agent_registry.items()
                if info['status'] == 'active' and self.agent_workloads[agent_id] < self.max_workload_per_agent
            ]

        return [
            agent_id for agent_id, info in self.agent_registry.items()
            if info['type'] == required_type and info['status'] == 'active'
            and self.agent_workloads[agent_id] < self.max_workload_per_agent
        ]

    def _select_agent(self, candidates: List[str], strategy: str) -> str:
        """Select best agent based on strategy"""
        if strategy == 'load_balanced':
            # Select agent with lowest workload
            return min(candidates, key=lambda x: self.agent_workloads[x])

        elif strategy == 'round_robin':
            # Simple round-robin selection
            return candidates[len(self.task_history) % len(candidates)]

        elif strategy == 'random':
            # Random selection
            import random
            return random.choice(candidates)

        else:
            # Default to load balanced
            return min(candidates, key=lambda x: self.agent_workloads[x])

    async def _get_coordination_status(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get current coordination status"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'total_agents': len(self.agent_registry),
            'active_agents': sum(1 for info in self.agent_registry.values() if info['status'] == 'active'),
            'agent_types': defaultdict(int),
            'workloads': dict(self.agent_workloads),
            'total_tasks_assigned': len(self.task_history),
            'recent_tasks': self.task_history[-10:] if self.task_history else []
        }

        # Count agents by type
        for info in self.agent_registry.values():
            status['agent_types'][info['type']] += 1

        status['agent_types'] = dict(status['agent_types'])

        return status

    async def _rebalance_workloads(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Rebalance workloads across agents"""
        self.logger.info("Rebalancing agent workloads")

        # Get current workload distribution
        workloads = list(self.agent_workloads.items())
        avg_workload = sum(w for _, w in workloads) / len(workloads) if workloads else 0

        # Identify overloaded and underloaded agents
        overloaded = [(agent, load) for agent, load in workloads if load > avg_workload * 1.5]
        underloaded = [(agent, load) for agent, load in workloads if load < avg_workload * 0.5]

        rebalance_actions = []

        for agent, load in overloaded:
            target_reduction = int((load - avg_workload) / 2)
            rebalance_actions.append({
                'agent': agent,
                'action': 'reduce',
                'amount': target_reduction
            })

        for agent, load in underloaded:
            target_increase = int((avg_workload - load) / 2)
            rebalance_actions.append({
                'agent': agent,
                'action': 'increase',
                'amount': target_increase
            })

        return {
            'avg_workload': avg_workload,
            'overloaded_count': len(overloaded),
            'underloaded_count': len(underloaded),
            'rebalance_actions': rebalance_actions
        }

    def complete_task(self, agent_id: str, task_id: str, success: bool):
        """Mark a task as completed and update workload"""
        if agent_id in self.agent_workloads:
            self.agent_workloads[agent_id] = max(0, self.agent_workloads[agent_id] - 1)

        # Update task history
        for task in self.task_history:
            if task.get('task_id') == task_id:
                task['completed_at'] = datetime.now().isoformat()
                task['success'] = success
                break

    async def _do_shutdown(self):
        """Clean up coordinator resources"""
        self.logger.info("Shutting down coordinator agent")

        # Save final state
        await self.store_memory('final_state', {
            'total_agents': len(self.agent_registry),
            'total_tasks': len(self.task_history),
            'timestamp': datetime.now().isoformat()
        }, 'shutdown')
