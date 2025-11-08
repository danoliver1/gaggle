"""Pull request management for GitHub integration."""

import logging
from typing import Any

try:
    from github import GithubException

    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

from .client import GitHubClient

logger = logging.getLogger(__name__)


class PullRequestManager:
    """Manages GitHub pull requests for Gaggle sprints."""

    def __init__(self, github_client: GitHubClient):
        self.client = github_client

    async def create_pull_request(
        self,
        repo_name: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
        draft: bool = False,
    ) -> dict[str, Any] | None:
        """Create a new pull request."""
        try:
            if not self.client.client:
                logger.error("GitHub client not initialized")
                return None

            repo = self.client.client.get_repo(repo_name)

            pr = repo.create_pull(
                title=title, body=body, head=head_branch, base=base_branch, draft=draft
            )

            logger.info(f"Created PR #{pr.number}: {title}")

            return {
                "number": pr.number,
                "id": pr.id,
                "title": pr.title,
                "body": pr.body,
                "state": pr.state,
                "draft": pr.draft,
                "url": pr.html_url,
                "head": {"ref": pr.head.ref, "sha": pr.head.sha},
                "base": {"ref": pr.base.ref, "sha": pr.base.sha},
                "author": pr.user.login,
                "created_at": pr.created_at.isoformat(),
                "mergeable": pr.mergeable,
                "merged": pr.merged,
            }

        except GithubException as e:
            logger.error(f"GitHub API error creating PR: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating PR: {e}")
            return None

    async def list_pull_requests(
        self, repo_name: str, state: str = "open", limit: int = 30
    ) -> list[dict[str, Any]]:
        """List pull requests for a repository."""
        try:
            if not self.client.client:
                return []

            repo = self.client.client.get_repo(repo_name)
            pull_requests = []

            prs = repo.get_pulls(state=state)[:limit]

            for pr in prs:
                pull_requests.append(
                    {
                        "number": pr.number,
                        "id": pr.id,
                        "title": pr.title,
                        "state": pr.state,
                        "draft": pr.draft,
                        "url": pr.html_url,
                        "head_ref": pr.head.ref,
                        "base_ref": pr.base.ref,
                        "author": pr.user.login,
                        "created_at": pr.created_at.isoformat(),
                        "updated_at": (
                            pr.updated_at.isoformat() if pr.updated_at else None
                        ),
                        "mergeable": pr.mergeable,
                        "merged": pr.merged,
                        "comments": pr.comments,
                        "review_comments": pr.review_comments,
                        "commits": pr.commits,
                        "additions": pr.additions,
                        "deletions": pr.deletions,
                        "changed_files": pr.changed_files,
                    }
                )

            return pull_requests

        except GithubException as e:
            logger.error(f"GitHub API error listing PRs: {e}")
            return []
        except Exception as e:
            logger.error(f"Error listing PRs: {e}")
            return []

    async def get_pull_request(
        self, repo_name: str, pr_number: int
    ) -> dict[str, Any] | None:
        """Get detailed information about a specific pull request."""
        try:
            if not self.client.client:
                return None

            repo = self.client.client.get_repo(repo_name)
            pr = repo.get_pull(pr_number)

            # Get additional details
            files_changed = []
            for file in pr.get_files():
                files_changed.append(
                    {
                        "filename": file.filename,
                        "status": file.status,
                        "additions": file.additions,
                        "deletions": file.deletions,
                        "changes": file.changes,
                        "patch": file.patch,
                    }
                )

            reviews = []
            for review in pr.get_reviews():
                reviews.append(
                    {
                        "id": review.id,
                        "user": review.user.login,
                        "state": review.state,
                        "body": review.body,
                        "submitted_at": (
                            review.submitted_at.isoformat()
                            if review.submitted_at
                            else None
                        ),
                    }
                )

            return {
                "number": pr.number,
                "id": pr.id,
                "title": pr.title,
                "body": pr.body,
                "state": pr.state,
                "draft": pr.draft,
                "url": pr.html_url,
                "head": {
                    "ref": pr.head.ref,
                    "sha": pr.head.sha,
                    "repo": pr.head.repo.full_name if pr.head.repo else None,
                },
                "base": {
                    "ref": pr.base.ref,
                    "sha": pr.base.sha,
                    "repo": pr.base.repo.full_name if pr.base.repo else None,
                },
                "author": pr.user.login,
                "assignees": [assignee.login for assignee in pr.assignees],
                "labels": [label.name for label in pr.labels],
                "milestone": pr.milestone.title if pr.milestone else None,
                "created_at": pr.created_at.isoformat(),
                "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
                "closed_at": pr.closed_at.isoformat() if pr.closed_at else None,
                "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
                "merge_commit_sha": pr.merge_commit_sha,
                "mergeable": pr.mergeable,
                "merged": pr.merged,
                "mergeable_state": pr.mergeable_state,
                "comments": pr.comments,
                "review_comments": pr.review_comments,
                "commits": pr.commits,
                "additions": pr.additions,
                "deletions": pr.deletions,
                "changed_files": pr.changed_files,
                "files": files_changed,
                "reviews": reviews,
            }

        except GithubException as e:
            logger.error(f"GitHub API error getting PR #{pr_number}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting PR #{pr_number}: {e}")
            return None

    async def update_pull_request(
        self,
        repo_name: str,
        pr_number: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
    ) -> bool:
        """Update pull request details."""
        try:
            if not self.client.client:
                return False

            repo = self.client.client.get_repo(repo_name)
            pr = repo.get_pull(pr_number)

            update_data = {}
            if title is not None:
                update_data["title"] = title
            if body is not None:
                update_data["body"] = body
            if state is not None:
                update_data["state"] = state

            if update_data:
                pr.edit(**update_data)
                logger.info(f"Updated PR #{pr_number}")
                return True

            return True

        except GithubException as e:
            logger.error(f"GitHub API error updating PR #{pr_number}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error updating PR #{pr_number}: {e}")
            return False

    async def merge_pull_request(
        self,
        repo_name: str,
        pr_number: int,
        commit_message: str | None = None,
        merge_method: str = "merge",
    ) -> bool:
        """Merge a pull request."""
        try:
            if not self.client.client:
                return False

            repo = self.client.client.get_repo(repo_name)
            pr = repo.get_pull(pr_number)

            if not pr.mergeable:
                logger.error(f"PR #{pr_number} is not mergeable")
                return False

            merge_result = pr.merge(
                commit_message=commit_message, merge_method=merge_method
            )

            if merge_result.merged:
                logger.info(f"Successfully merged PR #{pr_number}")
                return True
            else:
                logger.error(f"Failed to merge PR #{pr_number}: {merge_result.message}")
                return False

        except GithubException as e:
            logger.error(f"GitHub API error merging PR #{pr_number}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error merging PR #{pr_number}: {e}")
            return False

    async def add_review_comment(
        self,
        repo_name: str,
        pr_number: int,
        body: str,
        path: str | None = None,
        position: int | None = None,
    ) -> bool:
        """Add a review comment to a pull request."""
        try:
            if not self.client.client:
                return False

            repo = self.client.client.get_repo(repo_name)
            pr = repo.get_pull(pr_number)

            if path and position:
                # Line-specific review comment
                pr.create_review_comment(body=body, path=path, position=position)
            else:
                # General comment
                pr.create_issue_comment(body=body)

            logger.info(f"Added review comment to PR #{pr_number}")
            return True

        except GithubException as e:
            logger.error(f"GitHub API error adding comment to PR #{pr_number}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error adding comment to PR #{pr_number}: {e}")
            return False

    async def create_review(
        self,
        repo_name: str,
        pr_number: int,
        event: str,  # 'APPROVE', 'REQUEST_CHANGES', 'COMMENT'
        body: str | None = None,
        comments: list[dict[str, Any]] | None = None,
    ) -> bool:
        """Create a review for a pull request."""
        try:
            if not self.client.client:
                return False

            repo = self.client.client.get_repo(repo_name)
            pr = repo.get_pull(pr_number)

            review_comments = []
            if comments:
                for comment in comments:
                    review_comments.append(
                        {
                            "path": comment["path"],
                            "position": comment["position"],
                            "body": comment["body"],
                        }
                    )

            pr.create_review(body=body, event=event, comments=review_comments)

            logger.info(f"Created review for PR #{pr_number} with event: {event}")
            return True

        except GithubException as e:
            logger.error(f"GitHub API error creating review for PR #{pr_number}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error creating review for PR #{pr_number}: {e}")
            return False

    async def get_pr_template(self, repo_name: str) -> str | None:
        """Get pull request template from repository."""
        template_paths = [
            ".github/pull_request_template.md",
            ".github/PULL_REQUEST_TEMPLATE.md",
            "docs/pull_request_template.md",
            "PULL_REQUEST_TEMPLATE.md",
        ]

        for path in template_paths:
            content = await self.client.get_file_content(repo_name, path)
            if content:
                return content

        return None

    async def generate_pr_body(
        self, sprint_id: str, story_ids: list[str], changes_summary: str
    ) -> str:
        """Generate a pull request body for sprint work."""
        body_parts = [f"## Sprint: {sprint_id}", "", "### User Stories", ""]

        for story_id in story_ids:
            body_parts.append(f"- Closes #{story_id}")

        body_parts.extend(
            [
                "",
                "### Changes Summary",
                changes_summary,
                "",
                "### Test Plan",
                "- [ ] Unit tests pass",
                "- [ ] Integration tests pass",
                "- [ ] Manual testing completed",
                "",
                "### Checklist",
                "- [ ] Code follows project style guidelines",
                "- [ ] Self-review completed",
                "- [ ] Documentation updated if needed",
                "- [ ] No breaking changes introduced",
                "",
                "🤖 Generated by Gaggle Sprint Assistant",
            ]
        )

        return "\n".join(body_parts)
