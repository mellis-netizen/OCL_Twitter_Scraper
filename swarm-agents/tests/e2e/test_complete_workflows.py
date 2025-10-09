#!/usr/bin/env python3
"""
End-to-End Tests for Complete Swarm Workflows
Tests complete optimization workflows from start to finish
"""

import asyncio
import pytest
import uuid
import tempfile
import os
from datetime import datetime, timezone
from typing import Dict, List, Any
from pathlib import Path

from backend.message_queue import TaskDefinition, Priority
from backend.agent_manager import AgentStatus
from backend.database.models import OptimizationStatus


@pytest.mark.e2e
@pytest.mark.slow
class TestCompleteOptimizationWorkflow:
    """Test complete optimization workflow from discovery to implementation"""
    
    async def test_full_optimization_discovery_and_implementation(self, full_backend_stack, test_cleanup):
        """Test complete workflow: optimization discovery, validation, and implementation"""
        message_queue = full_backend_stack['message_queue']
        agent_manager = full_backend_stack['agent_manager']
        coordination_service = full_backend_stack['coordination_service']
        database = full_backend_stack['database']
        
        # Create temporary test files
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test_scraper.py"
            test_file.write_text("""
import time
import requests

def scrape_data():
    # Inefficient implementation
    for i in range(100):
        time.sleep(0.01)  # Inefficient delay
        response = requests.get("https://api.example.com/data")
        if response.status_code == 200:
            print(f"Got data: {response.json()}")
    return "completed"
""")
            
            test_cleanup(lambda: os.unlink(test_file) if test_file.exists() else None)
            
            # Deploy optimization agents
            scraping_instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=1)
            performance_instances = await agent_manager.deploy_agent('performance-optimizer', replicas=1)
            
            # Set agents as healthy
            for agent_id in scraping_instances + performance_instances:
                agent_manager.agents[agent_id].status = AgentStatus.HEALTHY
            
            try:
                # Step 1: Optimization Discovery Task
                discovery_task = TaskDefinition(
                    id=str(uuid.uuid4()),
                    type="code_analysis",
                    agent_type="scraping-efficiency",
                    priority=Priority.HIGH,
                    payload={
                        'target_files': [str(test_file)],
                        'analysis_type': 'performance_bottlenecks',
                        'depth': 'detailed'
                    },
                    timeout=300,
                    created_at=datetime.now(timezone.utc)
                )
                
                # Enqueue discovery task
                await message_queue.enqueue_task(discovery_task)
                
                # Agent processes discovery task
                assigned_agent = await agent_manager.assign_task_to_agent(discovery_task)
                assert assigned_agent is not None, "Discovery task should be assigned to an agent"
                
                # Simulate discovery results
                discovery_results = {
                    'optimizations_found': [
                        {
                            'id': str(uuid.uuid4()),
                            'type': 'remove_sleep_delay',
                            'severity': 'high',
                            'file': str(test_file),
                            'line': 7,
                            'description': 'Remove inefficient sleep delay in loop',
                            'estimated_improvement': '95% performance gain',
                            'confidence': 0.95
                        },
                        {
                            'id': str(uuid.uuid4()),
                            'type': 'batch_requests',
                            'severity': 'medium', 
                            'file': str(test_file),
                            'line': 8,
                            'description': 'Batch API requests instead of individual calls',
                            'estimated_improvement': '70% network efficiency',
                            'confidence': 0.80
                        }
                    ],
                    'analysis_metadata': {
                        'lines_analyzed': 15,
                        'functions_analyzed': 1,
                        'complexity_score': 3.2
                    }
                }
                
                await message_queue.submit_task_result(
                    discovery_task.id,
                    assigned_agent,
                    discovery_results,
                    success=True
                )
                
                # Step 2: Optimization Validation
                for optimization in discovery_results['optimizations_found']:
                    validation_task = TaskDefinition(
                        id=str(uuid.uuid4()),
                        type="optimization_validation",
                        agent_type="performance-optimizer",
                        priority=Priority.HIGH,
                        payload={
                            'optimization_id': optimization['id'],
                            'target_file': optimization['file'],
                            'optimization_type': optimization['type'],
                            'proposed_change': optimization['description']
                        },
                        timeout=300,
                        created_at=datetime.now(timezone.utc)
                    )
                    
                    await message_queue.enqueue_task(validation_task)
                    
                    # Assign to performance optimizer
                    validator_agent = await agent_manager.assign_task_to_agent(validation_task)
                    assert validator_agent is not None, "Validation task should be assigned"
                    
                    # Simulate validation results
                    validation_results = {
                        'validation_passed': True,
                        'safety_score': 0.9,
                        'test_results': {
                            'syntax_valid': True,
                            'imports_intact': True,
                            'functionality_preserved': True
                        },
                        'risk_assessment': 'low',
                        'recommended_action': 'proceed'
                    }
                    
                    await message_queue.submit_task_result(
                        validation_task.id,
                        validator_agent,
                        validation_results,
                        success=True
                    )
                
                # Step 3: Coordination and Resource Claiming
                high_priority_optimization = discovery_results['optimizations_found'][0]
                
                # Claim resource for modification
                resource_claimed = await coordination_service.claim_resource(
                    assigned_agent,
                    str(test_file)
                )
                assert resource_claimed, "Should be able to claim file resource"
                
                # Step 4: Implementation Task
                implementation_task = TaskDefinition(
                    id=str(uuid.uuid4()),
                    type="optimization_implementation",
                    agent_type="scraping-efficiency",
                    priority=Priority.CRITICAL,
                    payload={
                        'optimization_id': high_priority_optimization['id'],
                        'target_file': str(test_file),
                        'optimization_type': high_priority_optimization['type'],
                        'implementation_plan': {
                            'remove_line': 7,
                            'add_comment': 'Removed inefficient sleep delay for performance'
                        }
                    },
                    timeout=600,
                    created_at=datetime.now(timezone.utc)
                )
                
                await message_queue.enqueue_task(implementation_task)
                implementer_agent = await agent_manager.assign_task_to_agent(implementation_task)
                assert implementer_agent is not None, "Implementation task should be assigned"
                
                # Simulate implementation
                original_content = test_file.read_text()
                
                # Apply optimization (remove sleep line)
                lines = original_content.split('\n')
                lines[6] = '        # Removed inefficient sleep delay for performance'  # Replace sleep line
                optimized_content = '\n'.join(lines)
                
                test_file.write_text(optimized_content)
                
                implementation_results = {
                    'implementation_successful': True,
                    'files_modified': [str(test_file)],
                    'changes_applied': 1,
                    'backup_created': f"{str(test_file)}.backup",
                    'verification_passed': True,
                    'performance_impact': {
                        'estimated_improvement': '95%',
                        'affected_functions': ['scrape_data']
                    }
                }
                
                await message_queue.submit_task_result(
                    implementation_task.id,
                    implementer_agent,
                    implementation_results,
                    success=True
                )
                
                # Step 5: Post-Implementation Verification
                verification_task = TaskDefinition(
                    id=str(uuid.uuid4()),
                    type="post_optimization_verification",
                    agent_type="scraping-efficiency",
                    priority=Priority.HIGH,
                    payload={
                        'target_file': str(test_file),
                        'optimization_id': high_priority_optimization['id'],
                        'expected_improvements': ['performance_gain']
                    },
                    timeout=300,
                    created_at=datetime.now(timezone.utc)
                )
                
                await message_queue.enqueue_task(verification_task)
                verifier_agent = await agent_manager.assign_task_to_agent(verification_task)
                
                # Simulate verification
                verification_results = {
                    'verification_successful': True,
                    'syntax_check_passed': True,
                    'functionality_preserved': True,
                    'performance_metrics': {
                        'execution_time_improvement': '94%',
                        'memory_usage_unchanged': True,
                        'api_call_efficiency': 'maintained'
                    },
                    'quality_score': 0.95
                }
                
                await message_queue.submit_task_result(
                    verification_task.id,
                    verifier_agent,
                    verification_results,
                    success=True
                )
                
                # Step 6: Release Resource and Record Success
                await coordination_service.release_resource(assigned_agent, str(test_file))
                
                # Record coordination event
                await coordination_service.record_coordination_event(
                    assigned_agent,
                    'optimization_completed',
                    {
                        'optimization_id': high_priority_optimization['id'],
                        'file': str(test_file),
                        'improvement': '94%',
                        'workflow_duration': 'completed'
                    }
                )
                
                # Verify final state
                final_content = test_file.read_text()
                assert 'sleep(0.01)' not in final_content, "Sleep delay should be removed"
                assert 'Removed inefficient sleep delay' in final_content, "Comment should be added"
                
                # Check task completion statistics
                task_stats = await message_queue.get_task_statistics()
                assert task_stats['status_counts']['completed'] >= 4, "All workflow tasks should complete"
                
                # Check agent utilization
                agent_status = await agent_manager.get_agent_status()
                total_tasks = sum(agent['task_count'] for agent in agent_status['agents'].values())
                assert total_tasks >= 4, "Agents should have processed workflow tasks"
                
            finally:
                # Cleanup agents
                for agent_id in scraping_instances + performance_instances:
                    await agent_manager.stop_agent(agent_id, force=True)
    
    async def test_multi_agent_collaboration_workflow(self, full_backend_stack):
        """Test workflow requiring collaboration between multiple agent types"""
        message_queue = full_backend_stack['message_queue']
        agent_manager = full_backend_stack['agent_manager']
        coordination_service = full_backend_stack['coordination_service']
        
        # Deploy multiple agent types
        scraping_agents = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=2)
        keyword_agents = await agent_manager.deploy_agent('keyword-precision-specialist', replicas=1)
        performance_agents = await agent_manager.deploy_agent('performance-optimizer', replicas=1)
        
        # Set all agents as healthy
        all_agents = scraping_agents + keyword_agents + performance_agents
        for agent_id in all_agents:
            agent_manager.agents[agent_id].status = AgentStatus.HEALTHY
        
        try:
            # Step 1: Keyword Analysis Task
            keyword_task = TaskDefinition(
                id=str(uuid.uuid4()),
                type="keyword_analysis",
                agent_type="keyword-precision",
                priority=Priority.HIGH,
                payload={
                    'source_text': 'TGE blockchain defi cryptocurrency token launch',
                    'analysis_depth': 'comprehensive',
                    'confidence_threshold': 0.8
                },
                timeout=300,
                created_at=datetime.now(timezone.utc)
            )
            
            await message_queue.enqueue_task(keyword_task)
            keyword_agent = await agent_manager.assign_task_to_agent(keyword_task)
            assert keyword_agent is not None
            
            # Simulate keyword analysis results
            keyword_results = {
                'extracted_keywords': [
                    {'keyword': 'TGE', 'confidence': 0.95, 'category': 'event'},
                    {'keyword': 'blockchain', 'confidence': 0.90, 'category': 'technology'},
                    {'keyword': 'defi', 'confidence': 0.85, 'category': 'sector'},
                    {'keyword': 'token launch', 'confidence': 0.88, 'category': 'event'}
                ],
                'sentiment_score': 0.7,
                'relevance_score': 0.92
            }
            
            await message_queue.submit_task_result(
                keyword_task.id,
                keyword_agent,
                keyword_results,
                success=True
            )
            
            # Step 2: Share keyword insights with scraping agents
            from backend.message_queue import SwarmMessage, MessageType
            
            for scraping_agent_id in scraping_agents:
                keyword_sharing_message = SwarmMessage(
                    id=str(uuid.uuid4()),
                    type=MessageType.COORDINATION_EVENT,
                    sender=keyword_agent,
                    recipient=scraping_agent_id,
                    timestamp=datetime.now(timezone.utc),
                    payload={
                        'event_type': 'keyword_insights_shared',
                        'keywords': keyword_results['extracted_keywords'],
                        'source_task': keyword_task.id
                    },
                    priority=Priority.MEDIUM
                )
                
                await message_queue.publish_message(keyword_sharing_message)
            
            # Step 3: Enhanced scraping task using keyword insights
            enhanced_scraping_task = TaskDefinition(
                id=str(uuid.uuid4()),
                type="enhanced_scraping",
                agent_type="scraping-efficiency",
                priority=Priority.HIGH,
                payload={
                    'keywords': [kw['keyword'] for kw in keyword_results['extracted_keywords']],
                    'target_sources': ['twitter', 'telegram', 'discord'],
                    'optimization_level': 'high',
                    'keyword_source_task': keyword_task.id
                },
                timeout=600,
                created_at=datetime.now(timezone.utc)
            )
            
            await message_queue.enqueue_task(enhanced_scraping_task)
            scraping_agent = await agent_manager.assign_task_to_agent(enhanced_scraping_task)
            assert scraping_agent is not None
            
            # Simulate enhanced scraping results
            scraping_results = {
                'data_collected': 150,
                'keyword_matches': {
                    'TGE': 45,
                    'blockchain': 30,
                    'defi': 25,
                    'token launch': 20
                },
                'sources_processed': 3,
                'efficiency_improvement': '40%',
                'quality_score': 0.88
            }
            
            await message_queue.submit_task_result(
                enhanced_scraping_task.id,
                scraping_agent,
                scraping_results,
                success=True
            )
            
            # Step 4: Performance optimization based on scraping patterns
            performance_task = TaskDefinition(
                id=str(uuid.uuid4()),
                type="pattern_optimization",
                agent_type="performance-optimizer",
                priority=Priority.MEDIUM,
                payload={
                    'scraping_patterns': scraping_results['keyword_matches'],
                    'efficiency_target': '60%',
                    'optimization_focus': 'keyword_matching'
                },
                timeout=400,
                created_at=datetime.now(timezone.utc)
            )
            
            await message_queue.enqueue_task(performance_task)
            performance_agent = await agent_manager.assign_task_to_agent(performance_task)
            assert performance_agent is not None
            
            # Simulate performance optimization
            performance_results = {
                'optimizations_identified': 3,
                'estimated_improvement': '55%',
                'recommendations': [
                    'Use compiled regex for keyword matching',
                    'Implement keyword caching',
                    'Optimize data structure for frequent lookups'
                ],
                'implementation_complexity': 'medium'
            }
            
            await message_queue.submit_task_result(
                performance_task.id,
                performance_agent,
                performance_results,
                success=True
            )
            
            # Step 5: Coordination event for workflow completion
            await coordination_service.record_coordination_event(
                'system',
                'multi_agent_workflow_completed',
                {
                    'participating_agents': all_agents,
                    'workflow_type': 'keyword_enhanced_scraping',
                    'tasks_completed': 3,
                    'overall_improvement': '55%',
                    'collaboration_success': True
                }
            )
            
            # Verify workflow completion
            coord_status = await coordination_service.get_coordination_status()
            assert 'recent_events' in coord_status
            
            final_stats = await message_queue.get_task_statistics()
            assert final_stats['status_counts']['completed'] >= 3
            
            # Verify agent collaboration metrics
            agent_status = await agent_manager.get_agent_status()
            participating_agents = len([a for a in agent_status['agents'].values() if a['task_count'] > 0])
            assert participating_agents >= 3, "Multiple agent types should participate"
            
        finally:
            # Cleanup all agents
            for agent_id in all_agents:
                await agent_manager.stop_agent(agent_id, force=True)
    
    async def test_error_recovery_workflow(self, full_backend_stack):
        """Test workflow with errors and recovery mechanisms"""
        message_queue = full_backend_stack['message_queue']
        agent_manager = full_backend_stack['agent_manager']
        coordination_service = full_backend_stack['coordination_service']
        
        # Deploy agents
        instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=2)
        
        for agent_id in instances:
            agent_manager.agents[agent_id].status = AgentStatus.HEALTHY
        
        try:
            # Step 1: Task that will initially fail
            failing_task = TaskDefinition(
                id=str(uuid.uuid4()),
                type="error_prone_analysis",
                agent_type="scraping-efficiency",
                priority=Priority.HIGH,
                payload={
                    'target_file': '/nonexistent/file.py',
                    'analysis_type': 'deep'
                },
                timeout=300,
                retries=2,
                created_at=datetime.now(timezone.utc)
            )
            
            await message_queue.enqueue_task(failing_task)
            assigned_agent = await agent_manager.assign_task_to_agent(failing_task)
            assert assigned_agent is not None
            
            # Simulate initial failure
            await message_queue.submit_task_result(
                failing_task.id,
                assigned_agent,
                {'error': 'File not found', 'retry_recommended': True},
                success=False
            )
            
            # Step 2: Corrective task with proper file path
            corrected_task = TaskDefinition(
                id=str(uuid.uuid4()),
                type="corrected_analysis",
                agent_type="scraping-efficiency",
                priority=Priority.HIGH,
                payload={
                    'target_file': '/tmp/test_file.py',  # Valid path
                    'analysis_type': 'basic',
                    'fallback_mode': True,
                    'original_task': failing_task.id
                },
                timeout=300,
                created_at=datetime.now(timezone.utc)
            )
            
            await message_queue.enqueue_task(corrected_task)
            recovery_agent = await agent_manager.assign_task_to_agent(corrected_task)
            
            # Simulate successful recovery
            recovery_results = {
                'recovery_successful': True,
                'fallback_analysis': {
                    'basic_metrics': 'computed',
                    'confidence': 0.7
                },
                'original_task_ref': failing_task.id,
                'recovery_strategy': 'fallback_mode'
            }
            
            await message_queue.submit_task_result(
                corrected_task.id,
                recovery_agent,
                recovery_results,
                success=True
            )
            
            # Step 3: Agent failure and restart
            failed_agent = instances[0]
            agent_manager.agents[failed_agent].status = AgentStatus.FAILED
            
            # System detects failure and restarts
            restart_success = await agent_manager.restart_agent(failed_agent)
            if restart_success:
                assert agent_manager.agents[failed_agent].restart_count > 0
            
            # Step 4: Task reassignment after agent failure
            reassignment_task = TaskDefinition(
                id=str(uuid.uuid4()),
                type="post_recovery_task",
                agent_type="scraping-efficiency",
                priority=Priority.MEDIUM,
                payload={
                    'recovery_context': recovery_results,
                    'continuation': True
                },
                timeout=300,
                created_at=datetime.now(timezone.utc)
            )
            
            await message_queue.enqueue_task(reassignment_task)
            
            # Should be assigned to healthy agent
            healthy_agent = await agent_manager.assign_task_to_agent(reassignment_task)
            assert healthy_agent is not None
            assert healthy_agent != failed_agent or restart_success
            
            # Complete workflow successfully
            final_results = {
                'workflow_recovered': True,
                'error_handling_successful': True,
                'final_status': 'completed_with_recovery'
            }
            
            await message_queue.submit_task_result(
                reassignment_task.id,
                healthy_agent,
                final_results,
                success=True
            )
            
            # Record recovery event
            await coordination_service.record_coordination_event(
                'system',
                'error_recovery_completed',
                {
                    'failed_tasks': 1,
                    'recovered_tasks': 2,
                    'agent_restarts': 1 if restart_success else 0,
                    'recovery_strategy': 'task_reassignment_and_fallback'
                }
            )
            
            # Verify recovery workflow
            final_stats = await message_queue.get_task_statistics()
            assert final_stats['status_counts']['completed'] >= 2
            assert final_stats['status_counts']['failed'] >= 1
            
        finally:
            # Cleanup
            for agent_id in instances:
                await agent_manager.stop_agent(agent_id, force=True)
    
    async def test_resource_contention_workflow(self, full_backend_stack):
        """Test workflow with resource contention and coordination"""
        message_queue = full_backend_stack['message_queue']
        agent_manager = full_backend_stack['agent_manager']
        coordination_service = full_backend_stack['coordination_service']
        
        # Deploy multiple agents that will compete for resources
        instances = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=3)
        
        for agent_id in instances:
            agent_manager.agents[agent_id].status = AgentStatus.HEALTHY
        
        try:
            shared_resource = "/shared/config.json"
            
            # Step 1: Multiple agents try to claim same resource
            contention_tasks = []
            for i, agent_id in enumerate(instances):
                task = TaskDefinition(
                    id=str(uuid.uuid4()),
                    type="resource_modification",
                    agent_type="scraping-efficiency",
                    priority=Priority.HIGH,
                    payload={
                        'target_resource': shared_resource,
                        'modification_type': f'update_{i}',
                        'agent_index': i
                    },
                    timeout=300,
                    created_at=datetime.now(timezone.utc)
                )
                contention_tasks.append(task)
                await message_queue.enqueue_task(task)
            
            # Assign tasks to different agents
            assignments = []
            for task in contention_tasks:
                agent = await agent_manager.assign_task_to_agent(task)
                assignments.append((task, agent))
            
            # Step 2: Simulate resource claiming race condition
            claim_results = []
            for task, agent in assignments:
                claimed = await coordination_service.claim_resource(agent, shared_resource)
                claim_results.append((task, agent, claimed))
                
                if claimed:
                    # Successfully claimed - can proceed
                    success_result = {
                        'resource_claimed': True,
                        'modification_completed': True,
                        'agent_id': agent,
                        'modification_type': task.payload['modification_type']
                    }
                    
                    await message_queue.submit_task_result(
                        task.id, agent, success_result, success=True
                    )
                    
                    # Release resource after task
                    await coordination_service.release_resource(agent, shared_resource)
                else:
                    # Failed to claim - defer task
                    defer_result = {
                        'resource_claimed': False,
                        'task_deferred': True,
                        'reason': 'resource_unavailable'
                    }
                    
                    await message_queue.submit_task_result(
                        task.id, agent, defer_result, success=False
                    )
            
            # Step 3: Process deferred tasks
            successful_claims = [r for r in claim_results if r[2]]
            failed_claims = [r for r in claim_results if not r[2]]
            
            # Retry failed claims one by one
            for task, agent, _ in failed_claims:
                # Wait for resource to be available and retry
                retry_claimed = await coordination_service.claim_resource(agent, shared_resource)
                if retry_claimed:
                    retry_result = {
                        'resource_claimed_on_retry': True,
                        'modification_completed': True,
                        'retry_successful': True,
                        'agent_id': agent
                    }
                    
                    await message_queue.submit_task_result(
                        task.id, agent, retry_result, success=True
                    )
                    
                    await coordination_service.release_resource(agent, shared_resource)
            
            # Step 4: Verify resource coordination worked
            coord_status = await coordination_service.get_coordination_status()
            
            # All tasks should eventually complete
            final_stats = await message_queue.get_task_statistics()
            total_attempts = len(contention_tasks)
            completed = final_stats['status_counts']['completed']
            
            print(f"Resource contention results: {completed}/{total_attempts} tasks completed")
            
            # At least one task should succeed (the one that got the resource first)
            assert completed >= 1, "At least one resource contention task should succeed"
            
            # Record coordination success
            await coordination_service.record_coordination_event(
                'system',
                'resource_contention_resolved',
                {
                    'competing_agents': len(instances),
                    'resource': shared_resource,
                    'successful_claims': len(successful_claims),
                    'retries_needed': len(failed_claims),
                    'coordination_effective': True
                }
            )
            
        finally:
            # Cleanup
            for agent_id in instances:
                await agent_manager.stop_agent(agent_id, force=True)


@pytest.mark.e2e
class TestSystemIntegrationScenarios:
    """Test realistic system integration scenarios"""
    
    async def test_high_volume_tge_detection_scenario(self, full_backend_stack):
        """Test high-volume TGE detection scenario"""
        message_queue = full_backend_stack['message_queue']
        agent_manager = full_backend_stack['agent_manager']
        
        # Deploy comprehensive agent fleet
        scraping_agents = await agent_manager.deploy_agent('scraping-efficiency-specialist', replicas=3)
        keyword_agents = await agent_manager.deploy_agent('keyword-precision-specialist', replicas=2)
        
        all_agents = scraping_agents + keyword_agents
        for agent_id in all_agents:
            agent_manager.agents[agent_id].status = AgentStatus.HEALTHY
        
        try:
            # Simulate high-volume data processing
            num_data_sources = 20
            data_processing_tasks = []
            
            for i in range(num_data_sources):
                # Keyword analysis tasks
                keyword_task = TaskDefinition(
                    id=str(uuid.uuid4()),
                    type="real_time_keyword_analysis",
                    agent_type="keyword-precision",
                    priority=Priority.HIGH if i < 5 else Priority.MEDIUM,
                    payload={
                        'source_id': f'source_{i}',
                        'content': f'New TGE announcement for BlockchainProject{i} token launching next week with DeFi integration',
                        'urgency': 'high' if i < 5 else 'normal'
                    },
                    timeout=120,
                    created_at=datetime.now(timezone.utc)
                )
                data_processing_tasks.append(keyword_task)
                
                # Scraping efficiency tasks
                scraping_task = TaskDefinition(
                    id=str(uuid.uuid4()),
                    type="optimized_data_collection",
                    agent_type="scraping-efficiency",
                    priority=Priority.MEDIUM,
                    payload={
                        'source_type': 'social_media',
                        'target_keywords': ['TGE', 'token launch', 'blockchain'],
                        'data_source_id': f'source_{i}',
                        'collection_depth': 'comprehensive'
                    },
                    timeout=180,
                    created_at=datetime.now(timezone.utc)
                )
                data_processing_tasks.append(scraping_task)
            
            # Enqueue all tasks
            for task in data_processing_tasks:
                await message_queue.enqueue_task(task)
            
            # Process tasks with available agents
            completed_tasks = 0
            processing_results = []
            
            # Simulate real-time processing
            for task in data_processing_tasks:
                assigned_agent = await agent_manager.assign_task_to_agent(task)
                if assigned_agent:
                    # Simulate processing results
                    if task.type == "real_time_keyword_analysis":
                        result = {
                            'tge_indicators': ['token launch', 'blockchain project'],
                            'confidence_score': 0.85,
                            'urgency_level': task.payload['urgency'],
                            'processing_time': 0.5
                        }
                    else:  # scraping task
                        result = {
                            'data_collected': 50,
                            'tge_mentions': 8,
                            'quality_score': 0.78,
                            'processing_efficiency': '85%'
                        }
                    
                    await message_queue.submit_task_result(
                        task.id, assigned_agent, result, success=True
                    )
                    completed_tasks += 1
                    processing_results.append(result)
            
            # Verify high-volume processing
            assert completed_tasks >= len(data_processing_tasks) * 0.8, "Should process most tasks"
            
            final_stats = await message_queue.get_task_statistics()
            agent_status = await agent_manager.get_agent_status()
            
            print(f"Processed {completed_tasks} tasks across {len(all_agents)} agents")
            print(f"System throughput: {completed_tasks/len(all_agents):.1f} tasks per agent")
            
            # System should handle high volume efficiently
            total_agent_tasks = sum(a['task_count'] for a in agent_status['agents'].values())
            assert total_agent_tasks >= num_data_sources, "Agents should be actively processing"
            
        finally:
            # Cleanup
            for agent_id in all_agents:
                await agent_manager.stop_agent(agent_id, force=True)
    
    async def test_cross_platform_optimization_scenario(self, full_backend_stack):
        """Test cross-platform optimization scenario"""
        message_queue = full_backend_stack['message_queue']
        agent_manager = full_backend_stack['agent_manager']
        coordination_service = full_backend_stack['coordination_service']
        
        # Deploy diverse agent types
        agents_config = [
            ('scraping-efficiency-specialist', 2),
            ('keyword-precision-specialist', 1),
            ('performance-optimizer', 1)
        ]
        
        all_agents = []
        for agent_type, count in agents_config:
            instances = await agent_manager.deploy_agent(agent_type, replicas=count)
            all_agents.extend(instances)
        
        for agent_id in all_agents:
            agent_manager.agents[agent_id].status = AgentStatus.HEALTHY
        
        try:
            # Cross-platform optimization workflow
            platforms = ['twitter', 'telegram', 'discord', 'reddit']
            
            # Step 1: Platform-specific analysis
            platform_analysis_tasks = []
            for platform in platforms:
                task = TaskDefinition(
                    id=str(uuid.uuid4()),
                    type="platform_specific_analysis",
                    agent_type="scraping-efficiency",
                    priority=Priority.HIGH,
                    payload={
                        'platform': platform,
                        'analysis_focus': 'tge_detection_patterns',
                        'optimization_target': 'cross_platform_efficiency'
                    },
                    timeout=300,
                    created_at=datetime.now(timezone.utc)
                )
                platform_analysis_tasks.append(task)
                await message_queue.enqueue_task(task)
            
            # Process platform analysis
            platform_results = {}
            for task in platform_analysis_tasks:
                agent = await agent_manager.assign_task_to_agent(task)
                if agent:
                    platform = task.payload['platform']
                    result = {
                        'platform': platform,
                        'tge_patterns_identified': 5,
                        'optimization_opportunities': [
                            f'{platform}_keyword_filtering',
                            f'{platform}_rate_limiting_optimization',
                            f'{platform}_data_extraction_efficiency'
                        ],
                        'platform_specific_insights': {
                            'user_behavior': f'{platform}_patterns',
                            'content_structure': f'{platform}_format',
                            'rate_limits': f'{platform}_limits'
                        }
                    }
                    
                    platform_results[platform] = result
                    await message_queue.submit_task_result(task.id, agent, result, success=True)
            
            # Step 2: Cross-platform optimization synthesis
            synthesis_task = TaskDefinition(
                id=str(uuid.uuid4()),
                type="cross_platform_optimization_synthesis",
                agent_type="performance-optimizer",
                priority=Priority.CRITICAL,
                payload={
                    'platform_analyses': platform_results,
                    'optimization_goal': 'unified_efficiency',
                    'target_improvement': '50%'
                },
                timeout=600,
                created_at=datetime.now(timezone.utc)
            )
            
            await message_queue.enqueue_task(synthesis_task)
            optimizer_agent = await agent_manager.assign_task_to_agent(synthesis_task)
            
            # Simulate cross-platform optimization
            synthesis_result = {
                'unified_optimizations': [
                    'shared_keyword_cache',
                    'adaptive_rate_limiting',
                    'cross_platform_deduplication',
                    'unified_data_normalization'
                ],
                'platform_specific_optimizations': {
                    platform: result['optimization_opportunities'] 
                    for platform, result in platform_results.items()
                },
                'estimated_improvement': '52%',
                'implementation_complexity': 'high',
                'coordination_requirements': ['shared_memory', 'cross_agent_communication']
            }
            
            await message_queue.submit_task_result(
                synthesis_task.id, optimizer_agent, synthesis_result, success=True
            )
            
            # Step 3: Implementation coordination
            for optimization in synthesis_result['unified_optimizations']:
                coordination_task = TaskDefinition(
                    id=str(uuid.uuid4()),
                    type="coordinated_optimization_implementation",
                    agent_type="scraping-efficiency",
                    priority=Priority.HIGH,
                    payload={
                        'optimization_type': optimization,
                        'affected_platforms': platforms,
                        'coordination_required': True,
                        'cross_platform_impact': True
                    },
                    timeout=400,
                    created_at=datetime.now(timezone.utc)
                )
                
                await message_queue.enqueue_task(coordination_task)
                impl_agent = await agent_manager.assign_task_to_agent(coordination_task)
                
                if impl_agent:
                    impl_result = {
                        'optimization_implemented': True,
                        'platforms_affected': platforms,
                        'implementation_successful': True,
                        'cross_platform_coordination': 'effective'
                    }
                    
                    await message_queue.submit_task_result(
                        coordination_task.id, impl_agent, impl_result, success=True
                    )
            
            # Record cross-platform success
            await coordination_service.record_coordination_event(
                'system',
                'cross_platform_optimization_completed',
                {
                    'platforms_optimized': platforms,
                    'optimizations_implemented': len(synthesis_result['unified_optimizations']),
                    'estimated_improvement': synthesis_result['estimated_improvement'],
                    'coordination_effective': True
                }
            )
            
            # Verify cross-platform workflow
            final_stats = await message_queue.get_task_statistics()
            expected_tasks = len(platforms) + 1 + len(synthesis_result['unified_optimizations'])
            
            assert final_stats['status_counts']['completed'] >= expected_tasks * 0.8
            
        finally:
            # Cleanup
            for agent_id in all_agents:
                await agent_manager.stop_agent(agent_id, force=True)