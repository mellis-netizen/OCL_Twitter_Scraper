#!/usr/bin/env python3
"""
TGE Swarm Health Monitor and Auto-Recovery System
Comprehensive health monitoring with intelligent recovery mechanisms
"""

import asyncio
import aiohttp
import docker
import json
import logging
import os
import time
import consul
import redis.asyncio as redis
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
import psutil
import asyncpg

class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

class RecoveryAction(Enum):
    NONE = "none"
    RESTART = "restart"
    RECREATE = "recreate"
    SCALE_UP = "scale_up"
    FAILOVER = "failover"
    ALERT_ONLY = "alert_only"

@dataclass
class HealthCheck:
    name: str
    check_type: str
    endpoint: Optional[str] = None
    expected_status: int = 200
    timeout: int = 10
    interval: int = 30
    failure_threshold: int = 3
    success_threshold: int = 1
    recovery_action: RecoveryAction = RecoveryAction.RESTART

@dataclass
class HealthResult:
    check_name: str
    status: HealthStatus
    timestamp: datetime
    response_time: float
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = None

@dataclass
class ComponentHealth:
    component_name: str
    overall_status: HealthStatus
    checks: List[HealthResult]
    last_recovery_attempt: Optional[datetime] = None
    recovery_count: int = 0
    failure_streak: int = 0

class HealthMonitor:
    """Advanced health monitoring system with auto-recovery capabilities"""
    
    def __init__(self, config_path: str = "config/health.yaml"):
        self.config = self._load_config(config_path)
        self.docker_client = docker.from_env()
        self.consul_client = consul.Consul(
            host=self.config.get('consul_host', 'localhost'),
            port=self.config.get('consul_port', 8500)
        )
        
        # Health state management
        self.component_health: Dict[str, ComponentHealth] = {}
        self.recovery_history: List[Dict[str, Any]] = []
        self.health_checks: Dict[str, List[HealthCheck]] = {}
        
        # Recovery settings
        self.max_recovery_attempts = self.config.get('max_recovery_attempts', 3)
        self.recovery_cooldown = self.config.get('recovery_cooldown', 300)  # 5 minutes
        self.circuit_breaker_threshold = self.config.get('circuit_breaker_threshold', 5)
        
        self.setup_logging()
        self._initialize_health_checks()
        
    def setup_logging(self):
        """Setup health monitor logging"""
        log_level = self.config.get('log_level', 'INFO')
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/health-monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('HealthMonitor')
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load health monitoring configuration"""
        try:
            import yaml
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.warning(f"Config file {config_path} not found, using defaults")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default health monitoring configuration"""
        return {
            'consul_host': 'localhost',
            'consul_port': 8500,
            'redis_cluster': [
                'redis-master-1:7001',
                'redis-master-2:7002', 
                'redis-master-3:7003'
            ],
            'postgres_url': 'postgresql://swarm_user:password@postgres-primary:5432/tge_swarm',
            'max_recovery_attempts': 3,
            'recovery_cooldown': 300,
            'circuit_breaker_threshold': 5,
            'notification_channels': ['console', 'webhook'],
            'webhook_url': None,
            'log_level': 'INFO'
        }
    
    def _initialize_health_checks(self):
        """Initialize health checks for all components"""
        
        # Swarm Queen health checks
        self.health_checks['swarm-queen'] = [
            HealthCheck(
                name="api_health",
                check_type="http",
                endpoint="http://swarm-queen:8080/health",
                interval=30,
                recovery_action=RecoveryAction.RESTART
            ),
            HealthCheck(
                name="metrics_endpoint",
                check_type="http",
                endpoint="http://swarm-queen:8001/metrics",
                interval=60,
                recovery_action=RecoveryAction.ALERT_ONLY
            )
        ]
        
        # Memory Coordinator health checks
        self.health_checks['memory-coordinator'] = [
            HealthCheck(
                name="coordinator_health",
                check_type="http",
                endpoint="http://swarm-memory-coordinator:8002/health",
                interval=30,
                recovery_action=RecoveryAction.RESTART
            )
        ]
        
        # Agent health checks (dynamic based on service discovery)
        self.health_checks['agents'] = [
            HealthCheck(
                name="agent_health",
                check_type="consul_service",
                interval=30,
                recovery_action=RecoveryAction.RECREATE
            )
        ]
        
        # Infrastructure health checks
        self.health_checks['postgres'] = [
            HealthCheck(
                name="postgres_connection",
                check_type="postgres",
                interval=60,
                recovery_action=RecoveryAction.ALERT_ONLY
            )
        ]
        
        self.health_checks['redis'] = [
            HealthCheck(
                name="redis_cluster",
                check_type="redis",
                interval=30,
                recovery_action=RecoveryAction.ALERT_ONLY
            )
        ]
        
        self.health_checks['consul'] = [
            HealthCheck(
                name="consul_health",
                check_type="http",
                endpoint="http://consul:8500/v1/status/leader",
                interval=30,
                recovery_action=RecoveryAction.ALERT_ONLY
            )
        ]
    
    async def start_monitoring(self):
        """Start continuous health monitoring"""
        self.logger.info("Starting TGE Swarm health monitoring...")
        
        # Start monitoring tasks for each component
        tasks = []
        for component_name, checks in self.health_checks.items():
            task = asyncio.create_task(
                self._monitor_component(component_name, checks)
            )
            tasks.append(task)
        
        # Start recovery processor
        tasks.append(asyncio.create_task(self._process_recovery_queue()))
        
        # Start health metrics reporter
        tasks.append(asyncio.create_task(self._report_health_metrics()))
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            self.logger.error(f"Health monitoring error: {e}")
            raise
    
    async def _monitor_component(self, component_name: str, checks: List[HealthCheck]):
        """Monitor a specific component continuously"""
        while True:
            try:
                component_results = []
                
                for check in checks:
                    result = await self._execute_health_check(check)
                    component_results.append(result)
                    
                    # Log check result
                    if result.status != HealthStatus.HEALTHY:
                        self.logger.warning(
                            f"Health check failed: {component_name}.{check.name} - {result.error_message}"
                        )
                
                # Update component health
                await self._update_component_health(component_name, component_results)
                
                # Determine next check interval (minimum of all checks)
                next_interval = min(check.interval for check in checks)
                await asyncio.sleep(next_interval)
                
            except Exception as e:
                self.logger.error(f"Error monitoring component {component_name}: {e}")
                await asyncio.sleep(30)  # Fallback interval
    
    async def _execute_health_check(self, check: HealthCheck) -> HealthResult:
        """Execute a specific health check"""
        start_time = time.time()
        
        try:
            if check.check_type == "http":
                return await self._http_health_check(check, start_time)
            elif check.check_type == "postgres":
                return await self._postgres_health_check(check, start_time)
            elif check.check_type == "redis":
                return await self._redis_health_check(check, start_time)
            elif check.check_type == "consul_service":
                return await self._consul_service_check(check, start_time)
            elif check.check_type == "docker":
                return await self._docker_health_check(check, start_time)
            else:
                return HealthResult(
                    check_name=check.name,
                    status=HealthStatus.UNKNOWN,
                    timestamp=datetime.now(),
                    response_time=0.0,
                    error_message=f"Unknown check type: {check.check_type}"
                )
                
        except Exception as e:
            response_time = time.time() - start_time
            return HealthResult(
                check_name=check.name,
                status=HealthStatus.CRITICAL,
                timestamp=datetime.now(),
                response_time=response_time,
                error_message=str(e)
            )
    
    async def _http_health_check(self, check: HealthCheck, start_time: float) -> HealthResult:
        """Execute HTTP health check"""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=check.timeout)) as session:
            try:
                async with session.get(check.endpoint) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == check.expected_status:
                        status = HealthStatus.HEALTHY
                        error_message = None
                    else:
                        status = HealthStatus.CRITICAL
                        error_message = f"HTTP {response.status} (expected {check.expected_status})"
                    
                    # Try to get response metrics
                    metrics = {}
                    try:
                        if 'json' in response.headers.get('content-type', ''):
                            response_data = await response.json()
                            if isinstance(response_data, dict):
                                metrics = response_data
                    except:
                        pass
                    
                    return HealthResult(
                        check_name=check.name,
                        status=status,
                        timestamp=datetime.now(),
                        response_time=response_time,
                        error_message=error_message,
                        metrics=metrics
                    )
                    
            except asyncio.TimeoutError:
                response_time = time.time() - start_time
                return HealthResult(
                    check_name=check.name,
                    status=HealthStatus.CRITICAL,
                    timestamp=datetime.now(),
                    response_time=response_time,
                    error_message=f"Timeout after {check.timeout}s"
                )
    
    async def _postgres_health_check(self, check: HealthCheck, start_time: float) -> HealthResult:
        """Execute PostgreSQL health check"""
        try:
            conn = await asyncpg.connect(self.config['postgres_url'])
            
            # Test basic connectivity and get metrics
            result = await conn.fetch("SELECT version(), pg_database_size(current_database()) as db_size")
            await conn.execute("SELECT 1")  # Simple query test
            
            await conn.close()
            
            response_time = time.time() - start_time
            
            metrics = {
                'database_size': result[0]['db_size'] if result else 0,
                'connection_time': response_time
            }
            
            return HealthResult(
                check_name=check.name,
                status=HealthStatus.HEALTHY,
                timestamp=datetime.now(),
                response_time=response_time,
                metrics=metrics
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return HealthResult(
                check_name=check.name,
                status=HealthStatus.CRITICAL,
                timestamp=datetime.now(),
                response_time=response_time,
                error_message=str(e)
            )
    
    async def _redis_health_check(self, check: HealthCheck, start_time: float) -> HealthResult:
        """Execute Redis cluster health check"""
        healthy_nodes = 0
        total_nodes = len(self.config['redis_cluster'])
        errors = []
        
        for node_url in self.config['redis_cluster']:
            try:
                host, port = node_url.split(':')
                r = redis.Redis(host=host, port=int(port), decode_responses=True)
                
                # Test connectivity and get info
                await r.ping()
                info = await r.info()
                
                healthy_nodes += 1
                await r.close()
                
            except Exception as e:
                errors.append(f"{node_url}: {str(e)}")
        
        response_time = time.time() - start_time
        
        if healthy_nodes == total_nodes:
            status = HealthStatus.HEALTHY
            error_message = None
        elif healthy_nodes > 0:
            status = HealthStatus.WARNING
            error_message = f"Only {healthy_nodes}/{total_nodes} nodes healthy"
        else:
            status = HealthStatus.CRITICAL
            error_message = f"All nodes down: {'; '.join(errors)}"
        
        metrics = {
            'healthy_nodes': healthy_nodes,
            'total_nodes': total_nodes,
            'cluster_health_percentage': (healthy_nodes / total_nodes) * 100
        }
        
        return HealthResult(
            check_name=check.name,
            status=status,
            timestamp=datetime.now(),
            response_time=response_time,
            error_message=error_message,
            metrics=metrics
        )
    
    async def _consul_service_check(self, check: HealthCheck, start_time: float) -> HealthResult:
        """Check agent health via Consul service discovery"""
        try:
            services = self.consul_client.health.service('tge-agent', passing=True)[1]
            total_agents = len(self.consul_client.agent.services()[1])
            healthy_agents = len(services)
            
            response_time = time.time() - start_time
            
            if healthy_agents == total_agents and total_agents > 0:
                status = HealthStatus.HEALTHY
                error_message = None
            elif healthy_agents > 0:
                status = HealthStatus.WARNING
                error_message = f"Only {healthy_agents}/{total_agents} agents healthy"
            else:
                status = HealthStatus.CRITICAL
                error_message = "No healthy agents found"
            
            metrics = {
                'healthy_agents': healthy_agents,
                'total_agents': total_agents,
                'agent_health_percentage': (healthy_agents / max(total_agents, 1)) * 100
            }
            
            return HealthResult(
                check_name=check.name,
                status=status,
                timestamp=datetime.now(),
                response_time=response_time,
                error_message=error_message,
                metrics=metrics
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return HealthResult(
                check_name=check.name,
                status=HealthStatus.CRITICAL,
                timestamp=datetime.now(),
                response_time=response_time,
                error_message=str(e)
            )
    
    async def _docker_health_check(self, check: HealthCheck, start_time: float) -> HealthResult:
        """Check Docker container health"""
        try:
            containers = self.docker_client.containers.list(
                filters={'label': 'swarm.managed=true'}
            )
            
            healthy_containers = 0
            total_containers = len(containers)
            
            for container in containers:
                if container.status == 'running':
                    # Check if container has health check
                    if container.attrs.get('State', {}).get('Health'):
                        health_status = container.attrs['State']['Health']['Status']
                        if health_status == 'healthy':
                            healthy_containers += 1
                    else:
                        # No health check defined, assume healthy if running
                        healthy_containers += 1
            
            response_time = time.time() - start_time
            
            if healthy_containers == total_containers and total_containers > 0:
                status = HealthStatus.HEALTHY
                error_message = None
            elif healthy_containers > 0:
                status = HealthStatus.WARNING
                error_message = f"Only {healthy_containers}/{total_containers} containers healthy"
            else:
                status = HealthStatus.CRITICAL
                error_message = "No healthy containers found"
            
            metrics = {
                'healthy_containers': healthy_containers,
                'total_containers': total_containers,
                'container_health_percentage': (healthy_containers / max(total_containers, 1)) * 100
            }
            
            return HealthResult(
                check_name=check.name,
                status=status,
                timestamp=datetime.now(),
                response_time=response_time,
                error_message=error_message,
                metrics=metrics
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return HealthResult(
                check_name=check.name,
                status=HealthStatus.CRITICAL,
                timestamp=datetime.now(),
                response_time=response_time,
                error_message=str(e)
            )
    
    async def _update_component_health(self, component_name: str, results: List[HealthResult]):
        """Update component health status and trigger recovery if needed"""
        # Determine overall component status
        statuses = [result.status for result in results]
        
        if HealthStatus.CRITICAL in statuses:
            overall_status = HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            overall_status = HealthStatus.WARNING
        elif HealthStatus.HEALTHY in statuses:
            overall_status = HealthStatus.HEALTHY
        else:
            overall_status = HealthStatus.UNKNOWN
        
        # Update or create component health record
        if component_name not in self.component_health:
            self.component_health[component_name] = ComponentHealth(
                component_name=component_name,
                overall_status=overall_status,
                checks=results
            )
        else:
            component = self.component_health[component_name]
            previous_status = component.overall_status
            
            component.overall_status = overall_status
            component.checks = results
            
            # Update failure streak
            if overall_status != HealthStatus.HEALTHY:
                component.failure_streak += 1
            else:
                component.failure_streak = 0
            
            # Trigger recovery if conditions are met
            if self._should_trigger_recovery(component, previous_status):
                await self._trigger_recovery(component)
    
    def _should_trigger_recovery(self, component: ComponentHealth, previous_status: HealthStatus) -> bool:
        """Determine if recovery should be triggered"""
        # Don't recover if recently attempted
        if component.last_recovery_attempt:
            time_since_recovery = datetime.now() - component.last_recovery_attempt
            if time_since_recovery.total_seconds() < self.recovery_cooldown:
                return False
        
        # Don't recover if too many attempts
        if component.recovery_count >= self.max_recovery_attempts:
            return False
        
        # Trigger on critical status or sustained warnings
        if component.overall_status == HealthStatus.CRITICAL:
            return True
        
        if component.overall_status == HealthStatus.WARNING and component.failure_streak >= 3:
            return True
        
        return False
    
    async def _trigger_recovery(self, component: ComponentHealth):
        """Trigger recovery action for a component"""
        self.logger.warning(f"Triggering recovery for component: {component.component_name}")
        
        # Find the most severe recovery action needed
        recovery_actions = []
        for check_result in component.checks:
            if check_result.status != HealthStatus.HEALTHY:
                # Find corresponding check config
                for check in self.health_checks.get(component.component_name, []):
                    if check.name == check_result.check_name:
                        recovery_actions.append(check.recovery_action)
                        break
        
        # Select most severe action
        action_priority = {
            RecoveryAction.NONE: 0,
            RecoveryAction.ALERT_ONLY: 1,
            RecoveryAction.RESTART: 2,
            RecoveryAction.RECREATE: 3,
            RecoveryAction.SCALE_UP: 4,
            RecoveryAction.FAILOVER: 5
        }
        
        if recovery_actions:
            action = max(recovery_actions, key=lambda x: action_priority[x])
            success = await self._execute_recovery_action(component, action)
            
            # Update recovery tracking
            component.last_recovery_attempt = datetime.now()
            component.recovery_count += 1
            
            # Record recovery attempt
            self.recovery_history.append({
                'timestamp': datetime.now().isoformat(),
                'component': component.component_name,
                'action': action.value,
                'success': success,
                'attempt_number': component.recovery_count
            })
    
    async def _execute_recovery_action(self, component: ComponentHealth, action: RecoveryAction) -> bool:
        """Execute specific recovery action"""
        try:
            if action == RecoveryAction.ALERT_ONLY:
                await self._send_alert(component, action)
                return True
            
            elif action == RecoveryAction.RESTART:
                return await self._restart_component(component)
            
            elif action == RecoveryAction.RECREATE:
                return await self._recreate_component(component)
            
            elif action == RecoveryAction.SCALE_UP:
                return await self._scale_up_component(component)
            
            elif action == RecoveryAction.FAILOVER:
                return await self._failover_component(component)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Recovery action {action.value} failed for {component.component_name}: {e}")
            return False
    
    async def _restart_component(self, component: ComponentHealth) -> bool:
        """Restart component containers"""
        try:
            containers = self.docker_client.containers.list(
                filters={
                    'label': f'swarm.component={component.component_name}',
                    'status': 'running'
                }
            )
            
            for container in containers:
                self.logger.info(f"Restarting container: {container.name}")
                container.restart(timeout=30)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restart {component.component_name}: {e}")
            return False
    
    async def _recreate_component(self, component: ComponentHealth) -> bool:
        """Recreate component containers"""
        # This would integrate with the deployment framework
        self.logger.info(f"Recreating component: {component.component_name}")
        # TODO: Integrate with AgentDeploymentFramework
        return True
    
    async def _scale_up_component(self, component: ComponentHealth) -> bool:
        """Scale up component"""
        self.logger.info(f"Scaling up component: {component.component_name}")
        # TODO: Implement scaling logic
        return True
    
    async def _failover_component(self, component: ComponentHealth) -> bool:
        """Failover component to backup"""
        self.logger.info(f"Failing over component: {component.component_name}")
        # TODO: Implement failover logic
        return True
    
    async def _send_alert(self, component: ComponentHealth, action: RecoveryAction):
        """Send alert notifications"""
        alert_data = {
            'timestamp': datetime.now().isoformat(),
            'component': component.component_name,
            'status': component.overall_status.value,
            'action': action.value,
            'failure_streak': component.failure_streak,
            'recovery_count': component.recovery_count,
            'checks': [asdict(check) for check in component.checks]
        }
        
        # Console alert
        if 'console' in self.config.get('notification_channels', []):
            self.logger.error(f"ALERT: {component.component_name} is {component.overall_status.value}")
        
        # Webhook alert
        if 'webhook' in self.config.get('notification_channels', []) and self.config.get('webhook_url'):
            try:
                async with aiohttp.ClientSession() as session:
                    await session.post(self.config['webhook_url'], json=alert_data)
            except Exception as e:
                self.logger.error(f"Failed to send webhook alert: {e}")
    
    async def _process_recovery_queue(self):
        """Process recovery actions queue"""
        while True:
            try:
                # This could be enhanced with a proper queue system
                await asyncio.sleep(10)
            except Exception as e:
                self.logger.error(f"Recovery queue processing error: {e}")
                await asyncio.sleep(30)
    
    async def _report_health_metrics(self):
        """Report health metrics to monitoring system"""
        while True:
            try:
                # TODO: Send metrics to Prometheus pushgateway or Redis
                await asyncio.sleep(60)
            except Exception as e:
                self.logger.error(f"Health metrics reporting error: {e}")
                await asyncio.sleep(60)
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary"""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'overall_health': 'healthy',
            'components': {},
            'recovery_stats': {
                'total_recoveries': len(self.recovery_history),
                'successful_recoveries': len([r for r in self.recovery_history if r['success']]),
                'recent_recoveries': len([r for r in self.recovery_history 
                                        if datetime.fromisoformat(r['timestamp']) > datetime.now() - timedelta(hours=24)])
            }
        }
        
        critical_components = 0
        warning_components = 0
        
        for component_name, component in self.component_health.items():
            component_summary = {
                'status': component.overall_status.value,
                'failure_streak': component.failure_streak,
                'recovery_count': component.recovery_count,
                'last_recovery': component.last_recovery_attempt.isoformat() if component.last_recovery_attempt else None,
                'checks': {}
            }
            
            for check in component.checks:
                component_summary['checks'][check.check_name] = {
                    'status': check.status.value,
                    'response_time': check.response_time,
                    'error': check.error_message,
                    'timestamp': check.timestamp.isoformat()
                }
            
            summary['components'][component_name] = component_summary
            
            if component.overall_status == HealthStatus.CRITICAL:
                critical_components += 1
            elif component.overall_status == HealthStatus.WARNING:
                warning_components += 1
        
        # Determine overall health
        if critical_components > 0:
            summary['overall_health'] = 'critical'
        elif warning_components > 0:
            summary['overall_health'] = 'warning'
        else:
            summary['overall_health'] = 'healthy'
        
        return summary

# CLI Interface
if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description='TGE Swarm Health Monitor')
    parser.add_argument('command', choices=['start', 'status', 'check'], 
                       help='Command to execute')
    parser.add_argument('--config', default='config/health.yaml', 
                       help='Configuration file path')
    parser.add_argument('--component', help='Specific component to check')
    
    args = parser.parse_args()
    
    monitor = HealthMonitor(args.config)
    
    async def main():
        if args.command == 'start':
            await monitor.start_monitoring()
        
        elif args.command == 'status':
            summary = monitor.get_health_summary()
            print(json.dumps(summary, indent=2))
        
        elif args.command == 'check' and args.component:
            if args.component in monitor.health_checks:
                checks = monitor.health_checks[args.component]
                results = []
                for check in checks:
                    result = await monitor._execute_health_check(check)
                    results.append(asdict(result))
                
                print(json.dumps(results, indent=2))
            else:
                print(f"Unknown component: {args.component}")
                sys.exit(1)
    
    asyncio.run(main())