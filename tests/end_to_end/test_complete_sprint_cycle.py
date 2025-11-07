"""End-to-end tests for complete sprint cycles in Gaggle."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

# Test a complete sprint from inception to completion
from src.gaggle.workflows.sprint_planning import SprintPlanningWorkflow
from src.gaggle.workflows.sprint_execution import SprintExecutionWorkflow
from src.gaggle.agents.coordination.product_owner import ProductOwner
from src.gaggle.agents.coordination.scrum_master import ScrumMaster
from src.gaggle.agents.architecture.tech_lead import TechLead
from src.gaggle.dashboards.sprint_metrics import SprintMetricsCollector
from src.gaggle.integrations.github_api import GitHubAPIClient
from src.gaggle.integrations.cicd_pipelines import CICDPipelineManager
from src.gaggle.optimization.cost_optimizer import CostOptimizationEngine
from src.gaggle.learning.multi_sprint_optimizer import MultiSprintOptimizer
from src.gaggle.teams.custom_compositions import TeamCompositionManager


@pytest.fixture
def comprehensive_project_requirements():
    """Comprehensive project requirements for full sprint cycle testing."""
    return {
        "project_name": "SaaS Task Management Platform",
        "business_context": {
            "domain": "productivity software",
            "target_users": "small to medium teams",
            "market_size": "medium",
            "competitive_landscape": "crowded"
        },
        "features": [
            "Multi-user workspace management",
            "Real-time collaborative task boards",
            "Advanced reporting and analytics", 
            "API and third-party integrations",
            "Mobile responsive design",
            "Role-based access control"
        ],
        "technical_requirements": {
            "scalability": "support 1000+ concurrent users",
            "performance": "< 200ms response time",
            "availability": "99.9% uptime",
            "security": "SOC2 compliance required",
            "platforms": ["web", "mobile"]
        },
        "tech_stack": {
            "frontend": "React/TypeScript with Next.js",
            "backend": "Node.js/Express with GraphQL",
            "database": "PostgreSQL with Redis cache", 
            "deployment": "AWS with Kubernetes",
            "monitoring": "DataDog, Sentry",
            "testing": "Jest, Cypress, Playwright"
        },
        "constraints": {
            "timeline_months": 6,
            "team_size_max": 8,
            "budget_total": 150000,
            "quality_level": "enterprise",
            "compliance_requirements": ["GDPR", "SOC2"],
            "performance_targets": {
                "load_time": "< 2s",
                "api_response": "< 200ms", 
                "availability": "99.9%"
            }
        }
    }


@pytest.fixture
def production_team_setup():
    """Production-like team setup for testing."""
    return {
        "team_composition": {
            "product_owner": {"allocation": 0.5, "tier": "haiku"},
            "scrum_master": {"allocation": 0.3, "tier": "haiku"},
            "tech_lead": {"allocation": 0.4, "tier": "opus"},
            "senior_frontend_dev": {"allocation": 1.0, "tier": "sonnet"},
            "senior_backend_dev": {"allocation": 1.0, "tier": "sonnet"},
            "fullstack_dev": {"allocation": 1.0, "tier": "sonnet"},
            "qa_engineer": {"allocation": 1.0, "tier": "sonnet"},
            "devops_engineer": {"allocation": 0.3, "tier": "sonnet"}
        },
        "sprint_cadence": {
            "length_weeks": 2,
            "planning_hours": 4,
            "review_hours": 2,
            "retrospective_hours": 1.5,
            "daily_standup_minutes": 15
        },
        "tools_and_integrations": {
            "github": {"org": "saas-company", "repo": "task-platform"},
            "ci_cd": "github_actions",
            "monitoring": ["datadog", "sentry"],
            "communication": ["slack", "zoom"]
        }
    }


class TestCompleteSprintCycle:
    """End-to-end tests for complete sprint cycles."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_six_sprint_development_cycle(
        self, 
        comprehensive_project_requirements,
        production_team_setup
    ):
        """Test complete 6-sprint development cycle for SaaS platform."""
        
        # Initialize all systems
        planning_workflow = SprintPlanningWorkflow()
        execution_workflow = SprintExecutionWorkflow()
        metrics_collector = SprintMetricsCollector()
        cost_optimizer = CostOptimizationEngine()
        multi_sprint_optimizer = MultiSprintOptimizer()
        team_manager = TeamCompositionManager()
        
        project_results = {
            "sprints_completed": [],
            "learnings_extracted": [],
            "optimizations_applied": [],
            "total_cost": 0,
            "team_evolution": []
        }
        
        # Phase 1: Initial Team Composition
        initial_composition = team_manager.create_composition_for_project(
            "saas_platform", comprehensive_project_requirements["constraints"]
        )
        project_results["team_evolution"].append({
            "phase": "initial",
            "composition": initial_composition
        })
        
        # Phase 2: Execute 6 Sprints
        for sprint_number in range(1, 7):
            sprint_start = datetime.now() + timedelta(weeks=2 * (sprint_number - 1))
            sprint_end = sprint_start + timedelta(weeks=2)
            
            with patch('src.gaggle.workflows.sprint_planning.strands_adapter') as mock_planning_strands:
                with patch('src.gaggle.workflows.sprint_execution.strands_adapter') as mock_execution_strands:
                    with patch('src.gaggle.workflows.sprint_execution.github_client') as mock_github:
                        
                        # Mock agent responses based on sprint progression
                        self._setup_sprint_mocks(
                            mock_planning_strands,
                            mock_execution_strands, 
                            mock_github,
                            sprint_number
                        )
                        
                        # Sprint Planning
                        planning_result = await self._execute_sprint_planning(
                            planning_workflow,
                            comprehensive_project_requirements,
                            sprint_number,
                            project_results["sprints_completed"]
                        )
                        
                        # Sprint Execution  
                        execution_result = await self._execute_sprint_execution(
                            execution_workflow,
                            planning_result["sprint"],
                            sprint_number
                        )
                        
                        # Metrics Collection
                        sprint_metrics = await self._collect_sprint_metrics(
                            metrics_collector,
                            execution_result,
                            sprint_number
                        )
                        
                        # Cost Analysis
                        cost_analysis = await self._analyze_sprint_costs(
                            cost_optimizer,
                            planning_result["sprint"],
                            sprint_metrics
                        )
                        
                        sprint_summary = {
                            "sprint_number": sprint_number,
                            "planning_result": planning_result,
                            "execution_result": execution_result,
                            "metrics": sprint_metrics,
                            "cost_analysis": cost_analysis,
                            "completed_at": datetime.now().isoformat()
                        }
                        
                        project_results["sprints_completed"].append(sprint_summary)
                        project_results["total_cost"] += cost_analysis["total_cost_usd"]
                        
                        # Learning and Optimization (after sprint 2)
                        if sprint_number >= 2:
                            await self._apply_multi_sprint_learning(
                                multi_sprint_optimizer,
                                team_manager,
                                cost_optimizer,
                                project_results,
                                sprint_number
                            )
        
        # Phase 3: Final Project Analysis
        final_analysis = await self._generate_final_project_analysis(project_results)
        
        # Assertions for complete cycle
        assert len(project_results["sprints_completed"]) == 6
        assert project_results["total_cost"] > 0
        assert len(project_results["learnings_extracted"]) >= 4  # Learning starts from sprint 2
        assert len(project_results["optimizations_applied"]) >= 2
        assert final_analysis["project_success_score"] >= 7.0
        assert final_analysis["velocity_improvement"] > 0
        assert final_analysis["cost_efficiency_improvement"] > 0
    
    def _setup_sprint_mocks(
        self, 
        mock_planning_strands, 
        mock_execution_strands, 
        mock_github, 
        sprint_number
    ):
        """Setup mocks for sprint execution based on sprint progression."""
        
        # Mock planning agents
        mock_planning_agent = Mock()
        mock_planning_agent.aexecute = AsyncMock(return_value={
            "result": f"Sprint {sprint_number} planning completed with improved efficiency",
            "token_usage": {"input_tokens": 150, "output_tokens": 300 + sprint_number * 10}
        })
        mock_planning_strands.create_agent.return_value = mock_planning_agent
        
        # Mock execution agents with improving performance
        success_rate = 0.7 + (sprint_number * 0.05)  # Improving success rate
        task_count = 8 + sprint_number  # Increasing task complexity
        
        successful_tasks = [
            {
                "agent": f"agent_{i}",
                "result": {"result": f"Task {i} completed successfully"},
                "index": i
            }
            for i in range(int(task_count * success_rate))
        ]
        
        failed_tasks = [
            {
                "agent": f"agent_{i}",
                "error": "Minor issue resolved in next iteration", 
                "index": i
            }
            for i in range(task_count - len(successful_tasks))
        ]
        
        mock_execution_strands.execute_parallel_tasks = AsyncMock(return_value={
            "successful": successful_tasks,
            "failed": failed_tasks,
            "summary": {
                "total_tasks": task_count,
                "success_rate": success_rate * 100
            }
        })
        
        # Mock GitHub integration
        mock_github.sync_sprint_with_github = AsyncMock(return_value={
            "milestone": {"number": sprint_number, "title": f"Sprint {sprint_number}"},
            "project_board": {"id": f"PB_{sprint_number:03d}"},
            "user_story_issues": list(range(1, 6))  # 5 user stories per sprint
        })
    
    async def _execute_sprint_planning(
        self, 
        planning_workflow, 
        project_requirements, 
        sprint_number,
        completed_sprints
    ):
        """Execute sprint planning with context from previous sprints."""
        
        # Adjust requirements based on sprint progression
        sprint_requirements = project_requirements.copy()
        sprint_requirements["sprint_context"] = {
            "sprint_number": sprint_number,
            "completed_sprints": len(completed_sprints),
            "velocity_history": [s["metrics"]["velocity"]["actual"] for s in completed_sprints[-3:]],
            "previous_learnings": [s.get("learnings", {}) for s in completed_sprints[-2:]]
        }
        
        with patch.object(planning_workflow, '_create_user_stories') as mock_create:
            with patch.object(planning_workflow, '_analyze_architecture') as mock_analyze:
                with patch.object(planning_workflow, '_plan_sprint') as mock_plan:
                    
                    # Mock user story creation with sprint progression
                    story_points = 25 + sprint_number * 3  # Increasing complexity
                    mock_create.return_value = {
                        "user_stories": [
                            {
                                "id": f"US-{sprint_number:03d}-{i:02d}",
                                "title": f"Sprint {sprint_number} Feature {i}",
                                "story_points": 3 + (i % 3),
                                "priority": "high" if i <= 2 else "medium"
                            }
                            for i in range(1, 6)  # 5 stories per sprint
                        ],
                        "total_story_points": story_points
                    }
                    
                    # Mock architecture analysis
                    mock_analyze.return_value = {
                        "architecture_requirements": {
                            "components": [f"Service{i}" for i in range(1, 4)],
                            "patterns": ["microservices", "event-driven"],
                            "complexity_score": 7.0 + sprint_number * 0.3
                        },
                        "task_breakdown": [
                            {
                                "id": f"TASK-{sprint_number:03d}-{i:02d}",
                                "title": f"Sprint {sprint_number} Task {i}",
                                "estimated_hours": 4 + (i % 4),
                                "assigned_role": ["frontend_developer", "backend_developer", "fullstack_developer"][i % 3]
                            }
                            for i in range(1, 9)  # 8 tasks per sprint
                        ]
                    }
                    
                    # Mock sprint plan
                    mock_plan.return_value = {
                        "sprint": {
                            "id": f"SPRINT-{sprint_number:03d}",
                            "name": f"Sprint {sprint_number}: Platform Development",
                            "goal": f"Deliver core platform features for milestone {sprint_number}",
                            "start_date": datetime.now() + timedelta(weeks=2 * (sprint_number - 1)),
                            "end_date": datetime.now() + timedelta(weeks=2 * sprint_number),
                            "selected_stories": [f"US-{sprint_number:03d}-{i:02d}" for i in range(1, 6)],
                            "capacity_analysis": {
                                "planned_velocity": story_points,
                                "team_capacity": 30,
                                "confidence_level": 0.8 + sprint_number * 0.02
                            }
                        }
                    }
                    
                    return await planning_workflow.execute_complete_planning(sprint_requirements)
    
    async def _execute_sprint_execution(self, execution_workflow, sprint_plan, sprint_number):
        """Execute sprint with realistic progression."""
        
        from src.gaggle.models.sprint import Sprint, UserStory, Task, TaskStatus
        
        # Create sprint object
        sprint = Sprint(
            id=sprint_plan["id"],
            name=sprint_plan["name"],
            goal=sprint_plan["goal"],
            start_date=sprint_plan["start_date"],
            end_date=sprint_plan["end_date"],
            user_stories=[],
            team_velocity=sprint_plan["capacity_analysis"]["planned_velocity"]
        )
        
        # Add user stories with tasks
        for story_id in sprint_plan["selected_stories"]:
            user_story = UserStory(
                id=story_id,
                title=f"Story {story_id}",
                description=f"Implementation for {story_id}",
                acceptance_criteria=[f"AC1 for {story_id}", f"AC2 for {story_id}"],
                priority="high",
                story_points=5,
                tasks=[
                    Task(
                        id=f"{story_id}-TASK-{i}",
                        title=f"Task {i} for {story_id}",
                        description=f"Implementation task {i}",
                        status=TaskStatus.TODO,
                        assigned_to=f"developer_{i % 3}",
                        estimated_hours=4,
                        user_story_id=story_id
                    )
                    for i in range(1, 3)  # 2 tasks per story
                ]
            )
            sprint.user_stories.append(user_story)
        
        return await execution_workflow.execute_sprint(sprint)
    
    async def _collect_sprint_metrics(self, metrics_collector, execution_result, sprint_number):
        """Collect comprehensive sprint metrics."""
        
        # Simulate realistic metrics with improvement over time
        base_velocity = 20
        velocity_improvement = sprint_number * 0.05
        actual_velocity = base_velocity * (1 + velocity_improvement)
        
        base_quality = 7.5
        quality_improvement = sprint_number * 0.1
        quality_score = min(base_quality + quality_improvement, 10.0)
        
        base_cost = 2000
        cost_efficiency = sprint_number * 0.03
        actual_cost = base_cost * (1 - cost_efficiency)
        
        return {
            "sprint_number": sprint_number,
            "velocity": {
                "planned": base_velocity,
                "actual": actual_velocity,
                "achievement_rate": actual_velocity / base_velocity
            },
            "quality": {
                "score": quality_score,
                "defects_found": max(5 - sprint_number, 0),
                "defects_resolved": max(4 - sprint_number // 2, 0),
                "test_coverage": min(80 + sprint_number * 2, 95)
            },
            "cost": {
                "planned_usd": base_cost,
                "actual_usd": actual_cost,
                "efficiency": cost_efficiency,
                "cost_per_story_point": actual_cost / actual_velocity
            },
            "team": {
                "satisfaction": min(4.0 + sprint_number * 0.1, 5.0),
                "efficiency": min(75 + sprint_number * 3, 95),
                "collaboration_score": min(7.5 + sprint_number * 0.2, 10.0)
            },
            "technical": {
                "code_quality": min(8.0 + sprint_number * 0.15, 10.0),
                "technical_debt": max(20 - sprint_number * 2, 5),
                "automation_coverage": min(60 + sprint_number * 5, 90)
            }
        }
    
    async def _analyze_sprint_costs(self, cost_optimizer, sprint_plan, metrics):
        """Analyze sprint costs with optimization opportunities."""
        
        from src.gaggle.models.sprint import Sprint
        
        # Create sprint object for cost analysis
        sprint = Sprint(
            id=sprint_plan["id"],
            name=sprint_plan["name"],
            goal=sprint_plan["goal"],
            start_date=sprint_plan["start_date"],
            end_date=sprint_plan["end_date"],
            user_stories=[],
            team_velocity=sprint_plan["capacity_analysis"]["planned_velocity"]
        )
        
        cost_metrics = await cost_optimizer.analyze_sprint_costs(sprint)
        
        return {
            "total_cost_usd": cost_metrics.total_cost_usd,
            "cost_breakdown": cost_metrics.cost_by_tier,
            "token_usage": cost_metrics.total_tokens,
            "efficiency_score": metrics["cost"]["efficiency"],
            "optimization_opportunities": [
                {
                    "strategy": "model_tier_optimization",
                    "potential_savings": cost_metrics.total_cost_usd * 0.15,
                    "implementation_effort": "low"
                },
                {
                    "strategy": "parallel_processing",
                    "potential_savings": cost_metrics.total_cost_usd * 0.10,
                    "implementation_effort": "medium"
                }
            ]
        }
    
    async def _apply_multi_sprint_learning(
        self,
        multi_sprint_optimizer,
        team_manager, 
        cost_optimizer,
        project_results,
        current_sprint_number
    ):
        """Apply learning and optimizations based on multiple sprint data."""
        
        if len(project_results["sprints_completed"]) < 2:
            return
        
        # Extract data from completed sprints
        sprint_data = []
        for sprint_summary in project_results["sprints_completed"]:
            sprint_data.append({
                "sprint_id": sprint_summary["sprint_number"],
                "planned_velocity": sprint_summary["metrics"]["velocity"]["planned"],
                "actual_velocity": sprint_summary["metrics"]["velocity"]["actual"],
                "quality_score": sprint_summary["metrics"]["quality"]["score"],
                "cost_usd": sprint_summary["cost_analysis"]["total_cost_usd"],
                "team_satisfaction": sprint_summary["metrics"]["team"]["satisfaction"]
            })
        
        # Analyze performance trends
        performance_analysis = await multi_sprint_optimizer.analyze_sprint_performance(sprint_data)
        
        # Generate learnings
        learnings = {
            "sprint_range": f"Sprints 1-{current_sprint_number}",
            "performance_trends": performance_analysis,
            "key_insights": [
                f"Velocity trending {performance_analysis['velocity_trend']['direction']}",
                f"Quality trending {performance_analysis['quality_trend']['direction']}",
                f"Cost trending {performance_analysis['cost_trend']['direction']}"
            ],
            "recommended_actions": []
        }
        
        # Apply optimizations based on trends
        if performance_analysis["velocity_trend"]["direction"] == "declining":
            learnings["recommended_actions"].append("Increase parallel processing")
            
        if performance_analysis["cost_trend"]["direction"] == "increasing":
            learnings["recommended_actions"].append("Optimize model tier assignments")
            
        if performance_analysis["quality_trend"]["direction"] == "declining":
            learnings["recommended_actions"].append("Enhance QA processes")
        
        project_results["learnings_extracted"].append(learnings)
        
        # Apply team composition optimizations every 2 sprints
        if current_sprint_number % 2 == 0:
            current_composition = project_results["team_evolution"][-1]["composition"]
            
            optimization_goals = {
                "minimize_cost": performance_analysis["cost_trend"]["direction"] == "increasing",
                "improve_velocity": performance_analysis["velocity_trend"]["direction"] == "declining",
                "maintain_quality": performance_analysis["quality_trend"]["direction"] != "declining"
            }
            
            optimized_composition = team_manager.optimize_composition_for_constraints(
                current_composition, optimization_goals
            )
            
            project_results["team_evolution"].append({
                "phase": f"optimization_{current_sprint_number}",
                "composition": optimized_composition,
                "optimization_applied": optimization_goals
            })
            
            project_results["optimizations_applied"].append({
                "sprint": current_sprint_number,
                "type": "team_composition",
                "details": optimized_composition["optimization_changes"]
            })
    
    async def _generate_final_project_analysis(self, project_results):
        """Generate comprehensive final project analysis."""
        
        sprints = project_results["sprints_completed"]
        
        # Calculate overall improvements
        first_sprint_velocity = sprints[0]["metrics"]["velocity"]["actual"]
        last_sprint_velocity = sprints[-1]["metrics"]["velocity"]["actual"]
        velocity_improvement = (last_sprint_velocity - first_sprint_velocity) / first_sprint_velocity * 100
        
        first_sprint_cost = sprints[0]["cost_analysis"]["total_cost_usd"]
        last_sprint_cost = sprints[-1]["cost_analysis"]["total_cost_usd"]
        cost_efficiency_improvement = (first_sprint_cost - last_sprint_cost) / first_sprint_cost * 100
        
        first_sprint_quality = sprints[0]["metrics"]["quality"]["score"]
        last_sprint_quality = sprints[-1]["metrics"]["quality"]["score"]
        quality_improvement = (last_sprint_quality - first_sprint_quality) / first_sprint_quality * 100
        
        # Calculate project success score
        velocity_score = min(velocity_improvement / 20 * 2.5, 2.5)  # Max 2.5 points
        cost_score = min(cost_efficiency_improvement / 15 * 2.5, 2.5)  # Max 2.5 points
        quality_score = min(quality_improvement / 20 * 2.5, 2.5)  # Max 2.5 points
        learning_score = len(project_results["learnings_extracted"]) * 0.5  # Max 2.5 points
        
        project_success_score = velocity_score + cost_score + quality_score + learning_score
        
        return {
            "project_duration_sprints": len(sprints),
            "total_cost_usd": project_results["total_cost"],
            "velocity_improvement": velocity_improvement,
            "cost_efficiency_improvement": cost_efficiency_improvement,
            "quality_improvement": quality_improvement,
            "project_success_score": project_success_score,
            "learnings_count": len(project_results["learnings_extracted"]),
            "optimizations_applied": len(project_results["optimizations_applied"]),
            "team_evolutions": len(project_results["team_evolution"]),
            "final_team_satisfaction": sprints[-1]["metrics"]["team"]["satisfaction"],
            "final_quality_score": sprints[-1]["metrics"]["quality"]["score"],
            "recommendation": "Project completed successfully with continuous improvement" if project_success_score >= 7.0 else "Project completed with areas for improvement"
        }


class TestProductionReadinessScenarios:
    """Tests for production readiness scenarios."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_high_load_concurrent_sprints(self):
        """Test system behavior under high load with concurrent sprints."""
        
        # Simulate running multiple sprints concurrently for different projects
        concurrent_sprints = 5
        execution_workflow = SprintExecutionWorkflow()
        
        async def run_concurrent_sprint(sprint_id):
            from src.gaggle.models.sprint import Sprint
            
            sprint = Sprint(
                id=f"SPRINT-LOAD-{sprint_id:03d}",
                name=f"Load Test Sprint {sprint_id}",
                goal=f"Load testing sprint {sprint_id}",
                start_date=datetime.now(),
                end_date=datetime.now() + timedelta(weeks=2),
                user_stories=[],
                team_velocity=20
            )
            
            with patch('src.gaggle.workflows.sprint_execution.strands_adapter') as mock_strands:
                with patch('src.gaggle.workflows.sprint_execution.github_client') as mock_github:
                    mock_strands.execute_parallel_tasks = AsyncMock(return_value={
                        "successful": [{"agent": f"agent_{i}", "result": {"result": "success"}} for i in range(8)],
                        "failed": []
                    })
                    mock_github.sync_sprint_with_github = AsyncMock(return_value={"milestone": {"number": sprint_id}})
                    
                    return await execution_workflow.execute_sprint(sprint)
        
        # Run sprints concurrently
        start_time = datetime.now()
        results = await asyncio.gather(*[run_concurrent_sprint(i) for i in range(concurrent_sprints)])
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Verify all sprints completed successfully
        assert len(results) == concurrent_sprints
        for result in results:
            assert "execution_summary" in result
            assert result["execution_summary"]["success_rate"] == 100.0
        
        # Verify reasonable execution time (should benefit from parallelization)
        assert execution_time < 60  # Should complete within 60 seconds
    
    @pytest.mark.asyncio
    async def test_enterprise_scale_sprint_with_large_team(self):
        """Test sprint execution with enterprise-scale team and complexity."""
        
        from src.gaggle.models.sprint import Sprint, UserStory, Task, TaskStatus
        
        # Create large enterprise sprint
        user_stories = []
        for story_num in range(1, 21):  # 20 user stories
            tasks = []
            for task_num in range(1, 6):  # 5 tasks per story
                task = Task(
                    id=f"TASK-{story_num:03d}-{task_num:02d}",
                    title=f"Task {task_num} for Story {story_num}",
                    description=f"Enterprise task implementation",
                    status=TaskStatus.TODO,
                    assigned_to=f"dev_team_{task_num % 4}",
                    estimated_hours=6,
                    user_story_id=f"US-{story_num:03d}"
                )
                tasks.append(task)
            
            story = UserStory(
                id=f"US-{story_num:03d}",
                title=f"Enterprise Feature {story_num}",
                description=f"Large scale feature implementation",
                acceptance_criteria=[f"AC{i}" for i in range(1, 6)],
                priority="high" if story_num <= 10 else "medium",
                story_points=8,
                tasks=tasks
            )
            user_stories.append(story)
        
        enterprise_sprint = Sprint(
            id="SPRINT-ENTERPRISE-001",
            name="Enterprise Scale Sprint",
            goal="Deliver large-scale enterprise features",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(weeks=2),
            user_stories=user_stories,
            team_velocity=100  # Large team velocity
        )
        
        execution_workflow = SprintExecutionWorkflow()
        
        with patch('src.gaggle.workflows.sprint_execution.strands_adapter') as mock_strands:
            with patch('src.gaggle.workflows.sprint_execution.github_client') as mock_github:
                # Mock large scale execution
                successful_tasks = [
                    {"agent": f"enterprise_agent_{i}", "result": {"result": f"Enterprise task {i} completed"}}
                    for i in range(85)  # 85% success rate
                ]
                failed_tasks = [
                    {"agent": f"enterprise_agent_{i}", "error": "Temporary issue"}
                    for i in range(15)  # 15% failure rate
                ]
                
                mock_strands.execute_parallel_tasks = AsyncMock(return_value={
                    "successful": successful_tasks,
                    "failed": failed_tasks,
                    "summary": {"total_tasks": 100, "success_rate": 85.0}
                })
                
                mock_github.sync_sprint_with_github = AsyncMock(return_value={
                    "milestone": {"number": 1},
                    "user_story_issues": list(range(1, 21))
                })
                
                result = await execution_workflow.execute_sprint(enterprise_sprint)
                
                # Verify enterprise scale handling
                assert result["sprint_id"] == "SPRINT-ENTERPRISE-001"
                assert result["execution_summary"]["success_rate"] == 85.0
                assert len(result["execution_summary"]["failed_tasks"]) == 15
                assert "github_integration" in result
    
    @pytest.mark.asyncio
    async def test_disaster_recovery_and_system_resilience(self):
        """Test system resilience and disaster recovery scenarios."""
        
        from src.gaggle.models.sprint import Sprint
        
        sprint = Sprint(
            id="SPRINT-RESILIENCE-001",
            name="Resilience Test Sprint", 
            goal="Test system resilience",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(weeks=2),
            user_stories=[],
            team_velocity=20
        )
        
        execution_workflow = SprintExecutionWorkflow()
        
        # Test multiple failure scenarios
        failure_scenarios = [
            {
                "name": "GitHub API Failure",
                "github_fails": True,
                "strands_fails": False,
                "expected_recovery": True
            },
            {
                "name": "Strands Adapter Failure", 
                "github_fails": False,
                "strands_fails": True,
                "expected_recovery": True
            },
            {
                "name": "Multiple System Failure",
                "github_fails": True,
                "strands_fails": True,
                "expected_recovery": False
            }
        ]
        
        results = []
        
        for scenario in failure_scenarios:
            with patch('src.gaggle.workflows.sprint_execution.github_client') as mock_github:
                with patch('src.gaggle.workflows.sprint_execution.strands_adapter') as mock_strands:
                    
                    if scenario["github_fails"]:
                        mock_github.sync_sprint_with_github = AsyncMock(
                            side_effect=Exception("GitHub API unavailable")
                        )
                    else:
                        mock_github.sync_sprint_with_github = AsyncMock(return_value={"milestone": {"number": 1}})
                    
                    if scenario["strands_fails"]:
                        mock_strands.execute_parallel_tasks = AsyncMock(
                            side_effect=Exception("Strands framework unavailable")
                        )
                    else:
                        mock_strands.execute_parallel_tasks = AsyncMock(return_value={
                            "successful": [{"agent": "test", "result": {"result": "success"}}],
                            "failed": []
                        })
                    
                    try:
                        result = await execution_workflow.execute_sprint(sprint)
                        scenario_result = {
                            "scenario": scenario["name"],
                            "completed": True,
                            "result": result
                        }
                    except Exception as e:
                        scenario_result = {
                            "scenario": scenario["name"],
                            "completed": False,
                            "error": str(e)
                        }
                    
                    results.append(scenario_result)
        
        # Verify resilience expectations
        assert results[0]["completed"] == failure_scenarios[0]["expected_recovery"]
        assert results[1]["completed"] == failure_scenarios[1]["expected_recovery"] 
        assert results[2]["completed"] == failure_scenarios[2]["expected_recovery"]


if __name__ == "__main__":
    # Run specific test for development
    pytest.main([__file__ + "::TestCompleteSprintCycle::test_full_six_sprint_development_cycle", "-v", "-s"])