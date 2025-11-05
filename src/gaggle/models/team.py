"""Team and agent configuration models."""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

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
    current_task_id: Optional[str] = None
    
    # Configuration
    model_tier: ModelTier = Field(..., description="Model tier for this agent")
    max_concurrent_tasks: int = Field(1, description="Maximum concurrent tasks")
    
    # Performance tracking
    tasks_completed: int = Field(0, description="Total tasks completed")
    total_tokens_used: int = Field(0, description="Total tokens consumed")
    total_cost: float = Field(0.0, description="Total cost incurred")
    
    # Specializations and capabilities
    specializations: List[str] = Field(default_factory=list, description="Agent specializations")
    tools_enabled: List[str] = Field(default_factory=list, description="Available tools")
    
    # Time tracking
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True
    
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
    
    def get_performance_metrics(self) -> Dict[str, Any]:
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
            "role": self.role.value,
            "tasks_completed": self.tasks_completed,
            "total_tokens_used": self.total_tokens_used,
            "total_cost": self.total_cost,
            "avg_tokens_per_task": avg_tokens_per_task,
            "avg_cost_per_task": avg_cost_per_task,
            "status": self.status.value,
            "model_tier": self.model_tier.value,
        }


class AgentAssignment(BaseModel):
    """Assignment of tasks to agents for optimization."""
    
    agent_id: str
    task_ids: List[str] = Field(default_factory=list)
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
    members: List[TeamMember] = Field(default_factory=list)
    
    # Team capacity and constraints
    max_parallel_tasks: int = Field(10, description="Maximum parallel tasks for the team")
    sprint_capacity_hours: float = Field(400.0, description="Total sprint capacity in hours")
    
    # Cost management
    budget_per_sprint: Optional[float] = None
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
    
    def get_member_by_id(self, member_id: str) -> Optional[TeamMember]:
        """Get a team member by ID."""
        return next((m for m in self.members if m.id == member_id), None)
    
    def get_members_by_role(self, role: AgentRole) -> List[TeamMember]:
        """Get team members by role."""
        return [m for m in self.members if m.role == role]
    
    def get_available_members(self) -> List[TeamMember]:
        """Get available team members."""
        return [m for m in self.members if m.status == AgentStatus.AVAILABLE]
    
    def get_members_by_status(self, status: AgentStatus) -> List[TeamMember]:
        """Get team members by status."""
        return [m for m in self.members if m.status == status]
    
    def get_team_capacity(self) -> Dict[AgentRole, int]:
        """Get team capacity by role."""
        capacity = {}
        for member in self.members:
            if member.role not in capacity:
                capacity[member.role] = 0
            capacity[member.role] += 1
        return capacity
    
    def get_team_workload(self) -> Dict[str, Any]:
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
    
    def get_team_performance_summary(self) -> Dict[str, Any]:
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
    
    def optimize_task_assignments(self, task_estimates: List[Any]) -> List[AgentAssignment]:
        """Optimize task assignments across team members."""
        # This would integrate with the CostCalculator
        # Placeholder implementation
        assignments = []
        
        available_members = self.get_available_members()
        if not available_members:
            return assignments
        
        # Simple round-robin assignment as placeholder
        for i, task in enumerate(task_estimates):
            member = available_members[i % len(available_members)]
            
            # Find existing assignment or create new one
            assignment = next(
                (a for a in assignments if a.agent_id == member.id),
                None
            )
            
            if not assignment:
                assignment = AgentAssignment(agent_id=member.id)
                assignments.append(assignment)
            
            assignment.add_task(
                task_id=getattr(task, 'id', f'task_{i}'),
                estimated_hours=getattr(task, 'estimated_hours', 2.0),
                estimated_cost=getattr(task, 'estimated_cost', 1.0)
            )
        
        return assignments
    
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