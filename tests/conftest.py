"""Pytest configuration and shared fixtures for Gaggle tests."""

import asyncio
import os
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

# Import models for fixtures
from gaggle.agents.base import AgentContext
from gaggle.models.sprint import Sprint
from gaggle.models.story import UserStory
from gaggle.models.task import Task, TaskStatus, TaskType


# Test environment setup
def pytest_configure(config):
    """Configure pytest environment."""
    os.environ["TESTING"] = "true"
    os.environ["GAGGLE_ENV"] = "test"
    os.environ["ANTHROPIC_API_KEY"] = "test_key"
    os.environ["GITHUB_TOKEN"] = "test_token"


# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return Task(
        id="TASK-001",
        title="Implement user authentication",
        description="Create secure user authentication system",
        task_type=TaskType.BACKEND,
        status=TaskStatus.TODO,
        assigned_to="backend_developer",
        estimated_hours=6.0,
        story_id="US-001",
    )


@pytest.fixture
def sample_user_story():
    """Create a sample user story for testing."""
    story = UserStory(
        id="US-001",
        title="User Authentication",
        description="As a user, I want to authenticate securely",
        story_points=8,
    )

    # Add acceptance criteria using the model method
    story.add_acceptance_criteria("User can register with email and password")
    story.add_acceptance_criteria("User can login with valid credentials")

    return story


@pytest.fixture
def sample_sprint(sample_user_story):
    """Create a sample sprint for testing."""
    return Sprint(
        id="SPRINT-001",
        name="Authentication Sprint",
        goal="Implement secure user authentication",
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(weeks=2),
        user_stories=[sample_user_story],
        team_velocity=25,
    )


@pytest.fixture
def agent_context():
    """Create a mock agent context for testing."""
    return AgentContext(sprint_id="TEST-SPRINT-001")


@pytest.fixture
def mock_anthropic_response():
    """Create a mock response from Anthropic API."""
    return {
        "result": "Mock agent analysis response with detailed insights about the requirements.",
        "token_usage": {"input_tokens": 100, "output_tokens": 200},
        "model_id": "claude-3-haiku-20240307",
    }


@pytest.fixture
def sample_user_stories():
    """Create multiple sample user stories for testing."""
    stories = []
    
    for i in range(3):
        story = UserStory(
            id=f"US-00{i+1}",
            title=f"User Story {i+1}",
            description=f"As a user, I want feature {i+1}",
            story_points=3 + i,
        )
        story.add_acceptance_criteria(f"Acceptance criteria {i+1}")
        stories.append(story)
    
    return stories


@pytest.fixture
def sprint(sample_user_stories):
    """Create a sprint fixture for testing."""
    return Sprint(
        id="SPRINT-TEST-001",
        goal="Test sprint goal",
        user_stories=sample_user_stories,
    )
