"""
Swarm Configuration Manager
Handles loading and validating TGE swarm configuration
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any


class SwarmConfigManager:
    """
    Manager for TGE swarm configuration
    """

    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.logger = logging.getLogger('SwarmConfig')

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            self.logger.warning(f"Config file not found: {self.config_path}. Using defaults.")
            return self._default_config()

        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)

            self.logger.info(f"Loaded configuration from {self.config_path}")
            return self._merge_with_defaults(config)

        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Default TGE swarm configuration"""
        return {
            'cluster_name': 'tge-swarm',
            'log_level': 'INFO',
            'log_file': 'logs/orchestrator.log',
            'scraping_interval': 300,  # 5 minutes

            # Redis configuration
            'redis_urls': ['localhost:6379'],

            # Memory configuration
            'memory_path': './tge-memory',

            # Agent configuration
            'agents': {
                'news_scraper': {
                    'count': 2,
                    'enable_hooks': True,
                    'timeout': 120
                },
                'twitter_monitor': {
                    'count': 1,
                    'enable_hooks': True,
                    'timeout': 60
                },
                'keyword_analyzer': {
                    'count': 2,
                    'enable_hooks': True,
                    'similarity_threshold': 0.85
                },
                'data_quality': {
                    'count': 1,
                    'enable_hooks': True,
                    'similarity_threshold': 0.85,
                    'min_content_length': 100,
                    'min_confidence': 0.3
                }
            },

            # Coordinator configuration
            'coordinator': {
                'max_workload_per_agent': 5,
                'enable_hooks': True
            },

            # TGE detection configuration
            'companies': [
                {
                    'name': 'Example Project',
                    'aliases': ['ExampleProj', 'EXPL'],
                    'tokens': ['EXPL'],
                    'priority': 'HIGH'
                }
            ],

            'keywords': [
                'token generation event', 'tge', 'airdrop', 'token launch',
                'mainnet launch', 'listing', 'claim tokens', 'token distribution'
            ],

            'news_sources': [
                'https://cointelegraph.com/rss',
                'https://cryptoslate.com/feed/',
                'https://decrypt.co/feed'
            ],

            # Twitter configuration
            'twitter_bearer_token': None,  # Set via environment variable
        }

    def _merge_with_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge loaded config with defaults"""
        defaults = self._default_config()

        def deep_merge(default: Dict, override: Dict) -> Dict:
            """Recursively merge dictionaries"""
            result = default.copy()

            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value

            return result

        return deep_merge(defaults, config)

    def save_config(self, config: Dict[str, Any]):
        """Save configuration to file"""
        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)

            self.logger.info(f"Saved configuration to {self.config_path}")

        except Exception as e:
            self.logger.error(f"Error saving config: {e}")

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration"""
        required_fields = ['cluster_name', 'agents', 'companies', 'keywords']

        for field in required_fields:
            if field not in config:
                self.logger.error(f"Missing required field: {field}")
                return False

        # Validate agent counts
        for agent_type, agent_config in config.get('agents', {}).items():
            if 'count' not in agent_config:
                self.logger.error(f"Missing 'count' for agent type: {agent_type}")
                return False

            if agent_config['count'] < 0:
                self.logger.error(f"Invalid agent count for {agent_type}: {agent_config['count']}")
                return False

        self.logger.info("Configuration validated successfully")
        return True
