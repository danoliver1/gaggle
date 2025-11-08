#!/usr/bin/env python3
"""
Simple test to verify core domain models work correctly.
"""

from datetime import date, timedelta

# Test the sprint model directly
from gaggle.models.sprint import SprintMetrics, SprintModel, SprintStatus
from gaggle.models.story import StoryPriority, StoryStatus, UserStory
from gaggle.models.task import Task, TaskComplexity, TaskStatus, TaskType


def test_sprint_creation():
    """Test sprint creation and initialization."""
    sprint = SprintModel(
        id="sprint_001",
        goal="Implement user authentication system",
        status=SprintStatus.PLANNING,
    )

    assert sprint.id == "sprint_001"
    assert sprint.goal == "Implement user authentication system"
    assert sprint.status == SprintStatus.PLANNING
    assert isinstance(sprint.metrics, SprintMetrics)
    assert len(sprint.user_stories) == 0
    assert len(sprint.tasks) == 0
    print("✅ Sprint creation test passed")


def test_user_story_creation():
    """Test user story creation."""
    story = UserStory(
        id="story_001",
        title="User Login Feature",
        description="As a user, I want to log in to the system so that I can access my account",
        priority=StoryPriority.HIGH,
        story_points=5.0,
        status=StoryStatus.BACKLOG,
    )

    # Add acceptance criteria
    criteria = story.add_acceptance_criteria("User can enter username and password")
    assert criteria in story.acceptance_criteria
    assert len(story.acceptance_criteria) == 1
    print("✅ User story creation test passed")


def test_task_creation():
    """Test task creation."""
    task = Task(
        id="task_001",
        title="Implement login form",
        description="Create React component for user login",
        task_type=TaskType.FRONTEND,
        complexity=TaskComplexity.MEDIUM,
    )

    assert task.id == "task_001"
    assert task.task_type == TaskType.FRONTEND
    assert task.complexity == TaskComplexity.MEDIUM
    assert task.status == TaskStatus.TODO
    print("✅ Task creation test passed")


def test_sprint_workflow():
    """Test basic sprint workflow."""
    # Create sprint
    sprint = SprintModel(id="sprint_001", goal="Build authentication system")

    # Create and add story
    story = UserStory(
        id="story_001",
        title="User Login",
        description="As a user, I want to log in",
        priority=StoryPriority.HIGH,
        story_points=5.0,
    )
    story.add_acceptance_criteria("Login form works")
    story.add_acceptance_criteria("Authentication validates correctly")

    sprint.add_story(story)
    assert len(sprint.user_stories) == 1
    assert story.id in sprint.sprint_backlog

    # Create and add task
    task = Task(
        id="task_001",
        title="Login form implementation",
        description="Implement React login form",
        task_type=TaskType.FRONTEND,
        complexity=TaskComplexity.MEDIUM,
        story_id=story.id,
    )

    sprint.add_task(task)
    assert len(sprint.tasks) == 1

    # Start sprint
    sprint.start_sprint(duration_days=10)
    assert sprint.status == SprintStatus.ACTIVE
    assert sprint.start_date == date.today()
    assert sprint.end_date == date.today() + timedelta(days=10)

    # Test story completion
    story.status = StoryStatus.DONE
    for criteria in story.acceptance_criteria:
        criteria.mark_satisfied("QA Engineer")

    sprint._update_metrics()
    assert sprint.metrics.velocity == story.story_points
    assert sprint.metrics.completion_percentage == 100.0

    print("✅ Sprint workflow test passed")


def test_team_configuration():
    """Test team configuration."""
    from gaggle.models.team import TeamConfiguration

    team = TeamConfiguration.create_default_team()
    assert len(team.members) == 6  # PO, SM, TL, FE, BE, QA

    # Check team capacity
    capacity = team.get_team_capacity()
    assert len(capacity) == 6  # 6 different roles

    # Check available members
    available = team.get_available_members()
    assert len(available) == 6  # All should be available initially

    print("✅ Team configuration test passed")


def test_cost_calculation():
    """Test cost calculation functionality."""
    from gaggle.config.models import AgentRole, calculate_cost, get_model_config

    # Test model config retrieval
    po_config = get_model_config(AgentRole.PRODUCT_OWNER)
    assert po_config.tier.value == "haiku"

    tl_config = get_model_config(AgentRole.TECH_LEAD)
    assert tl_config.tier.value == "opus"

    # Test cost calculation
    cost = calculate_cost(1000, 500, po_config)
    assert cost > 0

    # Opus should be more expensive than Haiku
    opus_cost = calculate_cost(1000, 500, tl_config)
    haiku_cost = calculate_cost(1000, 500, po_config)
    assert opus_cost > haiku_cost

    print("✅ Cost calculation test passed")


def main():
    """Run all tests."""
    print("🧪 Running Gaggle Core Tests...")

    try:
        test_sprint_creation()
        test_user_story_creation()
        test_task_creation()
        test_sprint_workflow()
        test_team_configuration()
        test_cost_calculation()

        print("\n🎉 All tests passed! Core domain models are working correctly.")
        print("✅ Sprint models: Creation, workflow, metrics")
        print("✅ User story models: Creation, acceptance criteria")
        print("✅ Task models: Creation, status tracking")
        print("✅ Team models: Configuration, capacity management")
        print("✅ Cost models: Model tiers, cost calculation")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    main()
