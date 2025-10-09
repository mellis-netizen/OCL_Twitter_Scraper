#!/usr/bin/env python3
"""
TGE Swarm Backend Service Orchestrator
Main entry point for all backend services with integrated coordination
"""

import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import yaml

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from backend.message_queue import create_message_queue, MessageQueue
from backend.agent_manager import AgentManager, AgentManagerAPI
from backend.coordination_service import CoordinationService
from backend.task_orchestrator import TaskOrchestrator
from backend.websocket_manager import EnhancedDashboardAPIServer
from backend.optimization_engine import OptimizationEngine
from swarm_memory_coordinator import SwarmMemoryCoordinator


class SwarmBackend:
    """Main backend service orchestrator for TGE Swarm"""
    
    def __init__(self, config_file: str = "config/swarm_backend.yaml"):
        self.config = self._load_config(config_file)
        self.running = False
        
        # Core services
        self.message_queue: Optional[MessageQueue] = None
        self.memory_coordinator: Optional[SwarmMemoryCoordinator] = None
        self.coordination_service: Optional[CoordinationService] = None
        self.agent_manager: Optional[AgentManager] = None
        self.task_orchestrator: Optional[TaskOrchestrator] = None
        self.optimization_engine: Optional[OptimizationEngine] = None
        self.dashboard_server: Optional[EnhancedDashboardAPIServer] = None
        
        # Service health tracking
        self.service_health = {}
        self.startup_sequence = [
            'message_queue',
            'memory_coordinator', 
            'coordination_service',
            'agent_manager',
            'task_orchestrator',
            'optimization_engine',
            'dashboard_server'
        ]
        
        self.setup_logging()
        self.setup_signal_handlers()
    
    def setup_logging(self):
        """Setup comprehensive logging"""
        log_level = self.config.get('log_level', 'INFO')
        log_dir = Path(self.config.get('log_dir', './logs'))
        log_dir.mkdir(exist_ok=True, parents=True)
        
        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / 'swarm_backend.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger('SwarmBackend')
        self.logger.info("Swarm Backend logging initialized")
    
    def setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load backend configuration"""
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    return yaml.safe_load(f)
            else:
                self.logger.warning(f"Config file {config_file} not found, using defaults")
                return self._default_config()
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default backend configuration"""
        return {
            'log_level': 'INFO',
            'log_dir': './logs',
            'redis_cluster': [
                'localhost:6379'
            ],
            'message_queue': {
                'cluster_name': 'tge-swarm'
            },
            'coordination_service': {
                'redis_url': 'redis://localhost:6379',
                'sync_interval': 90,
                'resource_lock_timeout': 300
            },
            'agent_manager': {
                'config_file': 'config/agent_manager.yaml',
                'max_agents_per_type': 5,
                'health_check_interval': 30
            },
            'task_orchestrator': {
                'scheduling_strategy': 'adaptive',
                'max_concurrent_tasks_per_agent': 3,
                'task_timeout_seconds': 300
            },
            'optimization_engine': {
                'project_root': '../',
                'auto_apply_low_risk': False,
                'require_approval_threshold': 'medium'
            },
            'dashboard_server': {
                'host': 'localhost',
                'port': 8080
            },
            'health_monitoring': {
                'check_interval': 30,
                'restart_failed_services': True,
                'max_restart_attempts': 3
            }
        }
    
    async def initialize(self):
        """Initialize all backend services"""
        self.logger.info("Starting TGE Swarm Backend initialization...")
        
        try:
            # Initialize services in dependency order
            for service_name in self.startup_sequence:
                self.logger.info(f"Initializing {service_name}...")
                
                success = await self._initialize_service(service_name)
                
                if success:
                    self.service_health[service_name] = {
                        'status': 'healthy',
                        'initialized_at': datetime.now().isoformat(),
                        'restart_count': 0
                    }
                    self.logger.info(f"✓ {service_name} initialized successfully")
                else:
                    self.service_health[service_name] = {
                        'status': 'failed',
                        'initialized_at': datetime.now().isoformat(),
                        'restart_count': 0
                    }
                    self.logger.error(f"✗ {service_name} initialization failed")
                    
                    # Decide if we should continue or fail
                    if service_name in ['message_queue', 'memory_coordinator']:
                        raise Exception(f"Critical service {service_name} failed to initialize")
            
            self.running = True
            self.logger.info("🚀 TGE Swarm Backend fully initialized")
            
            # Start health monitoring
            asyncio.create_task(self._health_monitoring_loop())
            
            return True
            
        except Exception as e:
            self.logger.error(f"Backend initialization failed: {e}")
            await self.shutdown()
            return False
    
    async def _initialize_service(self, service_name: str) -> bool:
        """Initialize individual service"""
        try:
            if service_name == 'message_queue':
                self.message_queue = await create_message_queue(
                    self.config['redis_cluster'],
                    self.config['message_queue']['cluster_name']
                )
                return True
            
            elif service_name == 'memory_coordinator':
                memory_path = self.config.get('memory_path', './safla-memory')
                self.memory_coordinator = SwarmMemoryCoordinator(memory_path)
                return True
            
            elif service_name == 'coordination_service':
                if not self.memory_coordinator or not self.message_queue:
                    return False
                
                self.coordination_service = CoordinationService(
                    self.memory_coordinator,
                    self.message_queue,
                    self.config['coordination_service']['redis_url']
                )
                await self.coordination_service.initialize()
                return True
            
            elif service_name == 'agent_manager':
                if not self.message_queue:
                    return False
                
                self.agent_manager = AgentManager(
                    self.config['agent_manager']['config_file']
                )
                await self.agent_manager.initialize(self.message_queue)
                return True
            
            elif service_name == 'task_orchestrator':
                if not self.message_queue or not self.agent_manager:
                    return False
                
                self.task_orchestrator = TaskOrchestrator(
                    self.message_queue,
                    self.agent_manager,
                    self.config['task_orchestrator']
                )
                await self.task_orchestrator.initialize()
                return True
            
            elif service_name == 'optimization_engine':
                if not all([self.message_queue, self.coordination_service]):
                    return False
                
                self.optimization_engine = OptimizationEngine(
                    self.message_queue,
                    self.coordination_service,
                    None,  # WebSocket manager will be set later
                    self.config['optimization_engine']
                )
                await self.optimization_engine.initialize()
                return True
            
            elif service_name == 'dashboard_server':
                self.dashboard_server = EnhancedDashboardAPIServer(
                    host=self.config['dashboard_server']['host'],
                    port=self.config['dashboard_server']['port'],
                    message_queue=self.message_queue,
                    agent_manager=self.agent_manager,
                    task_orchestrator=self.task_orchestrator,
                    coordination_service=self.coordination_service
                )
                
                # Link optimization engine to websocket manager
                if self.optimization_engine:
                    self.optimization_engine.websocket_manager = self.dashboard_server.websocket_manager
                
                await self.dashboard_server.start_server()
                return True
            
            else:
                self.logger.error(f"Unknown service: {service_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to initialize {service_name}: {e}")
            return False
    
    async def start(self):
        """Start the backend services"""
        if not await self.initialize():
            return False
        
        self.logger.info("TGE Swarm Backend is running...")
        self.logger.info(f"Dashboard available at: http://{self.config['dashboard_server']['host']}:{self.config['dashboard_server']['port']}")
        self.logger.info(f"WebSocket endpoint: ws://{self.config['dashboard_server']['host']}:{self.config['dashboard_server']['port']}/ws")
        
        # Keep running until shutdown
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        finally:
            await self.shutdown()
        
        return True
    
    async def _health_monitoring_loop(self):
        """Monitor service health and restart failed services if configured"""
        check_interval = self.config['health_monitoring']['check_interval']
        restart_failed = self.config['health_monitoring']['restart_failed_services']
        max_restarts = self.config['health_monitoring']['max_restart_attempts']
        
        while self.running:
            try:
                await asyncio.sleep(check_interval)
                
                for service_name in self.startup_sequence:
                    if service_name not in self.service_health:
                        continue
                    
                    service_info = self.service_health[service_name]
                    
                    # Check service health
                    is_healthy = await self._check_service_health(service_name)
                    
                    if not is_healthy and service_info['status'] == 'healthy':
                        # Service just failed
                        service_info['status'] = 'failed'
                        self.logger.error(f"Service {service_name} failed health check")
                        
                        # Attempt restart if configured and within limits
                        if (restart_failed and 
                            service_info['restart_count'] < max_restarts):
                            
                            self.logger.info(f"Attempting to restart {service_name}...")
                            
                            restart_success = await self._restart_service(service_name)
                            service_info['restart_count'] += 1
                            
                            if restart_success:
                                service_info['status'] = 'healthy'
                                self.logger.info(f"Successfully restarted {service_name}")
                            else:
                                self.logger.error(f"Failed to restart {service_name}")
                    
                    elif is_healthy and service_info['status'] == 'failed':
                        # Service recovered
                        service_info['status'] = 'healthy'
                        self.logger.info(f"Service {service_name} recovered")
                
            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(30)
    
    async def _check_service_health(self, service_name: str) -> bool:
        """Check if a service is healthy"""
        try:
            if service_name == 'message_queue':
                return self.message_queue is not None
            
            elif service_name == 'memory_coordinator':
                return self.memory_coordinator is not None
            
            elif service_name == 'coordination_service':
                return (self.coordination_service is not None and 
                       self.coordination_service.running)
            
            elif service_name == 'agent_manager':
                return (self.agent_manager is not None and 
                       self.agent_manager.running)
            
            elif service_name == 'task_orchestrator':
                return (self.task_orchestrator is not None and 
                       self.task_orchestrator.running)
            
            elif service_name == 'optimization_engine':
                return (self.optimization_engine is not None and 
                       self.optimization_engine.running)
            
            elif service_name == 'dashboard_server':
                return (self.dashboard_server is not None and 
                       self.dashboard_server.websocket_manager.running)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking health of {service_name}: {e}")
            return False
    
    async def _restart_service(self, service_name: str) -> bool:
        """Attempt to restart a failed service"""
        try:
            self.logger.info(f"Restarting service: {service_name}")
            
            # Stop the service first
            await self._stop_service(service_name)
            
            # Wait a moment
            await asyncio.sleep(2)
            
            # Reinitialize the service
            success = await self._initialize_service(service_name)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error restarting {service_name}: {e}")
            return False
    
    async def _stop_service(self, service_name: str):
        """Stop a specific service"""
        try:
            if service_name == 'coordination_service' and self.coordination_service:
                await self.coordination_service.shutdown()
                self.coordination_service = None
            
            elif service_name == 'agent_manager' and self.agent_manager:
                await self.agent_manager.shutdown()
                self.agent_manager = None
            
            elif service_name == 'task_orchestrator' and self.task_orchestrator:
                await self.task_orchestrator.shutdown()
                self.task_orchestrator = None
            
            elif service_name == 'optimization_engine' and self.optimization_engine:
                await self.optimization_engine.shutdown()
                self.optimization_engine = None
            
            elif service_name == 'dashboard_server' and self.dashboard_server:
                await self.dashboard_server.shutdown()
                self.dashboard_server = None
            
        except Exception as e:
            self.logger.error(f"Error stopping {service_name}: {e}")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'running': self.running,
            'services': {},
            'metrics': {}
        }
        
        # Service health
        for service_name in self.startup_sequence:
            if service_name in self.service_health:
                service_info = self.service_health[service_name].copy()
                service_info['healthy'] = await self._check_service_health(service_name)
                status['services'][service_name] = service_info
        
        # Collect metrics from services
        try:
            if self.agent_manager:
                status['metrics']['agents'] = await self.agent_manager.get_agent_status()
            
            if self.task_orchestrator:
                status['metrics']['tasks'] = await self.task_orchestrator.get_queue_status()
                status['metrics']['workloads'] = await self.task_orchestrator.get_agent_workloads()
            
            if self.coordination_service:
                status['metrics']['coordination'] = await self.coordination_service.get_coordination_status()
            
            if self.optimization_engine:
                status['metrics']['optimization'] = await self.optimization_engine.get_optimization_status()
            
            if self.message_queue:
                status['metrics']['message_queue'] = await self.message_queue.get_task_statistics()
            
            if self.dashboard_server and self.dashboard_server.websocket_manager:
                status['metrics']['websocket'] = await self.dashboard_server.websocket_manager._get_current_metrics()
        
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
            status['metrics']['error'] = str(e)
        
        return status
    
    async def shutdown(self):
        """Graceful shutdown of all services"""
        if not self.running:
            return
        
        self.running = False
        self.logger.info("Initiating graceful shutdown of TGE Swarm Backend...")
        
        # Shutdown services in reverse dependency order
        shutdown_sequence = list(reversed(self.startup_sequence))
        
        for service_name in shutdown_sequence:
            try:
                self.logger.info(f"Shutting down {service_name}...")
                await self._stop_service(service_name)
                self.logger.info(f"✓ {service_name} shutdown complete")
            except Exception as e:
                self.logger.error(f"Error shutting down {service_name}: {e}")
        
        # Final cleanup
        if self.message_queue:
            try:
                await self.message_queue.shutdown()
                self.message_queue = None
                self.logger.info("✓ Message queue shutdown complete")
            except Exception as e:
                self.logger.error(f"Error shutting down message queue: {e}")
        
        self.logger.info("🛑 TGE Swarm Backend shutdown complete")


# CLI interface
async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='TGE Swarm Backend Service Orchestrator')
    parser.add_argument('--config', default='config/swarm_backend.yaml', 
                       help='Configuration file path')
    parser.add_argument('--status', action='store_true',
                       help='Get system status and exit')
    
    args = parser.parse_args()
    
    # Create backend instance
    backend = SwarmBackend(args.config)
    
    if args.status:
        # Just get status and exit
        try:
            if await backend.initialize():
                status = await backend.get_system_status()
                print(json.dumps(status, indent=2, default=str))
                await backend.shutdown()
            else:
                print("Failed to initialize backend for status check")
                sys.exit(1)
        except Exception as e:
            print(f"Error getting status: {e}")
            sys.exit(1)
    else:
        # Start the backend
        success = await backend.start()
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    # Create default config directory and file if they don't exist
    config_dir = Path('config')
    config_dir.mkdir(exist_ok=True)
    
    config_file = config_dir / 'swarm_backend.yaml'
    if not config_file.exists():
        default_config = {
            'log_level': 'INFO',
            'log_dir': './logs',
            'redis_cluster': ['localhost:6379'],
            'message_queue': {'cluster_name': 'tge-swarm'},
            'coordination_service': {
                'redis_url': 'redis://localhost:6379',
                'sync_interval': 90
            },
            'agent_manager': {'config_file': 'config/agent_manager.yaml'},
            'task_orchestrator': {'scheduling_strategy': 'adaptive'},
            'optimization_engine': {'project_root': '../'},
            'dashboard_server': {'host': 'localhost', 'port': 8080},
            'health_monitoring': {
                'check_interval': 30,
                'restart_failed_services': True
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
        
        print(f"Created default config at {config_file}")
    
    asyncio.run(main())