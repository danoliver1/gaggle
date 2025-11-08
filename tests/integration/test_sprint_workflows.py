"""Integration tests for complete sprint workflows."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from gaggle.agents.architecture.tech_lead import TechLead
from gaggle.agents.coordination.product_owner import ProductOwner
from gaggle.agents.coordination.scrum_master import ScrumMaster
from gaggle.agents.implementation.backend_dev import BackendDeveloper
from gaggle.agents.implementation.frontend_dev import FrontendDeveloper
from gaggle.agents.qa.qa_engineer import QAEngineer
from gaggle.dashboards.sprint_metrics import SprintMetricsCollector
from gaggle.integrations.github_api import GitHubAPIClient
from gaggle.models.sprint import Sprint
from gaggle.models.story import UserStory
from gaggle.models.task import TaskModel as Task
from gaggle.models.task import TaskStatus
from gaggle.workflows.sprint_execution import SprintExecutionWorkflow
from gaggle.workflows.sprint_planning import SprintPlanningWorkflow


@pytest.fixture
def mock_agents():
    """Create mock agents for testing."""
    agents = {}

    for agent_class in [
        ProductOwner,
        ScrumMaster,
        TechLead,
        FrontendDeveloper,
        BackendDeveloper,
        QAEngineer,
    ]:
        agent = Mock()
        agent.agent = Mock()
        agent.agent.aexecute = AsyncMock(
            return_value={
                "result": f"Mock response from {agent_class.__name__}",
                "token_usage": {"input_tokens": 100, "output_tokens": 200},
            }
        )
        agents[agent_class.__name__] = agent

    return agents


@pytest.fixture
def sample_project_requirements():
    """Sample project requirements for testing."""
    return {
        "project_name": "E-commerce Platform",
        "features": [
            "User registration and authentication",
            "Product catalog with search",
            "Shopping cart and checkout",
            "Order management dashboard",
        ],
        "tech_stack": {
            "frontend": "React/TypeScript",
            "backend": "Node.js/Express",
            "database": "PostgreSQL",
            "deployment": "AWS",
        },
        "constraints": {
            "timeline_weeks": 8,
            "team_size": 6,
            "budget": 15000,
            "quality_level": "high",
        },
    }


@pytest.fixture
def sample_backlog():
    """Sample product backlog for testing."""
    return [
        UserStory(
            id="US-001",
            title="User Registration",
            description="As a user, I want to create an account",
            acceptance_criteria=[
                "User can enter email and password",
                "System validates input",
                "Confirmation email is sent",
            ],
            priority="high",
            story_points=5,
        ),
        UserStory(
            id="US-002",
            title="User Login",
            description="As a user, I want to log into my account",
            acceptance_criteria=[
                "User can enter credentials",
                "System authenticates user",
                "User is redirected to dashboard",
            ],
            priority="high",
            story_points=3,
        ),
        UserStory(
            id="US-003",
            title="Product Search",
            description="As a user, I want to search for products",
            acceptance_criteria=[
                "Search box is available",
                "Results are filtered and sorted",
                "Pagination works correctly",
            ],
            priority="medium",
            story_points=8,
        ),
    ]


class TestSprintPlanningWorkflow:
    """Tests for complete sprint planning workflow."""

    @pytest.mark.asyncio
    async def test_complete_sprint_planning_flow(
        self, mock_agents, sample_project_requirements
    ):
        """Test complete sprint planning from requirements to ready sprint."""

        # Mock Strands adapter
        with patch(
            "src.gaggle.workflows.sprint_planning.strands_adapter"
        ) as mock_strands:
            mock_strands.create_agent.return_value = mock_agents["ProductOwner"]

            workflow = SprintPlanningWorkflow()

            # Mock the internal methods to avoid complex agent setup
            with patch.object(workflow, "_create_user_stories") as mock_create_stories:
                with patch.object(
                    workflow, "_analyze_architecture"
                ) as mock_analyze_arch:
                    with patch.object(workflow, "_plan_sprint") as mock_plan_sprint:

                        # Setup mock responses
                        mock_create_stories.return_value = {
                            "user_stories": [
                                {
                                    "id": "US-001",
                                    "title": "User Registration",
                                    "story_points": 5,
                                    "priority": "high",
                                }
                            ],
                            "total_story_points": 16,
                        }

                        mock_analyze_arch.return_value = {
                            "architecture_requirements": {
                                "components": ["AuthService", "UserAPI"],
                                "patterns": ["MVC", "Repository"],
                            },
                            "task_breakdown": [
                                {
                                    "id": "TASK-001",
                                    "title": "Implement user registration API",
                                    "estimated_hours": 6,
                                    "assigned_role": "backend_developer",
                                }
                            ],
                        }

                        mock_plan_sprint.return_value = {
                            "sprint": {
                                "id": "SPRINT-001",
                                "name": "Authentication Sprint",
                                "selected_stories": ["US-001"],
                                "capacity_analysis": {
                                    "planned_velocity": 16,
                                    "team_capacity": 20,
                                },
                            }
                        }

                        result = await workflow.execute_complete_planning(
                            sample_project_requirements
                        )

                        assert "user_stories" in result
                        assert "architecture_analysis" in result
                        assert "sprint_plan" in result
                        assert "planning_metrics" in result

                        # Verify workflow called all planning phases
                        mock_create_stories.assert_called_once()
                        mock_analyze_arch.assert_called_once()
                        mock_plan_sprint.assert_called_once()


class TestSprintExecutionWorkflow:
    """Tests for complete sprint execution workflow."""

    @pytest.mark.asyncio
    async def test_complete_sprint_execution_flow(self, mock_agents, sample_backlog):
        """Test complete sprint execution from planning to review."""

        # Create sample sprint
        sprint = Sprint(
            id="SPRINT-001",
            name="Authentication Sprint",
            goal="Implement user authentication",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(weeks=2),
            user_stories=sample_backlog[:2],  # First 2 stories
            team_velocity=20,
        )

        # Add tasks to user stories
        for story in sprint.user_stories:
            story.tasks = [
                Task(
                    id=f"TASK-{story.id}-001",
                    title=f"Implement {story.title} frontend",
                    description=f"Frontend for {story.title}",
                    status=TaskStatus.TODO,
                    assigned_to="frontend_dev",
                    estimated_hours=4,
                    user_story_id=story.id,
                ),
                Task(
                    id=f"TASK-{story.id}-002",
                    title=f"Implement {story.title} backend",
                    description=f"Backend for {story.title}",
                    status=TaskStatus.TODO,
                    assigned_to="backend_dev",
                    estimated_hours=6,
                    user_story_id=story.id,
                ),
            ]

        workflow = SprintExecutionWorkflow()

        # Mock GitHub integration
        with patch(
            "src.gaggle.workflows.sprint_execution.github_client"
        ) as mock_github:
            mock_github.sync_sprint_with_github = AsyncMock(
                return_value={
                    "milestone": {"number": 1},
                    "project_board": {"id": "PB_001"},
                }
            )

            # Mock Strands adapter
            with patch(
                "src.gaggle.workflows.sprint_execution.strands_adapter"
            ) as mock_strands:
                mock_strands.create_agent.return_value = mock_agents[
                    "FrontendDeveloper"
                ]
                mock_strands.execute_parallel_tasks = AsyncMock(
                    return_value={
                        "successful": [
                            {
                                "agent": "frontend_dev",
                                "result": {"result": "Frontend implemented"},
                            },
                            {
                                "agent": "backend_dev",
                                "result": {"result": "Backend implemented"},
                            },
                        ],
                        "failed": [],
                    }
                )

                result = await workflow.execute_sprint(sprint)

                assert "sprint_id" in result
                assert "execution_summary" in result
                assert "daily_standups" in result
                assert "development_cycles" in result
                assert "final_review" in result

                # Verify GitHub integration was called
                mock_github.sync_sprint_with_github.assert_called_once_with(sprint)


class TestEndToEndSprintWorkflow:
    """End-to-end tests for complete sprint workflows."""

    @pytest.mark.asyncio
    async def test_full_sprint_cycle_planning_to_review(
        self, mock_agents, sample_project_requirements, sample_backlog
    ):
        """Test full sprint cycle from initial planning to final review."""

        # Phase 1: Sprint Planning
        planning_workflow = SprintPlanningWorkflow()

        with patch(
            "src.gaggle.workflows.sprint_planning.strands_adapter"
        ) as mock_strands:
            mock_strands.create_agent.return_value = mock_agents["ProductOwner"]

            with patch.object(planning_workflow, "_create_user_stories") as mock_create:
                with patch.object(
                    planning_workflow, "_analyze_architecture"
                ) as mock_analyze:
                    with patch.object(planning_workflow, "_plan_sprint") as mock_plan:

                        mock_create.return_value = {
                            "user_stories": sample_backlog,
                            "total_story_points": 16,
                        }
                        mock_analyze.return_value = {
                            "architecture_requirements": {},
                            "task_breakdown": [],
                        }
                        mock_plan.return_value = {
                            "sprint": {
                                "id": "SPRINT-001",
                                "name": "Auth Sprint",
                                "selected_stories": sample_backlog[:2],
                            }
                        }

                        planning_result = (
                            await planning_workflow.execute_complete_planning(
                                sample_project_requirements
                            )
                        )

        # Phase 2: Sprint Execution
        sprint = Sprint(
            id="SPRINT-001",
            name="Auth Sprint",
            goal="Implement authentication",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(weeks=2),
            user_stories=sample_backlog[:2],
            team_velocity=20,
        )

        execution_workflow = SprintExecutionWorkflow()

        with patch(
            "src.gaggle.workflows.sprint_execution.github_client"
        ) as mock_github, patch(
            "src.gaggle.workflows.sprint_execution.strands_adapter"
        ) as mock_strands:
            mock_github.sync_sprint_with_github = AsyncMock(
                return_value={"milestone": {"number": 1}}
            )
            mock_strands.create_agent.return_value = mock_agents[
                "FrontendDeveloper"
            ]
            mock_strands.execute_parallel_tasks = AsyncMock(
                return_value={"successful": [], "failed": []}
            )

            execution_result = await execution_workflow.execute_sprint(sprint)

        # Verify end-to-end flow
        assert planning_result is not None
        assert execution_result is not None
        assert "user_stories" in planning_result
        assert "sprint_id" in execution_result
        assert execution_result["sprint_id"] == "SPRINT-001"

    @pytest.mark.asyncio
    async def test_multi_sprint_execution_with_learning(
        self, mock_agents, sample_backlog
    ):
        """Test multiple sprint execution with learning and optimization."""

        sprints = [
            Sprint(
                id=f"SPRINT-00{i}",
                name=f"Sprint {i}",
                goal=f"Sprint {i} goals",
                start_date=datetime.now() + timedelta(weeks=2 * i),
                end_date=datetime.now() + timedelta(weeks=2 * i + 2),
                user_stories=(
                    sample_backlog[i : i + 1] if i < len(sample_backlog) else []
                ),
                team_velocity=20,
            )
            for i in range(1, 4)  # 3 sprints
        ]

        execution_workflow = SprintExecutionWorkflow()
        sprint_results = []

        # Execute multiple sprints
        for sprint in sprints:
            with patch(
                "src.gaggle.workflows.sprint_execution.github_client"
            ) as mock_github, patch(
                "src.gaggle.workflows.sprint_execution.strands_adapter"
            ) as mock_strands:
                mock_github.sync_sprint_with_github = AsyncMock(
                    return_value={"milestone": {"number": 1}}
                )
                mock_strands.create_agent.return_value = mock_agents[
                    "FrontendDeveloper"
                ]
                mock_strands.execute_parallel_tasks = AsyncMock(
                    return_value={
                        "successful": [
                            {"agent": "test", "result": {"result": "success"}}
                        ],
                        "failed": [],
                    }
                )

                result = await execution_workflow.execute_sprint(sprint)
                sprint_results.append(result)

        # Test learning from multiple sprints
        from gaggle.learning.multi_sprint_optimizer import MultiSprintOptimizer

        optimizer = MultiSprintOptimizer()

        # Mock sprint data for learning
        sprint_data = [
            {
                "sprint_id": f"SPRINT-00{i}",
                "planned_velocity": 20,
                "actual_velocity": 18 + i,  # Improving over time
                "quality_score": 8.0 + i * 0.5,
                "cost_usd": 1000 - i * 50,  # Decreasing cost
                "team_satisfaction": 4.0 + i * 0.2,
            }
            for i in range(1, 4)
        ]

        performance_analysis = await optimizer.analyze_sprint_performance(sprint_data)

        assert len(sprint_results) == 3
        assert "velocity_trend" in performance_analysis
        assert "quality_trend" in performance_analysis
        assert performance_analysis["velocity_trend"]["direction"] == "improving"
        assert performance_analysis["quality_trend"]["direction"] == "improving"


class TestSprintMetricsIntegration:
    """Tests for sprint metrics collection during workflows."""

    @pytest.mark.asyncio
    async def test_metrics_collection_during_sprint_execution(self, mock_agents):
        """Test that metrics are properly collected during sprint execution."""

        sprint = Sprint(
            id="SPRINT-001",
            name="Metrics Test Sprint",
            goal="Test metrics collection",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(weeks=2),
            user_stories=[
                UserStory(
                    id="US-001",
                    title="Test Story",
                    description="Test story for metrics",
                    acceptance_criteria=["AC1"],
                    priority="high",
                    story_points=5,
                    tasks=[
                        Task(
                            id="TASK-001",
                            title="Test Task",
                            description="Test task",
                            status=TaskStatus.TODO,
                            assigned_to="dev",
                            estimated_hours=4,
                            user_story_id="US-001",
                        )
                    ],
                )
            ],
            team_velocity=20,
        )

        metrics_collector = SprintMetricsCollector()

        # Mock metrics collection
        with patch.object(metrics_collector, "start_sprint_tracking") as mock_start:
            with patch.object(
                metrics_collector, "record_task_completion"
            ) as mock_record:
                with patch.object(
                    metrics_collector, "calculate_sprint_metrics"
                ) as mock_calculate:

                    mock_calculate.return_value = {
                        "velocity": {"planned": 20, "actual": 18},
                        "quality": {"score": 8.5, "defects": 2},
                        "cost": {"total_usd": 950, "per_story_point": 47.5},
                        "team": {"satisfaction": 4.2, "efficiency": 85},
                    }

                    # Start tracking
                    await metrics_collector.start_sprint_tracking(sprint)

                    # Simulate task completion
                    task = sprint.user_stories[0].tasks[0]
                    task.status = TaskStatus.DONE
                    await metrics_collector.record_task_completion(task, sprint.id)

                    # Calculate final metrics
                    final_metrics = await metrics_collector.calculate_sprint_metrics(
                        sprint.id
                    )

                    assert mock_start.called
                    assert mock_record.called
                    assert "velocity" in final_metrics
                    assert "quality" in final_metrics
                    assert "cost" in final_metrics


class TestGitHubIntegrationWorkflow:
    """Tests for GitHub integration in sprint workflows."""

    @pytest.mark.asyncio
    async def test_github_milestone_and_project_board_creation(self, sample_backlog):
        """Test GitHub milestone and project board creation during sprint setup."""

        sprint = Sprint(
            id="SPRINT-001",
            name="GitHub Integration Sprint",
            goal="Test GitHub integration",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(weeks=2),
            user_stories=sample_backlog[:2],
            team_velocity=20,
        )

        # Mock GitHub API client
        with patch("src.gaggle.integrations.github_api.Github") as mock_github:
            mock_repo = Mock()
            mock_milestone = Mock(
                number=1,
                title="Sprint 001",
                html_url="https://github.com/test/test/milestones/1",
            )
            mock_repo.create_milestone.return_value = mock_milestone

            mock_issue = Mock(
                number=1, html_url="https://github.com/test/test/issues/1"
            )
            mock_repo.create_issue.return_value = mock_issue

            mock_github.return_value.get_repo.return_value = mock_repo

            github_client = GitHubAPIClient("test-token", "test-org", "test-repo")

            # Test sprint sync
            sync_result = await github_client.sync_sprint_with_github(sprint)

            assert "milestone" in sync_result
            assert "user_story_issues" in sync_result
            assert sync_result["milestone"]["number"] == 1
            assert len(sync_result["user_story_issues"]) == 2

            # Verify milestone creation
            mock_repo.create_milestone.assert_called_once()

            # Verify issue creation for each user story
            assert mock_repo.create_issue.call_count == 2

    @pytest.mark.asyncio
    async def test_github_webhook_processing_during_sprint(self):
        """Test GitHub webhook processing during active sprint."""

        from gaggle.integrations.github_api import GitHubWebhookHandler

        webhook_handler = GitHubWebhookHandler("test-secret")

        # Register handlers for sprint events
        async def handle_pr_opened(payload):
            return {
                "processed": True,
                "action": "pr_opened",
                "pr_number": payload["pull_request"]["number"],
                "sprint_updated": True,
            }

        async def handle_issue_closed(payload):
            return {
                "processed": True,
                "action": "issue_closed",
                "issue_number": payload["issue"]["number"],
                "task_completed": True,
            }

        webhook_handler.register_event_handler("pull_request", handle_pr_opened)
        webhook_handler.register_event_handler("issues", handle_issue_closed)

        # Test PR opened webhook
        pr_payload = {
            "action": "opened",
            "pull_request": {"number": 1, "title": "Implement user login"},
        }

        pr_result = await webhook_handler.process_webhook("pull_request", pr_payload)

        assert pr_result["processed"] is True
        assert pr_result["action"] == "pr_opened"
        assert pr_result["pr_number"] == 1
        assert pr_result["sprint_updated"] is True

        # Test issue closed webhook
        issue_payload = {
            "action": "closed",
            "issue": {"number": 2, "title": "US-001: User Registration"},
        }

        issue_result = await webhook_handler.process_webhook("issues", issue_payload)

        assert issue_result["processed"] is True
        assert issue_result["action"] == "issue_closed"
        assert issue_result["task_completed"] is True


class TestErrorHandlingAndResilience:
    """Tests for error handling and resilience in sprint workflows."""

    @pytest.mark.asyncio
    async def test_sprint_execution_with_agent_failures(self, sample_backlog):
        """Test sprint execution resilience when some agents fail."""

        sprint = Sprint(
            id="SPRINT-001",
            name="Resilience Test Sprint",
            goal="Test error handling",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(weeks=2),
            user_stories=sample_backlog[:1],
            team_velocity=20,
        )

        # Add tasks
        sprint.user_stories[0].tasks = [
            Task(
                id="TASK-001",
                title="Frontend implementation",
                description="Frontend task",
                status=TaskStatus.TODO,
                assigned_to="frontend_dev",
                estimated_hours=4,
                user_story_id="US-001",
            ),
            Task(
                id="TASK-002",
                title="Backend implementation",
                description="Backend task",
                status=TaskStatus.TODO,
                assigned_to="backend_dev",
                estimated_hours=6,
                user_story_id="US-001",
            ),
        ]

        workflow = SprintExecutionWorkflow()

        with patch(
            "src.gaggle.workflows.sprint_execution.strands_adapter"
        ) as mock_strands:
            # Simulate one successful agent and one failed agent
            mock_strands.execute_parallel_tasks = AsyncMock(
                return_value={
                    "successful": [
                        {
                            "agent": "frontend_dev",
                            "result": {"result": "Frontend completed"},
                            "index": 0,
                        }
                    ],
                    "failed": [
                        {
                            "agent": "backend_dev",
                            "error": "Connection timeout",
                            "index": 1,
                        }
                    ],
                    "summary": {"total_tasks": 2, "success_rate": 50.0},
                }
            )

            with patch(
                "src.gaggle.workflows.sprint_execution.github_client"
            ) as mock_github:
                mock_github.sync_sprint_with_github = AsyncMock(
                    return_value={"milestone": {"number": 1}}
                )

                result = await workflow.execute_sprint(sprint)

                assert "execution_summary" in result
                assert "failed_tasks" in result["execution_summary"]
                assert len(result["execution_summary"]["failed_tasks"]) == 1
                assert result["execution_summary"]["success_rate"] == 50.0

    @pytest.mark.asyncio
    async def test_sprint_execution_with_github_api_failures(self, sample_backlog):
        """Test sprint execution when GitHub API calls fail."""

        sprint = Sprint(
            id="SPRINT-001",
            name="GitHub Failure Test",
            goal="Test GitHub API failure handling",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(weeks=2),
            user_stories=sample_backlog[:1],
            team_velocity=20,
        )

        workflow = SprintExecutionWorkflow()

        with patch(
            "src.gaggle.workflows.sprint_execution.github_client"
        ) as mock_github:
            # Simulate GitHub API failure
            mock_github.sync_sprint_with_github = AsyncMock(
                side_effect=Exception("GitHub API rate limit exceeded")
            )

            with patch(
                "src.gaggle.workflows.sprint_execution.strands_adapter"
            ) as mock_strands:
                mock_strands.execute_parallel_tasks = AsyncMock(
                    return_value={
                        "successful": [
                            {"agent": "test", "result": {"result": "success"}}
                        ],
                        "failed": [],
                    }
                )

                result = await workflow.execute_sprint(sprint)

                # Should continue execution despite GitHub failure
                assert "execution_summary" in result
                assert "github_integration_failed" in result
                assert result["github_integration_failed"] is True
