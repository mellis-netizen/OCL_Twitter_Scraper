#!/usr/bin/env python3
"""
Agent Lifecycle Management API for TGE Swarm
Manages agent deployment, scaling, health monitoring, and coordination
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
import docker
import docker.errors
from aiohttp import web, WSMsgType
import aiohttp_cors
import consul
import yaml

from message_queue import MessageQueue, SwarmMessage, MessageType, Priority, TaskDefinition


class AgentStatus(Enum):
    """Agent status enumeration"""
    PENDING = "pending"
    STARTING = "starting"
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    STOPPED = "stopped"
    FAILED = "failed"


class AgentType(Enum):
    """Agent type enumeration"""
    SCRAPING_EFFICIENCY = "scraping-efficiency"
    KEYWORD_PRECISION = "keyword-precision"
    API_RELIABILITY = "api-reliability"
    PERFORMANCE_OPTIMIZER = "performance-optimizer"
    DATA_QUALITY = "data-quality"
    MONITORING = "monitoring"


@dataclass
class AgentSpec:
    """Agent specification for deployment"""
    id: str
    name: str
    type: AgentType
    image: str
    cpu_limit: str = "0.5"
    memory_limit: str = "512m"
    environment: Dict[str, str] = None
    volumes: List[Dict[str, str]] = None
    ports: List[int] = None
    restart_policy: str = "unless-stopped"
    health_check: Dict[str, Any] = None
    dependencies: List[str] = None
    priority: int = 1
    replicas: int = 1


@dataclass
class AgentInstance:
    """Running agent instance"""
    id: str
    spec: AgentSpec
    container_id: str
    status: AgentStatus
    created_at: datetime
    last_seen: datetime
    health_checks: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    restart_count: int = 0
    task_count: int = 0
    error_rate: float = 0.0


class AgentManager:
    """Agent lifecycle management system"""
    
    def __init__(self, config_file: str = "config/agent_manager.yaml"):
        self.config = self._load_config(config_file)
        self.docker_client = docker.from_env()
        self.consul_client = consul.Consul(
            host=self.config.get('consul_host', 'localhost'),
            port=self.config.get('consul_port', 8500)
        )
        
        # State management
        self.agents: Dict[str, AgentInstance] = {}
        self.agent_specs: Dict[str, AgentSpec] = {}
        self.running = False
        
        # Message queue for agent communication
        self.message_queue: Optional[MessageQueue] = None
        
        # Load balancing
        self.load_balancer = LoadBalancer()
        
        # Health monitoring
        self.health_check_interval = 30
        self.restart_threshold = 3
        
        self.setup_logging()
        self._load_agent_specs()
    
    def setup_logging(self):
        """Setup agent manager logging"""
        self.logger = logging.getLogger("AgentManager")
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load agent manager configuration"""
        try:
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.warning(f"Config file {config_file} not found, using defaults")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default agent manager configuration"""
        return {
            'consul_host': 'localhost',
            'consul_port': 8500,
            'docker_network': 'tge-swarm',
            'registry_prefix': 'tge-swarm',
            'max_agents_per_type': 5,
            'health_check_interval': 30,
            'restart_threshold': 3,
            'scale_up_threshold': 0.8,
            'scale_down_threshold': 0.3,
            'default_resources': {
                'cpu_limit': '0.5',
                'memory_limit': '512m'
            }
        }
    
    def _load_agent_specs(self):
        """Load agent specifications from configuration"""
        specs_config = self.config.get('agent_specs', {})
        
        # Default agent specifications
        default_specs = {
            'scraping-efficiency-specialist': AgentSpec(
                id='scraping-efficiency-specialist',
                name='Scraping Efficiency Specialist',
                type=AgentType.SCRAPING_EFFICIENCY,
                image='tge-swarm/scraping-agent:latest',
                cpu_limit='1.0',
                memory_limit='1GB',
                environment={
                    'AGENT_TYPE': 'scraping-efficiency',
                    'REDIS_URL': 'redis://redis-cluster:7001',
                    'LOG_LEVEL': 'INFO'
                },
                health_check={
                    'test': ['CMD', 'curl', '-f', 'http://localhost:8080/health'],
                    'interval': '30s',
                    'timeout': '10s',
                    'retries': 3
                },
                priority=1,
                replicas=2
            ),
            'keyword-precision-specialist': AgentSpec(
                id='keyword-precision-specialist',
                name='TGE Keyword Precision Specialist',
                type=AgentType.KEYWORD_PRECISION,
                image='tge-swarm/keyword-agent:latest',
                cpu_limit='0.8',
                memory_limit='768m',
                environment={
                    'AGENT_TYPE': 'keyword-precision',
                    'REDIS_URL': 'redis://redis-cluster:7001',
                    'LOG_LEVEL': 'INFO'
                },
                health_check={
                    'test': ['CMD', 'curl', '-f', 'http://localhost:8080/health'],
                    'interval': '30s',
                    'timeout': '10s',
                    'retries': 3
                },
                priority=1,
                replicas=1
            ),
            'api-reliability-optimizer': AgentSpec(
                id='api-reliability-optimizer',
                name='API Reliability Optimizer',
                type=AgentType.API_RELIABILITY,
                image='tge-swarm/api-agent:latest',
                cpu_limit='0.6',
                memory_limit='512m',
                environment={
                    'AGENT_TYPE': 'api-reliability',
                    'REDIS_URL': 'redis://redis-cluster:7001',
                    'LOG_LEVEL': 'INFO'
                },
                health_check={
                    'test': ['CMD', 'curl', '-f', 'http://localhost:8080/health'],
                    'interval': '30s',
                    'timeout': '10s',
                    'retries': 3
                },
                priority=2,
                replicas=1
            ),
            'performance-optimizer': AgentSpec(
                id='performance-optimizer',
                name='Performance Bottleneck Eliminator',
                type=AgentType.PERFORMANCE_OPTIMIZER,
                image='tge-swarm/performance-agent:latest',
                cpu_limit='1.2',
                memory_limit='1GB',
                environment={
                    'AGENT_TYPE': 'performance-optimizer',
                    'REDIS_URL': 'redis://redis-cluster:7001',
                    'LOG_LEVEL': 'INFO'
                },
                health_check={
                    'test': ['CMD', 'curl', '-f', 'http://localhost:8080/health'],
                    'interval': '30s',
                    'timeout': '10s',
                    'retries': 3
                },
                priority=2,
                replicas=1
            ),
            'data-quality-enforcer': AgentSpec(
                id='data-quality-enforcer',
                name='Data Quality Enforcer',
                type=AgentType.DATA_QUALITY,
                image='tge-swarm/data-quality-agent:latest',
                cpu_limit='0.5',
                memory_limit='512m',
                environment={
                    'AGENT_TYPE': 'data-quality',
                    'REDIS_URL': 'redis://redis-cluster:7001',
                    'LOG_LEVEL': 'INFO'
                },
                health_check={
                    'test': ['CMD', 'curl', '-f', 'http://localhost:8080/health'],
                    'interval': '30s',
                    'timeout': '10s',
                    'retries': 3
                },
                priority=3,
                replicas=1
            )
        }
        
        # Merge with config
        for spec_id, spec in default_specs.items():
            if spec_id in specs_config:
                # Update with config values
                config_spec = specs_config[spec_id]
                for key, value in config_spec.items():
                    if hasattr(spec, key):
                        setattr(spec, key, value)
            
            self.agent_specs[spec_id] = spec
    
    async def initialize(self, message_queue: MessageQueue):
        """Initialize agent manager"""
        self.message_queue = message_queue
        
        # Register service discovery
        await self._register_service_discovery()
        
        # Start monitoring tasks
        self.running = True
        asyncio.create_task(self._health_monitoring_loop())
        asyncio.create_task(self._auto_scaling_loop())
        
        self.logger.info("Agent manager initialized")
    
    async def deploy_agent(self, spec_id: str, replicas: Optional[int] = None) -> List[str]:
        """Deploy agent instances"""
        if spec_id not in self.agent_specs:
            raise ValueError(f"Unknown agent spec: {spec_id}")
        
        spec = self.agent_specs[spec_id]
        target_replicas = replicas or spec.replicas
        
        deployed_instances = []
        
        for i in range(target_replicas):
            instance_id = f"{spec_id}-{i+1}-{int(time.time())}"
            
            try:
                # Create container
                container = await self._create_container(instance_id, spec)
                
                # Create agent instance
                agent_instance = AgentInstance(
                    id=instance_id,
                    spec=spec,
                    container_id=container.id,
                    status=AgentStatus.STARTING,
                    created_at=datetime.now(),
                    last_seen=datetime.now(),
                    health_checks=[],
                    metrics={}
                )
                
                # Register agent
                self.agents[instance_id] = agent_instance
                
                # Register with Consul
                await self._register_agent_with_consul(agent_instance)
                
                deployed_instances.append(instance_id)
                self.logger.info(f"Deployed agent instance: {instance_id}")
                
            except Exception as e:
                self.logger.error(f"Failed to deploy agent instance {instance_id}: {e}")
                continue
        
        return deployed_instances
    
    async def _create_container(self, instance_id: str, spec: AgentSpec) -> docker.models.containers.Container:
        """Create Docker container for agent"""
        # Prepare container configuration
        container_config = {
            'image': spec.image,
            'name': f"{self.config['registry_prefix']}-{instance_id}",
            'detach': True,
            'restart_policy': {'Name': spec.restart_policy},
            'environment': spec.environment or {},
            'labels': {
                'swarm.managed': 'true',
                'swarm.component': 'agent',
                'swarm.agent_type': spec.type.value,
                'swarm.agent_id': instance_id
            },
            'network': self.config.get('docker_network', 'tge-swarm')
        }
        
        # Add resource limits
        if spec.cpu_limit or spec.memory_limit:
            container_config['host_config'] = docker.types.HostConfig(
                cpu_count=float(spec.cpu_limit) if spec.cpu_limit else None,
                mem_limit=spec.memory_limit if spec.memory_limit else None
            )
        
        # Add ports
        if spec.ports:
            container_config['ports'] = {f"{port}/tcp": None for port in spec.ports}
        
        # Add volumes
        if spec.volumes:
            container_config['volumes'] = {}
            for volume in spec.volumes:
                container_config['volumes'][volume['host']] = {
                    'bind': volume['container'],
                    'mode': volume.get('mode', 'rw')
                }
        
        # Add health check
        if spec.health_check:
            container_config['healthcheck'] = spec.health_check
        
        # Create and start container
        container = self.docker_client.containers.run(**container_config)
        
        return container
    
    async def stop_agent(self, agent_id: str, force: bool = False) -> bool:
        """Stop agent instance"""
        if agent_id not in self.agents:
            return False
        
        agent = self.agents[agent_id]
        
        try:
            # Stop container
            container = self.docker_client.containers.get(agent.container_id)
            if force:
                container.kill()
            else:
                container.stop(timeout=30)
            
            # Update agent status
            agent.status = AgentStatus.STOPPED
            
            # Deregister from Consul
            await self._deregister_agent_from_consul(agent)
            
            self.logger.info(f"Stopped agent: {agent_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop agent {agent_id}: {e}")
            return False
    
    async def restart_agent(self, agent_id: str) -> bool:
        """Restart agent instance"""
        if agent_id not in self.agents:
            return False
        
        agent = self.agents[agent_id]
        
        try:
            # Stop existing container
            await self.stop_agent(agent_id)
            
            # Create new container
            container = await self._create_container(agent_id, agent.spec)
            
            # Update agent instance
            agent.container_id = container.id
            agent.status = AgentStatus.STARTING
            agent.restart_count += 1
            agent.last_seen = datetime.now()
            
            # Re-register with Consul
            await self._register_agent_with_consul(agent)
            
            self.logger.info(f"Restarted agent: {agent_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restart agent {agent_id}: {e}")
            agent.status = AgentStatus.FAILED
            return False
    
    async def scale_agent_type(self, agent_type: str, target_replicas: int) -> bool:
        """Scale agent type to target replica count"""
        current_agents = [a for a in self.agents.values() if a.spec.type.value == agent_type]
        current_count = len(current_agents)
        
        if target_replicas > current_count:
            # Scale up
            spec_id = f"{agent_type}-specialist"
            if spec_id in self.agent_specs:
                additional_replicas = target_replicas - current_count
                deployed = await self.deploy_agent(spec_id, additional_replicas)
                self.logger.info(f"Scaled up {agent_type}: {current_count} -> {target_replicas}")
                return len(deployed) == additional_replicas
        
        elif target_replicas < current_count:
            # Scale down
            agents_to_stop = current_agents[target_replicas:]
            stopped_count = 0
            
            for agent in agents_to_stop:
                if await self.stop_agent(agent.id):
                    stopped_count += 1
            
            self.logger.info(f"Scaled down {agent_type}: {current_count} -> {target_replicas}")
            return stopped_count == len(agents_to_stop)
        
        return True  # No scaling needed
    
    async def get_agent_status(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Get agent status information"""
        if agent_id:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                return {
                    'id': agent.id,
                    'name': agent.spec.name,
                    'type': agent.spec.type.value,
                    'status': agent.status.value,
                    'container_id': agent.container_id,
                    'created_at': agent.created_at.isoformat(),
                    'last_seen': agent.last_seen.isoformat(),
                    'restart_count': agent.restart_count,
                    'task_count': agent.task_count,
                    'error_rate': agent.error_rate,
                    'health_checks': agent.health_checks[-5:],  # Last 5 checks
                    'metrics': agent.metrics
                }
            else:
                return {'error': f'Agent {agent_id} not found'}
        
        # Return all agents
        agents_summary = {}
        status_counts = {'healthy': 0, 'warning': 0, 'critical': 0, 'stopped': 0, 'failed': 0}
        
        for agent_id, agent in self.agents.items():
            agents_summary[agent_id] = {
                'name': agent.spec.name,
                'type': agent.spec.type.value,
                'status': agent.status.value,
                'restart_count': agent.restart_count,
                'task_count': agent.task_count,
                'error_rate': agent.error_rate
            }
            
            status = agent.status.value
            if status in status_counts:
                status_counts[status] += 1
        
        return {
            'total_agents': len(self.agents),
            'status_counts': status_counts,
            'agents': agents_summary
        }
    
    async def assign_task_to_agent(self, task: TaskDefinition) -> Optional[str]:
        """Assign task to best available agent"""
        suitable_agents = []
        
        # Find agents that can handle this task type
        for agent_id, agent in self.agents.items():
            if (agent.status == AgentStatus.HEALTHY and 
                (task.agent_type == "any" or agent.spec.type.value == task.agent_type)):
                suitable_agents.append(agent)
        
        if not suitable_agents:
            return None
        
        # Use load balancer to select best agent
        selected_agent = self.load_balancer.select_agent(suitable_agents, task)
        
        if selected_agent:
            # Send task via message queue
            message = SwarmMessage(
                id=str(uuid.uuid4()),
                type=MessageType.TASK_ASSIGNMENT,
                sender="agent-manager",
                recipient=selected_agent.id,
                timestamp=datetime.now(),
                payload=asdict(task),
                priority=task.priority
            )
            
            if self.message_queue:
                await self.message_queue.publish_message(message)
            
            selected_agent.task_count += 1
            return selected_agent.id
        
        return None
    
    async def _health_monitoring_loop(self):
        """Continuous health monitoring of agents"""
        while self.running:
            try:
                for agent_id, agent in list(self.agents.items()):
                    await self._check_agent_health(agent)
                
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(10)
    
    async def _check_agent_health(self, agent: AgentInstance):
        """Check individual agent health"""
        try:
            # Check container status
            container = self.docker_client.containers.get(agent.container_id)
            container_status = container.status
            
            # Get health check result if available
            health_status = None
            if hasattr(container, 'attrs') and 'State' in container.attrs:
                health = container.attrs['State'].get('Health')
                if health:
                    health_status = health.get('Status', 'unknown')
            
            # Update agent status based on container state
            if container_status == 'running':
                if health_status == 'healthy' or health_status is None:
                    agent.status = AgentStatus.HEALTHY
                elif health_status == 'unhealthy':
                    agent.status = AgentStatus.CRITICAL
                else:
                    agent.status = AgentStatus.WARNING
            else:
                agent.status = AgentStatus.CRITICAL
            
            # Record health check
            health_check_result = {
                'timestamp': datetime.now().isoformat(),
                'container_status': container_status,
                'health_status': health_status,
                'status': agent.status.value
            }
            
            agent.health_checks.append(health_check_result)
            
            # Keep only last 10 health checks
            agent.health_checks = agent.health_checks[-10:]
            
            # Update last seen time
            agent.last_seen = datetime.now()
            
            # Check if restart is needed
            if (agent.status == AgentStatus.CRITICAL and 
                agent.restart_count < self.restart_threshold):
                self.logger.warning(f"Agent {agent.id} is critical, scheduling restart")
                asyncio.create_task(self.restart_agent(agent.id))
            
        except docker.errors.NotFound:
            self.logger.error(f"Container not found for agent {agent.id}")
            agent.status = AgentStatus.FAILED
        except Exception as e:
            self.logger.error(f"Error checking health for agent {agent.id}: {e}")
            agent.status = AgentStatus.WARNING
    
    async def _auto_scaling_loop(self):
        """Auto-scaling based on load and performance"""
        while self.running:
            try:
                # Check scaling conditions every 5 minutes
                await asyncio.sleep(300)
                
                # Get current metrics
                if self.message_queue:
                    task_stats = await self.message_queue.get_task_statistics()
                    
                    # Analyze queue lengths and decide on scaling
                    for agent_type in AgentType:
                        await self._evaluate_scaling_for_type(agent_type, task_stats)
                
            except Exception as e:
                self.logger.error(f"Error in auto-scaling loop: {e}")
                await asyncio.sleep(60)
    
    async def _evaluate_scaling_for_type(self, agent_type: AgentType, task_stats: Dict[str, Any]):
        """Evaluate if scaling is needed for agent type"""
        try:
            # Get current agents of this type
            current_agents = [a for a in self.agents.values() if a.spec.type == agent_type]
            healthy_agents = [a for a in current_agents if a.status == AgentStatus.HEALTHY]
            
            if not healthy_agents:
                return
            
            # Calculate average task load
            total_tasks = sum(a.task_count for a in healthy_agents)
            avg_tasks_per_agent = total_tasks / len(healthy_agents) if healthy_agents else 0
            
            # Scale up conditions
            scale_up_threshold = self.config.get('scale_up_threshold', 0.8)
            max_agents = self.config.get('max_agents_per_type', 5)
            
            if (avg_tasks_per_agent > scale_up_threshold and 
                len(current_agents) < max_agents):
                spec_id = f"{agent_type.value}-specialist"
                if spec_id in self.agent_specs:
                    await self.deploy_agent(spec_id, 1)
                    self.logger.info(f"Auto-scaled up {agent_type.value}: load={avg_tasks_per_agent}")
            
            # Scale down conditions
            scale_down_threshold = self.config.get('scale_down_threshold', 0.3)
            min_agents = 1
            
            if (avg_tasks_per_agent < scale_down_threshold and 
                len(healthy_agents) > min_agents):
                # Remove least utilized agent
                least_utilized = min(healthy_agents, key=lambda a: a.task_count)
                await self.stop_agent(least_utilized.id)
                self.logger.info(f"Auto-scaled down {agent_type.value}: load={avg_tasks_per_agent}")
                
        except Exception as e:
            self.logger.error(f"Error evaluating scaling for {agent_type.value}: {e}")
    
    async def _register_service_discovery(self):
        """Register agent manager with service discovery"""
        try:
            self.consul_client.agent.service.register(
                name='agent-manager',
                service_id='agent-manager-primary',
                address='agent-manager',
                port=8080,
                check=consul.Check.http('http://agent-manager:8080/health', interval='30s')
            )
            self.logger.info("Registered with service discovery")
        except Exception as e:
            self.logger.error(f"Failed to register with service discovery: {e}")
    
    async def _register_agent_with_consul(self, agent: AgentInstance):
        """Register agent with Consul service discovery"""
        try:
            self.consul_client.agent.service.register(
                name='tge-agent',
                service_id=agent.id,
                address=agent.container_id[:12],  # Use short container ID
                port=8080,
                tags=[agent.spec.type.value, f"priority:{agent.spec.priority}"],
                check=consul.Check.http(f'http://{agent.container_id[:12]}:8080/health', interval='30s')
            )
        except Exception as e:
            self.logger.error(f"Failed to register agent {agent.id} with Consul: {e}")
    
    async def _deregister_agent_from_consul(self, agent: AgentInstance):
        """Deregister agent from Consul service discovery"""
        try:
            self.consul_client.agent.service.deregister(agent.id)
        except Exception as e:
            self.logger.error(f"Failed to deregister agent {agent.id} from Consul: {e}")
    
    async def shutdown(self):
        """Shutdown agent manager gracefully"""
        self.running = False
        
        # Stop all agents gracefully
        stop_tasks = []
        for agent_id in list(self.agents.keys()):
            stop_tasks.append(self.stop_agent(agent_id))
        
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        self.logger.info("Agent manager shutdown complete")


class LoadBalancer:
    """Load balancer for task assignment"""
    
    def __init__(self):
        self.assignment_counts = {}
    
    def select_agent(self, agents: List[AgentInstance], task: TaskDefinition) -> Optional[AgentInstance]:
        """Select best agent for task using weighted round-robin"""
        if not agents:
            return None
        
        # Score agents based on load, priority, and task type match
        scored_agents = []
        
        for agent in agents:
            score = self._calculate_agent_score(agent, task)
            scored_agents.append((agent, score))
        
        # Sort by score (higher is better)
        scored_agents.sort(key=lambda x: x[1], reverse=True)
        
        # Return best agent
        return scored_agents[0][0]
    
    def _calculate_agent_score(self, agent: AgentInstance, task: TaskDefinition) -> float:
        """Calculate agent score for task assignment"""
        score = 100.0  # Base score
        
        # Penalize by current task load
        score -= agent.task_count * 10
        
        # Bonus for exact type match
        if agent.spec.type.value == task.agent_type:
            score += 20
        
        # Penalize by error rate
        score -= agent.error_rate * 50
        
        # Bonus for higher priority agents
        score += agent.spec.priority * 5
        
        # Penalize recently restarted agents
        if agent.restart_count > 0:
            score -= agent.restart_count * 5
        
        return max(score, 0)


# REST API for agent management
class AgentManagerAPI:
    """REST API for agent management"""
    
    def __init__(self, agent_manager: AgentManager):
        self.agent_manager = agent_manager
        self.app = web.Application()
        self.setup_routes()
        self.setup_cors()
    
    def setup_routes(self):
        """Setup API routes"""
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/agents', self.get_agents)
        self.app.router.add_get('/agents/{agent_id}', self.get_agent)
        self.app.router.add_post('/agents/{spec_id}/deploy', self.deploy_agent)
        self.app.router.add_post('/agents/{agent_id}/stop', self.stop_agent)
        self.app.router.add_post('/agents/{agent_id}/restart', self.restart_agent)
        self.app.router.add_post('/agents/{agent_type}/scale', self.scale_agents)
        self.app.router.add_get('/specs', self.get_agent_specs)
    
    def setup_cors(self):
        """Setup CORS for API"""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Add CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    async def health_check(self, request):
        """Health check endpoint"""
        return web.json_response({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'agent-manager'
        })
    
    async def get_agents(self, request):
        """Get all agents"""
        try:
            status = await self.agent_manager.get_agent_status()
            return web.json_response(status)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_agent(self, request):
        """Get specific agent"""
        agent_id = request.match_info['agent_id']
        try:
            status = await self.agent_manager.get_agent_status(agent_id)
            return web.json_response(status)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def deploy_agent(self, request):
        """Deploy agent instances"""
        spec_id = request.match_info['spec_id']
        data = await request.json() if request.content_type == 'application/json' else {}
        replicas = data.get('replicas')
        
        try:
            deployed_instances = await self.agent_manager.deploy_agent(spec_id, replicas)
            return web.json_response({
                'success': True,
                'deployed_instances': deployed_instances
            })
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def stop_agent(self, request):
        """Stop agent instance"""
        agent_id = request.match_info['agent_id']
        data = await request.json() if request.content_type == 'application/json' else {}
        force = data.get('force', False)
        
        try:
            success = await self.agent_manager.stop_agent(agent_id, force)
            return web.json_response({'success': success})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def restart_agent(self, request):
        """Restart agent instance"""
        agent_id = request.match_info['agent_id']
        
        try:
            success = await self.agent_manager.restart_agent(agent_id)
            return web.json_response({'success': success})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def scale_agents(self, request):
        """Scale agent type"""
        agent_type = request.match_info['agent_type']
        data = await request.json()
        target_replicas = data['replicas']
        
        try:
            success = await self.agent_manager.scale_agent_type(agent_type, target_replicas)
            return web.json_response({'success': success})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_agent_specs(self, request):
        """Get agent specifications"""
        try:
            specs = {}
            for spec_id, spec in self.agent_manager.agent_specs.items():
                specs[spec_id] = asdict(spec)
            return web.json_response(specs)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)


# CLI interface
if __name__ == "__main__":
    import sys
    
    async def main():
        # Initialize agent manager
        agent_manager = AgentManager()
        
        # Initialize message queue
        from message_queue import create_message_queue
        message_queue = await create_message_queue(["localhost:6379"])
        
        # Initialize agent manager with message queue
        await agent_manager.initialize(message_queue)
        
        if len(sys.argv) > 1:
            command = sys.argv[1]
            
            if command == "deploy":
                spec_id = sys.argv[2] if len(sys.argv) > 2 else "scraping-efficiency-specialist"
                instances = await agent_manager.deploy_agent(spec_id)
                print(f"Deployed instances: {instances}")
            
            elif command == "status":
                status = await agent_manager.get_agent_status()
                print(json.dumps(status, indent=2))
            
            elif command == "api":
                # Start API server
                api = AgentManagerAPI(agent_manager)
                runner = web.AppRunner(api.app)
                await runner.setup()
                site = web.TCPSite(runner, 'localhost', 8080)
                await site.start()
                
                print("Agent Manager API running on http://localhost:8080")
                
                # Keep running
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    pass
                finally:
                    await runner.cleanup()
                    await agent_manager.shutdown()
        else:
            print("Available commands: deploy [spec_id], status, api")
    
    asyncio.run(main())