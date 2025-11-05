"""Model configuration for different agent roles."""

from enum import Enum
from typing import Dict, Any
from pydantic import BaseModel


class ModelTier(str, Enum):
    """Model tiers for different agent roles."""
    HAIKU = "haiku"    # Coordination & facilitation
    SONNET = "sonnet"  # Implementation & testing  
    OPUS = "opus"      # Architecture & review


class AgentRole(str, Enum):
    """Agent roles in the Scrum team."""
    PRODUCT_OWNER = "product_owner"
    SCRUM_MASTER = "scrum_master"
    TECH_LEAD = "tech_lead"
    FRONTEND_DEV = "frontend_dev"
    BACKEND_DEV = "backend_dev"
    FULLSTACK_DEV = "fullstack_dev"
    QA_ENGINEER = "qa_engineer"


class ModelConfig(BaseModel):
    """Configuration for a specific model."""
    tier: ModelTier
    model_id: str
    max_tokens: int = 4096
    temperature: float = 0.7
    cost_per_input_token: float = 0.0
    cost_per_output_token: float = 0.0


# Model tier to agent role mapping
ROLE_TO_TIER: Dict[AgentRole, ModelTier] = {
    # Coordination Layer (Cheap - Haiku)
    AgentRole.PRODUCT_OWNER: ModelTier.HAIKU,
    AgentRole.SCRUM_MASTER: ModelTier.HAIKU,
    
    # Architecture & Review Layer (Expensive - Opus)
    AgentRole.TECH_LEAD: ModelTier.OPUS,
    
    # Implementation Layer (Mid-tier - Sonnet)
    AgentRole.FRONTEND_DEV: ModelTier.SONNET,
    AgentRole.BACKEND_DEV: ModelTier.SONNET,
    AgentRole.FULLSTACK_DEV: ModelTier.SONNET,
    
    # Quality Assurance Layer (Mid-tier - Sonnet)
    AgentRole.QA_ENGINEER: ModelTier.SONNET,
}

# Default model configurations
DEFAULT_MODEL_CONFIGS: Dict[ModelTier, ModelConfig] = {
    ModelTier.HAIKU: ModelConfig(
        tier=ModelTier.HAIKU,
        model_id="claude-3-haiku-20240307",
        max_tokens=4096,
        temperature=0.3,  # Lower temperature for coordination tasks
        cost_per_input_token=0.00025,
        cost_per_output_token=0.00125,
    ),
    ModelTier.SONNET: ModelConfig(
        tier=ModelTier.SONNET,
        model_id="claude-3-5-sonnet-20241022",
        max_tokens=8192,
        temperature=0.7,  # Balanced for implementation
        cost_per_input_token=0.003,
        cost_per_output_token=0.015,
    ),
    ModelTier.OPUS: ModelConfig(
        tier=ModelTier.OPUS,
        model_id="claude-3-opus-20240229",
        max_tokens=4096,
        temperature=0.5,  # Controlled for architecture decisions
        cost_per_input_token=0.015,
        cost_per_output_token=0.075,
    ),
}


def get_model_config(role: AgentRole) -> ModelConfig:
    """Get model configuration for a specific agent role."""
    tier = ROLE_TO_TIER[role]
    return DEFAULT_MODEL_CONFIGS[tier]


def get_model_tier(role: AgentRole) -> ModelTier:
    """Get model tier for a specific agent role."""
    return ROLE_TO_TIER[role]


def calculate_cost(input_tokens: int, output_tokens: int, config: ModelConfig) -> float:
    """Calculate cost for token usage with a specific model config."""
    input_cost = input_tokens * config.cost_per_input_token
    output_cost = output_tokens * config.cost_per_output_token
    return input_cost + output_cost