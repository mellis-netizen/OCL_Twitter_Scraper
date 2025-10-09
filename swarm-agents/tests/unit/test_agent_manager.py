#!/usr/bin/env python3
"""
Unit Tests for Agent Manager
Tests agent lifecycle, deployment, scaling, and health monitoring
"""

import asyncio
import pytest
import uuid
import tempfile
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call
import yaml

from backend.agent_manager import (
    AgentManager, AgentManagerAPI, AgentSpec, AgentInstance, AgentStatus, 
    AgentType, LoadBalancer
)
from backend.message_queue import TaskDefinition, Priority


@pytest.mark.unit
@pytest.mark.docker
class TestAgentManager:
    """Test agent manager functionality"""
    
    def test_agent_manager_initialization(self, agent_manager):
        """Test agent manager initialization"""
        assert agent_manager.agents == {}
        assert agent_manager.running is False
        assert len(agent_manager.agent_specs) > 0
        
        # Check default agent specs loaded
        assert 'scraping-efficiency-specialist' in agent_manager.agent_specs
        assert 'keyword-precision-specialist' in agent_manager.agent_specs
    
    def test_load_default_config(self):
        """Test loading default configuration"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("# empty config")
            config_file = f.name
        
        try:
            manager = AgentManager(config_file)
            config = manager._default_config()
            
            assert 'consul_host' in config
            assert 'max_agents_per_type' in config
            assert config['max_agents_per_type'] == 5
        finally:
            os.unlink(config_file)
    
    def test_load_custom_config(self):
        """Test loading custom configuration"""
        custom_config = {
            'consul_host': 'custom-host',
            'consul_port': 9500,
            'max_agents_per_type': 10,
            'health_check_interval': 60
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(custom_config, f)
            config_file = f.name
        
        try:
            manager = AgentManager(config_file)
            
            assert manager.config['consul_host'] == 'custom-host'
            assert manager.config['max_agents_per_type'] == 10
        finally:
            os.unlink(config_file)
    
    async def test_agent_manager_initialize_with_message_queue(self, agent_manager, message_queue):
        """Test agent manager initialization with message queue"""
        await agent_manager.initialize(message_queue)
        
        assert agent_manager.message_queue == message_queue
        assert agent_manager.running is True
    
    async def test_deploy_agent_success(self, agent_manager, mock_docker_client):
        """Test successful agent deployment"""
        spec_id = 'scraping-efficiency-specialist'
        
        # Mock message queue for initialization
        mock_mq = AsyncMock()
        await agent_manager.initialize(mock_mq)
        
        instances = await agent_manager.deploy_agent(spec_id, replicas=2)
        
        assert len(instances) == 2
        assert len(agent_manager.agents) == 2
        
        # Check Docker client was called
        assert mock_docker_client.containers.run.call_count == 2
    
    async def test_deploy_agent_invalid_spec(self, agent_manager):
        """Test deploying agent with invalid spec"""
        mock_mq = AsyncMock()
        await agent_manager.initialize(mock_mq)
        
        with pytest.raises(ValueError, match="Unknown agent spec"):
            await agent_manager.deploy_agent('invalid-spec')
    
    async def test_deploy_agent_docker_failure(self, agent_manager):
        """Test agent deployment with Docker failure"""
        mock_mq = AsyncMock()
        await agent_manager.initialize(mock_mq)
        
        # Mock Docker to raise exception
        with patch.object(agent_manager, '_create_container', side_effect=Exception("Docker error")):
            instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=1)
            
            # Should return empty list on failure
            assert len(instances) == 0
    
    def test_create_container_config(self, agent_manager):
        """Test container configuration creation"""
        spec = agent_manager.agent_specs['scraping-efficiency-specialist']
        instance_id = 'test-instance'
        
        # Mock the actual container creation
        with patch.object(agent_manager.docker_client.containers, 'run') as mock_run:
            mock_container = MagicMock()
            mock_container.id = 'container-123'
            mock_run.return_value = mock_container
            
            asyncio.run(agent_manager._create_container(instance_id, spec))
            
            # Check container configuration
            call_args = mock_run.call_args
            config = call_args[1]  # kwargs
            
            assert config['image'] == spec.image
            assert config['name'].endswith(instance_id)
            assert config['environment'] == spec.environment
            assert 'swarm.managed' in config['labels']
    
    async def test_stop_agent(self, agent_manager, mock_docker_client):
        """Test stopping agent instance"""
        mock_mq = AsyncMock()
        await agent_manager.initialize(mock_mq)
        
        # Deploy an agent first
        instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=1)
        agent_id = instances[0]
        
        # Stop the agent
        success = await agent_manager.stop_agent(agent_id)
        
        assert success is True
        assert agent_manager.agents[agent_id].status == AgentStatus.STOPPED
        
        # Check Docker stop was called
        mock_docker_client.containers.get.return_value.stop.assert_called_once()
    
    async def test_stop_agent_force(self, agent_manager, mock_docker_client):
        """Test force stopping agent instance"""
        mock_mq = AsyncMock()
        await agent_manager.initialize(mock_mq)
        
        instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=1)
        agent_id = instances[0]
        
        success = await agent_manager.stop_agent(agent_id, force=True)
        
        assert success is True
        mock_docker_client.containers.get.return_value.kill.assert_called_once()
    
    async def test_stop_nonexistent_agent(self, agent_manager):
        """Test stopping non-existent agent"""
        mock_mq = AsyncMock()
        await agent_manager.initialize(mock_mq)
        
        success = await agent_manager.stop_agent('nonexistent-agent')
        assert success is False
    
    async def test_restart_agent(self, agent_manager, mock_docker_client):
        """Test restarting agent instance"""
        mock_mq = AsyncMock()
        await agent_manager.initialize(mock_mq)
        
        instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=1)
        agent_id = instances[0]
        
        initial_restart_count = agent_manager.agents[agent_id].restart_count
        
        success = await agent_manager.restart_agent(agent_id)
        
        assert success is True
        assert agent_manager.agents[agent_id].restart_count == initial_restart_count + 1
        assert agent_manager.agents[agent_id].status == AgentStatus.STARTING
    
    async def test_scale_agent_type_up(self, agent_manager, mock_docker_client):
        """Test scaling agent type up"""
        mock_mq = AsyncMock()
        await agent_manager.initialize(mock_mq)
        
        agent_type = 'scraping-efficiency'
        target_replicas = 3
        
        success = await agent_manager.scale_agent_type(agent_type, target_replicas)
        
        assert success is True
        
        # Count agents of this type
        agents_of_type = [a for a in agent_manager.agents.values() 
                         if a.spec.type.value == agent_type]
        assert len(agents_of_type) == target_replicas
    
    async def test_scale_agent_type_down(self, agent_manager, mock_docker_client):
        """Test scaling agent type down"""
        mock_mq = AsyncMock()
        await agent_manager.initialize(mock_mq)
        
        # Deploy 3 agents first
        agent_type = 'scraping-efficiency'
        await agent_manager.scale_agent_type(agent_type, 3)
        
        # Scale down to 1
        success = await agent_manager.scale_agent_type(agent_type, 1)
        
        assert success is True
        
        # Count remaining agents
        agents_of_type = [a for a in agent_manager.agents.values() 
                         if a.spec.type.value == agent_type and a.status != AgentStatus.STOPPED]
        assert len(agents_of_type) == 1
    
    async def test_get_agent_status_single(self, agent_manager, mock_docker_client):
        """Test getting single agent status"""
        mock_mq = AsyncMock()
        await agent_manager.initialize(mock_mq)
        
        instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=1)
        agent_id = instances[0]
        
        status = await agent_manager.get_agent_status(agent_id)
        
        assert 'id' in status
        assert status['id'] == agent_id
        assert 'status' in status
        assert 'created_at' in status
    
    async def test_get_agent_status_all(self, agent_manager, mock_docker_client):
        """Test getting all agents status"""
        mock_mq = AsyncMock()
        await agent_manager.initialize(mock_mq)
        
        await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=2)
        await agent_manager.deploy_agent('keyword-precision-specialist', replicas=1)
        
        status = await agent_manager.get_agent_status()
        
        assert 'total_agents' in status
        assert status['total_agents'] == 3
        assert 'status_counts' in status
        assert 'agents' in status
        assert len(status['agents']) == 3
    
    async def test_get_agent_status_nonexistent(self, agent_manager):
        """Test getting status for non-existent agent"""
        mock_mq = AsyncMock()
        await agent_manager.initialize(mock_mq)
        
        status = await agent_manager.get_agent_status('nonexistent')
        
        assert 'error' in status
    
    async def test_assign_task_to_agent(self, agent_manager, sample_task_definition, mock_docker_client):
        """Test task assignment to agent"""
        mock_mq = AsyncMock()
        await agent_manager.initialize(mock_mq)
        
        # Deploy agent and set it healthy
        instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=1)
        agent_id = instances[0]
        agent_manager.agents[agent_id].status = AgentStatus.HEALTHY
        
        # Update task to match agent type
        sample_task_definition.agent_type = 'scraping-efficiency'
        
        assigned_agent = await agent_manager.assign_task_to_agent(sample_task_definition)
        
        assert assigned_agent == agent_id
        assert agent_manager.agents[agent_id].task_count == 1
        
        # Check message was published
        mock_mq.publish_message.assert_called_once()
    
    async def test_assign_task_no_suitable_agent(self, agent_manager, sample_task_definition):
        """Test task assignment when no suitable agent available"""
        mock_mq = AsyncMock()
        await agent_manager.initialize(mock_mq)
        
        # Set task type that no deployed agent can handle
        sample_task_definition.agent_type = 'nonexistent-type'
        
        assigned_agent = await agent_manager.assign_task_to_agent(sample_task_definition)
        
        assert assigned_agent is None
    
    async def test_health_monitoring_loop(self, agent_manager, mock_docker_client):
        """Test health monitoring loop"""
        mock_mq = AsyncMock()
        await agent_manager.initialize(mock_mq)
        
        # Deploy agent
        instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=1)
        agent_id = instances[0]
        
        # Mock health check
        with patch.object(agent_manager, '_check_agent_health') as mock_health_check:
            mock_health_check.return_value = None
            
            # Start monitoring loop in background
            monitoring_task = asyncio.create_task(agent_manager._health_monitoring_loop())
            
            # Wait a short time
            await asyncio.sleep(0.1)
            
            # Stop monitoring
            agent_manager.running = False
            monitoring_task.cancel()
            
            try:
                await monitoring_task
            except asyncio.CancelledError:
                pass
            
            # Health check should have been called
            assert mock_health_check.called
    
    async def test_check_agent_health_healthy(self, agent_manager, mock_docker_client):
        """Test health check for healthy agent"""
        mock_mq = AsyncMock()
        await agent_manager.initialize(mock_mq)
        
        instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=1)
        agent_id = instances[0]
        agent = agent_manager.agents[agent_id]
        
        # Mock container as healthy
        mock_container = mock_docker_client.containers.get.return_value
        mock_container.status = 'running'
        mock_container.attrs = {'State': {'Health': {'Status': 'healthy'}}}
        
        await agent_manager._check_agent_health(agent)
        
        assert agent.status == AgentStatus.HEALTHY
        assert len(agent.health_checks) > 0
    
    async def test_check_agent_health_unhealthy(self, agent_manager, mock_docker_client):
        """Test health check for unhealthy agent"""
        mock_mq = AsyncMock()
        await agent_manager.initialize(mock_mq)
        
        instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=1)
        agent_id = instances[0]
        agent = agent_manager.agents[agent_id]
        
        # Mock container as unhealthy
        mock_container = mock_docker_client.containers.get.return_value
        mock_container.status = 'running'
        mock_container.attrs = {'State': {'Health': {'Status': 'unhealthy'}}}
        
        await agent_manager._check_agent_health(agent)
        
        assert agent.status == AgentStatus.CRITICAL
    
    async def test_agent_restart_on_critical_status(self, agent_manager, mock_docker_client):
        """Test automatic restart when agent becomes critical"""
        mock_mq = AsyncMock()
        await agent_manager.initialize(mock_mq)
        
        instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=1)
        agent_id = instances[0]
        agent = agent_manager.agents[agent_id]
        
        # Set agent as critical
        agent.status = AgentStatus.CRITICAL
        agent.restart_count = 0
        
        # Mock restart functionality
        with patch.object(agent_manager, 'restart_agent') as mock_restart:
            mock_restart.return_value = True
            
            await agent_manager._check_agent_health(agent)
            
            # Should trigger restart
            mock_restart.assert_called_once_with(agent_id)
    
    async def test_auto_scaling_evaluation(self, agent_manager, mock_docker_client):
        """Test auto-scaling evaluation logic"""
        mock_mq = AsyncMock()
        mock_mq.get_task_statistics.return_value = {
            'queue_lengths': {'HIGH': 5, 'MEDIUM': 10},
            'status_counts': {'completed': 50}
        }
        await agent_manager.initialize(mock_mq)
        
        # Deploy agents and set high task load
        instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=2)
        for agent_id in instances:
            agent_manager.agents[agent_id].status = AgentStatus.HEALTHY
            agent_manager.agents[agent_id].task_count = 10  # High load
        
        # Mock deploy for scale up
        with patch.object(agent_manager, 'deploy_agent') as mock_deploy:
            mock_deploy.return_value = ['new-agent']
            
            await agent_manager._evaluate_scaling_for_type(
                AgentType.SCRAPING_EFFICIENCY, 
                {'queue_lengths': {}}
            )
            
            # Should scale up due to high load
            mock_deploy.assert_called_once()
    
    async def test_consul_service_registration(self, agent_manager, mock_consul_client):
        """Test Consul service registration"""
        await agent_manager._register_service_discovery()
        
        # Check service was registered
        mock_consul_client.agent.service.register.assert_called_once()
        
        call_args = mock_consul_client.agent.service.register.call_args
        assert call_args[1]['name'] == 'agent-manager'
    
    async def test_agent_consul_registration(self, agent_manager, mock_consul_client, mock_docker_client):
        """Test agent registration with Consul"""
        mock_mq = AsyncMock()
        await agent_manager.initialize(mock_mq)
        
        instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=1)
        agent_id = instances[0]
        agent = agent_manager.agents[agent_id]
        
        await agent_manager._register_agent_with_consul(agent)
        
        # Check agent was registered
        mock_consul_client.agent.service.register.assert_called()
        
        call_args = mock_consul_client.agent.service.register.call_args
        assert call_args[1]['service_id'] == agent_id
    
    async def test_shutdown_graceful(self, agent_manager, mock_docker_client):
        """Test graceful shutdown"""
        mock_mq = AsyncMock()
        await agent_manager.initialize(mock_mq)
        
        # Deploy some agents
        await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=2)
        
        # Shutdown
        await agent_manager.shutdown()
        
        assert agent_manager.running is False
        
        # All agents should have been stopped
        mock_docker_client.containers.get.return_value.stop.assert_called()


@pytest.mark.unit
class TestAgentSpec:
    """Test agent specification data structure"""
    
    def test_agent_spec_creation(self):
        """Test creating agent specification"""
        spec = AgentSpec(
            id='test-agent',
            name='Test Agent',
            type=AgentType.SCRAPING_EFFICIENCY,
            image='test/agent:latest',
            cpu_limit='1.0',
            memory_limit='1GB'
        )
        
        assert spec.id == 'test-agent'
        assert spec.type == AgentType.SCRAPING_EFFICIENCY
        assert spec.restart_policy == 'unless-stopped'  # Default
        assert spec.replicas == 1  # Default
    
    def test_agent_spec_with_environment(self):
        """Test agent spec with environment variables"""
        env = {'VAR1': 'value1', 'VAR2': 'value2'}
        
        spec = AgentSpec(
            id='env-agent',
            name='Environment Agent',
            type=AgentType.KEYWORD_PRECISION,
            image='test/agent:latest',
            environment=env
        )
        
        assert spec.environment == env
    
    def test_agent_spec_with_volumes(self):
        """Test agent spec with volume mounts"""
        volumes = [
            {'host': '/host/path', 'container': '/container/path', 'mode': 'ro'}
        ]
        
        spec = AgentSpec(
            id='volume-agent',
            name='Volume Agent',
            type=AgentType.API_RELIABILITY,
            image='test/agent:latest',
            volumes=volumes
        )
        
        assert spec.volumes == volumes
    
    def test_agent_spec_with_health_check(self):
        """Test agent spec with health check configuration"""
        health_check = {
            'test': ['CMD', 'curl', '-f', 'http://localhost:8080/health'],
            'interval': '30s',
            'timeout': '10s',
            'retries': 3
        }
        
        spec = AgentSpec(
            id='health-agent',
            name='Health Check Agent',
            type=AgentType.PERFORMANCE_OPTIMIZER,
            image='test/agent:latest',
            health_check=health_check
        )
        
        assert spec.health_check == health_check


@pytest.mark.unit
class TestAgentInstance:
    """Test agent instance data structure"""
    
    def test_agent_instance_creation(self, sample_agent_data):
        """Test creating agent instance"""
        spec = AgentSpec(
            id='test-spec',
            name='Test Spec',
            type=AgentType.SCRAPING_EFFICIENCY,
            image='test:latest'
        )
        
        instance = AgentInstance(
            id='instance-123',
            spec=spec,
            container_id='container-456',
            status=AgentStatus.STARTING,
            created_at=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            health_checks=[],
            metrics={}
        )
        
        assert instance.id == 'instance-123'
        assert instance.status == AgentStatus.STARTING
        assert instance.restart_count == 0  # Default
        assert instance.task_count == 0  # Default


@pytest.mark.unit
class TestLoadBalancer:
    """Test load balancer functionality"""
    
    def test_load_balancer_creation(self):
        """Test creating load balancer"""
        lb = LoadBalancer()
        assert lb.assignment_counts == {}
    
    def test_select_agent_single(self):
        """Test selecting from single agent"""
        lb = LoadBalancer()
        
        spec = AgentSpec(
            id='test',
            name='Test',
            type=AgentType.SCRAPING_EFFICIENCY,
            image='test:latest'
        )
        
        agent = AgentInstance(
            id='agent-1',
            spec=spec,
            container_id='container-1',
            status=AgentStatus.HEALTHY,
            created_at=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            health_checks=[],
            metrics={}
        )
        
        task = TaskDefinition(
            id='task-1',
            type='test',
            agent_type='scraping-efficiency',
            priority=Priority.MEDIUM,
            payload={}
        )
        
        selected = lb.select_agent([agent], task)
        assert selected == agent
    
    def test_select_agent_multiple(self):
        """Test selecting from multiple agents"""
        lb = LoadBalancer()
        
        spec = AgentSpec(
            id='test',
            name='Test',
            type=AgentType.SCRAPING_EFFICIENCY,
            image='test:latest'
        )
        
        # Create agents with different loads
        agent1 = AgentInstance(
            id='agent-1', spec=spec, container_id='c1', status=AgentStatus.HEALTHY,
            created_at=datetime.now(timezone.utc), last_seen=datetime.now(timezone.utc),
            health_checks=[], metrics={}, task_count=5  # High load
        )
        
        agent2 = AgentInstance(
            id='agent-2', spec=spec, container_id='c2', status=AgentStatus.HEALTHY,
            created_at=datetime.now(timezone.utc), last_seen=datetime.now(timezone.utc),
            health_checks=[], metrics={}, task_count=1  # Low load
        )
        
        task = TaskDefinition(
            id='task-1',
            type='test',
            agent_type='scraping-efficiency',
            priority=Priority.MEDIUM,
            payload={}
        )
        
        selected = lb.select_agent([agent1, agent2], task)
        # Should select agent with lower load
        assert selected == agent2
    
    def test_select_agent_none_available(self):
        """Test selecting when no agents available"""
        lb = LoadBalancer()
        
        task = TaskDefinition(
            id='task-1',
            type='test',
            agent_type='any',
            priority=Priority.MEDIUM,
            payload={}
        )
        
        selected = lb.select_agent([], task)
        assert selected is None
    
    def test_calculate_agent_score(self):
        """Test agent scoring calculation"""
        lb = LoadBalancer()
        
        spec = AgentSpec(
            id='test',
            name='Test',
            type=AgentType.SCRAPING_EFFICIENCY,
            image='test:latest',
            priority=2
        )
        
        agent = AgentInstance(
            id='agent-1', spec=spec, container_id='c1', status=AgentStatus.HEALTHY,
            created_at=datetime.now(timezone.utc), last_seen=datetime.now(timezone.utc),
            health_checks=[], metrics={}, task_count=3, error_rate=0.1, restart_count=1
        )
        
        task = TaskDefinition(
            id='task-1',
            type='test',
            agent_type='scraping-efficiency',
            priority=Priority.MEDIUM,
            payload={}
        )
        
        score = lb._calculate_agent_score(agent, task)
        
        # Should be positive score
        assert score >= 0
        
        # Score calculation should consider task count, error rate, etc.
        expected_base = 100.0
        expected_score = (expected_base 
                         - agent.task_count * 10  # Task penalty
                         + 20  # Type match bonus
                         - agent.error_rate * 50  # Error penalty
                         + agent.spec.priority * 5  # Priority bonus
                         - agent.restart_count * 5)  # Restart penalty
        
        assert score == max(expected_score, 0)


@pytest.mark.unit
class TestAgentManagerAPI:
    """Test agent manager REST API"""
    
    def test_api_initialization(self, agent_manager):
        """Test API initialization"""
        api = AgentManagerAPI(agent_manager)
        
        assert api.agent_manager == agent_manager
        assert api.app is not None
    
    async def test_health_check_endpoint(self, agent_manager):
        """Test health check endpoint"""
        api = AgentManagerAPI(agent_manager)
        
        # Mock request
        request = MagicMock()
        
        response = await api.health_check(request)
        
        assert response.status == 200
        # Response should contain status and timestamp
    
    async def test_get_agents_endpoint(self, agent_manager):
        """Test get agents endpoint"""
        api = AgentManagerAPI(agent_manager)
        
        # Mock agent manager response
        with patch.object(agent_manager, 'get_agent_status') as mock_status:
            mock_status.return_value = {'total_agents': 0, 'agents': {}}
            
            request = MagicMock()
            response = await api.get_agents(request)
            
            assert response.status == 200
            mock_status.assert_called_once()
    
    async def test_deploy_agent_endpoint(self, agent_manager):
        """Test deploy agent endpoint"""
        api = AgentManagerAPI(agent_manager)
        
        # Mock request
        request = MagicMock()
        request.match_info = {'spec_id': 'test-spec'}
        request.content_type = 'application/json'
        request.json = AsyncMock(return_value={'replicas': 2})
        
        # Mock agent manager response
        with patch.object(agent_manager, 'deploy_agent') as mock_deploy:
            mock_deploy.return_value = ['agent-1', 'agent-2']
            
            response = await api.deploy_agent(request)
            
            assert response.status == 200
            mock_deploy.assert_called_once_with('test-spec', 2)
    
    async def test_api_error_handling(self, agent_manager):
        """Test API error handling"""
        api = AgentManagerAPI(agent_manager)
        
        # Mock agent manager to raise exception
        with patch.object(agent_manager, 'get_agent_status', side_effect=Exception("Test error")):
            request = MagicMock()
            response = await api.get_agents(request)
            
            assert response.status == 500