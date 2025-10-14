#!/usr/bin/env python3
"""
Unit Tests for Coordination Service
Tests agent coordination, resource management, and cross-pollination
"""

import asyncio
import pytest
import uuid
import tempfile
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from backend.coordination_service import (
    CoordinationService, CoordinationEvent, CoordinationEventType,
    SharedResource, ResourceType, AgentContext
)
from backend.message_queue import MessageQueue, SwarmMessage, MessageType, Priority
from swarm_memory_coordinator import SwarmMemoryCoordinator


@pytest.mark.unit
@pytest.mark.redis
class TestCoordinationService:
    """Test coordination service functionality"""

    async def test_coordination_service_initialization(self, memory_coordinator, message_queue):
        """Test coordination service initialization"""
        service = CoordinationService(
            memory_coordinator, message_queue,
            redis_url="redis://localhost:6379/15"
        )

        assert service.memory_coordinator == memory_coordinator
        assert service.message_queue == message_queue
        assert service.active_agents == {}
        assert service.shared_resources == {}
        assert service.running is False

    async def test_initialize_coordination_service(self, coordination_service):
        """Test full initialization with shared resources"""
        assert coordination_service.running is True
        assert len(coordination_service.shared_resources) > 0

        # Check that TGE-specific resources are initialized
        assert 'tge-config' in coordination_service.shared_resources
        assert 'news-scraper' in coordination_service.shared_resources
        assert 'twitter-api' in coordination_service.shared_resources

    async def test_register_agent(self, coordination_service):
        """Test agent registration"""
        agent_id = "test-agent-1"
        agent_type = "scraping-efficiency"
        capabilities = ["web-scraping", "api-optimization"]
        specializations = ["news-scraping", "twitter-monitoring"]

        success = await coordination_service.register_agent(
            agent_id, agent_type, capabilities, specializations
        )

        assert success is True
        assert agent_id in coordination_service.active_agents

        agent_context = coordination_service.active_agents[agent_id]
        assert agent_context.agent_id == agent_id
        assert agent_context.agent_type == agent_type
        assert agent_context.capabilities == capabilities
        assert agent_context.specializations == specializations

    async def test_deregister_agent(self, coordination_service):
        """Test agent deregistration"""
        agent_id = "test-agent-1"

        # Register first
        await coordination_service.register_agent(
            agent_id, "scraping-efficiency", ["web-scraping"], ["news-scraping"]
        )

        assert agent_id in coordination_service.active_agents

        # Deregister
        success = await coordination_service.deregister_agent(agent_id)

        assert success is True
        assert agent_id not in coordination_service.active_agents

    async def test_deregister_nonexistent_agent(self, coordination_service):
        """Test deregistering non-existent agent"""
        success = await coordination_service.deregister_agent("nonexistent-agent")
        assert success is False

    async def test_request_resource_access_read(self, coordination_service):
        """Test requesting read access to shared resource"""
        agent_id = "test-agent-1"

        # Register agent first
        await coordination_service.register_agent(
            agent_id, "scraping-efficiency", ["web-scraping"], ["news-scraping"]
        )

        # Request read access
        success = await coordination_service.request_resource_access(
            agent_id, "tge-config", access_type="read"
        )

        assert success is True

        # Resource should not be locked for read access
        resource = coordination_service.shared_resources["tge-config"]
        assert resource.locked_by is None

    async def test_request_resource_access_write(self, coordination_service):
        """Test requesting write access to shared resource"""
        agent_id = "test-agent-1"

        # Register agent first
        await coordination_service.register_agent(
            agent_id, "scraping-efficiency", ["web-scraping"], ["news-scraping"]
        )

        # Request write access
        success = await coordination_service.request_resource_access(
            agent_id, "tge-config", access_type="write"
        )

        assert success is True

        # Resource should be locked
        resource = coordination_service.shared_resources["tge-config"]
        assert resource.locked_by == agent_id
        assert resource.locked_at is not None

    async def test_request_resource_access_conflict(self, coordination_service):
        """Test resource access conflict when resource is locked"""
        agent1_id = "test-agent-1"
        agent2_id = "test-agent-2"

        # Register agents
        await coordination_service.register_agent(
            agent1_id, "scraping-efficiency", ["web-scraping"], ["news-scraping"]
        )
        await coordination_service.register_agent(
            agent2_id, "keyword-precision", ["nlp"], ["keyword-matching"]
        )

        # Agent 1 gets write access
        success1 = await coordination_service.request_resource_access(
            agent1_id, "tge-config", access_type="write"
        )
        assert success1 is True

        # Agent 2 tries to get write access (should fail)
        success2 = await coordination_service.request_resource_access(
            agent2_id, "tge-config", access_type="write"
        )
        assert success2 is False

    async def test_release_resource_access(self, coordination_service):
        """Test releasing resource access"""
        agent_id = "test-agent-1"

        # Register agent and get write access
        await coordination_service.register_agent(
            agent_id, "scraping-efficiency", ["web-scraping"], ["news-scraping"]
        )
        await coordination_service.request_resource_access(
            agent_id, "tge-config", access_type="write"
        )

        # Verify locked
        resource = coordination_service.shared_resources["tge-config"]
        assert resource.locked_by == agent_id

        # Release
        success = await coordination_service.release_resource_access(agent_id, "tge-config")

        assert success is True
        assert resource.locked_by is None
        assert resource.locked_at is None

    async def test_release_resource_not_owned(self, coordination_service):
        """Test releasing resource not owned by agent"""
        agent1_id = "test-agent-1"
        agent2_id = "test-agent-2"

        # Register agents
        await coordination_service.register_agent(
            agent1_id, "scraping-efficiency", ["web-scraping"], ["news-scraping"]
        )
        await coordination_service.register_agent(
            agent2_id, "keyword-precision", ["nlp"], ["keyword-matching"]
        )

        # Agent 1 gets write access
        await coordination_service.request_resource_access(
            agent1_id, "tge-config", access_type="write"
        )

        # Agent 2 tries to release (should fail)
        success = await coordination_service.release_resource_access(agent2_id, "tge-config")
        assert success is False

    async def test_coordinate_optimization(self, coordination_service):
        """Test optimization coordination across agents"""
        requesting_agent = "test-agent-1"
        other_agent = "test-agent-2"

        # Register agents with complementary capabilities
        await coordination_service.register_agent(
            requesting_agent, "scraping-efficiency",
            ["web-scraping", "api-optimization"],
            ["news-scraping"]
        )
        await coordination_service.register_agent(
            other_agent, "performance-optimizer",
            ["performance-tuning", "profiling"],
            ["scraping-performance"]
        )

        # Coordinate optimization
        coordination_id = await coordination_service.coordinate_optimization(
            requesting_agent=requesting_agent,
            optimization_type="performance-optimization",
            target_resources=["news-scraper"],
            parameters={"threshold": 0.8}
        )

        assert coordination_id != ""
        assert coordination_service.coordination_metrics['optimizations_coordinated'] >= 1

    async def test_report_task_completion(self, coordination_service):
        """Test reporting task completion"""
        agent_id = "test-agent-1"
        task_id = str(uuid.uuid4())

        # Register agent
        await coordination_service.register_agent(
            agent_id, "scraping-efficiency", ["web-scraping"], ["news-scraping"]
        )

        results = {
            'execution_time': 45.2,
            'success_rate': 0.95,
            'optimizations_found': []
        }

        await coordination_service.report_task_completion(
            agent_id, task_id, results
        )

        # Check agent context updated
        agent_context = coordination_service.active_agents[agent_id]
        assert agent_context.current_task is None
        assert 'avg_execution_time' in agent_context.performance_metrics

    async def test_detect_conflicts_resource(self, coordination_service):
        """Test conflict detection for resource conflicts"""
        agent1_id = "test-agent-1"
        agent2_id = "test-agent-2"

        # Register agents
        await coordination_service.register_agent(
            agent1_id, "scraping-efficiency", ["web-scraping"], ["news-scraping"]
        )
        await coordination_service.register_agent(
            agent2_id, "keyword-precision", ["nlp"], ["keyword-matching"]
        )

        # Agent 1 accesses resource
        await coordination_service.request_resource_access(
            agent1_id, "tge-config", access_type="write"
        )

        # Agent 2 proposes changes to same resource
        proposed_changes = [
            {
                'target_resource': 'tge-config',
                'type': 'code_optimization',
                'description': 'Optimize configuration'
            }
        ]

        conflicts = await coordination_service.detect_conflicts(agent2_id, proposed_changes)

        assert len(conflicts) > 0
        assert conflicts[0]['type'] == 'resource_conflict'
        assert agent1_id in conflicts[0]['conflicting_agents']

    async def test_get_coordination_status(self, coordination_service):
        """Test getting coordination status"""
        # Register some agents
        await coordination_service.register_agent(
            "agent-1", "scraping-efficiency", ["web-scraping"], ["news-scraping"]
        )
        await coordination_service.register_agent(
            "agent-2", "keyword-precision", ["nlp"], ["keyword-matching"]
        )

        status = await coordination_service.get_coordination_status()

        assert 'timestamp' in status
        assert 'active_agents' in status
        assert status['active_agents'] == 2
        assert 'shared_resources' in status
        assert 'metrics' in status
        assert 'resource_status' in status

    async def test_resource_lock_expiration(self, coordination_service):
        """Test automatic expiration of resource locks"""
        agent_id = "test-agent-1"

        # Register agent and get write access
        await coordination_service.register_agent(
            agent_id, "scraping-efficiency", ["web-scraping"], ["news-scraping"]
        )
        await coordination_service.request_resource_access(
            agent_id, "tge-config", access_type="write"
        )

        resource = coordination_service.shared_resources["tge-config"]

        # Manually set lock time to expired
        resource.locked_at = datetime.now() - timedelta(seconds=coordination_service.resource_lock_timeout + 1)

        # Another agent should now be able to get access
        agent2_id = "test-agent-2"
        await coordination_service.register_agent(
            agent2_id, "keyword-precision", ["nlp"], ["keyword-matching"]
        )

        success = await coordination_service.request_resource_access(
            agent2_id, "tge-config", access_type="write"
        )

        assert success is True
        assert resource.locked_by == agent2_id

    async def test_coordination_metrics_tracking(self, coordination_service):
        """Test coordination metrics are tracked correctly"""
        initial_events = coordination_service.coordination_metrics['events_processed']

        # Perform some coordinated actions
        agent_id = "test-agent-1"
        await coordination_service.register_agent(
            agent_id, "scraping-efficiency", ["web-scraping"], ["news-scraping"]
        )

        # Check metrics updated
        assert coordination_service.coordination_metrics['events_processed'] > initial_events

    async def test_agent_deregistration_releases_resources(self, coordination_service):
        """Test that deregistering agent releases all its resources"""
        agent_id = "test-agent-1"

        # Register agent and lock resources
        await coordination_service.register_agent(
            agent_id, "scraping-efficiency", ["web-scraping"], ["news-scraping"]
        )
        await coordination_service.request_resource_access(
            agent_id, "tge-config", access_type="write"
        )
        await coordination_service.request_resource_access(
            agent_id, "news-scraper", access_type="write"
        )

        # Verify resources are locked
        assert coordination_service.shared_resources["tge-config"].locked_by == agent_id
        assert coordination_service.shared_resources["news-scraper"].locked_by == agent_id

        # Deregister agent
        await coordination_service.deregister_agent(agent_id)

        # Verify resources are released
        assert coordination_service.shared_resources["tge-config"].locked_by is None
        assert coordination_service.shared_resources["news-scraper"].locked_by is None

    async def test_access_log_tracking(self, coordination_service):
        """Test resource access logging"""
        agent_id = "test-agent-1"

        # Register agent
        await coordination_service.register_agent(
            agent_id, "scraping-efficiency", ["web-scraping"], ["news-scraping"]
        )

        # Access resource multiple times
        for _ in range(3):
            await coordination_service.request_resource_access(
                agent_id, "tge-config", access_type="read"
            )

        # Check access log
        resource = coordination_service.shared_resources["tge-config"]
        assert len(resource.access_log) == 3
        assert all(log['agent_id'] == agent_id for log in resource.access_log)
        assert all(log['granted'] is True for log in resource.access_log)

    async def test_capability_matching(self, coordination_service):
        """Test capability matching for optimization coordination"""
        agent1_id = "test-agent-1"
        agent2_id = "test-agent-2"

        # Register agents with different capabilities
        await coordination_service.register_agent(
            agent1_id, "scraping-efficiency",
            ["web-scraping", "api-optimization"],
            ["news-scraping"]
        )
        await coordination_service.register_agent(
            agent2_id, "keyword-precision",
            ["nlp", "text-analysis"],
            ["keyword-matching"]
        )

        # Test capability matching
        scraping_capabilities = coordination_service._match_capabilities_to_optimization(
            ["web-scraping", "api-optimization"],
            "scraping-efficiency"
        )

        assert len(scraping_capabilities) > 0
        assert "web-scraping" in scraping_capabilities or "api-optimization" in scraping_capabilities

    async def test_shutdown_gracefully(self, coordination_service):
        """Test graceful shutdown"""
        # Register some agents
        await coordination_service.register_agent(
            "agent-1", "scraping-efficiency", ["web-scraping"], ["news-scraping"]
        )

        assert coordination_service.running is True

        # Shutdown
        await coordination_service.shutdown()

        assert coordination_service.running is False


@pytest.mark.unit
class TestCoordinationEvent:
    """Test coordination event data structure"""

    def test_coordination_event_creation(self):
        """Test creating coordination event"""
        event = CoordinationEvent(
            id=str(uuid.uuid4()),
            type=CoordinationEventType.AGENT_JOINED,
            agent_id="test-agent",
            timestamp=datetime.now(),
            data={"agent_type": "scraping-efficiency"}
        )

        assert event.type == CoordinationEventType.AGENT_JOINED
        assert event.priority == Priority.MEDIUM  # Default
        assert event.expires_at is None  # Default

    def test_coordination_event_with_priority(self):
        """Test coordination event with custom priority"""
        event = CoordinationEvent(
            id=str(uuid.uuid4()),
            type=CoordinationEventType.CONFLICT_DETECTED,
            agent_id="test-agent",
            timestamp=datetime.now(),
            data={},
            priority=Priority.HIGH
        )

        assert event.priority == Priority.HIGH

    def test_coordination_event_with_expiration(self):
        """Test coordination event with expiration"""
        expires_at = datetime.now() + timedelta(hours=1)

        event = CoordinationEvent(
            id=str(uuid.uuid4()),
            type=CoordinationEventType.SYNC_REQUEST,
            agent_id="test-agent",
            timestamp=datetime.now(),
            data={},
            expires_at=expires_at
        )

        assert event.expires_at == expires_at


@pytest.mark.unit
class TestSharedResource:
    """Test shared resource data structure"""

    def test_shared_resource_creation(self):
        """Test creating shared resource"""
        resource = SharedResource(
            id="test-resource",
            type=ResourceType.FILE,
            name="test_file.py",
            owner=None,
            locked_by=None,
            locked_at=None,
            metadata={"path": "/path/to/file"},
            access_log=[]
        )

        assert resource.id == "test-resource"
        assert resource.type == ResourceType.FILE
        assert resource.locked_by is None
        assert len(resource.access_log) == 0

    def test_shared_resource_with_lock(self):
        """Test shared resource with lock"""
        locked_at = datetime.now()

        resource = SharedResource(
            id="test-resource",
            type=ResourceType.FILE,
            name="test_file.py",
            owner="test-agent",
            locked_by="test-agent",
            locked_at=locked_at,
            metadata={"path": "/path/to/file"},
            access_log=[]
        )

        assert resource.locked_by == "test-agent"
        assert resource.locked_at == locked_at


@pytest.mark.unit
class TestAgentContext:
    """Test agent context data structure"""

    def test_agent_context_creation(self):
        """Test creating agent context"""
        context = AgentContext(
            agent_id="test-agent",
            agent_type="scraping-efficiency",
            current_task=None,
            capabilities=["web-scraping", "api-optimization"],
            specializations=["news-scraping"],
            performance_metrics={},
            last_sync=datetime.now(),
            shared_insights=[],
            collaboration_history={}
        )

        assert context.agent_id == "test-agent"
        assert context.agent_type == "scraping-efficiency"
        assert len(context.capabilities) == 2
        assert context.current_task is None

    def test_agent_context_with_task(self):
        """Test agent context with current task"""
        task_id = str(uuid.uuid4())

        context = AgentContext(
            agent_id="test-agent",
            agent_type="scraping-efficiency",
            current_task=task_id,
            capabilities=["web-scraping"],
            specializations=["news-scraping"],
            performance_metrics={"avg_execution_time": 45.2},
            last_sync=datetime.now(),
            shared_insights=["insight1", "insight2"],
            collaboration_history={"other-agent": ["task1", "task2"]}
        )

        assert context.current_task == task_id
        assert len(context.shared_insights) == 2
        assert "other-agent" in context.collaboration_history
