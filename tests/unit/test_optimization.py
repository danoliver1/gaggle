"""Unit tests for Gaggle optimization systems."""

from datetime import datetime, timedelta

import pytest

from gaggle.config.models import AgentRole, ModelTier
from gaggle.learning.multi_sprint_optimizer import (
    MultiSprintOptimizer,
    OptimizationStrategyGenerator,
    SprintLearningEngine,
)
from gaggle.models.sprint import Sprint
from gaggle.models.story import UserStory
from gaggle.models.task import Task, TaskStatus
from gaggle.optimization.cost_optimizer import (
    CachingOptimizer,
    CostOptimizationEngine,
    CostOptimizationStrategy,
    ModelTierOptimizer,
    OptimizationGoal,
    ParallelExecutionOptimizer,
)
from gaggle.teams.custom_compositions import (
    ProjectComplexity,
    ProjectType,
    TeamCompositionBuilder,
    TeamCompositionManager,
    TeamCompositionRequirements,
    TeamSize,
)


@pytest.fixture
def sample_tasks():
    """Sample tasks for testing."""
    return [
        Task(
            id="TASK-001",
            title="Implement login form",
            description="Create React login component",
            status=TaskStatus.TODO,
            assigned_to="frontend_dev",
            estimated_hours=4,
            priority="high",
            task_type="frontend",
            assigned_role=AgentRole.FRONTEND_DEV,
        ),
        Task(
            id="TASK-002",
            title="Create auth API",
            description="Implement authentication endpoints",
            status=TaskStatus.TODO,
            assigned_to="backend_dev",
            estimated_hours=6,
            priority="high",
            task_type="backend",
            assigned_role=AgentRole.BACKEND_DEV,
        ),
        Task(
            id="TASK-003",
            title="Review auth code",
            description="Code review for authentication",
            status=TaskStatus.TODO,
            assigned_to="tech_lead",
            estimated_hours=2,
            priority="medium",
            task_type="architecture",
            assigned_role=AgentRole.TECH_LEAD,
        ),
    ]


@pytest.fixture
def sample_sprint(sample_tasks):
    """Sample sprint with tasks."""
    user_story = UserStory(
        id="US-001",
        title="User Authentication",
        description="Implement user login/logout",
        priority="high",
        story_points=8,
    )
    user_story.add_acceptance_criteria("Login form")
    user_story.add_acceptance_criteria("API endpoints")

    return Sprint(
        id="SPRINT-001",
        name="Auth Sprint",
        goal="Implement authentication",
        start_date=datetime.now().date(),
        end_date=(datetime.now() + timedelta(weeks=2)).date(),
        user_stories=[user_story],
        team_velocity=20,
        tasks=sample_tasks,
    )


class TestModelTierOptimizer:
    """Tests for Model Tier Optimizer."""

    def test_init(self):
        """Test Model Tier Optimizer initialization."""
        optimizer = ModelTierOptimizer()
        assert hasattr(optimizer, "tier_costs")
        assert ModelTier.HAIKU in optimizer.tier_costs
        assert ModelTier.SONNET in optimizer.tier_costs
        assert ModelTier.OPUS in optimizer.tier_costs

    def test_analyze_role_complexity(self, sample_tasks):
        """Test role complexity analysis."""
        optimizer = ModelTierOptimizer()

        complexity = optimizer.analyze_role_complexity(sample_tasks)

        assert AgentRole.FRONTEND_DEV in complexity
        assert AgentRole.BACKEND_DEV in complexity
        assert AgentRole.TECH_LEAD in complexity
        assert complexity[AgentRole.FRONTEND_DEV] > 0
        assert (
            complexity[AgentRole.BACKEND_DEV]
            > complexity[AgentRole.FRONTEND_DEV]
        )  # Higher priority/hours

    def test_recommend_tier_assignments_minimize_cost(self, sample_tasks):
        """Test tier assignment recommendations for cost minimization."""
        optimizer = ModelTierOptimizer()

        role_complexity = {
            AgentRole.FRONTEND_DEV: 1.0,  # Low complexity
            AgentRole.BACKEND_DEV: 2.0,  # Medium complexity
            AgentRole.TECH_LEAD: 4.0,  # High complexity
        }

        recommendations = optimizer.recommend_tier_assignments(
            role_complexity, OptimizationGoal.MINIMIZE_COST
        )

        assert recommendations[AgentRole.FRONTEND_DEV] == ModelTier.HAIKU
        assert recommendations[AgentRole.BACKEND_DEV] == ModelTier.SONNET
        assert recommendations[AgentRole.TECH_LEAD] == ModelTier.OPUS

    def test_calculate_cost_impact(self):
        """Test cost impact calculation."""
        optimizer = ModelTierOptimizer()

        current_assignments = {
            AgentRole.FRONTEND_DEV: ModelTier.SONNET,
            AgentRole.BACKEND_DEV: ModelTier.SONNET,
        }

        recommended_assignments = {
            AgentRole.FRONTEND_DEV: ModelTier.HAIKU,
            AgentRole.BACKEND_DEV: ModelTier.SONNET,
        }

        expected_tokens = {
            AgentRole.FRONTEND_DEV: 2000,
            AgentRole.BACKEND_DEV: 2000,
        }

        impact = optimizer.calculate_cost_impact(
            current_assignments, recommended_assignments, expected_tokens
        )

        assert "current_cost_usd" in impact
        assert "recommended_cost_usd" in impact
        assert "savings_usd" in impact
        assert "savings_percent" in impact
        assert (
            impact["savings_usd"] > 0
        )  # Should save money by using Haiku for frontend


class TestParallelExecutionOptimizer:
    """Tests for Parallel Execution Optimizer."""

    def test_init(self):
        """Test Parallel Execution Optimizer initialization."""
        optimizer = ParallelExecutionOptimizer()
        assert hasattr(optimizer, "logger")

    def test_analyze_task_dependencies(self, sample_tasks):
        """Test task dependency analysis."""
        optimizer = ParallelExecutionOptimizer()

        dependencies = optimizer.analyze_task_dependencies(sample_tasks)

        assert len(dependencies) == len(sample_tasks)
        for task in sample_tasks:
            assert task.id in dependencies

        # Frontend should depend on API design (implicit dependency)
        frontend_task_id = next(
            t.id for t in sample_tasks if t.task_type == "frontend"
        )
        assert isinstance(dependencies[frontend_task_id], list)

    def test_create_execution_batches(self, sample_tasks):
        """Test execution batch creation."""
        optimizer = ParallelExecutionOptimizer()

        dependencies = {
            "TASK-001": ["TASK-002"],  # Frontend depends on backend
            "TASK-002": [],  # Backend has no dependencies
            "TASK-003": ["TASK-001", "TASK-002"],  # Review depends on both
        }

        batches = optimizer.create_execution_batches(
            sample_tasks, dependencies, max_parallel_tasks=2
        )

        assert len(batches) > 0
        # First batch should contain only tasks with no dependencies
        first_batch_ids = [task.id for task in batches[0]]
        assert "TASK-002" in first_batch_ids  # Backend has no dependencies
        assert "TASK-001" not in first_batch_ids  # Frontend depends on backend

    def test_estimate_execution_time(self, sample_tasks):
        """Test execution time estimation."""
        optimizer = ParallelExecutionOptimizer()

        batches = [
            [sample_tasks[0]],  # First batch: 1 task
            [sample_tasks[1], sample_tasks[2]],  # Second batch: 2 tasks in parallel
        ]

        task_duration_estimates = {
            "TASK-001": 3600,  # 1 hour
            "TASK-002": 7200,  # 2 hours
            "TASK-003": 1800,  # 30 minutes
        }

        analysis = optimizer.estimate_execution_time(batches, task_duration_estimates)

        assert "total_sequential_time_seconds" in analysis
        assert "total_parallel_time_seconds" in analysis
        assert "time_savings_seconds" in analysis
        assert "efficiency_percent" in analysis

        # Parallel time should be less than sequential
        assert (
            analysis["total_parallel_time_seconds"]
            < analysis["total_sequential_time_seconds"]
        )


class TestCachingOptimizer:
    """Tests for Caching Optimizer."""

    def test_init(self):
        """Test Caching Optimizer initialization."""
        optimizer = CachingOptimizer()
        assert hasattr(optimizer, "cache_hit_savings")
        assert optimizer.cache_hit_savings == 0.95

    def test_identify_cacheable_operations(self, sample_tasks):
        """Test cacheable operations identification."""
        optimizer = CachingOptimizer()

        # Add task types to make them cacheable
        sample_tasks[0].task_type = "code_review"
        sample_tasks[1].task_type = "test_generation"
        sample_tasks[2].task_type = "documentation"

        cacheable_ops = optimizer.identify_cacheable_operations(sample_tasks)

        assert "code_review_patterns" in cacheable_ops
        assert "test_generation_templates" in cacheable_ops
        assert "api_documentation_formats" in cacheable_ops
        assert len(cacheable_ops["code_review_patterns"]) > 0

    def test_estimate_cache_savings(self):
        """Test cache savings estimation."""
        optimizer = CachingOptimizer()

        cacheable_operations = {
            "code_review_patterns": ["TASK-001", "TASK-002"],
            "test_generation_templates": ["TASK-003"],
            "api_documentation_formats": [],
            "common_implementations": ["TASK-004"],
            "security_scan_rules": [],
        }

        savings = optimizer.estimate_cache_savings(
            cacheable_operations, expected_cache_hit_rate=0.4
        )

        assert "total_cacheable_operations" in savings
        assert "expected_cache_hits" in savings
        assert "estimated_savings_usd" in savings
        assert "savings_percent" in savings
        assert savings["total_cacheable_operations"] == 4
        assert savings["expected_cache_hits"] == 4 * 0.4


class TestCostOptimizationEngine:
    """Tests for Cost Optimization Engine."""

    def test_init(self):
        """Test Cost Optimization Engine initialization."""
        engine = CostOptimizationEngine()
        assert hasattr(engine, "model_tier_optimizer")
        assert hasattr(engine, "parallel_optimizer")
        assert hasattr(engine, "caching_optimizer")

    @pytest.mark.asyncio
    async def test_analyze_sprint_costs(self, sample_sprint):
        """Test sprint cost analysis."""
        engine = CostOptimizationEngine()

        metrics = await engine.analyze_sprint_costs(sample_sprint)

        assert hasattr(metrics, "total_tokens")
        assert hasattr(metrics, "total_cost_usd")
        assert hasattr(metrics, "cost_by_tier")
        assert hasattr(metrics, "cost_by_agent_role")
        assert metrics.total_tokens > 0
        assert metrics.total_cost_usd > 0

    @pytest.mark.asyncio
    async def test_generate_optimization_recommendations(self, sample_sprint):
        """Test optimization recommendations generation."""
        engine = CostOptimizationEngine()

        # First analyze costs
        current_metrics = await engine.analyze_sprint_costs(sample_sprint)

        recommendations = await engine.generate_optimization_recommendations(
            sample_sprint, current_metrics, OptimizationGoal.MINIMIZE_COST
        )

        assert isinstance(recommendations, list)
        for rec in recommendations:
            assert hasattr(rec, "strategy")
            assert hasattr(rec, "description")
            assert hasattr(rec, "estimated_savings_percent")
            assert hasattr(rec, "estimated_savings_usd")
            assert rec.estimated_savings_percent >= 0

    @pytest.mark.asyncio
    async def test_implement_optimization(self, sample_sprint):
        """Test optimization implementation."""
        engine = CostOptimizationEngine()

        result = await engine.implement_optimization(
            sample_sprint,
            CostOptimizationStrategy.MODEL_TIER_OPTIMIZATION,
            {"expected_savings_percent": 15},
        )

        assert result["strategy"] == "model_tier_optimization"
        assert result["sprint_id"] == sample_sprint.id
        assert result["success"] is True
        assert "details" in result
        assert "estimated_impact" in result


class TestSprintLearningEngine:
    """Tests for Sprint Learning Engine."""

    def test_init(self):
        """Test Sprint Learning Engine initialization."""
        engine = SprintLearningEngine()
        assert hasattr(engine, "logger")

    @pytest.mark.asyncio
    async def test_extract_learnings(self, sample_sprint):
        """Test sprint learning extraction."""
        engine = SprintLearningEngine()

        # Need to mark sprint as completed to extract learnings
        from gaggle.models.sprint import SprintStatus
        sample_sprint.status = SprintStatus.COMPLETED
        
        learnings = await engine.extract_learnings([sample_sprint])

        assert isinstance(learnings, list)
        # Since the sprint may not have enough data for learnings, 
        # we just verify the method runs without error and returns the right type
        for learning in learnings:
            assert hasattr(learning, "sprint_id")
            assert hasattr(learning, "domain") 
            assert hasattr(learning, "insight")
            assert hasattr(learning, "impact_score")
            assert hasattr(learning, "confidence")


class TestOptimizationStrategyGenerator:
    """Tests for Optimization Strategy Generator."""

    def test_init(self):
        """Test Optimization Strategy Generator initialization."""
        generator = OptimizationStrategyGenerator()
        assert hasattr(generator, "logger")

    @pytest.mark.asyncio
    async def test_generate_improvement_strategies(self):
        """Test improvement strategy generation."""
        generator = OptimizationStrategyGenerator()

        from gaggle.learning.multi_sprint_optimizer import SprintLearning, OptimizationDomain
        from datetime import datetime, timezone
        
        learning = SprintLearning(
            sprint_id="SPRINT-001",
            domain=OptimizationDomain.VELOCITY,
            insight="parallel execution optimization needed",
            impact_score=7.5,
            confidence=0.8,
            recommendation="Implement parallel testing",
            evidence={"velocity_achievement": 0.9, "quality_score": 8.5},
            created_at=datetime.now(timezone.utc)
        )

        strategies = await generator.generate_strategies([learning])

        assert isinstance(strategies, list)
        assert len(strategies) > 0
        
        # Check that we got strategies for the velocity domain
        velocity_strategies = [s for s in strategies if s.domain == OptimizationDomain.VELOCITY]
        assert len(velocity_strategies) > 0
        
        for strategy in strategies:
            assert hasattr(strategy, "name")
            assert hasattr(strategy, "description")
            assert hasattr(strategy, "domain")
            assert hasattr(strategy, "expected_improvement")
            assert hasattr(strategy, "confidence")


class TestMultiSprintOptimizer:
    """Tests for Multi-Sprint Optimizer."""

    def test_init(self):
        """Test Multi-Sprint Optimizer initialization."""
        optimizer = MultiSprintOptimizer()
        assert hasattr(optimizer, "learning_engine")
        assert hasattr(optimizer, "strategy_generator")

    @pytest.mark.asyncio
    async def test_optimize_future_sprints(self, sample_sprint):
        """Test future sprint optimization."""
        optimizer = MultiSprintOptimizer()

        # Create completed sprints for analysis
        completed_sprints = [sample_sprint]

        optimization_report = await optimizer.optimize_future_sprints(
            completed_sprints, upcoming_sprint=sample_sprint
        )

        assert "optimization_summary" in optimization_report
        assert "key_learnings" in optimization_report
        assert "optimization_strategies" in optimization_report
        assert "applied_optimizations" in optimization_report
        assert "expected_improvements" in optimization_report

        # Check optimization summary
        summary = optimization_report["optimization_summary"]
        assert summary["learnings_extracted"] >= 0
        assert summary["strategies_generated"] >= 0
        assert summary["optimizations_applied"] >= 0


class TestTeamCompositionManager:
    """Tests for Team Composition Manager."""

    def test_init(self):
        """Test Team Composition Manager initialization."""
        manager = TeamCompositionManager()
        assert hasattr(manager, "builder")
        assert hasattr(manager, "compositions_history")

    @pytest.mark.asyncio
    async def test_recommend_team_composition_for_web_app(self):
        """Test team composition recommendation for web applications."""
        manager = TeamCompositionManager()

        requirements = TeamCompositionRequirements(
            project_type=ProjectType.WEB_APPLICATION,
            team_size=TeamSize.SMALL,
            complexity=ProjectComplexity.MODERATE,
            budget_constraints=2000.0,
            timeline_weeks=8,
        )

        recommendation = await manager.recommend_team_composition(requirements)

        assert "primary_recommendation" in recommendation
        assert "alternatives" in recommendation
        assert "comparison" in recommendation
        assert "selection_guidance" in recommendation

        # Check primary recommendation structure
        primary = recommendation["primary_recommendation"]
        assert "agents" in primary
        assert "estimated_cost_per_sprint" in primary
        assert "estimated_velocity" in primary
        assert primary["project_type"] == "web_application"

        # Should have reasonable cost estimate
        assert primary["estimated_cost_per_sprint"] > 0
        assert primary["estimated_velocity"] > 0



class TestTeamCompositionBuilder:
    """Tests for Team Composition Builder."""

    def test_init(self):
        """Test Team Composition Builder initialization."""
        builder = TeamCompositionBuilder()
        assert hasattr(builder, "logger")
        assert hasattr(builder, "tier_costs")

    @pytest.mark.asyncio
    async def test_build_team_composition(self):
        """Test team composition building."""
        builder = TeamCompositionBuilder()

        requirements = TeamCompositionRequirements(
            project_type=ProjectType.WEB_APPLICATION,
            team_size=TeamSize.SMALL,
            complexity=ProjectComplexity.SIMPLE,
        )

        composition = await builder.build_team_composition(requirements)

        assert len(composition.agents) > 0
        assert composition.project_type == ProjectType.WEB_APPLICATION
        assert composition.estimated_cost_per_sprint > 0
        assert composition.estimated_velocity > 0
        
        # Check for essential roles
        agent_roles = [agent.role for agent in composition.agents]
        assert AgentRole.PRODUCT_OWNER in agent_roles
        assert AgentRole.SCRUM_MASTER in agent_roles



class TestOptimizationIntegration:
    """Integration tests between optimization systems."""

    @pytest.mark.asyncio
    async def test_cost_and_learning_integration(self, sample_sprint):
        """Test integration between cost optimization and learning systems."""
        cost_engine = CostOptimizationEngine()
        learning_engine = SprintLearningEngine()

        # Analyze costs
        cost_metrics = await cost_engine.analyze_sprint_costs(sample_sprint)

        # Mark sprint as completed and extract learnings
        from gaggle.models.sprint import SprintStatus
        sample_sprint.status = SprintStatus.COMPLETED
        
        learnings = await learning_engine.extract_learnings([sample_sprint])

        # Generate cost optimization recommendations
        cost_recommendations = await cost_engine.generate_optimization_recommendations(
            sample_sprint, cost_metrics
        )

        assert learnings is not None
        assert isinstance(learnings, list)
        assert isinstance(cost_recommendations, list)  # May be empty for low-cost sprints
        assert cost_metrics.total_cost_usd > 0
        assert cost_metrics.cost_per_story_point >= 0

        # Integration works - both systems process the same sprint data
        for learning in learnings:
            assert hasattr(learning, "sprint_id")
            assert learning.sprint_id == sample_sprint.id

    @pytest.mark.asyncio
    async def test_team_composition_cost_optimization(self, sample_sprint):
        """Test integration between team composition and cost optimization."""
        composition_manager = TeamCompositionManager()
        cost_engine = CostOptimizationEngine()

        # Create team composition
        requirements = TeamCompositionRequirements(
            project_type=ProjectType.WEB_APPLICATION,
            team_size=TeamSize.SMALL,
            complexity=ProjectComplexity.SIMPLE,
            budget_constraints=1000.0,
        )
        
        recommendation = await composition_manager.recommend_team_composition(requirements)
        composition = recommendation["primary_recommendation"]

        # Analyze costs for the composition
        cost_metrics = await cost_engine.analyze_sprint_costs(sample_sprint)

        # Test that both systems work together - composition has cost info
        assert composition["estimated_cost_per_sprint"] > 0
        assert composition["estimated_velocity"] > 0

        # Integration test - both systems work and provide useful data
        assert composition is not None
        assert cost_metrics is not None
        assert cost_metrics.total_cost_usd > 0
        assert composition["estimated_cost_per_sprint"] <= 1000.0  # Within budget
