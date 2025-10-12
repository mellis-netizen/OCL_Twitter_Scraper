"""
TGE Swarm Orchestrator
Main orchestration service combining TGE scraping with swarm coordination
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add paths
sys.path.append(str(Path(__file__).parent.parent))

from src.agents import (
    NewsScraperAgent,
    TwitterMonitorAgent,
    KeywordAnalyzerAgent,
    DataQualityAgent,
    CoordinatorAgent
)
from src.message_queue_integration import TGEMessageQueueIntegration
from src.memory_coordinator import TGEMemoryCoordinator
from src.swarm_config import SwarmConfigManager


class TGESwarmOrchestrator:
    """
    Unified orchestrator for TGE detection with multi-agent coordination
    Combines scraping, monitoring, analysis, and quality control
    """

    def __init__(self, config_path: str = "config/tge_swarm.yaml"):
        # Load configuration
        self.config_manager = SwarmConfigManager(config_path)
        self.config = self.config_manager.load_config()

        # Core components
        self.message_queue: Optional[TGEMessageQueueIntegration] = None
        self.memory_coordinator: Optional[TGEMemoryCoordinator] = None

        # Agents
        self.agents = {}
        self.coordinator: Optional[CoordinatorAgent] = None

        # State
        self.running = False
        self.cycle_count = 0
        self.scraping_interval = self.config.get('scraping_interval', 300)  # 5 minutes default

        # Setup logging
        self.setup_logging()

        # Signal handlers for graceful shutdown
        self.setup_signal_handlers()

    def setup_logging(self):
        """Setup comprehensive logging"""
        log_level = self.config.get('log_level', 'INFO')
        log_file = self.config.get('log_file', 'logs/orchestrator.log')

        Path(log_file).parent.mkdir(exist_ok=True, parents=True)

        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )

        self.logger = logging.getLogger('TGEOrchestrator')
        self.logger.info("TGE Swarm Orchestrator logging initialized")

    def setup_signal_handlers(self):
        """Setup graceful shutdown on signals"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def initialize(self):
        """Initialize all orchestrator components"""
        self.logger.info("Initializing TGE Swarm Orchestrator...")

        try:
            # Initialize message queue
            self.logger.info("Initializing message queue...")
            self.message_queue = TGEMessageQueueIntegration(
                self.config.get('redis_urls', ['localhost:6379']),
                self.config.get('cluster_name', 'tge-swarm')
            )
            await self.message_queue.initialize()

            # Initialize memory coordinator
            self.logger.info("Initializing memory coordinator...")
            self.memory_coordinator = TGEMemoryCoordinator(
                self.config.get('memory_path', './tge-memory')
            )
            await self.memory_coordinator.initialize()

            # Initialize coordinator agent
            self.logger.info("Initializing coordinator agent...")
            self.coordinator = CoordinatorAgent(
                agent_id='coordinator-main',
                config=self.config.get('coordinator', {})
            )
            await self.coordinator.initialize()

            # Initialize specialized agents
            await self._initialize_agents()

            self.running = True
            self.logger.info("TGE Swarm Orchestrator initialized successfully")

            return True

        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            await self.shutdown()
            return False

    async def _initialize_agents(self):
        """Initialize all specialized agents"""
        agent_configs = self.config.get('agents', {})

        # News Scraper Agents
        news_agent_count = agent_configs.get('news_scraper', {}).get('count', 1)
        for i in range(news_agent_count):
            agent_id = f'news-scraper-{i}'
            agent = NewsScraperAgent(
                agent_id=agent_id,
                config={
                    **agent_configs.get('news_scraper', {}),
                    'companies': self.config.get('companies', []),
                    'keywords': self.config.get('keywords', []),
                    'news_sources': self.config.get('news_sources', [])
                }
            )
            await agent.initialize()
            self.agents[agent_id] = agent

            # Register with coordinator
            await self.coordinator.execute_task({
                'type': 'register_agent',
                'agent_id': agent_id,
                'agent_type': 'news_scraper',
                'capabilities': ['fetch_articles', 'analyze_feed_health']
            })

        # Twitter Monitor Agents
        twitter_agent_count = agent_configs.get('twitter_monitor', {}).get('count', 1)
        twitter_token = self.config.get('twitter_bearer_token')

        if twitter_token:
            for i in range(twitter_agent_count):
                agent_id = f'twitter-monitor-{i}'
                agent = TwitterMonitorAgent(
                    agent_id=agent_id,
                    config={
                        **agent_configs.get('twitter_monitor', {}),
                        'bearer_token': twitter_token,
                        'companies': self.config.get('companies', []),
                        'keywords': self.config.get('keywords', [])
                    }
                )
                await agent.initialize()
                self.agents[agent_id] = agent

                await self.coordinator.execute_task({
                    'type': 'register_agent',
                    'agent_id': agent_id,
                    'agent_type': 'twitter_monitor',
                    'capabilities': ['fetch_tweets', 'search_tge']
                })

        # Keyword Analyzer Agents
        analyzer_agent_count = agent_configs.get('keyword_analyzer', {}).get('count', 1)
        for i in range(analyzer_agent_count):
            agent_id = f'keyword-analyzer-{i}'
            agent = KeywordAnalyzerAgent(
                agent_id=agent_id,
                config=agent_configs.get('keyword_analyzer', {})
            )
            await agent.initialize()
            self.agents[agent_id] = agent

            await self.coordinator.execute_task({
                'type': 'register_agent',
                'agent_id': agent_id,
                'agent_type': 'keyword_analyzer',
                'capabilities': ['analyze_content', 'batch_analyze']
            })

        # Data Quality Agents
        quality_agent_count = agent_configs.get('data_quality', {}).get('count', 1)
        for i in range(quality_agent_count):
            agent_id = f'data-quality-{i}'
            agent = DataQualityAgent(
                agent_id=agent_id,
                config=agent_configs.get('data_quality', {})
            )
            await agent.initialize()
            self.agents[agent_id] = agent

            await self.coordinator.execute_task({
                'type': 'register_agent',
                'agent_id': agent_id,
                'agent_type': 'data_quality',
                'capabilities': ['deduplicate', 'validate']
            })

        self.logger.info(f"Initialized {len(self.agents)} specialized agents")

    async def run(self):
        """Main orchestration loop"""
        if not await self.initialize():
            self.logger.error("Failed to initialize orchestrator")
            return

        self.logger.info("Starting TGE Swarm Orchestrator main loop...")

        try:
            while self.running:
                cycle_start = datetime.now()
                self.cycle_count += 1

                self.logger.info(f"=== Starting scraping cycle #{self.cycle_count} ===")

                try:
                    # Execute parallel scraping cycle
                    await self.orchestrate_scraping_cycle()

                    # Coordinate agent communication
                    await self.coordinate_agents()

                except Exception as e:
                    self.logger.error(f"Error in scraping cycle: {e}")

                # Calculate sleep time
                cycle_duration = (datetime.now() - cycle_start).total_seconds()
                sleep_time = max(0, self.scraping_interval - cycle_duration)

                self.logger.info(f"Cycle #{self.cycle_count} completed in {cycle_duration:.1f}s. Sleeping {sleep_time:.1f}s...")

                await asyncio.sleep(sleep_time)

        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        finally:
            await self.shutdown()

    async def orchestrate_scraping_cycle(self):
        """Execute a complete scraping cycle with parallel agent execution"""
        tasks = []

        # Phase 1: Parallel data collection
        self.logger.info("Phase 1: Parallel data collection")

        # News scraping tasks
        for agent_id, agent in self.agents.items():
            if 'news-scraper' in agent_id:
                task = {
                    'id': f'fetch-news-{self.cycle_count}',
                    'type': 'fetch_articles',
                    'timeout': 120,
                    'agent_type': 'news_scraper'
                }
                tasks.append(self._execute_agent_task(agent, task))

        # Twitter monitoring tasks
        for agent_id, agent in self.agents.items():
            if 'twitter-monitor' in agent_id:
                task = {
                    'id': f'fetch-tweets-{self.cycle_count}',
                    'type': 'fetch_tweets',
                    'timeout': 60,
                    'agent_type': 'twitter_monitor'
                }
                tasks.append(self._execute_agent_task(agent, task))

        # Execute collection tasks in parallel
        collection_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        all_articles = []
        all_tweets = []

        for result in collection_results:
            if isinstance(result, Exception):
                self.logger.error(f"Collection task failed: {result}")
                continue

            if result.get('success'):
                task_result = result.get('result', {})
                if 'articles' in task_result:
                    all_articles.extend(task_result['articles'])
                if 'tweets' in task_result:
                    all_tweets.extend(task_result['tweets'])

        self.logger.info(f"Collected {len(all_articles)} articles and {len(all_tweets)} tweets")

        # Store in shared memory
        await self.memory_coordinator.store_shared_data('latest_cycle', {
            'cycle': self.cycle_count,
            'articles_count': len(all_articles),
            'tweets_count': len(all_tweets),
            'timestamp': datetime.now().isoformat()
        })

        # Phase 2: Parallel analysis and quality control
        self.logger.info("Phase 2: Parallel analysis and quality control")

        analysis_tasks = []

        # Analyze articles
        if all_articles:
            analyzer_agent = next((a for id, a in self.agents.items() if 'keyword-analyzer' in id), None)
            if analyzer_agent:
                analysis_tasks.append(self._execute_agent_task(analyzer_agent, {
                    'id': f'analyze-articles-{self.cycle_count}',
                    'type': 'batch_analyze',
                    'items': all_articles
                }))

        # Analyze tweets
        if all_tweets:
            analyzer_agent = next((a for id, a in self.agents.items() if 'keyword-analyzer' in id), None)
            if analyzer_agent:
                analysis_tasks.append(self._execute_agent_task(analyzer_agent, {
                    'id': f'analyze-tweets-{self.cycle_count}',
                    'type': 'batch_analyze',
                    'items': all_tweets
                }))

        # Deduplicate articles
        if all_articles:
            quality_agent = next((a for id, a in self.agents.items() if 'data-quality' in id), None)
            if quality_agent:
                analysis_tasks.append(self._execute_agent_task(quality_agent, {
                    'id': f'dedup-articles-{self.cycle_count}',
                    'type': 'deduplicate',
                    'items': all_articles,
                    'strategy': 'url_and_content'
                }))

        # Execute analysis tasks in parallel
        analysis_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)

        # Process analysis results
        for result in analysis_results:
            if isinstance(result, Exception):
                self.logger.error(f"Analysis task failed: {result}")
                continue

            if result.get('success'):
                self.logger.info(f"Analysis task {result.get('task_id')} completed successfully")

    async def coordinate_agents(self):
        """Coordinate communication and state sharing between agents"""
        # Get coordination status
        status_result = await self.coordinator.execute_task({'type': 'get_status'})

        if status_result.get('success'):
            status = status_result.get('result', {})
            self.logger.info(f"Coordination status: {status.get('total_agents')} agents, "
                           f"{status.get('total_tasks_assigned')} tasks assigned")

            # Store in shared memory
            await self.memory_coordinator.store_shared_data('coordination_status', status)

    async def _execute_agent_task(self, agent, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task on a specific agent"""
        try:
            result = await agent.execute_task(task)
            return result
        except Exception as e:
            self.logger.error(f"Task execution failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            'orchestrator': {
                'running': self.running,
                'cycle_count': self.cycle_count,
                'uptime': 'N/A',  # Would need start time tracking
                'timestamp': datetime.now().isoformat()
            },
            'agents': {},
            'coordination': {},
            'memory': {}
        }

        # Get agent statuses
        for agent_id, agent in self.agents.items():
            status['agents'][agent_id] = agent.get_status()

        # Get coordination status
        if self.coordinator:
            coord_result = await self.coordinator.execute_task({'type': 'get_status'})
            if coord_result.get('success'):
                status['coordination'] = coord_result.get('result', {})

        # Get memory stats
        if self.memory_coordinator:
            status['memory'] = await self.memory_coordinator.get_stats()

        return status

    async def shutdown(self):
        """Graceful shutdown of all components"""
        if not self.running:
            return

        self.logger.info("Shutting down TGE Swarm Orchestrator...")
        self.running = False

        # Shutdown agents
        for agent_id, agent in self.agents.items():
            try:
                self.logger.info(f"Shutting down agent: {agent_id}")
                await agent.shutdown()
            except Exception as e:
                self.logger.error(f"Error shutting down agent {agent_id}: {e}")

        # Shutdown coordinator
        if self.coordinator:
            try:
                await self.coordinator.shutdown()
            except Exception as e:
                self.logger.error(f"Error shutting down coordinator: {e}")

        # Shutdown memory coordinator
        if self.memory_coordinator:
            try:
                await self.memory_coordinator.shutdown()
            except Exception as e:
                self.logger.error(f"Error shutting down memory coordinator: {e}")

        # Shutdown message queue
        if self.message_queue:
            try:
                await self.message_queue.shutdown()
            except Exception as e:
                self.logger.error(f"Error shutting down message queue: {e}")

        self.logger.info("TGE Swarm Orchestrator shutdown complete")


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='TGE Swarm Orchestrator')
    parser.add_argument('--config', default='config/tge_swarm.yaml',
                       help='Configuration file path')
    parser.add_argument('--status', action='store_true',
                       help='Get system status and exit')

    args = parser.parse_args()

    orchestrator = TGESwarmOrchestrator(args.config)

    if args.status:
        # Just get status
        if await orchestrator.initialize():
            status = await orchestrator.get_system_status()
            import json
            print(json.dumps(status, indent=2, default=str))
            await orchestrator.shutdown()
        else:
            print("Failed to initialize orchestrator")
            sys.exit(1)
    else:
        # Run the orchestrator
        await orchestrator.run()


if __name__ == '__main__':
    asyncio.run(main())
