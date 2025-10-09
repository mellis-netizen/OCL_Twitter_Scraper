#!/usr/bin/env python3
"""
Enhanced Shared Memory Coordination Service for TGE Swarm
Builds upon the existing SwarmMemoryCoordinator with real-time coordination capabilities
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
from pathlib import Path
import redis.asyncio as redis

from message_queue import MessageQueue, SwarmMessage, MessageType, Priority
import sys
import os

# Import the existing memory coordinator
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from swarm_memory_coordinator import SwarmMemoryCoordinator


class CoordinationEventType(Enum):
    """Types of coordination events"""
    AGENT_JOINED = "agent_joined"
    AGENT_LEFT = "agent_left"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    OPTIMIZATION_DISCOVERED = "optimization_discovered"
    CONFLICT_DETECTED = "conflict_detected"
    RESOURCE_CLAIMED = "resource_claimed"
    RESOURCE_RELEASED = "resource_released"
    SYNC_REQUEST = "sync_request"
    CROSS_POLLINATION = "cross_pollination"


class ResourceType(Enum):
    """Types of shared resources"""
    FILE = "file"
    DATABASE = "database"
    API_ENDPOINT = "api_endpoint"
    MEMORY_REGION = "memory_region"
    OPTIMIZATION_TARGET = "optimization_target"


@dataclass
class CoordinationEvent:
    """Coordination event for agent synchronization"""
    id: str
    type: CoordinationEventType
    agent_id: str
    timestamp: datetime
    data: Dict[str, Any]
    priority: Priority = Priority.MEDIUM
    expires_at: Optional[datetime] = None


@dataclass
class SharedResource:
    """Shared resource definition"""
    id: str
    type: ResourceType
    name: str
    owner: Optional[str]
    locked_by: Optional[str]
    locked_at: Optional[datetime]
    metadata: Dict[str, Any]
    access_log: List[Dict[str, Any]]


@dataclass
class AgentContext:
    """Agent context and state"""
    agent_id: str
    agent_type: str
    current_task: Optional[str]
    capabilities: List[str]
    specializations: List[str]
    performance_metrics: Dict[str, float]
    last_sync: datetime
    shared_insights: List[str]
    collaboration_history: Dict[str, List[str]]


class CoordinationService:
    """Enhanced coordination service for swarm agents"""
    
    def __init__(self, memory_coordinator: SwarmMemoryCoordinator, message_queue: MessageQueue, 
                 redis_url: str = "redis://localhost:6379"):
        self.memory_coordinator = memory_coordinator
        self.message_queue = message_queue
        self.redis_url = redis_url
        self.redis_pool = None
        
        # State management
        self.active_agents: Dict[str, AgentContext] = {}
        self.shared_resources: Dict[str, SharedResource] = {}
        self.coordination_events: List[CoordinationEvent] = []
        self.conflict_resolution_queue: List[Dict[str, Any]] = []
        
        # Coordination settings
        self.sync_interval = 90  # seconds
        self.resource_lock_timeout = 300  # 5 minutes
        self.max_events_history = 1000
        
        # Performance tracking
        self.coordination_metrics = {
            'events_processed': 0,
            'conflicts_resolved': 0,
            'optimizations_coordinated': 0,
            'cross_pollinations': 0,
            'resource_locks': 0
        }
        
        self.setup_logging()
        self.running = False
    
    def setup_logging(self):
        """Setup coordination service logging"""
        self.logger = logging.getLogger("CoordinationService")
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    async def initialize(self):
        """Initialize coordination service"""
        # Initialize Redis connection
        self.redis_pool = redis.from_url(self.redis_url, decode_responses=True)
        await self.redis_pool.ping()
        
        # Initialize shared resources from config
        await self._initialize_shared_resources()
        
        # Subscribe to coordination events
        await self.message_queue.subscribe_to_broadcast(self._handle_coordination_message)
        
        # Start coordination loops
        self.running = True
        asyncio.create_task(self._coordination_loop())
        asyncio.create_task(self._conflict_resolution_loop())
        asyncio.create_task(self._resource_cleanup_loop())
        asyncio.create_task(self._cross_pollination_loop())
        
        self.logger.info("Coordination service initialized")
    
    async def _initialize_shared_resources(self):
        """Initialize shared resources that agents can coordinate on"""
        # TGE Detection System resources
        resources = [
            SharedResource(
                id="tge-config",
                type=ResourceType.FILE,
                name="config.py",
                owner=None,
                locked_by=None,
                locked_at=None,
                metadata={"path": "../config.py", "type": "configuration"},
                access_log=[]
            ),
            SharedResource(
                id="news-scraper",
                type=ResourceType.FILE,
                name="news_scraper_optimized.py",
                owner=None,
                locked_by=None,
                locked_at=None,
                metadata={"path": "../src/news_scraper_optimized.py", "type": "core_module"},
                access_log=[]
            ),
            SharedResource(
                id="twitter-monitor",
                type=ResourceType.FILE,
                name="twitter_monitor_optimized.py",
                owner=None,
                locked_by=None,
                locked_at=None,
                metadata={"path": "../src/twitter_monitor_optimized.py", "type": "core_module"},
                access_log=[]
            ),
            SharedResource(
                id="main-optimized",
                type=ResourceType.FILE,
                name="main_optimized.py",
                owner=None,
                locked_by=None,
                locked_at=None,
                metadata={"path": "../src/main_optimized.py", "type": "orchestrator"},
                access_log=[]
            ),
            SharedResource(
                id="tge-database",
                type=ResourceType.DATABASE,
                name="TGE Detection Database",
                owner=None,
                locked_by=None,
                locked_at=None,
                metadata={"type": "postgresql", "schema": "tge_swarm"},
                access_log=[]
            ),
            SharedResource(
                id="twitter-api",
                type=ResourceType.API_ENDPOINT,
                name="Twitter API v2",
                owner=None,
                locked_by=None,
                locked_at=None,
                metadata={"rate_limit": 300, "endpoint": "twitter_api_v2"},
                access_log=[]
            ),
            SharedResource(
                id="news-apis",
                type=ResourceType.API_ENDPOINT,
                name="News RSS Feeds",
                owner=None,
                locked_by=None,
                locked_at=None,
                metadata={"endpoints": "multiple_rss", "rate_limit": 1000},
                access_log=[]
            )
        ]
        
        for resource in resources:
            self.shared_resources[resource.id] = resource
            # Store in Redis for persistence
            await self.redis_pool.hset(
                "coordination:resources", 
                resource.id, 
                json.dumps(asdict(resource), default=str)
            )
        
        self.logger.info(f"Initialized {len(resources)} shared resources")
    
    async def register_agent(self, agent_id: str, agent_type: str, capabilities: List[str], 
                           specializations: List[str]) -> bool:
        """Register agent with coordination service"""
        try:
            agent_context = AgentContext(
                agent_id=agent_id,
                agent_type=agent_type,
                current_task=None,
                capabilities=capabilities,
                specializations=specializations,
                performance_metrics={},
                last_sync=datetime.now(),
                shared_insights=[],
                collaboration_history={}
            )
            
            self.active_agents[agent_id] = agent_context
            
            # Store in Redis
            await self.redis_pool.hset(
                "coordination:agents",
                agent_id,
                json.dumps(asdict(agent_context), default=str)
            )
            
            # Publish agent joined event
            event = CoordinationEvent(
                id=str(uuid.uuid4()),
                type=CoordinationEventType.AGENT_JOINED,
                agent_id=agent_id,
                timestamp=datetime.now(),
                data={
                    "agent_type": agent_type,
                    "capabilities": capabilities,
                    "specializations": specializations
                }
            )
            
            await self._publish_coordination_event(event)
            
            self.logger.info(f"Registered agent {agent_id} with type {agent_type}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register agent {agent_id}: {e}")
            return False
    
    async def deregister_agent(self, agent_id: str) -> bool:
        """Deregister agent from coordination service"""
        try:
            if agent_id not in self.active_agents:
                return False
            
            # Release any locked resources
            await self._release_agent_resources(agent_id)
            
            # Remove from active agents
            del self.active_agents[agent_id]
            
            # Remove from Redis
            await self.redis_pool.hdel("coordination:agents", agent_id)
            
            # Publish agent left event
            event = CoordinationEvent(
                id=str(uuid.uuid4()),
                type=CoordinationEventType.AGENT_LEFT,
                agent_id=agent_id,
                timestamp=datetime.now(),
                data={}
            )
            
            await self._publish_coordination_event(event)
            
            self.logger.info(f"Deregistered agent {agent_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to deregister agent {agent_id}: {e}")
            return False
    
    async def request_resource_access(self, agent_id: str, resource_id: str, 
                                    access_type: str = "read", timeout: int = 300) -> bool:
        """Request access to shared resource"""
        try:
            if resource_id not in self.shared_resources:
                self.logger.error(f"Resource {resource_id} not found")
                return False
            
            resource = self.shared_resources[resource_id]
            
            # Check if resource is available
            if access_type == "write" and resource.locked_by and resource.locked_by != agent_id:
                # Check if lock has expired
                if (resource.locked_at and 
                    datetime.now() - resource.locked_at > timedelta(seconds=self.resource_lock_timeout)):
                    # Lock expired, release it
                    await self._release_resource_lock(resource_id)
                else:
                    # Resource is locked by another agent
                    self.logger.warning(f"Resource {resource_id} is locked by {resource.locked_by}")
                    return False
            
            # Grant access
            if access_type == "write":
                resource.locked_by = agent_id
                resource.locked_at = datetime.now()
            
            # Log access
            access_log_entry = {
                'agent_id': agent_id,
                'access_type': access_type,
                'timestamp': datetime.now().isoformat(),
                'granted': True
            }
            resource.access_log.append(access_log_entry)
            
            # Keep only last 20 access log entries
            resource.access_log = resource.access_log[-20:]
            
            # Update in Redis
            await self.redis_pool.hset(
                "coordination:resources",
                resource_id,
                json.dumps(asdict(resource), default=str)
            )
            
            # Publish resource claimed event
            if access_type == "write":
                event = CoordinationEvent(
                    id=str(uuid.uuid4()),
                    type=CoordinationEventType.RESOURCE_CLAIMED,
                    agent_id=agent_id,
                    timestamp=datetime.now(),
                    data={
                        "resource_id": resource_id,
                        "access_type": access_type
                    }
                )
                await self._publish_coordination_event(event)
                
                self.coordination_metrics['resource_locks'] += 1
            
            self.logger.info(f"Granted {access_type} access to {resource_id} for agent {agent_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to grant resource access: {e}")
            return False
    
    async def release_resource_access(self, agent_id: str, resource_id: str) -> bool:
        """Release access to shared resource"""
        try:
            if resource_id not in self.shared_resources:
                return False
            
            resource = self.shared_resources[resource_id]
            
            if resource.locked_by == agent_id:
                resource.locked_by = None
                resource.locked_at = None
                
                # Update in Redis
                await self.redis_pool.hset(
                    "coordination:resources",
                    resource_id,
                    json.dumps(asdict(resource), default=str)
                )
                
                # Publish resource released event
                event = CoordinationEvent(
                    id=str(uuid.uuid4()),
                    type=CoordinationEventType.RESOURCE_RELEASED,
                    agent_id=agent_id,
                    timestamp=datetime.now(),
                    data={"resource_id": resource_id}
                )
                await self._publish_coordination_event(event)
                
                self.logger.info(f"Released resource {resource_id} from agent {agent_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to release resource access: {e}")
            return False
    
    async def coordinate_optimization(self, requesting_agent: str, optimization_type: str,
                                    target_resources: List[str], parameters: Dict[str, Any]) -> str:
        """Coordinate optimization across multiple agents"""
        try:
            coordination_id = str(uuid.uuid4())
            
            # Check if any agents can collaborate on this optimization
            capable_agents = []
            for agent_id, context in self.active_agents.items():
                if agent_id != requesting_agent:
                    # Check if agent has relevant capabilities
                    relevant_capabilities = self._match_capabilities_to_optimization(
                        context.capabilities, optimization_type
                    )
                    if relevant_capabilities:
                        capable_agents.append((agent_id, relevant_capabilities))
            
            # Store optimization request in memory coordinator
            optimization_data = {
                'coordination_id': coordination_id,
                'requesting_agent': requesting_agent,
                'optimization_type': optimization_type,
                'target_resources': target_resources,
                'parameters': parameters,
                'capable_agents': [agent[0] for agent in capable_agents],
                'status': 'coordinating',
                'started_at': datetime.now().isoformat()
            }
            
            memory_id = self.memory_coordinator.store_memory(
                requesting_agent, 
                "optimization_coordination", 
                optimization_data
            )
            
            # Publish optimization discovery event
            event = CoordinationEvent(
                id=coordination_id,
                type=CoordinationEventType.OPTIMIZATION_DISCOVERED,
                agent_id=requesting_agent,
                timestamp=datetime.now(),
                data={
                    'optimization_type': optimization_type,
                    'target_resources': target_resources,
                    'capable_agents': [agent[0] for agent in capable_agents],
                    'memory_id': memory_id
                },
                priority=Priority.HIGH
            )
            
            await self._publish_coordination_event(event)
            
            # Trigger cross-pollination with capable agents
            if capable_agents:
                cross_pollination = self.memory_coordinator.cross_pollinate(
                    target_agent=requesting_agent,
                    source_agents=[agent[0] for agent in capable_agents],
                    focus_areas=[optimization_type]
                )
                
                self.coordination_metrics['cross_pollinations'] += 1
            
            self.coordination_metrics['optimizations_coordinated'] += 1
            self.logger.info(f"Coordinated optimization {coordination_id} with {len(capable_agents)} agents")
            
            return coordination_id
            
        except Exception as e:
            self.logger.error(f"Failed to coordinate optimization: {e}")
            return ""
    
    async def report_task_completion(self, agent_id: str, task_id: str, results: Dict[str, Any],
                                   optimizations_found: List[Dict[str, Any]] = None):
        """Report task completion with coordination implications"""
        try:
            # Store results in memory coordinator
            completion_data = {
                'task_id': task_id,
                'agent_id': agent_id,
                'results': results,
                'optimizations_found': optimizations_found or [],
                'completed_at': datetime.now().isoformat()
            }
            
            memory_id = self.memory_coordinator.store_memory(
                agent_id,
                "task_completion",
                completion_data
            )
            
            # Update agent context
            if agent_id in self.active_agents:
                agent_context = self.active_agents[agent_id]
                agent_context.current_task = None
                agent_context.last_sync = datetime.now()
                
                # Update performance metrics based on results
                self._update_agent_performance_metrics(agent_context, results)
            
            # Publish task completion event
            event = CoordinationEvent(
                id=str(uuid.uuid4()),
                type=CoordinationEventType.TASK_COMPLETED,
                agent_id=agent_id,
                timestamp=datetime.now(),
                data={
                    'task_id': task_id,
                    'memory_id': memory_id,
                    'optimizations_found': len(optimizations_found) if optimizations_found else 0
                }
            )
            
            await self._publish_coordination_event(event)
            
            # If optimizations were found, trigger coordination
            if optimizations_found:
                for optimization in optimizations_found:
                    await self.coordinate_optimization(
                        agent_id,
                        optimization.get('type', 'general'),
                        optimization.get('target_resources', []),
                        optimization.get('parameters', {})
                    )
            
            self.logger.info(f"Reported task completion for {task_id} by agent {agent_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to report task completion: {e}")
    
    async def detect_conflicts(self, agent_id: str, proposed_changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect potential conflicts with other agents' work"""
        conflicts = []
        
        try:
            for change in proposed_changes:
                target_resource = change.get('target_resource')
                change_type = change.get('type')
                
                # Check for resource conflicts
                if target_resource and target_resource in self.shared_resources:
                    resource = self.shared_resources[target_resource]
                    
                    # Check if another agent is working on the same resource
                    recent_access = [
                        log for log in resource.access_log
                        if (datetime.now() - datetime.fromisoformat(log['timestamp'])).total_seconds() < 3600
                        and log['agent_id'] != agent_id
                    ]
                    
                    if recent_access:
                        conflicts.append({
                            'type': 'resource_conflict',
                            'resource': target_resource,
                            'conflicting_agents': [log['agent_id'] for log in recent_access],
                            'change': change
                        })
                
                # Check for logical conflicts in optimization goals
                similar_optimizations = self._find_similar_optimizations(change)
                if similar_optimizations:
                    conflicts.append({
                        'type': 'optimization_conflict',
                        'similar_optimizations': similar_optimizations,
                        'change': change
                    })
            
            if conflicts:
                # Store conflict in resolution queue
                conflict_record = {
                    'id': str(uuid.uuid4()),
                    'agent_id': agent_id,
                    'conflicts': conflicts,
                    'proposed_changes': proposed_changes,
                    'detected_at': datetime.now(),
                    'status': 'pending'
                }
                
                self.conflict_resolution_queue.append(conflict_record)
                
                # Publish conflict detection event
                event = CoordinationEvent(
                    id=conflict_record['id'],
                    type=CoordinationEventType.CONFLICT_DETECTED,
                    agent_id=agent_id,
                    timestamp=datetime.now(),
                    data={
                        'conflicts': conflicts,
                        'severity': self._assess_conflict_severity(conflicts)
                    },
                    priority=Priority.HIGH
                )
                
                await self._publish_coordination_event(event)
                
                self.logger.warning(f"Detected {len(conflicts)} conflicts for agent {agent_id}")
            
            return conflicts
            
        except Exception as e:
            self.logger.error(f"Failed to detect conflicts: {e}")
            return []
    
    async def get_coordination_status(self) -> Dict[str, Any]:
        """Get current coordination status"""
        try:
            # Get recent events
            recent_events = self.coordination_events[-20:] if self.coordination_events else []
            
            # Get resource utilization
            resource_status = {}
            for resource_id, resource in self.shared_resources.items():
                resource_status[resource_id] = {
                    'locked': resource.locked_by is not None,
                    'locked_by': resource.locked_by,
                    'recent_access_count': len([
                        log for log in resource.access_log
                        if (datetime.now() - datetime.fromisoformat(log['timestamp'])).total_seconds() < 3600
                    ])
                }
            
            # Get agent collaboration matrix
            collaboration_matrix = self._build_collaboration_matrix()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'active_agents': len(self.active_agents),
                'shared_resources': len(self.shared_resources),
                'pending_conflicts': len(self.conflict_resolution_queue),
                'recent_events': len(recent_events),
                'metrics': self.coordination_metrics,
                'resource_status': resource_status,
                'collaboration_matrix': collaboration_matrix,
                'events': [asdict(event) for event in recent_events]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get coordination status: {e}")
            return {}
    
    async def _coordination_loop(self):
        """Main coordination loop for periodic synchronization"""
        while self.running:
            try:
                await asyncio.sleep(self.sync_interval)
                
                # Trigger synthesis in memory coordinator
                synthesis = self.memory_coordinator.synthesize_findings()
                
                # Check for new coordination opportunities
                await self._identify_coordination_opportunities(synthesis)
                
                # Update agent contexts
                await self._update_agent_contexts()
                
                # Clean up old events
                self._cleanup_old_events()
                
            except Exception as e:
                self.logger.error(f"Error in coordination loop: {e}")
                await asyncio.sleep(30)
    
    async def _conflict_resolution_loop(self):
        """Loop for resolving coordination conflicts"""
        while self.running:
            try:
                if self.conflict_resolution_queue:
                    conflict = self.conflict_resolution_queue.pop(0)
                    await self._resolve_conflict(conflict)
                
                await asyncio.sleep(10)
                
            except Exception as e:
                self.logger.error(f"Error in conflict resolution loop: {e}")
                await asyncio.sleep(30)
    
    async def _resource_cleanup_loop(self):
        """Loop for cleaning up expired resource locks"""
        while self.running:
            try:
                current_time = datetime.now()
                
                for resource_id, resource in self.shared_resources.items():
                    if (resource.locked_by and resource.locked_at and
                        current_time - resource.locked_at > timedelta(seconds=self.resource_lock_timeout)):
                        
                        await self._release_resource_lock(resource_id)
                        self.logger.warning(f"Released expired lock on resource {resource_id}")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in resource cleanup loop: {e}")
                await asyncio.sleep(60)
    
    async def _cross_pollination_loop(self):
        """Loop for triggering cross-pollination between agents"""
        while self.running:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                # Identify agents that could benefit from cross-pollination
                agent_pairs = self._identify_cross_pollination_opportunities()
                
                for source_agent, target_agent, focus_areas in agent_pairs:
                    cross_pollination = self.memory_coordinator.cross_pollinate(
                        target_agent=target_agent,
                        source_agents=[source_agent],
                        focus_areas=focus_areas
                    )
                    
                    # Publish cross-pollination event
                    event = CoordinationEvent(
                        id=str(uuid.uuid4()),
                        type=CoordinationEventType.CROSS_POLLINATION,
                        agent_id=target_agent,
                        timestamp=datetime.now(),
                        data={
                            'source_agent': source_agent,
                            'focus_areas': focus_areas,
                            'findings_count': len(cross_pollination.get('relevant_findings', []))
                        }
                    )
                    
                    await self._publish_coordination_event(event)
                    self.coordination_metrics['cross_pollinations'] += 1
                
            except Exception as e:
                self.logger.error(f"Error in cross-pollination loop: {e}")
                await asyncio.sleep(300)
    
    async def _publish_coordination_event(self, event: CoordinationEvent):
        """Publish coordination event to message queue"""
        message = SwarmMessage(
            id=event.id,
            type=MessageType.COORDINATION_EVENT,
            sender="coordination-service",
            recipient=None,  # Broadcast
            timestamp=event.timestamp,
            payload=asdict(event),
            priority=event.priority
        )
        
        await self.message_queue.publish_message(message)
        
        # Store event locally
        self.coordination_events.append(event)
        
        # Keep only recent events in memory
        if len(self.coordination_events) > self.max_events_history:
            self.coordination_events = self.coordination_events[-self.max_events_history:]
        
        self.coordination_metrics['events_processed'] += 1
    
    async def _handle_coordination_message(self, message: SwarmMessage):
        """Handle incoming coordination messages"""
        try:
            if message.type == MessageType.COORDINATION_EVENT:
                event_data = message.payload
                
                # Process specific event types
                if event_data.get('type') == CoordinationEventType.SYNC_REQUEST.value:
                    await self._handle_sync_request(message.sender, event_data)
                
            elif message.type == MessageType.OPTIMIZATION_REQUEST:
                # Handle optimization requests from agents
                await self._handle_optimization_request(message.sender, message.payload)
                
        except Exception as e:
            self.logger.error(f"Error handling coordination message: {e}")
    
    def _match_capabilities_to_optimization(self, capabilities: List[str], optimization_type: str) -> List[str]:
        """Match agent capabilities to optimization type"""
        relevant_capabilities = []
        
        capability_map = {
            'scraping-efficiency': ['web-scraping', 'api-optimization', 'performance-tuning'],
            'keyword-precision': ['nlp', 'text-analysis', 'pattern-matching'],
            'api-reliability': ['error-handling', 'retry-logic', 'circuit-breakers'],
            'performance-optimization': ['profiling', 'memory-management', 'async-programming'],
            'data-quality': ['validation', 'sanitization', 'deduplication']
        }
        
        target_capabilities = capability_map.get(optimization_type, [])
        
        for capability in capabilities:
            if capability in target_capabilities or any(target in capability for target in target_capabilities):
                relevant_capabilities.append(capability)
        
        return relevant_capabilities
    
    def _update_agent_performance_metrics(self, agent_context: AgentContext, results: Dict[str, Any]):
        """Update agent performance metrics based on task results"""
        # Extract performance indicators from results
        if 'execution_time' in results:
            agent_context.performance_metrics['avg_execution_time'] = results['execution_time']
        
        if 'success_rate' in results:
            agent_context.performance_metrics['success_rate'] = results['success_rate']
        
        if 'optimizations_found' in results:
            agent_context.performance_metrics['optimizations_per_task'] = len(results['optimizations_found'])
        
        # Update last sync time
        agent_context.last_sync = datetime.now()
    
    def _find_similar_optimizations(self, change: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find similar optimization work by other agents"""
        similar = []
        
        # Get recent optimizations from memory coordinator
        recent_memories = self.memory_coordinator.retrieve_memory(memory_type="optimization_coordination")
        
        target_files = change.get('target_files', [])
        optimization_type = change.get('type', '')
        
        for memory in recent_memories[-50:]:  # Check last 50 memories
            memory_data = memory.get('content', {})
            
            # Check for overlapping target files
            memory_targets = memory_data.get('target_resources', [])
            if any(target in memory_targets for target in target_files):
                similar.append({
                    'memory_id': memory.get('memory_id'),
                    'agent_id': memory.get('agent_id'),
                    'overlap_score': len(set(target_files) & set(memory_targets)),
                    'optimization_type': memory_data.get('optimization_type')
                })
        
        return similar
    
    def _assess_conflict_severity(self, conflicts: List[Dict[str, Any]]) -> str:
        """Assess the severity of detected conflicts"""
        if not conflicts:
            return "none"
        
        severity_scores = []
        for conflict in conflicts:
            if conflict['type'] == 'resource_conflict':
                severity_scores.append(3)  # High severity
            elif conflict['type'] == 'optimization_conflict':
                severity_scores.append(2)  # Medium severity
            else:
                severity_scores.append(1)  # Low severity
        
        max_severity = max(severity_scores)
        
        if max_severity >= 3:
            return "high"
        elif max_severity >= 2:
            return "medium"
        else:
            return "low"
    
    def _build_collaboration_matrix(self) -> Dict[str, Dict[str, int]]:
        """Build collaboration matrix between agents"""
        matrix = {}
        
        for agent_id, context in self.active_agents.items():
            matrix[agent_id] = {}
            for other_agent_id in self.active_agents:
                if other_agent_id != agent_id:
                    collaboration_count = len(context.collaboration_history.get(other_agent_id, []))
                    matrix[agent_id][other_agent_id] = collaboration_count
        
        return matrix
    
    def _identify_cross_pollination_opportunities(self) -> List[Tuple[str, str, List[str]]]:
        """Identify opportunities for cross-pollination between agents"""
        opportunities = []
        
        for target_agent_id, target_context in self.active_agents.items():
            for source_agent_id, source_context in self.active_agents.items():
                if source_agent_id != target_agent_id:
                    # Check for complementary specializations
                    common_areas = set(target_context.specializations) & set(source_context.specializations)
                    
                    if common_areas:
                        opportunities.append((source_agent_id, target_agent_id, list(common_areas)))
        
        return opportunities[:5]  # Limit to top 5 opportunities
    
    async def _release_agent_resources(self, agent_id: str):
        """Release all resources locked by an agent"""
        for resource_id, resource in self.shared_resources.items():
            if resource.locked_by == agent_id:
                await self.release_resource_access(agent_id, resource_id)
    
    async def _release_resource_lock(self, resource_id: str):
        """Release expired resource lock"""
        if resource_id in self.shared_resources:
            resource = self.shared_resources[resource_id]
            locked_by = resource.locked_by
            
            resource.locked_by = None
            resource.locked_at = None
            
            # Update in Redis
            await self.redis_pool.hset(
                "coordination:resources",
                resource_id,
                json.dumps(asdict(resource), default=str)
            )
            
            if locked_by:
                self.logger.info(f"Released expired lock on {resource_id} from {locked_by}")
    
    def _cleanup_old_events(self):
        """Clean up old coordination events"""
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.coordination_events = [
            event for event in self.coordination_events
            if event.timestamp > cutoff_time
        ]
    
    async def _identify_coordination_opportunities(self, synthesis: Dict[str, Any]):
        """Identify new coordination opportunities from synthesis"""
        # Analyze synthesis for coordination patterns
        cross_cutting_issues = synthesis.get('cross_cutting_issues', [])
        
        for issue in cross_cutting_issues:
            affected_agents = issue.get('affected_agents', [])
            if len(affected_agents) > 1:
                # Trigger coordination for this issue
                await self.coordinate_optimization(
                    requesting_agent=affected_agents[0],
                    optimization_type=issue.get('issue', 'general'),
                    target_resources=[],
                    parameters={'cross_cutting': True, 'affected_agents': affected_agents}
                )
    
    async def _update_agent_contexts(self):
        """Update agent contexts with latest information"""
        for agent_id, context in self.active_agents.items():
            # Update in Redis
            await self.redis_pool.hset(
                "coordination:agents",
                agent_id,
                json.dumps(asdict(context), default=str)
            )
    
    async def _resolve_conflict(self, conflict_record: Dict[str, Any]):
        """Resolve coordination conflict"""
        try:
            conflicts = conflict_record['conflicts']
            agent_id = conflict_record['agent_id']
            
            # Simple conflict resolution strategy
            for conflict in conflicts:
                if conflict['type'] == 'resource_conflict':
                    # Notify agents about conflict and suggest coordination
                    message = SwarmMessage(
                        id=str(uuid.uuid4()),
                        type=MessageType.COORDINATION_EVENT,
                        sender="coordination-service",
                        recipient=agent_id,
                        timestamp=datetime.now(),
                        payload={
                            'type': 'conflict_resolution',
                            'conflict': conflict,
                            'suggested_action': 'coordinate_with_agents'
                        },
                        priority=Priority.HIGH
                    )
                    
                    await self.message_queue.publish_message(message)
            
            conflict_record['status'] = 'resolved'
            self.coordination_metrics['conflicts_resolved'] += 1
            
            self.logger.info(f"Resolved conflict {conflict_record['id']} for agent {agent_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to resolve conflict: {e}")
    
    async def _handle_sync_request(self, agent_id: str, event_data: Dict[str, Any]):
        """Handle sync request from agent"""
        # Get recent coordination events for this agent
        relevant_events = [
            event for event in self.coordination_events[-50:]
            if (event.agent_id == agent_id or 
                event.type in [CoordinationEventType.OPTIMIZATION_DISCOVERED, 
                             CoordinationEventType.CROSS_POLLINATION])
        ]
        
        # Send sync response
        response = SwarmMessage(
            id=str(uuid.uuid4()),
            type=MessageType.COORDINATION_EVENT,
            sender="coordination-service",
            recipient=agent_id,
            timestamp=datetime.now(),
            payload={
                'type': 'sync_response',
                'events': [asdict(event) for event in relevant_events],
                'coordination_status': await self.get_coordination_status()
            }
        )
        
        await self.message_queue.publish_message(response)
    
    async def _handle_optimization_request(self, agent_id: str, payload: Dict[str, Any]):
        """Handle optimization request from agent"""
        optimization_type = payload.get('optimization_type', 'general')
        target_files = payload.get('target_files', [])
        parameters = payload.get('parameters', {})
        
        coordination_id = await self.coordinate_optimization(
            requesting_agent=agent_id,
            optimization_type=optimization_type,
            target_resources=target_files,
            parameters=parameters
        )
        
        if coordination_id:
            self.logger.info(f"Started optimization coordination {coordination_id} for agent {agent_id}")
    
    async def shutdown(self):
        """Shutdown coordination service gracefully"""
        self.running = False
        
        if self.redis_pool:
            await self.redis_pool.close()
        
        self.logger.info("Coordination service shutdown complete")


# CLI interface for testing
if __name__ == "__main__":
    import sys
    
    async def test_coordination_service():
        # Initialize components
        memory_coordinator = SwarmMemoryCoordinator()
        
        from message_queue import create_message_queue
        message_queue = await create_message_queue(["localhost:6379"])
        
        # Initialize coordination service
        coordination_service = CoordinationService(memory_coordinator, message_queue)
        await coordination_service.initialize()
        
        # Test agent registration
        success = await coordination_service.register_agent(
            agent_id="test-agent-1",
            agent_type="scraping-efficiency",
            capabilities=["web-scraping", "api-optimization"],
            specializations=["news-scraping", "twitter-monitoring"]
        )
        
        print(f"Agent registration: {success}")
        
        # Test resource access
        access_granted = await coordination_service.request_resource_access(
            agent_id="test-agent-1",
            resource_id="tge-config",
            access_type="write"
        )
        
        print(f"Resource access granted: {access_granted}")
        
        # Get coordination status
        status = await coordination_service.get_coordination_status()
        print(f"Coordination status: {json.dumps(status, indent=2, default=str)}")
        
        await coordination_service.shutdown()
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        asyncio.run(test_coordination_service())
    else:
        print("Use 'python coordination_service.py test' to run tests")