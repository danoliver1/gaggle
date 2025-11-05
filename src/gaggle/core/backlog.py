"""Product backlog business logic."""

from typing import List, Dict, Any
from ..models.story import UserStory, StoryPriority


class ProductBacklog:
    """Product backlog management."""
    
    def __init__(self):
        self.stories: List[UserStory] = []
    
    def add_story(self, story: UserStory) -> None:
        """Add a story to the backlog."""
        if story not in self.stories:
            self.stories.append(story)
    
    def get_stories_by_priority(self, priority: StoryPriority) -> List[UserStory]:
        """Get stories by priority."""
        return [story for story in self.stories if story.priority == priority]
    
    def get_prioritized_stories(self) -> List[UserStory]:
        """Get stories sorted by priority."""
        priority_order = {
            StoryPriority.CRITICAL: 1,
            StoryPriority.HIGH: 2,
            StoryPriority.MEDIUM: 3,
            StoryPriority.LOW: 4
        }
        return sorted(self.stories, key=lambda s: priority_order.get(s.priority, 5))