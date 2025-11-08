"""Base agent class and common functionality."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from datetime import datetime
import structlog
import uuid

# Conditional imports for Strands framework
try:
    from strands import Agent
    from strands.models import BedrockModel, AnthropicModel
    STRANDS_AVAILABLE = True
except ImportError:
    # Mock implementation for development
    STRANDS_AVAILABLE = False
    Agent = None
    BedrockModel = None
    AnthropicModel = None

from ..config.models import AgentRole, ModelConfig, get_model_config
from ..config.settings import settings
from ..utils.logging import get_logger
from ..utils.token_counter import TokenCounter
from ..integrations.strands_adapter import strands_adapter
from ..core.communication import MessageBus, MessageHandler, AgentMessage, MessageType
from ..core.state import AgentStateMachine, ContextManager, AgentContext as NewAgentContext


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
    """Base class for all Gaggle agents with structured communication support."""
    
    def __init__(
        self,
        role: AgentRole,
        name: Optional[str] = None,
        context: Optional[AgentContext] = None,
        message_bus: Optional[MessageBus] = None,
        context_manager: Optional[ContextManager] = None,
    ):
        self.role = role
        self.name = name or self._get_default_name()
        self.agent_id = str(uuid.uuid4())
        self.context = context
        self.logger = get_logger(self.name)
        
        # Get model configuration for this role
        self.model_config = get_model_config(role)
        
        # Initialize the underlying Strands agent using adapter
        self._agent = self._create_strands_agent()
        
        # Tools available to this agent
        self.tools = self._get_tools()
        
        # Structured communication setup
        self.message_bus = message_bus
        self.context_manager = context_manager or ContextManager()
        self.agent_context = self.context_manager.get_or_create_context(role, self.agent_id)
        
        # State machine for context-aware coordination
        self.state_machine: Optional[AgentStateMachine] = self._create_state_machine()
        
        # Message handling
        self.message_handlers: List[MessageHandler] = []
        self._setup_message_handlers()
        
        # Performance metrics
        self.task_count = 0
        self.total_tokens_used = 0
        self.total_cost = 0.0
        
        # Initialize communication if message bus is available
        if self.message_bus:
            self._register_with_message_bus()
    
    def _create_state_machine(self) -> Optional[AgentStateMachine]:
        """Create state machine for this agent type."""
        # This will be overridden by specific agent classes
        return None
    
    def _setup_message_handlers(self) -> None:
        """Setup message handlers for this agent."""
        # Base implementation - to be extended by specific agents
        pass
    
    def _register_with_message_bus(self) -> None:
        """Register message handlers with the message bus."""
        if self.message_bus:
            for handler in self.message_handlers:
                self.message_bus.register_handler(handler)
    
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
    
    def _create_strands_agent(self) -> Any:
        """Create the underlying Strands agent using the adapter."""
        return strands_adapter.create_agent(
            name=self.name,
            role=self.role,
            instruction=self._get_instruction(),
            tools=self._get_tools(),
            context={"agent_context": self.context}
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
        
        # Update state machine if available
        if self.state_machine:
            self.state_machine.transition_to(
                self.state_machine.current_state,  # Stay in current state or transition as needed
                "task_started",
                {"task": task}
            )
        
        try:
            # Execute the task using the Strands agent
            result = await self._agent.aexecute(task, **kwargs)
            
            # Track token usage if available
            if hasattr(result, 'token_usage'):
                self._track_token_usage(result.token_usage)
            
            self.task_count += 1
            
            # Update state machine on completion
            if self.state_machine:
                self.state_machine.transition_to(
                    self.state_machine.current_state,
                    "task_completed",
                    {"task": task, "result": result}
                )
            
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
            # Update state machine on error
            if self.state_machine:
                self.state_machine.transition_to(
                    self.state_machine.current_state,
                    "error_occurred",
                    {"error": str(e), "task": task}
                )
            
            self.logger.error(
                "agent_task_error",
                agent=self.name,
                role=self.role.value,
                error=str(e),
                task=task[:100] + "..." if len(task) > 100 else task,
            )
            raise
    
    async def send_message(self, message: AgentMessage) -> bool:
        """Send a message through the message bus."""
        if not self.message_bus:
            self.logger.warning("No message bus available for sending message")
            return False
        
        validation = await self.message_bus.send_message(message)
        
        if not validation.is_valid:
            self.logger.warning(
                f"Message validation failed: {validation.errors}",
                message_id=message.id,
                message_type=message.message_type.value
            )
        
        return validation.is_valid
    
    async def handle_message(self, message: AgentMessage) -> None:
        """Handle an incoming message."""
        self.logger.debug(
            f"Received message: {message.message_type.value}",
            message_id=message.id,
            sender=message.sender.value
        )
        
        # Check if agent can handle this message in current state
        if self.state_machine and not self.state_machine.can_handle_message(message):
            self.logger.warning(
                f"Cannot handle message in current state: {self.state_machine.current_state.value}",
                message_type=message.message_type.value
            )
            return
        
        # Store current message for context
        self.state_machine.current_message = message if self.state_machine else None
        
        # Process message based on type
        await self._process_message(message)
    
    @abstractmethod
    async def _process_message(self, message: AgentMessage) -> None:
        """Process a specific message type. To be implemented by specific agents."""
        pass
    
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
        metrics = {
            "agent": self.name,
            "agent_id": self.agent_id,
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
        
        # Add state machine info if available
        if self.state_machine:
            metrics.update(self.state_machine.get_state_info())
        
        return metrics


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