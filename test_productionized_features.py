#!/usr/bin/env python3
"""
Test script to verify that all productionized implementations work correctly.
"""

import asyncio
from datetime import datetime

import pytest

from gaggle.models.team import TeamConfiguration, TeamMember, AgentAssignment
from gaggle.models.story import UserStory, StoryStatus, AcceptanceCriteria
from gaggle.models.task import Task, TaskStatus, TaskType, TaskComplexity
from gaggle.config.models import AgentRole, ModelTier
from gaggle.tools.project_tools import BacklogTool


def test_task_optimization_algorithm():
    """Test the productionized task optimization algorithm."""
    print("🔧 Testing Task Optimization Algorithm...")
    
    # Create a team with diverse members
    team = TeamConfiguration(
        id="test_team",
        name="Test Team"
    )
    
    # Add team members with different roles
    team.add_member(TeamMember(
        id="fe_001",
        name="Frontend Developer",
        role=AgentRole.FRONTEND_DEV,
        model_tier=ModelTier.SONNET,
        specializations=["react", "typescript", "ui"]
    ))
    
    team.add_member(TeamMember(
        id="be_001", 
        name="Backend Developer",
        role=AgentRole.BACKEND_DEV,
        model_tier=ModelTier.SONNET,
        specializations=["python", "api", "database"]
    ))
    
    team.add_member(TeamMember(
        id="tl_001",
        name="Tech Lead",
        role=AgentRole.TECH_LEAD,
        model_tier=ModelTier.OPUS,
        specializations=["architecture", "code_review"]
    ))
    
    # Create mock tasks with different characteristics
    tasks = [
        Task(
            id="task_1",
            title="Frontend UI Component",
            description="Build React component",
            task_type=TaskType.FRONTEND,
            complexity=TaskComplexity.MEDIUM,
            assigned_role=AgentRole.FRONTEND_DEV,
            estimated_hours=4.0,
            estimated_input_tokens=800,
            estimated_output_tokens=400
        ),
        Task(
            id="task_2", 
            title="API Endpoint",
            description="Create backend API",
            task_type=TaskType.BACKEND,
            complexity=TaskComplexity.HIGH,
            assigned_role=AgentRole.BACKEND_DEV,
            estimated_hours=6.0,
            estimated_input_tokens=1200,
            estimated_output_tokens=600
        ),
        Task(
            id="task_3",
            title="Architecture Review", 
            description="Review system design",
            task_type=TaskType.ARCHITECTURE,
            complexity=TaskComplexity.HIGH,
            assigned_role=AgentRole.TECH_LEAD,
            estimated_hours=3.0,
            estimated_input_tokens=1500,
            estimated_output_tokens=800
        )
    ]
    
    # Test optimization
    assignments = team.optimize_task_assignments(tasks)
    
    print(f"   ✅ Generated {len(assignments)} assignments")
    
    # Verify assignments
    assert len(assignments) == 3, f"Expected 3 assignments, got {len(assignments)}"
    
    # Verify role matching
    for assignment in assignments:
        member = team.get_member_by_id(assignment.agent_id)
        role_value = member.role.value if hasattr(member.role, 'value') else str(member.role)
        print(f"   📋 {member.name} ({role_value}): {len(assignment.task_ids)} tasks")
        assert len(assignment.task_ids) > 0, f"Member {member.name} should have tasks assigned"
        
    print("   ✅ Task optimization algorithm works correctly!")
    return True


def test_story_dependency_checking():
    """Test the productionized story dependency checking."""
    print("📚 Testing Story Dependency Checking...")
    
    # Create stories with dependencies
    story1 = UserStory(
        id="story_1",
        title="User Authentication",
        description="As a user, I want to log in so that I can access the system",
        status=StoryStatus.DONE
    )
    
    story2 = UserStory(
        id="story_2", 
        title="User Profile",
        description="As a user, I want to view my profile so that I can see my information",
        status=StoryStatus.IN_PROGRESS,
        dependencies=["story_1"]  # Depends on authentication
    )
    
    story3 = UserStory(
        id="story_3",
        title="User Settings",
        description="As a user, I want to update my settings so that I can customize my experience", 
        status=StoryStatus.BACKLOG,
        dependencies=["story_1", "story_missing"]  # Depends on auth + missing story
    )
    
    story_registry = {
        "story_1": story1,
        "story_2": story2,
        "story_3": story3
    }
    
    # Test dependency checking
    assert not story1.has_unresolved_dependencies(story_registry), "Story 1 should have no unresolved dependencies"
    assert not story2.has_unresolved_dependencies(story_registry), "Story 2 dependencies should be resolved (story 1 is done)"
    assert story3.has_unresolved_dependencies(story_registry), "Story 3 should have unresolved dependencies (missing story)"
    
    # Test without registry (conservative mode)
    assert story2.has_unresolved_dependencies(), "Without registry, should assume dependencies are unresolved"
    
    print("   ✅ Story dependency checking works correctly!")
    return True


@pytest.mark.asyncio
async def test_backlog_prioritization():
    """Test the productionized backlog prioritization algorithm."""
    print("📊 Testing Backlog Prioritization Algorithm...")
    
    backlog_tool = BacklogTool()
    
    # Create test stories with different characteristics
    stories = [
        {
            "id": "story_1",
            "title": "User Login Security",
            "description": "As a user, I want secure login so that my account is protected",
            "priority": "critical",
            "story_points": 5,
            "dependencies": []
        },
        {
            "id": "story_2", 
            "title": "Dashboard UI",
            "description": "As a user, I want a dashboard so that I can see overview",
            "priority": "medium",
            "story_points": 8,  # Large story
            "dependencies": ["story_1"]  # Has dependencies
        },
        {
            "id": "story_3",
            "title": "Customer Support Chat", 
            "description": "As a customer, I want live chat so that I can get help",
            "priority": "low",
            "story_points": 3,  # Small story
            "dependencies": []
        },
        {
            "id": "story_4",
            "title": "Performance Optimization",
            "description": "As a developer, I want faster load times so that users are happy",
            "priority": "high", 
            "story_points": 2,  # Small high-priority story
            "dependencies": []
        }
    ]
    
    result = await backlog_tool.prioritize_stories(stories)
    
    prioritized_stories = result["prioritized_stories"]
    scores = result["priority_scores"]
    
    print(f"   📈 Prioritized {len(prioritized_stories)} stories")
    print(f"   📋 Priority order: {[s['title'][:20] + '...' for s in prioritized_stories]}")
    
    # Verify critical priority story comes first
    assert prioritized_stories[0]["priority"] == "critical", "Critical priority story should be first"
    
    # Verify high priority small story ranks well
    high_priority_positions = [i for i, story in enumerate(prioritized_stories) if story["priority"] == "high"]
    assert len(high_priority_positions) > 0 and high_priority_positions[0] <= 2, "High priority story should rank highly"
    
    print("   ✅ Backlog prioritization algorithm works correctly!")
    return True


async def run_all_tests():
    """Run all productionized feature tests."""
    print("🚀 Testing All Productionized Features\n" + "="*50)
    
    tests_passed = 0
    total_tests = 3
    
    try:
        if test_task_optimization_algorithm():
            tests_passed += 1
        print()
        
        if test_story_dependency_checking():
            tests_passed += 1
        print()
        
        if await test_backlog_prioritization():
            tests_passed += 1
        print()
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    print("="*50)
    print(f"🏁 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All productionized features are working correctly!")
        return True
    else:
        print("⚠️  Some tests failed - review implementations")
        return False


if __name__ == "__main__":
    asyncio.run(run_all_tests())