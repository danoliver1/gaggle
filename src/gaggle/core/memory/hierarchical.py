"""Hierarchical memory system for intelligent context management."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import uuid

from ..state.context import ContextLevel


class MemoryLevel(Enum):
    """Memory levels with different characteristics and retention."""
    WORKING = "working"          # Current sprint context (high-frequency, short-term)
    EPISODIC = "episodic"       # Sprint history and experiences (medium-term)
    SEMANTIC = "semantic"       # Domain knowledge and patterns (long-term)
    PROCEDURAL = "procedural"   # Workflow processes and templates (permanent)


class RetrievalStrategy(Enum):
    """Strategies for retrieving memory items."""
    RECENCY = "recency"         # Most recently accessed
    FREQUENCY = "frequency"     # Most frequently accessed
    RELEVANCE = "relevance"     # Best matching query
    HYBRID = "hybrid"           # Combination of factors


@dataclass
class MemoryItem:
    """Individual memory item in the hierarchical system."""
    id: str
    level: MemoryLevel
    content: Dict[str, Any]
    tags: Set[str] = field(default_factory=set)
    
    # Temporal metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    
    # Relevance and importance
    importance_score: float = 1.0  # 0.0 to 1.0
    relevance_decay: float = 0.95  # How quickly relevance decays
    
    # Relationships
    parent_id: Optional[str] = None
    child_ids: Set[str] = field(default_factory=set)
    related_ids: Set[str] = field(default_factory=set)
    
    # Context metadata
    agent_id: Optional[str] = None
    sprint_id: Optional[str] = None
    session_id: Optional[str] = None
    
    def access(self) -> None:
        """Update access tracking."""
        self.last_accessed = datetime.now()
        self.access_count += 1
    
    def calculate_relevance_score(self, query_terms: Set[str]) -> float:
        """Calculate relevance score for a query."""
        if not query_terms:
            return 0.0
        
        # Tag-based relevance
        tag_matches = len(query_terms.intersection(self.tags))
        tag_score = tag_matches / len(query_terms) if query_terms else 0.0
        
        # Content-based relevance (simplified)
        content_str = json.dumps(self.content).lower()
        content_matches = sum(1 for term in query_terms if term.lower() in content_str)
        content_score = content_matches / len(query_terms) if query_terms else 0.0
        
        # Temporal decay
        hours_since_access = (datetime.now() - self.last_accessed).total_seconds() / 3600
        temporal_decay = self.relevance_decay ** hours_since_access
        
        # Frequency boost
        frequency_boost = min(self.access_count / 10.0, 1.0)
        
        # Combine scores
        base_relevance = (tag_score * 0.6 + content_score * 0.4)
        final_score = base_relevance * temporal_decay * (1 + frequency_boost * 0.2)
        
        return min(final_score * self.importance_score, 1.0)
    
    def is_expired(self) -> bool:
        """Check if memory item should be expired based on level."""
        now = datetime.now()
        age = now - self.created_at
        
        # Different TTL for different levels
        ttl_map = {
            MemoryLevel.WORKING: timedelta(days=30),      # Sprint cycle
            MemoryLevel.EPISODIC: timedelta(days=365),    # 1 year
            MemoryLevel.SEMANTIC: timedelta(days=999999), # Permanent
            MemoryLevel.PROCEDURAL: timedelta(days=999999) # Permanent
        }
        
        return age > ttl_map[self.level]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize memory item to dictionary."""
        return {
            "id": self.id,
            "level": self.level.value,
            "content": self.content,
            "tags": list(self.tags),
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "importance_score": self.importance_score,
            "relevance_decay": self.relevance_decay,
            "parent_id": self.parent_id,
            "child_ids": list(self.child_ids),
            "related_ids": list(self.related_ids),
            "agent_id": self.agent_id,
            "sprint_id": self.sprint_id,
            "session_id": self.session_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryItem":
        """Deserialize memory item from dictionary."""
        return cls(
            id=data["id"],
            level=MemoryLevel(data["level"]),
            content=data["content"],
            tags=set(data.get("tags", [])),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"]),
            access_count=data.get("access_count", 0),
            importance_score=data.get("importance_score", 1.0),
            relevance_decay=data.get("relevance_decay", 0.95),
            parent_id=data.get("parent_id"),
            child_ids=set(data.get("child_ids", [])),
            related_ids=set(data.get("related_ids", [])),
            agent_id=data.get("agent_id"),
            sprint_id=data.get("sprint_id"),
            session_id=data.get("session_id")
        )


@dataclass
class RetrievalResult:
    """Result of memory retrieval operation."""
    items: List[MemoryItem]
    total_found: int
    retrieval_time: float
    strategy_used: RetrievalStrategy
    query_terms: Set[str]
    
    # Quality metrics
    average_relevance: float = 0.0
    coverage_score: float = 0.0  # How well results cover the query
    
    def get_top_items(self, limit: int) -> List[MemoryItem]:
        """Get top N items by relevance."""
        return self.items[:limit]
    
    def get_items_by_level(self, level: MemoryLevel) -> List[MemoryItem]:
        """Get items from specific memory level."""
        return [item for item in self.items if item.level == level]


class HierarchicalMemory:
    """Hierarchical memory system for a single agent."""
    
    def __init__(self, agent_id: str, max_items_per_level: Optional[Dict[MemoryLevel, int]] = None):
        self.agent_id = agent_id
        self.max_items_per_level = max_items_per_level or {
            MemoryLevel.WORKING: 500,      # Current sprint items
            MemoryLevel.EPISODIC: 2000,    # Historical experiences
            MemoryLevel.SEMANTIC: 1000,    # Domain knowledge
            MemoryLevel.PROCEDURAL: 200    # Process templates
        }
        
        # Memory storage by level
        self.memory_levels: Dict[MemoryLevel, Dict[str, MemoryItem]] = {
            level: {} for level in MemoryLevel
        }
        
        # Indexing for fast retrieval
        self.tag_index: Dict[str, Set[str]] = {}  # tag -> item_ids
        self.relationship_index: Dict[str, Set[str]] = {}  # item_id -> related_item_ids
        
        self.logger = logging.getLogger(f"memory.hierarchical.{agent_id}")
    
    def store(self, item: MemoryItem) -> str:
        """Store a memory item at the appropriate level."""
        if item.agent_id is None:
            item.agent_id = self.agent_id
        
        # Check capacity and potentially evict items
        self._enforce_capacity_limits(item.level)
        
        # Store the item
        self.memory_levels[item.level][item.id] = item
        
        # Update indexes
        self._update_indexes(item)
        
        self.logger.debug(f"Stored memory item {item.id} at level {item.level.value}")
        return item.id
    
    def retrieve(
        self, 
        query_terms: Set[str], 
        levels: Optional[List[MemoryLevel]] = None,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        limit: int = 10
    ) -> RetrievalResult:
        """Retrieve memory items matching query terms."""
        start_time = datetime.now()
        
        search_levels = levels or list(MemoryLevel)
        candidates = []
        
        # Collect candidates from specified levels
        for level in search_levels:
            for item in self.memory_levels[level].values():
                relevance = item.calculate_relevance_score(query_terms)
                if relevance > 0.1:  # Threshold for inclusion
                    candidates.append((item, relevance))
        
        # Sort by strategy
        sorted_candidates = self._sort_by_strategy(candidates, strategy)
        
        # Limit results
        top_items = [item for item, _ in sorted_candidates[:limit]]
        
        # Update access tracking
        for item in top_items:
            item.access()
        
        retrieval_time = (datetime.now() - start_time).total_seconds()
        
        # Calculate quality metrics
        avg_relevance = sum(score for _, score in sorted_candidates[:limit]) / len(sorted_candidates[:limit]) if sorted_candidates else 0.0
        
        result = RetrievalResult(
            items=top_items,
            total_found=len(candidates),
            retrieval_time=retrieval_time,
            strategy_used=strategy,
            query_terms=query_terms,
            average_relevance=avg_relevance
        )
        
        self.logger.debug(f"Retrieved {len(top_items)} items for query in {retrieval_time:.3f}s")
        return result
    
    def get_item(self, item_id: str) -> Optional[MemoryItem]:
        """Get specific memory item by ID."""
        for level_storage in self.memory_levels.values():
            if item_id in level_storage:
                item = level_storage[item_id]
                item.access()
                return item
        return None
    
    def get_related_items(self, item_id: str, max_depth: int = 2) -> List[MemoryItem]:
        """Get items related to a specific item."""
        visited = set()
        related = []
        queue = [(item_id, 0)]
        
        while queue and len(related) < 20:  # Limit to prevent excessive retrieval
            current_id, depth = queue.pop(0)
            
            if current_id in visited or depth > max_depth:
                continue
            
            visited.add(current_id)
            item = self.get_item(current_id)
            
            if item and current_id != item_id:  # Don't include the original item
                related.append(item)
            
            # Add related items to queue
            if item:
                for related_id in item.related_ids:
                    if related_id not in visited:
                        queue.append((related_id, depth + 1))
        
        return related
    
    def promote_item(self, item_id: str, target_level: MemoryLevel) -> bool:
        """Promote/demote an item to a different memory level."""
        # Find the item
        source_level = None
        item = None
        
        for level, storage in self.memory_levels.items():
            if item_id in storage:
                source_level = level
                item = storage[item_id]
                break
        
        if not item or source_level == target_level:
            return False
        
        # Remove from source level
        del self.memory_levels[source_level][item_id]
        
        # Update level and store in target
        item.level = target_level
        self.memory_levels[target_level][item_id] = item
        
        self.logger.info(f"Promoted item {item_id} from {source_level.value} to {target_level.value}")
        return True
    
    def cleanup_expired(self) -> Dict[MemoryLevel, int]:
        """Remove expired items from all levels."""
        removed_counts = {}
        
        for level, storage in self.memory_levels.items():
            expired_ids = [
                item_id for item_id, item in storage.items()
                if item.is_expired()
            ]
            
            for item_id in expired_ids:
                del storage[item_id]
                self._remove_from_indexes(item_id)
            
            if expired_ids:
                removed_counts[level] = len(expired_ids)
                self.logger.info(f"Removed {len(expired_ids)} expired items from {level.value}")
        
        return removed_counts
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        stats = {
            "agent_id": self.agent_id,
            "levels": {},
            "total_items": 0,
            "total_size_estimate": 0
        }
        
        for level, storage in self.memory_levels.items():
            level_stats = {
                "count": len(storage),
                "capacity": self.max_items_per_level[level],
                "utilization": len(storage) / self.max_items_per_level[level],
                "avg_access_count": 0.0,
                "most_accessed": None
            }
            
            if storage:
                access_counts = [item.access_count for item in storage.values()]
                level_stats["avg_access_count"] = sum(access_counts) / len(access_counts)
                
                most_accessed = max(storage.values(), key=lambda x: x.access_count)
                level_stats["most_accessed"] = {
                    "id": most_accessed.id,
                    "access_count": most_accessed.access_count,
                    "tags": list(most_accessed.tags)
                }
            
            stats["levels"][level.value] = level_stats
            stats["total_items"] += len(storage)
            
            # Estimate size (very rough)
            for item in storage.values():
                stats["total_size_estimate"] += len(json.dumps(item.content))
        
        stats["index_sizes"] = {
            "tag_index": len(self.tag_index),
            "relationship_index": len(self.relationship_index)
        }
        
        return stats
    
    def _enforce_capacity_limits(self, level: MemoryLevel) -> None:
        """Enforce capacity limits by evicting least useful items."""
        storage = self.memory_levels[level]
        max_items = self.max_items_per_level[level]
        
        if len(storage) >= max_items:
            # Calculate eviction scores (lower is more likely to be evicted)
            scored_items = []
            for item in storage.values():
                # Score based on recency, frequency, and importance
                hours_since_access = (datetime.now() - item.last_accessed).total_seconds() / 3600
                recency_score = 1.0 / (1.0 + hours_since_access)
                frequency_score = min(item.access_count / 10.0, 1.0)
                
                eviction_score = (recency_score * 0.4 + frequency_score * 0.4 + item.importance_score * 0.2)
                scored_items.append((item, eviction_score))
            
            # Sort by eviction score (ascending - worst first)
            scored_items.sort(key=lambda x: x[1])
            
            # Evict worst 20% or enough to make room
            num_to_evict = max(1, len(storage) // 5)
            for item, _ in scored_items[:num_to_evict]:
                del storage[item.id]
                self._remove_from_indexes(item.id)
                self.logger.debug(f"Evicted item {item.id} from {level.value} due to capacity")
    
    def _update_indexes(self, item: MemoryItem) -> None:
        """Update search indexes for an item."""
        # Tag index
        for tag in item.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = set()
            self.tag_index[tag].add(item.id)
        
        # Relationship index
        if item.related_ids:
            self.relationship_index[item.id] = item.related_ids.copy()
    
    def _remove_from_indexes(self, item_id: str) -> None:
        """Remove item from all indexes."""
        # Remove from tag index
        for tag_items in self.tag_index.values():
            tag_items.discard(item_id)
        
        # Remove empty tag entries
        empty_tags = [tag for tag, items in self.tag_index.items() if not items]
        for tag in empty_tags:
            del self.tag_index[tag]
        
        # Remove from relationship index
        self.relationship_index.pop(item_id, None)
    
    def _sort_by_strategy(self, candidates: List[Tuple[MemoryItem, float]], strategy: RetrievalStrategy) -> List[Tuple[MemoryItem, float]]:
        """Sort candidates by retrieval strategy."""
        if strategy == RetrievalStrategy.RELEVANCE:
            return sorted(candidates, key=lambda x: x[1], reverse=True)
        
        elif strategy == RetrievalStrategy.RECENCY:
            return sorted(candidates, key=lambda x: x[0].last_accessed, reverse=True)
        
        elif strategy == RetrievalStrategy.FREQUENCY:
            return sorted(candidates, key=lambda x: x[0].access_count, reverse=True)
        
        elif strategy == RetrievalStrategy.HYBRID:
            # Combine relevance, recency, and frequency
            def hybrid_score(item_and_relevance):
                item, relevance = item_and_relevance
                hours_since_access = (datetime.now() - item.last_accessed).total_seconds() / 3600
                recency_score = 1.0 / (1.0 + hours_since_access / 24.0)  # Decay over days
                frequency_score = min(item.access_count / 10.0, 1.0)
                
                return relevance * 0.5 + recency_score * 0.3 + frequency_score * 0.2
            
            return sorted(candidates, key=hybrid_score, reverse=True)
        
        return candidates


class MemoryManager:
    """Global memory manager for all agents in the system."""
    
    def __init__(self):
        self.agent_memories: Dict[str, HierarchicalMemory] = {}
        self.shared_memory: HierarchicalMemory = HierarchicalMemory("shared")
        self.logger = logging.getLogger("memory.manager")
    
    def get_agent_memory(self, agent_id: str) -> HierarchicalMemory:
        """Get or create hierarchical memory for an agent."""
        if agent_id not in self.agent_memories:
            self.agent_memories[agent_id] = HierarchicalMemory(agent_id)
            self.logger.info(f"Created memory system for agent {agent_id}")
        
        return self.agent_memories[agent_id]
    
    def store_shared_memory(self, item: MemoryItem) -> str:
        """Store an item in shared memory accessible to all agents."""
        return self.shared_memory.store(item)
    
    def search_across_agents(
        self, 
        query_terms: Set[str], 
        agent_ids: Optional[List[str]] = None,
        include_shared: bool = True,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        limit_per_agent: int = 5
    ) -> Dict[str, RetrievalResult]:
        """Search across multiple agents' memories."""
        results = {}
        
        search_agents = agent_ids or list(self.agent_memories.keys())
        
        # Search individual agent memories
        for agent_id in search_agents:
            if agent_id in self.agent_memories:
                memory = self.agent_memories[agent_id]
                result = memory.retrieve(query_terms, strategy=strategy, limit=limit_per_agent)
                if result.items:
                    results[agent_id] = result
        
        # Search shared memory
        if include_shared:
            shared_result = self.shared_memory.retrieve(query_terms, strategy=strategy, limit=limit_per_agent)
            if shared_result.items:
                results["shared"] = shared_result
        
        return results
    
    def cleanup_all_memories(self) -> Dict[str, Dict[MemoryLevel, int]]:
        """Cleanup expired items from all agent memories."""
        cleanup_results = {}
        
        # Cleanup individual agent memories
        for agent_id, memory in self.agent_memories.items():
            removed = memory.cleanup_expired()
            if removed:
                cleanup_results[agent_id] = removed
        
        # Cleanup shared memory
        shared_removed = self.shared_memory.cleanup_expired()
        if shared_removed:
            cleanup_results["shared"] = shared_removed
        
        return cleanup_results
    
    def get_system_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics for the entire system."""
        stats = {
            "total_agents": len(self.agent_memories),
            "agents": {},
            "shared": self.shared_memory.get_memory_stats(),
            "system_totals": {
                "total_items": 0,
                "total_size_estimate": 0
            }
        }
        
        for agent_id, memory in self.agent_memories.items():
            agent_stats = memory.get_memory_stats()
            stats["agents"][agent_id] = agent_stats
            stats["system_totals"]["total_items"] += agent_stats["total_items"]
            stats["system_totals"]["total_size_estimate"] += agent_stats["total_size_estimate"]
        
        # Add shared memory to totals
        shared_stats = stats["shared"]
        stats["system_totals"]["total_items"] += shared_stats["total_items"]
        stats["system_totals"]["total_size_estimate"] += shared_stats["total_size_estimate"]
        
        return stats