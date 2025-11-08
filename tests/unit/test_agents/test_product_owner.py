"""Tests for Product Owner agent."""

from unittest.mock import patch

import pytest

from gaggle.agents.coordination.product_owner import ProductOwner
from gaggle.models.story import StoryStatus, UserStory


class TestProductOwner:
    """Test cases for Product Owner agent."""

    @pytest.fixture
    def product_owner(self, agent_context):
        """Create a Product Owner instance for testing."""
        return ProductOwner(context=agent_context)

    @pytest.mark.asyncio
    async def test_analyze_requirements(self, product_owner, mock_anthropic_response):
        """Test requirements analysis functionality."""

        # Mock the agent execution
        with patch.object(
            product_owner, "execute", return_value=mock_anthropic_response
        ):

            product_idea = (
                "Build a user management system with authentication and profiles"
            )

            result = await product_owner.analyze_requirements(product_idea)

            # Verify result structure
            assert "product_idea" in result
            assert "analysis" in result
            assert "clarifying_questions" in result
            assert "user_personas" in result
            assert "next_steps" in result

            # Verify content
            assert result["product_idea"] == product_idea
            assert isinstance(result["clarifying_questions"], list)
            assert isinstance(result["user_personas"], list)
            assert isinstance(result["next_steps"], list)

    @pytest.mark.asyncio
    async def test_create_user_stories(self, product_owner, mock_anthropic_response):
        """Test user story creation functionality."""

        with patch.object(
            product_owner, "execute", return_value=mock_anthropic_response
        ):

            product_idea = "Build a task management application"
            clarifications = {
                "Who are the primary users?": "Project managers and team members",
                "What's the main business goal?": "Improve team productivity",
            }

            stories = await product_owner.create_user_stories(
                product_idea, clarifications
            )

            # Verify stories were created
            assert isinstance(stories, list)
            assert len(stories) > 0

            # Verify story structure
            for story in stories:
                assert isinstance(story, UserStory)
                assert story.title
                assert story.description
                assert story.status == StoryStatus.BACKLOG
                assert story.product_owner == product_owner.name
                assert len(story.acceptance_criteria) > 0

    @pytest.mark.asyncio
    async def test_prioritize_backlog(
        self, product_owner, sample_user_stories, mock_anthropic_response
    ):
        """Test backlog prioritization functionality."""

        with patch.object(
            product_owner, "execute", return_value=mock_anthropic_response
        ):

            prioritized_stories = await product_owner.prioritize_backlog(
                sample_user_stories
            )

            # Verify prioritization
            assert isinstance(prioritized_stories, list)
            assert len(prioritized_stories) == len(sample_user_stories)

            # Verify all original stories are included
            original_ids = {story.id for story in sample_user_stories}
            prioritized_ids = {story.id for story in prioritized_stories}
            assert original_ids == prioritized_ids

    @pytest.mark.asyncio
    async def test_review_sprint_deliverables(
        self, product_owner, sample_user_stories, mock_anthropic_response
    ):
        """Test sprint deliverable review functionality."""

        from gaggle.models.sprint import SprintModel

        # Create a mock sprint
        sprint = SprintModel(id="sprint_001", goal="Implement user management features")

        # Mark some acceptance criteria as satisfied
        for story in sample_user_stories:
            for criteria in story.acceptance_criteria[:2]:  # Satisfy first 2 criteria
                criteria.mark_satisfied("QA Engineer")

        with patch.object(
            product_owner, "execute", return_value=mock_anthropic_response
        ):

            review_result = await product_owner.review_sprint_deliverables(
                sprint, sample_user_stories
            )

            # Verify review structure
            assert "sprint_id" in review_result
            assert "review_decisions" in review_result
            assert "overall_assessment" in review_result
            assert "recommendations" in review_result

            # Verify review decisions
            assert len(review_result["review_decisions"]) == len(sample_user_stories)

            for decision in review_result["review_decisions"]:
                assert "story_id" in decision
                assert "story_title" in decision
                assert "accepted" in decision
                assert "feedback" in decision
                assert isinstance(decision["accepted"], bool)

    def test_extract_questions(self, product_owner):
        """Test question extraction from analysis text."""

        analysis_text = """
        Here are the key questions we need to answer:
        - Who are the primary users of this system?
        - What's the expected user volume?
        - Are there any compliance requirements?
        - How will users authenticate?

        Additional considerations include performance and scalability.
        """

        questions = product_owner._extract_questions(analysis_text)

        assert isinstance(questions, list)
        assert len(questions) > 0

        # Verify questions contain actual question marks
        for question in questions:
            if question.strip():  # Skip empty questions
                assert "?" in question

    def test_extract_personas(self, product_owner):
        """Test persona extraction from analysis text."""

        analysis_text = """
        The primary user personas include:
        - Project Manager: Needs oversight and reporting
        - Team Member: Needs task assignment and tracking
        - Administrator: Needs user management capabilities

        Secondary personas might include stakeholders and clients.
        """

        personas = product_owner._extract_personas(analysis_text)

        assert isinstance(personas, list)
        assert len(personas) > 0
