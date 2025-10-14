#!/usr/bin/env python3
"""
Unit Tests for Optimization Engine
Tests optimization submission, execution, validation, and rollback
"""

import asyncio
import pytest
import uuid
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
import json

from backend.optimization_engine import (
    OptimizationEngine, OptimizationRecommendation, OptimizationExecution,
    OptimizationType, OptimizationStatus, OptimizationSeverity, OptimizationPlan
)
from backend.message_queue import MessageQueue
from backend.coordination_service import CoordinationService
from backend.websocket_manager import WebSocketManager


@pytest.mark.unit
class TestOptimizationEngine:
    """Test optimization engine functionality"""

    def test_optimization_engine_initialization(self):
        """Test optimization engine initialization"""
        mock_mq = MagicMock()
        mock_coord = MagicMock()
        mock_ws = MagicMock()

        engine = OptimizationEngine(mock_mq, mock_coord, mock_ws)

        assert engine.message_queue == mock_mq
        assert engine.coordination_service == mock_coord
        assert engine.websocket_manager == mock_ws
        assert engine.running is False
        assert len(engine.pending_recommendations) == 0
        assert len(engine.active_executions) == 0

    def test_default_config(self):
        """Test default configuration"""
        mock_mq = MagicMock()
        mock_coord = MagicMock()
        mock_ws = MagicMock()

        engine = OptimizationEngine(mock_mq, mock_coord, mock_ws)
        config = engine.config

        assert 'project_root' in config
        assert 'backup_dir' in config
        assert 'auto_apply_low_risk' in config
        assert 'rollback_on_failure' in config
        assert config['max_concurrent_optimizations'] == 3

    async def test_submit_recommendation(self):
        """Test submitting optimization recommendation"""
        mock_mq = AsyncMock()
        mock_coord = AsyncMock()
        mock_ws = AsyncMock()

        engine = OptimizationEngine(mock_mq, mock_coord, mock_ws)

        recommendation = OptimizationRecommendation(
            id=str(uuid.uuid4()),
            agent_id="test-agent",
            type=OptimizationType.CODE_OPTIMIZATION,
            severity=OptimizationSeverity.MEDIUM,
            title="Test Optimization",
            description="Test optimization for unit testing",
            target_files=["test_file.py"],
            proposed_changes=[{'type': 'code_replacement'}],
            expected_benefits=["Improved performance"],
            risk_assessment={'level': 'medium'},
            validation_requirements=['syntax_check'],
            created_at=datetime.now(),
            confidence_score=0.8
        )

        rec_id = await engine.submit_recommendation(recommendation)

        assert rec_id == recommendation.id
        assert recommendation.id in engine.pending_recommendations
        assert engine.optimization_metrics['total_recommendations'] == 1

    async def test_auto_apply_low_risk_recommendation(self):
        """Test auto-apply for low risk recommendations"""
        mock_mq = AsyncMock()
        mock_coord = AsyncMock()
        mock_ws = AsyncMock()

        config = {
            'auto_apply_low_risk': True,
            'max_concurrent_optimizations': 3,
            'backup_dir': tempfile.mkdtemp(),
            'temp_dir': tempfile.mkdtemp()
        }

        engine = OptimizationEngine(mock_mq, mock_coord, mock_ws, config=config)

        # Low risk, high confidence recommendation
        recommendation = OptimizationRecommendation(
            id=str(uuid.uuid4()),
            agent_id="test-agent",
            type=OptimizationType.CODE_OPTIMIZATION,
            severity=OptimizationSeverity.LOW,
            title="Low Risk Optimization",
            description="Safe optimization",
            target_files=["test_file.py"],
            proposed_changes=[],
            expected_benefits=["Minor improvement"],
            risk_assessment={'level': 'low'},
            validation_requirements=[],
            created_at=datetime.now(),
            confidence_score=0.9
        )

        with patch.object(engine, '_execute_single_optimization') as mock_execute:
            mock_execute.return_value = str(uuid.uuid4())

            should_auto_apply = await engine._should_auto_apply(recommendation)
            assert should_auto_apply is True

        # Cleanup
        shutil.rmtree(config['backup_dir'])
        shutil.rmtree(config['temp_dir'])

    async def test_create_optimization_plan(self):
        """Test creating optimization plan"""
        mock_mq = AsyncMock()
        mock_coord = AsyncMock()
        mock_ws = AsyncMock()

        engine = OptimizationEngine(mock_mq, mock_coord, mock_ws)

        # Create recommendations
        rec1 = OptimizationRecommendation(
            id=str(uuid.uuid4()),
            agent_id="test-agent",
            type=OptimizationType.CODE_OPTIMIZATION,
            severity=OptimizationSeverity.MEDIUM,
            title="Optimization 1",
            description="First optimization",
            target_files=["file1.py"],
            proposed_changes=[],
            expected_benefits=[],
            risk_assessment={},
            validation_requirements=[],
            created_at=datetime.now(),
            confidence_score=0.8
        )

        rec2 = OptimizationRecommendation(
            id=str(uuid.uuid4()),
            agent_id="test-agent",
            type=OptimizationType.PERFORMANCE_TUNING,
            severity=OptimizationSeverity.LOW,
            title="Optimization 2",
            description="Second optimization",
            target_files=["file2.py"],
            proposed_changes=[],
            expected_benefits=[],
            risk_assessment={},
            validation_requirements=[],
            created_at=datetime.now(),
            confidence_score=0.9
        )

        # Submit recommendations
        await engine.submit_recommendation(rec1)
        await engine.submit_recommendation(rec2)

        # Create plan
        plan_id = await engine.create_optimization_plan([rec1.id, rec2.id])

        assert plan_id != ""
        assert plan_id in engine.optimization_plans

        plan = engine.optimization_plans[plan_id]
        assert len(plan.recommendations) == 2
        assert plan.dependencies_resolved is True

    async def test_create_plan_with_invalid_recommendation(self):
        """Test creating plan with invalid recommendation ID"""
        mock_mq = AsyncMock()
        mock_coord = AsyncMock()
        mock_ws = AsyncMock()

        engine = OptimizationEngine(mock_mq, mock_coord, mock_ws)

        plan_id = await engine.create_optimization_plan(["nonexistent-id"])

        assert plan_id == ""

    async def test_validate_syntax_success(self):
        """Test syntax validation for valid Python file"""
        mock_mq = AsyncMock()
        mock_coord = AsyncMock()
        mock_ws = AsyncMock()

        # Create temporary Python file
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("print('Hello World')\n")

            config = {'project_root': temp_dir}
            engine = OptimizationEngine(mock_mq, mock_coord, mock_ws, config=config)

            recommendation = OptimizationRecommendation(
                id=str(uuid.uuid4()),
                agent_id="test-agent",
                type=OptimizationType.CODE_OPTIMIZATION,
                severity=OptimizationSeverity.LOW,
                title="Test",
                description="Test",
                target_files=["test.py"],
                proposed_changes=[],
                expected_benefits=[],
                risk_assessment={},
                validation_requirements=['syntax_check'],
                created_at=datetime.now(),
                confidence_score=0.8
            )

            result = await engine._validate_syntax(recommendation, 'pre')

            assert result['success'] is True
            assert len(result['errors']) == 0

    async def test_validate_syntax_failure(self):
        """Test syntax validation for invalid Python file"""
        mock_mq = AsyncMock()
        mock_coord = AsyncMock()
        mock_ws = AsyncMock()

        # Create temporary Python file with syntax error
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("def broken_function(\npass\n")  # Missing closing paren

            config = {'project_root': temp_dir}
            engine = OptimizationEngine(mock_mq, mock_coord, mock_ws, config=config)

            recommendation = OptimizationRecommendation(
                id=str(uuid.uuid4()),
                agent_id="test-agent",
                type=OptimizationType.CODE_OPTIMIZATION,
                severity=OptimizationSeverity.LOW,
                title="Test",
                description="Test",
                target_files=["test.py"],
                proposed_changes=[],
                expected_benefits=[],
                risk_assessment={},
                validation_requirements=['syntax_check'],
                created_at=datetime.now(),
                confidence_score=0.8
            )

            result = await engine._validate_syntax(recommendation, 'pre')

            assert result['success'] is False
            assert len(result['errors']) > 0

    async def test_create_backups(self):
        """Test creating file backups"""
        mock_mq = AsyncMock()
        mock_coord = AsyncMock()
        mock_ws = AsyncMock()

        # Create temporary files
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir) / "backups"
            backup_dir.mkdir()

            project_file = Path(temp_dir) / "test.py"
            project_file.write_text("original content")

            config = {
                'project_root': temp_dir,
                'backup_dir': str(backup_dir)
            }

            engine = OptimizationEngine(mock_mq, mock_coord, mock_ws, config=config)

            backup_data = await engine._create_backups(["test.py"])

            assert "test.py" in backup_data
            assert Path(backup_data["test.py"]).exists()

            # Verify backup content
            backup_content = Path(backup_data["test.py"]).read_text()
            assert backup_content == "original content"

    async def test_rollback_optimization(self):
        """Test rolling back optimization changes"""
        mock_mq = AsyncMock()
        mock_coord = AsyncMock()
        mock_ws = AsyncMock()

        # Create temporary files
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir) / "backups"
            backup_dir.mkdir()

            # Create original file
            project_file = Path(temp_dir) / "test.py"
            project_file.write_text("original content")

            # Create backup
            backup_file = backup_dir / "test.py_backup"
            backup_file.write_text("original content")

            # Modify file to simulate optimization
            project_file.write_text("modified content")

            config = {
                'project_root': temp_dir,
                'backup_dir': str(backup_dir)
            }

            engine = OptimizationEngine(mock_mq, mock_coord, mock_ws, config=config)

            # Create mock execution
            recommendation = OptimizationRecommendation(
                id=str(uuid.uuid4()),
                agent_id="test-agent",
                type=OptimizationType.CODE_OPTIMIZATION,
                severity=OptimizationSeverity.LOW,
                title="Test",
                description="Test",
                target_files=["test.py"],
                proposed_changes=[],
                expected_benefits=[],
                risk_assessment={},
                validation_requirements=[],
                created_at=datetime.now(),
                confidence_score=0.8
            )

            execution = OptimizationExecution(
                id=str(uuid.uuid4()),
                recommendation=recommendation,
                status=OptimizationStatus.FAILED,
                started_at=datetime.now(),
                completed_at=None,
                execution_log=[],
                validation_results={},
                rollback_data={"test.py": str(backup_file)},
                success_metrics={},
                error_message=None
            )

            # Rollback
            await engine._rollback_optimization(execution)

            # Verify file restored
            restored_content = project_file.read_text()
            assert restored_content == "original content"
            assert execution.status == OptimizationStatus.ROLLED_BACK

    async def test_apply_code_optimization(self):
        """Test applying code optimization"""
        mock_mq = AsyncMock()
        mock_coord = AsyncMock()
        mock_ws = AsyncMock()

        # Create temporary file
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("print('old message')")

            config = {'project_root': temp_dir}
            engine = OptimizationEngine(mock_mq, mock_coord, mock_ws, config=config)

            recommendation = OptimizationRecommendation(
                id=str(uuid.uuid4()),
                agent_id="test-agent",
                type=OptimizationType.CODE_OPTIMIZATION,
                severity=OptimizationSeverity.LOW,
                title="Test",
                description="Test",
                target_files=["test.py"],
                proposed_changes=[{
                    'type': 'code_replacement',
                    'file': 'test.py',
                    'old_code': "print('old message')",
                    'new_code': "print('new message')"
                }],
                expected_benefits=[],
                risk_assessment={},
                validation_requirements=[],
                created_at=datetime.now(),
                confidence_score=0.8
            )

            result = await engine._apply_code_optimization(
                recommendation, {}, plan_only=False
            )

            assert 'test.py' in result
            assert result['test.py']['success'] is True

            # Verify file modified
            modified_content = test_file.read_text()
            assert modified_content == "print('new message')"

    async def test_optimization_metrics_tracking(self):
        """Test optimization metrics are tracked"""
        mock_mq = AsyncMock()
        mock_coord = AsyncMock()
        mock_ws = AsyncMock()

        engine = OptimizationEngine(mock_mq, mock_coord, mock_ws)

        # Initial metrics
        assert engine.optimization_metrics['total_recommendations'] == 0
        assert engine.optimization_metrics['applied_optimizations'] == 0

        # Submit recommendation
        recommendation = OptimizationRecommendation(
            id=str(uuid.uuid4()),
            agent_id="test-agent",
            type=OptimizationType.CODE_OPTIMIZATION,
            severity=OptimizationSeverity.LOW,
            title="Test",
            description="Test",
            target_files=[],
            proposed_changes=[],
            expected_benefits=[],
            risk_assessment={},
            validation_requirements=[],
            created_at=datetime.now(),
            confidence_score=0.8
        )

        await engine.submit_recommendation(recommendation)

        assert engine.optimization_metrics['total_recommendations'] == 1

    async def test_requires_approval(self):
        """Test approval requirement logic"""
        mock_mq = AsyncMock()
        mock_coord = AsyncMock()
        mock_ws = AsyncMock()

        config = {'require_approval_threshold': 'medium'}
        engine = OptimizationEngine(mock_mq, mock_coord, mock_ws, config=config)

        # Low severity should not require approval
        assert engine._requires_approval(OptimizationSeverity.LOW) is False

        # Medium severity should require approval
        assert engine._requires_approval(OptimizationSeverity.MEDIUM) is True

        # High severity should require approval
        assert engine._requires_approval(OptimizationSeverity.HIGH) is True

        # Critical severity should require approval
        assert engine._requires_approval(OptimizationSeverity.CRITICAL) is True

    async def test_success_rate_calculation(self):
        """Test success rate calculation"""
        mock_mq = AsyncMock()
        mock_coord = AsyncMock()
        mock_ws = AsyncMock()

        engine = OptimizationEngine(mock_mq, mock_coord, mock_ws)

        # No optimizations yet
        engine._update_success_rate()
        assert engine.optimization_metrics['success_rate'] == 0.0

        # Add some successful and failed optimizations
        engine.optimization_metrics['applied_optimizations'] = 8
        engine.optimization_metrics['failed_optimizations'] = 2

        engine._update_success_rate()
        assert engine.optimization_metrics['success_rate'] == 0.8

    async def test_get_optimization_status(self):
        """Test getting optimization engine status"""
        mock_mq = AsyncMock()
        mock_coord = AsyncMock()
        mock_ws = AsyncMock()

        engine = OptimizationEngine(mock_mq, mock_coord, mock_ws)

        # Submit some recommendations
        rec1 = OptimizationRecommendation(
            id=str(uuid.uuid4()),
            agent_id="test-agent",
            type=OptimizationType.CODE_OPTIMIZATION,
            severity=OptimizationSeverity.LOW,
            title="Test 1",
            description="Test",
            target_files=[],
            proposed_changes=[],
            expected_benefits=[],
            risk_assessment={},
            validation_requirements=[],
            created_at=datetime.now(),
            confidence_score=0.8
        )

        await engine.submit_recommendation(rec1)

        status = await engine.get_optimization_status()

        assert 'timestamp' in status
        assert 'pending_recommendations' in status
        assert status['pending_recommendations'] == 1
        assert 'metrics' in status
        assert status['metrics']['total_recommendations'] == 1


@pytest.mark.unit
class TestOptimizationRecommendation:
    """Test optimization recommendation data structure"""

    def test_recommendation_creation(self):
        """Test creating optimization recommendation"""
        recommendation = OptimizationRecommendation(
            id=str(uuid.uuid4()),
            agent_id="test-agent",
            type=OptimizationType.CODE_OPTIMIZATION,
            severity=OptimizationSeverity.MEDIUM,
            title="Test Optimization",
            description="Test description",
            target_files=["file1.py", "file2.py"],
            proposed_changes=[
                {'type': 'code_replacement', 'file': 'file1.py'}
            ],
            expected_benefits=["Improved performance", "Better readability"],
            risk_assessment={'level': 'medium', 'impact': 'localized'},
            validation_requirements=['syntax_check', 'unit_tests'],
            created_at=datetime.now(),
            confidence_score=0.85
        )

        assert recommendation.type == OptimizationType.CODE_OPTIMIZATION
        assert recommendation.severity == OptimizationSeverity.MEDIUM
        assert len(recommendation.target_files) == 2
        assert recommendation.confidence_score == 0.85


@pytest.mark.unit
class TestOptimizationExecution:
    """Test optimization execution tracking"""

    def test_execution_creation(self):
        """Test creating optimization execution"""
        recommendation = OptimizationRecommendation(
            id=str(uuid.uuid4()),
            agent_id="test-agent",
            type=OptimizationType.CODE_OPTIMIZATION,
            severity=OptimizationSeverity.LOW,
            title="Test",
            description="Test",
            target_files=[],
            proposed_changes=[],
            expected_benefits=[],
            risk_assessment={},
            validation_requirements=[],
            created_at=datetime.now(),
            confidence_score=0.8
        )

        execution = OptimizationExecution(
            id=str(uuid.uuid4()),
            recommendation=recommendation,
            status=OptimizationStatus.PENDING,
            started_at=datetime.now(),
            completed_at=None,
            execution_log=[],
            validation_results={},
            rollback_data={},
            success_metrics={},
            error_message=None
        )

        assert execution.status == OptimizationStatus.PENDING
        assert execution.completed_at is None
        assert len(execution.execution_log) == 0

    def test_execution_with_results(self):
        """Test execution with completion results"""
        recommendation = OptimizationRecommendation(
            id=str(uuid.uuid4()),
            agent_id="test-agent",
            type=OptimizationType.PERFORMANCE_TUNING,
            severity=OptimizationSeverity.MEDIUM,
            title="Test",
            description="Test",
            target_files=[],
            proposed_changes=[],
            expected_benefits=[],
            risk_assessment={},
            validation_requirements=[],
            created_at=datetime.now(),
            confidence_score=0.8
        )

        started_at = datetime.now()
        completed_at = started_at + timedelta(seconds=30)

        execution = OptimizationExecution(
            id=str(uuid.uuid4()),
            recommendation=recommendation,
            status=OptimizationStatus.COMPLETED,
            started_at=started_at,
            completed_at=completed_at,
            execution_log=[
                {'timestamp': started_at.isoformat(), 'message': 'Started'},
                {'timestamp': completed_at.isoformat(), 'message': 'Completed'}
            ],
            validation_results={'pre': {'success': True}, 'post': {'success': True}},
            rollback_data={},
            success_metrics={'performance_improvement': '15%'},
            error_message=None
        )

        assert execution.status == OptimizationStatus.COMPLETED
        assert execution.completed_at is not None
        assert len(execution.execution_log) == 2
        assert 'performance_improvement' in execution.success_metrics


@pytest.mark.unit
class TestOptimizationPlan:
    """Test optimization plan data structure"""

    def test_plan_creation(self):
        """Test creating optimization plan"""
        rec1 = OptimizationRecommendation(
            id=str(uuid.uuid4()),
            agent_id="test-agent",
            type=OptimizationType.CODE_OPTIMIZATION,
            severity=OptimizationSeverity.LOW,
            title="Opt 1",
            description="Test",
            target_files=[],
            proposed_changes=[],
            expected_benefits=[],
            risk_assessment={},
            validation_requirements=[],
            created_at=datetime.now(),
            confidence_score=0.8
        )

        rec2 = OptimizationRecommendation(
            id=str(uuid.uuid4()),
            agent_id="test-agent",
            type=OptimizationType.PERFORMANCE_TUNING,
            severity=OptimizationSeverity.MEDIUM,
            title="Opt 2",
            description="Test",
            target_files=[],
            proposed_changes=[],
            expected_benefits=[],
            risk_assessment={},
            validation_requirements=[],
            created_at=datetime.now(),
            confidence_score=0.9
        )

        plan = OptimizationPlan(
            id=str(uuid.uuid4()),
            recommendations=[rec1, rec2],
            execution_order=[rec1.id, rec2.id],
            dependencies_resolved=True,
            estimated_duration=300,
            risk_level=OptimizationSeverity.MEDIUM,
            approval_required=True,
            created_at=datetime.now()
        )

        assert len(plan.recommendations) == 2
        assert plan.dependencies_resolved is True
        assert plan.risk_level == OptimizationSeverity.MEDIUM
        assert plan.approval_required is True
