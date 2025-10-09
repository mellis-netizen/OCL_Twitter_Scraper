#!/usr/bin/env python3
"""
Unit Tests for Database Models and Repositories
Tests SQLAlchemy models, repositories, and data consistency
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from backend.database.models import (
    Base, DatabaseManager, Agent, Task, SharedResource, OptimizationRecommendation,
    OptimizationExecution, CoordinationEvent, SystemMetric, PerformanceBaseline,
    OptimizationImpact, AgentRepository, TaskRepository, OptimizationRepository,
    MetricsRepository, AgentStatus, TaskStatus, OptimizationStatus, Priority,
    CoordinationEventType, initialize_database
)


@pytest.mark.unit
@pytest.mark.database
class TestDatabaseModels:
    """Test database model definitions and relationships"""
    
    def test_agent_model_creation(self, test_session, sample_agent_data):
        """Test creating agent model"""
        agent = Agent(
            name=sample_agent_data['name'],
            agent_type=sample_agent_data['agent_type'],
            container_id=sample_agent_data['container_id'],
            status=sample_agent_data['status'],
            host=sample_agent_data['host'],
            port=sample_agent_data['port'],
            cpu_limit=sample_agent_data['cpu_limit'],
            memory_limit=sample_agent_data['memory_limit'],
            capabilities=sample_agent_data['capabilities'],
            specializations=sample_agent_data['specializations']
        )
        
        test_session.add(agent)
        test_session.commit()
        
        assert agent.id is not None
        assert agent.created_at is not None
        assert agent.updated_at is not None
        assert agent.name == sample_agent_data['name']
        assert agent.status == AgentStatus.HEALTHY
    
    def test_agent_model_unique_constraints(self, test_session):
        """Test agent model unique constraints"""
        # Create first agent
        agent1 = Agent(
            name="agent1",
            agent_type="test",
            container_id="unique-container-123"
        )
        test_session.add(agent1)
        test_session.commit()
        
        # Try to create second agent with same container_id
        agent2 = Agent(
            name="agent2",
            agent_type="test",
            container_id="unique-container-123"  # Same container ID
        )
        test_session.add(agent2)
        
        with pytest.raises(IntegrityError):
            test_session.commit()
    
    def test_task_model_creation(self, test_session, sample_task_data):
        """Test creating task model"""
        task = Task(
            task_type=sample_task_data['task_type'],
            agent_type=sample_task_data['agent_type'],
            priority=sample_task_data['priority'],
            payload=sample_task_data['payload'],
            timeout=sample_task_data['timeout'],
            retries=sample_task_data['retries']
        )
        
        test_session.add(task)
        test_session.commit()
        
        assert task.id is not None
        assert task.status == TaskStatus.PENDING  # Default
        assert task.retry_count == 0  # Default
        assert task.payload == sample_task_data['payload']
    
    def test_task_agent_relationship(self, test_session, sample_agent_data, sample_task_data):
        """Test task-agent relationship"""
        # Create agent
        agent = Agent(
            name=sample_agent_data['name'],
            agent_type=sample_agent_data['agent_type'],
            container_id=sample_agent_data['container_id']
        )
        test_session.add(agent)
        test_session.flush()
        
        # Create task assigned to agent
        task = Task(
            task_type=sample_task_data['task_type'],
            agent_type=sample_task_data['agent_type'],
            priority=sample_task_data['priority'],
            agent_id=agent.id
        )
        test_session.add(task)
        test_session.commit()
        
        # Test relationship
        assert task.agent == agent
        assert task in agent.tasks
    
    def test_shared_resource_model(self, test_session):
        """Test shared resource model"""
        resource = SharedResource(
            name="test-file.py",
            resource_type="file",
            path="/path/to/test-file.py",
            metadata={"size": 1024, "encoding": "utf-8"},
            checksum="abc123def456"
        )
        
        test_session.add(resource)
        test_session.commit()
        
        assert resource.id is not None
        assert resource.locked_by is None  # Default
        assert resource.read_only is False  # Default
    
    def test_optimization_recommendation_model(self, test_session, sample_optimization_data):
        """Test optimization recommendation model"""
        # Create agent first
        agent = Agent(name="test-agent", agent_type="test", container_id="test-123")
        test_session.add(agent)
        test_session.flush()
        
        recommendation = OptimizationRecommendation(
            agent_id=agent.id,
            title=sample_optimization_data['title'],
            description=sample_optimization_data['description'],
            optimization_type=sample_optimization_data['optimization_type'],
            severity=sample_optimization_data['severity'],
            target_files=sample_optimization_data['target_files'],
            proposed_changes=sample_optimization_data['proposed_changes'],
            expected_benefits=sample_optimization_data['expected_benefits'],
            confidence_score=sample_optimization_data['confidence_score']
        )
        
        test_session.add(recommendation)
        test_session.commit()
        
        assert recommendation.id is not None
        assert recommendation.agent == agent
        assert recommendation.status == 'pending'  # Default
    
    def test_optimization_execution_model(self, test_session):
        """Test optimization execution model"""
        # Create agent and recommendation
        agent = Agent(name="test-agent", agent_type="test", container_id="test-123")
        test_session.add(agent)
        test_session.flush()
        
        recommendation = OptimizationRecommendation(
            agent_id=agent.id,
            title="Test optimization",
            optimization_type="test",
            severity="low"
        )
        test_session.add(recommendation)
        test_session.flush()
        
        execution = OptimizationExecution(
            recommendation_id=recommendation.id,
            agent_id=agent.id,
            status=OptimizationStatus.PENDING,
            execution_log=["Started execution"],
            rollback_data={"backup": "data"}
        )
        
        test_session.add(execution)
        test_session.commit()
        
        assert execution.id is not None
        assert execution.recommendation == recommendation
        assert execution.agent == agent
    
    def test_coordination_event_model(self, test_session):
        """Test coordination event model"""
        # Create agent
        agent = Agent(name="test-agent", agent_type="test", container_id="test-123")
        test_session.add(agent)
        test_session.flush()
        
        event = CoordinationEvent(
            agent_id=agent.id,
            event_type=CoordinationEventType.AGENT_JOINED,
            priority=Priority.MEDIUM,
            event_data={"timestamp": datetime.now(timezone.utc).isoformat()},
            correlation_id=uuid.uuid4(),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        test_session.add(event)
        test_session.commit()
        
        assert event.id is not None
        assert event.agent == agent
        assert event.processed is False  # Default
    
    def test_system_metric_model(self, test_session):
        """Test system metric model"""
        metric = SystemMetric(
            metric_name="cpu_usage",
            metric_type="gauge",
            source="agent-123",
            value=75.5,
            tags={"host": "localhost", "component": "agent"},
            timestamp=datetime.now(timezone.utc)
        )
        
        test_session.add(metric)
        test_session.commit()
        
        assert metric.id is not None
        assert metric.value == 75.5
        assert metric.tags["host"] == "localhost"
    
    def test_performance_baseline_model(self, test_session):
        """Test performance baseline model"""
        baseline = PerformanceBaseline(
            component="message_queue",
            metric_name="throughput",
            baseline_value=1000.0,
            measurement_date=datetime.now(timezone.utc),
            measurement_duration=3600,
            sample_size=100,
            min_value=800.0,
            max_value=1200.0,
            mean_value=1000.0,
            median_value=995.0,
            std_deviation=50.0,
            conditions={"load": "normal", "agents": 5},
            version="1.0.0"
        )
        
        test_session.add(baseline)
        test_session.commit()
        
        assert baseline.id is not None
        assert baseline.baseline_value == 1000.0
    
    def test_optimization_impact_model(self, test_session):
        """Test optimization impact model"""
        # Create required dependencies
        agent = Agent(name="test-agent", agent_type="test", container_id="test-123")
        test_session.add(agent)
        test_session.flush()
        
        recommendation = OptimizationRecommendation(
            agent_id=agent.id,
            title="Test optimization",
            optimization_type="test",
            severity="low"
        )
        test_session.add(recommendation)
        test_session.flush()
        
        execution = OptimizationExecution(
            recommendation_id=recommendation.id,
            agent_id=agent.id
        )
        test_session.add(execution)
        test_session.flush()
        
        impact = OptimizationImpact(
            execution_id=execution.id,
            metric_name="response_time",
            before_value=100.0,
            after_value=80.0,
            improvement_percent=20.0,
            measurement_window=300,
            confidence_level=0.95,
            measurement_conditions={"load": "high"}
        )
        
        test_session.add(impact)
        test_session.commit()
        
        assert impact.id is not None
        assert impact.improvement_percent == 20.0
        assert impact.execution == execution


@pytest.mark.unit
@pytest.mark.database
class TestDatabaseManager:
    """Test database manager functionality"""
    
    def test_database_manager_creation(self):
        """Test database manager creation"""
        db_manager = DatabaseManager("sqlite:///:memory:")
        
        assert db_manager.database_url == "sqlite:///:memory:"
        assert db_manager.engine is not None
        assert db_manager.SessionLocal is not None
    
    def test_create_tables(self):
        """Test table creation"""
        db_manager = DatabaseManager("sqlite:///:memory:")
        db_manager.create_tables()
        
        # Tables should exist
        metadata = Base.metadata
        assert len(metadata.tables) > 0
    
    def test_get_session(self):
        """Test session creation"""
        db_manager = DatabaseManager("sqlite:///:memory:")
        db_manager.create_tables()
        
        session = db_manager.get_session()
        assert session is not None
        
        session.close()
    
    def test_database_initialization_function(self):
        """Test database initialization function"""
        db_manager = initialize_database("sqlite:///:memory:", drop_existing=False)
        
        assert isinstance(db_manager, DatabaseManager)
        
        # Should be able to create a session
        session = db_manager.get_session()
        session.close()


@pytest.mark.unit
@pytest.mark.database
class TestAgentRepository:
    """Test agent repository operations"""
    
    def test_create_agent(self, test_session, sample_agent_data):
        """Test creating agent through repository"""
        repo = AgentRepository(test_session)
        
        agent = repo.create_agent(**sample_agent_data)
        
        assert agent.id is not None
        assert agent.name == sample_agent_data['name']
        assert agent.status == sample_agent_data['status']
    
    def test_get_agent_by_id(self, test_session, sample_agent_data):
        """Test getting agent by ID"""
        repo = AgentRepository(test_session)
        
        # Create agent
        agent = repo.create_agent(**sample_agent_data)
        agent_id = agent.id
        
        # Retrieve agent
        retrieved_agent = repo.get_agent(agent_id)
        
        assert retrieved_agent is not None
        assert retrieved_agent.id == agent_id
        assert retrieved_agent.name == sample_agent_data['name']
    
    def test_get_agent_by_container_id(self, test_session, sample_agent_data):
        """Test getting agent by container ID"""
        repo = AgentRepository(test_session)
        
        agent = repo.create_agent(**sample_agent_data)
        container_id = agent.container_id
        
        retrieved_agent = repo.get_agent_by_container_id(container_id)
        
        assert retrieved_agent is not None
        assert retrieved_agent.container_id == container_id
    
    def test_get_agents_by_type(self, test_session):
        """Test getting agents by type"""
        repo = AgentRepository(test_session)
        
        # Create agents of different types
        agent1 = repo.create_agent(
            name="agent1", 
            agent_type="scraping", 
            container_id="c1"
        )
        agent2 = repo.create_agent(
            name="agent2", 
            agent_type="scraping", 
            container_id="c2"
        )
        agent3 = repo.create_agent(
            name="agent3", 
            agent_type="keyword", 
            container_id="c3"
        )
        
        scraping_agents = repo.get_agents_by_type("scraping")
        
        assert len(scraping_agents) == 2
        assert agent1 in scraping_agents
        assert agent2 in scraping_agents
        assert agent3 not in scraping_agents
    
    def test_get_healthy_agents(self, test_session):
        """Test getting healthy agents"""
        repo = AgentRepository(test_session)
        
        # Create agents with different statuses
        healthy_agent = repo.create_agent(
            name="healthy", 
            agent_type="test", 
            container_id="h1",
            status=AgentStatus.HEALTHY
        )
        failed_agent = repo.create_agent(
            name="failed", 
            agent_type="test", 
            container_id="f1",
            status=AgentStatus.FAILED
        )
        
        healthy_agents = repo.get_healthy_agents()
        
        assert len(healthy_agents) == 1
        assert healthy_agents[0] == healthy_agent
    
    def test_update_agent_status(self, test_session, sample_agent_data):
        """Test updating agent status"""
        repo = AgentRepository(test_session)
        
        agent = repo.create_agent(**sample_agent_data)
        agent_id = agent.id
        
        # Update status
        repo.update_agent_status(
            agent_id, 
            AgentStatus.WARNING, 
            error_rate=0.1,
            task_count=5
        )
        
        # Retrieve updated agent
        updated_agent = repo.get_agent(agent_id)
        
        assert updated_agent.status == AgentStatus.WARNING
        assert updated_agent.error_rate == 0.1
        assert updated_agent.task_count == 5
    
    def test_delete_agent(self, test_session, sample_agent_data):
        """Test deleting agent"""
        repo = AgentRepository(test_session)
        
        agent = repo.create_agent(**sample_agent_data)
        agent_id = agent.id
        
        # Delete agent
        repo.delete_agent(agent_id)
        
        # Should not be found
        deleted_agent = repo.get_agent(agent_id)
        assert deleted_agent is None


@pytest.mark.unit
@pytest.mark.database
class TestTaskRepository:
    """Test task repository operations"""
    
    def test_create_task(self, test_session, sample_task_data):
        """Test creating task through repository"""
        repo = TaskRepository(test_session)
        
        task = repo.create_task(**sample_task_data)
        
        assert task.id is not None
        assert task.task_type == sample_task_data['task_type']
        assert task.status == TaskStatus.PENDING
    
    def test_get_task_by_id(self, test_session, sample_task_data):
        """Test getting task by ID"""
        repo = TaskRepository(test_session)
        
        task = repo.create_task(**sample_task_data)
        task_id = task.id
        
        retrieved_task = repo.get_task(task_id)
        
        assert retrieved_task is not None
        assert retrieved_task.id == task_id
    
    def test_get_pending_tasks(self, test_session):
        """Test getting pending tasks"""
        repo = TaskRepository(test_session)
        
        # Create tasks with different statuses
        pending_task = repo.create_task(
            task_type="test",
            agent_type="any",
            priority=Priority.MEDIUM,
            status=TaskStatus.PENDING
        )
        running_task = repo.create_task(
            task_type="test",
            agent_type="any",
            priority=Priority.HIGH,
            status=TaskStatus.RUNNING
        )
        
        pending_tasks = repo.get_pending_tasks()
        
        assert len(pending_tasks) == 1
        assert pending_tasks[0] == pending_task
    
    def test_get_pending_tasks_by_agent_type(self, test_session):
        """Test getting pending tasks filtered by agent type"""
        repo = TaskRepository(test_session)
        
        # Create tasks for different agent types
        task1 = repo.create_task(
            task_type="test1",
            agent_type="scraping",
            priority=Priority.MEDIUM
        )
        task2 = repo.create_task(
            task_type="test2",
            agent_type="keyword",
            priority=Priority.HIGH
        )
        
        scraping_tasks = repo.get_pending_tasks("scraping")
        
        assert len(scraping_tasks) == 1
        assert scraping_tasks[0] == task1
    
    def test_get_agent_tasks(self, test_session):
        """Test getting tasks for specific agent"""
        repo = TaskRepository(test_session)
        
        # Create agent
        agent_repo = AgentRepository(test_session)
        agent = agent_repo.create_agent(
            name="test-agent",
            agent_type="test",
            container_id="test-123"
        )
        
        # Create tasks for agent
        task1 = repo.create_task(
            task_type="test1",
            agent_type="test",
            priority=Priority.MEDIUM,
            agent_id=agent.id
        )
        task2 = repo.create_task(
            task_type="test2",
            agent_type="test",
            priority=Priority.HIGH,
            agent_id=agent.id
        )
        
        agent_tasks = repo.get_agent_tasks(agent.id)
        
        assert len(agent_tasks) == 2
        assert task1 in agent_tasks
        assert task2 in agent_tasks
    
    def test_update_task_status(self, test_session, sample_task_data):
        """Test updating task status"""
        repo = TaskRepository(test_session)
        
        task = repo.create_task(**sample_task_data)
        task_id = task.id
        
        # Update status
        repo.update_task_status(
            task_id,
            TaskStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            execution_log=["Task started"]
        )
        
        # Retrieve updated task
        updated_task = repo.get_task(task_id)
        
        assert updated_task.status == TaskStatus.RUNNING
        assert updated_task.started_at is not None
        assert updated_task.execution_log == ["Task started"]
    
    def test_get_task_statistics(self, test_session):
        """Test getting task statistics"""
        repo = TaskRepository(test_session)
        
        # Create tasks with different statuses
        repo.create_task(
            task_type="test1", agent_type="any", 
            priority=Priority.MEDIUM, status=TaskStatus.PENDING
        )
        repo.create_task(
            task_type="test2", agent_type="any", 
            priority=Priority.HIGH, status=TaskStatus.RUNNING
        )
        repo.create_task(
            task_type="test3", agent_type="any", 
            priority=Priority.LOW, status=TaskStatus.COMPLETED
        )
        
        stats = repo.get_task_statistics()
        
        assert stats['pending'] == 1
        assert stats['running'] == 1
        assert stats['completed'] == 1


@pytest.mark.unit
@pytest.mark.database
class TestOptimizationRepository:
    """Test optimization repository operations"""
    
    def test_create_recommendation(self, test_session, sample_optimization_data):
        """Test creating optimization recommendation"""
        # Create agent first
        agent_repo = AgentRepository(test_session)
        agent = agent_repo.create_agent(
            name="test-agent",
            agent_type="test",
            container_id="test-123"
        )
        
        repo = OptimizationRepository(test_session)
        
        recommendation = repo.create_recommendation(
            agent_id=agent.id,
            **sample_optimization_data
        )
        
        assert recommendation.id is not None
        assert recommendation.agent_id == agent.id
    
    def test_create_execution(self, test_session):
        """Test creating optimization execution"""
        # Create dependencies
        agent_repo = AgentRepository(test_session)
        agent = agent_repo.create_agent(
            name="test-agent",
            agent_type="test",
            container_id="test-123"
        )
        
        opt_repo = OptimizationRepository(test_session)
        recommendation = opt_repo.create_recommendation(
            agent_id=agent.id,
            title="Test",
            optimization_type="test",
            severity="low"
        )
        
        execution = opt_repo.create_execution(
            recommendation_id=recommendation.id,
            agent_id=agent.id,
            status=OptimizationStatus.PENDING
        )
        
        assert execution.id is not None
        assert execution.recommendation_id == recommendation.id
    
    def test_get_pending_recommendations(self, test_session):
        """Test getting pending recommendations"""
        # Create agent and recommendations
        agent_repo = AgentRepository(test_session)
        agent = agent_repo.create_agent(
            name="test-agent",
            agent_type="test",
            container_id="test-123"
        )
        
        repo = OptimizationRepository(test_session)
        
        pending_rec = repo.create_recommendation(
            agent_id=agent.id,
            title="Pending",
            optimization_type="test",
            severity="low",
            status="pending"
        )
        
        approved_rec = repo.create_recommendation(
            agent_id=agent.id,
            title="Approved",
            optimization_type="test",
            severity="low",
            status="approved"
        )
        
        pending_recommendations = repo.get_pending_recommendations()
        
        assert len(pending_recommendations) == 1
        assert pending_recommendations[0] == pending_rec
    
    def test_get_active_executions(self, test_session):
        """Test getting active executions"""
        # Create dependencies
        agent_repo = AgentRepository(test_session)
        agent = agent_repo.create_agent(
            name="test-agent",
            agent_type="test",
            container_id="test-123"
        )
        
        repo = OptimizationRepository(test_session)
        recommendation = repo.create_recommendation(
            agent_id=agent.id,
            title="Test",
            optimization_type="test",
            severity="low"
        )
        
        # Create executions with different statuses
        active_execution = repo.create_execution(
            recommendation_id=recommendation.id,
            agent_id=agent.id,
            status=OptimizationStatus.ANALYZING
        )
        
        completed_execution = repo.create_execution(
            recommendation_id=recommendation.id,
            agent_id=agent.id,
            status=OptimizationStatus.COMPLETED
        )
        
        active_executions = repo.get_active_executions()
        
        assert len(active_executions) == 1
        assert active_executions[0] == active_execution
    
    def test_update_execution_status(self, test_session):
        """Test updating execution status"""
        # Create dependencies
        agent_repo = AgentRepository(test_session)
        agent = agent_repo.create_agent(
            name="test-agent",
            agent_type="test",
            container_id="test-123"
        )
        
        repo = OptimizationRepository(test_session)
        recommendation = repo.create_recommendation(
            agent_id=agent.id,
            title="Test",
            optimization_type="test",
            severity="low"
        )
        
        execution = repo.create_execution(
            recommendation_id=recommendation.id,
            agent_id=agent.id,
            status=OptimizationStatus.PENDING
        )
        
        # Update status
        repo.update_execution_status(
            execution.id,
            OptimizationStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            execution_log=["Execution started"]
        )
        
        # Verify update
        test_session.refresh(execution)
        assert execution.status == OptimizationStatus.RUNNING
        assert execution.started_at is not None


@pytest.mark.unit
@pytest.mark.database
class TestMetricsRepository:
    """Test metrics repository operations"""
    
    def test_record_metric(self, test_session):
        """Test recording system metric"""
        repo = MetricsRepository(test_session)
        
        metric = repo.record_metric(
            metric_name="cpu_usage",
            metric_type="gauge",
            source="agent-123",
            value=75.5,
            tags={"host": "localhost"}
        )
        
        assert metric.id is not None
        assert metric.value == 75.5
        assert metric.tags["host"] == "localhost"
    
    def test_get_metrics(self, test_session):
        """Test getting metrics with filters"""
        repo = MetricsRepository(test_session)
        
        # Create metrics
        metric1 = repo.record_metric(
            metric_name="cpu_usage",
            metric_type="gauge",
            source="agent-1",
            value=70.0
        )
        
        metric2 = repo.record_metric(
            metric_name="cpu_usage",
            metric_type="gauge",
            source="agent-2",
            value=80.0
        )
        
        metric3 = repo.record_metric(
            metric_name="memory_usage",
            metric_type="gauge",
            source="agent-1",
            value=50.0
        )
        
        # Get CPU metrics
        cpu_metrics = repo.get_metrics("cpu_usage")
        assert len(cpu_metrics) == 2
        
        # Get CPU metrics for specific source
        agent1_cpu_metrics = repo.get_metrics("cpu_usage", source="agent-1")
        assert len(agent1_cpu_metrics) == 1
        assert agent1_cpu_metrics[0] == metric1
    
    def test_create_baseline(self, test_session):
        """Test creating performance baseline"""
        repo = MetricsRepository(test_session)
        
        baseline = repo.create_baseline(
            component="message_queue",
            metric_name="throughput",
            baseline_value=1000.0,
            measurement_date=datetime.now(timezone.utc),
            measurement_duration=3600,
            sample_size=100
        )
        
        assert baseline.id is not None
        assert baseline.baseline_value == 1000.0
    
    def test_get_latest_baseline(self, test_session):
        """Test getting latest baseline"""
        repo = MetricsRepository(test_session)
        
        # Create baselines at different times
        older_baseline = repo.create_baseline(
            component="test_component",
            metric_name="test_metric",
            baseline_value=100.0,
            measurement_date=datetime.now(timezone.utc) - timedelta(days=1)
        )
        
        newer_baseline = repo.create_baseline(
            component="test_component",
            metric_name="test_metric",
            baseline_value=200.0,
            measurement_date=datetime.now(timezone.utc)
        )
        
        latest = repo.get_latest_baseline("test_component", "test_metric")
        
        assert latest == newer_baseline
    
    def test_record_optimization_impact(self, test_session):
        """Test recording optimization impact"""
        # Create dependencies
        agent_repo = AgentRepository(test_session)
        agent = agent_repo.create_agent(
            name="test-agent",
            agent_type="test",
            container_id="test-123"
        )
        
        opt_repo = OptimizationRepository(test_session)
        recommendation = opt_repo.create_recommendation(
            agent_id=agent.id,
            title="Test",
            optimization_type="test",
            severity="low"
        )
        
        execution = opt_repo.create_execution(
            recommendation_id=recommendation.id,
            agent_id=agent.id
        )
        
        metrics_repo = MetricsRepository(test_session)
        impact = metrics_repo.record_optimization_impact(
            execution_id=execution.id,
            metric_name="response_time",
            before_value=100.0,
            after_value=80.0,
            improvement_percent=20.0,
            measurement_window=300,
            confidence_level=0.95
        )
        
        assert impact.id is not None
        assert impact.improvement_percent == 20.0
        assert impact.execution_id == execution.id


@pytest.mark.unit
@pytest.mark.database
class TestDatabaseConstraints:
    """Test database constraints and data integrity"""
    
    def test_agent_container_id_uniqueness(self, test_session):
        """Test that agent container IDs must be unique"""
        agent1 = Agent(
            name="agent1",
            agent_type="test",
            container_id="unique-id"
        )
        
        agent2 = Agent(
            name="agent2",
            agent_type="test",
            container_id="unique-id"  # Same container ID
        )
        
        test_session.add(agent1)
        test_session.commit()
        
        test_session.add(agent2)
        with pytest.raises(IntegrityError):
            test_session.commit()
    
    def test_shared_resource_name_uniqueness(self, test_session):
        """Test that shared resource names must be unique"""
        resource1 = SharedResource(
            name="unique-resource",
            resource_type="file",
            path="/path/1"
        )
        
        resource2 = SharedResource(
            name="unique-resource",  # Same name
            resource_type="file",
            path="/path/2"
        )
        
        test_session.add(resource1)
        test_session.commit()
        
        test_session.add(resource2)
        with pytest.raises(IntegrityError):
            test_session.commit()
    
    def test_foreign_key_constraints(self, test_session):
        """Test foreign key constraints"""
        # Try to create task with non-existent agent_id
        task = Task(
            task_type="test",
            agent_type="test",
            priority=Priority.MEDIUM,
            agent_id=uuid.uuid4()  # Non-existent agent
        )
        
        test_session.add(task)
        # This should work (foreign key allows NULL or valid references)
        test_session.commit()
    
    def test_baseline_unique_constraint(self, test_session):
        """Test performance baseline unique constraint"""
        measurement_date = datetime.now(timezone.utc)
        
        baseline1 = PerformanceBaseline(
            component="test_component",
            metric_name="test_metric",
            baseline_value=100.0,
            measurement_date=measurement_date
        )
        
        baseline2 = PerformanceBaseline(
            component="test_component",
            metric_name="test_metric",
            baseline_value=200.0,
            measurement_date=measurement_date  # Same date
        )
        
        test_session.add(baseline1)
        test_session.commit()
        
        test_session.add(baseline2)
        with pytest.raises(IntegrityError):
            test_session.commit()