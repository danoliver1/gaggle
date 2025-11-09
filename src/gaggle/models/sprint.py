"""Sprint domain model."""

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..config.models import AgentRole
from .story import UserStory, StoryStatus
from .task import Task


class SprintStatus(str, Enum):
    """Sprint status enumeration."""
    PLANNING = "planning"
    ACTIVE = "active"
    REVIEW = "review"
    RETROSPECTIVE = "retrospective"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SprintMetrics(BaseModel):
    """Sprint performance metrics."""
    velocity: float = Field(0.0, description="Story points completed")
    burndown_remaining: float = Field(0.0, description="Remaining story points")
    total_story_points: float = Field(0.0, description="Total story points planned")

    # Token usage metrics
    total_tokens_used: int = Field(0, description="Total tokens consumed")
    total_cost: float = Field(0.0, description="Total cost in USD")
    cost_by_role: dict[str, float] = Field(default_factory=dict)

    # Time metrics
    actual_duration_days: float | None = None
    planned_duration_days: int = Field(10, description="Planned sprint duration")

    # Task metrics
    tasks_completed: int = Field(0, description="Number of tasks completed")
    tasks_total: int = Field(0, description="Total number of tasks")

    # Quality metrics
    bugs_found: int = Field(0, description="Bugs found during sprint")
    code_review_iterations: int = Field(0, description="Average review iterations")

    @property
    def completion_percentage(self) -> float:
        """Calculate sprint completion percentage."""
        if self.total_story_points == 0:
            return 0.0
        return (self.velocity / self.total_story_points) * 100

    @property
    def cost_per_story_point(self) -> float:
        """Calculate cost per story point."""
        if self.velocity == 0:
            return 0.0
        return self.total_cost / self.velocity

    @property
    def task_completion_rate(self) -> float:
        """Calculate task completion rate."""
        if self.tasks_total == 0:
            return 0.0
        return (self.tasks_completed / self.tasks_total) * 100


class SprintModel(BaseModel):
    """Sprint domain model."""

    id: str = Field(..., description="Unique sprint identifier")
    goal: str = Field(..., description="Sprint goal description")
    status: SprintStatus = Field(SprintStatus.PLANNING, description="Current sprint status")

    # Timeline
    start_date: date | None = None
    end_date: date | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Sprint content
    user_stories: list[UserStory] = Field(default_factory=list)
    tasks: list[Task] = Field(default_factory=list)

    # Team configuration
    team_capacity: dict[AgentRole, int] = Field(default_factory=dict)

    # Metrics and tracking
    metrics: SprintMetrics = Field(default_factory=SprintMetrics)

    # Sprint artifacts
    sprint_backlog: list[str] = Field(default_factory=list, description="Story IDs in sprint backlog")
    sprint_notes: list[str] = Field(default_factory=list, description="Sprint notes and observations")

    # GitHub integration
    github_milestone_id: int | None = None
    github_project_id: int | None = None

    model_config = ConfigDict(use_enum_values=True)

    @field_validator('id')
    @classmethod
    def validate_id(cls, v):
        """Validate sprint ID is not empty."""
        if not v.strip():
            raise ValueError('Sprint ID cannot be empty')
        return v.strip()

    @field_validator('goal')
    @classmethod
    def validate_goal(cls, v):
        """Validate sprint goal."""
        if not v.strip():
            raise ValueError('Sprint goal cannot be empty')
        if len(v.strip()) < 10:
            raise ValueError('Sprint goal must be at least 10 characters')
        return v.strip()

    @field_validator('end_date')
    @classmethod
    def validate_end_date(cls, v, info):
        """Validate that end date is after start date."""
        if hasattr(info, 'data') and v and info.data.get('start_date') and v <= info.data['start_date']:
            raise ValueError('End date must be after start date')
        return v

    def add_story(self, story: UserStory) -> None:
        """Add a user story to the sprint."""
        if story.id not in [s.id for s in self.user_stories]:
            self.user_stories.append(story)
            self.sprint_backlog.append(story.id)
            self._update_metrics()

    def add_task(self, task: Task) -> None:
        """Add a task to the sprint."""
        if task.id not in [t.id for t in self.tasks]:
            self.tasks.append(task)
            self._update_metrics()

    def start_sprint(self, duration_days: int = 10) -> None:
        """Start the sprint."""
        if self.status != SprintStatus.PLANNING:
            raise ValueError("Can only start sprints in planning status")

        self.status = SprintStatus.ACTIVE
        self.start_date = date.today()
        self.end_date = date.today() + timedelta(days=duration_days)
        self.metrics.planned_duration_days = duration_days
        self.updated_at = datetime.utcnow()

    def complete_sprint(self) -> None:
        """Complete the sprint."""
        if self.status not in [SprintStatus.ACTIVE, SprintStatus.REVIEW]:
            raise ValueError("Can only complete active or in-review sprints")

        self.status = SprintStatus.COMPLETED
        self.updated_at = datetime.utcnow()

        if self.start_date:
            actual_days = (date.today() - self.start_date).days
            self.metrics.actual_duration_days = actual_days

        self._update_metrics()

    def add_note(self, note: str) -> None:
        """Add a note to the sprint."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        self.sprint_notes.append(f"[{timestamp}] {note}")
        self.updated_at = datetime.utcnow()

    def get_stories_by_status(self, status: str) -> list[UserStory]:
        """Get stories filtered by status."""
        return [story for story in self.user_stories if story.status == status]

    def get_tasks_by_status(self, status: str) -> list[Task]:
        """Get tasks filtered by status."""
        return [task for task in self.tasks if task.status == status]

    def get_tasks_for_story(self, story_id: str) -> list[Task]:
        """Get all tasks for a specific story."""
        return [task for task in self.tasks if task.story_id == story_id]

    def _update_metrics(self) -> None:
        """Update sprint metrics based on current state."""
        from .story import StoryStatus
        from .task import TaskStatus

        # Story points metrics
        total_points = sum(story.story_points for story in self.user_stories)
        completed_points = sum(
            story.story_points
            for story in self.user_stories
            if story.status == StoryStatus.DONE
        )

        self.metrics.total_story_points = total_points
        self.metrics.velocity = completed_points
        self.metrics.burndown_remaining = total_points - completed_points

        # Task metrics
        completed_tasks = len([
            task for task in self.tasks
            if task.status == TaskStatus.DONE
        ])

        self.metrics.tasks_completed = completed_tasks
        self.metrics.tasks_total = len(self.tasks)

        self.updated_at = datetime.utcnow()

    def get_daily_standup_report(self) -> dict[str, Any]:
        """Generate daily standup report."""
        return {
            "sprint_id": self.id,
            "sprint_goal": self.goal,
            "days_remaining": self._get_days_remaining(),
            "completion_percentage": self.metrics.completion_percentage,
            "stories_completed": len(self.get_stories_by_status(StoryStatus.DONE.value)),
            "stories_in_progress": len(self.get_stories_by_status(StoryStatus.IN_PROGRESS.value)),
            "tasks_completed": self.metrics.tasks_completed,
            "tasks_total": self.metrics.tasks_total,
            "blockers": self._get_blocked_tasks(),
            "recent_notes": self.sprint_notes[-3:] if self.sprint_notes else [],
        }

    def _get_days_remaining(self) -> int | None:
        """Get days remaining in sprint."""
        if not self.end_date:
            return None
        return (self.end_date - date.today()).days

    def _get_blocked_tasks(self) -> list[dict[str, str]]:
        """Get list of blocked tasks."""
        from .task import TaskStatus

        blocked_tasks = [
            task for task in self.tasks
            if task.status == TaskStatus.BLOCKED
        ]

        return [
            {
                "task_id": task.id,
                "title": task.title,
                "assignee": task.assigned_to,
                "blocker_reason": task.blocker_reason or "Unknown"
            }
            for task in blocked_tasks
        ]


# Import needed for validator
from datetime import timedelta

# Alias for convenience
Sprint = SprintModel
