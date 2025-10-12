"""
Pytest configuration for unit tests
Sets up mocking and test environment
"""

import sys
import os
from unittest.mock import MagicMock

# Mock external dependencies before any imports
sys.modules['redis'] = MagicMock()
sys.modules['psycopg2'] = MagicMock()

# Set SQLite for testing
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['REDIS_URL'] = 'redis://localhost:6379/0'
