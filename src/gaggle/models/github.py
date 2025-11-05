"""GitHub integration models."""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl


class IssueState(str, Enum):
    """GitHub issue state."""
    OPEN = "open"
    CLOSED = "closed"


class PullRequestState(str, Enum):
    """GitHub pull request state."""
    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"


class ProjectBoardColumnType(str, Enum):
    """Project board column types."""
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"


class GitHubRepository(BaseModel):
    """GitHub repository configuration."""
    
    owner: str = Field(..., description="Repository owner")
    name: str = Field(..., description="Repository name")
    full_name: str = Field(..., description="Full repository name (owner/name)")
    
    # Repository metadata
    id: Optional[int] = None
    description: Optional[str] = None
    private: bool = Field(False, description="Whether repository is private")
    
    # URLs
    html_url: Optional[HttpUrl] = None
    clone_url: Optional[HttpUrl] = None
    
    # Branch configuration
    default_branch: str = Field("main", description="Default branch name")
    
    # Integration settings
    auto_create_issues: bool = Field(True, description="Auto-create issues for stories/tasks")
    auto_create_prs: bool = Field(True, description="Auto-create pull requests")
    auto_merge_approved: bool = Field(False, description="Auto-merge approved PRs")
    
    # Project board configuration
    project_board_id: Optional[int] = None
    milestone_prefix: str = Field("Sprint", description="Prefix for milestone names")
    
    @property
    def api_url(self) -> str:
        """Get the GitHub API URL for this repository."""
        return f"https://api.github.com/repos/{self.full_name}"
    
    @classmethod
    def from_url(cls, repo_url: str) -> "GitHubRepository":
        """Create repository from GitHub URL."""
        # Parse GitHub URL to extract owner and name
        if repo_url.startswith("https://github.com/"):
            parts = repo_url.replace("https://github.com/", "").split("/")
            if len(parts) >= 2:
                owner, name = parts[0], parts[1].replace(".git", "")
                return cls(
                    owner=owner,
                    name=name,
                    full_name=f"{owner}/{name}",
                    html_url=repo_url
                )
        
        raise ValueError(f"Invalid GitHub repository URL: {repo_url}")


class Issue(BaseModel):
    """GitHub issue model."""
    
    id: Optional[int] = None
    number: Optional[int] = None
    title: str = Field(..., description="Issue title")
    body: Optional[str] = None
    state: IssueState = Field(IssueState.OPEN)
    
    # Labels and metadata
    labels: List[str] = Field(default_factory=list)
    assignees: List[str] = Field(default_factory=list)
    milestone: Optional[str] = None
    
    # Links to Gaggle entities
    story_id: Optional[str] = None
    task_id: Optional[str] = None
    sprint_id: Optional[str] = None
    
    # GitHub metadata
    html_url: Optional[HttpUrl] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    
    # Comments and activity
    comments_count: int = Field(0)
    
    def add_label(self, label: str) -> None:
        """Add a label to the issue."""
        if label not in self.labels:
            self.labels.append(label)
    
    def remove_label(self, label: str) -> None:
        """Remove a label from the issue."""
        if label in self.labels:
            self.labels.remove(label)
    
    def assign_to(self, assignee: str) -> None:
        """Assign the issue to someone."""
        if assignee not in self.assignees:
            self.assignees.append(assignee)
    
    def unassign_from(self, assignee: str) -> None:
        """Unassign the issue from someone."""
        if assignee in self.assignees:
            self.assignees.remove(assignee)


class PullRequest(BaseModel):
    """GitHub pull request model."""
    
    id: Optional[int] = None
    number: Optional[int] = None
    title: str = Field(..., description="Pull request title")
    body: Optional[str] = None
    state: PullRequestState = Field(PullRequestState.OPEN)
    
    # Branch information
    head_branch: str = Field(..., description="Source branch")
    base_branch: str = Field("main", description="Target branch")
    
    # Review information
    reviewers: List[str] = Field(default_factory=list)
    approved_by: List[str] = Field(default_factory=list)
    changes_requested_by: List[str] = Field(default_factory=list)
    
    # Links to Gaggle entities
    task_ids: List[str] = Field(default_factory=list, description="Related task IDs")
    story_id: Optional[str] = None
    sprint_id: Optional[str] = None
    
    # GitHub metadata
    html_url: Optional[HttpUrl] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    merged_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    
    # Code changes
    additions: int = Field(0, description="Lines added")
    deletions: int = Field(0, description="Lines deleted")
    changed_files: int = Field(0, description="Number of files changed")
    
    # CI/CD status
    checks_passed: bool = Field(False, description="Whether all checks passed")
    
    def add_reviewer(self, reviewer: str) -> None:
        """Add a reviewer to the pull request."""
        if reviewer not in self.reviewers:
            self.reviewers.append(reviewer)
    
    def approve(self, reviewer: str) -> None:
        """Mark as approved by a reviewer."""
        if reviewer not in self.approved_by:
            self.approved_by.append(reviewer)
        
        # Remove from changes requested if present
        if reviewer in self.changes_requested_by:
            self.changes_requested_by.remove(reviewer)
    
    def request_changes(self, reviewer: str) -> None:
        """Request changes from a reviewer."""
        if reviewer not in self.changes_requested_by:
            self.changes_requested_by.append(reviewer)
        
        # Remove from approved if present
        if reviewer in self.approved_by:
            self.approved_by.remove(reviewer)
    
    def is_approved(self) -> bool:
        """Check if pull request is approved."""
        return (
            len(self.approved_by) > 0 and
            len(self.changes_requested_by) == 0 and
            self.checks_passed
        )
    
    def can_be_merged(self) -> bool:
        """Check if pull request can be merged."""
        return (
            self.state == PullRequestState.OPEN and
            self.is_approved()
        )


class ProjectBoardColumn(BaseModel):
    """Project board column."""
    
    id: Optional[int] = None
    name: str = Field(..., description="Column name")
    column_type: ProjectBoardColumnType = Field(..., description="Column type")
    position: int = Field(0, description="Column position")
    
    # Cards in this column
    issue_ids: List[int] = Field(default_factory=list)
    
    def add_issue(self, issue_id: int) -> None:
        """Add an issue to this column."""
        if issue_id not in self.issue_ids:
            self.issue_ids.append(issue_id)
    
    def remove_issue(self, issue_id: int) -> None:
        """Remove an issue from this column."""
        if issue_id in self.issue_ids:
            self.issue_ids.remove(issue_id)


class ProjectBoard(BaseModel):
    """GitHub project board for sprint management."""
    
    id: Optional[int] = None
    name: str = Field(..., description="Project board name")
    description: Optional[str] = None
    
    # Board configuration
    columns: List[ProjectBoardColumn] = Field(default_factory=list)
    
    # Links to Gaggle entities
    sprint_id: Optional[str] = None
    repository_id: Optional[int] = None
    
    # GitHub metadata
    html_url: Optional[HttpUrl] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def add_column(self, column: ProjectBoardColumn) -> None:
        """Add a column to the board."""
        if column.name not in [c.name for c in self.columns]:
            column.position = len(self.columns)
            self.columns.append(column)
    
    def get_column_by_type(self, column_type: ProjectBoardColumnType) -> Optional[ProjectBoardColumn]:
        """Get column by type."""
        return next((c for c in self.columns if c.column_type == column_type), None)
    
    def move_issue(self, issue_id: int, to_column_type: ProjectBoardColumnType) -> None:
        """Move an issue from one column to another."""
        # Remove from all columns
        for column in self.columns:
            column.remove_issue(issue_id)
        
        # Add to target column
        target_column = self.get_column_by_type(to_column_type)
        if target_column:
            target_column.add_issue(issue_id)
    
    def get_board_summary(self) -> Dict[str, Any]:
        """Get summary of the board."""
        summary = {
            "board_id": self.id,
            "board_name": self.name,
            "sprint_id": self.sprint_id,
            "total_issues": sum(len(col.issue_ids) for col in self.columns),
            "columns": []
        }
        
        for column in self.columns:
            summary["columns"].append({
                "name": column.name,
                "type": column.column_type.value,
                "issue_count": len(column.issue_ids),
                "position": column.position
            })
        
        return summary
    
    @classmethod
    def create_sprint_board(cls, sprint_id: str, sprint_name: str) -> "ProjectBoard":
        """Create a project board for a sprint."""
        board = cls(
            name=f"Sprint Board - {sprint_name}",
            description=f"Project board for sprint {sprint_id}",
            sprint_id=sprint_id
        )
        
        # Add default columns
        default_columns = [
            ProjectBoardColumn(
                name="Product Backlog",
                column_type=ProjectBoardColumnType.BACKLOG
            ),
            ProjectBoardColumn(
                name="Sprint Backlog", 
                column_type=ProjectBoardColumnType.TODO
            ),
            ProjectBoardColumn(
                name="In Progress",
                column_type=ProjectBoardColumnType.IN_PROGRESS
            ),
            ProjectBoardColumn(
                name="In Review",
                column_type=ProjectBoardColumnType.IN_REVIEW
            ),
            ProjectBoardColumn(
                name="Done",
                column_type=ProjectBoardColumnType.DONE
            ),
        ]
        
        for column in default_columns:
            board.add_column(column)
        
        return board


class GitHubIntegrationConfig(BaseModel):
    """Configuration for GitHub integration."""
    
    repository: GitHubRepository
    
    # Authentication
    token: str = Field(..., description="GitHub personal access token")
    
    # Integration settings
    create_issues_for_stories: bool = True
    create_issues_for_tasks: bool = True
    create_pull_requests: bool = True
    create_project_boards: bool = True
    create_milestones: bool = True
    
    # Branch strategy
    branch_prefix: str = Field("gaggle/", description="Prefix for branches created by Gaggle")
    main_branch: str = Field("main", description="Main branch name")
    
    # Labels
    story_label: str = "user-story"
    task_label: str = "task"
    sprint_label_prefix: str = "sprint-"
    
    # Review settings
    require_code_review: bool = True
    auto_assign_reviewers: bool = True
    default_reviewers: List[str] = Field(default_factory=list)
    
    def get_story_labels(self, story) -> List[str]:
        """Get labels for a story."""
        labels = [self.story_label]
        
        if hasattr(story, 'priority'):
            labels.append(f"priority-{story.priority.value}")
        
        if hasattr(story, 'sprint_id') and story.sprint_id:
            labels.append(f"{self.sprint_label_prefix}{story.sprint_id}")
        
        return labels
    
    def get_task_labels(self, task) -> List[str]:
        """Get labels for a task."""
        labels = [self.task_label]
        
        if hasattr(task, 'task_type'):
            labels.append(f"type-{task.task_type.value}")
        
        if hasattr(task, 'complexity'):
            labels.append(f"complexity-{task.complexity.value}")
        
        if hasattr(task, 'sprint_id') and task.sprint_id:
            labels.append(f"{self.sprint_label_prefix}{task.sprint_id}")
        
        return labels