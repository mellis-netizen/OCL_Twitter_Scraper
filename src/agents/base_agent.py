"""
Base Agent Class for TGE Swarm Coordination
Provides hooks integration, message queue communication, and state management
"""

import asyncio
import json
import logging
import subprocess
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class BaseAgent(ABC):
    """
    Base class for all TGE swarm agents with integrated coordination capabilities
    """

    def __init__(self, agent_id: str, agent_type: str, config: Dict[str, Any] = None):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.config = config or {}
        self.running = False
        self.session_id = f"swarm-{agent_id}-{int(datetime.now().timestamp())}"

        # State management
        self.state = {
            'status': 'initialized',
            'tasks_completed': 0,
            'tasks_failed': 0,
            'last_activity': None,
            'metrics': {}
        }

        # Setup logging
        self.logger = logging.getLogger(f"Agent.{agent_type}.{agent_id}")
        self.logger.setLevel(logging.INFO)

        # Hooks enabled flag
        self.hooks_enabled = self.config.get('enable_hooks', True)

    async def initialize(self):
        """Initialize agent and run pre-task hooks"""
        self.logger.info(f"Initializing {self.agent_type} agent: {self.agent_id}")

        if self.hooks_enabled:
            await self._run_pre_task_hook(f"Initialize {self.agent_type} agent")
            await self._session_restore()

        await self._do_initialize()
        self.running = True
        self.state['status'] = 'ready'

    @abstractmethod
    async def _do_initialize(self):
        """Agent-specific initialization logic"""
        pass

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task with hooks integration"""
        task_id = task.get('id', str(uuid.uuid4()))
        task_description = task.get('description', 'Unknown task')

        self.logger.info(f"Executing task {task_id}: {task_description}")

        try:
            # Pre-task hook
            if self.hooks_enabled:
                await self._run_pre_task_hook(task_description)

            # Execute actual task
            result = await self._execute_task_impl(task)

            # Post-task hook
            if self.hooks_enabled:
                await self._run_post_task_hook(task_id, success=True)
                await self._notify_completion(task_id, result)

            self.state['tasks_completed'] += 1
            self.state['last_activity'] = datetime.now().isoformat()

            return {
                'success': True,
                'task_id': task_id,
                'agent_id': self.agent_id,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Task {task_id} failed: {str(e)}")

            if self.hooks_enabled:
                await self._run_post_task_hook(task_id, success=False)

            self.state['tasks_failed'] += 1

            return {
                'success': False,
                'task_id': task_id,
                'agent_id': self.agent_id,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    @abstractmethod
    async def _execute_task_impl(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Agent-specific task execution logic"""
        pass

    async def shutdown(self):
        """Graceful shutdown with session end hook"""
        self.logger.info(f"Shutting down {self.agent_type} agent: {self.agent_id}")

        if self.hooks_enabled:
            await self._session_end()

        await self._do_shutdown()
        self.running = False
        self.state['status'] = 'shutdown'

    @abstractmethod
    async def _do_shutdown(self):
        """Agent-specific shutdown logic"""
        pass

    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        return {
            'agent_id': self.agent_id,
            'agent_type': self.agent_type,
            'running': self.running,
            'state': self.state,
            'session_id': self.session_id
        }

    # Hook Integration Methods

    async def _run_pre_task_hook(self, description: str):
        """Run pre-task hook"""
        try:
            cmd = [
                'npx', 'claude-flow@alpha', 'hooks', 'pre-task',
                '--description', description
            ]
            await self._run_hook_command(cmd, "pre-task")
        except Exception as e:
            self.logger.warning(f"Pre-task hook failed: {e}")

    async def _run_post_task_hook(self, task_id: str, success: bool):
        """Run post-task hook"""
        try:
            cmd = [
                'npx', 'claude-flow@alpha', 'hooks', 'post-task',
                '--task-id', task_id
            ]
            await self._run_hook_command(cmd, "post-task")
        except Exception as e:
            self.logger.warning(f"Post-task hook failed: {e}")

    async def _run_post_edit_hook(self, file_path: str, memory_key: str = None):
        """Run post-edit hook for file changes"""
        try:
            if not memory_key:
                memory_key = f"swarm/{self.agent_id}/{int(datetime.now().timestamp())}"

            cmd = [
                'npx', 'claude-flow@alpha', 'hooks', 'post-edit',
                '--file', file_path,
                '--memory-key', memory_key
            ]
            await self._run_hook_command(cmd, "post-edit")
        except Exception as e:
            self.logger.warning(f"Post-edit hook failed: {e}")

    async def _notify_completion(self, task_id: str, result: Any):
        """Notify completion through hooks"""
        try:
            message = f"Task {task_id} completed by {self.agent_type} agent"
            cmd = [
                'npx', 'claude-flow@alpha', 'hooks', 'notify',
                '--message', message
            ]
            await self._run_hook_command(cmd, "notify")
        except Exception as e:
            self.logger.warning(f"Notify hook failed: {e}")

    async def _session_restore(self):
        """Restore session context"""
        try:
            cmd = [
                'npx', 'claude-flow@alpha', 'hooks', 'session-restore',
                '--session-id', self.session_id
            ]
            await self._run_hook_command(cmd, "session-restore")
        except Exception as e:
            self.logger.warning(f"Session restore hook failed: {e}")

    async def _session_end(self):
        """End session with metrics export"""
        try:
            cmd = [
                'npx', 'claude-flow@alpha', 'hooks', 'session-end',
                '--export-metrics', 'true'
            ]
            await self._run_hook_command(cmd, "session-end")
        except Exception as e:
            self.logger.warning(f"Session end hook failed: {e}")

    async def _run_hook_command(self, cmd: List[str], hook_name: str):
        """Execute hook command"""
        self.logger.debug(f"Running {hook_name} hook: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            self.logger.warning(f"{hook_name} hook failed: {error_msg}")
        else:
            output = stdout.decode() if stdout else ""
            self.logger.debug(f"{hook_name} hook output: {output}")

    # Memory Management Methods

    async def store_memory(self, key: str, value: Any, category: str = "agent_data"):
        """Store data in swarm memory"""
        try:
            memory_key = f"{category}/{self.agent_id}/{key}"
            cmd = [
                'npx', 'claude-flow@alpha', 'memory', 'store',
                '--key', memory_key,
                '--value', json.dumps(value)
            ]
            await self._run_hook_command(cmd, "memory-store")
        except Exception as e:
            self.logger.warning(f"Memory store failed: {e}")

    async def retrieve_memory(self, key: str, category: str = "agent_data") -> Optional[Any]:
        """Retrieve data from swarm memory"""
        try:
            memory_key = f"{category}/{self.agent_id}/{key}"
            cmd = [
                'npx', 'claude-flow@alpha', 'memory', 'retrieve',
                '--key', memory_key
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0 and stdout:
                return json.loads(stdout.decode())

            return None

        except Exception as e:
            self.logger.warning(f"Memory retrieve failed: {e}")
            return None

    async def update_metrics(self, metrics: Dict[str, Any]):
        """Update agent metrics"""
        self.state['metrics'].update(metrics)

        if self.hooks_enabled:
            await self.store_memory('metrics', self.state['metrics'], 'metrics')
