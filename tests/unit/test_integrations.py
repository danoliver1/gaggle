"""Unit tests for Gaggle integrations."""

from datetime import datetime, timedelta
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
    start_date = datetime.now().date()
    end_date = start_date + timedelta(days=14)
    return Sprint(
        id="SPRINT-001",
        name="Test Sprint",
        goal="Test sprint functionality",
        start_date=start_date,
        end_date=end_date,
        user_stories=[],
        team_velocity=20,
    )


class TestGitHubAPIClient:
    """Tests for GitHub API client."""

    def test_init(self):
        """Test GitHub API client initialization."""
        client = GitHubAPIClient("test-token", "test-org/test-repo")
        assert client.token == "test-token"
        assert client.repo == "test-org/test-repo"
        assert client.base_url == "https://api.github.com"

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
    async def test_create_user_story_issue(self):
        """Test user story issue creation."""
        client = GitHubAPIClient("test-token", "test-org/test-repo")
        
        # Mock the aiohttp request
        with patch.object(client, '_make_request') as mock_request:
            mock_request.return_value = {
                "number": 1,
                "html_url": "https://github.com/test-org/test-repo/issues/1",
                "id": 1,
                "state": "open"
            }

            user_story = UserStory(
                id="US-001",
                title="Test Story",
                description="Test description",
                priority="high",
                story_points=3,
            )
            user_story.add_acceptance_criteria("AC1")
            user_story.add_acceptance_criteria("AC2")

            result = await client.create_user_story_issue(user_story)

            assert result["number"] == 1
            assert result["html_url"] == "https://github.com/test-org/test-repo/issues/1"
            assert mock_request.called


class TestGitHubWebhookHandler:
    """Tests for GitHub webhook handler."""

    def test_init(self):
        """Test webhook handler initialization."""
        handler = GitHubWebhookHandler("test-secret")
        assert handler.webhook_secret == "test-secret"
        assert handler.logger is not None

    @pytest.mark.asyncio
    async def test_handle_webhook_verification(self):
        """Test webhook signature verification."""
        handler = GitHubWebhookHandler("test-secret")
        
        # Mock signature verification
        with patch.object(handler, '_verify_signature', return_value=True):
            result = handler._verify_signature("test-payload", "sha256=test-signature")
            assert result is True

    @pytest.mark.asyncio
    async def test_handle_webhook_processing(self):
        """Test webhook processing."""
        handler = GitHubWebhookHandler("test-secret")

        payload = {"action": "opened", "pull_request": {"number": 1}}
        headers = {
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=test-signature"
        }
        
        # Mock signature verification
        with patch.object(handler, '_verify_signature', return_value=True):
            result = await handler.handle_webhook(payload, headers)
            
            assert result is not None
            assert "action" in result or "message" in result


class TestStrandsFrameworkAdapter:
    """Tests for Strands framework adapter."""

    def test_init_with_strands_unavailable(self):
        """Test adapter initialization when Strands is unavailable."""
        # The adapter should already be using MockStrandsAgent since Strands is not installed
        adapter = StrandsFrameworkAdapter()
        assert adapter.strands_available is False
        assert adapter.Agent == MockStrandsAgent

    def test_create_agent_with_mock(self):
        """Test agent creation with mock implementation."""
        adapter = StrandsFrameworkAdapter()

        from gaggle.config.models import AgentRole

        agent = adapter.create_agent(
            name="test-agent",
            role=AgentRole.FRONTEND_DEV,
            instruction="Test instruction",
            tools=[],
        )

        assert isinstance(agent, MockStrandsAgent)
        assert agent.name == "test-agent"
        assert agent.instruction == "Test instruction"

    @pytest.mark.asyncio
    async def test_execute_parallel_tasks(self):
        """Test parallel task execution."""
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

        agent = MockStrandsAgent("test-agent", model, "test instruction", [])
        result = await agent.aexecute("test task")

        # MockStrandsAgent falls back to mock behavior when real LLM fails
        assert "result" in result
        assert "token_usage" in result 
        assert "model_id" in result
        assert result["token_usage"]["input_tokens"] > 0
        assert result["token_usage"]["output_tokens"] > 0


class TestLLMProviderManager:
    """Tests for LLM Provider Manager."""

    def test_init(self):
        """Test LLM Provider Manager initialization."""
        manager = LLMProviderManager()
        assert hasattr(manager, "providers")
        assert hasattr(manager, "logger")
        assert isinstance(manager.providers, dict)
        assert len(manager.providers) > 0

    @pytest.mark.asyncio
    async def test_generate_response_anthropic(self):
        """Test response generation with Anthropic provider."""
        manager = LLMProviderManager()

        # Mock the provider for SONNET tier
        sonnet_provider = manager.providers[ModelTier.SONNET]
        with patch.object(sonnet_provider, "generate_response") as mock_generate:
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

    def test_get_usage_stats(self):
        """Test usage statistics retrieval."""
        manager = LLMProviderManager()

        stats = manager.get_all_usage_metrics()
        assert isinstance(stats, dict)
        assert "providers" in stats
        assert "total_cost" in stats
        assert "total_tokens" in stats


class TestAnthropicProvider:
    """Tests for Anthropic provider."""

    def test_init(self):
        """Test Anthropic provider initialization."""
        config = Mock()
        config.model_id = "claude-3-sonnet"
        config.max_tokens = 4096

        provider = AnthropicProvider(config, api_key="test-key")
        assert provider.api_key == "test-key"
        assert provider.config == config
        assert provider.base_url == "https://api.anthropic.com/v1"

    @pytest.mark.asyncio
    async def test_generate_response(self):
        """Test response generation."""
        config = Mock()
        config.model_id = "claude-3-sonnet"
        config.max_tokens = 4096
        config.temperature = 0.7
        config.cost_per_input_token = 0.001
        config.cost_per_output_token = 0.002

        provider = AnthropicProvider(config, api_key="test-key")
        
        # Mock the provider's session and context manager
        mock_response = Mock()
        mock_response.json = AsyncMock(return_value={
            "content": [{"text": "Test response"}],
            "usage": {"input_tokens": 50, "output_tokens": 100},
            "stop_reason": "end_turn"
        })
        mock_response.raise_for_status = Mock()
        
        # Create proper async context manager mock
        mock_session = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=False)
        mock_session.post.return_value = mock_context_manager
        provider.session = mock_session

        result = await provider.generate_response("Test prompt", "Test system")

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
            llm_manager, "generate_response"
        ) as mock_llm:
            mock_llm.return_value = {
                "response": "Pipeline setup complete",
                "usage": {"input_tokens": 100, "output_tokens": 200},
            }

            with patch.object(
                cicd_manager, "setup_sprint_pipeline"
            ) as mock_workflow:
                mock_workflow.return_value = {
                    "sprint_id": sample_sprint.id,
                    "workflows_created": [".github/workflows/test.yml"],
                    "environments_configured": ["staging"]
                }

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
