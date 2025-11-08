"""Team and agent configuration models."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..config.models import AgentRole, ModelTier


class AgentStatus(str, Enum):
    """Agent status enumeration."""
    AVAILABLE = "available"
    BUSY = "busy"
    BLOCKED = "blocked"
    OFFLINE = "offline"


class TeamMember(BaseModel):
    """Team member (agent) configuration."""

    id: str = Field(..., description="Unique team member identifier")
    name: str = Field(..., description="Display name for the team member")
    role: AgentRole = Field(..., description="Agent role in the team")

    # Status and availability
    status: AgentStatus = Field(AgentStatus.AVAILABLE, description="Current status")
    current_task_id: str | None = None

    # Configuration
    model_tier: ModelTier = Field(..., description="Model tier for this agent")
    max_concurrent_tasks: int = Field(1, description="Maximum concurrent tasks")

    # Performance tracking
    tasks_completed: int = Field(0, description="Total tasks completed")
    total_tokens_used: int = Field(0, description="Total tokens consumed")
    total_cost: float = Field(0.0, description="Total cost incurred")

    # Specializations and capabilities
    specializations: list[str] = Field(default_factory=list, description="Agent specializations")
    tools_enabled: list[str] = Field(default_factory=list, description="Available tools")

    # Time tracking
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(use_enum_values=True)

    @field_validator('id')
    @classmethod
    def validate_id(cls, v):
        """Validate team member ID is not empty."""
        if not v.strip():
            raise ValueError('Team member ID cannot be empty')
        return v.strip()

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate team member name is not empty."""
        if not v.strip():
            raise ValueError('Team member name cannot be empty')
        return v.strip()

    def assign_task(self, task_id: str) -> None:
        """Assign a task to this team member."""
        if self.status != AgentStatus.AVAILABLE:
            raise ValueError(f"Agent {self.name} is not available (status: {self.status})")

        self.current_task_id = task_id
        self.status = AgentStatus.BUSY
        self.last_active_at = datetime.utcnow()

    def complete_task(self, tokens_used: int = 0, cost_incurred: float = 0.0) -> None:
        """Mark current task as completed."""
        if self.status != AgentStatus.BUSY:
            raise ValueError(f"Agent {self.name} is not working on a task")

        self.current_task_id = None
        self.status = AgentStatus.AVAILABLE
        self.tasks_completed += 1
        self.total_tokens_used += tokens_used
        self.total_cost += cost_incurred
        self.last_active_at = datetime.utcnow()

    def block_agent(self, reason: str) -> None:
        """Block the agent."""
        self.status = AgentStatus.BLOCKED
        self.last_active_at = datetime.utcnow()

    def unblock_agent(self) -> None:
        """Unblock the agent."""
        if self.status == AgentStatus.BLOCKED:
            self.status = AgentStatus.AVAILABLE
            self.last_active_at = datetime.utcnow()

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get performance metrics for this team member."""
        avg_tokens_per_task = (
            self.total_tokens_used / self.tasks_completed
            if self.tasks_completed > 0 else 0
        )
        avg_cost_per_task = (
            self.total_cost / self.tasks_completed
            if self.tasks_completed > 0 else 0
        )

        return {
            "member_id": self.id,
            "name": self.name,
            "role": self.role,  # Already a string due to use_enum_values = True
            "tasks_completed": self.tasks_completed,
            "total_tokens_used": self.total_tokens_used,
            "total_cost": self.total_cost,
            "avg_tokens_per_task": avg_tokens_per_task,
            "avg_cost_per_task": avg_cost_per_task,
            "status": self.status,  # Already a string due to use_enum_values = True
            "model_tier": self.model_tier,  # Already a string due to use_enum_values = True
        }


class AgentAssignment(BaseModel):
    """Assignment of tasks to agents for optimization."""

    agent_id: str
    task_ids: list[str] = Field(default_factory=list)
    estimated_workload_hours: float = Field(0.0)
    estimated_cost: float = Field(0.0)
    can_parallelize: bool = Field(True)

    def add_task(self, task_id: str, estimated_hours: float = 0.0, estimated_cost: float = 0.0) -> None:
        """Add a task to this assignment."""
        if task_id not in self.task_ids:
            self.task_ids.append(task_id)
            self.estimated_workload_hours += estimated_hours
            self.estimated_cost += estimated_cost


class TeamConfiguration(BaseModel):
    """Configuration for the entire Gaggle team."""

    id: str = Field(..., description="Unique team configuration identifier")
    name: str = Field(..., description="Team name")

    # Team members
    members: list[TeamMember] = Field(default_factory=list)

    # Team capacity and constraints
    max_parallel_tasks: int = Field(10, description="Maximum parallel tasks for the team")
    sprint_capacity_hours: float = Field(400.0, description="Total sprint capacity in hours")

    # Cost management
    budget_per_sprint: float | None = None
    cost_optimization_enabled: bool = Field(True)

    # Team dynamics
    coordination_overhead: float = Field(0.1, description="Coordination overhead percentage")
    review_cycles_per_task: int = Field(1, description="Average review cycles per task")

    # Configuration metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def add_member(self, member: TeamMember) -> None:
        """Add a team member."""
        if member.id not in [m.id for m in self.members]:
            self.members.append(member)
            self.updated_at = datetime.utcnow()

    def remove_member(self, member_id: str) -> None:
        """Remove a team member."""
        self.members = [m for m in self.members if m.id != member_id]
        self.updated_at = datetime.utcnow()

    def get_member_by_id(self, member_id: str) -> TeamMember | None:
        """Get a team member by ID."""
        return next((m for m in self.members if m.id == member_id), None)

    def get_members_by_role(self, role: AgentRole) -> list[TeamMember]:
        """Get team members by role."""
        return [m for m in self.members if m.role == role]

    def get_available_members(self) -> list[TeamMember]:
        """Get available team members."""
        return [m for m in self.members if m.status == AgentStatus.AVAILABLE]

    def get_members_by_status(self, status: AgentStatus) -> list[TeamMember]:
        """Get team members by status."""
        return [m for m in self.members if m.status == status]

    def get_team_capacity(self) -> dict[AgentRole, int]:
        """Get team capacity by role."""
        capacity = {}
        for member in self.members:
            if member.role not in capacity:
                capacity[member.role] = 0
            capacity[member.role] += 1
        return capacity

    def get_team_workload(self) -> dict[str, Any]:
        """Get current team workload."""
        total_members = len(self.members)
        busy_members = len([m for m in self.members if m.status == AgentStatus.BUSY])
        available_members = len(self.get_available_members())
        blocked_members = len([m for m in self.members if m.status == AgentStatus.BLOCKED])

        utilization_rate = (busy_members / total_members * 100) if total_members > 0 else 0

        return {
            "total_members": total_members,
            "available_members": available_members,
            "busy_members": busy_members,
            "blocked_members": blocked_members,
            "utilization_rate": utilization_rate,
            "capacity_by_role": self.get_team_capacity(),
        }

    def get_team_performance_summary(self) -> dict[str, Any]:
        """Get team performance summary."""
        total_tasks = sum(m.tasks_completed for m in self.members)
        total_tokens = sum(m.total_tokens_used for m in self.members)
        total_cost = sum(m.total_cost for m in self.members)

        performance_by_role = {}
        for role in AgentRole:
            role_members = self.get_members_by_role(role)
            if role_members:
                role_tasks = sum(m.tasks_completed for m in role_members)
                role_cost = sum(m.total_cost for m in role_members)
                role_tokens = sum(m.total_tokens_used for m in role_members)

                performance_by_role[role.value] = {
                    "member_count": len(role_members),
                    "tasks_completed": role_tasks,
                    "total_cost": role_cost,
                    "total_tokens": role_tokens,
                    "avg_cost_per_member": role_cost / len(role_members),
                    "avg_tasks_per_member": role_tasks / len(role_members),
                }

        return {
            "team_id": self.id,
            "team_name": self.name,
            "total_tasks_completed": total_tasks,
            "total_tokens_used": total_tokens,
            "total_cost": total_cost,
            "performance_by_role": performance_by_role,
            "current_workload": self.get_team_workload(),
        }

    def optimize_task_assignments(self, task_estimates: list[Any]) -> list[AgentAssignment]:
        """Optimize task assignments across team members using workload balancing and role matching."""
        from ..config.models import calculate_cost, get_model_config

        assignments = []
        available_members = self.get_available_members()
        if not available_members:
            return assignments

        # Initialize assignments for all available members
        member_assignments = {
            member.id: AgentAssignment(agent_id=member.id)
            for member in available_members
        }

        # Sort tasks by priority (complexity and estimated hours)
        sorted_tasks = sorted(
            task_estimates,
            key=lambda t: (
                getattr(t, 'complexity', 'medium'),
                -(getattr(t, 'estimated_hours', 2.0))  # Higher hours first
            )
        )

        for task in sorted_tasks:
            task_role = getattr(task, 'assigned_role', None)
            task_type = getattr(task, 'task_type', None)
            estimated_hours = getattr(task, 'estimated_hours', 2.0)

            # Find best member for this task
            best_member = self._find_best_member_for_task(
                available_members, task, member_assignments
            )

            if best_member:
                # Calculate estimated cost
                model_config = get_model_config(best_member.role)
                estimated_tokens = getattr(task, 'estimated_input_tokens', 1000) + getattr(task, 'estimated_output_tokens', 500)
                estimated_cost = calculate_cost(
                    getattr(task, 'estimated_input_tokens', 1000),
                    getattr(task, 'estimated_output_tokens', 500),
                    model_config
                )

                # Add task to member's assignment
                member_assignments[best_member.id].add_task(
                    task_id=getattr(task, 'id', f'task_{id(task)}'),
                    estimated_hours=estimated_hours,
                    estimated_cost=estimated_cost
                )

        # Return non-empty assignments
        return [assignment for assignment in member_assignments.values() if assignment.task_ids]

    def _find_best_member_for_task(self, available_members: list['TeamMember'], task: Any, current_assignments: dict[str, AgentAssignment]) -> 'TeamMember | None':
        """Find the best team member for a given task based on role matching and workload."""
        if not available_members:
            return None

        task_role = getattr(task, 'assigned_role', None)
        task_type = getattr(task, 'task_type', None)

        # Score each member
        member_scores = []

        for member in available_members:
            score = 0.0

            # Role matching bonus
            if task_role and member.role == task_role:
                score += 100.0

            # Task type specialization bonus
            if task_type and hasattr(member, 'specializations'):
                if any(spec.lower() in str(task_type).lower() for spec in member.specializations):
                    score += 50.0

            # Workload balancing penalty (prefer less loaded members)
            current_workload = current_assignments.get(member.id, AgentAssignment(agent_id=member.id))
            workload_penalty = current_workload.estimated_workload_hours * 10
            score -= workload_penalty

            # Model tier efficiency bonus (higher tier for complex tasks)
            task_complexity = getattr(task, 'complexity', 'medium')
            model_tier_value = member.model_tier.value if hasattr(member.model_tier, 'value') else str(member.model_tier).lower()
            if task_complexity == 'high' and model_tier_value in ['opus', 'sonnet'] or task_complexity == 'low' and model_tier_value == 'haiku':
                score += 25.0

            member_scores.append((member, score))

        # Return member with highest score
        member_scores.sort(key=lambda x: x[1], reverse=True)
        return member_scores[0][0] if member_scores else None

    @classmethod
    def create_default_team(cls) -> "TeamConfiguration":
        """Create a default team configuration."""
        from ..config.models import get_model_tier

        team = cls(
            id="default_team",
            name="Default Gaggle Team",
        )

        # Add default team members
        default_members = [
            TeamMember(
                id="po_001",
                name="ProductOwner",
                role=AgentRole.PRODUCT_OWNER,
                model_tier=get_model_tier(AgentRole.PRODUCT_OWNER),
                specializations=["requirements", "business_analysis"],
                tools_enabled=["backlog_tool", "story_template_tool"]
            ),
            TeamMember(
                id="sm_001",
                name="ScrumMaster",
                role=AgentRole.SCRUM_MASTER,
                model_tier=get_model_tier(AgentRole.SCRUM_MASTER),
                specializations=["facilitation", "metrics"],
                tools_enabled=["sprint_board_tool", "metrics_tool"]
            ),
            TeamMember(
                id="tl_001",
                name="TechLead",
                role=AgentRole.TECH_LEAD,
                model_tier=get_model_tier(AgentRole.TECH_LEAD),
                specializations=["architecture", "code_review"],
                tools_enabled=["architecture_tool", "code_review_tool"]
            ),
            TeamMember(
                id="fe_001",
                name="FrontendDev",
                role=AgentRole.FRONTEND_DEV,
                model_tier=get_model_tier(AgentRole.FRONTEND_DEV),
                specializations=["react", "typescript"],
                tools_enabled=["code_tool", "test_tool"]
            ),
            TeamMember(
                id="be_001",
                name="BackendDev",
                role=AgentRole.BACKEND_DEV,
                model_tier=get_model_tier(AgentRole.BACKEND_DEV),
                specializations=["python", "apis"],
                tools_enabled=["code_tool", "database_tool"]
            ),
            TeamMember(
                id="qa_001",
                name="QAEngineer",
                role=AgentRole.QA_ENGINEER,
                model_tier=get_model_tier(AgentRole.QA_ENGINEER),
                specializations=["testing", "automation"],
                tools_enabled=["test_tool", "bug_tool"]
            ),
        ]

        for member in default_members:
            team.add_member(member)

        return team
