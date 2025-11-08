"""Structured message schemas for agent communication."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import uuid

from ...config.models import AgentRole
from ...models.task import TaskPriority, TaskStatus, TaskType


class MessageType(Enum):
    """Types of messages in the system."""
    TASK_ASSIGNMENT = "task_assignment"
    SPRINT_PLANNING = "sprint_planning"
    CODE_REVIEW = "code_review"
    STANDUP_UPDATE = "standup_update"
    REQUIREMENT_CLARIFICATION = "requirement_clarification"
    ARCHITECTURE_DECISION = "architecture_decision"
    QUALITY_REPORT = "quality_report"
    COORDINATION_REQUEST = "coordination_request"


class MessagePriority(Enum):
    """Message priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ValidationResult:
    """Result of message validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, error: str) -> None:
        """Add validation error."""
        self.is_valid = False
        self.errors.append(error)
    
    def add_warning(self, warning: str) -> None:
        """Add validation warning."""
        self.warnings.append(warning)


@dataclass
class AgentMessage(ABC):
    """Base class for all agent messages with structured communication."""
    
    # Required fields first
    sender: AgentRole
    
    # Core message metadata with defaults
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = field(default=None, init=False)
    timestamp: datetime = field(default_factory=datetime.now)
    recipient: Optional[AgentRole] = field(default=None)
    priority: MessagePriority = field(default=MessagePriority.MEDIUM)
    
    # Message content
    subject: str = field(default="")
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Coordination metadata
    correlation_id: Optional[str] = field(default=None)  # Links related messages
    requires_response: bool = field(default=False)
    response_deadline: Optional[datetime] = field(default=None)
    
    def __post_init__(self):
        """Initialize message type based on class."""
        if not hasattr(self, 'message_type') or self.message_type is None:
            class_name = self.__class__.__name__
            if class_name.endswith('Message'):
                type_name = class_name[:-7].lower()  # Remove 'Message' suffix
                # Convert CamelCase to snake_case
                type_name = ''.join(['_' + c.lower() if c.isupper() and i > 0 else c.lower() 
                                   for i, c in enumerate(type_name)])
                try:
                    self.message_type = MessageType(type_name)
                except ValueError:
                    self.message_type = MessageType.COORDINATION_REQUEST
    
    @abstractmethod
    def validate(self) -> ValidationResult:
        """Validate message content and structure."""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        return {
            "id": self.id,
            "message_type": self.message_type.value,
            "timestamp": self.timestamp.isoformat(),
            "sender": self.sender.value,
            "recipient": self.recipient.value if self.recipient else None,
            "priority": self.priority.value,
            "subject": self.subject,
            "context": self.context,
            "correlation_id": self.correlation_id,
            "requires_response": self.requires_response,
            "response_deadline": self.response_deadline.isoformat() if self.response_deadline else None,
            **self._get_specific_fields()
        }
    
    def _get_specific_fields(self) -> Dict[str, Any]:
        """Get message-type specific fields for serialization."""
        return {}


@dataclass
class TaskAssignmentMessage(AgentMessage):
    """Message for assigning tasks to agents."""
    
    # Task details (using defaults to avoid dataclass inheritance issues)
    task_id: str = field(default="")
    task_title: str = field(default="")
    task_description: str = field(default="")
    task_type: TaskType = field(default=TaskType.FRONTEND)
    assignee: AgentRole = field(default=AgentRole.FRONTEND_DEV)
    
    # Message type override
    message_type: MessageType = field(default=MessageType.TASK_ASSIGNMENT, init=False)
    
    # Planning details
    estimated_effort: int = field(default=0)  # Story points or hours
    dependencies: List[str] = field(default_factory=list)  # Task IDs
    acceptance_criteria: List[str] = field(default_factory=list)
    
    # Coordination
    blocked_by: List[str] = field(default_factory=list)  # Task IDs that must complete first
    blocks: List[str] = field(default_factory=list)  # Task IDs that depend on this
    
    def validate(self) -> ValidationResult:
        """Validate task assignment message."""
        result = ValidationResult(is_valid=True)
        
        if not self.task_id:
            result.add_error("task_id is required")
        
        if not self.task_title:
            result.add_error("task_title is required")
        
        if not self.task_description:
            result.add_error("task_description is required")
            
        if self.estimated_effort <= 0:
            result.add_error("estimated_effort must be positive")
            
        if self.estimated_effort > 13:
            result.add_warning("estimated_effort exceeds typical sprint capacity")
        
        if not self.acceptance_criteria:
            result.add_warning("No acceptance criteria defined")
        
        # Validate assignee matches task type
        valid_assignments = {
            TaskType.FRONTEND: [AgentRole.FRONTEND_DEV, AgentRole.FULLSTACK_DEV],
            TaskType.BACKEND: [AgentRole.BACKEND_DEV, AgentRole.FULLSTACK_DEV],
            TaskType.FULLSTACK: [AgentRole.FULLSTACK_DEV],
            TaskType.TESTING: [AgentRole.QA_ENGINEER],
            TaskType.ARCHITECTURE: [AgentRole.TECH_LEAD],
            TaskType.DEVOPS: [AgentRole.BACKEND_DEV, AgentRole.FULLSTACK_DEV]
        }
        
        if self.assignee not in valid_assignments.get(self.task_type, []):
            result.add_warning(f"Assignee {self.assignee.value} may not be optimal for {self.task_type.value} task")
        
        return result
    
    def _get_specific_fields(self) -> Dict[str, Any]:
        """Get task-specific fields."""
        return {
            "task_id": self.task_id,
            "task_title": self.task_title,
            "task_description": self.task_description,
            "task_type": self.task_type.value,
            "assignee": self.assignee.value,
            "estimated_effort": self.estimated_effort,
            "dependencies": self.dependencies,
            "acceptance_criteria": self.acceptance_criteria,
            "blocked_by": self.blocked_by,
            "blocks": self.blocks
        }


@dataclass
class SprintPlanningMessage(AgentMessage):
    """Message for sprint planning coordination."""
    
    # Sprint details (using defaults to avoid inheritance issues)
    sprint_id: str = field(default="")
    sprint_goal: str = field(default="")
    
    # Message type override
    message_type: MessageType = field(default=MessageType.SPRINT_PLANNING, init=False)
    sprint_duration_days: int = field(default=14)
    
    # Planning data
    story_ids: List[str] = field(default_factory=list)
    total_story_points: int = 0
    team_capacity: int = 0
    capacity_utilization: float = 0.0
    
    # Risk assessment
    risks: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    
    def validate(self) -> ValidationResult:
        """Validate sprint planning message."""
        result = ValidationResult(is_valid=True)
        
        if not self.sprint_id:
            result.add_error("sprint_id is required")
        
        if not self.sprint_goal:
            result.add_error("sprint_goal is required")
        
        if self.sprint_duration_days <= 0:
            result.add_error("sprint_duration_days must be positive")
            
        if self.sprint_duration_days > 30:
            result.add_warning("Sprint duration exceeds recommended maximum")
        
        if not self.story_ids:
            result.add_warning("No stories planned for sprint")
        
        if self.capacity_utilization > 1.0:
            result.add_warning("Sprint appears over-committed")
        elif self.capacity_utilization < 0.6:
            result.add_warning("Sprint may be under-committed")
        
        if not self.success_criteria:
            result.add_warning("No success criteria defined")
            
        return result
    
    def _get_specific_fields(self) -> Dict[str, Any]:
        """Get sprint-specific fields."""
        return {
            "sprint_id": self.sprint_id,
            "sprint_goal": self.sprint_goal,
            "sprint_duration_days": self.sprint_duration_days,
            "story_ids": self.story_ids,
            "total_story_points": self.total_story_points,
            "team_capacity": self.team_capacity,
            "capacity_utilization": self.capacity_utilization,
            "risks": self.risks,
            "assumptions": self.assumptions,
            "success_criteria": self.success_criteria
        }


@dataclass
class CodeReviewMessage(AgentMessage):
    """Message for code review coordination."""
    
    # Review details (using defaults to avoid inheritance issues)
    review_id: str = field(default="")
    
    # Message type override
    message_type: MessageType = field(default=MessageType.CODE_REVIEW, init=False)
    pull_request_url: str = field(default="")
    files_changed: List[str] = field(default_factory=list)
    lines_added: int = 0
    lines_removed: int = 0
    
    # Review criteria
    review_type: str = "standard"  # standard, security, performance, architecture
    urgency: str = "normal"  # critical, high, normal, low
    
    # Review results
    approved: Optional[bool] = None
    issues_found: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    def validate(self) -> ValidationResult:
        """Validate code review message."""
        result = ValidationResult(is_valid=True)
        
        if not self.review_id:
            result.add_error("review_id is required")
            
        if not self.files_changed:
            result.add_warning("No files specified for review")
        
        if self.lines_added + self.lines_removed > 500:
            result.add_warning("Large changeset may require additional review time")
        
        if self.approved is False and not self.issues_found:
            result.add_warning("Review rejected but no issues specified")
            
        return result
    
    def _get_specific_fields(self) -> Dict[str, Any]:
        """Get review-specific fields."""
        return {
            "review_id": self.review_id,
            "pull_request_url": self.pull_request_url,
            "files_changed": self.files_changed,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "review_type": self.review_type,
            "urgency": self.urgency,
            "approved": self.approved,
            "issues_found": self.issues_found,
            "suggestions": self.suggestions
        }


@dataclass
class StandupUpdateMessage(AgentMessage):
    """Message for daily standup updates."""
    
    # Agent details (using defaults to avoid inheritance issues)
    agent_name: str = field(default="")
    
    # Message type override
    message_type: MessageType = field(default=MessageType.STANDUP_UPDATE, init=False)
    current_task_id: Optional[str] = field(default=None)
    
    # Progress updates
    completed_yesterday: List[str] = field(default_factory=list)  # Task IDs or descriptions
    planned_today: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    
    # Metrics
    hours_worked_yesterday: float = 0.0
    estimated_hours_today: float = 0.0
    confidence_level: float = 1.0  # 0.0 to 1.0
    
    def validate(self) -> ValidationResult:
        """Validate standup update message."""
        result = ValidationResult(is_valid=True)
        
        if not self.agent_name:
            result.add_error("agent_name is required")
        
        if self.hours_worked_yesterday < 0:
            result.add_error("hours_worked_yesterday cannot be negative")
            
        if self.estimated_hours_today < 0:
            result.add_error("estimated_hours_today cannot be negative")
        
        if not (0.0 <= self.confidence_level <= 1.0):
            result.add_error("confidence_level must be between 0.0 and 1.0")
        
        if self.blockers and not self.planned_today:
            result.add_warning("Agent has blockers but no planned work")
            
        if self.confidence_level < 0.5:
            result.add_warning("Low confidence level may indicate risks")
            
        return result
    
    def _get_specific_fields(self) -> Dict[str, Any]:
        """Get standup-specific fields."""
        return {
            "agent_name": self.agent_name,
            "current_task_id": self.current_task_id,
            "completed_yesterday": self.completed_yesterday,
            "planned_today": self.planned_today,
            "blockers": self.blockers,
            "hours_worked_yesterday": self.hours_worked_yesterday,
            "estimated_hours_today": self.estimated_hours_today,
            "confidence_level": self.confidence_level
        }