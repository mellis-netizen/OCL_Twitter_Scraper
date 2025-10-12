"""
News Scraper Agent
Wraps OptimizedNewsScraper with swarm coordination capabilities
"""

import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.news_scraper_optimized import OptimizedNewsScraper
from src.agents.base_agent import BaseAgent


class NewsScraperAgent(BaseAgent):
    """
    Agent that wraps news scraping functionality with swarm coordination
    """

    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, "news_scraper", config)

        self.scraper = None
        self.companies = config.get('companies', [])
        self.keywords = config.get('keywords', [])
        self.news_sources = config.get('news_sources', [])

    async def _do_initialize(self):
        """Initialize the news scraper"""
        self.logger.info("Initializing OptimizedNewsScraper")

        self.scraper = OptimizedNewsScraper(
            companies=self.companies,
            keywords=self.keywords,
            news_sources=self.news_sources
        )

        # Store initialization in memory
        await self.store_memory('initialized', {
            'timestamp': datetime.now().isoformat(),
            'companies_count': len(self.companies),
            'sources_count': len(self.news_sources)
        }, 'initialization')

    async def _execute_task_impl(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute news scraping task"""
        task_type = task.get('type', 'fetch_articles')

        if task_type == 'fetch_articles':
            return await self._fetch_articles(task)
        elif task_type == 'analyze_feed_health':
            return await self._analyze_feed_health(task)
        elif task_type == 'prioritize_feeds':
            return await self._prioritize_feeds(task)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def _fetch_articles(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch and analyze articles from news sources"""
        timeout = task.get('timeout', 120)

        self.logger.info(f"Fetching articles with timeout={timeout}s")

        # Fetch articles using the optimized scraper
        articles = self.scraper.fetch_all_articles(timeout=timeout)

        # Store results in memory for other agents
        await self.store_memory('latest_articles', {
            'timestamp': datetime.now().isoformat(),
            'count': len(articles),
            'articles': articles[:10]  # Store top 10
        }, 'results')

        # Update metrics
        await self.update_metrics({
            'articles_found': len(articles),
            'last_fetch': datetime.now().isoformat()
        })

        return {
            'articles': articles,
            'count': len(articles),
            'timestamp': datetime.now().isoformat()
        }

    async def _analyze_feed_health(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze health of news feeds"""
        self.logger.info("Analyzing feed health")

        health_report = self.scraper.get_feed_health_report()

        # Store health report in memory
        await self.store_memory('feed_health', health_report, 'health')

        return health_report

    async def _prioritize_feeds(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Prioritize feeds based on performance"""
        self.logger.info("Prioritizing feeds")

        prioritized = self.scraper.prioritize_feeds()

        # Store prioritization in memory
        await self.store_memory('feed_priority', {
            'timestamp': datetime.now().isoformat(),
            'feeds': prioritized
        }, 'optimization')

        return {
            'prioritized_feeds': prioritized,
            'count': len(prioritized)
        }

    async def _do_shutdown(self):
        """Clean up scraper resources"""
        self.logger.info("Shutting down news scraper")

        if self.scraper:
            # Save state
            self.scraper.save_state()
            self.scraper.save_cache()
