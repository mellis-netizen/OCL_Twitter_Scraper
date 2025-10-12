"""
Message Queue Integration for TGE Swarm
Provides integration between TGE orchestrator and swarm-agents message queue
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

# Add swarm-agents to path
sys.path.append(str(Path(__file__).parent.parent / 'swarm-agents'))

from backend.message_queue import create_message_queue, MessageQueue, TaskDefinition, Priority


class TGEMessageQueueIntegration:
    """
    Integration layer for TGE-specific message queue operations
    """

    def __init__(self, redis_urls: List[str], cluster_name: str = "tge-swarm"):
        self.redis_urls = redis_urls
        self.cluster_name = cluster_name
        self.message_queue: Optional[MessageQueue] = None

        self.logger = logging.getLogger('TGEMessageQueue')

    async def initialize(self):
        """Initialize message queue connection"""
        self.logger.info(f"Initializing message queue: {self.cluster_name}")

        try:
            self.message_queue = await create_message_queue(
                self.redis_urls,
                self.cluster_name
            )

            self.logger.info("Message queue initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize message queue: {e}")
            raise

    async def enqueue_scraping_task(self, agent_type: str, task_config: Dict[str, Any],
                                   priority: str = 'MEDIUM') -> bool:
        """Enqueue a scraping task"""
        if not self.message_queue:
            raise RuntimeError("Message queue not initialized")

        task = TaskDefinition(
            id=f"scraping-{datetime.now().timestamp()}",
            type='scraping',
            agent_type=agent_type,
            priority=Priority[priority],
            payload=task_config,
            timeout=task_config.get('timeout', 300),
            retries=task_config.get('retries', 3),
            created_at=datetime.now()
        )

        return await self.message_queue.enqueue_task(task)

    async def enqueue_analysis_task(self, items: List[Dict], priority: str = 'HIGH') -> bool:
        """Enqueue an analysis task"""
        if not self.message_queue:
            raise RuntimeError("Message queue not initialized")

        task = TaskDefinition(
            id=f"analysis-{datetime.now().timestamp()}",
            type='analysis',
            agent_type='keyword_analyzer',
            priority=Priority[priority],
            payload={'items': items},
            timeout=180,
            created_at=datetime.now()
        )

        return await self.message_queue.enqueue_task(task)

    async def enqueue_quality_check_task(self, items: List[Dict], check_type: str = 'deduplicate',
                                        priority: str = 'MEDIUM') -> bool:
        """Enqueue a data quality check task"""
        if not self.message_queue:
            raise RuntimeError("Message queue not initialized")

        task = TaskDefinition(
            id=f"quality-{datetime.now().timestamp()}",
            type='quality_check',
            agent_type='data_quality',
            priority=Priority[priority],
            payload={
                'items': items,
                'check_type': check_type
            },
            timeout=120,
            created_at=datetime.now()
        )

        return await self.message_queue.enqueue_task(task)

    async def get_task_results(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent task results"""
        if not self.message_queue:
            raise RuntimeError("Message queue not initialized")

        return await self.message_queue.get_task_results(limit)

    async def get_queue_statistics(self) -> Dict[str, Any]:
        """Get task queue statistics"""
        if not self.message_queue:
            raise RuntimeError("Message queue not initialized")

        return await self.message_queue.get_task_statistics()

    async def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        if not self.message_queue:
            raise RuntimeError("Message queue not initialized")

        return await self.message_queue.get_agent_status()

    async def publish_metric(self, source: str, metric_name: str, value: Any,
                           tags: Dict[str, str] = None):
        """Publish a system metric"""
        if not self.message_queue:
            return

        await self.message_queue.publish_metric(source, metric_name, value, tags)

    async def cleanup_old_tasks(self):
        """Clean up old task entries"""
        if not self.message_queue:
            return

        await self.message_queue.cleanup_expired_tasks()

    async def shutdown(self):
        """Shutdown message queue gracefully"""
        if self.message_queue:
            self.logger.info("Shutting down message queue")
            await self.message_queue.shutdown()
