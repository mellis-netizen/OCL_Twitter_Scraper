"""
Twitter Monitor Agent
Wraps OptimizedTwitterMonitor with swarm coordination capabilities
"""

import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.twitter_monitor_optimized import OptimizedTwitterMonitor
from src.agents.base_agent import BaseAgent


class TwitterMonitorAgent(BaseAgent):
    """
    Agent that wraps Twitter monitoring functionality with swarm coordination
    """

    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, "twitter_monitor", config)

        self.monitor = None
        self.bearer_token = config.get('bearer_token')
        self.companies = config.get('companies', [])
        self.keywords = config.get('keywords', [])

    async def _do_initialize(self):
        """Initialize the Twitter monitor"""
        self.logger.info("Initializing OptimizedTwitterMonitor")

        if not self.bearer_token:
            raise ValueError("Twitter bearer token is required")

        self.monitor = OptimizedTwitterMonitor(
            bearer_token=self.bearer_token,
            companies=self.companies,
            keywords=self.keywords
        )

        # Store initialization in memory
        await self.store_memory('initialized', {
            'timestamp': datetime.now().isoformat(),
            'companies_count': len(self.companies)
        }, 'initialization')

    async def _execute_task_impl(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Twitter monitoring task"""
        task_type = task.get('type', 'fetch_tweets')

        if task_type == 'fetch_tweets':
            return await self._fetch_tweets(task)
        elif task_type == 'search_tge':
            return await self._search_tge_tweets(task)
        elif task_type == 'analyze_relevance':
            return await self._analyze_tweet_relevance(task)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def _fetch_tweets(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch tweets from monitored accounts"""
        timeout = task.get('timeout', 60)

        self.logger.info(f"Fetching tweets with timeout={timeout}s")

        # Fetch tweets using the optimized monitor
        tweets = self.monitor.fetch_all_tweets(timeout=timeout)

        # Analyze relevance for each tweet
        analyzed_tweets = []
        for tweet in tweets:
            is_relevant, confidence, info = self.monitor.analyze_tweet_relevance(tweet)
            if is_relevant:
                tweet['relevance'] = {
                    'confidence': confidence,
                    'info': info
                }
                analyzed_tweets.append(tweet)

        # Store results in memory
        await self.store_memory('latest_tweets', {
            'timestamp': datetime.now().isoformat(),
            'count': len(analyzed_tweets),
            'tweets': analyzed_tweets[:10]  # Store top 10
        }, 'results')

        # Update metrics
        await self.update_metrics({
            'tweets_found': len(tweets),
            'relevant_tweets': len(analyzed_tweets),
            'last_fetch': datetime.now().isoformat()
        })

        return {
            'tweets': analyzed_tweets,
            'total_fetched': len(tweets),
            'relevant_count': len(analyzed_tweets),
            'timestamp': datetime.now().isoformat()
        }

    async def _search_tge_tweets(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Search for TGE-specific tweets"""
        self.logger.info("Searching for TGE tweets")

        tweets = self.monitor.search_tge_tweets()

        # Store in memory
        await self.store_memory('tge_tweets', {
            'timestamp': datetime.now().isoformat(),
            'count': len(tweets),
            'tweets': tweets
        }, 'results')

        return {
            'tweets': tweets,
            'count': len(tweets)
        }

    async def _analyze_tweet_relevance(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze relevance of specific tweets"""
        tweets = task.get('tweets', [])

        results = []
        for tweet in tweets:
            is_relevant, confidence, info = self.monitor.analyze_tweet_relevance(tweet)
            results.append({
                'tweet_id': tweet.get('id'),
                'is_relevant': is_relevant,
                'confidence': confidence,
                'info': info
            })

        return {
            'analysis_results': results,
            'count': len(results)
        }

    async def _do_shutdown(self):
        """Clean up monitor resources"""
        self.logger.info("Shutting down Twitter monitor")

        if self.monitor:
            # Save state
            self.monitor.save_state()
            self.monitor.save_cache()
