"""
TGE Swarm Agent Implementations
Specialized agents for Token Generation Event monitoring and detection
"""

from .base_agent import TGEAgent, AgentCapability, AgentStatus
from .scraping_specialist import ScrapingEfficiencySpecialist
from .keyword_specialist import KeywordPrecisionSpecialist
from .api_specialist import APIReliabilityOptimizer

__all__ = [
    'TGEAgent',
    'AgentCapability',
    'AgentStatus',
    'ScrapingEfficiencySpecialist',
    'KeywordPrecisionSpecialist',
    'APIReliabilityOptimizer'
]
