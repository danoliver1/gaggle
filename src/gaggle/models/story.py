"""User story domain model."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StoryStatus(str, Enum):
    """User story status enumeration."""
    BACKLOG = "backlog"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CANCELLED = "cancelled"


class StoryPriority(str, Enum):
    """User story priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AcceptanceCriteria(BaseModel):
    """Acceptance criteria for a user story."""
    id: str = Field(..., description="Unique identifier for the criteria")
    description: str = Field(..., description="Acceptance criteria description")
    is_satisfied: bool = Field(False, description="Whether criteria is satisfied")
    verified_by: str | None = None
    verified_at: datetime | None = None

    def mark_satisfied(self, verified_by: str) -> None:
        """Mark this criteria as satisfied."""
        self.is_satisfied = True
        self.verified_by = verified_by
        self.verified_at = datetime.utcnow()


class UserStory(BaseModel):
    """User story domain model."""

    id: str = Field(..., description="Unique story identifier")
    title: str = Field(..., description="Story title")
    description: str = Field(..., description="Story description (As a... I want... So that...)")

    # Story classification
    priority: StoryPriority = Field(StoryPriority.MEDIUM, description="Story priority")
    story_points: float = Field(0.0, description="Story points estimate")
    epic_id: str | None = None

    # Status tracking
    status: StoryStatus = Field(StoryStatus.BACKLOG, description="Current story status")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Acceptance criteria
    acceptance_criteria: list[AcceptanceCriteria] = Field(default_factory=list)

    # Assignments and ownership
    product_owner: str | None = None
    assigned_to: str | None = None

    # Technical details
    technical_notes: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list, description="Dependent story IDs")

    # GitHub integration
    github_issue_id: int | None = None
    github_labels: list[str] = Field(default_factory=list)

    # Sprint association
    sprint_id: str | None = None

    # Business value
    business_value: str | None = None
    user_persona: str | None = None

    model_config = ConfigDict(use_enum_values=True)

    @field_validator('id')
    @classmethod
    def validate_id(cls, v):
        """Validate story ID is not empty."""
        if not v.strip():
            raise ValueError('Story ID cannot be empty')
        return v.strip()

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Validate story title."""
        if not v.strip():
            raise ValueError('Story title cannot be empty')
        if len(v.strip()) > 200:
            raise ValueError('Story title must be 200 characters or less')
        return v.strip()

    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        """Validate story description."""
        if not v.strip():
            raise ValueError('Story description cannot be empty')
        if len(v.strip()) < 10:
            raise ValueError('Story description must be at least 10 characters')
        return v.strip()

    @field_validator('story_points')
    @classmethod
    def validate_story_points(cls, v):
        """Validate story points are non-negative."""
        if v < 0:
            raise ValueError('Story points must be non-negative')
        return v

    def add_acceptance_criteria(self, description: str) -> AcceptanceCriteria:
        """Add acceptance criteria to the story."""
        criteria_id = f"{self.id}_ac_{len(self.acceptance_criteria) + 1}"
        criteria = AcceptanceCriteria(
            id=criteria_id,
            description=description
        )
        self.acceptance_criteria.append(criteria)
        self.updated_at = datetime.utcnow()
        return criteria

    def move_to_status(self, new_status: StoryStatus, updated_by: str | None = None) -> None:
        """Move story to a new status."""
        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.utcnow()

        # Add technical note about status change
        note = f"Status changed from {old_status} to {new_status}"
        if updated_by:
            note += f" by {updated_by}"
        self.add_technical_note(note)

    def add_technical_note(self, note: str) -> None:
        """Add a technical note to the story."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        self.technical_notes.append(f"[{timestamp}] {note}")
        self.updated_at = datetime.utcnow()

    def assign_to(self, assignee: str) -> None:
        """Assign the story to someone."""
        old_assignee = self.assigned_to
        self.assigned_to = assignee
        self.updated_at = datetime.utcnow()

        if old_assignee:
            self.add_technical_note(f"Reassigned from {old_assignee} to {assignee}")
        else:
            self.add_technical_note(f"Assigned to {assignee}")

    def add_dependency(self, dependent_story_id: str) -> None:
        """Add a dependency to another story."""
        if dependent_story_id not in self.dependencies:
            self.dependencies.append(dependent_story_id)
            self.add_technical_note(f"Added dependency on story {dependent_story_id}")
            self.updated_at = datetime.utcnow()

    def remove_dependency(self, dependent_story_id: str) -> None:
        """Remove a dependency."""
        if dependent_story_id in self.dependencies:
            self.dependencies.remove(dependent_story_id)
            self.add_technical_note(f"Removed dependency on story {dependent_story_id}")
            self.updated_at = datetime.utcnow()

    def is_ready_for_development(self) -> bool:
        """Check if story is ready for development."""
        return (
            self.status in [StoryStatus.READY, StoryStatus.IN_PROGRESS] and
            len(self.acceptance_criteria) > 0 and
            self.story_points > 0 and
            not self.has_unresolved_dependencies()
        )

    def has_unresolved_dependencies(self, story_registry: dict[str, 'UserStory'] | None = None) -> bool:
        """Check if story has unresolved dependencies.
        
        Args:
            story_registry: Optional dictionary of story_id -> UserStory for dependency checking.
                          If None, assumes dependencies are unresolved.
        """
        if not self.dependencies:
            return False

        if story_registry is None:
            # Conservative assumption: if we can't check dependencies, assume they're unresolved
            return True

        # Check each dependency
        for dep_story_id in self.dependencies:
            dependent_story = story_registry.get(dep_story_id)

            if not dependent_story:
                # Dependency story doesn't exist - unresolved
                return True

            if dependent_story.status not in [StoryStatus.DONE]:
                # Dependency is not complete - unresolved
                return True

        # All dependencies are resolved
        return False

    def get_completion_percentage(self) -> float:
        """Calculate completion percentage based on acceptance criteria."""
        if not self.acceptance_criteria:
            return 0.0

        satisfied_count = sum(1 for ac in self.acceptance_criteria if ac.is_satisfied)
        return (satisfied_count / len(self.acceptance_criteria)) * 100

    def get_definition_of_done_checklist(self) -> dict[str, bool]:
        """Get definition of done checklist."""
        return {
            "has_acceptance_criteria": len(self.acceptance_criteria) > 0,
            "all_criteria_satisfied": all(ac.is_satisfied for ac in self.acceptance_criteria),
            "has_story_points": self.story_points > 0,
            "has_assignee": self.assigned_to is not None,
            "no_blockers": self.status != StoryStatus.CANCELLED,
            "in_done_status": self.status == StoryStatus.DONE,
        }

    def is_definition_of_done_met(self) -> bool:
        """Check if definition of done is met."""
        checklist = self.get_definition_of_done_checklist()
        return all(checklist.values())

    def to_github_issue(self) -> dict[str, Any]:
        """Convert to GitHub issue format."""
        body = f"""## User Story
{self.description}

## Acceptance Criteria
"""
        for i, criteria in enumerate(self.acceptance_criteria, 1):
            status = "✅" if criteria.is_satisfied else "⬜"
            body += f"{status} {i}. {criteria.description}\n"

        if self.business_value:
            body += f"\n## Business Value\n{self.business_value}"

        if self.technical_notes:
            body += "\n## Technical Notes\n"
            for note in self.technical_notes[-5:]:  # Last 5 notes
                body += f"- {note}\n"

        labels = ["user-story"] + self.github_labels
        if self.priority != StoryPriority.MEDIUM:
            labels.append(f"priority-{self.priority.value}")

        return {
            "title": self.title,
            "body": body,
            "labels": labels,
            "assignees": [self.assigned_to] if self.assigned_to else [],
        }
