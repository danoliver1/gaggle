"""Task domain model."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field, validator

from ..config.models import AgentRole


class TaskStatus(str, Enum):
    """Task status enumeration."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """Task type classification."""
    FRONTEND = "frontend"
    BACKEND = "backend"
    FULLSTACK = "fullstack"
    TESTING = "testing"
    ARCHITECTURE = "architecture"
    DOCUMENTATION = "documentation"
    DEVOPS = "devops"
    RESEARCH = "research"


class TaskComplexity(str, Enum):
    """Task complexity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskDependency(BaseModel):
    """Task dependency relationship."""
    task_id: str = Field(..., description="ID of the dependent task")
    dependency_type: str = Field("blocks", description="Type of dependency")
    description: Optional[str] = None


class Task(BaseModel):
    """Task domain model."""
    
    id: str = Field(..., description="Unique task identifier")
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Detailed task description")
    
    # Classification
    task_type: TaskType = Field(..., description="Type of task")
    complexity: TaskComplexity = Field(TaskComplexity.MEDIUM, description="Task complexity")
    
    # Story association
    story_id: Optional[str] = None
    
    # Status and progress
    status: TaskStatus = Field(TaskStatus.TODO, description="Current task status")
    progress_percentage: float = Field(0.0, description="Task completion percentage")
    
    # Assignment
    assigned_to: Optional[str] = None
    assigned_role: Optional[AgentRole] = None
    
    # Time tracking
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Dependencies
    dependencies: List[TaskDependency] = Field(default_factory=list)
    blocks: List[str] = Field(default_factory=list, description="Task IDs that this task blocks")
    
    # Additional fields used by agents
    user_story_id: Optional[str] = None
    blocked: bool = False
    reviewed: bool = False
    review_status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Blocking information
    blocker_reason: Optional[str] = None
    blocked_at: Optional[datetime] = None
    
    # Technical details
    technical_requirements: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    
    # Code and artifacts
    code_files: List[str] = Field(default_factory=list, description="Files created/modified")
    pull_request_url: Optional[str] = None
    github_issue_id: Optional[int] = None
    
    # Review information
    review_notes: List[str] = Field(default_factory=list)
    review_iterations: int = Field(0, description="Number of review cycles")
    
    # Token usage tracking
    estimated_input_tokens: int = Field(0, description="Estimated input tokens")
    estimated_output_tokens: int = Field(0, description="Estimated output tokens")
    actual_input_tokens: int = Field(0, description="Actual input tokens used")
    actual_output_tokens: int = Field(0, description="Actual output tokens used")
    
    # Sprint context
    sprint_id: Optional[str] = None
    
    class Config:
        use_enum_values = True
    
    @validator('progress_percentage')
    def validate_progress(cls, v):
        """Validate progress percentage is between 0 and 100."""
        if not 0 <= v <= 100:
            raise ValueError('Progress percentage must be between 0 and 100')
        return v
    
    @validator('estimated_hours', 'actual_hours')
    def validate_hours(cls, v):
        """Validate hours are positive."""
        if v is not None and v < 0:
            raise ValueError('Hours must be positive')
        return v
    
    def assign_to_agent(self, agent_name: str, agent_role: AgentRole) -> None:
        """Assign task to a specific agent."""
        old_assignee = self.assigned_to
        self.assigned_to = agent_name
        self.assigned_role = agent_role
        self.updated_at = datetime.utcnow()
        
        note = f"Assigned to {agent_name} ({agent_role.value})"
        if old_assignee:
            note = f"Reassigned from {old_assignee} to {agent_name} ({agent_role.value})"
        
        self.add_review_note(note)
    
    def start_work(self) -> None:
        """Start working on the task."""
        if self.status != TaskStatus.TODO:
            raise ValueError("Can only start tasks that are in TODO status")
        
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.add_review_note("Task started")
    
    def mark_for_review(self) -> None:
        """Mark task as ready for review."""
        if self.status != TaskStatus.IN_PROGRESS:
            raise ValueError("Can only mark in-progress tasks for review")
        
        self.status = TaskStatus.IN_REVIEW
        self.progress_percentage = 100.0
        self.updated_at = datetime.utcnow()
        self.add_review_note("Task marked for review")
    
    def complete_task(self, completed_by: Optional[str] = None) -> None:
        """Mark task as completed."""
        if self.status not in [TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW]:
            raise ValueError("Can only complete in-progress or in-review tasks")
        
        self.status = TaskStatus.DONE
        self.progress_percentage = 100.0
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        note = "Task completed"
        if completed_by:
            note += f" by {completed_by}"
        self.add_review_note(note)
        
        # Calculate actual hours if started
        if self.started_at:
            duration = self.completed_at - self.started_at
            self.actual_hours = duration.total_seconds() / 3600
    
    def block_task(self, reason: str) -> None:
        """Block the task with a reason."""
        self.status = TaskStatus.BLOCKED
        self.blocker_reason = reason
        self.blocked_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.add_review_note(f"Task blocked: {reason}")
    
    def unblock_task(self) -> None:
        """Unblock the task."""
        if self.status != TaskStatus.BLOCKED:
            raise ValueError("Can only unblock blocked tasks")
        
        self.status = TaskStatus.IN_PROGRESS
        self.blocker_reason = None
        self.blocked_at = None
        self.updated_at = datetime.utcnow()
        self.add_review_note("Task unblocked")
    
    def add_dependency(self, task_id: str, dependency_type: str = "blocks", description: Optional[str] = None) -> None:
        """Add a dependency to another task."""
        dependency = TaskDependency(
            task_id=task_id,
            dependency_type=dependency_type,
            description=description
        )
        
        if dependency not in self.dependencies:
            self.dependencies.append(dependency)
            self.updated_at = datetime.utcnow()
            self.add_review_note(f"Added dependency on task {task_id}")
    
    def remove_dependency(self, task_id: str) -> None:
        """Remove a dependency."""
        self.dependencies = [dep for dep in self.dependencies if dep.task_id != task_id]
        self.updated_at = datetime.utcnow()
        self.add_review_note(f"Removed dependency on task {task_id}")
    
    def add_review_note(self, note: str) -> None:
        """Add a review note."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        self.review_notes.append(f"[{timestamp}] {note}")
        self.updated_at = datetime.utcnow()
    
    def add_code_file(self, file_path: str) -> None:
        """Add a code file that was created/modified for this task."""
        if file_path not in self.code_files:
            self.code_files.append(file_path)
            self.updated_at = datetime.utcnow()
    
    def update_progress(self, percentage: float, note: Optional[str] = None) -> None:
        """Update task progress."""
        old_progress = self.progress_percentage
        self.progress_percentage = percentage
        self.updated_at = datetime.utcnow()
        
        progress_note = f"Progress updated from {old_progress}% to {percentage}%"
        if note:
            progress_note += f": {note}"
        
        self.add_review_note(progress_note)
    
    def track_token_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Track actual token usage for this task."""
        self.actual_input_tokens += input_tokens
        self.actual_output_tokens += output_tokens
        self.updated_at = datetime.utcnow()
    
    def is_ready_to_start(self) -> bool:
        """Check if task is ready to start (no blocking dependencies)."""
        return (
            self.status == TaskStatus.TODO and
            len(self.dependencies) == 0  # Simplified - would need dependency resolution
        )
    
    def can_be_parallelized(self) -> bool:
        """Check if this task can be parallelized with others."""
        # Tasks with dependencies or that block others are harder to parallelize
        return (
            len(self.dependencies) == 0 and
            len(self.blocks) == 0 and
            self.task_type != TaskType.ARCHITECTURE  # Architecture tasks often need coordination
        )
    
    def get_time_metrics(self) -> Dict[str, Any]:
        """Get time-related metrics for the task."""
        metrics = {
            "estimated_hours": self.estimated_hours,
            "actual_hours": self.actual_hours,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }
        
        if self.started_at and self.completed_at:
            duration = self.completed_at - self.started_at
            metrics["cycle_time_hours"] = duration.total_seconds() / 3600
        
        if self.created_at and self.started_at:
            lead_time = self.started_at - self.created_at
            metrics["lead_time_hours"] = lead_time.total_seconds() / 3600
        
        return metrics
    
    def get_cost_estimate(self) -> Dict[str, float]:
        """Get cost estimate for this task."""
        if not self.assigned_role:
            return {"estimated_cost": 0.0, "actual_cost": 0.0}
        
        from ..config.models import get_model_config, calculate_cost
        
        config = get_model_config(self.assigned_role)
        
        estimated_cost = calculate_cost(
            self.estimated_input_tokens,
            self.estimated_output_tokens,
            config
        )
        
        actual_cost = calculate_cost(
            self.actual_input_tokens,
            self.actual_output_tokens,
            config
        )
        
        return {
            "estimated_cost": estimated_cost,
            "actual_cost": actual_cost,
            "cost_variance": actual_cost - estimated_cost,
        }
    
    def to_github_issue(self) -> Dict[str, Any]:
        """Convert task to GitHub issue format."""
        body = f"""## Task Description
{self.description}

## Technical Requirements
"""
        for req in self.technical_requirements:
            body += f"- {req}\n"
        
        body += "\n## Acceptance Criteria\n"
        for criteria in self.acceptance_criteria:
            body += f"- [ ] {criteria}\n"
        
        if self.dependencies:
            body += "\n## Dependencies\n"
            for dep in self.dependencies:
                body += f"- Depends on: #{dep.task_id}"
                if dep.description:
                    body += f" - {dep.description}"
                body += "\n"
        
        labels = [
            f"task-{self.task_type.value}",
            f"complexity-{self.complexity.value}"
        ]
        
        if self.assigned_role:
            labels.append(f"agent-{self.assigned_role.value}")
        
        return {
            "title": self.title,
            "body": body,
            "labels": labels,
            "assignees": [self.assigned_to] if self.assigned_to else [],
        }


# Alias for compatibility with existing code
TaskModel = Task