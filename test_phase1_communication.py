#!/usr/bin/env python3
"""Test Phase 1: Structured Communication Architecture implementation."""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_message_schema_creation():
    """Test creating and validating message schemas."""
    print("🧪 Testing Message Schema Creation...")

    try:
        from gaggle.config.models import AgentRole
        from gaggle.core.communication.messages import (
            SprintPlanningMessage,
            StandupUpdateMessage,
            TaskAssignmentMessage,
        )
        from gaggle.models.task import TaskType

        # Test TaskAssignmentMessage
        task_message = TaskAssignmentMessage(
            sender=AgentRole.TECH_LEAD,
            recipient=AgentRole.FRONTEND_DEV,
            subject="Implement user login form",
            task_id="TASK-001",
            task_title="User Login Form",
            task_description="Create a responsive login form with validation",
            task_type=TaskType.FRONTEND,
            assignee=AgentRole.FRONTEND_DEV,
            estimated_effort=5,
            acceptance_criteria=[
                "Form validates input",
                "Shows error messages",
                "Responsive design",
            ],
        )

        validation = task_message.validate()
        assert (
            validation.is_valid
        ), f"Task message validation failed: {validation.errors}"
        print("   ✅ TaskAssignmentMessage created and validated")

        # Test SprintPlanningMessage
        planning_message = SprintPlanningMessage(
            sender=AgentRole.SCRUM_MASTER,
            subject="Sprint 1 Planning Complete",
            sprint_id="SPRINT-001",
            sprint_goal="Implement user authentication",
            story_ids=["US-001", "US-002"],
            total_story_points=13,
            team_capacity=40,
            capacity_utilization=0.75,
        )

        validation = planning_message.validate()
        assert (
            validation.is_valid
        ), f"Planning message validation failed: {validation.errors}"
        print("   ✅ SprintPlanningMessage created and validated")

        # Test StandupUpdateMessage
        standup_message = StandupUpdateMessage(
            sender=AgentRole.FRONTEND_DEV,
            agent_name="FrontendDev-001",
            completed_yesterday=["TASK-001"],
            planned_today=["TASK-002"],
            hours_worked_yesterday=6.0,
            estimated_hours_today=7.0,
            confidence_level=0.8,
        )

        validation = standup_message.validate()
        assert (
            validation.is_valid
        ), f"Standup message validation failed: {validation.errors}"
        print("   ✅ StandupUpdateMessage created and validated")

        return True

    except Exception as e:
        print(f"   ❌ Message schema test failed: {e}")
        return False


def test_state_machine_creation():
    """Test creating agent state machines."""
    print("\n🧪 Testing Agent State Machines...")

    try:
        from gaggle.config.models import AgentRole
        from gaggle.core.state.machines import (
            AgentState,
            DeveloperStateMachine,
            ProductOwnerStateMachine,
            TechLeadStateMachine,
        )

        # Test ProductOwner state machine
        po_sm = ProductOwnerStateMachine(AgentRole.PRODUCT_OWNER, "po-001")
        assert po_sm.current_state == AgentState.IDLE
        assert po_sm.is_available_for_work()
        print(
            f"   ✅ ProductOwner state machine created (state: {po_sm.current_state.value})"
        )

        # Test state transition
        success = po_sm.transition_to(AgentState.PLANNING, "sprint_planning_started")
        assert success, "State transition failed"
        assert po_sm.current_state == AgentState.PLANNING
        print("   ✅ State transition successful: IDLE -> PLANNING")

        # Test capabilities
        capabilities = po_sm.get_capabilities_for_state(AgentState.PLANNING)
        assert "create_user_stories" in capabilities
        print(
            f"   ✅ Planning state capabilities: {len(capabilities)} actions available"
        )

        # Test TechLead state machine
        tl_sm = TechLeadStateMachine(AgentRole.TECH_LEAD, "tl-001")
        assert tl_sm.current_state == AgentState.IDLE
        print("   ✅ TechLead state machine created")

        # Test Developer state machine
        dev_sm = DeveloperStateMachine(AgentRole.FRONTEND_DEV, "dev-001")
        assert dev_sm.current_state == AgentState.IDLE
        print("   ✅ Developer state machine created")

        return True

    except Exception as e:
        print(f"   ❌ State machine test failed: {e}")
        return False


def test_context_management():
    """Test agent context management."""
    print("\n🧪 Testing Context Management...")

    try:
        from gaggle.config.models import AgentRole
        from gaggle.core.state.context import ContextItem, ContextLevel, ContextManager

        # Create context manager
        context_manager = ContextManager()

        # Create agent context
        agent_context = context_manager.get_or_create_context(
            AgentRole.PRODUCT_OWNER, "po-001"
        )

        assert agent_context.agent_role == AgentRole.PRODUCT_OWNER
        assert agent_context.agent_id == "po-001"
        print(f"   ✅ Agent context created for {agent_context.agent_role.value}")

        # Add context items
        immediate_context = ContextItem(
            id="current-task",
            level=ContextLevel.IMMEDIATE,
            content={"task_id": "TASK-001", "description": "Create user stories"},
            tags={"current", "planning"},
        )

        agent_context.add_context(immediate_context)

        # Retrieve context
        retrieved = agent_context.get_context("current-task", ContextLevel.IMMEDIATE)
        assert retrieved is not None
        assert retrieved.content["task_id"] == "TASK-001"
        print("   ✅ Context item stored and retrieved successfully")

        # Search context
        results = agent_context.search_context("planning")
        assert len(results) > 0
        print(f"   ✅ Context search found {len(results)} items")

        return True

    except Exception as e:
        print(f"   ❌ Context management test failed: {e}")
        return False


async def test_message_bus():
    """Test message bus functionality."""
    print("\n🧪 Testing Message Bus...")

    try:
        from gaggle.config.models import AgentRole
        from gaggle.core.communication.bus import MessageBus, MessageHandler
        from gaggle.core.communication.messages import (
            MessageType,
            TaskAssignmentMessage,
        )
        from gaggle.models.task import TaskType

        # Create message bus
        message_bus = MessageBus()
        await message_bus.start()

        print("   ✅ Message bus started")

        # Create a test handler
        received_messages = []

        async def test_handler(message):
            received_messages.append(message)

        handler = MessageHandler(
            handler_id="test-handler",
            agent_role=AgentRole.FRONTEND_DEV,
            message_types={MessageType.TASK_ASSIGNMENT},
            callback=test_handler,
        )

        # Register handler
        message_bus.register_handler(handler)
        print("   ✅ Message handler registered")

        # Create and send test message
        test_message = TaskAssignmentMessage(
            sender=AgentRole.TECH_LEAD,
            recipient=AgentRole.FRONTEND_DEV,
            task_id="TEST-001",
            task_title="Test Task",
            task_description="Test message delivery",
            task_type=TaskType.FRONTEND,
            assignee=AgentRole.FRONTEND_DEV,
            estimated_effort=1,
        )

        validation = await message_bus.send_message(test_message)
        assert validation.is_valid, f"Message validation failed: {validation.errors}"
        print("   ✅ Test message sent successfully")

        # Give message bus time to process
        await asyncio.sleep(0.2)

        # Check metrics
        metrics = message_bus.get_metrics()
        assert metrics["total_messages"] >= 1
        print(
            f"   ✅ Message bus metrics: {metrics['total_messages']} messages processed"
        )

        await message_bus.stop()
        print("   ✅ Message bus stopped")

        return True

    except Exception as e:
        print(f"   ❌ Message bus test failed: {e}")
        return False


async def test_protocol_validation():
    """Test communication protocol validation."""
    print("\n🧪 Testing Protocol Validation...")

    try:
        from gaggle.config.models import AgentRole
        from gaggle.core.communication.messages import TaskAssignmentMessage
        from gaggle.core.communication.protocols import (
            ProtocolValidator,
        )
        from gaggle.models.task import TaskType

        # Create protocol validator
        validator = ProtocolValidator()

        # Create valid task assignment message
        message = TaskAssignmentMessage(
            sender=AgentRole.TECH_LEAD,  # Valid sender for task assignment
            recipient=AgentRole.FRONTEND_DEV,
            task_id="PROTO-001",
            task_title="Protocol Test Task",
            task_description="Test protocol validation",
            task_type=TaskType.FRONTEND,
            assignee=AgentRole.FRONTEND_DEV,
            estimated_effort=3,
        )

        # Validate message through protocol
        validation = validator.validate_message(message)
        assert validation.is_valid, f"Protocol validation failed: {validation.errors}"
        print("   ✅ Valid message passed protocol validation")

        # Check that protocol was created
        protocols = validator.get_active_protocols()
        assert len(protocols) > 0
        print(f"   ✅ Protocol created: {len(protocols)} active protocols")

        # Get protocol status
        status = validator.get_protocol_status()
        assert len(status) > 0
        print("   ✅ Protocol status retrieved")

        return True

    except Exception as e:
        print(f"   ❌ Protocol validation test failed: {e}")
        return False


async def main():
    """Run all Phase 1 tests."""
    print("🚀 Testing Phase 1: Structured Communication Architecture")
    print("=" * 60)

    tests = [
        ("Message Schema Creation", test_message_schema_creation),
        ("Agent State Machines", test_state_machine_creation),
        ("Context Management", test_context_management),
        ("Message Bus", test_message_bus),
        ("Protocol Validation", test_protocol_validation),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   ❌ Test failed with exception: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 60)
    print("🎯 PHASE 1 TEST SUMMARY:")

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 All Phase 1 tests passed!")
        print("✨ Structured Communication Architecture is working correctly!")
        return True
    else:
        print("\n❌ Some Phase 1 tests failed")
        print("🔧 Phase 1 implementation needs fixes before proceeding to Phase 2")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
