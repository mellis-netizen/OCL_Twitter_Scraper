#!/usr/bin/env python3
"""
TGE Swarm Agent Deployment Framework
Handles lifecycle management, scaling, and health monitoring of swarm agents
"""

import asyncio
import docker
import json
import logging
import os
import time
import yaml
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
import aioredis
import asyncpg
from dataclasses import dataclass, asdict
import consul

class AgentState(Enum):
    PENDING = "pending"
    DEPLOYING = "deploying"
    RUNNING = "running"
    SCALING = "scaling"
    UNHEALTHY = "unhealthy"
    TERMINATING = "terminating"
    FAILED = "failed"
    STOPPED = "stopped"

@dataclass
class AgentSpec:
    name: str
    type: str
    image: str
    replicas: int = 1
    resources: Dict[str, Any] = None
    environment: Dict[str, str] = None
    volumes: List[str] = None
    health_check: Dict[str, Any] = None
    deployment_strategy: str = "rolling"
    auto_scaling: Dict[str, Any] = None

@dataclass
class AgentInstance:
    id: str
    agent_name: str
    container_id: str
    state: AgentState
    created_at: datetime
    last_health_check: Optional[datetime] = None
    health_status: str = "unknown"
    metrics: Dict[str, Any] = None
    restart_count: int = 0

class AgentDeploymentFramework:
    """Manages the complete lifecycle of TGE Swarm agents"""
    
    def __init__(self, config_path: str = "config/deployment.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        
        # Initialize clients
        self.docker_client = docker.from_env()
        self.consul_client = consul.Consul(
            host=self.config.get('consul_host', 'localhost'),
            port=self.config.get('consul_port', 8500)
        )
        
        # State management
        self.agents: Dict[str, AgentSpec] = {}
        self.instances: Dict[str, List[AgentInstance]] = {}
        self.deployment_history: List[Dict[str, Any]] = []
        
        # Event loops
        self.health_check_interval = self.config.get('health_check_interval', 30)
        self.scaling_check_interval = self.config.get('scaling_check_interval', 60)
        
        self.setup_logging()
        
    def setup_logging(self):
        """Setup deployment framework logging"""
        log_level = self.config.get('log_level', 'INFO')
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/agent-deployment.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('AgentDeploymentFramework')
        
    def _load_config(self) -> Dict[str, Any]:
        """Load deployment configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.warning(f"Config file {self.config_path} not found, using defaults")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for the deployment framework"""
        return {
            'docker_network': 'swarm-agents',
            'registry_url': 'localhost:5000',
            'health_check_interval': 30,
            'scaling_check_interval': 60,
            'max_restart_attempts': 3,
            'resource_limits': {
                'memory': '512m',
                'cpu': '0.3'
            },
            'consul_host': 'localhost',
            'consul_port': 8500,
            'redis_cluster': [
                'redis-master-1:7001',
                'redis-master-2:7002',
                'redis-master-3:7003'
            ],
            'postgres_url': 'postgresql://swarm_user:password@postgres-primary:5432/tge_swarm'
        }
    
    async def register_agent_spec(self, spec: AgentSpec) -> bool:
        """Register a new agent specification"""
        try:
            self.agents[spec.name] = spec
            self.instances[spec.name] = []
            
            # Register in service discovery
            await self._register_service(spec)
            
            self.logger.info(f"Registered agent specification: {spec.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register agent spec {spec.name}: {e}")
            return False
    
    async def deploy_agent(self, agent_name: str, force: bool = False) -> bool:
        """Deploy an agent with the specified number of replicas"""
        if agent_name not in self.agents:
            self.logger.error(f"Agent {agent_name} not found in specifications")
            return False
        
        spec = self.agents[agent_name]
        current_instances = len(self.instances[agent_name])
        
        if current_instances >= spec.replicas and not force:
            self.logger.info(f"Agent {agent_name} already has {current_instances} instances (desired: {spec.replicas})")
            return True
        
        try:
            deployment_id = f"deploy-{agent_name}-{int(time.time())}"
            self.logger.info(f"Starting deployment {deployment_id} for agent {agent_name}")
            
            # Record deployment start
            deployment_record = {
                'id': deployment_id,
                'agent_name': agent_name,
                'started_at': datetime.now(),
                'status': 'in_progress',
                'target_replicas': spec.replicas,
                'strategy': spec.deployment_strategy
            }
            self.deployment_history.append(deployment_record)
            
            if spec.deployment_strategy == "rolling":
                success = await self._rolling_deployment(spec)
            elif spec.deployment_strategy == "blue_green":
                success = await self._blue_green_deployment(spec)
            else:
                success = await self._direct_deployment(spec)
            
            # Update deployment record
            deployment_record['completed_at'] = datetime.now()
            deployment_record['status'] = 'success' if success else 'failed'
            
            return success
            
        except Exception as e:
            self.logger.error(f"Deployment failed for {agent_name}: {e}")
            return False
    
    async def _rolling_deployment(self, spec: AgentSpec) -> bool:
        """Perform rolling deployment of agent instances"""
        target_replicas = spec.replicas
        current_instances = self.instances[spec.name]
        
        # Scale up if needed
        instances_to_create = max(0, target_replicas - len(current_instances))
        
        for i in range(instances_to_create):
            instance = await self._create_instance(spec)
            if instance:
                self.instances[spec.name].append(instance)
                self.logger.info(f"Created instance {instance.id} for agent {spec.name}")
                
                # Wait for health check before proceeding
                await self._wait_for_healthy(instance)
            else:
                self.logger.error(f"Failed to create instance {i+1} for agent {spec.name}")
                return False
        
        # Scale down if needed (remove excess instances)
        while len(self.instances[spec.name]) > target_replicas:
            instance = self.instances[spec.name].pop()
            await self._terminate_instance(instance)
            self.logger.info(f"Terminated excess instance {instance.id} for agent {spec.name}")
        
        return True
    
    async def _blue_green_deployment(self, spec: AgentSpec) -> bool:
        """Perform blue-green deployment of agent instances"""
        current_instances = self.instances[spec.name].copy()
        new_instances = []
        
        try:
            # Create new instances (green)
            for i in range(spec.replicas):
                instance = await self._create_instance(spec)
                if instance:
                    new_instances.append(instance)
                    await self._wait_for_healthy(instance)
                else:
                    raise Exception(f"Failed to create new instance {i+1}")
            
            # Switch traffic to new instances
            self.instances[spec.name] = new_instances
            
            # Terminate old instances (blue)
            for instance in current_instances:
                await self._terminate_instance(instance)
            
            self.logger.info(f"Blue-green deployment completed for agent {spec.name}")
            return True
            
        except Exception as e:
            # Rollback: terminate new instances and restore old ones
            for instance in new_instances:
                await self._terminate_instance(instance)
            self.instances[spec.name] = current_instances
            
            self.logger.error(f"Blue-green deployment failed for {spec.name}: {e}")
            return False
    
    async def _direct_deployment(self, spec: AgentSpec) -> bool:
        """Perform direct deployment (all at once)"""
        # Terminate existing instances
        for instance in self.instances[spec.name]:
            await self._terminate_instance(instance)
        self.instances[spec.name] = []
        
        # Create new instances
        for i in range(spec.replicas):
            instance = await self._create_instance(spec)
            if instance:
                self.instances[spec.name].append(instance)
            else:
                self.logger.error(f"Failed to create instance {i+1} for agent {spec.name}")
                return False
        
        return True
    
    async def _create_instance(self, spec: AgentSpec) -> Optional[AgentInstance]:
        """Create a new agent instance"""
        try:
            instance_id = f"{spec.name}-{int(time.time())}-{os.urandom(4).hex()}"
            
            # Prepare container configuration
            container_config = {
                'image': spec.image,
                'name': instance_id,
                'environment': self._build_environment(spec, instance_id),
                'volumes': self._build_volumes(spec),
                'network': self.config.get('docker_network', 'swarm-agents'),
                'detach': True,
                'restart_policy': {'Name': 'unless-stopped'},
                'labels': {
                    'swarm.agent.name': spec.name,
                    'swarm.agent.type': spec.type,
                    'swarm.instance.id': instance_id,
                    'swarm.managed': 'true'
                }
            }
            
            # Apply resource limits
            if spec.resources:
                container_config['mem_limit'] = spec.resources.get('memory', '512m')
                container_config['cpu_quota'] = int(float(spec.resources.get('cpu', '0.3')) * 100000)
                container_config['cpu_period'] = 100000
            
            # Create and start container
            container = self.docker_client.containers.run(**container_config)
            
            instance = AgentInstance(
                id=instance_id,
                agent_name=spec.name,
                container_id=container.id,
                state=AgentState.DEPLOYING,
                created_at=datetime.now()
            )
            
            # Register with service discovery
            await self._register_instance(instance, spec)
            
            instance.state = AgentState.RUNNING
            self.logger.info(f"Created instance {instance_id} for agent {spec.name}")
            
            return instance
            
        except Exception as e:
            self.logger.error(f"Failed to create instance for agent {spec.name}: {e}")
            return None
    
    def _build_environment(self, spec: AgentSpec, instance_id: str) -> Dict[str, str]:
        """Build environment variables for agent container"""
        env = {
            'AGENT_TYPE': spec.type,
            'AGENT_ID': instance_id,
            'AGENT_NAME': spec.name,
            'DEPLOYMENT_TIMESTAMP': datetime.now().isoformat(),
            'POSTGRES_URL': self.config['postgres_url'],
            'REDIS_CLUSTER_URLS': ','.join(self.config['redis_cluster']),
            'CONSUL_URL': f"http://{self.config['consul_host']}:{self.config['consul_port']}",
            'LOG_LEVEL': self.config.get('log_level', 'INFO')
        }
        
        # Add spec-specific environment variables
        if spec.environment:
            env.update(spec.environment)
        
        return env
    
    def _build_volumes(self, spec: AgentSpec) -> Dict[str, Dict[str, str]]:
        """Build volume mounts for agent container"""
        volumes = {
            './logs': {'bind': '/app/logs', 'mode': 'rw'},
            './reports': {'bind': '/app/reports', 'mode': 'rw'},
            '../src': {'bind': '/app/src', 'mode': 'ro'},
            '../config.py': {'bind': '/app/config.py', 'mode': 'ro'}
        }
        
        if spec.volumes:
            for volume in spec.volumes:
                host_path, container_path, mode = volume.split(':')
                volumes[host_path] = {'bind': container_path, 'mode': mode}
        
        return volumes
    
    async def _wait_for_healthy(self, instance: AgentInstance, timeout: int = 60) -> bool:
        """Wait for instance to become healthy"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if await self._check_instance_health(instance):
                instance.health_status = "healthy"
                instance.last_health_check = datetime.now()
                return True
            
            await asyncio.sleep(5)
        
        self.logger.warning(f"Instance {instance.id} did not become healthy within {timeout}s")
        return False
    
    async def _check_instance_health(self, instance: AgentInstance) -> bool:
        """Check health of a specific instance"""
        try:
            container = self.docker_client.containers.get(instance.container_id)
            
            # Check container status
            if container.status != 'running':
                return False
            
            # Check health endpoint if configured
            spec = self.agents[instance.agent_name]
            if spec.health_check:
                # Implement custom health check logic
                return await self._custom_health_check(instance, spec.health_check)
            
            # Default: container is running
            return True
            
        except Exception as e:
            self.logger.error(f"Health check failed for instance {instance.id}: {e}")
            return False
    
    async def _custom_health_check(self, instance: AgentInstance, health_config: Dict[str, Any]) -> bool:
        """Perform custom health check based on configuration"""
        # This would implement various health check strategies
        # For now, return True as placeholder
        return True
    
    async def _terminate_instance(self, instance: AgentInstance) -> bool:
        """Terminate an agent instance"""
        try:
            instance.state = AgentState.TERMINATING
            
            # Remove from service discovery
            await self._deregister_instance(instance)
            
            # Stop and remove container
            container = self.docker_client.containers.get(instance.container_id)
            container.stop(timeout=30)
            container.remove()
            
            instance.state = AgentState.STOPPED
            self.logger.info(f"Terminated instance {instance.id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to terminate instance {instance.id}: {e}")
            instance.state = AgentState.FAILED
            return False
    
    async def _register_service(self, spec: AgentSpec) -> bool:
        """Register agent service with Consul"""
        try:
            service_definition = {
                'name': f"tge-agent-{spec.name}",
                'tags': ['swarm', 'agent', spec.type],
                'meta': {
                    'agent_type': spec.type,
                    'replicas': str(spec.replicas)
                }
            }
            
            self.consul_client.agent.service.register(**service_definition)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register service for {spec.name}: {e}")
            return False
    
    async def _register_instance(self, instance: AgentInstance, spec: AgentSpec) -> bool:
        """Register instance with service discovery"""
        try:
            # Get container IP
            container = self.docker_client.containers.get(instance.container_id)
            container.reload()
            
            networks = container.attrs['NetworkSettings']['Networks']
            network_name = self.config.get('docker_network', 'swarm-agents')
            
            if network_name in networks:
                ip_address = networks[network_name]['IPAddress']
            else:
                ip_address = list(networks.values())[0]['IPAddress']
            
            # Register with Consul
            service_id = f"tge-agent-{spec.name}-{instance.id}"
            self.consul_client.agent.service.register(
                name=f"tge-agent-{spec.name}",
                service_id=service_id,
                address=ip_address,
                port=8000,  # Default agent port
                tags=['swarm', 'agent', spec.type, instance.id],
                meta={
                    'instance_id': instance.id,
                    'container_id': instance.container_id,
                    'created_at': instance.created_at.isoformat()
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register instance {instance.id}: {e}")
            return False
    
    async def _deregister_instance(self, instance: AgentInstance) -> bool:
        """Deregister instance from service discovery"""
        try:
            service_id = f"tge-agent-{instance.agent_name}-{instance.id}"
            self.consul_client.agent.service.deregister(service_id)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to deregister instance {instance.id}: {e}")
            return False
    
    async def scale_agent(self, agent_name: str, replicas: int) -> bool:
        """Scale agent to specified number of replicas"""
        if agent_name not in self.agents:
            self.logger.error(f"Agent {agent_name} not found")
            return False
        
        spec = self.agents[agent_name]
        current_replicas = len(self.instances[agent_name])
        
        if replicas == current_replicas:
            self.logger.info(f"Agent {agent_name} already has {replicas} replicas")
            return True
        
        # Update spec
        spec.replicas = replicas
        
        # Deploy with new replica count
        return await self.deploy_agent(agent_name, force=True)
    
    async def start_health_monitoring(self):
        """Start continuous health monitoring of all instances"""
        while True:
            try:
                for agent_name, instances in self.instances.items():
                    for instance in instances:
                        if instance.state == AgentState.RUNNING:
                            is_healthy = await self._check_instance_health(instance)
                            
                            if is_healthy:
                                instance.health_status = "healthy"
                                instance.last_health_check = datetime.now()
                            else:
                                instance.health_status = "unhealthy"
                                instance.state = AgentState.UNHEALTHY
                                
                                # Attempt restart if within limits
                                if instance.restart_count < self.config.get('max_restart_attempts', 3):
                                    await self._restart_instance(instance)
                                else:
                                    self.logger.error(f"Instance {instance.id} exceeded restart limit")
                                    instance.state = AgentState.FAILED
                
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                self.logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(30)
    
    async def _restart_instance(self, instance: AgentInstance) -> bool:
        """Restart a failed instance"""
        try:
            instance.restart_count += 1
            self.logger.info(f"Restarting instance {instance.id} (attempt {instance.restart_count})")
            
            container = self.docker_client.containers.get(instance.container_id)
            container.restart(timeout=30)
            
            # Wait for health check
            if await self._wait_for_healthy(instance):
                instance.state = AgentState.RUNNING
                return True
            else:
                instance.state = AgentState.FAILED
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to restart instance {instance.id}: {e}")
            instance.state = AgentState.FAILED
            return False
    
    def get_deployment_status(self) -> Dict[str, Any]:
        """Get current deployment status"""
        status = {
            'agents': {},
            'total_instances': 0,
            'healthy_instances': 0,
            'unhealthy_instances': 0,
            'recent_deployments': self.deployment_history[-10:]
        }
        
        for agent_name, instances in self.instances.items():
            agent_status = {
                'spec': asdict(self.agents[agent_name]),
                'instances': [],
                'desired_replicas': self.agents[agent_name].replicas,
                'actual_replicas': len(instances),
                'healthy_replicas': 0
            }
            
            for instance in instances:
                instance_info = {
                    'id': instance.id,
                    'state': instance.state.value,
                    'health_status': instance.health_status,
                    'created_at': instance.created_at.isoformat(),
                    'last_health_check': instance.last_health_check.isoformat() if instance.last_health_check else None,
                    'restart_count': instance.restart_count
                }
                
                agent_status['instances'].append(instance_info)
                status['total_instances'] += 1
                
                if instance.health_status == "healthy":
                    agent_status['healthy_replicas'] += 1
                    status['healthy_instances'] += 1
                else:
                    status['unhealthy_instances'] += 1
            
            status['agents'][agent_name] = agent_status
        
        return status

# CLI Interface
if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description='TGE Swarm Agent Deployment Framework')
    parser.add_argument('command', choices=['deploy', 'scale', 'status', 'monitor', 'terminate'])
    parser.add_argument('--agent', help='Agent name')
    parser.add_argument('--replicas', type=int, help='Number of replicas')
    parser.add_argument('--config', default='config/deployment.yaml', help='Config file path')
    
    args = parser.parse_args()
    
    framework = AgentDeploymentFramework(args.config)
    
    async def main():
        if args.command == 'status':
            status = framework.get_deployment_status()
            print(json.dumps(status, indent=2))
        
        elif args.command == 'deploy' and args.agent:
            # Load agent specs from config
            # This would typically load from a specification file
            success = await framework.deploy_agent(args.agent)
            print(f"Deployment {'successful' if success else 'failed'}")
        
        elif args.command == 'scale' and args.agent and args.replicas:
            success = await framework.scale_agent(args.agent, args.replicas)
            print(f"Scaling {'successful' if success else 'failed'}")
        
        elif args.command == 'monitor':
            print("Starting health monitoring...")
            await framework.start_health_monitoring()
        
        else:
            parser.print_help()
    
    asyncio.run(main())