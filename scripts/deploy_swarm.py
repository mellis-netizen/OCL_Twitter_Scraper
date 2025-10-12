#!/usr/bin/env python3
"""
TGE Swarm Deployment Script
Automates deployment, initialization, and health monitoring of TGE swarm system
"""

import asyncio
import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.orchestrator import TGESwarmOrchestrator
from src.swarm_config import SwarmConfigManager


class SwarmDeploymentManager:
    """
    Manages deployment and lifecycle of TGE swarm system
    """

    def __init__(self, config_path: str = "config/tge_swarm.yaml"):
        self.config_path = config_path
        self.config_manager = SwarmConfigManager(config_path)
        self.config = self.config_manager.load_config()

        self.orchestrator = None
        self.health_check_interval = 30

        self.setup_logging()

    def setup_logging(self):
        """Setup deployment logging"""
        log_level = self.config.get('log_level', 'INFO')

        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/deployment.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )

        self.logger = logging.getLogger('SwarmDeployment')

    async def deploy(self):
        """Deploy the TGE swarm system"""
        self.logger.info("=" * 60)
        self.logger.info("Starting TGE Swarm Deployment")
        self.logger.info("=" * 60)

        try:
            # Step 1: Validate environment
            self.logger.info("Step 1: Validating environment...")
            if not await self.validate_environment():
                self.logger.error("Environment validation failed")
                return False

            # Step 2: Initialize Redis
            self.logger.info("Step 2: Checking Redis connection...")
            if not await self.check_redis():
                self.logger.error("Redis connection failed")
                return False

            # Step 3: Initialize directory structure
            self.logger.info("Step 3: Creating directory structure...")
            self.create_directories()

            # Step 4: Generate configuration if needed
            self.logger.info("Step 4: Generating configuration...")
            await self.generate_config()

            # Step 5: Initialize claude-flow hooks
            self.logger.info("Step 5: Initializing claude-flow...")
            if not await self.initialize_claude_flow():
                self.logger.warning("Claude-flow initialization failed (optional)")

            # Step 6: Deploy orchestrator
            self.logger.info("Step 6: Deploying orchestrator...")
            if not await self.deploy_orchestrator():
                self.logger.error("Orchestrator deployment failed")
                return False

            # Step 7: Verify deployment
            self.logger.info("Step 7: Verifying deployment...")
            if not await self.verify_deployment():
                self.logger.error("Deployment verification failed")
                return False

            self.logger.info("=" * 60)
            self.logger.info("TGE Swarm Deployment Complete!")
            self.logger.info("=" * 60)

            return True

        except Exception as e:
            self.logger.error(f"Deployment failed: {e}")
            return False

    async def validate_environment(self) -> bool:
        """Validate deployment environment"""
        self.logger.info("Validating Python version...")

        if sys.version_info < (3, 8):
            self.logger.error("Python 3.8+ required")
            return False

        self.logger.info(f"Python version: {sys.version}")

        # Check required packages
        required_packages = [
            'asyncio', 'yaml', 'aiofiles', 'redis'
        ]

        for package in required_packages:
            try:
                __import__(package)
                self.logger.info(f"✓ Package available: {package}")
            except ImportError:
                self.logger.error(f"✗ Missing package: {package}")
                return False

        return True

    async def check_redis(self) -> bool:
        """Check Redis connection"""
        redis_urls = self.config.get('redis_urls', ['localhost:6379'])

        for redis_url in redis_urls:
            try:
                host, port = redis_url.split(':')

                # Try to connect using redis-py
                import redis.asyncio as redis

                r = redis.Redis(host=host, port=int(port), decode_responses=True)
                await r.ping()
                await r.close()

                self.logger.info(f"✓ Redis connection successful: {redis_url}")
                return True

            except Exception as e:
                self.logger.warning(f"✗ Redis connection failed for {redis_url}: {e}")
                continue

        self.logger.error("Could not connect to any Redis instance")
        return False

    def create_directories(self):
        """Create necessary directories"""
        directories = [
            'logs',
            'config',
            'state',
            'tge-memory',
            'tge-memory/shared',
            'tge-memory/dedup',
            'tge-memory/agents',
            'tge-memory/metrics'
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            self.logger.info(f"✓ Directory created: {directory}")

    async def generate_config(self):
        """Generate default configuration if not exists"""
        config_file = Path(self.config_path)

        if not config_file.exists():
            self.logger.info(f"Generating default config at {self.config_path}")

            # Ensure parent directory exists
            config_file.parent.mkdir(parents=True, exist_ok=True)

            # Save default config
            self.config_manager.save_config(self.config)

            self.logger.info("✓ Default configuration generated")
        else:
            self.logger.info("✓ Using existing configuration")

    async def initialize_claude_flow(self) -> bool:
        """Initialize claude-flow hooks system"""
        try:
            # Check if claude-flow is available
            result = subprocess.run(
                ['npx', 'claude-flow@alpha', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                self.logger.info("✓ Claude-flow available")

                # Initialize swarm
                init_result = subprocess.run(
                    ['npx', 'claude-flow@alpha', 'swarm', 'init', '--topology', 'mesh'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if init_result.returncode == 0:
                    self.logger.info("✓ Claude-flow swarm initialized")
                    return True
                else:
                    self.logger.warning(f"Claude-flow init warning: {init_result.stderr}")
                    return True  # Non-critical
            else:
                self.logger.warning("Claude-flow not available (optional)")
                return True

        except subprocess.TimeoutExpired:
            self.logger.warning("Claude-flow initialization timed out (optional)")
            return True
        except Exception as e:
            self.logger.warning(f"Claude-flow initialization failed: {e} (optional)")
            return True

    async def deploy_orchestrator(self) -> bool:
        """Deploy the TGE orchestrator"""
        try:
            self.logger.info("Creating orchestrator instance...")

            self.orchestrator = TGESwarmOrchestrator(self.config_path)

            self.logger.info("Initializing orchestrator...")

            if await self.orchestrator.initialize():
                self.logger.info("✓ Orchestrator deployed successfully")
                return True
            else:
                self.logger.error("✗ Orchestrator initialization failed")
                return False

        except Exception as e:
            self.logger.error(f"Orchestrator deployment error: {e}")
            return False

    async def verify_deployment(self) -> bool:
        """Verify deployment health"""
        if not self.orchestrator:
            return False

        try:
            # Get system status
            status = await self.orchestrator.get_system_status()

            # Check orchestrator
            if not status.get('orchestrator', {}).get('running'):
                self.logger.error("Orchestrator not running")
                return False

            self.logger.info("✓ Orchestrator running")

            # Check agents
            agents = status.get('agents', {})
            agent_count = len(agents)

            if agent_count == 0:
                self.logger.error("No agents initialized")
                return False

            self.logger.info(f"✓ {agent_count} agents initialized")

            # Check each agent
            for agent_id, agent_status in agents.items():
                if agent_status.get('running'):
                    self.logger.info(f"  ✓ {agent_id}: running")
                else:
                    self.logger.warning(f"  ✗ {agent_id}: not running")

            # Check memory
            memory = status.get('memory', {})
            self.logger.info(f"✓ Memory coordinator: {memory.get('shared_cache_entries', 0)} shared entries")

            return True

        except Exception as e:
            self.logger.error(f"Verification failed: {e}")
            return False

    async def run_health_monitoring(self):
        """Run continuous health monitoring"""
        self.logger.info("Starting health monitoring...")

        while True:
            try:
                await asyncio.sleep(self.health_check_interval)

                if self.orchestrator:
                    status = await self.orchestrator.get_system_status()

                    # Log health summary
                    self.logger.info("=" * 40)
                    self.logger.info("Health Check Summary")
                    self.logger.info("=" * 40)

                    orchestrator_status = status.get('orchestrator', {})
                    self.logger.info(f"Orchestrator: {'RUNNING' if orchestrator_status.get('running') else 'STOPPED'}")
                    self.logger.info(f"Cycle: #{orchestrator_status.get('cycle_count', 0)}")

                    agents = status.get('agents', {})
                    running_agents = sum(1 for a in agents.values() if a.get('running'))
                    self.logger.info(f"Agents: {running_agents}/{len(agents)} running")

                    memory = status.get('memory', {})
                    self.logger.info(f"Memory: {memory.get('shared_cache_entries', 0)} shared, "
                                   f"{memory.get('dedup_cache_entries', 0)} dedup entries")

                    self.logger.info("=" * 40)

            except Exception as e:
                self.logger.error(f"Health check error: {e}")

    async def start(self):
        """Start the deployed system"""
        if not self.orchestrator:
            self.logger.error("Orchestrator not deployed. Run 'deploy' first.")
            return

        self.logger.info("Starting TGE Swarm Orchestrator...")

        # Start health monitoring in background
        health_task = asyncio.create_task(self.run_health_monitoring())

        try:
            # Run orchestrator
            await self.orchestrator.run()
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        finally:
            health_task.cancel()
            await self.shutdown()

    async def shutdown(self):
        """Shutdown the system"""
        self.logger.info("Shutting down TGE Swarm...")

        if self.orchestrator:
            await self.orchestrator.shutdown()

        self.logger.info("Shutdown complete")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='TGE Swarm Deployment Manager')
    parser.add_argument('action', choices=['deploy', 'start', 'status', 'deploy-and-start'],
                       help='Deployment action')
    parser.add_argument('--config', default='config/tge_swarm.yaml',
                       help='Configuration file path')

    args = parser.parse_args()

    manager = SwarmDeploymentManager(args.config)

    if args.action == 'deploy':
        success = await manager.deploy()
        sys.exit(0 if success else 1)

    elif args.action == 'start':
        await manager.start()

    elif args.action == 'deploy-and-start':
        if await manager.deploy():
            await manager.start()
        else:
            sys.exit(1)

    elif args.action == 'status':
        if await manager.deploy():
            status = await manager.orchestrator.get_system_status()
            import json
            print(json.dumps(status, indent=2, default=str))
            await manager.shutdown()
        else:
            sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
