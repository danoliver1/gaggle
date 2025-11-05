"""Token usage tracking and cost calculation."""

from typing import Dict, List, Tuple
from datetime import datetime
from dataclasses import dataclass, field

from ..config.models import AgentRole, get_model_config, calculate_cost


@dataclass
class TokenUsage:
    """Token usage record."""
    agent_role: AgentRole
    input_tokens: int
    output_tokens: int
    cost: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


class TokenCounter:
    """Tracks token usage and costs across agents."""
    
    def __init__(self):
        self.usage_records: List[TokenUsage] = []
        self._totals_by_role: Dict[AgentRole, Tuple[int, int, float]] = {}
    
    def add_usage(self, input_tokens: int, output_tokens: int, role: AgentRole) -> None:
        """Add token usage for an agent role."""
        config = get_model_config(role)
        cost = calculate_cost(input_tokens, output_tokens, config)
        
        usage = TokenUsage(
            agent_role=role,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
        )
        
        self.usage_records.append(usage)
        
        # Update totals
        current = self._totals_by_role.get(role, (0, 0, 0.0))
        self._totals_by_role[role] = (
            current[0] + input_tokens,
            current[1] + output_tokens,
            current[2] + cost,
        )
    
    def get_total_tokens(self) -> int:
        """Get total tokens used across all agents."""
        return sum(
            input_tokens + output_tokens
            for input_tokens, output_tokens, _ in self._totals_by_role.values()
        )
    
    def get_total_cost(self) -> float:
        """Get total cost across all agents."""
        return sum(cost for _, _, cost in self._totals_by_role.values())
    
    def get_usage_by_role(self, role: AgentRole) -> Tuple[int, int, float]:
        """Get usage totals for a specific role."""
        return self._totals_by_role.get(role, (0, 0, 0.0))
    
    def get_cost_breakdown(self) -> Dict[str, Dict[str, float]]:
        """Get cost breakdown by role and model tier."""
        breakdown = {}
        
        for role, (input_tokens, output_tokens, cost) in self._totals_by_role.items():
            config = get_model_config(role)
            breakdown[role.value] = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost": cost,
                "model_tier": config.tier.value,
                "model_id": config.model_id,
            }
        
        return breakdown
    
    def get_efficiency_metrics(self) -> Dict[str, float]:
        """Get efficiency metrics."""
        total_cost = self.get_total_cost()
        total_tokens = self.get_total_tokens()
        
        if not total_tokens:
            return {"avg_cost_per_token": 0.0, "tokens_per_dollar": 0.0}
        
        return {
            "avg_cost_per_token": total_cost / total_tokens,
            "tokens_per_dollar": total_tokens / total_cost if total_cost > 0 else 0.0,
        }
    
    def reset(self) -> None:
        """Reset all usage tracking."""
        self.usage_records.clear()
        self._totals_by_role.clear()
    
    def export_usage_data(self) -> List[Dict[str, any]]:
        """Export usage data for analysis."""
        return [
            {
                "agent_role": record.agent_role.value,
                "input_tokens": record.input_tokens,
                "output_tokens": record.output_tokens,
                "total_tokens": record.input_tokens + record.output_tokens,
                "cost": record.cost,
                "timestamp": record.timestamp.isoformat(),
                "model_tier": get_model_config(record.agent_role).tier.value,
            }
            for record in self.usage_records
        ]