"""
Test suite for swarm coordination integration.
Verifies backward compatibility and swarm functionality.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from swarm_integration import SwarmCoordinationHooks, get_swarm_hooks, initialize_swarm


class TestSwarmIntegrationBackwardCompatibility(unittest.TestCase):
    """Test that swarm integration maintains backward compatibility."""

    def test_disabled_by_default(self):
        """Test that swarm is disabled by default."""
        hooks = SwarmCoordinationHooks()
        self.assertFalse(hooks.enabled)

    def test_hooks_are_noops_when_disabled(self):
        """Test that all hooks are no-ops when swarm is disabled."""
        hooks = SwarmCoordinationHooks(enabled=False)

        # These should all complete without errors or side effects
        task_id = hooks.pre_task("test task")
        self.assertIsNotNone(task_id)

        hooks.post_task(task_id, status='completed')
        hooks.memory_store('test_key', {'data': 'test'}, ttl=60, shared=True)
        result = hooks.memory_retrieve('test_key', shared=True)
        self.assertIsNone(result)  # Should return None when disabled

        hooks.post_edit('test_file.py', operation='update')
        hooks.notify("test message", level='info')
        hooks.coordinate_rate_limit('twitter/search', {'remaining': 100})
        hooks.coordinate_deduplication('abc123', {'url': 'test.com'})

        is_dup = hooks.check_duplicate('abc123')
        self.assertFalse(is_dup)  # Should return False when disabled

    def test_can_enable_via_parameter(self):
        """Test that swarm can be enabled via parameter."""
        hooks = SwarmCoordinationHooks(enabled=True)
        self.assertTrue(hooks.enabled)

    def test_can_enable_via_env_var(self):
        """Test that swarm can be enabled via environment variable."""
        with patch.dict(os.environ, {'SWARM_ENABLED': 'true'}):
            hooks = SwarmCoordinationHooks()
            self.assertTrue(hooks.enabled)

    def test_global_hooks_singleton(self):
        """Test that get_swarm_hooks returns a singleton."""
        hooks1 = get_swarm_hooks()
        hooks2 = get_swarm_hooks()
        self.assertIs(hooks1, hooks2)

    def test_initialize_swarm(self):
        """Test swarm initialization."""
        hooks = initialize_swarm(enabled=True, session_id='test-session')
        self.assertTrue(hooks.enabled)
        self.assertEqual(hooks.session_id, 'test-session')


class TestSwarmCoordinationHooks(unittest.TestCase):
    """Test swarm coordination functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.hooks = SwarmCoordinationHooks(enabled=False)  # Disabled for unit tests

    def test_task_tracking(self):
        """Test task tracking functionality."""
        task_id = self.hooks.pre_task("test task")
        self.assertIn(task_id, self.hooks.active_tasks)
        self.assertEqual(self.hooks.active_tasks[task_id]['status'], 'in_progress')

        metrics = {'time': 10.5, 'count': 25}
        self.hooks.post_task(task_id, status='completed', metrics=metrics)
        self.assertNotIn(task_id, self.hooks.active_tasks)
        self.assertIn(task_id, self.hooks.task_metrics)

    def test_agent_identification(self):
        """Test agent identification."""
        self.assertIsNotNone(self.hooks.agent_id)
        self.assertIsNotNone(self.hooks.agent_role)
        self.assertIsNotNone(self.hooks.session_id)

    def test_memory_prefix(self):
        """Test memory namespace prefixes."""
        self.assertTrue(self.hooks.memory_prefix.startswith('swarm/'))
        self.assertEqual(self.hooks.shared_memory_prefix, 'swarm/shared')

    @patch('subprocess.run')
    def test_hook_execution_success(self, mock_run):
        """Test successful hook execution."""
        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

        hooks = SwarmCoordinationHooks(enabled=True)
        result = hooks._run_hook('test-hook', param1='value1')

        self.assertTrue(result)
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_hook_execution_failure(self, mock_run):
        """Test hook execution failure handling."""
        mock_run.return_value = Mock(returncode=1, stdout='', stderr='Error')

        hooks = SwarmCoordinationHooks(enabled=True)
        result = hooks._run_hook('test-hook', param1='value1')

        self.assertFalse(result)

    @patch('subprocess.run')
    def test_hook_timeout_handling(self, mock_run):
        """Test hook timeout handling."""
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired('cmd', 30)

        hooks = SwarmCoordinationHooks(enabled=True)
        result = hooks._run_hook('test-hook')

        self.assertFalse(result)


class TestMainMonitorIntegration(unittest.TestCase):
    """Test swarm integration in main monitor."""

    @patch('swarm_integration.SwarmCoordinationHooks')
    def test_monitor_initializes_swarm(self, mock_hooks):
        """Test that monitor initializes swarm hooks."""
        mock_hooks.return_value = Mock(enabled=False)

        # Import here to avoid loading dependencies
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        from main_optimized import OptimizedCryptoTGEMonitor

        monitor = OptimizedCryptoTGEMonitor(swarm_enabled=False)
        self.assertIsNotNone(monitor.swarm_hooks)

    def test_backward_compatibility(self):
        """Test that monitor works without swarm enabled."""
        # This should not raise any errors
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

        # Verify imports work
        try:
            from main_optimized import OptimizedCryptoTGEMonitor
            from swarm_integration import SwarmCoordinationHooks
        except ImportError as e:
            self.fail(f"Import failed: {str(e)}")


class TestConfigurationValidation(unittest.TestCase):
    """Test configuration validation."""

    def test_config_has_swarm_settings(self):
        """Test that config.py has swarm settings."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

        try:
            from config import SWARM_CONFIG, SWARM_AGENTS
            self.assertIsNotNone(SWARM_CONFIG)
            self.assertIsNotNone(SWARM_AGENTS)
            self.assertIn('enabled', SWARM_CONFIG)
            self.assertIn('agent_id', SWARM_CONFIG)
        except ImportError as e:
            self.fail(f"Config import failed: {str(e)}")

    def test_swarm_agents_definition(self):
        """Test swarm agents are properly defined."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

        from config import SWARM_AGENTS

        expected_roles = [
            'scraping-efficiency-specialist',
            'tge-keyword-precision-specialist',
            'api-reliability-optimizer'
        ]

        for role in expected_roles:
            self.assertIn(role, SWARM_AGENTS)
            self.assertIn('role', SWARM_AGENTS[role])
            self.assertIn('priority', SWARM_AGENTS[role])
            self.assertIn('focus', SWARM_AGENTS[role])


class TestEnvironmentTemplate(unittest.TestCase):
    """Test environment variable template."""

    def test_env_template_exists(self):
        """Test that .env.swarm.template exists."""
        template_path = os.path.join(
            os.path.dirname(__file__), '..', 'config', '.env.swarm.template'
        )
        self.assertTrue(os.path.exists(template_path), f"Template not found: {template_path}")

    def test_env_template_content(self):
        """Test that template contains required variables."""
        template_path = os.path.join(
            os.path.dirname(__file__), '..', 'config', '.env.swarm.template'
        )

        with open(template_path, 'r') as f:
            content = f.read()

        required_vars = [
            'SWARM_ENABLED',
            'SWARM_AGENT_ID',
            'SWARM_AGENT_ROLE',
            'SWARM_COORDINATION_ENABLED',
            'SWARM_MEMORY_ENABLED',
            'SWARM_RATE_LIMIT_COORD',
            'SWARM_DEDUP_COORD'
        ]

        for var in required_vars:
            self.assertIn(var, content, f"Missing variable: {var}")


class TestDocumentation(unittest.TestCase):
    """Test documentation completeness."""

    def test_swarm_integration_doc_exists(self):
        """Test that SWARM_INTEGRATION.md exists."""
        doc_path = os.path.join(
            os.path.dirname(__file__), '..', 'docs', 'SWARM_INTEGRATION.md'
        )
        self.assertTrue(os.path.exists(doc_path), f"Documentation not found: {doc_path}")

    def test_swarm_integration_doc_content(self):
        """Test that documentation covers key topics."""
        doc_path = os.path.join(
            os.path.dirname(__file__), '..', 'docs', 'SWARM_INTEGRATION.md'
        )

        with open(doc_path, 'r') as f:
            content = f.read()

        required_topics = [
            'Overview',
            'Architecture',
            'Features',
            'Configuration',
            'Integration Points',
            'Multi-Agent Deployment',
            'Backward Compatibility',
            'Troubleshooting'
        ]

        for topic in required_topics:
            self.assertIn(topic, content, f"Missing documentation topic: {topic}")


def run_tests():
    """Run all tests and report results."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSwarmIntegrationBackwardCompatibility))
    suite.addTests(loader.loadTestsFromTestCase(TestSwarmCoordinationHooks))
    suite.addTests(loader.loadTestsFromTestCase(TestMainMonitorIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigurationValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestEnvironmentTemplate))
    suite.addTests(loader.loadTestsFromTestCase(TestDocumentation))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print("SWARM INTEGRATION TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 70)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
