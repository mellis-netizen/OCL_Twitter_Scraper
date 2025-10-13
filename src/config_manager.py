"""
Production-Grade Configuration Management
Provides environment-based configuration, feature flags, and secrets management
"""

import os
import json
import logging
from typing import Any, Dict, Optional, List, Type, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import re

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Application environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class ConfigValue:
    """Configuration value with metadata"""
    value: Any
    source: str  # env, file, default
    is_secret: bool = False
    description: str = ""


class ConfigurationError(Exception):
    """Raised when configuration is invalid"""
    pass


class FeatureFlag:
    """Feature flag with conditions"""

    def __init__(
        self,
        name: str,
        enabled: bool = False,
        rollout_percentage: int = 100,
        allowed_environments: Optional[List[Environment]] = None
    ):
        self.name = name
        self.enabled = enabled
        self.rollout_percentage = rollout_percentage
        self.allowed_environments = allowed_environments or [
            Environment.DEVELOPMENT,
            Environment.STAGING,
            Environment.PRODUCTION
        ]

    def is_enabled(self, environment: Environment, user_id: Optional[str] = None) -> bool:
        """Check if feature is enabled"""
        if not self.enabled:
            return False

        if environment not in self.allowed_environments:
            return False

        if self.rollout_percentage < 100:
            # Simple hash-based rollout
            if user_id:
                hash_value = hash(f"{self.name}:{user_id}") % 100
                return hash_value < self.rollout_percentage
            else:
                # No user_id, use percentage of time
                import random
                return random.random() * 100 < self.rollout_percentage

        return True


class ConfigManager:
    """Manages application configuration"""

    def __init__(self, env: Optional[Environment] = None):
        # Determine environment
        if env is None:
            env_str = os.getenv('APP_ENV', 'development').lower()
            try:
                self.env = Environment(env_str)
            except ValueError:
                logger.warning(f"Invalid environment '{env_str}', defaulting to development")
                self.env = Environment.DEVELOPMENT
        else:
            self.env = env

        self.config: Dict[str, ConfigValue] = {}
        self.feature_flags: Dict[str, FeatureFlag] = {}
        self.required_keys: List[str] = []

        logger.info(f"Configuration manager initialized for environment: {self.env.value}")

    def set(
        self,
        key: str,
        value: Any,
        source: str = "manual",
        is_secret: bool = False,
        description: str = ""
    ):
        """Set configuration value"""
        self.config[key] = ConfigValue(
            value=value,
            source=source,
            is_secret=is_secret,
            description=description
        )

    def get(
        self,
        key: str,
        default: Any = None,
        required: bool = False,
        value_type: Optional[Type] = None
    ) -> Any:
        """
        Get configuration value

        Args:
            key: Configuration key
            default: Default value if not found
            required: Raise error if not found
            value_type: Expected type for validation

        Returns:
            Configuration value

        Raises:
            ConfigurationError: If required key is missing or type is wrong
        """
        if key in self.config:
            value = self.config[key].value

            # Type validation
            if value_type is not None and value is not None:
                if not isinstance(value, value_type):
                    try:
                        value = value_type(value)
                    except (ValueError, TypeError):
                        raise ConfigurationError(
                            f"Config key '{key}' has wrong type: "
                            f"expected {value_type.__name__}, got {type(value).__name__}"
                        )

            return value

        if required:
            raise ConfigurationError(f"Required configuration key '{key}' not found")

        return default

    def get_int(self, key: str, default: int = 0, required: bool = False) -> int:
        """Get integer configuration value"""
        return self.get(key, default, required, int)

    def get_float(self, key: str, default: float = 0.0, required: bool = False) -> float:
        """Get float configuration value"""
        return self.get(key, default, required, float)

    def get_bool(self, key: str, default: bool = False, required: bool = False) -> bool:
        """Get boolean configuration value"""
        value = self.get(key, default, required)

        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')

        return bool(value)

    def get_string(self, key: str, default: str = "", required: bool = False) -> str:
        """Get string configuration value"""
        return self.get(key, default, required, str)

    def get_list(
        self,
        key: str,
        default: Optional[List] = None,
        required: bool = False,
        separator: str = ","
    ) -> List[str]:
        """Get list configuration value"""
        value = self.get(key, default, required)

        if value is None:
            return default or []

        if isinstance(value, list):
            return value

        if isinstance(value, str):
            return [item.strip() for item in value.split(separator) if item.strip()]

        return [str(value)]

    def load_from_env(self, prefix: str = "", required_keys: Optional[List[str]] = None):
        """
        Load configuration from environment variables

        Args:
            prefix: Prefix for environment variables (e.g., "APP_")
            required_keys: List of required keys
        """
        if required_keys:
            self.required_keys.extend(required_keys)

        for key, value in os.environ.items():
            if prefix and not key.startswith(prefix):
                continue

            # Remove prefix
            config_key = key[len(prefix):] if prefix else key

            # Convert to lowercase with underscores
            config_key = config_key.lower()

            # Detect if value might be secret
            is_secret = any(
                secret_indicator in config_key.lower()
                for secret_indicator in ['password', 'secret', 'key', 'token', 'api_key']
            )

            self.set(config_key, value, source="env", is_secret=is_secret)

        # Validate required keys
        missing_keys = [k for k in self.required_keys if k not in self.config]
        if missing_keys:
            raise ConfigurationError(f"Missing required configuration keys: {missing_keys}")

        logger.info(f"Loaded {len(self.config)} configuration values from environment")

    def load_from_file(self, filepath: str, file_format: str = "json"):
        """
        Load configuration from file

        Args:
            filepath: Path to configuration file
            file_format: File format (json, yaml, toml)
        """
        path = Path(filepath)

        if not path.exists():
            logger.warning(f"Configuration file not found: {filepath}")
            return

        try:
            with open(path, 'r') as f:
                if file_format == "json":
                    data = json.load(f)
                else:
                    raise ConfigurationError(f"Unsupported file format: {file_format}")

            # Load configuration
            for key, value in data.items():
                if key not in self.config:  # Don't override env vars
                    self.set(key, value, source="file")

            logger.info(f"Loaded configuration from {filepath}")

        except Exception as e:
            logger.error(f"Failed to load configuration from {filepath}: {str(e)}")
            raise ConfigurationError(f"Failed to load configuration file: {str(e)}")

    def register_feature_flag(self, flag: FeatureFlag):
        """Register a feature flag"""
        self.feature_flags[flag.name] = flag
        logger.info(f"Registered feature flag: {flag.name}")

    def is_feature_enabled(self, flag_name: str, user_id: Optional[str] = None) -> bool:
        """Check if feature flag is enabled"""
        if flag_name not in self.feature_flags:
            logger.warning(f"Unknown feature flag: {flag_name}")
            return False

        return self.feature_flags[flag_name].is_enabled(self.env, user_id)

    def get_all_config(self, include_secrets: bool = False) -> Dict[str, Any]:
        """
        Get all configuration values

        Args:
            include_secrets: Whether to include secret values

        Returns:
            Dictionary of configuration
        """
        result = {}

        for key, config_value in self.config.items():
            if config_value.is_secret and not include_secrets:
                result[key] = "***REDACTED***"
            else:
                result[key] = config_value.value

        return result

    def validate(self, schema: Dict[str, Dict[str, Any]]):
        """
        Validate configuration against schema

        Args:
            schema: Configuration schema
                {
                    'key': {
                        'type': str,
                        'required': True,
                        'default': 'value',
                        'validator': lambda x: x > 0
                    }
                }

        Raises:
            ConfigurationError: If validation fails
        """
        errors = []

        for key, rules in schema.items():
            required = rules.get('required', False)
            value_type = rules.get('type')
            default = rules.get('default')
            validator = rules.get('validator')

            # Check if key exists
            if key not in self.config:
                if required:
                    errors.append(f"Required key '{key}' not found")
                elif default is not None:
                    self.set(key, default, source="default")
                continue

            value = self.config[key].value

            # Type check
            if value_type and not isinstance(value, value_type):
                errors.append(f"Key '{key}' has wrong type: expected {value_type.__name__}")

            # Custom validator
            if validator:
                try:
                    if not validator(value):
                        errors.append(f"Key '{key}' failed validation")
                except Exception as e:
                    errors.append(f"Key '{key}' validation error: {str(e)}")

        if errors:
            raise ConfigurationError(f"Configuration validation failed: {', '.join(errors)}")

    def export_to_file(self, filepath: str, include_secrets: bool = False):
        """Export configuration to file"""
        config_dict = self.get_all_config(include_secrets)

        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(config_dict, f, indent=2)
            logger.info(f"Exported configuration to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export configuration: {str(e)}")
            raise


class SecretsManager:
    """Manages sensitive configuration (passwords, API keys, etc.)"""

    def __init__(self):
        self.secrets: Dict[str, str] = {}

    def set_secret(self, key: str, value: str):
        """Set a secret value"""
        self.secrets[key] = value
        logger.info(f"Secret set: {key}")

    def get_secret(self, key: str, required: bool = True) -> Optional[str]:
        """Get a secret value"""
        if key not in self.secrets:
            if required:
                raise ConfigurationError(f"Required secret '{key}' not found")
            return None

        return self.secrets[key]

    def load_from_env(self, prefix: str = "SECRET_"):
        """Load secrets from environment variables"""
        for key, value in os.environ.items():
            if key.startswith(prefix):
                secret_key = key[len(prefix):].lower()
                self.set_secret(secret_key, value)

        logger.info(f"Loaded {len(self.secrets)} secrets from environment")

    def clear(self):
        """Clear all secrets"""
        self.secrets.clear()
        logger.info("All secrets cleared")


# Global instances
config_manager: Optional[ConfigManager] = None
secrets_manager = SecretsManager()


def initialize_config(env: Optional[Environment] = None) -> ConfigManager:
    """Initialize global configuration manager"""
    global config_manager
    config_manager = ConfigManager(env)
    return config_manager


def get_config() -> Optional[ConfigManager]:
    """Get global configuration manager"""
    return config_manager


def get_secrets() -> SecretsManager:
    """Get global secrets manager"""
    return secrets_manager
