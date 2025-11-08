"""Agent context management for state-aware coordination."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from ...config.models import AgentRole


class ContextLevel(Enum):
    """Levels of context information."""

    IMMEDIATE = "immediate"  # Current task/message context
    WORKING = "working"  # Current sprint context
    EPISODIC = "episodic"  # Sprint history and patterns
    SEMANTIC = "semantic"  # General knowledge and templates
    PROCEDURAL = "procedural"  # Workflow and process knowledge


@dataclass
class ContextItem:
    """Individual piece of context information."""

    id: str
    level: ContextLevel
    content: dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    relevance_score: float = 1.0
    tags: set[str] = field(default_factory=set)

    def access(self) -> None:
        """Update access tracking."""
        self.accessed_at = datetime.now()
        self.access_count += 1

    def update_relevance(self, score: float) -> None:
        """Update relevance score."""
        self.relevance_score = max(0.0, min(1.0, score))

    def is_expired(self, ttl: timedelta | None = None) -> bool:
        """Check if context item has expired."""
        if ttl is None:
            # Default TTL based on context level
            ttl_map = {
                ContextLevel.IMMEDIATE: timedelta(hours=1),
                ContextLevel.WORKING: timedelta(days=30),
                ContextLevel.EPISODIC: timedelta(days=365),
                ContextLevel.SEMANTIC: timedelta(days=999999),  # Effectively permanent
                ContextLevel.PROCEDURAL: timedelta(days=999999),
            }
            ttl = ttl_map[self.level]

        return datetime.now() - self.created_at > ttl


@dataclass
class AgentContext:
    """Context information for an agent."""

    agent_role: AgentRole
    agent_id: str
    current_state: str = "idle"

    # Context storage by level
    immediate_context: dict[str, ContextItem] = field(default_factory=dict)
    working_context: dict[str, ContextItem] = field(default_factory=dict)
    episodic_context: dict[str, ContextItem] = field(default_factory=dict)
    semantic_context: dict[str, ContextItem] = field(default_factory=dict)
    procedural_context: dict[str, ContextItem] = field(default_factory=dict)

    # Current activity tracking
    current_sprint_id: str | None = None
    current_task_id: str | None = None
    current_objectives: list[str] = field(default_factory=list)

    # Performance tracking
    completed_tasks: list[str] = field(default_factory=list)
    failed_tasks: list[str] = field(default_factory=list)
    performance_metrics: dict[str, float] = field(default_factory=dict)

    def get_context_storage(self, level: ContextLevel) -> dict[str, ContextItem]:
        """Get the appropriate context storage for a level."""
        storage_map = {
            ContextLevel.IMMEDIATE: self.immediate_context,
            ContextLevel.WORKING: self.working_context,
            ContextLevel.EPISODIC: self.episodic_context,
            ContextLevel.SEMANTIC: self.semantic_context,
            ContextLevel.PROCEDURAL: self.procedural_context,
        }
        return storage_map[level]

    def add_context(self, item: ContextItem) -> None:
        """Add context item to appropriate storage."""
        storage = self.get_context_storage(item.level)
        storage[item.id] = item

    def get_context(
        self, item_id: str, level: ContextLevel | None = None
    ) -> ContextItem | None:
        """Get context item by ID."""
        if level:
            storage = self.get_context_storage(level)
            item = storage.get(item_id)
            if item:
                item.access()
            return item

        # Search all levels if level not specified
        for context_level in ContextLevel:
            storage = self.get_context_storage(context_level)
            item = storage.get(item_id)
            if item:
                item.access()
                return item

        return None

    def search_context(
        self, query: str, level: ContextLevel | None = None, limit: int = 10
    ) -> list[ContextItem]:
        """Search context items by content."""
        results = []

        levels_to_search = [level] if level else list(ContextLevel)

        for search_level in levels_to_search:
            storage = self.get_context_storage(search_level)
            for item in storage.values():
                if self._matches_query(item, query):
                    item.access()
                    results.append(item)

        # Sort by relevance and recency
        results.sort(key=lambda x: (x.relevance_score, x.accessed_at), reverse=True)
        return results[:limit]

    def _matches_query(self, item: ContextItem, query: str) -> bool:
        """Check if context item matches query."""
        query_lower = query.lower()

        # Search in tags
        for tag in item.tags:
            if query_lower in tag.lower():
                return True

        # Search in content (simplified)
        content_str = json.dumps(item.content).lower()
        return query_lower in content_str

    def cleanup_expired(self) -> int:
        """Remove expired context items."""
        removed_count = 0

        for level in ContextLevel:
            storage = self.get_context_storage(level)
            expired_items = [
                item_id for item_id, item in storage.items() if item.is_expired()
            ]

            for item_id in expired_items:
                del storage[item_id]
                removed_count += 1

        return removed_count

    def get_context_summary(self) -> dict[str, Any]:
        """Get summary of current context."""
        summary = {
            "agent_role": self.agent_role.value,
            "agent_id": self.agent_id,
            "current_state": self.current_state,
            "current_sprint_id": self.current_sprint_id,
            "current_task_id": self.current_task_id,
            "current_objectives": self.current_objectives,
            "context_counts": {},
            "performance_metrics": self.performance_metrics,
        }

        for level in ContextLevel:
            storage = self.get_context_storage(level)
            summary["context_counts"][level.value] = len(storage)

        return summary


class ContextManager:
    """Manages context for all agents."""

    def __init__(self):
        self.agent_contexts: dict[str, AgentContext] = {}
        self.shared_context: dict[ContextLevel, dict[str, ContextItem]] = {
            level: {} for level in ContextLevel
        }
        self.logger = logging.getLogger("context.manager")

    def get_or_create_context(
        self, agent_role: AgentRole, agent_id: str
    ) -> AgentContext:
        """Get or create context for an agent."""
        if agent_id not in self.agent_contexts:
            self.agent_contexts[agent_id] = AgentContext(
                agent_role=agent_role, agent_id=agent_id
            )
            self.logger.info(
                f"Created context for agent {agent_id} ({agent_role.value})"
            )

        return self.agent_contexts[agent_id]

    def add_shared_context(self, item: ContextItem) -> None:
        """Add context item to shared context."""
        self.shared_context[item.level][item.id] = item
        self.logger.debug(
            f"Added shared context item {item.id} at level {item.level.value}"
        )

    def get_shared_context(
        self, level: ContextLevel, item_id: str
    ) -> ContextItem | None:
        """Get shared context item."""
        item = self.shared_context[level].get(item_id)
        if item:
            item.access()
        return item

    def search_shared_context(
        self, query: str, level: ContextLevel | None = None, limit: int = 10
    ) -> list[ContextItem]:
        """Search shared context."""
        results = []

        levels_to_search = [level] if level else list(ContextLevel)

        for search_level in levels_to_search:
            for item in self.shared_context[search_level].values():
                if self._matches_query(item, query):
                    item.access()
                    results.append(item)

        results.sort(key=lambda x: (x.relevance_score, x.accessed_at), reverse=True)
        return results[:limit]

    def _matches_query(self, item: ContextItem, query: str) -> bool:
        """Check if context item matches query."""
        query_lower = query.lower()

        for tag in item.tags:
            if query_lower in tag.lower():
                return True

        content_str = json.dumps(item.content).lower()
        return query_lower in content_str

    def update_agent_state(self, agent_id: str, new_state: str) -> bool:
        """Update agent's current state."""
        if agent_id in self.agent_contexts:
            old_state = self.agent_contexts[agent_id].current_state
            self.agent_contexts[agent_id].current_state = new_state
            self.logger.info(
                f"Agent {agent_id} state changed: {old_state} -> {new_state}"
            )
            return True
        return False

    def cleanup_all_expired(self) -> dict[str, int]:
        """Cleanup expired context for all agents."""
        cleanup_stats = {}

        # Cleanup agent contexts
        for agent_id, context in self.agent_contexts.items():
            removed = context.cleanup_expired()
            if removed > 0:
                cleanup_stats[agent_id] = removed

        # Cleanup shared context
        total_shared_removed = 0
        for level in ContextLevel:
            storage = self.shared_context[level]
            expired_items = [
                item_id for item_id, item in storage.items() if item.is_expired()
            ]

            for item_id in expired_items:
                del storage[item_id]
                total_shared_removed += 1

        if total_shared_removed > 0:
            cleanup_stats["shared_context"] = total_shared_removed

        return cleanup_stats

    def get_system_context_summary(self) -> dict[str, Any]:
        """Get summary of all context in the system."""
        summary = {
            "total_agents": len(self.agent_contexts),
            "agents": {},
            "shared_context_counts": {},
        }

        # Agent context summaries
        for agent_id, context in self.agent_contexts.items():
            summary["agents"][agent_id] = context.get_context_summary()

        # Shared context counts
        for level in ContextLevel:
            summary["shared_context_counts"][level.value] = len(
                self.shared_context[level]
            )

        return summary
