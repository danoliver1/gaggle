#!/usr/bin/env python3
"""
Production-ready minimal test suite - focused on core functionality that MUST work.
"""

import pytest
from datetime import datetime

# Import ONLY what we need and know works
from gaggle.models.task import Task, TaskStatus, TaskType, TaskComplexity
from gaggle.models.story import UserStory, StoryStatus, AcceptanceCriteria
from gaggle.models.sprint import SprintModel, SprintStatus
from gaggle.models.team import TeamMember, TeamConfiguration, AgentStatus
from gaggle.config.models import AgentRole, ModelTier, get_model_config, calculate_cost


class TestCoreModelsProduction:
    """Test the absolute core model functionality required for production."""
    
    def test_task_creation_and_basic_workflow(self):
        """Test task creation and basic state transitions work."""
        # Create task
        task = Task(
            id="task_1",
            title="Production Task",
            description="Production task description",
            task_type=TaskType.BACKEND
        )
        
        assert task.id == "task_1"
        assert task.status == TaskStatus.TODO
        assert task.progress_percentage == 0.0
        
        # Test basic workflow
        task.start_work()
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.started_at is not None
        
        task.mark_for_review()
        assert task.status == TaskStatus.IN_REVIEW
        assert task.progress_percentage == 100.0
        
        task.complete_task()
        assert task.status == TaskStatus.DONE
        assert task.completed_at is not None
        
    def test_user_story_creation_and_criteria(self):
        """Test user story creation and acceptance criteria."""
        story = UserStory(
            id="story_1",
            title="Production Story",
            description="As a user, I want production functionality so that the system works"
        )
        
        assert story.id == "story_1"
        assert story.status == StoryStatus.BACKLOG
        assert len(story.acceptance_criteria) == 0
        
        # Add acceptance criteria
        criteria = story.add_acceptance_criteria("System must work correctly")
        assert len(story.acceptance_criteria) == 1
        assert criteria.description == "System must work correctly"
        assert not criteria.is_satisfied
        
        # Mark criteria as satisfied
        criteria.mark_satisfied("test_user")
        assert criteria.is_satisfied
        assert criteria.verified_by == "test_user"
        
        # Check completion
        completion = story.get_completion_percentage()
        assert completion == 100.0
        
    def test_sprint_creation_and_lifecycle(self):
        """Test sprint creation and basic lifecycle."""
        sprint = SprintModel(
            id="sprint_1",
            goal="Production sprint goal that is long enough to pass validation"
        )
        
        assert sprint.id == "sprint_1" 
        assert sprint.status == SprintStatus.PLANNING
        
        # Start sprint
        sprint.start_sprint()
        assert sprint.status == SprintStatus.ACTIVE
        
        # Add story
        story = UserStory(
            id="story_1", 
            title="Sprint Story",
            description="Story for sprint testing"
        )
        sprint.add_story(story)
        assert len(sprint.user_stories) == 1
        
        # Complete sprint
        sprint.complete_sprint()
        assert sprint.status == SprintStatus.COMPLETED
        
    def test_team_configuration_and_management(self):
        """Test team configuration and member management."""
        team = TeamConfiguration(
            id="production_team",
            name="Production Team"
        )
        
        assert team.id == "production_team"
        assert len(team.members) == 0
        
        # Add team member
        member = TeamMember(
            id="dev_1",
            name="Production Developer", 
            role=AgentRole.BACKEND_DEV,
            model_tier=ModelTier.SONNET
        )
        team.add_member(member)
        assert len(team.members) == 1
        
        # Test member retrieval
        found = team.get_member_by_id("dev_1")
        assert found is not None
        assert found.name == "Production Developer"
        
        # Test capacity calculation
        capacity = team.get_team_capacity()
        assert AgentRole.BACKEND_DEV in capacity
        assert capacity[AgentRole.BACKEND_DEV] == 1
        
        # Test available members
        available = team.get_available_members()
        assert len(available) == 1


class TestProductionizedAlgorithms:
    """Test the newly productionized algorithms work correctly."""
    
    def test_task_optimization_algorithm_works(self):
        """Test task optimization produces valid assignments."""
        team = TeamConfiguration(id="opt_team", name="Optimization Team")
        
        # Add diverse team members
        team.add_member(TeamMember(
            id="fe_1", name="Frontend Dev", role=AgentRole.FRONTEND_DEV, model_tier=ModelTier.SONNET
        ))
        team.add_member(TeamMember(
            id="be_1", name="Backend Dev", role=AgentRole.BACKEND_DEV, model_tier=ModelTier.SONNET
        ))
        
        # Create test tasks with estimated_hours to avoid None values
        tasks = [
            Task(id="task_1", title="Frontend Task", description="Frontend UI development work", 
                 task_type=TaskType.FRONTEND, assigned_role=AgentRole.FRONTEND_DEV, estimated_hours=4.0),
            Task(id="task_2", title="Backend Task", description="Backend API development work",
                 task_type=TaskType.BACKEND, assigned_role=AgentRole.BACKEND_DEV, estimated_hours=6.0)
        ]
        
        # Test optimization
        assignments = team.optimize_task_assignments(tasks)
        
        # Verify assignments
        assert len(assignments) == 2
        assert all(len(assignment.task_ids) > 0 for assignment in assignments)
        
        # Verify each task is assigned
        all_assigned_tasks = []
        for assignment in assignments:
            all_assigned_tasks.extend(assignment.task_ids)
        assert len(all_assigned_tasks) == 2
        
    def test_story_dependency_checking_works(self):
        """Test story dependency checking logic."""
        # Create stories
        story1 = UserStory(id="story_1", title="Base Story", 
                          description="Base functionality", status=StoryStatus.DONE)
        story2 = UserStory(id="story_2", title="Dependent Story",
                          description="Depends on base", dependencies=["story_1"])
        
        # Create registry
        registry = {"story_1": story1, "story_2": story2}
        
        # Test dependency resolution
        assert not story1.has_unresolved_dependencies(registry)
        assert not story2.has_unresolved_dependencies(registry)  # story_1 is DONE
        
        # Test with unresolved dependency
        story1.status = StoryStatus.IN_PROGRESS
        assert story2.has_unresolved_dependencies(registry)  # story_1 not DONE
        
        # Test with missing dependency
        story3 = UserStory(id="story_3", title="Missing Dep Story",
                          description="Missing dependency", dependencies=["missing_story"])
        assert story3.has_unresolved_dependencies(registry)


class TestCriticalConfigurations:
    """Test configuration and cost calculation works."""
    
    def test_model_configuration_retrieval(self):
        """Test model configs can be retrieved for all roles."""
        for role in [AgentRole.BACKEND_DEV, AgentRole.FRONTEND_DEV, AgentRole.TECH_LEAD]:
            config = get_model_config(role)
            assert config is not None
            assert config.tier in [ModelTier.HAIKU, ModelTier.SONNET, ModelTier.OPUS]
            assert config.cost_per_input_token > 0
            assert config.cost_per_output_token > 0
            
    def test_cost_calculation_works(self):
        """Test cost calculation produces reasonable results."""
        config = get_model_config(AgentRole.BACKEND_DEV)
        cost = calculate_cost(1000, 500, config)
        
        assert cost > 0
        assert isinstance(cost, float)
        assert cost < 15.0  # Sanity check - reasonable cost for 1000+500 tokens
        
    def test_team_member_performance_metrics(self):
        """Test team member performance tracking."""
        member = TeamMember(
            id="perf_member",
            name="Performance Member",
            role=AgentRole.BACKEND_DEV,
            model_tier=ModelTier.SONNET
        )
        
        # Test initial state
        assert member.tasks_completed == 0
        assert member.total_cost == 0.0
        
        # Assign task first, then complete it
        member.assign_task("test_task_123")
        member.complete_task(150, 0.01)  # 150 total tokens, $0.01
        
        assert member.tasks_completed == 1
        assert member.total_tokens_used == 150
        assert member.total_cost == 0.01
        
        # Test performance metrics
        metrics = member.get_performance_metrics()
        assert "member_id" in metrics
        assert "tasks_completed" in metrics
        assert metrics["tasks_completed"] == 1


if __name__ == "__main__":
    # Run with coverage
    pytest.main([__file__, "--cov=src/gaggle/models", "--cov=src/gaggle/config", 
                 "--cov-report=term-missing", "-v"])