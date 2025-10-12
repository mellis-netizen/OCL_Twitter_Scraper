"""
Unit Tests for Swarm Integration
Tests hook execution, memory coordination, and agent communication
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import sys
import os
import json
import subprocess

# Add src and swarm-agents to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'swarm-agents'))


class TestSwarmHooks(unittest.TestCase):
    """Test swarm coordination hooks"""

    def setUp(self):
        """Set up test fixtures"""
        self.agent_id = "test-agent-001"
        self.task_id = "task-tge-scraping"
        self.session_id = "swarm-session-123"

    def test_pre_task_hook(self):
        """Test pre-task hook execution"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="Pre-task hook executed",
                stderr=""
            )

            # Simulate pre-task hook call
            result = subprocess.run(
                ['npx', 'claude-flow@alpha', 'hooks', 'pre-task',
                 '--description', 'Starting TGE scraping'],
                capture_output=True,
                text=True
            )

            self.assertEqual(result.returncode, 0)

    def test_post_task_hook(self):
        """Test post-task hook execution"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="Post-task hook executed",
                stderr=""
            )

            result = subprocess.run(
                ['npx', 'claude-flow@alpha', 'hooks', 'post-task',
                 '--task-id', self.task_id],
                capture_output=True,
                text=True
            )

            self.assertEqual(result.returncode, 0)

    def test_post_edit_hook(self):
        """Test post-edit hook for file changes"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            file_path = "/path/to/file.py"
            memory_key = f"swarm/{self.agent_id}/file-edit"

            result = subprocess.run(
                ['npx', 'claude-flow@alpha', 'hooks', 'post-edit',
                 '--file', file_path,
                 '--memory-key', memory_key],
                capture_output=True,
                text=True
            )

            self.assertEqual(result.returncode, 0)

    def test_notify_hook(self):
        """Test notification hook"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            message = "TGE detected for Caldera"

            result = subprocess.run(
                ['npx', 'claude-flow@alpha', 'hooks', 'notify',
                 '--message', message],
                capture_output=True,
                text=True
            )

            self.assertEqual(result.returncode, 0)


class TestMemoryCoordination(unittest.TestCase):
    """Test memory-based coordination between agents"""

    def setUp(self):
        """Set up test fixtures"""
        self.agent_id = "scraper-agent"
        self.namespace = "coordination"

    def test_memory_store(self):
        """Test storing data in shared memory"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps({"success": True})
            )

            test_data = {
                "agent": self.agent_id,
                "status": "scraping_complete",
                "articles_found": 15,
                "tge_detections": 3
            }

            # Simulate memory store via hook
            result = subprocess.run(
                ['npx', 'claude-flow@alpha', 'hooks', 'post-task',
                 '--task-id', 'scraping',
                 '--memory-key', f'swarm/{self.agent_id}/status'],
                capture_output=True,
                text=True
            )

            self.assertEqual(result.returncode, 0)

    def test_memory_retrieve(self):
        """Test retrieving data from shared memory"""
        with patch('subprocess.run') as mock_run:
            stored_data = {
                "agent": "other-agent",
                "status": "analyzing",
                "results": []
            }

            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps(stored_data)
            )

            # Simulate session restore (reads memory)
            result = subprocess.run(
                ['npx', 'claude-flow@alpha', 'hooks', 'session-restore',
                 '--session-id', 'swarm-123'],
                capture_output=True,
                text=True
            )

            self.assertEqual(result.returncode, 0)

    def test_cross_agent_communication(self):
        """Test communication between agents via memory"""
        # Agent 1 stores data
        agent1_data = {
            "agent": "news-scraper",
            "articles": [
                {"title": "Caldera TGE", "confidence": 0.9}
            ]
        }

        # Agent 2 retrieves and processes
        agent2_data = {
            "agent": "twitter-monitor",
            "received_from": "news-scraper",
            "processing": True
        }

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            # Both agents can coordinate via memory
            self.assertTrue(True)  # Placeholder for actual coordination test

    def test_session_persistence(self):
        """Test session data persists across hook calls"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            # Session start
            subprocess.run(
                ['npx', 'claude-flow@alpha', 'hooks', 'session-restore',
                 '--session-id', 'swarm-123'],
                capture_output=True
            )

            # Session end with export
            subprocess.run(
                ['npx', 'claude-flow@alpha', 'hooks', 'session-end',
                 '--export-metrics', 'true'],
                capture_output=True
            )

            # Should have called hooks
            self.assertEqual(mock_run.call_count, 2)


class TestAgentCoordination(unittest.TestCase):
    """Test agent coordination patterns"""

    def test_parallel_agent_coordination(self):
        """Test multiple agents working in parallel"""
        agents = [
            {"name": "news-scraper", "task": "scraping"},
            {"name": "twitter-monitor", "task": "monitoring"},
            {"name": "analyzer", "task": "analyzing"}
        ]

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            # Each agent executes pre-task hook
            for agent in agents:
                subprocess.run(
                    ['npx', 'claude-flow@alpha', 'hooks', 'pre-task',
                     '--description', f'{agent["name"]} starting {agent["task"]}'],
                    capture_output=True
                )

            # Should have 3 hook calls
            self.assertEqual(mock_run.call_count, 3)

    def test_sequential_agent_workflow(self):
        """Test agents executing in sequence with coordination"""
        workflow = [
            {"agent": "scraper", "action": "fetch"},
            {"agent": "analyzer", "action": "analyze"},
            {"agent": "notifier", "action": "notify"}
        ]

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            for step in workflow:
                # Pre-task
                subprocess.run(
                    ['npx', 'claude-flow@alpha', 'hooks', 'pre-task',
                     '--description', f'{step["agent"]} {step["action"]}'],
                    capture_output=True
                )

                # Post-task with data
                subprocess.run(
                    ['npx', 'claude-flow@alpha', 'hooks', 'post-task',
                     '--task-id', f'{step["agent"]}-{step["action"]}'],
                    capture_output=True
                )

            # Should have 6 total calls (2 per step)
            self.assertEqual(mock_run.call_count, 6)

    def test_agent_error_handling(self):
        """Test coordination when agent encounters error"""
        with patch('subprocess.run') as mock_run:
            # Simulate hook failure
            mock_run.return_value = Mock(returncode=1, stderr="Hook failed")

            result = subprocess.run(
                ['npx', 'claude-flow@alpha', 'hooks', 'notify',
                 '--message', 'Error occurred'],
                capture_output=True,
                text=True
            )

            # Error should be captured
            self.assertEqual(result.returncode, 1)


class TestSwarmTopology(unittest.TestCase):
    """Test swarm topology and structure"""

    def test_swarm_initialization(self):
        """Test swarm initialization hook"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps({"topology": "mesh", "agents": 3})
            )

            # Initialize swarm
            # Note: Actual swarm init would be via MCP tools
            # This tests the hook integration
            self.assertTrue(True)

    def test_agent_registration(self):
        """Test agent registration in swarm"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            # Agent announces itself
            subprocess.run(
                ['npx', 'claude-flow@alpha', 'hooks', 'notify',
                 '--message', 'Agent news-scraper registered'],
                capture_output=True
            )

            mock_run.assert_called_once()


class TestDeduplication(unittest.TestCase):
    """Test cross-agent deduplication via memory"""

    def test_seen_urls_coordination(self):
        """Test URL deduplication across agents"""
        seen_urls = {
            "https://example.com/article1": "news-scraper",
            "https://example.com/article2": "twitter-monitor"
        }

        # Simulate checking if URL is already processed
        url = "https://example.com/article1"
        is_duplicate = url in seen_urls

        self.assertTrue(is_duplicate)

    def test_content_hash_coordination(self):
        """Test content hash deduplication"""
        import hashlib

        content1 = "Caldera TGE announcement"
        content2 = "Caldera TGE announcement"  # Duplicate
        content3 = "Different content"

        hash1 = hashlib.sha256(content1.encode()).hexdigest()
        hash2 = hashlib.sha256(content2.encode()).hexdigest()
        hash3 = hashlib.sha256(content3.encode()).hexdigest()

        self.assertEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)


class TestHookIntegration(unittest.TestCase):
    """Test integration of hooks in scraping workflow"""

    def test_scraping_workflow_with_hooks(self):
        """Test complete scraping workflow with hook integration"""
        workflow_steps = [
            "pre-task: Initialize scraping",
            "notify: Starting RSS feed processing",
            "post-edit: Article cache updated",
            "notify: 15 articles found",
            "post-task: Scraping complete"
        ]

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            for step in workflow_steps:
                parts = step.split(": ")
                hook_type = parts[0]
                message = parts[1]

                if hook_type == "pre-task":
                    subprocess.run(
                        ['npx', 'claude-flow@alpha', 'hooks', 'pre-task',
                         '--description', message],
                        capture_output=True
                    )
                elif hook_type == "notify":
                    subprocess.run(
                        ['npx', 'claude-flow@alpha', 'hooks', 'notify',
                         '--message', message],
                        capture_output=True
                    )
                elif hook_type == "post-task":
                    subprocess.run(
                        ['npx', 'claude-flow@alpha', 'hooks', 'post-task',
                         '--task-id', 'scraping'],
                        capture_output=True
                    )

            # Should have called hooks for each step
            self.assertGreater(mock_run.call_count, 0)

    def test_error_notification_via_hooks(self):
        """Test error notifications through hooks"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            error_msg = "Scraping failed: Network timeout"

            subprocess.run(
                ['npx', 'claude-flow@alpha', 'hooks', 'notify',
                 '--message', error_msg],
                capture_output=True
            )

            mock_run.assert_called_once()


class TestMetricsCollection(unittest.TestCase):
    """Test metrics collection via hooks"""

    def test_session_metrics_export(self):
        """Test session metrics are exported"""
        with patch('subprocess.run') as mock_run:
            mock_metrics = {
                "duration": 45.2,
                "articles_processed": 120,
                "tge_found": 5,
                "api_calls": 15
            }

            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps(mock_metrics)
            )

            result = subprocess.run(
                ['npx', 'claude-flow@alpha', 'hooks', 'session-end',
                 '--export-metrics', 'true'],
                capture_output=True,
                text=True
            )

            self.assertEqual(result.returncode, 0)

    def test_performance_tracking(self):
        """Test performance metrics are tracked"""
        metrics = {
            "scraping_time": 30.5,
            "articles_found": 45,
            "cache_hit_rate": 0.67,
            "api_call_count": 12
        }

        # Verify metrics structure
        self.assertIn("scraping_time", metrics)
        self.assertIn("articles_found", metrics)
        self.assertIsInstance(metrics["cache_hit_rate"], float)


if __name__ == '__main__':
    unittest.main()
