#!/usr/bin/env python3
"""
Database Models and Schemas for TGE Swarm Agent Coordination
Provides persistent storage for agent state, tasks, and optimization history
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from enum import Enum as PyEnum
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, DateTime, Text, JSON, Boolean,
    ForeignKey, Enum, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.types import TypeDecorator, VARCHAR
import json


# Custom UUID type for cross-database compatibility
class GUID(TypeDecorator):
    """Platform-independent GUID type"""
    impl = VARCHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(VARCHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value


# Enums
class AgentStatus(PyEnum):
    PENDING = "pending"
    STARTING = "starting"
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    STOPPED = "stopped"
    FAILED = "failed"


class TaskStatus(PyEnum):
    PENDING = "pending"
    QUEUED = "queued"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class OptimizationStatus(PyEnum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    VALIDATING = "validating"
    APPLYING = "applying"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class Priority(PyEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class CoordinationEventType(PyEnum):
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


# Base model
Base = declarative_base()


class BaseModel(Base):
    """Base model with common fields"""
    __abstract__ = True
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))


class Agent(BaseModel):
    """Agent instance model"""
    __tablename__ = 'agents'
    
    name = Column(String(255), nullable=False)
    agent_type = Column(String(100), nullable=False)
    container_id = Column(String(100), unique=True)
    status = Column(Enum(AgentStatus), default=AgentStatus.PENDING)
    host = Column(String(255))
    port = Column(Integer)
    version = Column(String(50))
    
    # Resource allocation
    cpu_limit = Column(Float)
    memory_limit = Column(String(50))
    
    # Runtime metrics
    last_seen = Column(DateTime(timezone=True))
    restart_count = Column(Integer, default=0)
    task_count = Column(Integer, default=0)
    error_rate = Column(Float, default=0.0)
    
    # Configuration
    environment = Column(JSON)
    capabilities = Column(JSON)  # List of capabilities
    specializations = Column(JSON)  # List of specializations
    
    # Health and performance
    health_checks = Column(JSON)  # List of recent health check results
    performance_metrics = Column(JSON)  # Performance data
    
    # Relationships
    tasks = relationship("Task", back_populates="agent")
    coordination_events = relationship("CoordinationEvent", back_populates="agent")
    optimization_executions = relationship("OptimizationExecution", back_populates="agent")
    
    # Indexes
    __table_args__ = (
        Index('idx_agent_type_status', 'agent_type', 'status'),
        Index('idx_agent_last_seen', 'last_seen'),
    )


class Task(BaseModel):
    """Task execution model"""
    __tablename__ = 'tasks'
    
    task_type = Column(String(100), nullable=False)
    agent_type = Column(String(100), nullable=False)
    priority = Column(Enum(Priority), default=Priority.MEDIUM)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    
    # Task definition
    payload = Column(JSON)  # Task parameters
    timeout = Column(Integer, default=300)
    retries = Column(Integer, default=3)
    retry_count = Column(Integer, default=0)
    
    # Dependencies
    dependencies = Column(JSON)  # List of task IDs this task depends on
    
    # Execution tracking
    agent_id = Column(GUID(), ForeignKey('agents.id'), nullable=True)
    assigned_at = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Results and errors
    result = Column(JSON)
    error_message = Column(Text)
    execution_log = Column(JSON)  # List of execution steps
    
    # Performance metrics
    queue_time = Column(Float)  # Time spent in queue
    execution_time = Column(Float)  # Time spent executing
    
    # Relationships
    agent = relationship("Agent", back_populates="tasks")
    
    # Indexes
    __table_args__ = (
        Index('idx_task_status_priority', 'status', 'priority'),
        Index('idx_task_agent_status', 'agent_id', 'status'),
        Index('idx_task_type_status', 'task_type', 'status'),
        Index('idx_task_created_at', 'created_at'),
    )


class SharedResource(BaseModel):
    """Shared resource model for coordination"""
    __tablename__ = 'shared_resources'
    
    name = Column(String(255), nullable=False, unique=True)
    resource_type = Column(String(100), nullable=False)
    path = Column(Text)  # File path or resource identifier
    
    # Lock management
    locked_by = Column(GUID(), ForeignKey('agents.id'), nullable=True)
    locked_at = Column(DateTime(timezone=True))
    lock_timeout = Column(Integer, default=300)
    
    # Resource metadata
    metadata = Column(JSON)
    checksum = Column(String(64))  # For file integrity
    
    # Access control
    read_only = Column(Boolean, default=False)
    access_log = Column(JSON)  # List of recent access attempts
    
    # Relationships
    locked_by_agent = relationship("Agent", foreign_keys=[locked_by])
    
    # Indexes
    __table_args__ = (
        Index('idx_resource_type', 'resource_type'),
        Index('idx_resource_locked', 'locked_by', 'locked_at'),
    )


class OptimizationRecommendation(BaseModel):
    """Optimization recommendation model"""
    __tablename__ = 'optimization_recommendations'
    
    agent_id = Column(GUID(), ForeignKey('agents.id'), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    optimization_type = Column(String(100), nullable=False)
    severity = Column(String(50), nullable=False)
    
    # Target and changes
    target_files = Column(JSON)  # List of target files
    proposed_changes = Column(JSON)  # List of proposed changes
    
    # Assessment
    expected_benefits = Column(JSON)  # List of expected benefits
    risk_assessment = Column(JSON)  # Risk analysis
    confidence_score = Column(Float, default=0.5)
    
    # Validation requirements
    validation_requirements = Column(JSON)  # List of validation steps
    
    # Dependencies
    dependencies = Column(JSON)  # List of recommendation IDs this depends on
    
    # Status
    status = Column(String(50), default='pending')
    approved_at = Column(DateTime(timezone=True))
    approved_by = Column(String(255))
    
    # Relationships
    agent = relationship("Agent")
    executions = relationship("OptimizationExecution", back_populates="recommendation")
    
    # Indexes
    __table_args__ = (
        Index('idx_optimization_agent_status', 'agent_id', 'status'),
        Index('idx_optimization_type_severity', 'optimization_type', 'severity'),
    )


class OptimizationExecution(BaseModel):
    """Optimization execution tracking model"""
    __tablename__ = 'optimization_executions'
    
    recommendation_id = Column(GUID(), ForeignKey('optimization_recommendations.id'), nullable=False)
    agent_id = Column(GUID(), ForeignKey('agents.id'), nullable=False)
    status = Column(Enum(OptimizationStatus), default=OptimizationStatus.PENDING)
    
    # Execution tracking
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Execution details
    execution_log = Column(JSON)  # List of execution steps
    validation_results = Column(JSON)  # Pre and post validation results
    rollback_data = Column(JSON)  # Data needed for rollback
    
    # Results
    success_metrics = Column(JSON)  # Success measurement data
    error_message = Column(Text)
    
    # Performance
    execution_time = Column(Float)
    validation_time = Column(Float)
    
    # Relationships
    recommendation = relationship("OptimizationRecommendation", back_populates="executions")
    agent = relationship("Agent", back_populates="optimization_executions")
    
    # Indexes
    __table_args__ = (
        Index('idx_execution_status', 'status'),
        Index('idx_execution_agent_status', 'agent_id', 'status'),
        Index('idx_execution_recommendation', 'recommendation_id'),
    )


class CoordinationEvent(BaseModel):
    """Coordination event model"""
    __tablename__ = 'coordination_events'
    
    agent_id = Column(GUID(), ForeignKey('agents.id'), nullable=False)
    event_type = Column(Enum(CoordinationEventType), nullable=False)
    priority = Column(Enum(Priority), default=Priority.MEDIUM)
    
    # Event data
    event_data = Column(JSON)
    correlation_id = Column(GUID())  # Link related events
    
    # Expiration
    expires_at = Column(DateTime(timezone=True))
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime(timezone=True))
    
    # Relationships
    agent = relationship("Agent", back_populates="coordination_events")
    
    # Indexes
    __table_args__ = (
        Index('idx_event_type_processed', 'event_type', 'processed'),
        Index('idx_event_agent_type', 'agent_id', 'event_type'),
        Index('idx_event_expires_at', 'expires_at'),
        Index('idx_event_correlation', 'correlation_id'),
    )


class SystemMetric(BaseModel):
    """System metrics model for performance tracking"""
    __tablename__ = 'system_metrics'
    
    metric_name = Column(String(255), nullable=False)
    metric_type = Column(String(100), nullable=False)  # counter, gauge, histogram
    source = Column(String(255), nullable=False)  # agent_id or system component
    
    # Metric value
    value = Column(Float)
    tags = Column(JSON)  # Additional tags/labels
    
    # Time series
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    
    # Indexes
    __table_args__ = (
        Index('idx_metric_name_source', 'metric_name', 'source'),
        Index('idx_metric_timestamp', 'timestamp'),
        Index('idx_metric_source_timestamp', 'source', 'timestamp'),
    )


class PerformanceBaseline(BaseModel):
    """Performance baseline tracking"""
    __tablename__ = 'performance_baselines'
    
    component = Column(String(255), nullable=False)
    metric_name = Column(String(255), nullable=False)
    baseline_value = Column(Float, nullable=False)
    
    # Measurement details
    measurement_date = Column(DateTime(timezone=True), nullable=False)
    measurement_duration = Column(Integer)  # Duration in seconds
    sample_size = Column(Integer)
    
    # Statistical data
    min_value = Column(Float)
    max_value = Column(Float)
    mean_value = Column(Float)
    median_value = Column(Float)
    std_deviation = Column(Float)
    
    # Context
    conditions = Column(JSON)  # Environment/conditions during measurement
    version = Column(String(50))  # System version
    
    # Indexes
    __table_args__ = (
        Index('idx_baseline_component_metric', 'component', 'metric_name'),
        Index('idx_baseline_date', 'measurement_date'),
        UniqueConstraint('component', 'metric_name', 'measurement_date', name='uq_baseline_component_metric_date'),
    )


class OptimizationImpact(BaseModel):
    """Track optimization impact on performance"""
    __tablename__ = 'optimization_impacts'
    
    execution_id = Column(GUID(), ForeignKey('optimization_executions.id'), nullable=False)
    metric_name = Column(String(255), nullable=False)
    
    # Before/after values
    before_value = Column(Float, nullable=False)
    after_value = Column(Float, nullable=False)
    improvement_percent = Column(Float)  # Calculated improvement percentage
    
    # Measurement details
    measurement_window = Column(Integer)  # Measurement window in seconds
    confidence_level = Column(Float)  # Statistical confidence
    
    # Context
    measurement_conditions = Column(JSON)
    
    # Relationships
    execution = relationship("OptimizationExecution")
    
    # Indexes
    __table_args__ = (
        Index('idx_impact_execution', 'execution_id'),
        Index('idx_impact_metric', 'metric_name'),
        Index('idx_impact_improvement', 'improvement_percent'),
    )


# Database manager class
class DatabaseManager:
    """Database connection and session management"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """Create all tables"""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """Drop all tables"""
        Base.metadata.drop_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    def close(self):
        """Close database connection"""
        self.engine.dispose()


# Repository classes for data access
class AgentRepository:
    """Repository for agent operations"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_agent(self, **kwargs) -> Agent:
        """Create new agent"""
        agent = Agent(**kwargs)
        self.session.add(agent)
        self.session.commit()
        self.session.refresh(agent)
        return agent
    
    def get_agent(self, agent_id: uuid.UUID) -> Optional[Agent]:
        """Get agent by ID"""
        return self.session.query(Agent).filter(Agent.id == agent_id).first()
    
    def get_agent_by_container_id(self, container_id: str) -> Optional[Agent]:
        """Get agent by container ID"""
        return self.session.query(Agent).filter(Agent.container_id == container_id).first()
    
    def get_agents_by_type(self, agent_type: str) -> List[Agent]:
        """Get agents by type"""
        return self.session.query(Agent).filter(Agent.agent_type == agent_type).all()
    
    def get_healthy_agents(self) -> List[Agent]:
        """Get all healthy agents"""
        return self.session.query(Agent).filter(Agent.status == AgentStatus.HEALTHY).all()
    
    def update_agent_status(self, agent_id: uuid.UUID, status: AgentStatus, **kwargs):
        """Update agent status and other fields"""
        self.session.query(Agent).filter(Agent.id == agent_id).update({
            'status': status,
            'last_seen': datetime.now(timezone.utc),
            **kwargs
        })
        self.session.commit()
    
    def delete_agent(self, agent_id: uuid.UUID):
        """Delete agent"""
        self.session.query(Agent).filter(Agent.id == agent_id).delete()
        self.session.commit()


class TaskRepository:
    """Repository for task operations"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_task(self, **kwargs) -> Task:
        """Create new task"""
        task = Task(**kwargs)
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task
    
    def get_task(self, task_id: uuid.UUID) -> Optional[Task]:
        """Get task by ID"""
        return self.session.query(Task).filter(Task.id == task_id).first()
    
    def get_pending_tasks(self, agent_type: str = None) -> List[Task]:
        """Get pending tasks, optionally filtered by agent type"""
        query = self.session.query(Task).filter(Task.status == TaskStatus.PENDING)
        if agent_type:
            query = query.filter(Task.agent_type == agent_type)
        return query.order_by(Task.priority.desc(), Task.created_at).all()
    
    def get_agent_tasks(self, agent_id: uuid.UUID, status: TaskStatus = None) -> List[Task]:
        """Get tasks for specific agent"""
        query = self.session.query(Task).filter(Task.agent_id == agent_id)
        if status:
            query = query.filter(Task.status == status)
        return query.all()
    
    def update_task_status(self, task_id: uuid.UUID, status: TaskStatus, **kwargs):
        """Update task status"""
        update_data = {'status': status, 'updated_at': datetime.now(timezone.utc)}
        update_data.update(kwargs)
        
        self.session.query(Task).filter(Task.id == task_id).update(update_data)
        self.session.commit()
    
    def get_task_statistics(self) -> Dict[str, int]:
        """Get task statistics"""
        from sqlalchemy import func
        
        stats = self.session.query(
            Task.status,
            func.count(Task.id).label('count')
        ).group_by(Task.status).all()
        
        return {status.value: count for status, count in stats}


class OptimizationRepository:
    """Repository for optimization operations"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_recommendation(self, **kwargs) -> OptimizationRecommendation:
        """Create optimization recommendation"""
        recommendation = OptimizationRecommendation(**kwargs)
        self.session.add(recommendation)
        self.session.commit()
        self.session.refresh(recommendation)
        return recommendation
    
    def create_execution(self, **kwargs) -> OptimizationExecution:
        """Create optimization execution"""
        execution = OptimizationExecution(**kwargs)
        self.session.add(execution)
        self.session.commit()
        self.session.refresh(execution)
        return execution
    
    def get_pending_recommendations(self) -> List[OptimizationRecommendation]:
        """Get pending recommendations"""
        return self.session.query(OptimizationRecommendation).filter(
            OptimizationRecommendation.status == 'pending'
        ).all()
    
    def get_active_executions(self) -> List[OptimizationExecution]:
        """Get active executions"""
        return self.session.query(OptimizationExecution).filter(
            OptimizationExecution.status.in_([
                OptimizationStatus.ANALYZING,
                OptimizationStatus.PLANNING,
                OptimizationStatus.VALIDATING,
                OptimizationStatus.APPLYING,
                OptimizationStatus.TESTING
            ])
        ).all()
    
    def update_execution_status(self, execution_id: uuid.UUID, status: OptimizationStatus, **kwargs):
        """Update execution status"""
        update_data = {'status': status, 'updated_at': datetime.now(timezone.utc)}
        update_data.update(kwargs)
        
        self.session.query(OptimizationExecution).filter(
            OptimizationExecution.id == execution_id
        ).update(update_data)
        self.session.commit()


class MetricsRepository:
    """Repository for metrics operations"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def record_metric(self, **kwargs) -> SystemMetric:
        """Record system metric"""
        metric = SystemMetric(**kwargs)
        self.session.add(metric)
        self.session.commit()
        return metric
    
    def get_metrics(self, metric_name: str, source: str = None, 
                   since: datetime = None, limit: int = 1000) -> List[SystemMetric]:
        """Get metrics with filters"""
        query = self.session.query(SystemMetric).filter(SystemMetric.metric_name == metric_name)
        
        if source:
            query = query.filter(SystemMetric.source == source)
        
        if since:
            query = query.filter(SystemMetric.timestamp >= since)
        
        return query.order_by(SystemMetric.timestamp.desc()).limit(limit).all()
    
    def create_baseline(self, **kwargs) -> PerformanceBaseline:
        """Create performance baseline"""
        baseline = PerformanceBaseline(**kwargs)
        self.session.add(baseline)
        self.session.commit()
        return baseline
    
    def get_latest_baseline(self, component: str, metric_name: str) -> Optional[PerformanceBaseline]:
        """Get latest baseline for component and metric"""
        return self.session.query(PerformanceBaseline).filter(
            PerformanceBaseline.component == component,
            PerformanceBaseline.metric_name == metric_name
        ).order_by(PerformanceBaseline.measurement_date.desc()).first()
    
    def record_optimization_impact(self, **kwargs) -> OptimizationImpact:
        """Record optimization impact"""
        impact = OptimizationImpact(**kwargs)
        self.session.add(impact)
        self.session.commit()
        return impact


# Database initialization script
def initialize_database(database_url: str, drop_existing: bool = False):
    """Initialize database with tables and indexes"""
    db_manager = DatabaseManager(database_url)
    
    if drop_existing:
        print("Dropping existing tables...")
        db_manager.drop_tables()
    
    print("Creating tables...")
    db_manager.create_tables()
    
    print("Database initialization complete")
    return db_manager


# CLI interface
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='TGE Swarm Database Management')
    parser.add_argument('--database-url', required=True, help='Database URL')
    parser.add_argument('--init', action='store_true', help='Initialize database')
    parser.add_argument('--drop', action='store_true', help='Drop existing tables')
    
    args = parser.parse_args()
    
    if args.init:
        initialize_database(args.database_url, args.drop)
    else:
        print("Use --init to initialize the database")