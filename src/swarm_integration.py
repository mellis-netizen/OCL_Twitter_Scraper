"""
Swarm Coordination Integration Module
Provides claude-flow swarm coordination hooks for multi-agent orchestration
"""

import os
import json
import logging
import subprocess
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from functools import wraps
import hashlib

logger = logging.getLogger(__name__)


class SwarmCoordinationHooks:
    """
    Claude-flow coordination hooks wrapper for TGE scraping system.
    Enables multi-agent orchestration with shared memory and coordination.
    """

    def __init__(self, enabled: bool = None, session_id: str = None):
        """
        Initialize swarm coordination hooks.

        Args:
            enabled: Enable/disable swarm coordination (default: check env var)
            session_id: Unique session identifier for this swarm instance
        """
        # Check if swarm coordination is enabled
        self.enabled = enabled if enabled is not None else os.getenv('SWARM_ENABLED', 'false').lower() == 'true'

        # Session management
        self.session_id = session_id or os.getenv('SWARM_SESSION_ID', f"tge-scraper-{datetime.now().strftime('%Y%m%d-%H%M%S')}")

        # Agent identification
        self.agent_id = os.getenv('SWARM_AGENT_ID', 'main-scraper')
        self.agent_role = os.getenv('SWARM_AGENT_ROLE', 'scraping-efficiency-specialist')

        # Memory coordination
        self.memory_prefix = f"swarm/{self.agent_id}"
        self.shared_memory_prefix = "swarm/shared"

        # Task tracking
        self.active_tasks = {}
        self.task_metrics = {}

        # Command configuration
        self.claude_flow_cmd = os.getenv('CLAUDE_FLOW_CMD', 'npx claude-flow@alpha')

        logger.info(f"Swarm coordination {'ENABLED' if self.enabled else 'DISABLED'}")
        if self.enabled:
            logger.info(f"Session: {self.session_id}, Agent: {self.agent_id}, Role: {self.agent_role}")

    def _run_hook(self, hook_name: str, **kwargs) -> bool:
        """
        Execute a claude-flow hook command.

        Args:
            hook_name: Name of the hook to execute
            **kwargs: Hook parameters

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.debug(f"Swarm disabled, skipping hook: {hook_name}")
            return True

        try:
            # Build command
            cmd = [self.claude_flow_cmd, 'hooks', hook_name]

            # Add parameters
            for key, value in kwargs.items():
                param_key = f"--{key.replace('_', '-')}"
                cmd.extend([param_key, str(value)])

            # Execute command
            result = subprocess.run(
                ' '.join(cmd),
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.debug(f"Hook {hook_name} executed successfully")
                return True
            else:
                logger.warning(f"Hook {hook_name} failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.warning(f"Hook {hook_name} timed out")
            return False
        except Exception as e:
            logger.error(f"Error executing hook {hook_name}: {str(e)}")
            return False

    async def _run_hook_async(self, hook_name: str, **kwargs) -> bool:
        """Async version of _run_hook."""
        if not self.enabled:
            return True

        try:
            cmd = [self.claude_flow_cmd, 'hooks', hook_name]
            for key, value in kwargs.items():
                param_key = f"--{key.replace('_', '-')}"
                cmd.extend([param_key, str(value)])

            process = await asyncio.create_subprocess_shell(
                ' '.join(cmd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)

            if process.returncode == 0:
                logger.debug(f"Hook {hook_name} executed successfully")
                return True
            else:
                logger.warning(f"Hook {hook_name} failed: {stderr.decode()}")
                return False

        except asyncio.TimeoutError:
            logger.warning(f"Hook {hook_name} timed out")
            return False
        except Exception as e:
            logger.error(f"Error executing hook {hook_name}: {str(e)}")
            return False

    # ========== Pre/Post Task Hooks ==========

    def pre_task(self, description: str, task_id: str = None) -> str:
        """
        Execute pre-task hook before starting a task.

        Args:
            description: Task description
            task_id: Optional task identifier (auto-generated if not provided)

        Returns:
            task_id for tracking
        """
        if task_id is None:
            task_id = f"task-{hashlib.md5(description.encode()).hexdigest()[:8]}-{int(datetime.now().timestamp())}"

        self.active_tasks[task_id] = {
            'description': description,
            'start_time': datetime.now(timezone.utc).isoformat(),
            'status': 'in_progress'
        }

        self._run_hook('pre-task', description=description, task_id=task_id)

        logger.info(f"Started task: {task_id} - {description}")
        return task_id

    async def pre_task_async(self, description: str, task_id: str = None) -> str:
        """Async version of pre_task."""
        if task_id is None:
            task_id = f"task-{hashlib.md5(description.encode()).hexdigest()[:8]}-{int(datetime.now().timestamp())}"

        self.active_tasks[task_id] = {
            'description': description,
            'start_time': datetime.now(timezone.utc).isoformat(),
            'status': 'in_progress'
        }

        await self._run_hook_async('pre-task', description=description, task_id=task_id)

        logger.info(f"Started task: {task_id} - {description}")
        return task_id

    def post_task(self, task_id: str, status: str = 'completed', metrics: Dict = None):
        """
        Execute post-task hook after completing a task.

        Args:
            task_id: Task identifier from pre_task
            status: Task completion status (completed/failed/partial)
            metrics: Optional performance metrics
        """
        if task_id not in self.active_tasks:
            logger.warning(f"Unknown task_id: {task_id}")
            return

        task = self.active_tasks[task_id]
        task['status'] = status
        task['end_time'] = datetime.now(timezone.utc).isoformat()

        if metrics:
            task['metrics'] = metrics
            self.task_metrics[task_id] = metrics

        # Build metrics string for hook
        metrics_str = json.dumps(metrics) if metrics else "{}"

        self._run_hook('post-task', task_id=task_id, status=status, metrics=metrics_str)

        logger.info(f"Completed task: {task_id} - {status}")

        # Move to history
        self.active_tasks.pop(task_id, None)

    async def post_task_async(self, task_id: str, status: str = 'completed', metrics: Dict = None):
        """Async version of post_task."""
        if task_id not in self.active_tasks:
            logger.warning(f"Unknown task_id: {task_id}")
            return

        task = self.active_tasks[task_id]
        task['status'] = status
        task['end_time'] = datetime.now(timezone.utc).isoformat()

        if metrics:
            task['metrics'] = metrics
            self.task_metrics[task_id] = metrics

        metrics_str = json.dumps(metrics) if metrics else "{}"
        await self._run_hook_async('post-task', task_id=task_id, status=status, metrics=metrics_str)

        logger.info(f"Completed task: {task_id} - {status}")
        self.active_tasks.pop(task_id, None)

    # ========== Memory Coordination Hooks ==========

    def memory_store(self, key: str, value: Any, ttl: int = 300, shared: bool = False):
        """
        Store data in swarm shared memory.

        Args:
            key: Memory key (will be prefixed with agent/shared namespace)
            value: Data to store (will be JSON serialized)
            ttl: Time-to-live in seconds (default: 5 minutes)
            shared: If True, store in shared namespace accessible by all agents
        """
        if not self.enabled:
            return

        # Determine namespace
        prefix = self.shared_memory_prefix if shared else self.memory_prefix
        full_key = f"{prefix}/{key}"

        # Serialize value
        if isinstance(value, (dict, list)):
            value_str = json.dumps(value)
        else:
            value_str = str(value)

        self._run_hook('memory-store', key=full_key, value=value_str, ttl=ttl)

        logger.debug(f"Stored in memory: {full_key} (TTL: {ttl}s)")

    async def memory_store_async(self, key: str, value: Any, ttl: int = 300, shared: bool = False):
        """Async version of memory_store."""
        if not self.enabled:
            return

        prefix = self.shared_memory_prefix if shared else self.memory_prefix
        full_key = f"{prefix}/{key}"

        if isinstance(value, (dict, list)):
            value_str = json.dumps(value)
        else:
            value_str = str(value)

        await self._run_hook_async('memory-store', key=full_key, value=value_str, ttl=ttl)
        logger.debug(f"Stored in memory: {full_key} (TTL: {ttl}s)")

    def memory_retrieve(self, key: str, shared: bool = False) -> Optional[Any]:
        """
        Retrieve data from swarm shared memory.

        Args:
            key: Memory key
            shared: If True, retrieve from shared namespace

        Returns:
            Stored value or None if not found
        """
        if not self.enabled:
            return None

        prefix = self.shared_memory_prefix if shared else self.memory_prefix
        full_key = f"{prefix}/{key}"

        try:
            result = subprocess.run(
                f"{self.claude_flow_cmd} hooks memory-retrieve --key {full_key}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout:
                # Try to parse as JSON
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return result.stdout.strip()

            return None

        except Exception as e:
            logger.error(f"Error retrieving memory {full_key}: {str(e)}")
            return None

    # ========== Post-Edit Hooks ==========

    def post_edit(self, file_path: str, operation: str = "update", memory_key: str = None):
        """
        Execute post-edit hook after modifying a file or data.

        Args:
            file_path: Path to file that was edited (or logical identifier)
            operation: Type of operation (create/update/delete)
            memory_key: Optional memory key to store edit metadata
        """
        if not self.enabled:
            return

        # Build memory key if not provided
        if memory_key is None:
            file_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
            memory_key = f"{self.memory_prefix}/edits/{file_hash}"

        # Store edit metadata
        edit_metadata = {
            'file': file_path,
            'operation': operation,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'agent': self.agent_id
        }

        self._run_hook('post-edit', file=file_path, memory_key=memory_key)

        # Also store in memory for coordination
        self.memory_store(f"edits/{file_path}", edit_metadata, ttl=600, shared=True)

        logger.debug(f"Post-edit hook: {file_path} - {operation}")

    async def post_edit_async(self, file_path: str, operation: str = "update", memory_key: str = None):
        """Async version of post_edit."""
        if not self.enabled:
            return

        if memory_key is None:
            file_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
            memory_key = f"{self.memory_prefix}/edits/{file_hash}"

        edit_metadata = {
            'file': file_path,
            'operation': operation,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'agent': self.agent_id
        }

        await self._run_hook_async('post-edit', file=file_path, memory_key=memory_key)
        await self.memory_store_async(f"edits/{file_path}", edit_metadata, ttl=600, shared=True)

        logger.debug(f"Post-edit hook: {file_path} - {operation}")

    # ========== Notification Hooks ==========

    def notify(self, message: str, level: str = "info"):
        """
        Send notification to swarm coordination system.

        Args:
            message: Notification message
            level: Notification level (info/warning/error/success)
        """
        if not self.enabled:
            return

        self._run_hook('notify', message=message, level=level)
        logger.debug(f"Swarm notification ({level}): {message}")

    async def notify_async(self, message: str, level: str = "info"):
        """Async version of notify."""
        if not self.enabled:
            return

        await self._run_hook_async('notify', message=message, level=level)
        logger.debug(f"Swarm notification ({level}): {message}")

    # ========== Session Management ==========

    def session_restore(self):
        """Restore swarm session context."""
        if not self.enabled:
            return

        self._run_hook('session-restore', session_id=self.session_id)
        logger.info(f"Restored swarm session: {self.session_id}")

    def session_end(self, export_metrics: bool = True):
        """End swarm session and optionally export metrics."""
        if not self.enabled:
            return

        self._run_hook('session-end', session_id=self.session_id, export_metrics=str(export_metrics).lower())
        logger.info(f"Ended swarm session: {self.session_id}")

    # ========== Rate Limit Coordination ==========

    def coordinate_rate_limit(self, service: str, limit_info: Dict):
        """
        Share rate limit information with other agents.

        Args:
            service: Service name (twitter/news_api/etc)
            limit_info: Rate limit details (remaining, reset_time, etc)
        """
        if not self.enabled:
            return

        key = f"rate_limits/{service}"
        self.memory_store(key, limit_info, ttl=900, shared=True)  # 15 min TTL

        logger.debug(f"Coordinated rate limit for {service}: {limit_info}")

    async def coordinate_rate_limit_async(self, service: str, limit_info: Dict):
        """Async version of coordinate_rate_limit."""
        if not self.enabled:
            return

        key = f"rate_limits/{service}"
        await self.memory_store_async(key, limit_info, ttl=900, shared=True)
        logger.debug(f"Coordinated rate limit for {service}: {limit_info}")

    def get_rate_limit_state(self, service: str) -> Optional[Dict]:
        """
        Get current rate limit state from shared memory.

        Args:
            service: Service name

        Returns:
            Rate limit info or None
        """
        if not self.enabled:
            return None

        key = f"rate_limits/{service}"
        return self.memory_retrieve(key, shared=True)

    # ========== Deduplication Coordination ==========

    def coordinate_deduplication(self, content_hash: str, metadata: Dict):
        """
        Share deduplication data with other agents.

        Args:
            content_hash: Hash of content
            metadata: Metadata about the content (url, timestamp, etc)
        """
        if not self.enabled:
            return

        key = f"dedup/{content_hash}"
        self.memory_store(key, metadata, ttl=86400, shared=True)  # 24h TTL

    async def coordinate_deduplication_async(self, content_hash: str, metadata: Dict):
        """Async version of coordinate_deduplication."""
        if not self.enabled:
            return

        key = f"dedup/{content_hash}"
        await self.memory_store_async(key, metadata, ttl=86400, shared=True)

    def check_duplicate(self, content_hash: str) -> bool:
        """
        Check if content has been seen by any agent.

        Args:
            content_hash: Hash of content to check

        Returns:
            True if duplicate, False if unique
        """
        if not self.enabled:
            return False

        key = f"dedup/{content_hash}"
        return self.memory_retrieve(key, shared=True) is not None


# ========== Decorator Utilities ==========

def with_swarm_task(description: str):
    """
    Decorator to wrap a function with pre/post task hooks.

    Usage:
        @with_swarm_task("Scraping news feeds")
        def scrape_news():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Try to find swarm hooks instance
            hooks = None
            if args and hasattr(args[0], 'swarm_hooks'):
                hooks = args[0].swarm_hooks
            elif 'swarm_hooks' in kwargs:
                hooks = kwargs['swarm_hooks']

            if hooks and hooks.enabled:
                task_id = hooks.pre_task(description)
                try:
                    result = func(*args, **kwargs)
                    hooks.post_task(task_id, status='completed')
                    return result
                except Exception as e:
                    hooks.post_task(task_id, status='failed', metrics={'error': str(e)})
                    raise
            else:
                return func(*args, **kwargs)

        return wrapper
    return decorator


def with_swarm_task_async(description: str):
    """Async version of with_swarm_task decorator."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            hooks = None
            if args and hasattr(args[0], 'swarm_hooks'):
                hooks = args[0].swarm_hooks
            elif 'swarm_hooks' in kwargs:
                hooks = kwargs['swarm_hooks']

            if hooks and hooks.enabled:
                task_id = await hooks.pre_task_async(description)
                try:
                    result = await func(*args, **kwargs)
                    await hooks.post_task_async(task_id, status='completed')
                    return result
                except Exception as e:
                    await hooks.post_task_async(task_id, status='failed', metrics={'error': str(e)})
                    raise
            else:
                return await func(*args, **kwargs)

        return wrapper
    return decorator


# ========== Global Instance ==========

# Create a global instance that can be used throughout the application
_global_hooks = None

def get_swarm_hooks() -> SwarmCoordinationHooks:
    """Get or create global swarm hooks instance."""
    global _global_hooks
    if _global_hooks is None:
        _global_hooks = SwarmCoordinationHooks()
    return _global_hooks


def initialize_swarm(enabled: bool = None, session_id: str = None) -> SwarmCoordinationHooks:
    """
    Initialize swarm coordination system.

    Args:
        enabled: Enable/disable swarm coordination
        session_id: Unique session identifier

    Returns:
        SwarmCoordinationHooks instance
    """
    global _global_hooks
    _global_hooks = SwarmCoordinationHooks(enabled=enabled, session_id=session_id)
    return _global_hooks
