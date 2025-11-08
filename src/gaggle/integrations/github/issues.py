"""Issue management for GitHub integration."""

import logging
from typing import Any

try:
    from github import GithubException

    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

from .client import GitHubClient

logger = logging.getLogger(__name__)


class IssueManager:
    """Manages GitHub issues for Gaggle sprints and user stories."""

    def __init__(self, github_client: GitHubClient):
        self.client = github_client

    async def create_issue(
        self,
        repo_name: str,
        title: str,
        body: str,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
        milestone: str | None = None,
    ) -> dict[str, Any] | None:
        """Create a new GitHub issue."""
        try:
            if not self.client.client:
                logger.error("GitHub client not initialized")
                return None

            repo = self.client.client.get_repo(repo_name)

            # Get label objects
            issue_labels = []
            if labels:
                for label_name in labels:
                    try:
                        label = repo.get_label(label_name)
                        issue_labels.append(label)
                    except GithubException:
                        # Create label if it doesn't exist
                        logger.info(f"Creating label: {label_name}")
                        label = repo.create_label(label_name, "0366d6")
                        issue_labels.append(label)

            # Get milestone object
            milestone_obj = None
            if milestone:
                try:
                    milestones = repo.get_milestones(state="open")
                    milestone_obj = next(
                        (m for m in milestones if m.title == milestone), None
                    )
                except GithubException:
                    logger.warning(f"Milestone not found: {milestone}")

            # Create issue
            issue = repo.create_issue(
                title=title,
                body=body,
                labels=issue_labels,
                assignees=assignees or [],
                milestone=milestone_obj,
            )

            logger.info(f"Created issue #{issue.number}: {title}")

            return {
                "number": issue.number,
                "id": issue.id,
                "title": issue.title,
                "body": issue.body,
                "state": issue.state,
                "url": issue.html_url,
                "author": issue.user.login,
                "assignees": [assignee.login for assignee in issue.assignees],
                "labels": [label.name for label in issue.labels],
                "milestone": issue.milestone.title if issue.milestone else None,
                "created_at": issue.created_at.isoformat(),
                "updated_at": (
                    issue.updated_at.isoformat() if issue.updated_at else None
                ),
                "closed_at": issue.closed_at.isoformat() if issue.closed_at else None,
                "comments": issue.comments,
            }

        except GithubException as e:
            logger.error(f"GitHub API error creating issue: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating issue: {e}")
            return None

    async def list_issues(
        self,
        repo_name: str,
        state: str = "open",
        labels: list[str] | None = None,
        assignee: str | None = None,
        milestone: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List issues with filtering options."""
        try:
            if not self.client.client:
                return []

            repo = self.client.client.get_repo(repo_name)
            issues = []

            # Build filter parameters
            kwargs = {"state": state}
            if labels:
                kwargs["labels"] = labels
            if assignee:
                kwargs["assignee"] = assignee
            if milestone:
                kwargs["milestone"] = milestone

            issue_list = repo.get_issues(**kwargs)[:limit]

            for issue in issue_list:
                # Skip pull requests (they appear as issues in GitHub API)
                if issue.pull_request:
                    continue

                issues.append(
                    {
                        "number": issue.number,
                        "id": issue.id,
                        "title": issue.title,
                        "body": issue.body,
                        "state": issue.state,
                        "url": issue.html_url,
                        "author": issue.user.login,
                        "assignees": [assignee.login for assignee in issue.assignees],
                        "labels": [label.name for label in issue.labels],
                        "milestone": issue.milestone.title if issue.milestone else None,
                        "created_at": issue.created_at.isoformat(),
                        "updated_at": (
                            issue.updated_at.isoformat() if issue.updated_at else None
                        ),
                        "closed_at": (
                            issue.closed_at.isoformat() if issue.closed_at else None
                        ),
                        "comments": issue.comments,
                    }
                )

            return issues

        except GithubException as e:
            logger.error(f"GitHub API error listing issues: {e}")
            return []
        except Exception as e:
            logger.error(f"Error listing issues: {e}")
            return []

    async def get_issue(
        self, repo_name: str, issue_number: int
    ) -> dict[str, Any] | None:
        """Get detailed information about a specific issue."""
        try:
            if not self.client.client:
                return None

            repo = self.client.client.get_repo(repo_name)
            issue = repo.get_issue(issue_number)

            # Get comments
            comments = []
            for comment in issue.get_comments():
                comments.append(
                    {
                        "id": comment.id,
                        "author": comment.user.login,
                        "body": comment.body,
                        "created_at": comment.created_at.isoformat(),
                        "updated_at": (
                            comment.updated_at.isoformat()
                            if comment.updated_at
                            else None
                        ),
                    }
                )

            # Get events (status changes, labels, etc.)
            events = []
            for event in issue.get_events():
                events.append(
                    {
                        "id": event.id,
                        "event": event.event,
                        "actor": event.actor.login if event.actor else None,
                        "created_at": event.created_at.isoformat(),
                        "label": event.label.name if event.label else None,
                    }
                )

            return {
                "number": issue.number,
                "id": issue.id,
                "title": issue.title,
                "body": issue.body,
                "state": issue.state,
                "url": issue.html_url,
                "author": issue.user.login,
                "assignees": [assignee.login for assignee in issue.assignees],
                "labels": [label.name for label in issue.labels],
                "milestone": issue.milestone.title if issue.milestone else None,
                "created_at": issue.created_at.isoformat(),
                "updated_at": (
                    issue.updated_at.isoformat() if issue.updated_at else None
                ),
                "closed_at": issue.closed_at.isoformat() if issue.closed_at else None,
                "comments_data": comments,
                "events": events,
                "comments_count": issue.comments,
                "locked": issue.locked,
                "reactions": {
                    "+1": (
                        issue.get_reactions()["+1"]
                        if hasattr(issue, "get_reactions")
                        else 0
                    ),
                    "-1": (
                        issue.get_reactions()["-1"]
                        if hasattr(issue, "get_reactions")
                        else 0
                    ),
                    "laugh": (
                        issue.get_reactions()["laugh"]
                        if hasattr(issue, "get_reactions")
                        else 0
                    ),
                    "hooray": (
                        issue.get_reactions()["hooray"]
                        if hasattr(issue, "get_reactions")
                        else 0
                    ),
                    "confused": (
                        issue.get_reactions()["confused"]
                        if hasattr(issue, "get_reactions")
                        else 0
                    ),
                    "heart": (
                        issue.get_reactions()["heart"]
                        if hasattr(issue, "get_reactions")
                        else 0
                    ),
                    "rocket": (
                        issue.get_reactions()["rocket"]
                        if hasattr(issue, "get_reactions")
                        else 0
                    ),
                    "eyes": (
                        issue.get_reactions()["eyes"]
                        if hasattr(issue, "get_reactions")
                        else 0
                    ),
                },
            }

        except GithubException as e:
            logger.error(f"GitHub API error getting issue #{issue_number}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting issue #{issue_number}: {e}")
            return None

    async def update_issue(
        self,
        repo_name: str,
        issue_number: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
    ) -> bool:
        """Update issue details."""
        try:
            if not self.client.client:
                return False

            repo = self.client.client.get_repo(repo_name)
            issue = repo.get_issue(issue_number)

            update_data = {}
            if title is not None:
                update_data["title"] = title
            if body is not None:
                update_data["body"] = body
            if state is not None:
                update_data["state"] = state
            if assignees is not None:
                update_data["assignees"] = assignees

            if labels is not None:
                # Get or create label objects
                label_objects = []
                for label_name in labels:
                    try:
                        label = repo.get_label(label_name)
                        label_objects.append(label)
                    except GithubException:
                        # Create label if it doesn't exist
                        label = repo.create_label(label_name, "0366d6")
                        label_objects.append(label)
                update_data["labels"] = label_objects

            if update_data:
                issue.edit(**update_data)
                logger.info(f"Updated issue #{issue_number}")
                return True

            return True

        except GithubException as e:
            logger.error(f"GitHub API error updating issue #{issue_number}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error updating issue #{issue_number}: {e}")
            return False

    async def close_issue(
        self, repo_name: str, issue_number: int, comment: str | None = None
    ) -> bool:
        """Close an issue with optional comment."""
        try:
            if not self.client.client:
                return False

            repo = self.client.client.get_repo(repo_name)
            issue = repo.get_issue(issue_number)

            # Add closing comment if provided
            if comment:
                issue.create_comment(comment)

            # Close the issue
            issue.edit(state="closed")

            logger.info(f"Closed issue #{issue_number}")
            return True

        except GithubException as e:
            logger.error(f"GitHub API error closing issue #{issue_number}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error closing issue #{issue_number}: {e}")
            return False

    async def add_comment(
        self, repo_name: str, issue_number: int, comment: str
    ) -> bool:
        """Add a comment to an issue."""
        try:
            if not self.client.client:
                return False

            repo = self.client.client.get_repo(repo_name)
            issue = repo.get_issue(issue_number)

            issue.create_comment(comment)
            logger.info(f"Added comment to issue #{issue_number}")
            return True

        except GithubException as e:
            logger.error(
                f"GitHub API error adding comment to issue #{issue_number}: {e}"
            )
            return False
        except Exception as e:
            logger.error(f"Error adding comment to issue #{issue_number}: {e}")
            return False

    async def create_user_story_issue(
        self,
        repo_name: str,
        story_title: str,
        description: str,
        acceptance_criteria: list[str],
        story_points: int | None = None,
        sprint_label: str | None = None,
    ) -> dict[str, Any] | None:
        """Create a GitHub issue for a user story."""

        # Format issue body
        body_parts = ["## User Story", description, "", "## Acceptance Criteria", ""]

        for i, criteria in enumerate(acceptance_criteria, 1):
            body_parts.append(f"{i}. {criteria}")

        if story_points:
            body_parts.extend(["", f"**Story Points:** {story_points}"])

        body_parts.extend(["", "---", "*Created by Gaggle Sprint Assistant*"])

        body = "\n".join(body_parts)

        # Set labels
        labels = ["user-story"]
        if sprint_label:
            labels.append(sprint_label)
        if story_points:
            labels.append(f"story-points-{story_points}")

        return await self.create_issue(
            repo_name=repo_name, title=story_title, body=body, labels=labels
        )

    async def create_bug_issue(
        self,
        repo_name: str,
        bug_title: str,
        description: str,
        steps_to_reproduce: list[str],
        expected_behavior: str,
        actual_behavior: str,
        environment: str | None = None,
        severity: str | None = None,
    ) -> dict[str, Any] | None:
        """Create a GitHub issue for a bug report."""

        body_parts = [
            "## Bug Description",
            description,
            "",
            "## Steps to Reproduce",
            "",
        ]

        for i, step in enumerate(steps_to_reproduce, 1):
            body_parts.append(f"{i}. {step}")

        body_parts.extend(
            [
                "",
                "## Expected Behavior",
                expected_behavior,
                "",
                "## Actual Behavior",
                actual_behavior,
            ]
        )

        if environment:
            body_parts.extend(["", "## Environment", environment])

        body_parts.extend(["", "---", "*Created by Gaggle Sprint Assistant*"])

        body = "\n".join(body_parts)

        # Set labels
        labels = ["bug"]
        if severity:
            labels.append(f"severity-{severity}")

        return await self.create_issue(
            repo_name=repo_name, title=bug_title, body=body, labels=labels
        )
