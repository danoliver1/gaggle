"""Unit tests for Gaggle agents."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from gaggle.agents.architecture.tech_lead import TechLead
from gaggle.agents.coordination.product_owner import ProductOwner
from gaggle.agents.coordination.scrum_master import ScrumMaster
from gaggle.agents.implementation.backend_dev import BackendDeveloper
from gaggle.agents.implementation.frontend_dev import FrontendDeveloper
from gaggle.agents.qa.qa_engineer import QAEngineer
from gaggle.config.models import AgentRole
from gaggle.models.sprint import Sprint, Task, TaskStatus, UserStory


@pytest.fixture
def mock_strands_agent():
    """Mock Strands agent for testing."""
    agent = Mock()
    agent.aexecute = AsyncMock(
        return_value={
            "result": "Mock agent response",
            "token_usage": {"input_tokens": 100, "output_tokens": 200},
            "model_id": "mock-model",
        }
    )
    return agent


@pytest.fixture
def sample_user_story():
    """Sample user story for testing."""
    return UserStory(
        id="US-001",
        title="User Registration",
        description="As a user, I want to register for an account",
        acceptance_criteria=[
            "User can enter email and password",
            "System validates input",
            "User receives confirmation email",
        ],
        priority="high",
        story_points=5,
    )


@pytest.fixture
def sample_task():
    """Sample task for testing."""
    return Task(
        id="TASK-001",
        title="Implement registration form",
        description="Create React component for user registration",
        status=TaskStatus.TODO,
        assigned_to="frontend_dev",
        estimated_hours=4,
        user_story_id="US-001",
    )


@pytest.fixture
def sample_sprint(sample_user_story):
    """Sample sprint for testing."""
    return Sprint(
        id="SPRINT-001",
        name="Authentication Sprint",
        goal="Implement user authentication features",
        start_date=datetime.now(),
        end_date=datetime.now(),
        user_stories=[sample_user_story],
        team_velocity=20,
    )


class TestProductOwner:
    """Tests for Product Owner agent."""

    def test_init(self):
        """Test Product Owner initialization."""
        po = ProductOwner()
        assert po.role == AgentRole.PRODUCT_OWNER
        assert po.agent is not None
        assert po.logger is not None

    @pytest.mark.asyncio
    async def test_create_user_stories(self, mock_strands_agent):
        """Test user story creation."""
        po = ProductOwner()
        po.agent = mock_strands_agent

        features = ["User authentication", "Dashboard view"]
        project_context = {"domain": "e-commerce", "users": "customers"}

        result = await po.create_user_stories(features, project_context)

        assert "user_stories" in result
        assert "total_story_points" in result
        assert mock_strands_agent.aexecute.called

    @pytest.mark.asyncio
    async def test_prioritize_backlog(self, mock_strands_agent, sample_user_story):
        """Test backlog prioritization."""
        po = ProductOwner()
        po.agent = mock_strands_agent

        backlog = [sample_user_story]
        criteria = {"business_value": 0.4, "risk": 0.3, "effort": 0.3}

        result = await po.prioritize_backlog(backlog, criteria)

        assert "prioritized_backlog" in result
        assert "prioritization_rationale" in result
        assert mock_strands_agent.aexecute.called

    @pytest.mark.asyncio
    async def test_review_sprint_deliverables(self, mock_strands_agent, sample_sprint):
        """Test sprint deliverable review."""
        po = ProductOwner()
        po.agent = mock_strands_agent

        result = await po.review_sprint_deliverables(sample_sprint)

        assert "review_summary" in result
        assert "acceptance_status" in result
        assert "feedback" in result
        assert mock_strands_agent.aexecute.called


class TestScrumMaster:
    """Tests for Scrum Master agent."""

    def test_init(self):
        """Test Scrum Master initialization."""
        sm = ScrumMaster()
        assert sm.role == AgentRole.SCRUM_MASTER
        assert sm.agent is not None

    @pytest.mark.asyncio
    async def test_plan_sprint(self, mock_strands_agent, sample_user_story):
        """Test sprint planning."""
        sm = ScrumMaster()
        sm.agent = mock_strands_agent

        backlog = [sample_user_story]
        team_velocity = 20

        result = await sm.plan_sprint(backlog, team_velocity)

        assert "sprint_plan" in result
        assert "selected_stories" in result
        assert "capacity_analysis" in result
        assert mock_strands_agent.aexecute.called

    @pytest.mark.asyncio
    async def test_facilitate_daily_standup(self, mock_strands_agent, sample_sprint):
        """Test daily standup facilitation."""
        sm = ScrumMaster()
        sm.agent = mock_strands_agent

        team_updates = {
            "frontend_dev": "Completed login form",
            "backend_dev": "Working on authentication API",
        }

        result = await sm.facilitate_daily_standup(sample_sprint, team_updates)

        assert "standup_summary" in result
        assert "blockers" in result
        assert "action_items" in result
        assert mock_strands_agent.aexecute.called


class TestTechLead:
    """Tests for Tech Lead agent."""

    def test_init(self):
        """Test Tech Lead initialization."""
        tl = TechLead()
        assert tl.role == AgentRole.TECH_LEAD
        assert tl.agent is not None

    @pytest.mark.asyncio
    async def test_analyze_architecture_requirements(
        self, mock_strands_agent, sample_user_story
    ):
        """Test architecture analysis."""
        tl = TechLead()
        tl.agent = mock_strands_agent

        user_stories = [sample_user_story]
        project_context = {"tech_stack": "React/Node.js", "scale": "medium"}

        result = await tl.analyze_architecture_requirements(
            user_stories, project_context
        )

        assert "architecture_requirements" in result
        assert "component_breakdown" in result
        assert "technical_decisions" in result
        assert mock_strands_agent.aexecute.called

    @pytest.mark.asyncio
    async def test_generate_reusable_utilities(self, mock_strands_agent):
        """Test reusable utility generation."""
        tl = TechLead()
        tl.agent = mock_strands_agent

        architecture_requirements = {
            "patterns": ["authentication", "validation"],
            "tech_stack": "React/Node.js",
        }

        result = await tl.generate_reusable_utilities(architecture_requirements)

        assert "utilities" in result
        assert "documentation" in result
        assert mock_strands_agent.aexecute.called

    @pytest.mark.asyncio
    async def test_review_code(self, mock_strands_agent, sample_task):
        """Test code review."""
        tl = TechLead()
        tl.agent = mock_strands_agent

        code_changes = {
            "files": ["src/components/LoginForm.jsx"],
            "diff": "mock diff content",
        }

        result = await tl.review_code(sample_task, code_changes)

        assert "review_status" in result
        assert "feedback" in result
        assert "quality_score" in result
        assert mock_strands_agent.aexecute.called


class TestFrontendDeveloper:
    """Tests for Frontend Developer agent."""

    def test_init(self):
        """Test Frontend Developer initialization."""
        fe_dev = FrontendDeveloper()
        assert fe_dev.role == AgentRole.FRONTEND_DEVELOPER
        assert fe_dev.agent is not None

    @pytest.mark.asyncio
    async def test_implement_ui_component(self, mock_strands_agent, sample_task):
        """Test UI component implementation."""
        fe_dev = FrontendDeveloper()
        fe_dev.agent = mock_strands_agent

        design_specs = {
            "component_type": "form",
            "fields": ["email", "password"],
            "styling": "Material-UI",
        }

        result = await fe_dev.implement_ui_component(sample_task, design_specs)

        assert "component_code" in result
        assert "test_code" in result
        assert "documentation" in result
        assert mock_strands_agent.aexecute.called

    @pytest.mark.asyncio
    async def test_integrate_with_api(self, mock_strands_agent, sample_task):
        """Test API integration."""
        fe_dev = FrontendDeveloper()
        fe_dev.agent = mock_strands_agent

        api_specs = {
            "endpoints": ["/api/auth/login"],
            "methods": ["POST"],
            "schemas": {"login": {"email": "string", "password": "string"}},
        }

        result = await fe_dev.integrate_with_api(sample_task, api_specs)

        assert "integration_code" in result
        assert "error_handling" in result
        assert "api_client" in result
        assert mock_strands_agent.aexecute.called


class TestBackendDeveloper:
    """Tests for Backend Developer agent."""

    def test_init(self):
        """Test Backend Developer initialization."""
        be_dev = BackendDeveloper()
        assert be_dev.role == AgentRole.BACKEND_DEVELOPER
        assert be_dev.agent is not None

    @pytest.mark.asyncio
    async def test_implement_api_endpoint(self, mock_strands_agent, sample_task):
        """Test API endpoint implementation."""
        be_dev = BackendDeveloper()
        be_dev.agent = mock_strands_agent

        endpoint_specs = {
            "path": "/api/auth/login",
            "method": "POST",
            "request_schema": {"email": "string", "password": "string"},
            "response_schema": {"token": "string", "user": "object"},
        }

        result = await be_dev.implement_api_endpoint(sample_task, endpoint_specs)

        assert "endpoint_code" in result
        assert "validation_logic" in result
        assert "test_cases" in result
        assert mock_strands_agent.aexecute.called

    @pytest.mark.asyncio
    async def test_implement_database_layer(self, mock_strands_agent, sample_task):
        """Test database layer implementation."""
        be_dev = BackendDeveloper()
        be_dev.agent = mock_strands_agent

        data_models = {
            "User": {
                "fields": ["id", "email", "password_hash", "created_at"],
                "relationships": [],
            }
        }

        result = await be_dev.implement_database_layer(sample_task, data_models)

        assert "model_code" in result
        assert "migration_scripts" in result
        assert "query_methods" in result
        assert mock_strands_agent.aexecute.called


class TestQAEngineer:
    """Tests for QA Engineer agent."""

    def test_init(self):
        """Test QA Engineer initialization."""
        qa = QAEngineer()
        assert qa.role == AgentRole.QA_ENGINEER
        assert qa.agent is not None

    @pytest.mark.asyncio
    async def test_create_test_plan(self, mock_strands_agent, sample_user_story):
        """Test test plan creation."""
        qa = QAEngineer()
        qa.agent = mock_strands_agent

        implementation_details = {
            "components": ["LoginForm", "AuthAPI"],
            "endpoints": ["/api/auth/login"],
            "user_flows": ["registration", "login"],
        }

        result = await qa.create_test_plan(sample_user_story, implementation_details)

        assert "test_plan" in result
        assert "test_cases" in result
        assert "coverage_analysis" in result
        assert mock_strands_agent.aexecute.called

    @pytest.mark.asyncio
    async def test_execute_functional_testing(self, mock_strands_agent, sample_task):
        """Test functional testing execution."""
        qa = QAEngineer()
        qa.agent = mock_strands_agent

        test_scenarios = [
            {
                "name": "Valid login",
                "steps": ["Enter valid credentials", "Click login"],
            },
            {
                "name": "Invalid login",
                "steps": ["Enter invalid credentials", "Verify error"],
            },
        ]

        result = await qa.execute_functional_testing(sample_task, test_scenarios)

        assert "test_results" in result
        assert "passed_tests" in result
        assert "failed_tests" in result
        assert "defects_found" in result
        assert mock_strands_agent.aexecute.called


class TestAgentIntegration:
    """Integration tests between agents."""

    @pytest.mark.asyncio
    async def test_story_creation_and_breakdown_flow(self, mock_strands_agent):
        """Test flow from story creation to task breakdown."""
        po = ProductOwner()
        tl = TechLead()

        po.agent = mock_strands_agent
        tl.agent = mock_strands_agent

        # Product Owner creates stories
        features = ["User authentication"]
        project_context = {"domain": "web app"}

        po_result = await po.create_user_stories(features, project_context)

        # Tech Lead analyzes and breaks down
        user_stories = po_result.get("user_stories", [])
        arch_result = await tl.analyze_architecture_requirements(
            user_stories, project_context
        )

        assert po_result is not None
        assert arch_result is not None
        assert mock_strands_agent.aexecute.call_count >= 2

    @pytest.mark.asyncio
    async def test_development_and_review_flow(self, mock_strands_agent, sample_task):
        """Test flow from development to code review."""
        fe_dev = FrontendDeveloper()
        tl = TechLead()

        fe_dev.agent = mock_strands_agent
        tl.agent = mock_strands_agent

        # Frontend developer implements
        design_specs = {"component_type": "form"}
        dev_result = await fe_dev.implement_ui_component(sample_task, design_specs)

        # Tech Lead reviews
        code_changes = {"files": ["LoginForm.jsx"], "diff": "mock diff"}
        review_result = await tl.review_code(sample_task, code_changes)

        assert dev_result is not None
        assert review_result is not None
        assert "review_status" in review_result
