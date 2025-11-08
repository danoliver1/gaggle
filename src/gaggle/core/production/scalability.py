"""Scalability features for multiple simultaneous sprints."""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ...config.models import AgentRole
from ...models import (
    Sprint,
)
from ..coordination.adaptive_planning import AdaptiveSprintPlanner

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Types of system resources."""

    AGENT_INSTANCE = "agent_instance"
    MEMORY = "memory"
    CPU = "cpu"
    NETWORK = "network"
    STORAGE = "storage"
    API_QUOTA = "api_quota"


class LoadBalancingStrategy(Enum):
    """Load balancing strategies."""

    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    WEIGHTED = "weighted"
    AFFINITY = "affinity"
    RANDOM = "random"


class ScalingTrigger(Enum):
    """Triggers for auto-scaling."""

    CPU_UTILIZATION = "cpu_utilization"
    MEMORY_UTILIZATION = "memory_utilization"
    QUEUE_LENGTH = "queue_length"
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"


@dataclass
class ResourceLimit:
    """Resource limit definition."""

    resource_type: ResourceType
    max_value: float
    unit: str

    # Scaling behavior
    scale_up_threshold: float = 0.8  # 80% utilization
    scale_down_threshold: float = 0.4  # 40% utilization

    def is_at_capacity(self, current_usage: float) -> bool:
        """Check if resource is at capacity."""
        utilization = current_usage / self.max_value
        return utilization >= self.scale_up_threshold

    def can_scale_down(self, current_usage: float) -> bool:
        """Check if resource can scale down."""
        utilization = current_usage / self.max_value
        return utilization <= self.scale_down_threshold


@dataclass
class AgentInstance:
    """Individual agent instance for scaling."""

    instance_id: str
    agent_role: AgentRole

    # Capacity
    max_concurrent_tasks: int = 3
    current_task_count: int = 0

    # State
    status: str = "available"  # available, busy, maintenance, error
    created_at: datetime = field(default_factory=datetime.now)

    # Performance
    tasks_completed: int = 0
    average_task_duration: float = 0.0
    error_count: int = 0

    # Resource usage
    memory_mb: float = 0.0
    cpu_percent: float = 0.0

    def available_capacity(self) -> int:
        """Get available task capacity."""
        return max(0, self.max_concurrent_tasks - self.current_task_count)

    def utilization_percent(self) -> float:
        """Get current utilization percentage."""
        return (self.current_task_count / self.max_concurrent_tasks) * 100

    def can_accept_task(self) -> bool:
        """Check if instance can accept new task."""
        return (
            self.status == "available"
            and self.current_task_count < self.max_concurrent_tasks
        )


@dataclass
class SprintCluster:
    """Cluster of related sprints for resource sharing."""

    cluster_id: str
    name: str

    # Sprints
    sprint_ids: set[str] = field(default_factory=set)

    # Resource allocation
    allocated_agents: dict[AgentRole, list[AgentInstance]] = field(
        default_factory=lambda: defaultdict(list)
    )
    resource_limits: dict[ResourceType, ResourceLimit] = field(default_factory=dict)

    # Load balancing
    load_balancing_strategy: LoadBalancingStrategy = LoadBalancingStrategy.LEAST_LOADED

    # Scaling
    auto_scaling_enabled: bool = True
    min_agents_per_role: dict[AgentRole, int] = field(
        default_factory=lambda: defaultdict(lambda: 1)
    )
    max_agents_per_role: dict[AgentRole, int] = field(
        default_factory=lambda: defaultdict(lambda: 10)
    )

    def total_agent_count(self) -> int:
        """Get total number of agents in cluster."""
        return sum(len(agents) for agents in self.allocated_agents.values())

    def get_utilization(self, role: AgentRole) -> float:
        """Get utilization for specific agent role."""
        agents = self.allocated_agents.get(role, [])
        if not agents:
            return 0.0

        total_capacity = sum(agent.max_concurrent_tasks for agent in agents)
        current_load = sum(agent.current_task_count for agent in agents)

        return (current_load / total_capacity) * 100 if total_capacity > 0 else 0.0


class ResourceManager:
    """Manages system resources across multiple sprints."""

    def __init__(self):
        self.global_limits: dict[ResourceType, ResourceLimit] = {}
        self.current_usage: dict[ResourceType, float] = defaultdict(float)

        # Agent pool management
        self.agent_pool: dict[AgentRole, list[AgentInstance]] = defaultdict(list)
        self.agent_assignments: dict[str, str] = {}  # instance_id -> sprint_id

        # Initialize default limits
        self._set_default_limits()

    def _set_default_limits(self) -> None:
        """Set default resource limits."""
        self.global_limits = {
            ResourceType.AGENT_INSTANCE: ResourceLimit(
                resource_type=ResourceType.AGENT_INSTANCE,
                max_value=100.0,  # Max 100 agent instances
                unit="instances",
            ),
            ResourceType.MEMORY: ResourceLimit(
                resource_type=ResourceType.MEMORY, max_value=16384.0, unit="MB"  # 16GB
            ),
            ResourceType.CPU: ResourceLimit(
                resource_type=ResourceType.CPU,
                max_value=80.0,  # 80% CPU
                unit="percent",
            ),
            ResourceType.API_QUOTA: ResourceLimit(
                resource_type=ResourceType.API_QUOTA,
                max_value=10000.0,  # 10k requests/hour
                unit="requests/hour",
            ),
        }

    def allocate_resources(
        self, sprint_id: str, requested_agents: dict[AgentRole, int]
    ) -> dict[AgentRole, list[AgentInstance]]:
        """Allocate resources for a sprint."""
        allocated = defaultdict(list)

        for role, count in requested_agents.items():
            available_agents = [
                agent
                for agent in self.agent_pool[role]
                if agent.instance_id not in self.agent_assignments
            ]

            # If not enough available, create new instances
            needed = count - len(available_agents)
            if needed > 0:
                new_agents = self._create_agent_instances(role, needed)
                self.agent_pool[role].extend(new_agents)
                available_agents.extend(new_agents)

            # Assign agents to sprint
            for i in range(min(count, len(available_agents))):
                agent = available_agents[i]
                self.agent_assignments[agent.instance_id] = sprint_id
                allocated[role].append(agent)

        logger.info(
            f"Allocated {sum(len(agents) for agents in allocated.values())} agents to sprint {sprint_id}"
        )
        return dict(allocated)

    def _create_agent_instances(
        self, role: AgentRole, count: int
    ) -> list[AgentInstance]:
        """Create new agent instances."""
        instances = []

        for i in range(count):
            instance = AgentInstance(
                instance_id=f"{role.value}_{datetime.now().isoformat()}_{i}",
                agent_role=role,
                max_concurrent_tasks=self._get_default_capacity(role),
            )
            instances.append(instance)

        return instances

    def _get_default_capacity(self, role: AgentRole) -> int:
        """Get default task capacity for agent role."""
        capacity_map = {
            AgentRole.PRODUCT_OWNER: 2,
            AgentRole.SCRUM_MASTER: 3,
            AgentRole.TECH_LEAD: 4,
            AgentRole.FRONTEND_DEV: 5,
            AgentRole.BACKEND_DEV: 5,
            AgentRole.FULLSTACK_DEV: 4,
            AgentRole.QA_ENGINEER: 6,
        }
        return capacity_map.get(role, 3)

    def release_resources(self, sprint_id: str) -> None:
        """Release resources allocated to a sprint."""
        released_instances = []

        for instance_id, assigned_sprint in list(self.agent_assignments.items()):
            if assigned_sprint == sprint_id:
                released_instances.append(instance_id)
                del self.agent_assignments[instance_id]

        logger.info(
            f"Released {len(released_instances)} agent instances from sprint {sprint_id}"
        )

    def get_resource_utilization(self) -> dict[ResourceType, float]:
        """Get current resource utilization."""
        utilization = {}

        for resource_type, limit in self.global_limits.items():
            current = self.current_usage[resource_type]
            utilization[resource_type] = (current / limit.max_value) * 100

        return utilization

    def can_allocate_sprint(self, requested_agents: dict[AgentRole, int]) -> bool:
        """Check if system can allocate resources for new sprint."""
        total_requested = sum(requested_agents.values())
        current_agents = sum(len(agents) for agents in self.agent_pool.values())

        agent_limit = self.global_limits[ResourceType.AGENT_INSTANCE]
        return (current_agents + total_requested) <= agent_limit.max_value


class LoadBalancer:
    """Load balancer for distributing tasks across agent instances."""

    def __init__(
        self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.LEAST_LOADED
    ):
        self.strategy = strategy
        self.request_counts: dict[str, int] = defaultdict(int)  # Round-robin tracking

    def select_agent(
        self, available_agents: list[AgentInstance], task_context: dict[str, Any] = None
    ) -> AgentInstance | None:
        """Select best agent instance for task."""
        if not available_agents:
            return None

        # Filter to only available agents
        candidates = [agent for agent in available_agents if agent.can_accept_task()]

        if not candidates:
            return None

        if self.strategy == LoadBalancingStrategy.LEAST_LOADED:
            return min(candidates, key=lambda a: a.utilization_percent())

        elif self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            # Simple round-robin based on request count
            agent_id = min(candidates, key=lambda a: self.request_counts[a.instance_id])
            self.request_counts[agent_id.instance_id] += 1
            return agent_id

        elif self.strategy == LoadBalancingStrategy.WEIGHTED:
            # Weight by historical performance
            def weight_score(agent):
                base_score = 1.0 / (agent.utilization_percent() + 1)
                performance_score = 1.0 / (agent.average_task_duration + 1)
                error_penalty = max(0.1, 1.0 - (agent.error_count * 0.1))
                return base_score * performance_score * error_penalty

            return max(candidates, key=weight_score)

        elif self.strategy == LoadBalancingStrategy.AFFINITY:
            # Prefer agents that have worked on similar tasks
            task_context.get("task_type", "") if task_context else ""
            # In a real implementation, would track agent-task type affinity
            return min(candidates, key=lambda a: a.utilization_percent())

        else:  # RANDOM
            import random

            return random.choice(candidates)


class ScalabilityManager:
    """Manages auto-scaling and resource optimization."""

    def __init__(self):
        self.resource_manager = ResourceManager()
        self.load_balancer = LoadBalancer()

        # Scaling configuration
        self.scaling_cooldown_minutes = 5
        self.last_scale_operations: dict[str, datetime] = {}

        # Monitoring
        self.scaling_history: list[dict[str, Any]] = []

    async def evaluate_scaling_needs(
        self, cluster: SprintCluster
    ) -> list[dict[str, Any]]:
        """Evaluate if cluster needs scaling up or down."""
        scaling_actions = []

        for role, agents in cluster.allocated_agents.items():
            if not agents:
                continue

            utilization = cluster.get_utilization(role)
            agent_count = len(agents)

            # Check for scale up
            if (
                utilization > 80
                and agent_count < cluster.max_agents_per_role[role]
                and self._can_scale(cluster.cluster_id, role)
            ):

                scaling_actions.append(
                    {
                        "action": "scale_up",
                        "cluster_id": cluster.cluster_id,
                        "role": role,
                        "current_count": agent_count,
                        "target_count": min(
                            agent_count + 1, cluster.max_agents_per_role[role]
                        ),
                        "reason": f"High utilization: {utilization:.1f}%",
                    }
                )

            # Check for scale down
            elif (
                utilization < 30
                and agent_count > cluster.min_agents_per_role[role]
                and self._can_scale(cluster.cluster_id, role)
            ):

                scaling_actions.append(
                    {
                        "action": "scale_down",
                        "cluster_id": cluster.cluster_id,
                        "role": role,
                        "current_count": agent_count,
                        "target_count": max(
                            agent_count - 1, cluster.min_agents_per_role[role]
                        ),
                        "reason": f"Low utilization: {utilization:.1f}%",
                    }
                )

        return scaling_actions

    def _can_scale(self, cluster_id: str, role: AgentRole) -> bool:
        """Check if scaling operation is allowed (cooldown, etc.)."""
        key = f"{cluster_id}_{role.value}"
        last_scale = self.last_scale_operations.get(key)

        if last_scale:
            time_since = datetime.now() - last_scale
            return time_since.total_seconds() / 60 >= self.scaling_cooldown_minutes

        return True

    async def execute_scaling_action(self, action: dict[str, Any]) -> bool:
        """Execute a scaling action."""
        cluster_id = action["cluster_id"]
        role = action["role"]
        current_count = action["current_count"]
        target_count = action["target_count"]

        try:
            if action["action"] == "scale_up":
                # Create additional agent instances
                needed = target_count - current_count
                new_instances = self.resource_manager._create_agent_instances(
                    role, needed
                )
                self.resource_manager.agent_pool[role].extend(new_instances)

                logger.info(
                    f"Scaled up {role.value} in cluster {cluster_id}: {current_count} -> {target_count}"
                )

            elif action["action"] == "scale_down":
                # Remove excess agent instances
                excess = current_count - target_count
                role_agents = self.resource_manager.agent_pool[role]

                # Find agents with lowest utilization to remove
                candidates = [a for a in role_agents if a.current_task_count == 0]
                to_remove = candidates[:excess]

                for agent in to_remove:
                    self.resource_manager.agent_pool[role].remove(agent)

                logger.info(
                    f"Scaled down {role.value} in cluster {cluster_id}: {current_count} -> {target_count}"
                )

            # Record scaling operation
            self.last_scale_operations[f"{cluster_id}_{role.value}"] = datetime.now()
            self.scaling_history.append(
                {**action, "executed_at": datetime.now(), "success": True}
            )

            return True

        except Exception as e:
            logger.error(f"Failed to execute scaling action: {e}")
            self.scaling_history.append(
                {
                    **action,
                    "executed_at": datetime.now(),
                    "success": False,
                    "error": str(e),
                }
            )
            return False

    def get_scaling_metrics(self) -> dict[str, Any]:
        """Get scaling operation metrics."""
        recent_operations = [
            op
            for op in self.scaling_history
            if (datetime.now() - op["executed_at"]).days < 7
        ]

        successful_ops = len([op for op in recent_operations if op["success"]])

        return {
            "total_operations_7d": len(recent_operations),
            "successful_operations_7d": successful_ops,
            "success_rate": (
                successful_ops / len(recent_operations) * 100
                if recent_operations
                else 0
            ),
            "scale_up_count": len(
                [op for op in recent_operations if op["action"] == "scale_up"]
            ),
            "scale_down_count": len(
                [op for op in recent_operations if op["action"] == "scale_down"]
            ),
            "average_cooldown_minutes": self.scaling_cooldown_minutes,
        }


class SprintOrchestrator:
    """Orchestrates multiple concurrent sprints with resource management."""

    def __init__(self):
        self.scalability_manager = ScalabilityManager()
        self.active_clusters: dict[str, SprintCluster] = {}
        self.sprint_assignments: dict[str, str] = {}  # sprint_id -> cluster_id

        # Orchestration
        self.max_concurrent_sprints = 20
        self.sprint_planners: dict[str, AdaptiveSprintPlanner] = {}

    async def create_sprint_cluster(
        self, cluster_config: dict[str, Any]
    ) -> SprintCluster:
        """Create a new sprint cluster."""
        cluster = SprintCluster(
            cluster_id=cluster_config["cluster_id"],
            name=cluster_config["name"],
            load_balancing_strategy=LoadBalancingStrategy(
                cluster_config.get("load_balancing_strategy", "least_loaded")
            ),
            auto_scaling_enabled=cluster_config.get("auto_scaling_enabled", True),
        )

        # Set resource limits if provided
        if "resource_limits" in cluster_config:
            for resource_type_str, limit_config in cluster_config[
                "resource_limits"
            ].items():
                resource_type = ResourceType(resource_type_str)
                cluster.resource_limits[resource_type] = ResourceLimit(
                    resource_type=resource_type,
                    max_value=limit_config["max_value"],
                    unit=limit_config["unit"],
                    scale_up_threshold=limit_config.get("scale_up_threshold", 0.8),
                    scale_down_threshold=limit_config.get("scale_down_threshold", 0.4),
                )

        self.active_clusters[cluster.cluster_id] = cluster
        logger.info(f"Created sprint cluster: {cluster.cluster_id}")

        return cluster

    async def assign_sprint_to_cluster(
        self, sprint: Sprint, cluster_id: str | None = None
    ) -> str:
        """Assign sprint to a cluster (auto-select if none specified)."""
        if cluster_id and cluster_id not in self.active_clusters:
            raise ValueError(f"Cluster not found: {cluster_id}")

        # Auto-select cluster if not specified
        if not cluster_id:
            cluster_id = self._select_best_cluster(sprint)

        cluster = self.active_clusters[cluster_id]
        cluster.sprint_ids.add(sprint.id)
        self.sprint_assignments[sprint.id] = cluster_id

        # Allocate resources for sprint
        required_agents = self._calculate_required_agents(sprint)
        allocated_agents = self.scalability_manager.resource_manager.allocate_resources(
            sprint.id, required_agents
        )

        # Update cluster allocation
        for role, agents in allocated_agents.items():
            cluster.allocated_agents[role].extend(agents)

        # Create sprint planner
        self.sprint_planners[sprint.id] = AdaptiveSprintPlanner()

        logger.info(f"Assigned sprint {sprint.id} to cluster {cluster_id}")
        return cluster_id

    def _select_best_cluster(self, sprint: Sprint) -> str:
        """Select best cluster for sprint based on current load."""
        if not self.active_clusters:
            # Create default cluster if none exist
            cluster_config = {
                "cluster_id": "default_cluster",
                "name": "Default Sprint Cluster",
                "auto_scaling_enabled": True,
            }
            asyncio.create_task(self.create_sprint_cluster(cluster_config))
            return "default_cluster"

        # Select cluster with lowest utilization
        best_cluster_id = min(
            self.active_clusters.keys(),
            key=lambda cid: sum(
                self.active_clusters[cid].get_utilization(role) for role in AgentRole
            )
            / len(AgentRole),
        )

        return best_cluster_id

    def _calculate_required_agents(self, sprint: Sprint) -> dict[AgentRole, int]:
        """Calculate required agents for sprint based on scope."""
        # Base team composition
        base_team = {
            AgentRole.PRODUCT_OWNER: 1,
            AgentRole.SCRUM_MASTER: 1,
            AgentRole.TECH_LEAD: 1,
            AgentRole.QA_ENGINEER: 1,
        }

        # Scale implementation team based on sprint size
        story_count = (
            len(sprint.user_stories)
            if hasattr(sprint, "user_stories") and sprint.user_stories
            else 3
        )
        complexity_factor = max(1, story_count // 3)  # One dev per 3 stories

        implementation_team = {
            AgentRole.FRONTEND_DEV: min(2, complexity_factor),
            AgentRole.BACKEND_DEV: min(2, complexity_factor),
            AgentRole.FULLSTACK_DEV: max(1, complexity_factor - 2),
        }

        return {**base_team, **implementation_team}

    async def manage_cluster_scaling(self) -> dict[str, Any]:
        """Manage auto-scaling for all clusters."""
        scaling_summary = {
            "clusters_evaluated": 0,
            "scaling_actions_taken": 0,
            "actions": [],
        }

        for cluster in self.active_clusters.values():
            if cluster.auto_scaling_enabled:
                scaling_summary["clusters_evaluated"] += 1

                # Evaluate scaling needs
                scaling_actions = await self.scalability_manager.evaluate_scaling_needs(
                    cluster
                )

                # Execute scaling actions
                for action in scaling_actions:
                    success = await self.scalability_manager.execute_scaling_action(
                        action
                    )
                    if success:
                        scaling_summary["scaling_actions_taken"] += 1
                    scaling_summary["actions"].append({**action, "success": success})

        return scaling_summary

    async def get_orchestration_status(self) -> dict[str, Any]:
        """Get overall orchestration status."""
        total_sprints = len(self.sprint_assignments)
        total_clusters = len(self.active_clusters)

        # Calculate resource utilization
        utilization = (
            self.scalability_manager.resource_manager.get_resource_utilization()
        )

        # Get cluster details
        cluster_details = {}
        for cluster_id, cluster in self.active_clusters.items():
            cluster_details[cluster_id] = {
                "sprint_count": len(cluster.sprint_ids),
                "total_agents": cluster.total_agent_count(),
                "agent_breakdown": {
                    role.value: len(agents)
                    for role, agents in cluster.allocated_agents.items()
                },
                "utilization_by_role": {
                    role.value: cluster.get_utilization(role) for role in AgentRole
                },
            }

        return {
            "total_active_sprints": total_sprints,
            "total_clusters": total_clusters,
            "max_concurrent_sprints": self.max_concurrent_sprints,
            "capacity_utilization": (total_sprints / self.max_concurrent_sprints) * 100,
            "resource_utilization": utilization,
            "clusters": cluster_details,
            "scaling_metrics": self.scalability_manager.get_scaling_metrics(),
        }

    async def shutdown_sprint(self, sprint_id: str) -> bool:
        """Shutdown sprint and release resources."""
        if sprint_id not in self.sprint_assignments:
            return False

        cluster_id = self.sprint_assignments[sprint_id]
        cluster = self.active_clusters[cluster_id]

        # Remove sprint from cluster
        cluster.sprint_ids.discard(sprint_id)
        del self.sprint_assignments[sprint_id]

        # Release resources
        self.scalability_manager.resource_manager.release_resources(sprint_id)

        # Clean up sprint planner
        if sprint_id in self.sprint_planners:
            del self.sprint_planners[sprint_id]

        logger.info(f"Shutdown sprint {sprint_id} from cluster {cluster_id}")
        return True
