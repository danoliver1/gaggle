#!/usr/bin/env python3
"""Basic functionality test for Gaggle agents."""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from gaggle.agents.coordination.product_owner import ProductOwner
from gaggle.agents.coordination.scrum_master import ScrumMaster
from gaggle.agents.architecture.tech_lead import TechLead
from gaggle.config.models import AgentRole


async def test_basic_agent_functionality():
    """Test basic agent creation and functionality."""
    print("🧪 Testing Gaggle Agent Functionality")
    print("=" * 50)
    
    # Test Product Owner
    print("\n1. Testing Product Owner...")
    try:
        po = ProductOwner()
        print(f"✅ Product Owner created: {po.name} ({po.role.value})")
        
        # Test a simple task
        result = await po.create_user_stories(
            product_idea="Web application with user login and dashboard for customers"
        )
        print(f"✅ Product Owner executed task successfully")
        print(f"   Stories created: {len(result) if result else 0}")
        
    except Exception as e:
        print(f"❌ Product Owner test failed: {e}")
        return False
    
    # Test Scrum Master
    print("\n2. Testing Scrum Master...")
    try:
        sm = ScrumMaster()
        print(f"✅ Scrum Master created: {sm.name} ({sm.role.value})")
        
        # Test planning functionality
        from gaggle.models.story import UserStory, StoryPriority
        sample_story = UserStory(
            id="US-001",
            title="User Login",
            description="User authentication feature",
            priority=StoryPriority.HIGH,
            story_points=5
        )
        
        result = await sm.plan_sprint([sample_story], team_velocity=20)
        print(f"✅ Scrum Master executed planning successfully")
        
    except Exception as e:
        print(f"❌ Scrum Master test failed: {e}")
        return False
    
    # Test Tech Lead
    print("\n3. Testing Tech Lead...")
    try:
        tl = TechLead()
        print(f"✅ Tech Lead created: {tl.name} ({tl.role.value})")
        
        # Test architecture analysis
        result = await tl.analyze_architecture_requirements(
            [sample_story],
            {"tech_stack": "React/Node.js", "scale": "medium"}
        )
        print(f"✅ Tech Lead executed analysis successfully")
        
    except Exception as e:
        print(f"❌ Tech Lead test failed: {e}")
        return False
    
    print("\n🎉 All basic functionality tests passed!")
    return True


async def test_cost_tracking():
    """Test cost tracking functionality."""
    print("\n💰 Testing Cost Tracking...")
    
    try:
        from gaggle.utils.token_counter import TokenCounter
        from gaggle.config.models import AgentRole, get_model_config, calculate_cost
        
        counter = TokenCounter()
        
        # Simulate some usage
        counter.add_usage(100, 200, AgentRole.PRODUCT_OWNER)
        counter.add_usage(500, 300, AgentRole.TECH_LEAD)
        
        total_cost = counter.get_total_cost()
        total_tokens = counter.get_total_tokens()
        
        print(f"✅ Cost tracking working:")
        print(f"   Total tokens: {total_tokens}")
        print(f"   Total cost: ${total_cost:.4f}")
        
        breakdown = counter.get_cost_breakdown()
        for role, data in breakdown.items():
            print(f"   {role}: {data['total_tokens']} tokens, ${data['cost']:.4f} ({data['model_tier']})")
        
        return True
        
    except Exception as e:
        print(f"❌ Cost tracking test failed: {e}")
        return False


async def test_models():
    """Test data models."""
    print("\n📊 Testing Data Models...")
    
    try:
        from gaggle.models.sprint import Sprint
        from gaggle.models.story import UserStory, AcceptanceCriteria, StoryPriority
        from gaggle.models.task import Task, TaskStatus, TaskType
        from datetime import datetime, timedelta
        
        # Create a task
        task = Task(
            id="TASK-001",
            title="Implement login form",
            description="Create React login component",
            task_type=TaskType.FRONTEND,
            status=TaskStatus.TODO,
            assigned_to="frontend_dev",
            estimated_hours=4,
            story_id="US-001"
        )
        
        # Create acceptance criteria
        ac1 = AcceptanceCriteria(
            id="AC-001",
            description="User can enter valid credentials and login"
        )
        ac2 = AcceptanceCriteria(
            id="AC-002", 
            description="System shows error for invalid credentials"
        )
        
        # Create a user story
        story = UserStory(
            id="US-001",
            title="User Authentication",
            description="User login functionality",
            acceptance_criteria=[ac1, ac2],
            priority=StoryPriority.HIGH,
            story_points=5
        )
        
        # Create a sprint
        sprint = Sprint(
            id="SPRINT-001",
            goal="Implement authentication",
            user_stories=[story]
        )
        
        print(f"✅ Models working:")
        print(f"   Sprint: {sprint.goal} with {len(sprint.user_stories)} stories")
        print(f"   Story: {story.title} with {len(story.acceptance_criteria)} acceptance criteria")
        print(f"   Task: {task.title} ({task.status})")
        
        return True
        
    except Exception as e:
        print(f"❌ Models test failed: {e}")
        return False


async def main():
    """Run all functionality tests."""
    print("🚀 Starting Gaggle Functionality Tests")
    print("=" * 60)
    
    # Test models first (no external dependencies)
    models_ok = await test_models()
    if not models_ok:
        print("\n❌ Basic models are broken - cannot continue")
        return False
    
    # Test cost tracking
    cost_ok = await test_cost_tracking()
    if not cost_ok:
        print("\n⚠️  Cost tracking has issues")
    
    # Test agent functionality
    agents_ok = await test_basic_agent_functionality()
    if not agents_ok:
        print("\n❌ Agent functionality is broken")
        return False
    
    print("\n" + "=" * 60)
    print("🎯 SUMMARY:")
    print(f"   Models: {'✅ Working' if models_ok else '❌ Broken'}")
    print(f"   Cost Tracking: {'✅ Working' if cost_ok else '❌ Broken'}")
    print(f"   Agents: {'✅ Working' if agents_ok else '❌ Broken'}")
    
    if models_ok and cost_ok and agents_ok:
        print("\n🎉 All core functionality is working!")
        return True
    else:
        print("\n❌ Some functionality is broken - see issues above")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)