"""
TGE Swarm Agents Package
Provides specialized agents for TGE detection and monitoring
"""

from .base_agent import BaseAgent
from .news_scraper_agent import NewsScraperAgent
from .twitter_monitor_agent import TwitterMonitorAgent
from .keyword_analyzer_agent import KeywordAnalyzerAgent
from .data_quality_agent import DataQualityAgent
from .coordinator_agent import CoordinatorAgent

__all__ = [
    'BaseAgent',
    'NewsScraperAgent',
    'TwitterMonitorAgent',
    'KeywordAnalyzerAgent',
    'DataQualityAgent',
    'CoordinatorAgent'
]
