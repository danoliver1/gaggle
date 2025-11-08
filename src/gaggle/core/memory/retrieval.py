"""Intelligent context retrieval with BM25 and embedding-based search."""

import json
import logging
import math
import re
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass
from typing import Any

from .hierarchical import MemoryItem


@dataclass
class RelevanceScore:
    """Detailed relevance scoring breakdown."""

    total_score: float
    bm25_score: float = 0.0
    semantic_score: float = 0.0
    temporal_score: float = 0.0
    frequency_score: float = 0.0
    importance_score: float = 0.0

    def combine_scores(
        self,
        bm25_weight: float = 0.4,
        semantic_weight: float = 0.3,
        temporal_weight: float = 0.15,
        frequency_weight: float = 0.1,
        importance_weight: float = 0.05,
    ) -> float:
        """Combine individual scores with specified weights."""
        self.total_score = (
            self.bm25_score * bm25_weight
            + self.semantic_score * semantic_weight
            + self.temporal_score * temporal_weight
            + self.frequency_score * frequency_weight
            + self.importance_score * importance_weight
        )
        return self.total_score


class ContextRetriever(ABC):
    """Abstract base class for context retrieval strategies."""

    @abstractmethod
    def retrieve(
        self, query: str, items: list[MemoryItem], limit: int = 10
    ) -> list[tuple[MemoryItem, RelevanceScore]]:
        """Retrieve relevant items with detailed scoring."""
        pass

    @abstractmethod
    def index_items(self, items: list[MemoryItem]) -> None:
        """Build index for efficient retrieval."""
        pass


class BM25Retriever(ContextRetriever):
    """BM25-based retrieval for keyword matching."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1  # Controls term frequency saturation
        self.b = b  # Controls length normalization
        self.logger = logging.getLogger("retrieval.bm25")

        # Index structures
        self.document_frequencies: dict[str, int] = {}
        self.item_term_counts: dict[str, dict[str, int]] = {}
        self.item_lengths: dict[str, int] = {}
        self.average_length: float = 0.0
        self.total_documents: int = 0

    def index_items(self, items: list[MemoryItem]) -> None:
        """Build BM25 index from memory items."""
        self.logger.debug(f"Indexing {len(items)} items for BM25 retrieval")

        # Reset index
        self.document_frequencies.clear()
        self.item_term_counts.clear()
        self.item_lengths.clear()

        # Process each item
        total_length = 0
        for item in items:
            # Extract text content
            text_content = self._extract_text(item)
            terms = self._tokenize(text_content)

            # Count terms
            term_counts = Counter(terms)
            self.item_term_counts[item.id] = dict(term_counts)
            self.item_lengths[item.id] = len(terms)
            total_length += len(terms)

            # Update document frequencies
            for term in set(terms):
                self.document_frequencies[term] = (
                    self.document_frequencies.get(term, 0) + 1
                )

        self.total_documents = len(items)
        self.average_length = total_length / len(items) if items else 0.0

        self.logger.debug(f"Indexed {len(self.document_frequencies)} unique terms")

    def retrieve(
        self, query: str, items: list[MemoryItem], limit: int = 10
    ) -> list[tuple[MemoryItem, RelevanceScore]]:
        """Retrieve items using BM25 scoring."""
        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        # Calculate BM25 scores
        scored_items = []
        for item in items:
            if item.id not in self.item_term_counts:
                continue

            bm25_score = self._calculate_bm25_score(query_terms, item.id)

            if bm25_score > 0:
                relevance = RelevanceScore(total_score=0.0, bm25_score=bm25_score)
                scored_items.append((item, relevance))

        # Sort by BM25 score
        scored_items.sort(key=lambda x: x[1].bm25_score, reverse=True)

        return scored_items[:limit]

    def _extract_text(self, item: MemoryItem) -> str:
        """Extract searchable text from memory item."""
        text_parts = []

        # Add tags
        text_parts.extend(item.tags)

        # Add content (recursive extraction)
        def extract_from_content(obj, depth=0):
            if depth > 3:  # Prevent infinite recursion
                return

            if isinstance(obj, str):
                text_parts.append(obj)
            elif isinstance(obj, dict):
                for value in obj.values():
                    extract_from_content(value, depth + 1)
            elif isinstance(obj, (list, tuple)):
                for value in obj:
                    extract_from_content(value, depth + 1)

        extract_from_content(item.content)

        return " ".join(str(part) for part in text_parts)

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text for BM25 processing."""
        # Convert to lowercase and split on non-alphanumeric characters
        text = text.lower()
        tokens = re.findall(r"\b\w+\b", text)

        # Filter out very short tokens
        tokens = [token for token in tokens if len(token) >= 2]

        return tokens

    def _calculate_bm25_score(self, query_terms: list[str], item_id: str) -> float:
        """Calculate BM25 score for an item."""
        if item_id not in self.item_term_counts:
            return 0.0

        item_term_counts = self.item_term_counts[item_id]
        item_length = self.item_lengths[item_id]

        score = 0.0
        for term in query_terms:
            if term not in item_term_counts:
                continue

            # Term frequency in document
            tf = item_term_counts[term]

            # Document frequency (how many documents contain this term)
            df = self.document_frequencies.get(term, 0)
            if df == 0:
                continue

            # Inverse document frequency
            idf = math.log((self.total_documents - df + 0.5) / (df + 0.5))

            # BM25 formula
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (
                1 - self.b + self.b * (item_length / self.average_length)
            )

            score += idf * (numerator / denominator)

        return score


class EmbeddingRetriever(ContextRetriever):
    """Embedding-based semantic retrieval (mock implementation)."""

    def __init__(self, embedding_dim: int = 384):
        self.embedding_dim = embedding_dim
        self.logger = logging.getLogger("retrieval.embedding")

        # Mock embeddings (in production, use actual embedding model)
        self.item_embeddings: dict[str, list[float]] = {}

    def index_items(self, items: list[MemoryItem]) -> None:
        """Build embedding index (mock implementation)."""
        self.logger.debug(f"Creating embeddings for {len(items)} items")

        for item in items:
            # Mock embedding generation based on text content
            text_content = self._extract_text(item)
            embedding = self._create_mock_embedding(text_content)
            self.item_embeddings[item.id] = embedding

    def retrieve(
        self, query: str, items: list[MemoryItem], limit: int = 10
    ) -> list[tuple[MemoryItem, RelevanceScore]]:
        """Retrieve items using semantic similarity."""
        query_embedding = self._create_mock_embedding(query)

        scored_items = []
        for item in items:
            if item.id not in self.item_embeddings:
                continue

            similarity = self._cosine_similarity(
                query_embedding, self.item_embeddings[item.id]
            )

            if similarity > 0.1:  # Threshold for inclusion
                relevance = RelevanceScore(total_score=0.0, semantic_score=similarity)
                scored_items.append((item, relevance))

        # Sort by similarity
        scored_items.sort(key=lambda x: x[1].semantic_score, reverse=True)

        return scored_items[:limit]

    def _extract_text(self, item: MemoryItem) -> str:
        """Extract text content for embedding."""
        text_parts = list(item.tags)
        text_parts.append(json.dumps(item.content))
        return " ".join(text_parts)

    def _create_mock_embedding(self, text: str) -> list[float]:
        """Create mock embedding based on text hash (for development)."""
        # In production, this would use a real embedding model like SentenceTransformers
        import hashlib

        # Create deterministic "embedding" based on text hash
        text_hash = hashlib.md5(text.encode()).hexdigest()

        # Convert hex chars to float values
        embedding = []
        for i in range(0, min(len(text_hash), self.embedding_dim // 16)):
            hex_char = text_hash[i]
            value = int(hex_char, 16) / 15.0  # Normalize to [0, 1]
            embedding.extend([value] * 16)  # Repeat to fill dimension

        # Pad or truncate to exact dimension
        while len(embedding) < self.embedding_dim:
            embedding.append(0.0)
        embedding = embedding[: self.embedding_dim]

        # Normalize to unit vector
        norm = math.sqrt(sum(x * x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


class HybridRetriever(ContextRetriever):
    """Hybrid retrieval combining BM25 and embedding approaches."""

    def __init__(self, bm25_weight: float = 0.6, embedding_weight: float = 0.4):
        self.bm25_weight = bm25_weight
        self.embedding_weight = embedding_weight

        self.bm25_retriever = BM25Retriever()
        self.embedding_retriever = EmbeddingRetriever()
        self.logger = logging.getLogger("retrieval.hybrid")

    def index_items(self, items: list[MemoryItem]) -> None:
        """Index items for both BM25 and embedding retrieval."""
        self.logger.debug(f"Creating hybrid index for {len(items)} items")

        self.bm25_retriever.index_items(items)
        self.embedding_retriever.index_items(items)

    def retrieve(
        self, query: str, items: list[MemoryItem], limit: int = 10
    ) -> list[tuple[MemoryItem, RelevanceScore]]:
        """Retrieve using hybrid approach."""
        # Get results from both retrievers
        bm25_results = self.bm25_retriever.retrieve(
            query, items, limit * 2
        )  # Get more candidates
        embedding_results = self.embedding_retriever.retrieve(query, items, limit * 2)

        # Combine results
        combined_scores: dict[str, RelevanceScore] = {}
        item_map: dict[str, MemoryItem] = {}

        # Add BM25 scores
        for item, score in bm25_results:
            combined_scores[item.id] = RelevanceScore(
                total_score=0.0, bm25_score=score.bm25_score
            )
            item_map[item.id] = item

        # Add embedding scores
        for item, score in embedding_results:
            if item.id in combined_scores:
                combined_scores[item.id].semantic_score = score.semantic_score
            else:
                combined_scores[item.id] = RelevanceScore(
                    total_score=0.0, semantic_score=score.semantic_score
                )
                item_map[item.id] = item

        # Calculate combined scores
        scored_items = []
        for item_id, score in combined_scores.items():
            # Combine BM25 and embedding scores
            combined_score = (
                score.bm25_score * self.bm25_weight
                + score.semantic_score * self.embedding_weight
            )
            score.total_score = combined_score

            scored_items.append((item_map[item_id], score))

        # Sort by combined score
        scored_items.sort(key=lambda x: x[1].total_score, reverse=True)

        return scored_items[:limit]


class RelevanceScorer:
    """Advanced relevance scoring with multiple factors."""

    def __init__(self):
        self.logger = logging.getLogger("retrieval.scorer")

    def score_item(
        self, item: MemoryItem, query_terms: set[str], base_score: float = 0.0
    ) -> RelevanceScore:
        """Calculate comprehensive relevance score for an item."""
        score = RelevanceScore(total_score=base_score, bm25_score=base_score)

        # Temporal scoring (recency)
        score.temporal_score = self._calculate_temporal_score(item)

        # Frequency scoring (access patterns)
        score.frequency_score = self._calculate_frequency_score(item)

        # Importance scoring
        score.importance_score = item.importance_score

        # Combine all scores
        score.combine_scores()

        return score

    def _calculate_temporal_score(self, item: MemoryItem) -> float:
        """Calculate temporal relevance based on recency."""
        from datetime import datetime

        now = datetime.now()
        hours_since_access = (now - item.last_accessed).total_seconds() / 3600
        hours_since_creation = (now - item.created_at).total_seconds() / 3600

        # Recency decay (half-life of 24 hours for access, 168 hours for creation)
        access_decay = 0.5 ** (hours_since_access / 24.0)
        creation_decay = 0.5 ** (hours_since_creation / 168.0)

        # Weight access more than creation
        return access_decay * 0.7 + creation_decay * 0.3

    def _calculate_frequency_score(self, item: MemoryItem) -> float:
        """Calculate frequency-based relevance."""
        # Logarithmic scaling to prevent dominance of very frequent items
        frequency_score = math.log(1 + item.access_count) / math.log(
            11
        )  # Scale to [0, 1] range
        return min(frequency_score, 1.0)

    def rank_items(
        self,
        items_and_scores: list[tuple[MemoryItem, RelevanceScore]],
        query_terms: set[str],
    ) -> list[tuple[MemoryItem, RelevanceScore]]:
        """Re-rank items using comprehensive scoring."""
        enhanced_scores = []

        for item, score in items_and_scores:
            enhanced_score = self.score_item(item, query_terms, score.total_score)
            # Keep the original retrieval scores and add temporal/frequency
            enhanced_score.bm25_score = score.bm25_score
            enhanced_score.semantic_score = score.semantic_score
            enhanced_score.combine_scores()

            enhanced_scores.append((item, enhanced_score))

        # Sort by enhanced total score
        enhanced_scores.sort(key=lambda x: x[1].total_score, reverse=True)

        return enhanced_scores


class AdvancedRetriever:
    """Advanced retrieval system combining multiple strategies."""

    def __init__(self, primary_strategy: str = "hybrid"):
        self.primary_strategy = primary_strategy
        self.retrievers = {
            "bm25": BM25Retriever(),
            "embedding": EmbeddingRetriever(),
            "hybrid": HybridRetriever(),
        }
        self.scorer = RelevanceScorer()
        self.logger = logging.getLogger("retrieval.advanced")

        # Retrieval statistics
        self.retrieval_stats = {
            "total_queries": 0,
            "average_retrieval_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

        # Simple query cache
        self.query_cache: dict[str, list[tuple[MemoryItem, RelevanceScore]]] = {}
        self.cache_size_limit = 100

    def retrieve_with_fallback(
        self,
        query: str,
        items: list[MemoryItem],
        limit: int = 10,
        fallback_strategies: list[str] | None = None,
    ) -> list[tuple[MemoryItem, RelevanceScore]]:
        """Retrieve with fallback to alternative strategies."""
        from datetime import datetime

        start_time = datetime.now()
        query_terms = set(query.lower().split())

        # Check cache first
        cache_key = f"{query}:{limit}:{len(items)}"
        if cache_key in self.query_cache:
            self.retrieval_stats["cache_hits"] += 1
            cached_results = self.query_cache[cache_key]
            # Filter to only items that are still in the current item list
            current_item_ids = {item.id for item in items}
            filtered_results = [
                (item, score)
                for item, score in cached_results
                if item.id in current_item_ids
            ]
            return filtered_results[:limit]

        self.retrieval_stats["cache_misses"] += 1

        # Try primary strategy
        try:
            if self.primary_strategy in self.retrievers:
                retriever = self.retrievers[self.primary_strategy]
                retriever.index_items(items)
                results = retriever.retrieve(query, items, limit)

                if results:
                    # Enhance with comprehensive scoring
                    enhanced_results = self.scorer.rank_items(results, query_terms)

                    # Cache results
                    self._cache_results(cache_key, enhanced_results[:limit])

                    # Update statistics
                    retrieval_time = (datetime.now() - start_time).total_seconds()
                    self._update_stats(retrieval_time)

                    return enhanced_results[:limit]

        except Exception as e:
            self.logger.warning(f"Primary retrieval strategy failed: {e}")

        # Try fallback strategies
        fallback_strategies = fallback_strategies or ["bm25", "embedding"]

        for strategy in fallback_strategies:
            if strategy == self.primary_strategy or strategy not in self.retrievers:
                continue

            try:
                retriever = self.retrievers[strategy]
                retriever.index_items(items)
                results = retriever.retrieve(query, items, limit)

                if results:
                    enhanced_results = self.scorer.rank_items(results, query_terms)
                    self._cache_results(cache_key, enhanced_results[:limit])

                    retrieval_time = (datetime.now() - start_time).total_seconds()
                    self._update_stats(retrieval_time)

                    self.logger.info(f"Used fallback strategy: {strategy}")
                    return enhanced_results[:limit]

            except Exception as e:
                self.logger.warning(f"Fallback strategy {strategy} failed: {e}")

        # If all strategies fail, return empty results
        self.logger.error("All retrieval strategies failed")
        return []

    def _cache_results(
        self, cache_key: str, results: list[tuple[MemoryItem, RelevanceScore]]
    ) -> None:
        """Cache retrieval results."""
        if len(self.query_cache) >= self.cache_size_limit:
            # Remove oldest entry
            oldest_key = next(iter(self.query_cache))
            del self.query_cache[oldest_key]

        self.query_cache[cache_key] = results.copy()

    def _update_stats(self, retrieval_time: float) -> None:
        """Update retrieval statistics."""
        self.retrieval_stats["total_queries"] += 1
        current_avg = self.retrieval_stats["average_retrieval_time"]
        total_queries = self.retrieval_stats["total_queries"]

        # Update running average
        new_avg = ((current_avg * (total_queries - 1)) + retrieval_time) / total_queries
        self.retrieval_stats["average_retrieval_time"] = new_avg

    def get_retrieval_stats(self) -> dict[str, Any]:
        """Get retrieval performance statistics."""
        cache_total = (
            self.retrieval_stats["cache_hits"] + self.retrieval_stats["cache_misses"]
        )
        cache_hit_rate = (
            self.retrieval_stats["cache_hits"] / cache_total if cache_total > 0 else 0.0
        )

        return {
            **self.retrieval_stats,
            "cache_hit_rate": cache_hit_rate,
            "cache_size": len(self.query_cache),
            "primary_strategy": self.primary_strategy,
        }

    def clear_cache(self) -> None:
        """Clear the query cache."""
        self.query_cache.clear()
        self.logger.info("Query cache cleared")
