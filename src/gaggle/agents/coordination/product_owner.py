"""Product Owner agent implementation."""

import uuid
from typing import Any

from ...config.models import AgentRole
from ...core.communication.messages import AgentMessage, MessageType
from ...models.sprint import SprintModel
from ...models.story import StoryPriority, StoryStatus, UserStory
from ...tools.github_tools import GitHubTool
from ...tools.project_tools import BacklogTool, StoryTemplateTool
from ..base import AgentContext, CoordinationAgent


class ProductOwner(CoordinationAgent):
    """
    Product Owner agent responsible for:
    - Clarifying requirements and asking business questions
    - Writing user stories with clear acceptance criteria
    - Prioritizing backlog based on business value
    - Accepting/rejecting work during sprint review
    """

    def __init__(self, name: str | None = None, context: AgentContext | None = None):
        super().__init__(AgentRole.PRODUCT_OWNER, name, context)

        # Tools specific to Product Owner
        self.backlog_tool = BacklogTool()
        self.story_template_tool = StoryTemplateTool()
        self.github_tool = GitHubTool() if context else None

    def _get_instruction(self) -> str:
        """Get the instruction prompt for the Product Owner."""
        return """You are a Product Owner in an Agile Scrum team. Your responsibilities include:

1. **Requirements Clarification:**
   - Ask clarifying questions about business value and user needs
   - Understand the "why" behind feature requests
   - Identify user personas and their goals

2. **User Story Creation:**
   - Write clear user stories using "As a... I want... So that..." format
   - Define specific, measurable acceptance criteria
   - Ensure stories provide business value

3. **Backlog Management:**
   - Prioritize stories based on business value, risk, and dependencies
   - Maintain a well-groomed product backlog
   - Ensure stories are ready for development

4. **Sprint Review:**
   - Review completed work against acceptance criteria
   - Accept or reject deliverables based on definition of done
   - Provide feedback for improvements

**Communication Style:**
- Ask specific, business-focused questions
- Focus on user value and outcomes
- Be decisive about priorities and acceptance criteria
- Collaborative but maintain product vision

**Key Principles:**
- Business value comes first
- User needs drive decisions
- Clear communication prevents waste
- Iterative improvement through feedback"""

    def _get_tools(self) -> list[Any]:
        """Get tools available to the Product Owner."""
        tools = []
        if hasattr(self, "backlog_tool"):
            tools.append(self.backlog_tool)
        if hasattr(self, "story_template_tool"):
            tools.append(self.story_template_tool)
        if hasattr(self, "github_tool"):
            tools.append(self.github_tool)
        return tools

    async def _process_message(self, message: AgentMessage) -> None:
        """Process incoming messages specific to Product Owner role."""
        if message.message_type == MessageType.REQUIREMENT_ANALYSIS_REQUEST:
            # Handle requirement analysis requests
            await self._handle_requirement_analysis_request(message)
        elif message.message_type == MessageType.STORY_CREATION_REQUEST:
            # Handle story creation requests
            await self._handle_story_creation_request(message)
        elif message.message_type == MessageType.BACKLOG_PRIORITIZATION_REQUEST:
            # Handle backlog prioritization requests
            await self._handle_backlog_prioritization_request(message)
        elif message.message_type == MessageType.SPRINT_REVIEW_REQUEST:
            # Handle sprint review requests
            await self._handle_sprint_review_request(message)
        else:
            self.logger.warning(
                f"Unhandled message type: {message.message_type.value}",
                message_id=message.id,
            )

    async def _handle_requirement_analysis_request(self, message: AgentMessage) -> None:
        """Handle requirement analysis request messages."""
        if "product_idea" in message.data:
            result = await self.analyze_requirements(message.data["product_idea"])
            
            # Send response back
            response = AgentMessage(
                id=str(uuid.uuid4()),
                sender=self.role,
                recipient=message.sender,
                message_type=MessageType.REQUIREMENT_ANALYSIS_RESPONSE,
                data=result,
                correlation_id=message.id,
            )
            await self.send_message(response)

    async def _handle_story_creation_request(self, message: AgentMessage) -> None:
        """Handle story creation request messages."""
        product_idea = message.data.get("product_idea", "")
        clarifications = message.data.get("clarifications", {})
        
        stories = await self.create_user_stories(product_idea, clarifications)
        
        # Convert stories to serializable format
        stories_data = [
            {
                "id": story.id,
                "title": story.title,
                "description": story.description,
                "priority": story.priority,
                "story_points": story.story_points,
                "status": story.status,
            }
            for story in stories
        ]
        
        response = AgentMessage(
            id=str(uuid.uuid4()),
            sender=self.role,
            recipient=message.sender,
            message_type=MessageType.STORY_CREATION_RESPONSE,
            data={"stories": stories_data},
            correlation_id=message.id,
        )
        await self.send_message(response)

    async def _handle_backlog_prioritization_request(self, message: AgentMessage) -> None:
        """Handle backlog prioritization request messages."""
        # This would need story data from the message
        if "stories" in message.data:
            # Convert story data back to UserStory objects
            stories = []
            for story_data in message.data["stories"]:
                story = UserStory(**story_data)
                stories.append(story)
            
            prioritized_stories = await self.prioritize_backlog(stories)
            
            # Convert back to serializable format
            prioritized_data = [
                {
                    "id": story.id,
                    "title": story.title,
                    "priority": story.priority,
                    "story_points": story.story_points,
                }
                for story in prioritized_stories
            ]
            
            response = AgentMessage(
                id=str(uuid.uuid4()),
                sender=self.role,
                recipient=message.sender,
                message_type=MessageType.BACKLOG_PRIORITIZATION_RESPONSE,
                data={"prioritized_stories": prioritized_data},
                correlation_id=message.id,
            )
            await self.send_message(response)

    async def _handle_sprint_review_request(self, message: AgentMessage) -> None:
        """Handle sprint review request messages."""
        # This would need sprint and story data from the message
        sprint_data = message.data.get("sprint", {})
        completed_stories_data = message.data.get("completed_stories", [])
        
        # Convert data back to objects (simplified)
        sprint = SprintModel(**sprint_data)
        completed_stories = [UserStory(**story_data) for story_data in completed_stories_data]
        
        review_result = await self.review_sprint_deliverables(sprint, completed_stories)
        
        response = AgentMessage(
            id=str(uuid.uuid4()),
            sender=self.role,
            recipient=message.sender,
            message_type=MessageType.SPRINT_REVIEW_RESPONSE,
            data=review_result,
            correlation_id=message.id,
        )
        await self.send_message(response)

    async def analyze_requirements(self, product_idea: str) -> dict[str, Any]:
        """Analyze product requirements and ask clarifying questions."""

        analysis_prompt = f"""
        Analyze this product idea and identify key questions that need clarification:

        Product Idea: {product_idea}

        Please provide:
        1. Key clarifying questions about business value
        2. User personas that might benefit
        3. Potential user needs and pain points
        4. High-level feature categories
        5. Success metrics we should consider

        Focus on understanding the "why" behind this product.
        """

        result = await self.execute(analysis_prompt)

        # Parse and structure the analysis
        return {
            "product_idea": product_idea,
            "analysis": result.get("result", ""),
            "clarifying_questions": self._extract_questions(result.get("result", "")),
            "user_personas": self._extract_personas(result.get("result", "")),
            "next_steps": ["Stakeholder interview", "User research", "MVP definition"],
        }

    async def create_user_stories(
        self, product_idea: str, clarifications: dict[str, str] = None
    ) -> list[UserStory]:
        """Create user stories from product requirements."""

        clarifications_text = ""
        if clarifications:
            clarifications_text = "\n\nAdditional Context:\n"
            for question, answer in clarifications.items():
                clarifications_text += f"Q: {question}\nA: {answer}\n"

        story_creation_prompt = f"""
        Create user stories for this product idea:

        Product Idea: {product_idea}
        {clarifications_text}

        For each user story, provide:
        1. Title (brief, descriptive)
        2. Description in "As a [user], I want [goal] so that [benefit]" format
        3. 3-5 specific acceptance criteria
        4. Business value explanation
        5. Priority level (critical/high/medium/low)
        6. Estimated story points (1, 2, 3, 5, 8, 13)

        Focus on:
        - User value and outcomes
        - Testable acceptance criteria
        - Incremental delivery
        - Clear scope boundaries

        Create 5-8 user stories that cover the core functionality.
        """

        result = await self.execute(story_creation_prompt)

        # Parse the result and create UserStory objects
        stories = self._parse_stories_from_result(result.get("result", ""))

        # Log story creation
        self.logger.info(
            "user_stories_created",
            product_idea=product_idea[:50] + "...",
            story_count=len(stories),
            total_story_points=sum(story.story_points for story in stories),
        )

        return stories

    async def prioritize_backlog(self, stories: list[UserStory]) -> list[UserStory]:
        """Prioritize user stories in the backlog."""

        stories_summary = "\n".join(
            [
                f"- {story.title} (Priority: {story.priority}, Points: {story.story_points})"
                for story in stories
            ]
        )

        prioritization_prompt = f"""
        Review and prioritize these user stories for maximum business value:

        Current Stories:
        {stories_summary}

        Consider:
        1. Business value and revenue impact
        2. User impact and urgency
        3. Technical dependencies
        4. Risk and complexity
        5. Market timing

        Provide:
        1. Recommended priority order (1 = highest priority)
        2. Reasoning for priority decisions
        3. Dependencies to consider
        4. Recommended MVP scope (first 3-4 stories)

        Focus on delivering value early and often.
        """

        result = await self.execute(prioritization_prompt)

        # Re-order stories based on the prioritization
        prioritized_stories = self._apply_prioritization(
            stories, result.get("result", "")
        )

        self.logger.info(
            "backlog_prioritized",
            story_count=len(prioritized_stories),
            mvp_stories=len(list(prioritized_stories[:4])),
        )

        return prioritized_stories

    async def review_sprint_deliverables(
        self, sprint: SprintModel, completed_stories: list[UserStory]
    ) -> dict[str, Any]:
        """Review completed sprint deliverables against acceptance criteria."""

        review_summary = []
        for story in completed_stories:
            criteria_status = []
            for criteria in story.acceptance_criteria:
                status = "✅" if criteria.is_satisfied else "❌"
                criteria_status.append(f"{status} {criteria.description}")

            review_summary.append(
                f"""
Story: {story.title}
Status: {story.status}
Acceptance Criteria:
{chr(10).join(criteria_status)}
"""
            )

        review_prompt = f"""
        Review these completed user stories from Sprint {sprint.id}:

        Sprint Goal: {sprint.goal}

        Completed Stories:
        {"".join(review_summary)}

        For each story, determine:
        1. Does it meet all acceptance criteria?
        2. Does it deliver the expected business value?
        3. Is it ready for production release?
        4. Any improvements needed for future stories?

        Provide:
        1. Accept/Reject decision for each story
        2. Overall sprint assessment
        3. Feedback for the development team
        4. Recommendations for next sprint

        Be thorough but constructive in your feedback.
        """

        result = await self.execute(review_prompt)

        # Process review decisions
        review_decisions = self._parse_review_decisions(
            result.get("result", ""), completed_stories
        )

        self.logger.info(
            "sprint_review_completed",
            sprint_id=sprint.id,
            stories_reviewed=len(completed_stories),
            stories_accepted=len([d for d in review_decisions if d["accepted"]]),
            stories_rejected=len([d for d in review_decisions if not d["accepted"]]),
        )

        return {
            "sprint_id": sprint.id,
            "review_decisions": review_decisions,
            "overall_assessment": result.get("result", ""),
            "recommendations": self._extract_recommendations(result.get("result", "")),
        }

    def _extract_questions(self, analysis_text: str) -> list[str]:
        """Extract clarifying questions from analysis text."""
        # Simple parsing - could be more sophisticated
        questions = []
        lines = analysis_text.split("\n")

        for line in lines:
            if "?" in line and (
                "question" in line.lower() or line.strip().startswith("-")
            ):
                question = line.strip().lstrip("- ").strip()
                if question and question not in questions:
                    questions.append(question)

        return questions[:10]  # Limit to 10 questions

    def _extract_personas(self, analysis_text: str) -> list[str]:
        """Extract user personas from analysis text."""
        personas = []
        lines = analysis_text.split("\n")

        for line in lines:
            if "persona" in line.lower() or "user" in line.lower():
                if line.strip().startswith("-") or line.strip().startswith("•"):
                    persona = line.strip().lstrip("- •").strip()
                    if persona and persona not in personas:
                        personas.append(persona)

        return personas[:5]  # Limit to 5 personas

    def _parse_stories_from_result(self, result_text: str) -> list[UserStory]:
        """Parse user stories from the agent's result."""
        stories = []

        # This is a simplified parser - in production, you'd want more robust parsing
        # For now, create some example stories based on common patterns

        story_count = result_text.lower().count("as a") + result_text.lower().count(
            "user story"
        )
        story_count = max(1, min(story_count, 8))  # Between 1-8 stories

        for i in range(story_count):
            story_id = str(uuid.uuid4())

            story = UserStory(
                id=story_id,
                title=f"User Story {i+1}",
                description="As a user, I want to use the system so that I can achieve my goals.",
                priority=StoryPriority.MEDIUM,
                story_points=3.0,
                status=StoryStatus.BACKLOG,
                product_owner=self.name,
            )

            # Add some default acceptance criteria
            story.add_acceptance_criteria("The feature works as described")
            story.add_acceptance_criteria("The interface is user-friendly")
            story.add_acceptance_criteria("The feature is properly tested")

            stories.append(story)

        return stories

    def _apply_prioritization(
        self, stories: list[UserStory], prioritization_result: str
    ) -> list[UserStory]:
        """Apply prioritization logic to stories."""
        # For now, just return stories as-is
        # In production, you'd parse the prioritization result and reorder
        return stories

    def _parse_review_decisions(
        self, review_result: str, stories: list[UserStory]
    ) -> list[dict[str, Any]]:
        """Parse review decisions from the result."""
        decisions = []

        for story in stories:
            # Simple heuristic - in production, parse the actual review text
            accepted = story.get_completion_percentage() >= 80

            decisions.append(
                {
                    "story_id": story.id,
                    "story_title": story.title,
                    "accepted": accepted,
                    "feedback": (
                        "Meets acceptance criteria"
                        if accepted
                        else "Needs additional work"
                    ),
                    "next_steps": (
                        [] if accepted else ["Address remaining acceptance criteria"]
                    ),
                }
            )

        return decisions

    def _extract_recommendations(self, review_result: str) -> list[str]:
        """Extract recommendations from review result."""
        recommendations = [
            "Continue with current development velocity",
            "Focus on code quality and testing",
            "Improve user story clarity in next sprint",
        ]
        return recommendations
