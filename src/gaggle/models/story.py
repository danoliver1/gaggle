"""User story domain model."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator


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
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    
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
    epic_id: Optional[str] = None
    
    # Status tracking
    status: StoryStatus = Field(StoryStatus.BACKLOG, description="Current story status")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Acceptance criteria
    acceptance_criteria: List[AcceptanceCriteria] = Field(default_factory=list)
    
    # Assignments and ownership
    product_owner: Optional[str] = None
    assigned_to: Optional[str] = None
    
    # Technical details
    technical_notes: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list, description="Dependent story IDs")
    
    # GitHub integration
    github_issue_id: Optional[int] = None
    github_labels: List[str] = Field(default_factory=list)
    
    # Sprint association
    sprint_id: Optional[str] = None
    
    # Business value
    business_value: Optional[str] = None
    user_persona: Optional[str] = None
    
    class Config:
        use_enum_values = True
    
    @validator('story_points')
    def validate_story_points(cls, v):
        """Validate story points are non-negative."""
        if v < 0:
            raise ValueError('Story points must be non-negative')
        return v
    
    @validator('description')
    def validate_user_story_format(cls, v):
        """Validate that description follows user story format."""
        if not any(phrase in v.lower() for phrase in ['as a', 'i want', 'so that']):
            # This is a warning, not a hard requirement
            pass
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
    
    def move_to_status(self, new_status: StoryStatus, updated_by: Optional[str] = None) -> None:
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
    
    def has_unresolved_dependencies(self) -> bool:
        """Check if story has unresolved dependencies."""
        # This would need to be checked against other stories in the system
        # For now, just return False as placeholder
        return len(self.dependencies) > 0
    
    def get_completion_percentage(self) -> float:
        """Calculate completion percentage based on acceptance criteria."""
        if not self.acceptance_criteria:
            return 0.0
        
        satisfied_count = sum(1 for ac in self.acceptance_criteria if ac.is_satisfied)
        return (satisfied_count / len(self.acceptance_criteria)) * 100
    
    def get_definition_of_done_checklist(self) -> Dict[str, bool]:
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
    
    def to_github_issue(self) -> Dict[str, Any]:
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