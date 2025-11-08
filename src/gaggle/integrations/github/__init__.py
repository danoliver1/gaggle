"""GitHub integration module for Gaggle."""

from .client import GitHubClient
from .issues import IssueManager
from .projects import ProjectManager
from .pull_requests import PullRequestManager

__all__ = ["GitHubClient", "PullRequestManager", "IssueManager", "ProjectManager"]
