"""Base agent class and common functionality."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from datetime import datetime
import structlog

from strands import Agent
from strands.models import BedrockModel, AnthropicModel

from ..config.models import AgentRole, ModelConfig, get_model_config
from ..config.settings import settings
from ..utils.logging import get_logger
from ..utils.token_counter import TokenCounter


class AgentContext:
    """Shared context for agents within a sprint."""
    
    def __init__(self, sprint_id: str):
        self.sprint_id = sprint_id
        self.shared_data: Dict[str, Any] = {}
        self.token_counter = TokenCounter()
        self.created_at = datetime.utcnow()
    
    def set(self, key: str, value: Any) -> None:
        """Set shared data."""
        self.shared_data[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get shared data."""
        return self.shared_data.get(key, default)
    
    def increment_tokens(self, input_tokens: int, output_tokens: int, role: AgentRole) -> None:
        """Track token usage for cost calculation."""
        self.token_counter.add_usage(input_tokens, output_tokens, role)


class BaseAgent(ABC):
    """Base class for all Gaggle agents."""
    
    def __init__(
        self,
        role: AgentRole,
        name: Optional[str] = None,
        context: Optional[AgentContext] = None,
    ):
        self.role = role
        self.name = name or self._get_default_name()
        self.context = context
        self.logger = get_logger(self.name)
        
        # Get model configuration for this role
        self.model_config = get_model_config(role)
        
        # Initialize the underlying Strands agent
        self._agent = self._create_strands_agent()
        
        # Tools available to this agent
        self.tools = self._get_tools()
        
        # Performance metrics
        self.task_count = 0
        self.total_tokens_used = 0
        self.total_cost = 0.0
    
    def _get_default_name(self) -> str:
        """Get default name based on role."""
        role_names = {
            AgentRole.PRODUCT_OWNER: "ProductOwner",
            AgentRole.SCRUM_MASTER: "ScrumMaster", 
            AgentRole.TECH_LEAD: "TechLead",
            AgentRole.FRONTEND_DEV: "FrontendDev",
            AgentRole.BACKEND_DEV: "BackendDev",
            AgentRole.FULLSTACK_DEV: "FullstackDev",
            AgentRole.QA_ENGINEER: "QAEngineer",
        }
        return role_names.get(self.role, "Agent")
    
    def _create_strands_agent(self) -> Agent:
        """Create the underlying Strands agent with appropriate model."""
        # Choose model provider based on configuration
        if settings.anthropic_api_key:
            model = AnthropicModel(
                model_id=self.model_config.model_id,
                api_key=settings.anthropic_api_key,
                max_tokens=self.model_config.max_tokens,
                temperature=self.model_config.temperature,
            )
        else:
            model = BedrockModel(
                model_id=self.model_config.model_id,
                region=settings.aws_region,
                max_tokens=self.model_config.max_tokens,
                temperature=self.model_config.temperature,
            )
        
        return Agent(
            name=self.name,
            model=model,
            instruction=self._get_instruction(),
            tools=self._get_tools(),
        )
    
    @abstractmethod
    def _get_instruction(self) -> str:
        """Get the instruction prompt for this agent role."""
        pass
    
    @abstractmethod
    def _get_tools(self) -> List[Any]:
        """Get the tools available to this agent."""
        pass
    
    async def execute(self, task: str, **kwargs) -> Dict[str, Any]:
        """Execute a task with this agent."""
        self.logger.info(
            "agent_task_start",
            agent=self.name,
            role=self.role.value,
            task=task[:100] + "..." if len(task) > 100 else task,
        )
        
        try:
            # Execute the task using the Strands agent
            result = await self._agent.aexecute(task, **kwargs)
            
            # Track token usage if available
            if hasattr(result, 'token_usage'):
                self._track_token_usage(result.token_usage)
            
            self.task_count += 1
            
            self.logger.info(
                "agent_task_complete",
                agent=self.name,
                role=self.role.value,
                task_count=self.task_count,
                total_tokens=self.total_tokens_used,
                total_cost=self.total_cost,
            )
            
            return {
                "result": result,
                "agent": self.name,
                "role": self.role.value,
                "tokens_used": getattr(result, 'token_usage', None),
                "timestamp": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            self.logger.error(
                "agent_task_error",
                agent=self.name,
                role=self.role.value,
                error=str(e),
                task=task[:100] + "..." if len(task) > 100 else task,
            )
            raise
    
    def _track_token_usage(self, token_usage: Dict[str, int]) -> None:
        """Track token usage and calculate costs."""
        input_tokens = token_usage.get('input_tokens', 0)
        output_tokens = token_usage.get('output_tokens', 0)
        
        self.total_tokens_used += input_tokens + output_tokens
        
        # Calculate cost
        cost = (
            input_tokens * self.model_config.cost_per_input_token +
            output_tokens * self.model_config.cost_per_output_token
        )
        self.total_cost += cost
        
        # Update context if available
        if self.context:
            self.context.increment_tokens(input_tokens, output_tokens, self.role)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this agent."""
        return {
            "agent": self.name,
            "role": self.role.value,
            "task_count": self.task_count,
            "total_tokens_used": self.total_tokens_used,
            "total_cost": self.total_cost,
            "avg_tokens_per_task": (
                self.total_tokens_used / self.task_count if self.task_count > 0 else 0
            ),
            "avg_cost_per_task": (
                self.total_cost / self.task_count if self.task_count > 0 else 0
            ),
        }


class CoordinationAgent(BaseAgent):
    """Base class for coordination layer agents (Haiku tier)."""
    
    def __init__(self, role: AgentRole, name: Optional[str] = None, context: Optional[AgentContext] = None):
        super().__init__(role, name, context)


class ArchitectureAgent(BaseAgent):
    """Base class for architecture layer agents (Opus tier)."""
    
    def __init__(self, role: AgentRole, name: Optional[str] = None, context: Optional[AgentContext] = None):
        super().__init__(role, name, context)


class ImplementationAgent(BaseAgent):
    """Base class for implementation layer agents (Sonnet tier)."""
    
    def __init__(self, role: AgentRole, name: Optional[str] = None, context: Optional[AgentContext] = None):
        super().__init__(role, name, context)


class QualityAssuranceAgent(BaseAgent):
    """Base class for quality assurance layer agents (Sonnet tier)."""
    
    def __init__(self, role: AgentRole, name: Optional[str] = None, context: Optional[AgentContext] = None):
        super().__init__(role, name, context)