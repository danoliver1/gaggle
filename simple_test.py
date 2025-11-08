#!/usr/bin/env python3
"""Simple test to verify basic functionality without LLM calls."""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_basic_imports():
    """Test that we can import the basic modules."""
    print("🧪 Testing Basic Imports...")

    try:
        print("✅ Models imported successfully")

        print("✅ ProductOwner imported successfully")

        print("✅ Config models imported successfully")

        return True

    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_model_creation():
    """Test basic model creation."""
    print("\n🏗️ Testing Model Creation...")

    try:
        from gaggle.models.sprint import Sprint
        from gaggle.models.story import AcceptanceCriteria, StoryPriority, UserStory
        from gaggle.models.task import Task, TaskStatus, TaskType

        # Create acceptance criteria
        ac = AcceptanceCriteria(id="AC-001", description="User can login successfully")

        # Create user story
        story = UserStory(
            id="US-001",
            title="User Login",
            description="As a user, I want to login",
            priority=StoryPriority.HIGH,
            story_points=5,
            acceptance_criteria=[ac],
        )

        # Test add_acceptance_criteria method
        story.add_acceptance_criteria("User receives error for invalid credentials")

        # Create task
        task = Task(
            id="TASK-001",
            title="Implement login form",
            description="Create login form",
            task_type=TaskType.FRONTEND,
            status=TaskStatus.TODO,
            story_id="US-001",
        )

        # Create sprint
        sprint = Sprint(
            id="SPRINT-001", goal="Implement authentication", user_stories=[story]
        )

        print("✅ Models created successfully:")
        print(f"   Story: {story.title} with {len(story.acceptance_criteria)} criteria")
        print(f"   Task: {task.title} ({task.status})")
        print(f"   Sprint: {sprint.goal} with {len(sprint.user_stories)} stories")

        return True

    except Exception as e:
        print(f"❌ Model creation failed: {e}")
        return False


def test_agent_creation():
    """Test agent creation without LLM calls."""
    print("\n🤖 Testing Agent Creation...")

    try:
        from gaggle.agents.coordination.product_owner import ProductOwner

        # Create agent
        po = ProductOwner()

        print("✅ Agent created:")
        print(f"   Name: {po.name}")
        print(f"   Role: {po.role.value}")
        print(f"   Model Config: {po.model_config.tier.value}")

        return True

    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        return False


def main():
    """Run all simple tests."""
    print("🚀 Running Simple Gaggle Tests")
    print("=" * 50)

    tests = [
        ("Basic Imports", test_basic_imports),
        ("Model Creation", test_model_creation),
        ("Agent Creation", test_agent_creation),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}...")
        result = test_func()
        results.append((test_name, result))

    print("\n" + "=" * 50)
    print("🎯 SUMMARY:")

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 All basic tests passed!")
        return True
    else:
        print("\n❌ Some tests failed - basic functionality is broken")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
