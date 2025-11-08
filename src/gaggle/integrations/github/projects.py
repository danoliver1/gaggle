"""GitHub Projects management for sprint boards."""

import logging
from datetime import datetime
from typing import Any

try:
    from github import GithubException

    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

from .client import GitHubClient

logger = logging.getLogger(__name__)


class ProjectManager:
    """Manages GitHub Projects for Gaggle sprint boards."""

    def __init__(self, github_client: GitHubClient):
        self.client = github_client

    async def create_project_board(
        self,
        repo_name: str,
        name: str,
        description: str,
        columns: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Create a new project board for sprint tracking."""
        try:
            if not self.client.client:
                logger.error("GitHub client not initialized")
                return None

            repo = self.client.client.get_repo(repo_name)

            # Create project board
            project = repo.create_project(name=name, body=description)

            # Create default columns if not specified
            if not columns:
                columns = ["Backlog", "Todo", "In Progress", "Review", "Done"]

            # Create columns
            created_columns = []
            for column_name in columns:
                column = project.create_column(column_name)
                created_columns.append(
                    {"id": column.id, "name": column.name, "url": column.url}
                )

            logger.info(f"Created project board: {name}")

            return {
                "id": project.id,
                "name": project.name,
                "body": project.body,
                "url": project.html_url,
                "state": project.state,
                "created_at": project.created_at.isoformat(),
                "updated_at": (
                    project.updated_at.isoformat() if project.updated_at else None
                ),
                "columns": created_columns,
            }

        except GithubException as e:
            logger.error(f"GitHub API error creating project board: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating project board: {e}")
            return None

    async def list_project_boards(self, repo_name: str) -> list[dict[str, Any]]:
        """List all project boards for a repository."""
        try:
            if not self.client.client:
                return []

            repo = self.client.client.get_repo(repo_name)
            projects = []

            for project in repo.get_projects():
                # Get columns for this project
                columns = []
                for column in project.get_columns():
                    columns.append(
                        {"id": column.id, "name": column.name, "url": column.url}
                    )

                projects.append(
                    {
                        "id": project.id,
                        "name": project.name,
                        "body": project.body,
                        "url": project.html_url,
                        "state": project.state,
                        "created_at": project.created_at.isoformat(),
                        "updated_at": (
                            project.updated_at.isoformat()
                            if project.updated_at
                            else None
                        ),
                        "columns": columns,
                    }
                )

            return projects

        except GithubException as e:
            logger.error(f"GitHub API error listing project boards: {e}")
            return []
        except Exception as e:
            logger.error(f"Error listing project boards: {e}")
            return []

    async def get_project_board(
        self, repo_name: str, project_id: int
    ) -> dict[str, Any] | None:
        """Get detailed information about a specific project board."""
        try:
            if not self.client.client:
                return None

            repo = self.client.client.get_repo(repo_name)
            project = repo.get_project(project_id)

            # Get columns and their cards
            columns = []
            for column in project.get_columns():
                cards = []
                for card in column.get_cards():
                    card_data = {
                        "id": card.id,
                        "note": card.note,
                        "created_at": card.created_at.isoformat(),
                        "updated_at": (
                            card.updated_at.isoformat() if card.updated_at else None
                        ),
                    }

                    # If card represents an issue
                    if card.content_url:
                        # Extract issue/PR info from URL
                        if "/issues/" in card.content_url:
                            issue_number = card.content_url.split("/issues/")[-1]
                            try:
                                issue = repo.get_issue(int(issue_number))
                                card_data["issue"] = {
                                    "number": issue.number,
                                    "title": issue.title,
                                    "state": issue.state,
                                    "assignees": [a.login for a in issue.assignees],
                                    "labels": [l.name for l in issue.labels],
                                }
                            except:
                                pass
                        elif "/pull/" in card.content_url:
                            pr_number = card.content_url.split("/pull/")[-1]
                            try:
                                pr = repo.get_pull(int(pr_number))
                                card_data["pull_request"] = {
                                    "number": pr.number,
                                    "title": pr.title,
                                    "state": pr.state,
                                    "draft": pr.draft,
                                    "assignees": [a.login for a in pr.assignees],
                                }
                            except:
                                pass

                    cards.append(card_data)

                columns.append(
                    {
                        "id": column.id,
                        "name": column.name,
                        "url": column.url,
                        "cards": cards,
                    }
                )

            return {
                "id": project.id,
                "name": project.name,
                "body": project.body,
                "url": project.html_url,
                "state": project.state,
                "created_at": project.created_at.isoformat(),
                "updated_at": (
                    project.updated_at.isoformat() if project.updated_at else None
                ),
                "columns": columns,
            }

        except GithubException as e:
            logger.error(f"GitHub API error getting project board #{project_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting project board #{project_id}: {e}")
            return None

    async def add_issue_to_project(
        self,
        repo_name: str,
        project_id: int,
        issue_number: int,
        column_name: str = "Backlog",
    ) -> bool:
        """Add an issue to a project board column."""
        try:
            if not self.client.client:
                return False

            repo = self.client.client.get_repo(repo_name)
            project = repo.get_project(project_id)
            issue = repo.get_issue(issue_number)

            # Find the target column
            target_column = None
            for column in project.get_columns():
                if column.name.lower() == column_name.lower():
                    target_column = column
                    break

            if not target_column:
                logger.error(
                    f"Column '{column_name}' not found in project #{project_id}"
                )
                return False

            # Create card for the issue
            target_column.create_card(content_id=issue.id, content_type="Issue")

            logger.info(
                f"Added issue #{issue_number} to project board column '{column_name}'"
            )
            return True

        except GithubException as e:
            logger.error(
                f"GitHub API error adding issue #{issue_number} to project: {e}"
            )
            return False
        except Exception as e:
            logger.error(f"Error adding issue #{issue_number} to project: {e}")
            return False

    async def move_card_to_column(
        self, repo_name: str, project_id: int, card_id: int, column_name: str
    ) -> bool:
        """Move a project card to a different column."""
        try:
            if not self.client.client:
                return False

            repo = self.client.client.get_repo(repo_name)
            project = repo.get_project(project_id)

            # Find the target column
            target_column = None
            for column in project.get_columns():
                if column.name.lower() == column_name.lower():
                    target_column = column
                    break

            if not target_column:
                logger.error(
                    f"Column '{column_name}' not found in project #{project_id}"
                )
                return False

            # Find the card (need to search through all columns)
            card = None
            for column in project.get_columns():
                for c in column.get_cards():
                    if c.id == card_id:
                        card = c
                        break
                if card:
                    break

            if not card:
                logger.error(f"Card #{card_id} not found in project #{project_id}")
                return False

            # Move the card
            card.move("bottom", target_column)

            logger.info(f"Moved card #{card_id} to column '{column_name}'")
            return True

        except GithubException as e:
            logger.error(f"GitHub API error moving card #{card_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error moving card #{card_id}: {e}")
            return False

    async def create_sprint_board(
        self,
        repo_name: str,
        sprint_name: str,
        sprint_goal: str,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any] | None:
        """Create a sprint project board with standard Scrum columns."""

        description = f"""
**Sprint Goal:** {sprint_goal}

**Duration:** {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}

**Sprint Planning Notes:**
- Sprint created by Gaggle Sprint Assistant
- Follow standard Scrum practices for card movement
- Move cards from left to right as work progresses

**Column Definitions:**
- **Product Backlog:** All prioritized user stories
- **Sprint Backlog:** Stories committed for this sprint
- **In Progress:** Stories currently being worked on
- **Code Review:** Stories pending code review
- **Testing:** Stories in testing phase
- **Done:** Completed stories meeting Definition of Done
        """.strip()

        sprint_columns = [
            "Product Backlog",
            "Sprint Backlog",
            "In Progress",
            "Code Review",
            "Testing",
            "Done",
        ]

        return await self.create_project_board(
            repo_name=repo_name,
            name=sprint_name,
            description=description,
            columns=sprint_columns,
        )

    async def get_sprint_progress(
        self, repo_name: str, project_id: int
    ) -> dict[str, Any]:
        """Get sprint progress metrics from project board."""
        try:
            project = await self.get_project_board(repo_name, project_id)
            if not project:
                return {}

            # Count cards in each column
            column_counts = {}
            total_cards = 0
            done_cards = 0

            for column in project["columns"]:
                count = len(column["cards"])
                column_counts[column["name"]] = count
                total_cards += count

                # Count done items
                if column["name"].lower() in ["done", "completed", "finished"]:
                    done_cards += count

            # Calculate progress percentage
            progress_percentage = (
                (done_cards / total_cards * 100) if total_cards > 0 else 0
            )

            # Identify bottlenecks (columns with many cards)
            avg_cards_per_column = (
                total_cards / len(project["columns"]) if project["columns"] else 0
            )
            bottlenecks = [
                col_name
                for col_name, count in column_counts.items()
                if count > avg_cards_per_column * 1.5
                and col_name.lower() not in ["done", "product backlog"]
            ]

            return {
                "project_id": project_id,
                "project_name": project["name"],
                "total_items": total_cards,
                "completed_items": done_cards,
                "progress_percentage": round(progress_percentage, 1),
                "column_distribution": column_counts,
                "bottlenecks": bottlenecks,
                "health_status": (
                    "healthy" if len(bottlenecks) == 0 else "attention_needed"
                ),
            }

        except Exception as e:
            logger.error(f"Error getting sprint progress: {e}")
            return {}

    async def close_sprint_board(self, repo_name: str, project_id: int) -> bool:
        """Close a sprint project board."""
        try:
            if not self.client.client:
                return False

            repo = self.client.client.get_repo(repo_name)
            project = repo.get_project(project_id)

            # Close the project
            project.edit(name=f"[CLOSED] {project.name}", state="closed")

            logger.info(f"Closed sprint project board #{project_id}")
            return True

        except GithubException as e:
            logger.error(f"GitHub API error closing project board #{project_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error closing project board #{project_id}: {e}")
            return False
