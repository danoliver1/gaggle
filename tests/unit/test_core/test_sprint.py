"""Tests for Sprint domain model."""

from datetime import date, timedelta

import pytest

from gaggle.models.sprint import SprintMetrics, SprintModel, SprintStatus
from gaggle.models.story import StoryStatus


class TestSprintModel:
    """Test cases for Sprint domain model."""

    @pytest.fixture
    def sprint(self):
        """Create a test sprint."""
        return SprintModel(
            id="sprint_001",
            goal="Implement user authentication system",
            status=SprintStatus.PLANNING,
        )

    def test_sprint_creation(self, sprint):
        """Test sprint creation and initialization."""
        assert sprint.id == "sprint_001"
        assert sprint.goal == "Implement user authentication system"
        assert sprint.status == SprintStatus.PLANNING
        assert isinstance(sprint.metrics, SprintMetrics)
        assert len(sprint.user_stories) == 0
        assert len(sprint.tasks) == 0

    def test_add_story(self, sprint, sample_user_story):
        """Test adding a user story to the sprint."""
        initial_count = len(sprint.user_stories)

        sprint.add_story(sample_user_story)

        assert len(sprint.user_stories) == initial_count + 1
        assert sample_user_story in sprint.user_stories
        assert sample_user_story.id in sprint.sprint_backlog

    def test_add_duplicate_story(self, sprint, sample_user_story):
        """Test that duplicate stories are not added."""
        sprint.add_story(sample_user_story)
        initial_count = len(sprint.user_stories)

        # Try to add the same story again
        sprint.add_story(sample_user_story)

        assert len(sprint.user_stories) == initial_count

    def test_start_sprint(self, sprint):
        """Test starting a sprint."""
        sprint.start_sprint(duration_days=14)

        assert sprint.status == SprintStatus.ACTIVE
        assert sprint.start_date == date.today()
        assert sprint.end_date == date.today() + timedelta(days=14)
        assert sprint.metrics.planned_duration_days == 14

    def test_start_sprint_wrong_status(self, sprint):
        """Test that sprint can only be started from planning status."""
        sprint.status = SprintStatus.ACTIVE

        with pytest.raises(
            ValueError, match="Can only start sprints in planning status"
        ):
            sprint.start_sprint()

    def test_complete_sprint(self, sprint):
        """Test completing a sprint."""
        # Start the sprint first
        sprint.start_sprint()

        # Complete the sprint
        sprint.complete_sprint()

        assert sprint.status == SprintStatus.COMPLETED
        assert sprint.metrics.actual_duration_days is not None

    def test_complete_sprint_wrong_status(self, sprint):
        """Test that sprint can only be completed from active or review status."""
        with pytest.raises(
            ValueError, match="Can only complete active or in-review sprints"
        ):
            sprint.complete_sprint()

    def test_add_note(self, sprint):
        """Test adding notes to the sprint."""
        initial_count = len(sprint.sprint_notes)

        sprint.add_note("Daily standup completed")

        assert len(sprint.sprint_notes) == initial_count + 1
        assert "Daily standup completed" in sprint.sprint_notes[-1]

    def test_get_stories_by_status(self, sprint, sample_user_stories):
        """Test filtering stories by status."""
        # Add stories with different statuses
        sample_user_stories[0].status = StoryStatus.DONE
        sample_user_stories[1].status = StoryStatus.IN_PROGRESS
        sample_user_stories[2].status = StoryStatus.BACKLOG

        for story in sample_user_stories:
            sprint.add_story(story)

        done_stories = sprint.get_stories_by_status(StoryStatus.DONE.value)
        in_progress_stories = sprint.get_stories_by_status(
            StoryStatus.IN_PROGRESS.value
        )

        assert len(done_stories) == 1
        assert len(in_progress_stories) == 1
        assert done_stories[0].status == StoryStatus.DONE
        assert in_progress_stories[0].status == StoryStatus.IN_PROGRESS

    def test_get_tasks_for_story(self, sprint, sample_user_story):
        """Test getting tasks for a specific story."""
        from gaggle.models.task import Task, TaskComplexity, TaskType

        # Add the story
        sprint.add_story(sample_user_story)

        # Create tasks for the story
        task1 = Task(
            id="task_001",
            title="Frontend Implementation",
            description="Implement login form",
            task_type=TaskType.FRONTEND,
            complexity=TaskComplexity.MEDIUM,
            story_id=sample_user_story.id,
        )

        task2 = Task(
            id="task_002",
            title="Backend API",
            description="Implement authentication API",
            task_type=TaskType.BACKEND,
            complexity=TaskComplexity.HIGH,
            story_id=sample_user_story.id,
        )

        sprint.add_task(task1)
        sprint.add_task(task2)

        story_tasks = sprint.get_tasks_for_story(sample_user_story.id)

        assert len(story_tasks) == 2
        assert all(task.story_id == sample_user_story.id for task in story_tasks)

    def test_metrics_update(self, sprint, sample_user_stories):
        """Test that metrics are updated when stories and tasks are added."""
        # Add stories
        for story in sample_user_stories:
            sprint.add_story(story)

        # Verify initial metrics
        total_points = sum(story.story_points for story in sample_user_stories)
        assert sprint.metrics.total_story_points == total_points
        assert sprint.metrics.velocity == 0.0  # No completed stories yet

        # Complete some stories
        sample_user_stories[0].status = StoryStatus.DONE
        sprint._update_metrics()

        assert sprint.metrics.velocity == sample_user_stories[0].story_points
        assert (
            sprint.metrics.burndown_remaining
            == total_points - sample_user_stories[0].story_points
        )

    def test_completion_percentage(self, sprint, sample_user_stories):
        """Test completion percentage calculation."""
        # Add stories
        for story in sample_user_stories:
            sprint.add_story(story)

        total_points = sum(story.story_points for story in sample_user_stories)

        # Complete first story
        sample_user_stories[0].status = StoryStatus.DONE
        sprint._update_metrics()

        expected_percentage = (sample_user_stories[0].story_points / total_points) * 100
        assert sprint.metrics.completion_percentage == expected_percentage

    def test_daily_standup_report(self, sprint, sample_user_stories):
        """Test daily standup report generation."""
        # Setup sprint
        sprint.start_sprint()
        for story in sample_user_stories:
            sprint.add_story(story)

        # Add some notes
        sprint.add_note("Frontend team made good progress")
        sprint.add_note("Backend API implementation started")

        report = sprint.get_daily_standup_report()

        assert "sprint_id" in report
        assert "sprint_goal" in report
        assert "days_remaining" in report
        assert "completion_percentage" in report
        assert "stories_completed" in report
        assert "stories_in_progress" in report
        assert "tasks_completed" in report
        assert "tasks_total" in report
        assert "blockers" in report
        assert "recent_notes" in report

        # Verify recent notes are included
        assert len(report["recent_notes"]) <= 3  # Should show last 3 notes


class TestSprintMetrics:
    """Test cases for Sprint metrics."""

    def test_cost_per_story_point(self):
        """Test cost per story point calculation."""
        metrics = SprintMetrics(velocity=10.0, total_cost=100.0)

        assert metrics.cost_per_story_point == 10.0

    def test_cost_per_story_point_zero_velocity(self):
        """Test cost per story point with zero velocity."""
        metrics = SprintMetrics(velocity=0.0, total_cost=100.0)

        assert metrics.cost_per_story_point == 0.0

    def test_task_completion_rate(self):
        """Test task completion rate calculation."""
        metrics = SprintMetrics(tasks_completed=8, tasks_total=10)

        assert metrics.task_completion_rate == 80.0

    def test_task_completion_rate_zero_tasks(self):
        """Test task completion rate with zero tasks."""
        metrics = SprintMetrics(tasks_completed=0, tasks_total=0)

        assert metrics.task_completion_rate == 0.0
