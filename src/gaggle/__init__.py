"""
Gaggle: AI-Powered Agile Development Team

An AI system that simulates a complete Scrum team to build software iteratively
and efficiently using multi-agent collaboration with specialized roles.
"""

__version__ = "0.1.0"
__author__ = "Dan Oliver"
__email__ = "dan@example.com"

from .core.backlog import ProductBacklog
from .core.sprint import Sprint
from .core.team import Team
from .models.sprint import SprintModel
from .models.story import UserStory
from .models.task import Task

__all__ = [
    "Sprint",
    "Team",
    "ProductBacklog",
    "SprintModel",
    "UserStory",
    "Task",
]
