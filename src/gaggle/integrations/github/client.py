"""GitHub API client for Gaggle integration."""

import logging
from typing import Any

try:
    import aiohttp
    import jwt

    from github import Github, GithubException

    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

from ...config.settings import GaggleSettings

logger = logging.getLogger(__name__)


class GitHubClient:
    """Async GitHub API client with authentication and rate limiting."""

    def __init__(self, settings: GaggleSettings):
        self.settings = settings
        self.client: Github | None = None
        self.session: aiohttp.ClientSession | None = None

        if not GITHUB_AVAILABLE:
            logger.warning(
                "GitHub dependencies not available. Install with: uv add PyGithub aiohttp PyJWT"
            )

    async def initialize(self) -> bool:
        """Initialize GitHub client with authentication."""
        try:
            if not GITHUB_AVAILABLE:
                return False

            # Initialize PyGithub client
            if self.settings.github_token:
                self.client = Github(self.settings.github_token)
            else:
                logger.error("GitHub token not configured")
                return False

            # Initialize aiohttp session for async operations
            self.session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"token {self.settings.github_token}",
                    "Accept": "application/vnd.github.v3+json",
                }
            )

            # Test authentication
            user = self.client.get_user()
            logger.info(f"GitHub client initialized for user: {user.login}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize GitHub client: {e}")
            return False

    async def close(self) -> None:
        """Clean up resources."""
        if self.session:
            await self.session.close()

    async def get_repository(self, repo_name: str) -> dict[str, Any] | None:
        """Get repository information."""
        try:
            if not self.client:
                return None

            repo = self.client.get_repo(repo_name)
            return {
                "id": repo.id,
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description,
                "url": repo.html_url,
                "clone_url": repo.clone_url,
                "default_branch": repo.default_branch,
                "language": repo.language,
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "open_issues": repo.open_issues_count,
                "created_at": repo.created_at.isoformat() if repo.created_at else None,
                "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
            }
        except GithubException as e:
            logger.error(f"GitHub API error getting repository {repo_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting repository {repo_name}: {e}")
            return None

    async def list_branches(self, repo_name: str) -> list[dict[str, Any]]:
        """List repository branches."""
        try:
            if not self.client:
                return []

            repo = self.client.get_repo(repo_name)
            branches = []

            for branch in repo.get_branches():
                branches.append(
                    {
                        "name": branch.name,
                        "sha": branch.commit.sha,
                        "protected": branch.protected,
                        "commit": {
                            "sha": branch.commit.sha,
                            "message": branch.commit.commit.message,
                            "author": branch.commit.commit.author.name,
                            "date": branch.commit.commit.author.date.isoformat(),
                        },
                    }
                )

            return branches

        except GithubException as e:
            logger.error(f"GitHub API error listing branches for {repo_name}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error listing branches for {repo_name}: {e}")
            return []

    async def create_branch(
        self, repo_name: str, branch_name: str, source_branch: str = "main"
    ) -> bool:
        """Create a new branch from source branch."""
        try:
            if not self.client:
                return False

            repo = self.client.get_repo(repo_name)
            source_ref = repo.get_git_ref(f"heads/{source_branch}")

            repo.create_git_ref(
                ref=f"refs/heads/{branch_name}", sha=source_ref.object.sha
            )

            logger.info(f"Created branch {branch_name} in {repo_name}")
            return True

        except GithubException as e:
            logger.error(
                f"GitHub API error creating branch {branch_name} in {repo_name}: {e}"
            )
            return False
        except Exception as e:
            logger.error(f"Error creating branch {branch_name} in {repo_name}: {e}")
            return False

    async def get_file_content(
        self, repo_name: str, file_path: str, branch: str = "main"
    ) -> str | None:
        """Get file content from repository."""
        try:
            if not self.client:
                return None

            repo = self.client.get_repo(repo_name)
            file_content = repo.get_contents(file_path, ref=branch)

            if isinstance(file_content, list):
                # Directory, not a file
                return None

            return file_content.decoded_content.decode("utf-8")

        except GithubException as e:
            logger.error(
                f"GitHub API error getting file {file_path} from {repo_name}: {e}"
            )
            return None
        except Exception as e:
            logger.error(f"Error getting file {file_path} from {repo_name}: {e}")
            return None

    async def create_or_update_file(
        self,
        repo_name: str,
        file_path: str,
        content: str,
        commit_message: str,
        branch: str = "main",
    ) -> bool:
        """Create or update a file in the repository."""
        try:
            if not self.client:
                return False

            repo = self.client.get_repo(repo_name)

            try:
                # Try to get existing file
                existing_file = repo.get_contents(file_path, ref=branch)
                # Update existing file
                repo.update_file(
                    path=file_path,
                    message=commit_message,
                    content=content,
                    sha=existing_file.sha,
                    branch=branch,
                )
                logger.info(f"Updated file {file_path} in {repo_name}")

            except GithubException:
                # File doesn't exist, create it
                repo.create_file(
                    path=file_path,
                    message=commit_message,
                    content=content,
                    branch=branch,
                )
                logger.info(f"Created file {file_path} in {repo_name}")

            return True

        except GithubException as e:
            logger.error(
                f"GitHub API error creating/updating file {file_path} in {repo_name}: {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Error creating/updating file {file_path} in {repo_name}: {e}"
            )
            return False

    async def get_rate_limit(self) -> dict[str, Any]:
        """Get current rate limit status."""
        try:
            if not self.client:
                return {}

            rate_limit = self.client.get_rate_limit()
            return {
                "core": {
                    "limit": rate_limit.core.limit,
                    "remaining": rate_limit.core.remaining,
                    "reset": rate_limit.core.reset.isoformat(),
                    "used": rate_limit.core.used,
                },
                "search": {
                    "limit": rate_limit.search.limit,
                    "remaining": rate_limit.search.remaining,
                    "reset": rate_limit.search.reset.isoformat(),
                    "used": rate_limit.search.used,
                },
            }

        except GithubException as e:
            logger.error(f"GitHub API error getting rate limit: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error getting rate limit: {e}")
            return {}

    def is_authenticated(self) -> bool:
        """Check if client is properly authenticated."""
        try:
            if not self.client:
                return False
            user = self.client.get_user()
            return user is not None
        except:
            return False
