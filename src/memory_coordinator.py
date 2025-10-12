"""
Memory Coordinator for TGE Swarm
Manages shared state, deduplication caches, and cross-agent memory
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import aiofiles


class TGEMemoryCoordinator:
    """
    Coordinator for shared memory and state management across TGE agents
    """

    def __init__(self, memory_path: str = './tge-memory'):
        self.memory_path = Path(memory_path)
        self.logger = logging.getLogger('TGEMemory')

        # Memory categories
        self.shared_data_path = self.memory_path / 'shared'
        self.dedup_cache_path = self.memory_path / 'dedup'
        self.agent_state_path = self.memory_path / 'agents'
        self.metrics_path = self.memory_path / 'metrics'

        # In-memory caches
        self.shared_cache = {}
        self.dedup_cache = {}
        self.rate_limit_state = {}

    async def initialize(self):
        """Initialize memory coordinator"""
        self.logger.info(f"Initializing memory coordinator at: {self.memory_path}")

        # Create directory structure
        for path in [self.shared_data_path, self.dedup_cache_path,
                    self.agent_state_path, self.metrics_path]:
            path.mkdir(parents=True, exist_ok=True)

        # Load existing caches
        await self._load_caches()

        self.logger.info("Memory coordinator initialized")

    async def _load_caches(self):
        """Load existing memory caches from disk"""
        try:
            # Load shared cache
            shared_file = self.shared_data_path / 'cache.json'
            if shared_file.exists():
                async with aiofiles.open(shared_file, 'r') as f:
                    content = await f.read()
                    self.shared_cache = json.loads(content)
                    self.logger.info(f"Loaded {len(self.shared_cache)} shared cache entries")

            # Load dedup cache
            dedup_file = self.dedup_cache_path / 'cache.json'
            if dedup_file.exists():
                async with aiofiles.open(dedup_file, 'r') as f:
                    content = await f.read()
                    self.dedup_cache = json.loads(content)
                    self.logger.info(f"Loaded {len(self.dedup_cache)} dedup cache entries")

        except Exception as e:
            self.logger.error(f"Error loading caches: {e}")

    async def store_shared_data(self, key: str, value: Any, ttl: int = None):
        """Store data in shared memory"""
        entry = {
            'value': value,
            'timestamp': datetime.now().isoformat(),
            'ttl': ttl
        }

        self.shared_cache[key] = entry

        # Persist to disk
        await self._save_shared_cache()

    async def retrieve_shared_data(self, key: str) -> Optional[Any]:
        """Retrieve data from shared memory"""
        if key not in self.shared_cache:
            return None

        entry = self.shared_cache[key]

        # Check TTL
        if entry.get('ttl'):
            timestamp = datetime.fromisoformat(entry['timestamp'])
            if datetime.now() - timestamp > timedelta(seconds=entry['ttl']):
                # Entry expired
                del self.shared_cache[key]
                return None

        return entry['value']

    async def store_dedup_entry(self, key: str, metadata: Dict[str, Any]):
        """Store deduplication entry"""
        self.dedup_cache[key] = {
            **metadata,
            'timestamp': datetime.now().isoformat()
        }

        # Persist periodically (not every time for performance)
        if len(self.dedup_cache) % 100 == 0:
            await self._save_dedup_cache()

    async def check_duplicate(self, key: str) -> bool:
        """Check if entry exists in dedup cache"""
        return key in self.dedup_cache

    async def get_dedup_entry(self, key: str) -> Optional[Dict[str, Any]]:
        """Get deduplication entry metadata"""
        return self.dedup_cache.get(key)

    async def store_rate_limit_state(self, service: str, endpoint: str, state: Dict[str, Any]):
        """Store rate limit state for coordination"""
        key = f"{service}/{endpoint}"
        self.rate_limit_state[key] = {
            **state,
            'updated_at': datetime.now().isoformat()
        }

    async def get_rate_limit_state(self, service: str, endpoint: str) -> Optional[Dict[str, Any]]:
        """Get rate limit state"""
        key = f"{service}/{endpoint}"
        return self.rate_limit_state.get(key)

    async def store_agent_state(self, agent_id: str, state: Dict[str, Any]):
        """Store agent state"""
        agent_file = self.agent_state_path / f"{agent_id}.json"

        try:
            async with aiofiles.open(agent_file, 'w') as f:
                await f.write(json.dumps(state, indent=2, default=str))
        except Exception as e:
            self.logger.error(f"Error storing agent state for {agent_id}: {e}")

    async def retrieve_agent_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve agent state"""
        agent_file = self.agent_state_path / f"{agent_id}.json"

        if not agent_file.exists():
            return None

        try:
            async with aiofiles.open(agent_file, 'r') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            self.logger.error(f"Error retrieving agent state for {agent_id}: {e}")
            return None

    async def store_metrics(self, category: str, metrics: Dict[str, Any]):
        """Store metrics"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        metrics_file = self.metrics_path / f"{category}_{timestamp}.json"

        try:
            async with aiofiles.open(metrics_file, 'w') as f:
                await f.write(json.dumps(metrics, indent=2, default=str))
        except Exception as e:
            self.logger.error(f"Error storing metrics: {e}")

    async def cleanup_old_entries(self, max_age_days: int = 7):
        """Clean up old memory entries"""
        cutoff = datetime.now() - timedelta(days=max_age_days)

        # Clean shared cache
        expired_keys = []
        for key, entry in self.shared_cache.items():
            timestamp = datetime.fromisoformat(entry['timestamp'])
            if timestamp < cutoff:
                expired_keys.append(key)

        for key in expired_keys:
            del self.shared_cache[key]

        if expired_keys:
            self.logger.info(f"Cleaned up {len(expired_keys)} expired shared cache entries")
            await self._save_shared_cache()

        # Clean dedup cache
        expired_dedup = []
        for key, entry in self.dedup_cache.items():
            timestamp = datetime.fromisoformat(entry['timestamp'])
            if timestamp < cutoff:
                expired_dedup.append(key)

        for key in expired_dedup:
            del self.dedup_cache[key]

        if expired_dedup:
            self.logger.info(f"Cleaned up {len(expired_dedup)} expired dedup entries")
            await self._save_dedup_cache()

    async def _save_shared_cache(self):
        """Persist shared cache to disk"""
        try:
            shared_file = self.shared_data_path / 'cache.json'
            async with aiofiles.open(shared_file, 'w') as f:
                await f.write(json.dumps(self.shared_cache, indent=2, default=str))
        except Exception as e:
            self.logger.error(f"Error saving shared cache: {e}")

    async def _save_dedup_cache(self):
        """Persist dedup cache to disk"""
        try:
            dedup_file = self.dedup_cache_path / 'cache.json'
            async with aiofiles.open(dedup_file, 'w') as f:
                await f.write(json.dumps(self.dedup_cache, indent=2, default=str))
        except Exception as e:
            self.logger.error(f"Error saving dedup cache: {e}")

    async def get_stats(self) -> Dict[str, Any]:
        """Get memory coordinator statistics"""
        return {
            'shared_cache_entries': len(self.shared_cache),
            'dedup_cache_entries': len(self.dedup_cache),
            'rate_limit_entries': len(self.rate_limit_state),
            'memory_path': str(self.memory_path),
            'timestamp': datetime.now().isoformat()
        }

    async def shutdown(self):
        """Shutdown and persist all caches"""
        self.logger.info("Shutting down memory coordinator")

        # Save all caches
        await self._save_shared_cache()
        await self._save_dedup_cache()

        self.logger.info("Memory coordinator shutdown complete")
