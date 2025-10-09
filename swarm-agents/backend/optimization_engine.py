#!/usr/bin/env python3
"""
Optimization Engine for TGE Swarm
Applies agent recommendations and orchestrates system improvements
"""

import asyncio
import json
import logging
import os
import time
import uuid
import subprocess
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import hashlib
import ast
import re

from message_queue import MessageQueue, SwarmMessage, MessageType, Priority, TaskDefinition
from coordination_service import CoordinationService
from websocket_manager import WebSocketManager, RealTimeUpdate, UpdateType


class OptimizationType(Enum):
    """Types of optimizations"""
    CODE_OPTIMIZATION = "code_optimization"
    PERFORMANCE_TUNING = "performance_tuning"
    KEYWORD_ENHANCEMENT = "keyword_enhancement"
    API_IMPROVEMENT = "api_improvement"
    CONFIGURATION_UPDATE = "configuration_update"
    ARCHITECTURAL_CHANGE = "architectural_change"
    RESOURCE_OPTIMIZATION = "resource_optimization"


class OptimizationStatus(Enum):
    """Optimization execution status"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    VALIDATING = "validating"
    APPLYING = "applying"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class OptimizationSeverity(Enum):
    """Optimization impact severity"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class OptimizationRecommendation:
    """Agent optimization recommendation"""
    id: str
    agent_id: str
    type: OptimizationType
    severity: OptimizationSeverity
    title: str
    description: str
    target_files: List[str]
    proposed_changes: List[Dict[str, Any]]
    expected_benefits: List[str]
    risk_assessment: Dict[str, Any]
    validation_requirements: List[str]
    created_at: datetime
    confidence_score: float
    dependencies: List[str] = None


@dataclass
class OptimizationExecution:
    """Optimization execution tracking"""
    id: str
    recommendation: OptimizationRecommendation
    status: OptimizationStatus
    started_at: datetime
    completed_at: Optional[datetime]
    execution_log: List[Dict[str, Any]]
    validation_results: Dict[str, Any]
    rollback_data: Dict[str, Any]
    success_metrics: Dict[str, Any]
    error_message: Optional[str]


@dataclass
class OptimizationPlan:
    """Comprehensive optimization plan"""
    id: str
    recommendations: List[OptimizationRecommendation]
    execution_order: List[str]
    dependencies_resolved: bool
    estimated_duration: int
    risk_level: OptimizationSeverity
    approval_required: bool
    created_at: datetime


class OptimizationEngine:
    """Advanced optimization engine for applying agent recommendations"""
    
    def __init__(self, message_queue: MessageQueue, coordination_service: CoordinationService,
                 websocket_manager: WebSocketManager, config: Dict[str, Any] = None):
        self.message_queue = message_queue
        self.coordination_service = coordination_service
        self.websocket_manager = websocket_manager
        self.config = config or self._default_config()
        
        # State management
        self.pending_recommendations: Dict[str, OptimizationRecommendation] = {}
        self.active_executions: Dict[str, OptimizationExecution] = {}
        self.completed_optimizations: List[OptimizationExecution] = []
        self.optimization_plans: Dict[str, OptimizationPlan] = {}
        
        # File system paths
        self.project_root = Path(self.config.get('project_root', '../'))
        self.backup_dir = Path(self.config.get('backup_dir', './backups'))
        self.temp_dir = Path(self.config.get('temp_dir', './temp'))
        
        # Create necessary directories
        self.backup_dir.mkdir(exist_ok=True, parents=True)
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        
        # Optimization strategies
        self.optimization_strategies = {
            OptimizationType.CODE_OPTIMIZATION: self._apply_code_optimization,
            OptimizationType.PERFORMANCE_TUNING: self._apply_performance_tuning,
            OptimizationType.KEYWORD_ENHANCEMENT: self._apply_keyword_enhancement,
            OptimizationType.API_IMPROVEMENT: self._apply_api_improvement,
            OptimizationType.CONFIGURATION_UPDATE: self._apply_configuration_update,
            OptimizationType.ARCHITECTURAL_CHANGE: self._apply_architectural_change,
            OptimizationType.RESOURCE_OPTIMIZATION: self._apply_resource_optimization
        }
        
        # Validation strategies
        self.validation_strategies = {
            'syntax_check': self._validate_syntax,
            'unit_tests': self._run_unit_tests,
            'integration_tests': self._run_integration_tests,
            'performance_benchmark': self._run_performance_benchmark,
            'security_scan': self._run_security_scan,
            'configuration_validation': self._validate_configuration
        }
        
        # Performance tracking
        self.optimization_metrics = {
            'total_recommendations': 0,
            'applied_optimizations': 0,
            'failed_optimizations': 0,
            'rolled_back_optimizations': 0,
            'avg_execution_time': 0.0,
            'success_rate': 0.0
        }
        
        self.running = False
        self.setup_logging()
    
    def setup_logging(self):
        """Setup optimization engine logging"""
        self.logger = logging.getLogger("OptimizationEngine")
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for optimization engine"""
        return {
            'project_root': '../',
            'backup_dir': './backups',
            'temp_dir': './temp',
            'auto_apply_low_risk': False,
            'require_approval_threshold': 'medium',
            'max_concurrent_optimizations': 3,
            'rollback_on_failure': True,
            'validation_timeout': 300,
            'backup_retention_days': 30,
            'performance_baseline_file': 'performance_baseline.json'
        }
    
    async def initialize(self):
        """Initialize optimization engine"""
        # Subscribe to optimization requests
        await self.message_queue.subscribe_to_broadcast(self._handle_optimization_message)
        
        # Start optimization loops
        self.running = True
        asyncio.create_task(self._optimization_processing_loop())
        asyncio.create_task(self._validation_monitoring_loop())
        asyncio.create_task(self._cleanup_loop())
        
        # Load performance baseline
        await self._load_performance_baseline()
        
        self.logger.info("Optimization engine initialized")
    
    async def submit_recommendation(self, recommendation: OptimizationRecommendation) -> str:
        """Submit optimization recommendation for processing"""
        try:
            # Store recommendation
            self.pending_recommendations[recommendation.id] = recommendation
            
            # Update metrics
            self.optimization_metrics['total_recommendations'] += 1
            
            # Send real-time update
            await self._send_realtime_update(UpdateType.OPTIMIZATION_RESULT, {
                'action': 'recommendation_submitted',
                'recommendation_id': recommendation.id,
                'type': recommendation.type.value,
                'severity': recommendation.severity.value,
                'agent_id': recommendation.agent_id
            })
            
            self.logger.info(f"Submitted optimization recommendation {recommendation.id} from agent {recommendation.agent_id}")
            
            # Check if auto-apply conditions are met
            if await self._should_auto_apply(recommendation):
                await self._create_and_execute_plan([recommendation])
            
            return recommendation.id
            
        except Exception as e:
            self.logger.error(f"Failed to submit recommendation {recommendation.id}: {e}")
            return ""
    
    async def create_optimization_plan(self, recommendation_ids: List[str]) -> str:
        """Create optimization plan from multiple recommendations"""
        try:
            recommendations = []
            for rec_id in recommendation_ids:
                if rec_id in self.pending_recommendations:
                    recommendations.append(self.pending_recommendations[rec_id])
                else:
                    raise ValueError(f"Recommendation {rec_id} not found")
            
            if not recommendations:
                raise ValueError("No valid recommendations provided")
            
            # Analyze dependencies and create execution order
            execution_order, dependencies_resolved = await self._analyze_dependencies(recommendations)
            
            # Calculate risk level and estimated duration
            risk_level = self._calculate_overall_risk(recommendations)
            estimated_duration = self._estimate_execution_duration(recommendations)
            
            # Create plan
            plan = OptimizationPlan(
                id=str(uuid.uuid4()),
                recommendations=recommendations,
                execution_order=execution_order,
                dependencies_resolved=dependencies_resolved,
                estimated_duration=estimated_duration,
                risk_level=risk_level,
                approval_required=self._requires_approval(risk_level),
                created_at=datetime.now()
            )
            
            self.optimization_plans[plan.id] = plan
            
            # Send real-time update
            await self._send_realtime_update(UpdateType.OPTIMIZATION_RESULT, {
                'action': 'plan_created',
                'plan_id': plan.id,
                'recommendations_count': len(recommendations),
                'risk_level': risk_level.value,
                'estimated_duration': estimated_duration,
                'approval_required': plan.approval_required
            })
            
            self.logger.info(f"Created optimization plan {plan.id} with {len(recommendations)} recommendations")
            return plan.id
            
        except Exception as e:
            self.logger.error(f"Failed to create optimization plan: {e}")
            return ""
    
    async def execute_optimization_plan(self, plan_id: str, force: bool = False) -> bool:
        """Execute optimization plan"""
        try:
            if plan_id not in self.optimization_plans:
                raise ValueError(f"Plan {plan_id} not found")
            
            plan = self.optimization_plans[plan_id]
            
            # Check approval requirements
            if plan.approval_required and not force:
                self.logger.warning(f"Plan {plan_id} requires approval but force=False")
                return False
            
            # Check dependencies
            if not plan.dependencies_resolved:
                self.logger.warning(f"Plan {plan_id} has unresolved dependencies")
                return False
            
            # Check concurrent execution limit
            if len(self.active_executions) >= self.config['max_concurrent_optimizations']:
                self.logger.warning(f"Maximum concurrent optimizations reached")
                return False
            
            # Execute recommendations in order
            success_count = 0
            for rec_id in plan.execution_order:
                recommendation = next(r for r in plan.recommendations if r.id == rec_id)
                
                execution_id = await self._execute_single_optimization(recommendation)
                if execution_id:
                    # Wait for completion
                    success = await self._wait_for_optimization_completion(execution_id)
                    if success:
                        success_count += 1
                    else:
                        # Handle failure based on configuration
                        if self.config['rollback_on_failure']:
                            await self._rollback_plan_execution(plan, success_count)
                        break
            
            # Update plan status
            plan_success = success_count == len(plan.recommendations)
            
            # Send real-time update
            await self._send_realtime_update(UpdateType.OPTIMIZATION_RESULT, {
                'action': 'plan_completed',
                'plan_id': plan_id,
                'success': plan_success,
                'completed_optimizations': success_count,
                'total_optimizations': len(plan.recommendations)
            })
            
            self.logger.info(f"Plan {plan_id} execution completed: {success_count}/{len(plan.recommendations)} successful")
            return plan_success
            
        except Exception as e:
            self.logger.error(f"Failed to execute optimization plan {plan_id}: {e}")
            return False
    
    async def _execute_single_optimization(self, recommendation: OptimizationRecommendation) -> str:
        """Execute single optimization recommendation"""
        try:
            execution_id = str(uuid.uuid4())
            
            # Create execution record
            execution = OptimizationExecution(
                id=execution_id,
                recommendation=recommendation,
                status=OptimizationStatus.ANALYZING,
                started_at=datetime.now(),
                completed_at=None,
                execution_log=[],
                validation_results={},
                rollback_data={},
                success_metrics={},
                error_message=None
            )
            
            self.active_executions[execution_id] = execution
            
            # Remove from pending
            if recommendation.id in self.pending_recommendations:
                del self.pending_recommendations[recommendation.id]
            
            # Log execution start
            await self._log_execution_step(execution, "Optimization execution started")
            
            # Send real-time update
            await self._send_realtime_update(UpdateType.OPTIMIZATION_RESULT, {
                'action': 'optimization_started',
                'execution_id': execution_id,
                'recommendation_id': recommendation.id,
                'type': recommendation.type.value
            })
            
            # Start async execution
            asyncio.create_task(self._execute_optimization_workflow(execution))
            
            return execution_id
            
        except Exception as e:
            self.logger.error(f"Failed to start optimization execution: {e}")
            return ""
    
    async def _execute_optimization_workflow(self, execution: OptimizationExecution):
        """Execute complete optimization workflow"""
        try:
            recommendation = execution.recommendation
            
            # Step 1: Analysis
            execution.status = OptimizationStatus.ANALYZING
            await self._log_execution_step(execution, "Analyzing optimization requirements")
            
            analysis_result = await self._analyze_optimization(recommendation)
            if not analysis_result['success']:
                raise Exception(f"Analysis failed: {analysis_result['error']}")
            
            # Step 2: Planning
            execution.status = OptimizationStatus.PLANNING
            await self._log_execution_step(execution, "Creating optimization plan")
            
            plan_result = await self._plan_optimization(recommendation, analysis_result['data'])
            if not plan_result['success']:
                raise Exception(f"Planning failed: {plan_result['error']}")
            
            # Step 3: Create backups
            await self._log_execution_step(execution, "Creating file backups")
            backup_result = await self._create_backups(recommendation.target_files)
            execution.rollback_data = backup_result
            
            # Step 4: Validation (pre-apply)
            execution.status = OptimizationStatus.VALIDATING
            await self._log_execution_step(execution, "Running pre-apply validation")
            
            pre_validation = await self._run_validations(recommendation, 'pre')
            execution.validation_results['pre'] = pre_validation
            
            if not pre_validation['success']:
                raise Exception(f"Pre-validation failed: {pre_validation['errors']}")
            
            # Step 5: Apply optimization
            execution.status = OptimizationStatus.APPLYING
            await self._log_execution_step(execution, "Applying optimization changes")
            
            apply_result = await self._apply_optimization(recommendation, plan_result['data'])
            if not apply_result['success']:
                raise Exception(f"Application failed: {apply_result['error']}")
            
            # Step 6: Post-apply validation
            execution.status = OptimizationStatus.TESTING
            await self._log_execution_step(execution, "Running post-apply validation")
            
            post_validation = await self._run_validations(recommendation, 'post')
            execution.validation_results['post'] = post_validation
            
            if not post_validation['success']:
                # Rollback if validation fails
                await self._log_execution_step(execution, "Post-validation failed, rolling back")
                await self._rollback_optimization(execution)
                raise Exception(f"Post-validation failed: {post_validation['errors']}")
            
            # Step 7: Success metrics collection
            execution.success_metrics = await self._collect_success_metrics(recommendation)
            
            # Step 8: Complete
            execution.status = OptimizationStatus.COMPLETED
            execution.completed_at = datetime.now()
            await self._log_execution_step(execution, "Optimization completed successfully")
            
            # Update global metrics
            self.optimization_metrics['applied_optimizations'] += 1
            self._update_success_rate()
            
            # Move to completed
            self.completed_optimizations.append(execution)
            del self.active_executions[execution.id]
            
            # Send real-time update
            await self._send_realtime_update(UpdateType.OPTIMIZATION_RESULT, {
                'action': 'optimization_completed',
                'execution_id': execution.id,
                'success': True,
                'duration': (execution.completed_at - execution.started_at).total_seconds(),
                'metrics': execution.success_metrics
            })
            
        except Exception as e:
            # Handle failure
            execution.status = OptimizationStatus.FAILED
            execution.completed_at = datetime.now()
            execution.error_message = str(e)
            
            await self._log_execution_step(execution, f"Optimization failed: {e}")
            
            # Rollback if configured
            if self.config['rollback_on_failure']:
                await self._rollback_optimization(execution)
            
            # Update metrics
            self.optimization_metrics['failed_optimizations'] += 1
            self._update_success_rate()
            
            # Move to completed (with failure status)
            self.completed_optimizations.append(execution)
            if execution.id in self.active_executions:
                del self.active_executions[execution.id]
            
            # Send real-time update
            await self._send_realtime_update(UpdateType.OPTIMIZATION_RESULT, {
                'action': 'optimization_failed',
                'execution_id': execution.id,
                'success': False,
                'error': str(e),
                'duration': (execution.completed_at - execution.started_at).total_seconds()
            })
            
            self.logger.error(f"Optimization {execution.id} failed: {e}")
    
    async def _analyze_optimization(self, recommendation: OptimizationRecommendation) -> Dict[str, Any]:
        """Analyze optimization requirements"""
        try:
            analysis_data = {
                'target_files_exist': [],
                'file_dependencies': [],
                'resource_requirements': {},
                'compatibility_check': {}
            }
            
            # Check target files exist
            for file_path in recommendation.target_files:
                full_path = self.project_root / file_path
                analysis_data['target_files_exist'].append({
                    'file': file_path,
                    'exists': full_path.exists(),
                    'readable': full_path.is_file() and os.access(full_path, os.R_OK),
                    'writable': full_path.is_file() and os.access(full_path, os.W_OK)
                })
            
            # Analyze file dependencies
            analysis_data['file_dependencies'] = await self._analyze_file_dependencies(recommendation.target_files)
            
            # Check resource requirements
            analysis_data['resource_requirements'] = await self._estimate_resource_requirements(recommendation)
            
            # Compatibility check
            analysis_data['compatibility_check'] = await self._check_compatibility(recommendation)
            
            return {'success': True, 'data': analysis_data}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _plan_optimization(self, recommendation: OptimizationRecommendation, 
                               analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create detailed optimization plan"""
        try:
            plan_data = {
                'steps': [],
                'file_operations': [],
                'validation_sequence': [],
                'rollback_plan': []
            }
            
            # Plan steps based on optimization type
            strategy = self.optimization_strategies.get(recommendation.type)
            if strategy:
                strategy_plan = await strategy(recommendation, analysis_data, plan_only=True)
                plan_data.update(strategy_plan)
            
            return {'success': True, 'data': plan_data}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _apply_optimization(self, recommendation: OptimizationRecommendation, 
                                plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply optimization using appropriate strategy"""
        try:
            strategy = self.optimization_strategies.get(recommendation.type)
            if not strategy:
                raise ValueError(f"No strategy for optimization type: {recommendation.type}")
            
            result = await strategy(recommendation, plan_data, plan_only=False)
            return {'success': True, 'data': result}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # Optimization strategy implementations
    async def _apply_code_optimization(self, recommendation: OptimizationRecommendation, 
                                     data: Dict[str, Any], plan_only: bool = False) -> Dict[str, Any]:
        """Apply code optimization changes"""
        if plan_only:
            return {
                'steps': ['Analyze code structure', 'Apply optimizations', 'Verify syntax'],
                'file_operations': [{'action': 'modify', 'files': recommendation.target_files}]
            }
        
        try:
            results = {}
            
            for change in recommendation.proposed_changes:
                if change['type'] == 'code_replacement':
                    file_path = self.project_root / change['file']
                    
                    # Read current content
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Apply replacement
                    old_code = change['old_code']
                    new_code = change['new_code']
                    
                    if old_code in content:
                        new_content = content.replace(old_code, new_code)
                        
                        # Write updated content
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        
                        results[change['file']] = {
                            'success': True,
                            'changes_applied': 1,
                            'lines_modified': len(new_code.splitlines()) - len(old_code.splitlines())
                        }
                    else:
                        results[change['file']] = {
                            'success': False,
                            'error': 'Target code not found'
                        }
            
            return results
            
        except Exception as e:
            self.logger.error(f"Code optimization failed: {e}")
            raise
    
    async def _apply_performance_tuning(self, recommendation: OptimizationRecommendation,
                                      data: Dict[str, Any], plan_only: bool = False) -> Dict[str, Any]:
        """Apply performance tuning optimizations"""
        if plan_only:
            return {
                'steps': ['Baseline measurement', 'Apply tuning', 'Performance verification'],
                'file_operations': [{'action': 'modify', 'files': recommendation.target_files}]
            }
        
        try:
            results = {}
            
            # Apply performance-specific changes
            for change in recommendation.proposed_changes:
                if change['type'] == 'async_optimization':
                    # Convert synchronous code to async
                    results.update(await self._apply_async_optimization(change))
                elif change['type'] == 'memory_optimization':
                    # Apply memory usage optimizations
                    results.update(await self._apply_memory_optimization(change))
                elif change['type'] == 'algorithm_optimization':
                    # Apply algorithmic improvements
                    results.update(await self._apply_algorithm_optimization(change))
            
            return results
            
        except Exception as e:
            self.logger.error(f"Performance tuning failed: {e}")
            raise
    
    async def _apply_keyword_enhancement(self, recommendation: OptimizationRecommendation,
                                       data: Dict[str, Any], plan_only: bool = False) -> Dict[str, Any]:
        """Apply keyword enhancement optimizations"""
        if plan_only:
            return {
                'steps': ['Analyze current keywords', 'Update keyword lists', 'Validate changes'],
                'file_operations': [{'action': 'modify', 'files': ['config.py']}]
            }
        
        try:
            results = {}
            
            # Apply keyword-specific changes
            for change in recommendation.proposed_changes:
                if change['type'] == 'keyword_addition':
                    results.update(await self._add_keywords(change))
                elif change['type'] == 'keyword_removal':
                    results.update(await self._remove_keywords(change))
                elif change['type'] == 'keyword_refinement':
                    results.update(await self._refine_keywords(change))
            
            return results
            
        except Exception as e:
            self.logger.error(f"Keyword enhancement failed: {e}")
            raise
    
    async def _apply_api_improvement(self, recommendation: OptimizationRecommendation,
                                   data: Dict[str, Any], plan_only: bool = False) -> Dict[str, Any]:
        """Apply API improvement optimizations"""
        if plan_only:
            return {
                'steps': ['Analyze API usage', 'Update API integration', 'Test connectivity'],
                'file_operations': [{'action': 'modify', 'files': recommendation.target_files}]
            }
        
        try:
            results = {}
            
            # Apply API-specific improvements
            for change in recommendation.proposed_changes:
                if change['type'] == 'error_handling':
                    results.update(await self._improve_error_handling(change))
                elif change['type'] == 'rate_limiting':
                    results.update(await self._improve_rate_limiting(change))
                elif change['type'] == 'retry_logic':
                    results.update(await self._improve_retry_logic(change))
            
            return results
            
        except Exception as e:
            self.logger.error(f"API improvement failed: {e}")
            raise
    
    async def _apply_configuration_update(self, recommendation: OptimizationRecommendation,
                                        data: Dict[str, Any], plan_only: bool = False) -> Dict[str, Any]:
        """Apply configuration updates"""
        if plan_only:
            return {
                'steps': ['Backup config', 'Update settings', 'Validate config'],
                'file_operations': [{'action': 'modify', 'files': recommendation.target_files}]
            }
        
        try:
            results = {}
            
            for change in recommendation.proposed_changes:
                if change['type'] == 'config_update':
                    file_path = self.project_root / change['file']
                    
                    if change['format'] == 'python':
                        results.update(await self._update_python_config(file_path, change))
                    elif change['format'] == 'yaml':
                        results.update(await self._update_yaml_config(file_path, change))
                    elif change['format'] == 'json':
                        results.update(await self._update_json_config(file_path, change))
            
            return results
            
        except Exception as e:
            self.logger.error(f"Configuration update failed: {e}")
            raise
    
    async def _apply_architectural_change(self, recommendation: OptimizationRecommendation,
                                        data: Dict[str, Any], plan_only: bool = False) -> Dict[str, Any]:
        """Apply architectural changes"""
        if plan_only:
            return {
                'steps': ['Plan architecture', 'Implement changes', 'Integration test'],
                'file_operations': [{'action': 'modify', 'files': recommendation.target_files}]
            }
        
        # Architectural changes require manual review
        raise NotImplementedError("Architectural changes require manual implementation")
    
    async def _apply_resource_optimization(self, recommendation: OptimizationRecommendation,
                                         data: Dict[str, Any], plan_only: bool = False) -> Dict[str, Any]:
        """Apply resource optimization"""
        if plan_only:
            return {
                'steps': ['Analyze resource usage', 'Apply optimizations', 'Monitor impact'],
                'file_operations': [{'action': 'modify', 'files': recommendation.target_files}]
            }
        
        try:
            results = {}
            
            for change in recommendation.proposed_changes:
                if change['type'] == 'memory_optimization':
                    results.update(await self._optimize_memory_usage(change))
                elif change['type'] == 'cpu_optimization':
                    results.update(await self._optimize_cpu_usage(change))
                elif change['type'] == 'io_optimization':
                    results.update(await self._optimize_io_operations(change))
            
            return results
            
        except Exception as e:
            self.logger.error(f"Resource optimization failed: {e}")
            raise
    
    # Validation implementations
    async def _run_validations(self, recommendation: OptimizationRecommendation, 
                             phase: str) -> Dict[str, Any]:
        """Run validation checks"""
        results = {'success': True, 'errors': [], 'warnings': []}
        
        for validation in recommendation.validation_requirements:
            if validation in self.validation_strategies:
                try:
                    result = await self.validation_strategies[validation](recommendation, phase)
                    
                    if not result['success']:
                        results['success'] = False
                        results['errors'].extend(result.get('errors', []))
                    
                    results['warnings'].extend(result.get('warnings', []))
                    
                except Exception as e:
                    results['success'] = False
                    results['errors'].append(f"Validation {validation} failed: {e}")
        
        return results
    
    async def _validate_syntax(self, recommendation: OptimizationRecommendation, 
                             phase: str) -> Dict[str, Any]:
        """Validate Python syntax"""
        results = {'success': True, 'errors': [], 'warnings': []}
        
        for file_path in recommendation.target_files:
            if file_path.endswith('.py'):
                full_path = self.project_root / file_path
                
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Parse AST to check syntax
                    ast.parse(content)
                    
                except SyntaxError as e:
                    results['success'] = False
                    results['errors'].append(f"Syntax error in {file_path}: {e}")
                except Exception as e:
                    results['errors'].append(f"Could not validate {file_path}: {e}")
        
        return results
    
    async def _run_unit_tests(self, recommendation: OptimizationRecommendation,
                            phase: str) -> Dict[str, Any]:
        """Run unit tests"""
        results = {'success': True, 'errors': [], 'warnings': []}
        
        try:
            # Run pytest on relevant test files
            test_command = ['python', '-m', 'pytest', '-v', '--tb=short']
            
            # Add specific test files if they exist
            for file_path in recommendation.target_files:
                test_file = file_path.replace('.py', '_test.py')
                test_path = self.project_root / 'tests' / test_file
                if test_path.exists():
                    test_command.append(str(test_path))
            
            # Run tests
            process = await asyncio.create_subprocess_exec(
                *test_command,
                cwd=self.project_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=self.config['validation_timeout']
            )
            
            if process.returncode != 0:
                results['success'] = False
                results['errors'].append(f"Unit tests failed: {stderr.decode()}")
            
        except asyncio.TimeoutError:
            results['success'] = False
            results['errors'].append("Unit tests timed out")
        except Exception as e:
            results['warnings'].append(f"Could not run unit tests: {e}")
        
        return results
    
    async def _run_integration_tests(self, recommendation: OptimizationRecommendation,
                                   phase: str) -> Dict[str, Any]:
        """Run integration tests"""
        results = {'success': True, 'errors': [], 'warnings': []}
        
        try:
            # Run integration test suite
            test_command = ['python', '-m', 'pytest', 'tests/integration/', '-v']
            
            process = await asyncio.create_subprocess_exec(
                *test_command,
                cwd=self.project_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config['validation_timeout'] * 2
            )
            
            if process.returncode != 0:
                results['success'] = False
                results['errors'].append(f"Integration tests failed: {stderr.decode()}")
            
        except asyncio.TimeoutError:
            results['success'] = False
            results['errors'].append("Integration tests timed out")
        except Exception as e:
            results['warnings'].append(f"Could not run integration tests: {e}")
        
        return results
    
    async def _run_performance_benchmark(self, recommendation: OptimizationRecommendation,
                                       phase: str) -> Dict[str, Any]:
        """Run performance benchmarks"""
        results = {'success': True, 'errors': [], 'warnings': []}
        
        try:
            # Run performance benchmark script
            benchmark_script = self.project_root / 'src' / 'performance_benchmarks.py'
            
            if benchmark_script.exists():
                process = await asyncio.create_subprocess_exec(
                    'python', str(benchmark_script),
                    cwd=self.project_root,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.config['validation_timeout'] * 3
                )
                
                if process.returncode != 0:
                    results['warnings'].append(f"Performance benchmark issues: {stderr.decode()}")
                else:
                    # Parse benchmark results
                    try:
                        benchmark_data = json.loads(stdout.decode())
                        results['benchmark_data'] = benchmark_data
                    except:
                        results['warnings'].append("Could not parse benchmark results")
            else:
                results['warnings'].append("No performance benchmark script found")
            
        except asyncio.TimeoutError:
            results['warnings'].append("Performance benchmark timed out")
        except Exception as e:
            results['warnings'].append(f"Could not run performance benchmark: {e}")
        
        return results
    
    async def _run_security_scan(self, recommendation: OptimizationRecommendation,
                               phase: str) -> Dict[str, Any]:
        """Run security scan"""
        results = {'success': True, 'errors': [], 'warnings': []}
        
        try:
            # Run bandit security scan on Python files
            python_files = [f for f in recommendation.target_files if f.endswith('.py')]
            
            if python_files:
                process = await asyncio.create_subprocess_exec(
                    'bandit', '-r', *python_files,
                    cwd=self.project_root,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.config['validation_timeout']
                )
                
                # Bandit returns non-zero for security issues, but that's expected
                if stderr:
                    results['warnings'].append(f"Security scan warnings: {stderr.decode()}")
            
        except FileNotFoundError:
            results['warnings'].append("Bandit not installed, skipping security scan")
        except Exception as e:
            results['warnings'].append(f"Could not run security scan: {e}")
        
        return results
    
    async def _validate_configuration(self, recommendation: OptimizationRecommendation,
                                    phase: str) -> Dict[str, Any]:
        """Validate configuration files"""
        results = {'success': True, 'errors': [], 'warnings': []}
        
        for file_path in recommendation.target_files:
            full_path = self.project_root / file_path
            
            try:
                if file_path.endswith('.py') and 'config' in file_path:
                    # Try to import and validate Python config
                    spec = importlib.util.spec_from_file_location("config", full_path)
                    config_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(config_module)
                    
                elif file_path.endswith('.yaml') or file_path.endswith('.yml'):
                    # Validate YAML syntax
                    with open(full_path, 'r') as f:
                        yaml.safe_load(f)
                        
                elif file_path.endswith('.json'):
                    # Validate JSON syntax
                    with open(full_path, 'r') as f:
                        json.load(f)
                        
            except Exception as e:
                results['success'] = False
                results['errors'].append(f"Configuration validation failed for {file_path}: {e}")
        
        return results
    
    # Helper methods
    async def _create_backups(self, target_files: List[str]) -> Dict[str, str]:
        """Create backups of target files"""
        backup_data = {}
        backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for file_path in target_files:
            source_path = self.project_root / file_path
            if source_path.exists():
                backup_name = f"{file_path.replace('/', '_')}_{backup_timestamp}.backup"
                backup_path = self.backup_dir / backup_name
                
                # Create backup directory if needed
                backup_path.parent.mkdir(exist_ok=True, parents=True)
                
                # Copy file
                shutil.copy2(source_path, backup_path)
                backup_data[file_path] = str(backup_path)
        
        return backup_data
    
    async def _rollback_optimization(self, execution: OptimizationExecution):
        """Rollback optimization changes"""
        try:
            execution.status = OptimizationStatus.ROLLED_BACK
            
            for file_path, backup_path in execution.rollback_data.items():
                source_path = self.project_root / file_path
                
                if Path(backup_path).exists():
                    shutil.copy2(backup_path, source_path)
                    await self._log_execution_step(execution, f"Rolled back {file_path}")
            
            # Update metrics
            self.optimization_metrics['rolled_back_optimizations'] += 1
            
            await self._log_execution_step(execution, "Rollback completed")
            
        except Exception as e:
            await self._log_execution_step(execution, f"Rollback failed: {e}")
            self.logger.error(f"Rollback failed for execution {execution.id}: {e}")
    
    async def _log_execution_step(self, execution: OptimizationExecution, message: str):
        """Log execution step"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'status': execution.status.value,
            'message': message
        }
        
        execution.execution_log.append(log_entry)
        self.logger.info(f"[{execution.id}] {message}")
        
        # Send real-time update
        await self._send_realtime_update(UpdateType.OPTIMIZATION_RESULT, {
            'action': 'execution_step',
            'execution_id': execution.id,
            'step': message,
            'status': execution.status.value
        })
    
    async def _send_realtime_update(self, update_type: UpdateType, data: Dict[str, Any]):
        """Send real-time update via WebSocket"""
        if self.websocket_manager:
            update = RealTimeUpdate(
                id=str(uuid.uuid4()),
                type=update_type,
                timestamp=datetime.now(),
                data=data
            )
            await self.websocket_manager.queue_update(update)
    
    async def _handle_optimization_message(self, message):
        """Handle optimization messages from message queue"""
        try:
            if message.type == MessageType.OPTIMIZATION_REQUEST:
                payload = message.payload
                
                # Create recommendation from message
                recommendation = OptimizationRecommendation(
                    id=str(uuid.uuid4()),
                    agent_id=message.sender,
                    type=OptimizationType(payload.get('optimization_type', 'code_optimization')),
                    severity=OptimizationSeverity(payload.get('severity', 'medium')),
                    title=payload.get('title', 'Agent Optimization'),
                    description=payload.get('description', ''),
                    target_files=payload.get('target_files', []),
                    proposed_changes=payload.get('proposed_changes', []),
                    expected_benefits=payload.get('expected_benefits', []),
                    risk_assessment=payload.get('risk_assessment', {}),
                    validation_requirements=payload.get('validation_requirements', ['syntax_check']),
                    created_at=datetime.now(),
                    confidence_score=payload.get('confidence_score', 0.5),
                    dependencies=payload.get('dependencies', [])
                )
                
                await self.submit_recommendation(recommendation)
                
        except Exception as e:
            self.logger.error(f"Error handling optimization message: {e}")
    
    async def _optimization_processing_loop(self):
        """Main optimization processing loop"""
        while self.running:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                # Check for auto-apply opportunities
                auto_apply_candidates = []
                for rec_id, recommendation in list(self.pending_recommendations.items()):
                    if await self._should_auto_apply(recommendation):
                        auto_apply_candidates.append(recommendation)
                
                # Execute auto-apply candidates
                for recommendation in auto_apply_candidates:
                    await self._execute_single_optimization(recommendation)
                
            except Exception as e:
                self.logger.error(f"Error in optimization processing loop: {e}")
                await asyncio.sleep(30)
    
    async def _validation_monitoring_loop(self):
        """Monitor validation timeouts and cleanup"""
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Check for timeouts
                current_time = datetime.now()
                timeout_threshold = timedelta(seconds=self.config['validation_timeout'] * 2)
                
                for execution_id, execution in list(self.active_executions.items()):
                    if current_time - execution.started_at > timeout_threshold:
                        self.logger.warning(f"Optimization {execution_id} timed out")
                        
                        execution.status = OptimizationStatus.FAILED
                        execution.completed_at = current_time
                        execution.error_message = "Execution timeout"
                        
                        # Move to completed
                        self.completed_optimizations.append(execution)
                        del self.active_executions[execution_id]
                
            except Exception as e:
                self.logger.error(f"Error in validation monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_loop(self):
        """Cleanup old data and backups"""
        while self.running:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Clean old backups
                cutoff_date = datetime.now() - timedelta(days=self.config['backup_retention_days'])
                
                for backup_file in self.backup_dir.glob('*.backup'):
                    if backup_file.stat().st_mtime < cutoff_date.timestamp():
                        backup_file.unlink()
                
                # Clean old completed optimizations (keep last 100)
                if len(self.completed_optimizations) > 100:
                    self.completed_optimizations = self.completed_optimizations[-100:]
                
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)
    
    async def _should_auto_apply(self, recommendation: OptimizationRecommendation) -> bool:
        """Check if optimization should be auto-applied"""
        if not self.config.get('auto_apply_low_risk', False):
            return False
        
        return (recommendation.severity == OptimizationSeverity.LOW and
                recommendation.confidence_score >= 0.8 and
                len(self.active_executions) < self.config['max_concurrent_optimizations'])
    
    def _requires_approval(self, risk_level: OptimizationSeverity) -> bool:
        """Check if optimization requires approval"""
        threshold = OptimizationSeverity(self.config.get('require_approval_threshold', 'medium'))
        
        severity_order = {
            OptimizationSeverity.LOW: 1,
            OptimizationSeverity.MEDIUM: 2,
            OptimizationSeverity.HIGH: 3,
            OptimizationSeverity.CRITICAL: 4
        }
        
        return severity_order[risk_level] >= severity_order[threshold]
    
    def _update_success_rate(self):
        """Update optimization success rate"""
        total = self.optimization_metrics['applied_optimizations'] + self.optimization_metrics['failed_optimizations']
        if total > 0:
            self.optimization_metrics['success_rate'] = self.optimization_metrics['applied_optimizations'] / total
    
    async def get_optimization_status(self) -> Dict[str, Any]:
        """Get current optimization engine status"""
        return {
            'timestamp': datetime.now().isoformat(),
            'pending_recommendations': len(self.pending_recommendations),
            'active_executions': len(self.active_executions),
            'completed_optimizations': len(self.completed_optimizations),
            'optimization_plans': len(self.optimization_plans),
            'metrics': self.optimization_metrics,
            'active_execution_details': {
                exec_id: {
                    'status': execution.status.value,
                    'started_at': execution.started_at.isoformat(),
                    'type': execution.recommendation.type.value,
                    'agent_id': execution.recommendation.agent_id
                }
                for exec_id, execution in self.active_executions.items()
            }
        }
    
    async def shutdown(self):
        """Shutdown optimization engine gracefully"""
        self.running = False
        
        # Wait for active executions to complete or timeout
        if self.active_executions:
            self.logger.info(f"Waiting for {len(self.active_executions)} active optimizations to complete...")
            
            timeout = 60  # Wait up to 1 minute
            start_time = time.time()
            
            while self.active_executions and (time.time() - start_time) < timeout:
                await asyncio.sleep(1)
            
            # Force stop remaining executions
            for execution in self.active_executions.values():
                execution.status = OptimizationStatus.FAILED
                execution.error_message = "System shutdown"
                execution.completed_at = datetime.now()
        
        self.logger.info("Optimization engine shutdown complete")


# CLI interface for testing
if __name__ == "__main__":
    import sys
    
    async def test_optimization_engine():
        # Create mock dependencies
        from message_queue import create_message_queue
        from coordination_service import CoordinationService
        from websocket_manager import WebSocketManager
        import swarm_memory_coordinator
        
        message_queue = await create_message_queue(["localhost:6379"])
        memory_coordinator = swarm_memory_coordinator.SwarmMemoryCoordinator()
        coordination_service = CoordinationService(memory_coordinator, message_queue)
        websocket_manager = WebSocketManager(message_queue)
        
        # Initialize services
        await coordination_service.initialize()
        await websocket_manager.initialize()
        
        # Create optimization engine
        optimization_engine = OptimizationEngine(
            message_queue, coordination_service, websocket_manager
        )
        await optimization_engine.initialize()
        
        # Create test recommendation
        test_recommendation = OptimizationRecommendation(
            id=str(uuid.uuid4()),
            agent_id="test-agent",
            type=OptimizationType.CODE_OPTIMIZATION,
            severity=OptimizationSeverity.LOW,
            title="Test Code Optimization",
            description="Test optimization for demonstration",
            target_files=["test_file.py"],
            proposed_changes=[
                {
                    'type': 'code_replacement',
                    'file': 'test_file.py',
                    'old_code': 'print("old")',
                    'new_code': 'print("new")'
                }
            ],
            expected_benefits=["Improved code clarity"],
            risk_assessment={'level': 'low'},
            validation_requirements=['syntax_check'],
            created_at=datetime.now(),
            confidence_score=0.9
        )
        
        # Submit recommendation
        rec_id = await optimization_engine.submit_recommendation(test_recommendation)
        print(f"Submitted recommendation: {rec_id}")
        
        # Get status
        await asyncio.sleep(2)
        status = await optimization_engine.get_optimization_status()
        print(f"Engine status: {json.dumps(status, indent=2, default=str)}")
        
        await optimization_engine.shutdown()
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        asyncio.run(test_optimization_engine())
    else:
        print("Use 'python optimization_engine.py test' to run tests")