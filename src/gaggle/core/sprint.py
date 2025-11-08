"""Sprint business logic."""

from typing import Any

from ..models.sprint import SprintModel
from ..models.story import UserStory
from ..models.task import Task


class Sprint:
    """Sprint business logic and workflow management."""

    def __init__(self, sprint_model: SprintModel):
        self.model = sprint_model

    def add_story(self, story: UserStory) -> None:
        """Add a story to the sprint."""
        self.model.add_story(story)

    def add_task(self, task: Task) -> None:
        """Add a task to the sprint."""
        self.model.add_task(task)

    def get_status(self) -> dict[str, Any]:
        """Get sprint status."""
        return {
            "id": self.model.id,
            "goal": self.model.goal,
            "status": self.model.status,
            "metrics": self.model.metrics,
            "completion_percentage": self.model.metrics.completion_percentage,
        }
