#!/usr/bin/env python3
"""Test script for comprehensive Pydantic validation across all models."""

import sys
from datetime import datetime, date
from pydantic import ValidationError
import pytest

# Import models
from gaggle.models.task import Task, TaskDependency, TaskStatus, TaskType, TaskComplexity, TaskPriority
from gaggle.models.story import UserStory, AcceptanceCriteria, StoryStatus, StoryPriority
from gaggle.models.sprint import SprintModel, SprintMetrics, SprintStatus
from gaggle.models.team import TeamMember, AgentAssignment, TeamConfiguration, AgentStatus
from gaggle.config.models import AgentRole, ModelTier


class TestAcceptanceCriteriaValidation:
    """Test AcceptanceCriteria model validation."""

    def test_valid_acceptance_criteria(self):
        """Test valid acceptance criteria creation."""
        criteria = AcceptanceCriteria(
            id="test_1",
            description="User can login with email and password"
        )
        assert criteria.id == "test_1"
        assert criteria.description == "User can login with email and password"
        assert criteria.is_satisfied is False

    def test_empty_id_validation(self):
        """Test empty ID validation."""
        with pytest.raises(ValidationError) as exc_info:
            AcceptanceCriteria(id="", description="Valid description")
        assert "Acceptance criteria ID cannot be empty" in str(exc_info.value)

    def test_empty_description_validation(self):
        """Test empty description validation."""
        with pytest.raises(ValidationError) as exc_info:
            AcceptanceCriteria(id="test_1", description="")
        assert "Acceptance criteria description cannot be empty" in str(exc_info.value)

    def test_description_length_validation(self):
        """Test description length validation."""
        # Too short
        with pytest.raises(ValidationError) as exc_info:
            AcceptanceCriteria(id="test_1", description="abc")
        assert "at least 5 characters" in str(exc_info.value)

        # Too long
        long_description = "x" * 501
        with pytest.raises(ValidationError) as exc_info:
            AcceptanceCriteria(id="test_1", description=long_description)
        assert "500 characters or less" in str(exc_info.value)

    def test_satisfaction_consistency(self):
        """Test satisfaction consistency validation."""
        # Satisfied criteria without verified_by
        with pytest.raises(ValidationError) as exc_info:
            AcceptanceCriteria(
                id="test_1",
                description="Valid description",
                is_satisfied=True
            )
        assert "Satisfied criteria must have verified_by" in str(exc_info.value)

        # Verified criteria not marked satisfied
        with pytest.raises(ValidationError) as exc_info:
            AcceptanceCriteria(
                id="test_1",
                description="Valid description",
                verified_by="QA Engineer"
            )
        assert "must be marked as satisfied" in str(exc_info.value)


class TestUserStoryValidation:
    """Test UserStory model validation."""

    def test_valid_user_story(self):
        """Test valid user story creation."""
        story = UserStory(
            id="US-001",
            title="User Registration",
            description="As a new user, I want to register an account so that I can access the application"
        )
        assert story.id == "US-001"
        assert story.title == "User Registration"

    def test_story_title_validation(self):
        """Test story title validation."""
        # Empty title
        with pytest.raises(ValidationError) as exc_info:
            UserStory(id="US-001", title="", description="Valid description")
        assert "Story title cannot be empty" in str(exc_info.value)

        # Too long title
        long_title = "x" * 201
        with pytest.raises(ValidationError) as exc_info:
            UserStory(id="US-001", title=long_title, description="Valid description")
        assert "200 characters or less" in str(exc_info.value)

    def test_story_description_validation(self):
        """Test story description validation."""
        # Empty description
        with pytest.raises(ValidationError) as exc_info:
            UserStory(id="US-001", title="Valid title", description="")
        assert "Story description cannot be empty" in str(exc_info.value)

        # Too short description
        with pytest.raises(ValidationError) as exc_info:
            UserStory(id="US-001", title="Valid title", description="short")
        assert "at least 10 characters" in str(exc_info.value)

    def test_story_points_validation(self):
        """Test story points validation."""
        with pytest.raises(ValidationError) as exc_info:
            UserStory(
                id="US-001",
                title="Valid title",
                description="Valid description",
                story_points=-1
            )
        assert "Story points must be non-negative" in str(exc_info.value)

    def test_story_status_constraints(self):
        """Test story status constraints."""
        # In-progress story without story points
        with pytest.raises(ValidationError) as exc_info:
            UserStory(
                id="US-001",
                title="Valid title",
                description="Valid description",
                status=StoryStatus.IN_PROGRESS,
                story_points=0
            )
        assert "must have story points > 0" in str(exc_info.value)

        # In-progress story without acceptance criteria
        with pytest.raises(ValidationError) as exc_info:
            UserStory(
                id="US-001",
                title="Valid title",
                description="Valid description",
                status=StoryStatus.IN_PROGRESS,
                story_points=3,
                acceptance_criteria=[]
            )
        assert "must have acceptance criteria" in str(exc_info.value)


class TestTaskValidation:
    """Test Task model validation."""

    def test_valid_task(self):
        """Test valid task creation."""
        task = Task(
            id="T-001",
            title="Implement user login",
            description="Create login form and authentication logic",
            task_type=TaskType.FRONTEND
        )
        assert task.id == "T-001"
        assert task.title == "Implement user login"
        assert task.task_type == TaskType.FRONTEND

    def test_task_id_validation(self):
        """Test task ID validation."""
        with pytest.raises(ValidationError) as exc_info:
            Task(
                id="",
                title="Valid title",
                description="Valid description",
                task_type=TaskType.FRONTEND
            )
        assert "Task ID cannot be empty" in str(exc_info.value)

    def test_task_title_validation(self):
        """Test task title validation."""
        # Empty title
        with pytest.raises(ValidationError) as exc_info:
            Task(
                id="T-001",
                title="",
                description="Valid description",
                task_type=TaskType.FRONTEND
            )
        assert "Task title cannot be empty" in str(exc_info.value)

        # Too long title
        long_title = "x" * 201
        with pytest.raises(ValidationError) as exc_info:
            Task(
                id="T-001",
                title=long_title,
                description="Valid description",
                task_type=TaskType.FRONTEND
            )
        assert "200 characters or less" in str(exc_info.value)

    def test_task_description_validation(self):
        """Test task description validation."""
        # Empty description
        with pytest.raises(ValidationError) as exc_info:
            Task(
                id="T-001",
                title="Valid title",
                description="",
                task_type=TaskType.FRONTEND
            )
        assert "Task description cannot be empty" in str(exc_info.value)

        # Too short description
        with pytest.raises(ValidationError) as exc_info:
            Task(
                id="T-001",
                title="Valid title",
                description="short",
                task_type=TaskType.FRONTEND
            )
        assert "at least 10 characters" in str(exc_info.value)

    def test_progress_percentage_validation(self):
        """Test progress percentage validation."""
        # Negative progress
        with pytest.raises(ValidationError) as exc_info:
            Task(
                id="T-001",
                title="Valid title",
                description="Valid description",
                task_type=TaskType.FRONTEND,
                progress_percentage=-1
            )
        assert "Progress percentage must be between 0 and 100" in str(exc_info.value)

        # Progress > 100
        with pytest.raises(ValidationError) as exc_info:
            Task(
                id="T-001",
                title="Valid title",
                description="Valid description",
                task_type=TaskType.FRONTEND,
                progress_percentage=101
            )
        assert "Progress percentage must be between 0 and 100" in str(exc_info.value)

    def test_hours_validation(self):
        """Test hours validation."""
        # Negative estimated hours
        with pytest.raises(ValidationError) as exc_info:
            Task(
                id="T-001",
                title="Valid title",
                description="Valid description",
                task_type=TaskType.FRONTEND,
                estimated_hours=-1
            )
        assert "Hours must be positive" in str(exc_info.value)

        # Unrealistic hours
        with pytest.raises(ValidationError) as exc_info:
            Task(
                id="T-001",
                title="Valid title",
                description="Valid description",
                task_type=TaskType.FRONTEND,
                estimated_hours=1001
            )
        assert "Hours cannot exceed 1000" in str(exc_info.value)

    def test_task_status_constraints(self):
        """Test task status constraints."""
        # In-progress task without assignment
        with pytest.raises(ValidationError) as exc_info:
            Task(
                id="T-001",
                title="Valid title",
                description="Valid description",
                task_type=TaskType.FRONTEND,
                status=TaskStatus.IN_PROGRESS
            )
        assert "Tasks in progress must be assigned to someone" in str(exc_info.value)

        # Blocked task without reason
        with pytest.raises(ValidationError) as exc_info:
            Task(
                id="T-001",
                title="Valid title",
                description="Valid description",
                task_type=TaskType.FRONTEND,
                status=TaskStatus.BLOCKED
            )
        assert "Blocked tasks must have blocker_reason" in str(exc_info.value)


class TestTaskDependencyValidation:
    """Test TaskDependency model validation."""

    def test_valid_task_dependency(self):
        """Test valid task dependency creation."""
        dep = TaskDependency(
            task_id="T-002",
            dependency_type="blocks",
            description="Must complete before UI work"
        )
        assert dep.task_id == "T-002"
        assert dep.dependency_type == "blocks"

    def test_dependency_type_validation(self):
        """Test dependency type validation."""
        with pytest.raises(ValidationError) as exc_info:
            TaskDependency(
                task_id="T-002",
                dependency_type="invalid_type"
            )
        assert "Dependency type must be one of" in str(exc_info.value)


class TestSprintValidation:
    """Test Sprint model validation."""

    def test_valid_sprint_metrics(self):
        """Test valid sprint metrics creation."""
        metrics = SprintMetrics(
            velocity=25.0,
            total_story_points=50.0,
            burndown_remaining=25.0,
            planned_duration_days=14
        )
        assert metrics.velocity == 25.0
        assert metrics.completion_percentage == 50.0

    def test_sprint_metrics_validation(self):
        """Test sprint metrics validation."""
        # Negative velocity
        with pytest.raises(ValidationError) as exc_info:
            SprintMetrics(velocity=-1)
        assert "Story point metrics must be non-negative" in str(exc_info.value)

        # Unrealistic token usage
        with pytest.raises(ValidationError) as exc_info:
            SprintMetrics(total_tokens_used=100000001)
        assert "Token usage seems unreasonably high" in str(exc_info.value)

        # Velocity exceeds total points
        with pytest.raises(ValidationError) as exc_info:
            SprintMetrics(
                velocity=100,
                total_story_points=50,
                burndown_remaining=-50  # This will be auto-corrected
            )
        assert "Velocity cannot exceed total story points" in str(exc_info.value)

    def test_valid_sprint(self):
        """Test valid sprint creation."""
        sprint = SprintModel(
            id="SP-001",
            goal="Implement user authentication system"
        )
        assert sprint.id == "SP-001"
        assert sprint.goal == "Implement user authentication system"

    def test_sprint_goal_validation(self):
        """Test sprint goal validation."""
        # Empty goal
        with pytest.raises(ValidationError) as exc_info:
            SprintModel(id="SP-001", goal="")
        assert "Sprint goal cannot be empty" in str(exc_info.value)

        # Too short goal
        with pytest.raises(ValidationError) as exc_info:
            SprintModel(id="SP-001", goal="short")
        assert "Sprint goal must be at least 10 characters" in str(exc_info.value)


class TestTeamValidation:
    """Test Team model validation."""

    def test_valid_team_member(self):
        """Test valid team member creation."""
        member = TeamMember(
            id="TM-001",
            name="John Doe",
            role=AgentRole.FRONTEND_DEV,
            model_tier=ModelTier.SONNET
        )
        assert member.id == "TM-001"
        assert member.name == "John Doe"
        assert member.role == AgentRole.FRONTEND_DEV

    def test_team_member_validation(self):
        """Test team member validation."""
        # Empty ID
        with pytest.raises(ValidationError) as exc_info:
            TeamMember(
                id="",
                name="John Doe",
                role=AgentRole.FRONTEND_DEV,
                model_tier=ModelTier.SONNET
            )
        assert "Team member ID cannot be empty" in str(exc_info.value)

        # Invalid max concurrent tasks
        with pytest.raises(ValidationError) as exc_info:
            TeamMember(
                id="TM-001",
                name="John Doe",
                role=AgentRole.FRONTEND_DEV,
                model_tier=ModelTier.SONNET,
                max_concurrent_tasks=0
            )
        assert "Max concurrent tasks must be positive" in str(exc_info.value)

    def test_team_member_status_constraints(self):
        """Test team member status constraints."""
        # Busy member without task
        with pytest.raises(ValidationError) as exc_info:
            TeamMember(
                id="TM-001",
                name="John Doe",
                role=AgentRole.FRONTEND_DEV,
                model_tier=ModelTier.SONNET,
                status=AgentStatus.BUSY
            )
        assert "Busy team members must have a current task" in str(exc_info.value)

    def test_valid_team_configuration(self):
        """Test valid team configuration creation."""
        team = TeamConfiguration(
            id="TEAM-001",
            name="Development Team Alpha"
        )
        assert team.id == "TEAM-001"
        assert team.name == "Development Team Alpha"

    def test_team_configuration_validation(self):
        """Test team configuration validation."""
        # Invalid coordination overhead
        with pytest.raises(ValidationError) as exc_info:
            TeamConfiguration(
                id="TEAM-001",
                name="Development Team Alpha",
                coordination_overhead=1.5  # >100%
            )
        assert "Coordination overhead cannot exceed 100%" in str(exc_info.value)


def run_validation_tests():
    """Run comprehensive validation tests."""
    print("🧪 Running Pydantic Validation Tests...")
    print("=" * 50)
    
    test_classes = [
        TestAcceptanceCriteriaValidation,
        TestUserStoryValidation,
        TestTaskValidation,
        TestTaskDependencyValidation,
        TestSprintValidation,
        TestTeamValidation
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        class_name = test_class.__name__
        print(f"\n📋 Testing {class_name}:")
        
        instance = test_class()
        methods = [method for method in dir(instance) if method.startswith('test_')]
        
        for method_name in methods:
            total_tests += 1
            try:
                method = getattr(instance, method_name)
                method()
                passed_tests += 1
                print(f"  ✅ {method_name}")
            except Exception as e:
                print(f"  ❌ {method_name}: {str(e)}")
    
    print("\n" + "=" * 50)
    print(f"📊 Validation Test Results:")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {total_tests - passed_tests}")
    print(f"📈 Success Rate: {(passed_tests / total_tests * 100):.1f}%")
    
    if passed_tests == total_tests:
        print("🎉 All validation tests passed!")
        return True
    else:
        print("⚠️  Some validation tests failed.")
        return False


if __name__ == "__main__":
    try:
        success = run_validation_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"💥 Error running validation tests: {e}")
        sys.exit(1)