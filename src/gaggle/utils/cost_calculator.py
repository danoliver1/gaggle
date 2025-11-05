"""Cost calculation and optimization utilities."""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from ..config.models import AgentRole, ModelTier, get_model_config, calculate_cost


class OptimizationStrategy(Enum):
    """Cost optimization strategies."""
    MINIMIZE_COST = "minimize_cost"
    MINIMIZE_TIME = "minimize_time"
    BALANCED = "balanced"


@dataclass
class TaskEstimate:
    """Estimate for a specific task."""
    task_id: str
    estimated_input_tokens: int
    estimated_output_tokens: int
    complexity: str  # "low", "medium", "high"
    can_parallelize: bool = True
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class AgentAllocation:
    """Allocation of tasks to agents."""
    agent_role: AgentRole
    tasks: List[TaskEstimate]
    estimated_cost: float
    estimated_time: float


class CostCalculator:
    """Calculates costs and optimizes task allocation."""
    
    def __init__(self):
        self.model_configs = {
            role: get_model_config(role) for role in AgentRole
        }
    
    def estimate_task_cost(
        self, 
        task: TaskEstimate, 
        agent_role: AgentRole
    ) -> float:
        """Estimate cost for a task with a specific agent role."""
        config = self.model_configs[agent_role]
        return calculate_cost(
            task.estimated_input_tokens,
            task.estimated_output_tokens,
            config
        )
    
    def estimate_task_time(
        self, 
        task: TaskEstimate, 
        agent_role: AgentRole
    ) -> float:
        """Estimate execution time for a task (simplified model)."""
        # Base time estimates by model tier (in minutes)
        base_times = {
            ModelTier.HAIKU: 2.0,   # Fast coordination tasks
            ModelTier.SONNET: 5.0,  # Implementation tasks
            ModelTier.OPUS: 8.0,    # Complex architecture tasks
        }
        
        config = self.model_configs[agent_role]
        base_time = base_times[config.tier]
        
        # Adjust by complexity
        complexity_multipliers = {
            "low": 0.5,
            "medium": 1.0,
            "high": 2.0,
        }
        
        multiplier = complexity_multipliers.get(task.complexity, 1.0)
        
        # Adjust by token count (rough approximation)
        total_tokens = task.estimated_input_tokens + task.estimated_output_tokens
        token_factor = 1 + (total_tokens / 10000)  # +10% per 10k tokens
        
        return base_time * multiplier * token_factor
    
    def optimize_allocation(
        self,
        tasks: List[TaskEstimate],
        available_agents: Dict[AgentRole, int],  # role -> count
        strategy: OptimizationStrategy = OptimizationStrategy.BALANCED
    ) -> List[AgentAllocation]:
        """
        Optimize task allocation across available agents.
        
        Args:
            tasks: List of tasks to allocate
            available_agents: Available agent count by role
            strategy: Optimization strategy
        
        Returns:
            Optimized allocation of tasks to agents
        """
        allocations: List[AgentAllocation] = []
        
        # Initialize allocations for available agents
        for role, count in available_agents.items():
            for i in range(count):
                allocations.append(AgentAllocation(
                    agent_role=role,
                    tasks=[],
                    estimated_cost=0.0,
                    estimated_time=0.0
                ))
        
        # Sort tasks by priority (dependencies first, then by complexity)
        sorted_tasks = self._sort_tasks_by_priority(tasks)
        
        # Allocate tasks based on strategy
        for task in sorted_tasks:
            best_allocation = self._find_best_allocation(
                task, allocations, strategy
            )
            
            if best_allocation:
                best_allocation.tasks.append(task)
                best_allocation.estimated_cost += self.estimate_task_cost(
                    task, best_allocation.agent_role
                )
                
                # For parallel tasks, time is max of current tasks
                # For sequential, time is sum
                task_time = self.estimate_task_time(task, best_allocation.agent_role)
                if task.can_parallelize and best_allocation.tasks:
                    best_allocation.estimated_time = max(
                        best_allocation.estimated_time, task_time
                    )
                else:
                    best_allocation.estimated_time += task_time
        
        return [alloc for alloc in allocations if alloc.tasks]
    
    def _sort_tasks_by_priority(self, tasks: List[TaskEstimate]) -> List[TaskEstimate]:
        """Sort tasks by priority (dependencies first, then complexity)."""
        # Build dependency graph
        task_map = {task.task_id: task for task in tasks}
        
        def dependency_depth(task: TaskEstimate) -> int:
            """Calculate dependency depth for a task."""
            if not task.dependencies:
                return 0
            
            max_depth = 0
            for dep_id in task.dependencies:
                if dep_id in task_map:
                    dep_task = task_map[dep_id]
                    max_depth = max(max_depth, dependency_depth(dep_task) + 1)
            
            return max_depth
        
        # Sort by dependency depth (ascending) then complexity (descending)
        complexity_order = {"high": 3, "medium": 2, "low": 1}
        
        return sorted(
            tasks,
            key=lambda t: (
                dependency_depth(t),
                -complexity_order.get(t.complexity, 1)
            )
        )
    
    def _find_best_allocation(
        self,
        task: TaskEstimate,
        allocations: List[AgentAllocation],
        strategy: OptimizationStrategy
    ) -> Optional[AgentAllocation]:
        """Find the best allocation for a task based on strategy."""
        
        # Filter allocations that can handle this task type
        suitable_allocations = self._filter_suitable_allocations(task, allocations)
        
        if not suitable_allocations:
            return None
        
        if strategy == OptimizationStrategy.MINIMIZE_COST:
            return min(
                suitable_allocations,
                key=lambda a: self.estimate_task_cost(task, a.agent_role)
            )
        
        elif strategy == OptimizationStrategy.MINIMIZE_TIME:
            return min(
                suitable_allocations,
                key=lambda a: a.estimated_time + self.estimate_task_time(task, a.agent_role)
            )
        
        else:  # BALANCED
            def balanced_score(allocation: AgentAllocation) -> float:
                cost = self.estimate_task_cost(task, allocation.agent_role)
                time = allocation.estimated_time + self.estimate_task_time(task, allocation.agent_role)
                
                # Normalize and combine (simple weighted average)
                # This is a simplified scoring - could be more sophisticated
                normalized_cost = cost / 100  # Rough normalization
                normalized_time = time / 60   # Normalize to hours
                
                return 0.6 * normalized_cost + 0.4 * normalized_time
            
            return min(suitable_allocations, key=balanced_score)
    
    def _filter_suitable_allocations(
        self, 
        task: TaskEstimate, 
        allocations: List[AgentAllocation]
    ) -> List[AgentAllocation]:
        """Filter allocations that can handle the given task type."""
        # Simple rules for which agents can handle which tasks
        # This could be more sophisticated based on task metadata
        
        suitable_roles = set()
        
        # All agents can handle basic tasks
        suitable_roles.update([
            AgentRole.FRONTEND_DEV,
            AgentRole.BACKEND_DEV,
            AgentRole.FULLSTACK_DEV,
        ])
        
        # Complex tasks might need Tech Lead
        if task.complexity == "high":
            suitable_roles.add(AgentRole.TECH_LEAD)
        
        # Architecture tasks need Tech Lead
        if "architecture" in task.task_id.lower():
            suitable_roles = {AgentRole.TECH_LEAD}
        
        # Testing tasks can be handled by QA or developers
        if "test" in task.task_id.lower():
            suitable_roles.add(AgentRole.QA_ENGINEER)
        
        return [
            alloc for alloc in allocations 
            if alloc.agent_role in suitable_roles
        ]
    
    def calculate_sprint_metrics(
        self, 
        allocations: List[AgentAllocation]
    ) -> Dict[str, float]:
        """Calculate overall sprint metrics from allocations."""
        total_cost = sum(alloc.estimated_cost for alloc in allocations)
        
        # Sprint time is the maximum time across all parallel tracks
        max_time = max(
            (alloc.estimated_time for alloc in allocations),
            default=0.0
        )
        
        total_tasks = sum(len(alloc.tasks) for alloc in allocations)
        
        return {
            "total_estimated_cost": total_cost,
            "estimated_sprint_time_hours": max_time / 60,
            "total_tasks": total_tasks,
            "avg_cost_per_task": total_cost / total_tasks if total_tasks > 0 else 0,
            "parallelization_efficiency": len(allocations) / max(len(allocations), 1),
        }