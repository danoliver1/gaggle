"""Pytest configuration and fixtures for Gaggle tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.gaggle.config.settings import GaggleSettings
from src.gaggle.agents.base import AgentContext
from src.gaggle.models.team import TeamConfiguration
from src.gaggle.models.story import UserStory, StoryPriority, StoryStatus


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    return GaggleSettings(
        github_token="test-token",
        github_repo="test-repo",
        github_org="test-org",
        anthropic_api_key="test-key",
        debug_mode=True,
        dry_run=True
    )


@pytest.fixture
def agent_context():
    """Create a test agent context."""
    return AgentContext("test_sprint")


@pytest.fixture
def team_config():
    """Create a test team configuration."""
    return TeamConfiguration.create_default_team()


@pytest.fixture
def sample_user_story():
    """Create a sample user story for testing."""
    story = UserStory(
        id="story_001",
        title="User Login Feature",
        description="As a user, I want to log in to the system so that I can access my account",
        priority=StoryPriority.HIGH,
        story_points=5.0,
        status=StoryStatus.BACKLOG
    )
    
    # Add acceptance criteria
    story.add_acceptance_criteria("User can enter username and password")
    story.add_acceptance_criteria("System validates credentials")
    story.add_acceptance_criteria("User is redirected to dashboard on success")
    story.add_acceptance_criteria("Error message shown for invalid credentials")
    
    return story


@pytest.fixture
def sample_user_stories():
    """Create multiple sample user stories for testing."""
    stories = []
    
    # Story 1: User Registration
    story1 = UserStory(
        id="story_001",
        title="User Registration",
        description="As a new user, I want to register for an account so that I can access the system",
        priority=StoryPriority.HIGH,
        story_points=3.0,
        status=StoryStatus.BACKLOG
    )
    story1.add_acceptance_criteria("User can enter registration details")
    story1.add_acceptance_criteria("System validates email format")
    story1.add_acceptance_criteria("Account is created successfully")
    stories.append(story1)
    
    # Story 2: User Profile
    story2 = UserStory(
        id="story_002", 
        title="User Profile Management",
        description="As a user, I want to manage my profile information so that I can keep it up to date",
        priority=StoryPriority.MEDIUM,
        story_points=2.0,
        status=StoryStatus.BACKLOG
    )
    story2.add_acceptance_criteria("User can view current profile")
    story2.add_acceptance_criteria("User can edit profile fields")
    story2.add_acceptance_criteria("Changes are saved successfully")
    stories.append(story2)
    
    # Story 3: Dashboard
    story3 = UserStory(
        id="story_003",
        title="User Dashboard",
        description="As a user, I want to see a dashboard with key information so that I can quickly understand my status",
        priority=StoryPriority.MEDIUM,
        story_points=5.0,
        status=StoryStatus.BACKLOG
    )
    story3.add_acceptance_criteria("Dashboard shows user statistics")
    story3.add_acceptance_criteria("Dashboard loads quickly")
    story3.add_acceptance_criteria("Dashboard is responsive")
    stories.append(story3)
    
    return stories


@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API response."""
    return {
        "result": """
        Based on the product requirements, I've analyzed the technical complexity and created a comprehensive plan.
        
        **User Stories Created:**
        1. User Registration System
        2. Authentication and Login
        3. User Profile Management
        4. Dashboard Implementation
        
        **Technical Analysis:**
        - Medium complexity overall
        - Frontend and backend components required
        - Database schema changes needed
        - Testing across multiple components
        
        **Recommendations:**
        - Start with authentication foundation
        - Build reusable form components
        - Implement comprehensive testing
        """,
        "token_usage": {
            "input_tokens": 150,
            "output_tokens": 450
        }
    }


@pytest.fixture
def mock_strands_agent():
    """Mock Strands Agent for testing."""
    mock_agent = AsyncMock()
    mock_agent.aexecute = AsyncMock()
    return mock_agent


@pytest.fixture(autouse=True)
def setup_test_logging():
    """Setup logging for tests."""
    from src.gaggle.utils.logging import setup_logging
    setup_logging()


@pytest.fixture
def mock_github_client():
    """Mock GitHub client for testing."""
    client = MagicMock()
    client.create_issue = AsyncMock(return_value={"number": 123, "html_url": "https://github.com/test/test/issues/123"})
    client.create_pull_request = AsyncMock(return_value={"number": 456, "html_url": "https://github.com/test/test/pull/456"})
    return client