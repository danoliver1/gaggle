"""Prompt caching system for 50-90% token cost reduction."""

import hashlib
import json
import logging
import pickle
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import uuid

from ...config.models import AgentRole, ModelTier


class CacheType(Enum):
    """Types of cached content."""
    TEMPLATE = "template"       # Instruction templates
    COMPONENT = "component"     # Generated code components
    PATTERN = "pattern"         # Common patterns and solutions
    CONTEXT = "context"         # Compressed context summaries
    RESPONSE = "response"       # Full LLM responses


@dataclass
class CacheKey:
    """Unique identifier for cached content."""
    cache_type: CacheType
    content_hash: str
    agent_role: Optional[AgentRole] = None
    model_tier: Optional[ModelTier] = None
    version: str = "1.0"
    
    def __str__(self) -> str:
        """String representation for storage keys."""
        parts = [
            self.cache_type.value,
            self.content_hash[:16],  # Truncate hash for readability
            self.agent_role.value if self.agent_role else "any",
            self.model_tier.value if self.model_tier else "any",
            self.version
        ]
        return ":".join(parts)
    
    @classmethod
    def from_content(
        cls,
        cache_type: CacheType,
        content: str,
        agent_role: Optional[AgentRole] = None,
        model_tier: Optional[ModelTier] = None,
        version: str = "1.0"
    ) -> "CacheKey":
        """Create cache key from content."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        return cls(cache_type, content_hash, agent_role, model_tier, version)


@dataclass
class CacheEntry:
    """Cache entry with metadata and content."""
    key: CacheKey
    content: Any
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    hit_count: int = 0
    
    # Metadata
    original_size: int = 0      # Size of original content in tokens
    compressed_size: int = 0    # Size of cached content in tokens
    compression_ratio: float = 1.0
    
    # Usage tracking
    token_savings: int = 0      # Total tokens saved by this cache entry
    cost_savings: float = 0.0   # Total cost saved (in dollars)
    
    # Quality metrics
    freshness_score: float = 1.0  # How fresh/relevant the cache is
    confidence_score: float = 1.0 # Confidence in cached content quality
    
    def access(self) -> None:
        """Update access tracking."""
        self.last_accessed = datetime.now()
        self.access_count += 1
    
    def record_hit(self, tokens_saved: int, cost_saved: float) -> None:
        """Record a cache hit with savings."""
        self.hit_count += 1
        self.token_savings += tokens_saved
        self.cost_savings += cost_saved
        self.access()
    
    def is_expired(self, ttl: Optional[timedelta] = None) -> bool:
        """Check if cache entry has expired."""
        if ttl is None:
            # Default TTL based on cache type
            ttl_map = {
                CacheType.TEMPLATE: timedelta(days=30),     # Templates stable
                CacheType.COMPONENT: timedelta(days=7),     # Components may evolve
                CacheType.PATTERN: timedelta(days=14),      # Patterns moderately stable
                CacheType.CONTEXT: timedelta(hours=24),     # Context changes daily
                CacheType.RESPONSE: timedelta(hours=1)      # Responses very specific
            }
            ttl = ttl_map.get(self.key.cache_type, timedelta(days=1))
        
        return datetime.now() - self.created_at > ttl
    
    def calculate_freshness(self) -> float:
        """Calculate freshness score based on age and usage."""
        # Age-based decay
        age_hours = (datetime.now() - self.created_at).total_seconds() / 3600
        age_decay = 0.95 ** (age_hours / 24.0)  # Decay over days
        
        # Usage-based boost
        usage_boost = min(self.hit_count / 10.0, 0.3)  # Max 30% boost
        
        self.freshness_score = min(age_decay + usage_boost, 1.0)
        return self.freshness_score
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize cache entry to dictionary."""
        return {
            "key": {
                "cache_type": self.key.cache_type.value,
                "content_hash": self.key.content_hash,
                "agent_role": self.key.agent_role.value if self.key.agent_role else None,
                "model_tier": self.key.model_tier.value if self.key.model_tier else None,
                "version": self.key.version
            },
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "hit_count": self.hit_count,
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "compression_ratio": self.compression_ratio,
            "token_savings": self.token_savings,
            "cost_savings": self.cost_savings,
            "freshness_score": self.freshness_score,
            "confidence_score": self.confidence_score
        }


class CachingStrategy(ABC):
    """Abstract base class for caching strategies."""
    
    @abstractmethod
    def should_cache(self, content: str, context: Dict[str, Any]) -> bool:
        """Determine if content should be cached."""
        pass
    
    @abstractmethod
    def get_cache_key(self, content: str, context: Dict[str, Any]) -> CacheKey:
        """Generate cache key for content."""
        pass
    
    @abstractmethod
    def preprocess_content(self, content: str, context: Dict[str, Any]) -> str:
        """Preprocess content before caching."""
        pass
    
    @abstractmethod
    def postprocess_content(self, cached_content: str, context: Dict[str, Any]) -> str:
        """Postprocess cached content before use."""
        pass


class TemplateCacher(CachingStrategy):
    """Caching strategy for instruction templates."""
    
    def __init__(self):
        self.logger = logging.getLogger("caching.template")
    
    def should_cache(self, content: str, context: Dict[str, Any]) -> bool:
        """Cache instruction templates and system prompts."""
        # Check for template indicators
        template_indicators = [
            "You are a", "Your role is", "You should",
            "Always", "Never", "Remember to",
            "Follow these", "Guidelines:", "Instructions:"
        ]
        
        content_lower = content.lower()
        return any(indicator.lower() in content_lower for indicator in template_indicators)
    
    def get_cache_key(self, content: str, context: Dict[str, Any]) -> CacheKey:
        """Generate cache key for template."""
        agent_role = context.get("agent_role")
        model_tier = context.get("model_tier")
        
        return CacheKey.from_content(
            CacheType.TEMPLATE,
            content,
            agent_role,
            model_tier
        )
    
    def preprocess_content(self, content: str, context: Dict[str, Any]) -> str:
        """Normalize template content."""
        # Remove dynamic elements that shouldn't be cached
        import re
        
        # Remove timestamps
        content = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', '{TIMESTAMP}', content)
        
        # Remove session IDs
        content = re.sub(r'\b[a-f0-9-]{32,}\b', '{SESSION_ID}', content)
        
        # Normalize whitespace
        content = re.sub(r'\s+', ' ', content.strip())
        
        return content
    
    def postprocess_content(self, cached_content: str, context: Dict[str, Any]) -> str:
        """Replace placeholders with actual values."""
        current_time = datetime.now().isoformat()
        session_id = context.get("session_id", str(uuid.uuid4()))
        
        content = cached_content.replace('{TIMESTAMP}', current_time)
        content = content.replace('{SESSION_ID}', session_id)
        
        return content


class ComponentCacher(CachingStrategy):
    """Caching strategy for generated code components."""
    
    def __init__(self):
        self.logger = logging.getLogger("caching.component")
    
    def should_cache(self, content: str, context: Dict[str, Any]) -> bool:
        """Cache reusable code components."""
        code_indicators = [
            "class ", "def ", "function ", "const ",
            "interface ", "type ", "enum ",
            "component", "module", "export"
        ]
        
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in code_indicators)
    
    def get_cache_key(self, content: str, context: Dict[str, Any]) -> CacheKey:
        """Generate cache key for component."""
        # Extract component signature for more specific caching
        import re
        
        # Try to find function/class/component names
        patterns = [
            r'class\s+(\w+)',
            r'def\s+(\w+)',
            r'function\s+(\w+)',
            r'const\s+(\w+)\s*=',
            r'export\s+(?:const|function|class)\s+(\w+)'
        ]
        
        component_name = ""
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                component_name = match.group(1)
                break
        
        # Include component name in hash for better specificity
        cache_content = f"{component_name}:{content}"
        
        return CacheKey.from_content(
            CacheType.COMPONENT,
            cache_content,
            context.get("agent_role"),
            context.get("model_tier")
        )
    
    def preprocess_content(self, content: str, context: Dict[str, Any]) -> str:
        """Normalize component content."""
        import re
        
        # Remove comments that might contain specific details
        content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        content = re.sub(r'#.*?$', '', content, flags=re.MULTILINE)
        
        # Normalize indentation
        lines = content.split('\n')
        normalized_lines = []
        for line in lines:
            if line.strip():
                # Count leading spaces and normalize to 2-space indentation
                leading_spaces = len(line) - len(line.lstrip())
                indent_level = leading_spaces // 4  # Assume 4-space indents
                normalized_line = '  ' * indent_level + line.lstrip()
                normalized_lines.append(normalized_line)
            else:
                normalized_lines.append('')
        
        return '\n'.join(normalized_lines)
    
    def postprocess_content(self, cached_content: str, context: Dict[str, Any]) -> str:
        """Adapt cached component to current context."""
        # Could add context-specific adaptations here
        return cached_content


class PatternCacher(CachingStrategy):
    """Caching strategy for common patterns and solutions."""
    
    def __init__(self):
        self.logger = logging.getLogger("caching.pattern")
        
        # Common patterns to cache
        self.pattern_indicators = [
            "error handling", "validation", "authentication",
            "database connection", "API endpoint", "middleware",
            "logging", "configuration", "testing", "deployment"
        ]
    
    def should_cache(self, content: str, context: Dict[str, Any]) -> bool:
        """Cache common patterns and solutions."""
        content_lower = content.lower()
        return any(pattern in content_lower for pattern in self.pattern_indicators)
    
    def get_cache_key(self, content: str, context: Dict[str, Any]) -> CacheKey:
        """Generate cache key for pattern."""
        # Identify the pattern type
        content_lower = content.lower()
        pattern_type = "generic"
        
        for pattern in self.pattern_indicators:
            if pattern in content_lower:
                pattern_type = pattern.replace(" ", "_")
                break
        
        # Include pattern type in cache key
        cache_content = f"{pattern_type}:{content}"
        
        return CacheKey.from_content(
            CacheType.PATTERN,
            cache_content,
            context.get("agent_role")
        )
    
    def preprocess_content(self, content: str, context: Dict[str, Any]) -> str:
        """Generalize pattern content."""
        import re
        
        # Replace specific names with placeholders
        content = re.sub(r'\b[A-Z][a-zA-Z]*(?:Service|Manager|Handler|Controller)\b', '{CLASS_NAME}', content)
        content = re.sub(r'\b[a-z][a-zA-Z]*(?:_id|Id|ID)\b', '{IDENTIFIER}', content)
        
        # Replace specific URLs and endpoints
        content = re.sub(r'https?://[^\s]+', '{URL}', content)
        content = re.sub(r'/api/v\d+/[^\s]*', '{API_ENDPOINT}', content)
        
        return content
    
    def postprocess_content(self, cached_content: str, context: Dict[str, Any]) -> str:
        """Customize pattern for current context."""
        # Replace placeholders with context-specific values
        class_name = context.get("class_name", "Handler")
        identifier = context.get("identifier", "item_id")
        url = context.get("url", "https://api.example.com")
        endpoint = context.get("endpoint", "/api/v1/items")
        
        content = cached_content.replace('{CLASS_NAME}', class_name)
        content = content.replace('{IDENTIFIER}', identifier)
        content = content.replace('{URL}', url)
        content = content.replace('{API_ENDPOINT}', endpoint)
        
        return content


class PromptCache:
    """Main prompt caching system."""
    
    def __init__(self, max_size: int = 1000, enable_persistence: bool = False):
        self.max_size = max_size
        self.enable_persistence = enable_persistence
        
        # Cache storage
        self.cache: Dict[str, CacheEntry] = {}
        
        # Caching strategies
        self.strategies = [
            TemplateCacher(),
            ComponentCacher(),
            PatternCacher()
        ]
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_token_savings": 0,
            "total_cost_savings": 0.0,
            "evictions": 0
        }
        
        self.logger = logging.getLogger("caching.prompt")
        
        # Load persistent cache if enabled
        if self.enable_persistence:
            self._load_persistent_cache()
    
    def get(self, content: str, context: Dict[str, Any]) -> Optional[CacheEntry]:
        """Get cached content if available."""
        self.stats["total_requests"] += 1
        
        # Try each caching strategy
        for strategy in self.strategies:
            if strategy.should_cache(content, context):
                processed_content = strategy.preprocess_content(content, context)
                cache_key = strategy.get_cache_key(processed_content, context)
                
                key_str = str(cache_key)
                if key_str in self.cache:
                    entry = self.cache[key_str]
                    
                    # Check if cache is still fresh
                    if not entry.is_expired():
                        entry.access()
                        self.stats["cache_hits"] += 1
                        
                        # Postprocess content
                        final_content = strategy.postprocess_content(entry.content, context)
                        entry.content = final_content
                        
                        self.logger.debug(f"Cache hit for key: {key_str}")
                        return entry
                    else:
                        # Remove expired entry
                        del self.cache[key_str]
                        self.logger.debug(f"Removed expired cache entry: {key_str}")
        
        self.stats["cache_misses"] += 1
        return None
    
    def put(
        self,
        content: str,
        cached_content: str,
        context: Dict[str, Any],
        original_tokens: int = 0,
        cached_tokens: int = 0
    ) -> bool:
        """Cache content with specified strategy."""
        
        # Find appropriate strategy
        strategy = None
        for s in self.strategies:
            if s.should_cache(content, context):
                strategy = s
                break
        
        if not strategy:
            return False
        
        # Create cache entry
        processed_content = strategy.preprocess_content(content, context)
        cache_key = strategy.get_cache_key(processed_content, context)
        
        entry = CacheEntry(
            key=cache_key,
            content=cached_content,
            original_size=original_tokens,
            compressed_size=cached_tokens
        )
        
        if original_tokens > 0:
            entry.compression_ratio = cached_tokens / original_tokens
        
        # Enforce cache size limit
        self._enforce_cache_size()
        
        # Store entry
        key_str = str(cache_key)
        self.cache[key_str] = entry
        
        self.logger.debug(f"Cached content with key: {key_str}")
        
        # Save to persistent storage if enabled
        if self.enable_persistence:
            self._save_persistent_cache()
        
        return True
    
    def record_savings(self, cache_key: str, tokens_saved: int, cost_saved: float) -> None:
        """Record token and cost savings from cache usage."""
        if cache_key in self.cache:
            self.cache[cache_key].record_hit(tokens_saved, cost_saved)
            
            # Update global stats
            self.stats["total_token_savings"] += tokens_saved
            self.stats["total_cost_savings"] += cost_saved
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        cache_size = len(self.cache)
        hit_rate = self.stats["cache_hits"] / self.stats["total_requests"] if self.stats["total_requests"] > 0 else 0.0
        
        # Calculate savings by cache type
        savings_by_type = {}
        entries_by_type = {}
        
        for entry in self.cache.values():
            cache_type = entry.key.cache_type.value
            if cache_type not in savings_by_type:
                savings_by_type[cache_type] = {"tokens": 0, "cost": 0.0}
                entries_by_type[cache_type] = 0
            
            savings_by_type[cache_type]["tokens"] += entry.token_savings
            savings_by_type[cache_type]["cost"] += entry.cost_savings
            entries_by_type[cache_type] += 1
        
        return {
            **self.stats,
            "hit_rate": hit_rate,
            "cache_size": cache_size,
            "cache_utilization": cache_size / self.max_size,
            "savings_by_type": savings_by_type,
            "entries_by_type": entries_by_type,
            "average_compression_ratio": self._calculate_average_compression()
        }
    
    def cleanup_expired(self) -> int:
        """Remove expired cache entries."""
        expired_keys = []
        
        for key_str, entry in self.cache.items():
            if entry.is_expired():
                expired_keys.append(key_str)
        
        for key_str in expired_keys:
            del self.cache[key_str]
        
        if expired_keys:
            self.logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def clear_cache(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.stats = {key: 0 if isinstance(value, (int, float)) else value for key, value in self.stats.items()}
        self.logger.info("Cache cleared")
    
    def _enforce_cache_size(self) -> None:
        """Enforce cache size limits by evicting least useful entries."""
        if len(self.cache) >= self.max_size:
            # Calculate eviction scores
            scored_entries = []
            for key_str, entry in self.cache.items():
                # Score based on freshness, hit count, and savings
                freshness = entry.calculate_freshness()
                hit_score = min(entry.hit_count / 10.0, 1.0)
                savings_score = min(entry.token_savings / 1000.0, 1.0)
                
                eviction_score = freshness * 0.4 + hit_score * 0.4 + savings_score * 0.2
                scored_entries.append((key_str, entry, eviction_score))
            
            # Sort by eviction score (ascending - worst first)
            scored_entries.sort(key=lambda x: x[2])
            
            # Evict worst 20%
            num_to_evict = max(1, len(self.cache) // 5)
            for key_str, _, _ in scored_entries[:num_to_evict]:
                del self.cache[key_str]
                self.stats["evictions"] += 1
                
            self.logger.debug(f"Evicted {num_to_evict} cache entries due to size limit")
    
    def _calculate_average_compression(self) -> float:
        """Calculate average compression ratio across all cached entries."""
        if not self.cache:
            return 1.0
        
        total_compression = sum(entry.compression_ratio for entry in self.cache.values())
        return total_compression / len(self.cache)
    
    def _save_persistent_cache(self) -> None:
        """Save cache to persistent storage."""
        try:
            cache_data = {key: entry.to_dict() for key, entry in self.cache.items()}
            with open("prompt_cache.pkl", "wb") as f:
                pickle.dump(cache_data, f)
        except Exception as e:
            self.logger.error(f"Failed to save persistent cache: {e}")
    
    def _load_persistent_cache(self) -> None:
        """Load cache from persistent storage."""
        try:
            with open("prompt_cache.pkl", "rb") as f:
                cache_data = pickle.load(f)
                
            for key_str, entry_data in cache_data.items():
                # Reconstruct cache entry
                key_data = entry_data["key"]
                cache_key = CacheKey(
                    cache_type=CacheType(key_data["cache_type"]),
                    content_hash=key_data["content_hash"],
                    agent_role=AgentRole(key_data["agent_role"]) if key_data["agent_role"] else None,
                    model_tier=ModelTier(key_data["model_tier"]) if key_data["model_tier"] else None,
                    version=key_data["version"]
                )
                
                entry = CacheEntry(
                    key=cache_key,
                    content=entry_data["content"],
                    created_at=datetime.fromisoformat(entry_data["created_at"]),
                    last_accessed=datetime.fromisoformat(entry_data["last_accessed"]),
                    access_count=entry_data["access_count"],
                    hit_count=entry_data["hit_count"],
                    original_size=entry_data["original_size"],
                    compressed_size=entry_data["compressed_size"],
                    compression_ratio=entry_data["compression_ratio"],
                    token_savings=entry_data["token_savings"],
                    cost_savings=entry_data["cost_savings"],
                    freshness_score=entry_data["freshness_score"],
                    confidence_score=entry_data["confidence_score"]
                )
                
                # Only load non-expired entries
                if not entry.is_expired():
                    self.cache[key_str] = entry
                
            self.logger.info(f"Loaded {len(self.cache)} cache entries from persistent storage")
            
        except FileNotFoundError:
            self.logger.info("No persistent cache found, starting fresh")
        except Exception as e:
            self.logger.error(f"Failed to load persistent cache: {e}")