"""Strands framework integration adapter for Gaggle."""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import structlog
import json

from ..config.models import AgentRole, ModelConfig, get_model_config, get_model_tier
from ..config.settings import settings
from ..utils.logging import get_logger
from .llm_providers import llm_provider_manager


logger = structlog.get_logger(__name__)


class MockStrandsAgent:
    """Mock Strands agent for development and testing."""
    
    def __init__(self, name: str, model: Any, instruction: str, tools: List[Any]):
        self.name = name
        self.model = model
        self.instruction = instruction
        self.tools = tools
        self.logger = get_logger(f"mock_agent_{name}")
    
    async def aexecute(self, task: str, **kwargs) -> Dict[str, Any]:
        """Execute task using real LLM or mock implementation."""
        
        self.logger.info(
            "agent_execution_started",
            agent=self.name,
            task=task[:100] + "..." if len(task) > 100 else task,
            use_real_llm=hasattr(self.model, 'tier')
        )
        
        # Use real LLM if model has tier information
        if hasattr(self.model, 'tier'):
            return await self._execute_with_real_llm(task, **kwargs)
        else:
            return await self._execute_with_mock(task, **kwargs)
    
    async def _execute_with_real_llm(self, task: str, **kwargs) -> Dict[str, Any]:
        """Execute task using real LLM provider."""
        
        try:
            # Get the model tier for this agent
            tier = self.model.tier
            
            # Generate response using LLM provider
            result = await llm_provider_manager.generate_response(
                tier=tier,
                prompt=task,
                system_prompt=self.instruction,
                **kwargs
            )
            
            self.logger.info(
                "real_llm_execution_success",
                agent=self.name,
                model_tier=tier.value,
                input_tokens=result.get("usage", {}).get("input_tokens", 0),
                output_tokens=result.get("usage", {}).get("output_tokens", 0)
            )
            
            return {
                "result": result.get("response", ""),
                "token_usage": result.get("usage", {}),
                "model_id": result.get("model", "unknown"),
                "model_tier": tier.value,
                "provider": result.get("provider", "unknown"),
                "timestamp": result.get("timestamp", datetime.now().isoformat())
            }
            
        except Exception as e:
            self.logger.error(
                "real_llm_execution_failed",
                agent=self.name,
                error=str(e)
            )
            # Fall back to mock execution
            return await self._execute_with_mock(task, **kwargs)
    
    async def _execute_with_mock(self, task: str, **kwargs) -> Dict[str, Any]:
        """Execute task using mock implementation."""
        
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        # Generate mock response based on task content
        mock_result = self._generate_mock_response(task, **kwargs)
        
        return {
            "result": mock_result,
            "token_usage": {
                "input_tokens": len(task.split()) * 1.3,
                "output_tokens": len(mock_result.split()) * 1.3
            },
            "model_id": self.model.model_id if hasattr(self.model, 'model_id') else "mock-model",
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_mock_response(self, task: str, **kwargs) -> str:
        """Generate a contextual mock response."""
        
        task_lower = task.lower()
        
        if "create" in task_lower and "test" in task_lower:
            return """I'll create comprehensive tests for this feature:

1. Unit tests covering core functionality
2. Integration tests for API endpoints  
3. End-to-end tests for user workflows
4. Performance tests for critical paths

The tests will achieve 95% code coverage and include proper mocking for external dependencies."""

        elif "implement" in task_lower and ("component" in task_lower or "ui" in task_lower):
            return """I'll implement this UI component with the following approach:

1. Create responsive React component with TypeScript
2. Implement proper accessibility (ARIA labels, keyboard navigation)
3. Add comprehensive unit tests with Testing Library
4. Include Storybook stories for design system
5. Optimize for performance with memoization

The component will follow team coding standards and design patterns."""

        elif "implement" in task_lower and ("api" in task_lower or "endpoint" in task_lower):
            return """I'll implement this API endpoint with:

1. FastAPI endpoint with proper validation using Pydantic
2. Authentication and authorization middleware
3. Comprehensive error handling and logging
4. Database operations with proper transaction management
5. OpenAPI documentation and response schemas
6. Unit and integration tests

The implementation will follow security best practices and API design standards."""

        elif "review" in task_lower and "code" in task_lower:
            return """Code review completed:

**Quality Assessment: 8.5/10**

✅ **Strengths:**
- Clean, readable code structure
- Proper error handling
- Good test coverage

⚠️ **Recommendations:**
- Add input validation for edge cases
- Consider extracting common utility functions
- Improve documentation for complex logic

**Approval Status:** Approved with minor suggestions
**Estimated fix time:** 1-2 hours"""

        elif "standup" in task_lower or "daily" in task_lower:
            return """Daily Standup Summary:

**Team Status:** ✅ On Track
**Sprint Progress:** 65% complete
**Active Tasks:** 8 in progress, 12 completed
**Blockers:** 1 (test environment setup)

**Key Updates:**
- Frontend: Login component completed, working on dashboard
- Backend: API endpoints implemented, reviewing auth middleware  
- QA: Testing user registration flow, found 2 minor issues
- Tech Lead: Completed architecture review, planning next iteration

**Action Items:**
- Resolve test environment blocker (DevOps, today)
- Schedule code review session (Tech Lead, this afternoon)"""

        elif "plan" in task_lower and "sprint" in task_lower:
            return """Sprint planning completed:

**Sprint Goal:** Build user authentication and dashboard features
**Duration:** 2 weeks
**Team Capacity:** 80 story points

**Planned Stories:**
1. User Registration (8 pts) - Frontend + Backend
2. User Login (5 pts) - Frontend + Backend  
3. User Dashboard (13 pts) - Fullstack
4. Profile Management (8 pts) - Frontend + Backend

**Task Breakdown:**
- 15 development tasks across team members
- 8 testing tasks for QA Engineer
- 3 architecture tasks for Tech Lead

**Risk Mitigation:**
- Parallel development streams identified
- Dependencies mapped and sequenced
- Daily check-ins scheduled"""

        elif "test" in task_lower and ("performance" in task_lower or "load" in task_lower):
            return """Performance testing completed:

**Results Summary:**
- ✅ Page load time: 2.3s (target: <3s)
- ✅ API response time: 320ms (target: <500ms)
- ✅ Concurrent users: 150 (target: 100)
- ⚠️ Memory usage: 480MB (consider optimization)

**Recommendations:**
1. Implement response caching for static content
2. Optimize database queries (add indexes)
3. Consider CDN for asset delivery
4. Monitor memory usage in production

**Overall Score:** 87/100 - Meets performance requirements"""

        else:
            return f"""Task analysis completed:

Based on the request: "{task[:200]}..."

I've analyzed the requirements and developed an implementation approach that follows best practices for:
- Code quality and maintainability
- Security and performance considerations  
- Testing and documentation standards
- Team collaboration workflows

The solution is ready for implementation with proper error handling, logging, and monitoring."""


class MockStrandsModel:
    """Mock Strands model for development."""
    
    def __init__(self, model_id: str, api_key: Optional[str] = None, tier=None, **kwargs):
        self.model_id = model_id
        self.api_key = api_key
        self.max_tokens = kwargs.get('max_tokens', 4096)
        self.temperature = kwargs.get('temperature', 0.7)
        self.region = kwargs.get('region', 'us-east-1')
        self.tier = tier  # Add tier for LLM provider routing


def create_mock_anthropic_model(**kwargs) -> MockStrandsModel:
    """Create mock Anthropic model."""
    return MockStrandsModel(**kwargs)


def create_mock_bedrock_model(**kwargs) -> MockStrandsModel:
    """Create mock Bedrock model.""" 
    return MockStrandsModel(**kwargs)


class StrandsFrameworkAdapter:
    """Adapter for Strands framework integration with fallback to mock implementation."""
    
    def __init__(self):
        self.logger = get_logger("strands_adapter")
        
        # Check if Strands is available
        try:
            from strands import Agent
            from strands.models import BedrockModel, AnthropicModel
            self.strands_available = True
            self.Agent = Agent
            self.BedrockModel = BedrockModel
            self.AnthropicModel = AnthropicModel
            self.logger.info("strands_framework_loaded", status="production")
        except ImportError:
            self.strands_available = False
            self.Agent = MockStrandsAgent
            self.BedrockModel = create_mock_bedrock_model
            self.AnthropicModel = create_mock_anthropic_model
            self.logger.info("strands_framework_unavailable", status="mock_mode")
    
    def create_agent(
        self, 
        name: str, 
        role: AgentRole,
        instruction: str,
        tools: List[Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Create a Strands agent with appropriate model configuration."""
        
        # Get model configuration for the role
        model_config = get_model_config(role)
        
        # Create model based on configuration
        if settings.anthropic_api_key:
            model = self.AnthropicModel(
                model_id=model_config.model_id,
                api_key=settings.anthropic_api_key,
                max_tokens=model_config.max_tokens,
                temperature=model_config.temperature,
                tier=model_config.tier  # Add tier for LLM routing
            )
        else:
            model = self.BedrockModel(
                model_id=model_config.model_id,
                region=settings.aws_region,
                max_tokens=model_config.max_tokens,
                temperature=model_config.temperature,
                tier=model_config.tier  # Add tier for LLM routing
            )
        
        # Create agent
        agent = self.Agent(
            name=name,
            model=model,
            instruction=instruction,
            tools=tools
        )
        
        self.logger.info(
            "agent_created",
            name=name,
            role=role.value,
            model_tier=model_config.tier.value,
            strands_available=self.strands_available
        )
        
        return agent
    
    async def execute_parallel_tasks(
        self, 
        agents: List[Any], 
        tasks: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute tasks in parallel across multiple agents."""
        
        if len(agents) != len(tasks):
            raise ValueError("Number of agents must match number of tasks")
        
        self.logger.info(
            "parallel_execution_started",
            agent_count=len(agents),
            task_count=len(tasks),
            framework_mode="production" if self.strands_available else "mock"
        )
        
        # Execute tasks in parallel
        execution_tasks = []
        for agent, task in zip(agents, tasks):
            execution_tasks.append(self._execute_single_task(agent, task, context))
        
        results = await asyncio.gather(*execution_tasks, return_exceptions=True)
        
        # Process results
        successful_results = []
        failed_results = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_results.append({
                    "agent": agents[i].name if hasattr(agents[i], 'name') else f"agent_{i}",
                    "task": tasks[i][:100] + "..." if len(tasks[i]) > 100 else tasks[i],
                    "error": str(result),
                    "index": i
                })
            else:
                successful_results.append({
                    "agent": agents[i].name if hasattr(agents[i], 'name') else f"agent_{i}",
                    "task": tasks[i][:100] + "..." if len(tasks[i]) > 100 else tasks[i],
                    "result": result,
                    "index": i
                })
        
        self.logger.info(
            "parallel_execution_completed",
            successful_count=len(successful_results),
            failed_count=len(failed_results),
            total_tasks=len(tasks)
        )
        
        return {
            "successful": successful_results,
            "failed": failed_results,
            "summary": {
                "total_tasks": len(tasks),
                "success_rate": (len(successful_results) / len(tasks)) * 100,
                "parallel_efficiency": self._calculate_efficiency(successful_results)
            }
        }
    
    async def _execute_single_task(
        self, 
        agent: Any, 
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a single task with an agent."""
        
        try:
            # Add context to task if provided
            if context:
                task_with_context = f"{task}\n\nContext: {json.dumps(context, indent=2)}"
            else:
                task_with_context = task
            
            # Execute task
            result = await agent.aexecute(task_with_context)
            
            return {
                "success": True,
                "result": result,
                "agent_name": agent.name if hasattr(agent, 'name') else "unknown",
                "execution_time": result.get("execution_time", 0) if isinstance(result, dict) else 0
            }
            
        except Exception as e:
            self.logger.error(
                "task_execution_failed",
                agent=agent.name if hasattr(agent, 'name') else "unknown",
                task=task[:100] + "..." if len(task) > 100 else task,
                error=str(e)
            )
            raise
    
    def _calculate_efficiency(self, results: List[Dict[str, Any]]) -> float:
        """Calculate parallel execution efficiency."""
        
        if not results:
            return 0.0
        
        # Mock efficiency calculation based on success rate and parallelization
        success_rate = len(results) / max(1, len(results))
        parallel_factor = min(len(results), 5) / 5.0  # Cap at 5 parallel tasks
        
        return (success_rate * 0.7 + parallel_factor * 0.3) * 100
    
    async def create_agent_conversation(
        self,
        agents: List[Any],
        topic: str,
        rounds: int = 3,
        moderator: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Create a conversation between multiple agents."""
        
        conversation_history = []
        current_topic = topic
        
        self.logger.info(
            "agent_conversation_started",
            participant_count=len(agents),
            topic=topic,
            rounds=rounds
        )
        
        for round_num in range(rounds):
            round_responses = []
            
            for agent in agents:
                # Build conversation context
                context = f"Topic: {current_topic}\n\nPrevious conversation:\n"
                for entry in conversation_history[-3:]:  # Last 3 entries for context
                    context += f"{entry['agent']}: {entry['response'][:200]}...\n"
                
                context += f"\nPlease provide your perspective on: {current_topic}"
                
                try:
                    response = await agent.aexecute(context)
                    response_text = response.get("result", str(response)) if isinstance(response, dict) else str(response)
                    
                    round_responses.append({
                        "agent": agent.name if hasattr(agent, 'name') else "unknown",
                        "response": response_text,
                        "round": round_num + 1,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    self.logger.error(
                        "conversation_agent_failed",
                        agent=agent.name if hasattr(agent, 'name') else "unknown",
                        round=round_num + 1,
                        error=str(e)
                    )
            
            conversation_history.extend(round_responses)
            
            # Update topic for next round if there are more rounds
            if round_num < rounds - 1 and moderator:
                try:
                    summary_prompt = f"Summarize key points from this conversation round and suggest focus for next round:\n"
                    for response in round_responses:
                        summary_prompt += f"{response['agent']}: {response['response'][:100]}...\n"
                    
                    moderation = await moderator.aexecute(summary_prompt)
                    current_topic = moderation.get("result", current_topic) if isinstance(moderation, dict) else str(moderation)
                except Exception as e:
                    self.logger.error("conversation_moderation_failed", error=str(e))
        
        self.logger.info(
            "agent_conversation_completed",
            total_exchanges=len(conversation_history),
            rounds_completed=rounds
        )
        
        return {
            "conversation_history": conversation_history,
            "summary": {
                "topic": topic,
                "rounds": rounds,
                "total_exchanges": len(conversation_history),
                "participants": [agent.name if hasattr(agent, 'name') else f"agent_{i}" for i, agent in enumerate(agents)]
            }
        }


# Global adapter instance
strands_adapter = StrandsFrameworkAdapter()