"""Unit tests for Gaggle integrations."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from gaggle.config.models import ModelTier
from gaggle.integrations.cicd_pipelines import (
    CICDPipelineManager,
    GitHubActionsPipeline,
    PipelineProvider,
)
from gaggle.integrations.github_api import GitHubAPIClient, GitHubWebhookHandler
from gaggle.integrations.llm_providers import (
    AnthropicProvider,
    LLMProviderManager,
)
from gaggle.integrations.strands_adapter import (
    MockStrandsAgent,
    StrandsFrameworkAdapter,
)
from gaggle.models.sprint import Sprint, UserStory


@pytest.fixture
def mock_github_client():
    """Mock GitHub client."""
    client = Mock()
    client.get_repo = Mock()
    client.get_user = Mock()
    return client


@pytest.fixture
def sample_sprint():
    """Sample sprint for testing."""
    return Sprint(
        id="SPRINT-001",
        name="Test Sprint",
        goal="Test sprint functionality",
        start_date=datetime.now(),
        end_date=datetime.now(),
        user_stories=[],
        team_velocity=20,
    )


class TestGitHubAPIClient:
    """Tests for GitHub API client."""

    def test_init(self):
        """Test GitHub API client initialization."""
        with patch("src.gaggle.integrations.github_api.Github") as mock_github:
            client = GitHubAPIClient("test-token", "test-org", "test-repo")
            assert client.token == "test-token"
            assert client.org_name == "test-org"
            assert client.repo_name == "test-repo"
            mock_github.assert_called_once_with("test-token")

    @pytest.mark.asyncio
    async def test_sync_sprint_with_github(self, sample_sprint, mock_github_client):
        """Test sprint sync with GitHub."""
        with patch(
            "src.gaggle.integrations.github_api.Github", return_value=mock_github_client
        ):
            client = GitHubAPIClient("test-token", "test-org", "test-repo")

            # Mock repository
            mock_repo = Mock()
            mock_repo.create_milestone = Mock(return_value=Mock(number=1))
            mock_github_client.get_repo.return_value = mock_repo

            result = await client.sync_sprint_with_github(sample_sprint)

            assert "milestone" in result
            assert "project_board" in result
            assert mock_repo.create_milestone.called

    @pytest.mark.asyncio
    async def test_create_user_story_issue(self, mock_github_client):
        """Test user story issue creation."""
        with patch(
            "src.gaggle.integrations.github_api.Github", return_value=mock_github_client
        ):
            client = GitHubAPIClient("test-token", "test-org", "test-repo")

            user_story = UserStory(
                id="US-001",
                title="Test Story",
                description="Test description",
                acceptance_criteria=["AC1", "AC2"],
                priority="high",
                story_points=3,
            )

            # Mock repository and issue creation
            mock_repo = Mock()
            mock_issue = Mock(
                number=1, html_url="https://github.com/test/test/issues/1"
            )
            mock_repo.create_issue = Mock(return_value=mock_issue)
            mock_github_client.get_repo.return_value = mock_repo

            result = await client.create_user_story_issue(user_story, "SPRINT-001")

            assert result["issue_number"] == 1
            assert result["issue_url"] == "https://github.com/test/test/issues/1"
            assert mock_repo.create_issue.called


class TestGitHubWebhookHandler:
    """Tests for GitHub webhook handler."""

    def test_init(self):
        """Test webhook handler initialization."""
        handler = GitHubWebhookHandler("test-secret")
        assert handler.webhook_secret == "test-secret"
        assert handler.event_handlers == {}

    def test_register_event_handler(self):
        """Test event handler registration."""
        handler = GitHubWebhookHandler("test-secret")

        async def test_handler(payload):
            return {"processed": True}

        handler.register_event_handler("pull_request", test_handler)

        assert "pull_request" in handler.event_handlers
        assert handler.event_handlers["pull_request"] == test_handler

    @pytest.mark.asyncio
    async def test_process_webhook(self):
        """Test webhook processing."""
        handler = GitHubWebhookHandler("test-secret")

        # Register test handler
        async def test_handler(payload):
            return {"processed": True, "action": payload["action"]}

        handler.register_event_handler("pull_request", test_handler)

        payload = {"action": "opened", "pull_request": {"number": 1}}
        result = await handler.process_webhook("pull_request", payload)

        assert result["processed"] is True
        assert result["action"] == "opened"


class TestStrandsFrameworkAdapter:
    """Tests for Strands framework adapter."""

    def test_init_with_strands_unavailable(self):
        """Test adapter initialization when Strands is unavailable."""
        with patch(
            "src.gaggle.integrations.strands_adapter.Agent", side_effect=ImportError
        ):
            adapter = StrandsFrameworkAdapter()
            assert adapter.strands_available is False
            assert adapter.Agent == MockStrandsAgent

    def test_create_agent_with_mock(self):
        """Test agent creation with mock implementation."""
        with patch(
            "src.gaggle.integrations.strands_adapter.Agent", side_effect=ImportError
        ):
            adapter = StrandsFrameworkAdapter()

            from gaggle.config.models import AgentRole

            agent = adapter.create_agent(
                name="test-agent",
                role=AgentRole.FRONTEND_DEVELOPER,
                instruction="Test instruction",
                tools=[],
            )

            assert isinstance(agent, MockStrandsAgent)
            assert agent.name == "test-agent"
            assert agent.instruction == "Test instruction"

    @pytest.mark.asyncio
    async def test_execute_parallel_tasks(self):
        """Test parallel task execution."""
        with patch(
            "src.gaggle.integrations.strands_adapter.Agent", side_effect=ImportError
        ):
            adapter = StrandsFrameworkAdapter()

            # Create mock agents
            agent1 = Mock()
            agent1.name = "agent1"
            agent1.aexecute = AsyncMock(return_value={"result": "result1"})

            agent2 = Mock()
            agent2.name = "agent2"
            agent2.aexecute = AsyncMock(return_value={"result": "result2"})

            agents = [agent1, agent2]
            tasks = ["task1", "task2"]

            result = await adapter.execute_parallel_tasks(agents, tasks)

            assert "successful" in result
            assert "failed" in result
            assert len(result["successful"]) == 2
            assert len(result["failed"]) == 0


class TestMockStrandsAgent:
    """Tests for Mock Strands agent."""

    def test_init(self):
        """Test Mock Strands agent initialization."""
        model = Mock()
        agent = MockStrandsAgent("test-agent", model, "test instruction", [])

        assert agent.name == "test-agent"
        assert agent.model == model
        assert agent.instruction == "test instruction"
        assert agent.tools == []

    @pytest.mark.asyncio
    async def test_execute_with_mock(self):
        """Test execution with mock implementation."""
        model = Mock()
        agent = MockStrandsAgent("test-agent", model, "test instruction", [])

        result = await agent.aexecute("create test for login component")

        assert "result" in result
        assert "token_usage" in result
        assert "model_id" in result
        assert "comprehensive tests" in result["result"]

    @pytest.mark.asyncio
    async def test_execute_with_real_llm_tier(self):
        """Test execution with real LLM when tier is available."""
        model = Mock()
        model.tier = ModelTier.SONNET

        with patch(
            "src.gaggle.integrations.strands_adapter.llm_provider_manager"
        ) as mock_provider:
            mock_provider.generate_response = AsyncMock(
                return_value={
                    "response": "Real LLM response",
                    "usage": {"input_tokens": 100, "output_tokens": 200},
                    "model": "claude-3-sonnet",
                    "provider": "anthropic",
                }
            )

            agent = MockStrandsAgent("test-agent", model, "test instruction", [])
            result = await agent.aexecute("test task")

            assert result["result"] == "Real LLM response"
            assert result["model_tier"] == "sonnet"
            assert result["provider"] == "anthropic"
            mock_provider.generate_response.assert_called_once()


class TestLLMProviderManager:
    """Tests for LLM Provider Manager."""

    def test_init(self):
        """Test LLM Provider Manager initialization."""
        manager = LLMProviderManager()
        assert hasattr(manager, "anthropic_provider")
        assert hasattr(manager, "aws_bedrock_provider")

    @pytest.mark.asyncio
    async def test_generate_response_anthropic(self):
        """Test response generation with Anthropic provider."""
        manager = LLMProviderManager()

        with patch.object(
            manager.anthropic_provider, "generate_response"
        ) as mock_generate:
            mock_generate.return_value = {
                "response": "Test response",
                "usage": {"input_tokens": 50, "output_tokens": 100},
                "model": "claude-3-sonnet",
            }

            result = await manager.generate_response(
                tier=ModelTier.SONNET,
                prompt="Test prompt",
                system_prompt="Test system prompt",
            )

            assert result["response"] == "Test response"
            assert result["model"] == "claude-3-sonnet"
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_usage_stats(self):
        """Test usage statistics retrieval."""
        manager = LLMProviderManager()

        # Add some mock usage data
        manager.usage_stats = {
            "anthropic": {
                "total_requests": 10,
                "total_tokens": 5000,
                "total_cost_usd": 1.50,
            }
        }

        stats = await manager.get_usage_stats()

        assert "anthropic" in stats
        assert stats["anthropic"]["total_requests"] == 10
        assert stats["anthropic"]["total_cost_usd"] == 1.50


class TestAnthropicProvider:
    """Tests for Anthropic provider."""

    def test_init(self):
        """Test Anthropic provider initialization."""
        with patch("src.gaggle.integrations.llm_providers.anthropic.AsyncAnthropic"):
            provider = AnthropicProvider("test-api-key")
            assert provider.api_key == "test-api-key"

    @pytest.mark.asyncio
    async def test_generate_response(self):
        """Test response generation."""
        with patch(
            "src.gaggle.integrations.llm_providers.anthropic.AsyncAnthropic"
        ) as mock_anthropic:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [Mock(text="Test response")]
            mock_response.usage = Mock(input_tokens=50, output_tokens=100)
            mock_response.model = "claude-3-sonnet-20240229"
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.return_value = mock_client

            provider = AnthropicProvider("test-api-key")
            result = await provider.generate_response(
                model="claude-3-sonnet-20240229",
                prompt="Test prompt",
                system_prompt="Test system",
            )

            assert result["response"] == "Test response"
            assert result["usage"]["input_tokens"] == 50
            assert result["usage"]["output_tokens"] == 100


class TestCICDPipelineManager:
    """Tests for CI/CD Pipeline Manager."""

    def test_init(self):
        """Test CI/CD Pipeline Manager initialization."""
        manager = CICDPipelineManager()
        assert hasattr(manager, "configurations")
        assert hasattr(manager, "executions")
        assert hasattr(manager, "github_actions")

    def test_configure_pipeline(self):
        """Test pipeline configuration."""
        from gaggle.integrations.cicd_pipelines import (
            DeploymentEnvironment,
            PipelineConfiguration,
        )

        manager = CICDPipelineManager()

        config = PipelineConfiguration(
            provider=PipelineProvider.GITHUB_ACTIONS,
            environments=[
                DeploymentEnvironment.STAGING,
                DeploymentEnvironment.PRODUCTION,
            ],
        )

        manager.configure_pipeline("test-project", config)

        assert "test-project" in manager.configurations
        assert manager.configurations["test-project"] == config

    @pytest.mark.asyncio
    async def test_setup_sprint_pipeline(self, sample_sprint):
        """Test sprint pipeline setup."""
        from gaggle.integrations.cicd_pipelines import (
            DeploymentEnvironment,
            PipelineConfiguration,
        )

        manager = CICDPipelineManager()

        # Configure pipeline first
        config = PipelineConfiguration(
            provider=PipelineProvider.GITHUB_ACTIONS,
            environments=[DeploymentEnvironment.STAGING],
        )
        manager.configure_pipeline("default", config)

        # Mock GitHub Actions workflow creation
        with patch.object(
            manager.github_actions, "create_sprint_workflow"
        ) as mock_create:
            mock_create.return_value = ".github/workflows/sprint-test.yml"

            result = await manager.setup_sprint_pipeline(sample_sprint)

            assert result["sprint_id"] == sample_sprint.id
            assert result["provider"] == "github_actions"
            assert len(result["workflows_created"]) == 1
            assert len(result["environments_configured"]) == 1


class TestGitHubActionsPipeline:
    """Tests for GitHub Actions pipeline."""

    def test_init(self):
        """Test GitHub Actions pipeline initialization."""
        pipeline = GitHubActionsPipeline()
        assert hasattr(pipeline, "logger")

    @pytest.mark.asyncio
    async def test_create_sprint_workflow(self, sample_sprint):
        """Test sprint workflow creation."""
        pipeline = GitHubActionsPipeline()

        workflow_path = await pipeline.create_sprint_workflow(sample_sprint)

        assert workflow_path == f".github/workflows/sprint-{sample_sprint.id}.yml"

    @pytest.mark.asyncio
    async def test_trigger_deployment(self, sample_sprint):
        """Test deployment triggering."""
        from gaggle.integrations.cicd_pipelines import DeploymentEnvironment

        pipeline = GitHubActionsPipeline()

        artifacts = {"app": "app.tar.gz", "config": "config.env"}

        execution = await pipeline.trigger_deployment(
            environment=DeploymentEnvironment.STAGING,
            sprint_id=sample_sprint.id,
            artifacts=artifacts,
        )

        assert execution.sprint_id == sample_sprint.id
        assert execution.environment == DeploymentEnvironment.STAGING
        assert execution.artifacts == artifacts


class TestIntegrationFlow:
    """Integration tests between different systems."""

    @pytest.mark.asyncio
    async def test_github_strands_integration(self, sample_sprint):
        """Test integration between GitHub API and Strands adapter."""
        with patch("src.gaggle.integrations.github_api.Github") as mock_github:
            with patch(
                "src.gaggle.integrations.strands_adapter.Agent", side_effect=ImportError
            ):
                # Setup GitHub client
                github_client = GitHubAPIClient("test-token", "test-org", "test-repo")
                mock_repo = Mock()
                mock_github.return_value.get_repo.return_value = mock_repo

                # Setup Strands adapter
                strands_adapter = StrandsFrameworkAdapter()

                # Test workflow
                github_result = await github_client.sync_sprint_with_github(
                    sample_sprint
                )

                agents = []
                tasks = ["analyze requirements", "create implementation plan"]

                strands_result = await strands_adapter.execute_parallel_tasks(
                    agents, tasks
                )

                assert github_result is not None
                assert strands_result is not None

    @pytest.mark.asyncio
    async def test_llm_cicd_integration(self, sample_sprint):
        """Test integration between LLM providers and CI/CD pipelines."""
        # Setup LLM provider
        llm_manager = LLMProviderManager()

        # Setup CI/CD manager
        from gaggle.integrations.cicd_pipelines import (
            DeploymentEnvironment,
            PipelineConfiguration,
        )

        cicd_manager = CICDPipelineManager()
        config = PipelineConfiguration(
            provider=PipelineProvider.GITHUB_ACTIONS,
            environments=[DeploymentEnvironment.STAGING],
        )
        cicd_manager.configure_pipeline("default", config)

        # Test workflow
        with patch.object(
            llm_manager.anthropic_provider, "generate_response"
        ) as mock_llm:
            mock_llm.return_value = {
                "response": "Pipeline setup complete",
                "usage": {"input_tokens": 100, "output_tokens": 200},
            }

            with patch.object(
                cicd_manager.github_actions, "create_sprint_workflow"
            ) as mock_workflow:
                mock_workflow.return_value = ".github/workflows/test.yml"

                # Generate LLM response for pipeline setup
                llm_result = await llm_manager.generate_response(
                    tier=ModelTier.SONNET,
                    prompt="Setup CI/CD pipeline",
                    system_prompt="You are a DevOps engineer",
                )

                # Setup sprint pipeline
                cicd_result = await cicd_manager.setup_sprint_pipeline(sample_sprint)

                assert llm_result["response"] == "Pipeline setup complete"
                assert cicd_result["sprint_id"] == sample_sprint.id
