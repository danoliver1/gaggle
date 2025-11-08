"""Pytest configuration and shared fixtures for Gaggle tests."""

import asyncio
import os
from datetime import datetime, timedelta

import pytest

# Import models for fixtures
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
