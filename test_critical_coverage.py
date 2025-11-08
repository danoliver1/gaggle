#!/usr/bin/env python3
"""
Critical coverage tests - focused tests to rapidly improve coverage to acceptable levels.
"""


import pytest

from gaggle.config.models import AgentRole, ModelTier, calculate_cost, get_model_config

# Import configurations
from gaggle.config.settings import GaggleSettings
from gaggle.models.sprint import SprintModel, SprintStatus
from gaggle.models.story import (
    StoryStatus,
    UserStory,
)

# Import core models
from gaggle.models.task import Task, TaskStatus, TaskType
from gaggle.models.team import TeamConfiguration, TeamMember
from gaggle.tools.code_tools import CodeAnalysisTool

# Import tools that need testing
from gaggle.tools.project_tools import BacklogTool
from gaggle.tools.review_tools import CodeReviewTool

# Import utilities
from gaggle.utils.cost_calculator import CostCalculator
from gaggle.utils.logging import get_logger
from gaggle.utils.token_counter import TokenCounter


class TestCoreModelMethods:
    """Test core model methods to improve coverage."""

    def test_task_lifecycle_methods(self):
        """Test task lifecycle methods."""
        task = Task(
            id="test_task",
            title="Test Task",
            description="Test task description",
            task_type=TaskType.BACKEND
        )

        # Test starting work
        task.start_work()
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.started_at is not None

        # Test marking for review
        task.mark_for_review()
        assert task.status == TaskStatus.IN_REVIEW
        assert task.progress_percentage == 100.0

        # Test completion
        task.complete_task("test_user")
        assert task.status == TaskStatus.DONE
        assert task.completed_at is not None
        assert task.actual_hours is not None

        # Test blocking/unblocking
        task.block_task("test blocker")
        assert task.status == TaskStatus.BLOCKED
        assert task.blocker_reason == "test blocker"

        task.unblock_task()
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.blocker_reason is None

    def test_task_dependencies(self):
        """Test task dependency management."""
        task = Task(
            id="test_task",
            title="Test Task",
            description="Test task description",
            task_type=TaskType.BACKEND
        )

        # Add dependency
        task.add_dependency("dep_task_1", "blocks", "Test dependency")
        assert len(task.dependencies) == 1

        # Remove dependency
        task.remove_dependency("dep_task_1")
        assert len(task.dependencies) == 0

        # Test review notes
        task.add_review_note("Test note")
        assert len(task.review_notes) == 1

        # Test code files
        task.add_code_file("/path/to/file.py")
        assert len(task.code_files) == 1

        # Test progress updates
        task.update_progress(50.0, "Half done")
        assert task.progress_percentage == 50.0

        # Test token tracking
        task.track_token_usage(100, 50)
        assert task.actual_input_tokens == 100
        assert task.actual_output_tokens == 50

    def test_task_metrics_and_status(self):
        """Test task metrics and status checking methods."""
        task = Task(
            id="test_task",
            title="Test Task",
            description="Test task description",
            task_type=TaskType.BACKEND,
            estimated_hours=4.0
        )

        # Test readiness check
        assert task.is_ready_to_start()

        # Test parallelization check
        assert task.can_be_parallelized()

        # Test time metrics
        task.start_work()
        task.complete_task()
        metrics = task.get_time_metrics()
        assert "cycle_time_hours" in metrics
        assert "estimated_hours" in metrics

        # Test cost estimate
        task.assigned_role = AgentRole.BACKEND_DEV
        task.estimated_input_tokens = 1000
        task.estimated_output_tokens = 500
        cost_info = task.get_cost_estimate()
        assert "estimated_cost" in cost_info
        assert "actual_cost" in cost_info

        # Test GitHub issue conversion
        issue_data = task.to_github_issue()
        assert "title" in issue_data
        assert "body" in issue_data
        assert "labels" in issue_data

    def test_user_story_methods(self):
        """Test UserStory methods."""
        story = UserStory(
            id="story_1",
            title="Test Story",
            description="As a user, I want to test so that testing works"
        )

        # Test adding acceptance criteria
        criteria = story.add_acceptance_criteria("User can do something")
        assert len(story.acceptance_criteria) == 1
        assert criteria.description == "User can do something"

        # Test status transitions
        story.move_to_status(StoryStatus.READY, "test_user")
        assert story.status == StoryStatus.READY

        # Test assignment
        story.assign_to("test_assignee")
        assert story.assigned_to == "test_assignee"

        # Test dependencies
        story.add_dependency("dep_story")
        assert "dep_story" in story.dependencies

        story.remove_dependency("dep_story")
        assert "dep_story" not in story.dependencies

        # Test completion checking
        story.acceptance_criteria[0].mark_satisfied("test_user")
        completion = story.get_completion_percentage()
        assert completion == 100.0

        # Test definition of done
        dod = story.get_definition_of_done_checklist()
        assert "has_acceptance_criteria" in dod
        assert "all_criteria_satisfied" in dod

        # Test GitHub conversion
        issue_data = story.to_github_issue()
        assert "title" in issue_data
        assert "body" in issue_data

    def test_sprint_workflow(self):
        """Test sprint workflow methods."""
        sprint = SprintModel(
            id="test_sprint",
            goal="Test sprint goal that is longer than minimum"
        )

        # Test adding stories
        story = UserStory(
            id="story_1",
            title="Test Story",
            description="Test story description"
        )
        sprint.add_story(story)
        assert len(sprint.user_stories) == 1

        # Test sprint lifecycle
        sprint.start_sprint()
        assert sprint.status == SprintStatus.ACTIVE

        # Test adding notes
        sprint.add_note("Test note")
        assert len(sprint.notes) == 1

        # Test completion
        sprint.complete_sprint()
        assert sprint.status == SprintStatus.COMPLETED

        # Test metrics
        metrics = sprint.get_performance_summary()
        assert "velocity" in metrics
        assert "completion_percentage" in metrics

    def test_team_management(self):
        """Test team management methods."""
        team = TeamConfiguration(
            id="test_team",
            name="Test Team"
        )

        member = TeamMember(
            id="member_1",
            name="Test Member",
            role=AgentRole.BACKEND_DEV,
            model_tier=ModelTier.SONNET
        )

        # Test adding members
        team.add_member(member)
        assert len(team.members) == 1

        # Test getting members
        found_member = team.get_member_by_id("member_1")
        assert found_member is not None
        assert found_member.name == "Test Member"

        # Test filtering by role
        backend_devs = team.get_members_by_role(AgentRole.BACKEND_DEV)
        assert len(backend_devs) == 1

        # Test capacity
        capacity = team.get_team_capacity()
        assert AgentRole.BACKEND_DEV in capacity

        # Test workload
        workload = team.get_team_workload()
        assert "total_members" in workload
        assert "utilization_rate" in workload

        # Test performance summary
        summary = team.get_team_performance_summary()
        assert "team_id" in summary
        assert "performance_by_role" in summary


class TestToolFunctionality:
    """Test tool functionality to improve coverage."""

    def test_backlog_tool(self):
        """Test BacklogTool methods."""
        tool = BacklogTool()

        # Test story creation
        story_data = {
            "title": "Test Story",
            "description": "Test description",
            "priority": "high"
        }
        result = tool.create_user_story(story_data)
        assert "story_id" in result
        assert "created_story" in result

    def test_code_analysis_tool(self):
        """Test CodeAnalysisTool methods."""
        tool = CodeAnalysisTool()

        # Test analysis (mock mode)
        code = "def test_function(): return True"
        result = tool.analyze_code_complexity(code, "test.py")
        assert "complexity_score" in result
        assert "recommendations" in result

    def test_code_review_tool(self):
        """Test CodeReviewTool methods."""
        tool = CodeReviewTool()

        # Test review creation
        review_data = {
            "code": "def test(): pass",
            "file_path": "test.py",
            "author": "test_author"
        }
        result = tool.create_review_request(review_data)
        assert "review_id" in result
        assert "status" in result


class TestUtilities:
    """Test utility classes."""

    def test_cost_calculator(self):
        """Test CostCalculator functionality."""
        calculator = CostCalculator()

        # Test cost calculation
        cost = calculator.calculate_cost(1000, 500, AgentRole.BACKEND_DEV)
        assert cost > 0

        # Test batch cost calculation
        tasks = [
            {"input_tokens": 1000, "output_tokens": 500, "role": AgentRole.BACKEND_DEV},
            {"input_tokens": 800, "output_tokens": 400, "role": AgentRole.FRONTEND_DEV}
        ]
        total_cost = calculator.calculate_batch_cost(tasks)
        assert total_cost > 0

    def test_token_counter(self):
        """Test TokenCounter functionality."""
        counter = TokenCounter()

        # Test adding usage
        counter.add_usage(1000, 500, AgentRole.BACKEND_DEV)

        # Test getting totals
        totals = counter.get_total_usage()
        assert totals["total_input_tokens"] == 1000
        assert totals["total_output_tokens"] == 500

        # Test reset
        counter.reset()
        totals_after_reset = counter.get_total_usage()
        assert totals_after_reset["total_input_tokens"] == 0

    def test_logging(self):
        """Test logging utility."""
        logger = get_logger("test_logger")
        assert logger.name == "test_logger"


class TestConfigurations:
    """Test configuration functionality."""

    def test_model_configs(self):
        """Test model configuration retrieval."""
        # Test getting model config for each role
        for role in AgentRole:
            config = get_model_config(role)
            assert config is not None
            assert config.tier in [ModelTier.HAIKU, ModelTier.SONNET, ModelTier.OPUS]
            assert config.cost_per_input_token > 0
            assert config.cost_per_output_token > 0

    def test_cost_calculation(self):
        """Test cost calculation utility."""
        config = get_model_config(AgentRole.BACKEND_DEV)
        cost = calculate_cost(1000, 500, config)
        assert cost > 0
        assert isinstance(cost, float)

    def test_settings(self):
        """Test settings configuration."""
        settings = GaggleSettings()
        # These should have defaults or be optional
        assert hasattr(settings, 'log_level')
        assert hasattr(settings, 'default_sprint_duration')
        assert hasattr(settings, 'max_parallel_tasks')


if __name__ == "__main__":
    pytest.main([__file__])
