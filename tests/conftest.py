"""Pytest configuration and shared fixtures for Gaggle tests."""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

# Import models for fixtures
from src.gaggle.models.sprint import Sprint, UserStory, Task, TaskStatus
from src.gaggle.config.models import AgentRole, ModelTier


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
        status=TaskStatus.TODO,
        assigned_to="backend_developer",
        estimated_hours=6,
        priority="high",
        user_story_id="US-001"
    )


@pytest.fixture
def sample_user_story():
    """Create a sample user story for testing."""
    return UserStory(
        id="US-001",
        title="User Authentication",
        description="As a user, I want to authenticate securely",
        acceptance_criteria=[
            "User can register with email and password",
            "User can login with valid credentials"
        ],
        priority="high",
        story_points=8
    )


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
        team_velocity=25
    )