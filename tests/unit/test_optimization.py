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
    TeamCompositionBuilder,
    TeamCompositionManager,
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
            task_type="frontend_implementation",
            assigned_role=AgentRole.FRONTEND_DEVELOPER,
        ),
        Task(
            id="TASK-002",
            title="Create auth API",
            description="Implement authentication endpoints",
            status=TaskStatus.TODO,
            assigned_to="backend_dev",
            estimated_hours=6,
            priority="high",
            task_type="api_implementation",
            assigned_role=AgentRole.BACKEND_DEVELOPER,
        ),
        Task(
            id="TASK-003",
            title="Review auth code",
            description="Code review for authentication",
            status=TaskStatus.TODO,
            assigned_to="tech_lead",
            estimated_hours=2,
            priority="medium",
            task_type="code_review",
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
        acceptance_criteria=["Login form", "API endpoints"],
        priority="high",
        story_points=8,
        tasks=sample_tasks,
    )

    return Sprint(
        id="SPRINT-001",
        name="Auth Sprint",
        goal="Implement authentication",
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(weeks=2),
        user_stories=[user_story],
        team_velocity=20,
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

        assert AgentRole.FRONTEND_DEVELOPER in complexity
        assert AgentRole.BACKEND_DEVELOPER in complexity
        assert AgentRole.TECH_LEAD in complexity
        assert complexity[AgentRole.FRONTEND_DEVELOPER] > 0
        assert (
            complexity[AgentRole.BACKEND_DEVELOPER]
            > complexity[AgentRole.FRONTEND_DEVELOPER]
        )  # Higher priority/hours

    def test_recommend_tier_assignments_minimize_cost(self, sample_tasks):
        """Test tier assignment recommendations for cost minimization."""
        optimizer = ModelTierOptimizer()

        role_complexity = {
            AgentRole.FRONTEND_DEVELOPER: 1.0,  # Low complexity
            AgentRole.BACKEND_DEVELOPER: 2.0,  # Medium complexity
            AgentRole.TECH_LEAD: 4.0,  # High complexity
        }

        recommendations = optimizer.recommend_tier_assignments(
            role_complexity, OptimizationGoal.MINIMIZE_COST
        )

        assert recommendations[AgentRole.FRONTEND_DEVELOPER] == ModelTier.HAIKU
        assert recommendations[AgentRole.BACKEND_DEVELOPER] == ModelTier.SONNET
        assert recommendations[AgentRole.TECH_LEAD] == ModelTier.OPUS

    def test_calculate_cost_impact(self):
        """Test cost impact calculation."""
        optimizer = ModelTierOptimizer()

        current_assignments = {
            AgentRole.FRONTEND_DEVELOPER: ModelTier.SONNET,
            AgentRole.BACKEND_DEVELOPER: ModelTier.SONNET,
        }

        recommended_assignments = {
            AgentRole.FRONTEND_DEVELOPER: ModelTier.HAIKU,
            AgentRole.BACKEND_DEVELOPER: ModelTier.SONNET,
        }

        expected_tokens = {
            AgentRole.FRONTEND_DEVELOPER: 2000,
            AgentRole.BACKEND_DEVELOPER: 2000,
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
            t.id for t in sample_tasks if t.task_type == "frontend_implementation"
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
        assert savings["total_cacheable_operations"] == 3
        assert savings["expected_cache_hits"] == 3 * 0.4


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
    async def test_extract_sprint_learnings(self, sample_sprint):
        """Test sprint learning extraction."""
        engine = SprintLearningEngine()

        sprint_data = {
            "completed_tasks": 8,
            "planned_tasks": 10,
            "velocity_achieved": 18,
            "velocity_planned": 20,
            "quality_score": 8.5,
            "team_satisfaction": 4.2,
        }

        learnings = await engine.extract_sprint_learnings(sample_sprint, sprint_data)

        assert "performance_analysis" in learnings
        assert "bottlenecks_identified" in learnings
        assert "success_factors" in learnings
        assert "improvement_opportunities" in learnings
        assert learnings["performance_analysis"]["velocity_achievement_rate"] == 0.9


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

        historical_data = [
            {
                "sprint_id": "SPRINT-001",
                "velocity_achievement": 0.9,
                "quality_score": 8.5,
                "cost_per_story_point": 25.0,
                "team_satisfaction": 4.2,
                "bottlenecks": ["testing", "code_review"],
            }
        ]

        strategies = await generator.generate_improvement_strategies(historical_data)

        assert "velocity_optimization" in strategies
        assert "quality_improvement" in strategies
        assert "cost_reduction" in strategies
        assert "team_satisfaction" in strategies

        for _category, strategy_list in strategies.items():
            assert isinstance(strategy_list, list)
            for strategy in strategy_list:
                assert "name" in strategy
                assert "description" in strategy
                assert "expected_impact" in strategy


class TestMultiSprintOptimizer:
    """Tests for Multi-Sprint Optimizer."""

    def test_init(self):
        """Test Multi-Sprint Optimizer initialization."""
        optimizer = MultiSprintOptimizer()
        assert hasattr(optimizer, "learning_engine")
        assert hasattr(optimizer, "strategy_generator")

    @pytest.mark.asyncio
    async def test_analyze_sprint_performance(self):
        """Test sprint performance analysis."""
        optimizer = MultiSprintOptimizer()

        sprint_data = [
            {
                "sprint_id": "SPRINT-001",
                "planned_velocity": 20,
                "actual_velocity": 18,
                "quality_score": 8.5,
                "cost_usd": 500.0,
                "team_satisfaction": 4.2,
            },
            {
                "sprint_id": "SPRINT-002",
                "planned_velocity": 20,
                "actual_velocity": 22,
                "quality_score": 9.0,
                "cost_usd": 450.0,
                "team_satisfaction": 4.5,
            },
        ]

        analysis = await optimizer.analyze_sprint_performance(sprint_data)

        assert "velocity_trend" in analysis
        assert "quality_trend" in analysis
        assert "cost_trend" in analysis
        assert "satisfaction_trend" in analysis
        assert "overall_performance_score" in analysis

        # Check trend calculations
        assert analysis["velocity_trend"]["direction"] == "improving"  # 18 -> 22
        assert analysis["quality_trend"]["direction"] == "improving"  # 8.5 -> 9.0
        assert analysis["cost_trend"]["direction"] == "improving"  # 500 -> 450


class TestTeamCompositionManager:
    """Tests for Team Composition Manager."""

    def test_init(self):
        """Test Team Composition Manager initialization."""
        manager = TeamCompositionManager()
        assert hasattr(manager, "builder")
        assert hasattr(manager, "compositions")

    def test_create_composition_for_web_app(self):
        """Test team composition creation for web applications."""
        manager = TeamCompositionManager()

        constraints = {
            "team_size": 5,
            "budget_per_sprint": 2000,
            "timeline_weeks": 8,
            "quality_requirements": "high",
        }

        composition = manager.create_composition_for_project(
            "web_application", constraints
        )

        assert "team_members" in composition
        assert "cost_breakdown" in composition
        assert "recommended_sprint_length" in composition
        assert len(composition["team_members"]) <= constraints["team_size"]

        # Should include essential web app roles
        roles = [member["role"] for member in composition["team_members"]]
        assert "frontend_developer" in roles
        assert "backend_developer" in roles

    def test_optimize_composition_for_constraints(self):
        """Test team composition optimization."""
        manager = TeamCompositionManager()

        current_composition = {
            "team_members": [
                {"role": "product_owner", "tier": "haiku", "allocation": 0.5},
                {"role": "frontend_developer", "tier": "sonnet", "allocation": 1.0},
                {"role": "backend_developer", "tier": "sonnet", "allocation": 1.0},
                {"role": "tech_lead", "tier": "opus", "allocation": 0.3},
            ]
        }

        optimization_goals = {
            "minimize_cost": True,
            "maintain_quality": True,
            "max_budget": 1500,
        }

        optimized = manager.optimize_composition_for_constraints(
            current_composition, optimization_goals
        )

        assert "optimized_team" in optimized
        assert "cost_savings" in optimized
        assert "optimization_changes" in optimized
        assert (
            optimized["estimated_cost_per_sprint"] <= optimization_goals["max_budget"]
        )


class TestTeamCompositionBuilder:
    """Tests for Team Composition Builder."""

    def test_init(self):
        """Test Team Composition Builder initialization."""
        builder = TeamCompositionBuilder()
        assert hasattr(builder, "role_requirements")
        assert hasattr(builder, "cost_calculator")

    def test_build_base_team(self):
        """Test base team building."""
        builder = TeamCompositionBuilder()

        base_team = builder.build_base_team()

        assert len(base_team) > 0
        required_roles = ["product_owner", "scrum_master"]
        team_roles = [member["role"] for member in base_team]

        for required_role in required_roles:
            assert required_role in team_roles

    def test_add_development_roles(self):
        """Test development role addition."""
        builder = TeamCompositionBuilder()

        team = []
        project_type = "web_application"
        constraints = {"team_size": 6, "frontend_heavy": True}

        team_with_dev_roles = builder.add_development_roles(
            team, project_type, constraints
        )

        assert len(team_with_dev_roles) > len(team)
        roles = [member["role"] for member in team_with_dev_roles]
        assert "frontend_developer" in roles


class TestOptimizationIntegration:
    """Integration tests between optimization systems."""

    @pytest.mark.asyncio
    async def test_cost_and_learning_integration(self, sample_sprint):
        """Test integration between cost optimization and learning systems."""
        cost_engine = CostOptimizationEngine()
        learning_engine = SprintLearningEngine()

        # Analyze costs
        cost_metrics = await cost_engine.analyze_sprint_costs(sample_sprint)

        # Extract learnings including cost data
        sprint_data = {
            "cost_per_story_point": cost_metrics.cost_per_story_point,
            "total_cost_usd": cost_metrics.total_cost_usd,
            "velocity_achieved": 18,
            "velocity_planned": 20,
        }

        learnings = await learning_engine.extract_sprint_learnings(
            sample_sprint, sprint_data
        )

        # Generate cost optimization recommendations
        cost_recommendations = await cost_engine.generate_optimization_recommendations(
            sample_sprint, cost_metrics
        )

        assert learnings is not None
        assert len(cost_recommendations) > 0
        assert "performance_analysis" in learnings

        # Cost learnings should influence future optimization
        assert (
            learnings["performance_analysis"]["cost_per_story_point"]
            == cost_metrics.cost_per_story_point
        )

    @pytest.mark.asyncio
    async def test_team_composition_cost_optimization(self, sample_sprint):
        """Test integration between team composition and cost optimization."""
        composition_manager = TeamCompositionManager()
        cost_engine = CostOptimizationEngine()

        # Create team composition
        constraints = {"team_size": 4, "budget_per_sprint": 1000}
        composition = composition_manager.create_composition_for_project(
            "web_application", constraints
        )

        # Analyze costs for the composition
        cost_metrics = await cost_engine.analyze_sprint_costs(sample_sprint)

        # Optimize composition based on cost analysis
        optimization_goals = {
            "minimize_cost": True,
            "max_budget": constraints["budget_per_sprint"],
        }

        optimized_composition = (
            composition_manager.optimize_composition_for_constraints(
                composition, optimization_goals
            )
        )

        assert composition is not None
        assert cost_metrics is not None
        assert optimized_composition is not None
        assert (
            optimized_composition["estimated_cost_per_sprint"]
            <= constraints["budget_per_sprint"]
        )
