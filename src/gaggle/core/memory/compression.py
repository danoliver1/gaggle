"""Context compression for efficient memory usage and token reduction."""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
import logging

from .hierarchical import MemoryItem, MemoryLevel


@dataclass
class CompressionResult:
    """Result of context compression operation."""
    original_content: str
    compressed_content: str
    original_size: int
    compressed_size: int
    compression_ratio: float
    compression_method: str
    quality_score: float = 1.0  # How much information is preserved
    
    def get_token_savings(self) -> int:
        """Calculate token savings from compression."""
        return self.original_size - self.compressed_size
    
    def get_savings_percentage(self) -> float:
        """Calculate percentage of tokens saved."""
        if self.original_size == 0:
            return 0.0
        return (self.get_token_savings() / self.original_size) * 100


class ContextCompressor(ABC):
    """Abstract base class for context compression strategies."""
    
    @abstractmethod
    def compress(self, content: str, context: Dict[str, Any] = None) -> CompressionResult:
        """Compress content and return result with metrics."""
        pass
    
    @abstractmethod
    def decompress(self, compressed_content: str, context: Dict[str, Any] = None) -> str:
        """Decompress content (if applicable)."""
        pass
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (simple approximation)."""
        # Rough estimation: 1 token ≈ 4 characters for English text
        return len(text) // 4


class SummaryCompressor(ContextCompressor):
    """Compress context by creating intelligent summaries."""
    
    def __init__(self, max_summary_ratio: float = 0.3):
        self.max_summary_ratio = max_summary_ratio  # Max summary size as ratio of original
        self.logger = logging.getLogger("compression.summary")
        
        # Key information patterns
        self.key_patterns = [
            r'\b(?:error|exception|failed|success|completed)\b',
            r'\b(?:important|critical|urgent|priority)\b',
            r'\b(?:decision|conclusion|result|outcome)\b',
            r'\b(?:todo|action|next|step)\b',
            r'\b(?:bug|fix|issue|problem)\b'
        ]
    
    def compress(self, content: str, context: Dict[str, Any] = None) -> CompressionResult:
        """Create intelligent summary of content."""
        original_size = self.estimate_tokens(content)
        
        # Extract key information
        summary_parts = []
        
        # 1. Extract sentences with key patterns
        sentences = self._split_into_sentences(content)
        key_sentences = self._extract_key_sentences(sentences)
        
        # 2. Extract structured data (JSON, lists, etc.)
        structured_data = self._extract_structured_data(content)
        
        # 3. Extract numerical data and metrics
        metrics = self._extract_metrics(content)
        
        # 4. Create summary
        if key_sentences:
            summary_parts.append("Key Points: " + " ".join(key_sentences[:5]))  # Top 5 sentences
        
        if structured_data:
            summary_parts.append(f"Data: {structured_data}")
        
        if metrics:
            summary_parts.append(f"Metrics: {metrics}")
        
        # 5. Add context-specific information
        if context:
            context_summary = self._add_context_info(content, context)
            if context_summary:
                summary_parts.append(context_summary)
        
        compressed_content = " | ".join(summary_parts)
        
        # Ensure we don't exceed max ratio
        max_size = int(original_size * self.max_summary_ratio)
        if self.estimate_tokens(compressed_content) > max_size:
            # Truncate to fit
            target_chars = max_size * 4  # Rough token-to-char conversion
            compressed_content = compressed_content[:target_chars] + "..."
        
        compressed_size = self.estimate_tokens(compressed_content)
        compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
        
        # Estimate quality based on information preservation
        quality_score = self._estimate_quality(content, compressed_content)
        
        return CompressionResult(
            original_content=content,
            compressed_content=compressed_content,
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=compression_ratio,
            compression_method="summary",
            quality_score=quality_score
        )
    
    def decompress(self, compressed_content: str, context: Dict[str, Any] = None) -> str:
        """Return compressed content (summaries can't be fully decompressed)."""
        return compressed_content
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _extract_key_sentences(self, sentences: List[str]) -> List[str]:
        """Extract sentences containing key information."""
        scored_sentences = []
        
        for sentence in sentences:
            score = 0
            sentence_lower = sentence.lower()
            
            # Score based on key patterns
            for pattern in self.key_patterns:
                matches = len(re.findall(pattern, sentence_lower))
                score += matches * 2
            
            # Score based on sentence length (prefer medium-length sentences)
            length = len(sentence.split())
            if 5 <= length <= 20:
                score += 1
            elif length > 20:
                score -= 1
            
            # Score based on position (earlier sentences often more important)
            if len(scored_sentences) < 3:
                score += 1
            
            if score > 0:
                scored_sentences.append((sentence, score))
        
        # Sort by score and return top sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        return [sentence for sentence, _ in scored_sentences]
    
    def _extract_structured_data(self, text: str) -> str:
        """Extract and summarize structured data."""
        structured_parts = []
        
        # Extract JSON-like structures
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        json_matches = re.findall(json_pattern, text)
        
        for match in json_matches[:3]:  # Limit to first 3 JSON objects
            try:
                data = json.loads(match)
                if isinstance(data, dict):
                    keys = list(data.keys())[:5]  # First 5 keys
                    structured_parts.append(f"Object({', '.join(keys)})")
            except json.JSONDecodeError:
                pass
        
        # Extract lists and arrays
        list_pattern = r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]'
        list_matches = re.findall(list_pattern, text)
        
        for match in list_matches[:2]:  # Limit to first 2 lists
            try:
                data = json.loads(match)
                if isinstance(data, list) and len(data) > 0:
                    structured_parts.append(f"List({len(data)} items)")
            except json.JSONDecodeError:
                pass
        
        return ", ".join(structured_parts) if structured_parts else ""
    
    def _extract_metrics(self, text: str) -> str:
        """Extract numerical metrics and statistics."""
        metrics = []
        
        # Extract percentages
        percentages = re.findall(r'\b\d+(?:\.\d+)?%', text)
        if percentages:
            metrics.append(f"Percentages: {', '.join(percentages[:3])}")
        
        # Extract numbers with units
        numbers_with_units = re.findall(r'\b\d+(?:\.\d+)?\s*(?:ms|seconds?|minutes?|hours?|days?|MB|GB|KB)', text)
        if numbers_with_units:
            metrics.append(f"Measurements: {', '.join(numbers_with_units[:3])}")
        
        # Extract counts
        count_pattern = r'\b(?:total|count|number):\s*\d+'
        counts = re.findall(count_pattern, text, re.IGNORECASE)
        if counts:
            metrics.append(f"Counts: {', '.join(counts[:3])}")
        
        return "; ".join(metrics) if metrics else ""
    
    def _add_context_info(self, content: str, context: Dict[str, Any]) -> str:
        """Add context-specific summary information."""
        context_parts = []
        
        # Add agent information
        if "agent_role" in context:
            context_parts.append(f"Agent: {context['agent_role']}")
        
        # Add sprint information
        if "sprint_id" in context:
            context_parts.append(f"Sprint: {context['sprint_id']}")
        
        # Add task information
        if "task_type" in context:
            context_parts.append(f"Task: {context['task_type']}")
        
        return ", ".join(context_parts) if context_parts else ""
    
    def _estimate_quality(self, original: str, compressed: str) -> float:
        """Estimate how well the compression preserves information."""
        if not original or not compressed:
            return 0.0
        
        # Simple heuristic: longer summaries generally preserve more information
        length_ratio = len(compressed) / len(original)
        
        # Check if key terms are preserved
        original_words = set(re.findall(r'\b\w+\b', original.lower()))
        compressed_words = set(re.findall(r'\b\w+\b', compressed.lower()))
        
        if original_words:
            word_preservation = len(compressed_words.intersection(original_words)) / len(original_words)
        else:
            word_preservation = 0.0
        
        # Combine metrics
        quality_score = length_ratio * 0.3 + word_preservation * 0.7
        return min(quality_score, 1.0)


class TemplateCompressor(ContextCompressor):
    """Compress context by extracting and replacing common templates."""
    
    def __init__(self):
        self.logger = logging.getLogger("compression.template")
        self.templates: Dict[str, str] = {}  # Template ID -> Template content
        self.template_counter = 0
    
    def compress(self, content: str, context: Dict[str, Any] = None) -> CompressionResult:
        """Compress by replacing repeated patterns with template references."""
        original_size = self.estimate_tokens(content)
        compressed_content = content
        
        # Find repeated patterns
        patterns = self._find_repeated_patterns(content)
        
        # Replace patterns with template references
        for pattern, occurrences in patterns.items():
            if occurrences >= 2 and len(pattern) > 20:  # Only template significant patterns
                template_id = self._create_template(pattern)
                template_ref = f"{{TEMPLATE_{template_id}}}"
                compressed_content = compressed_content.replace(pattern, template_ref)
        
        compressed_size = self.estimate_tokens(compressed_content)
        compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
        
        # Quality is high since templates preserve exact information
        quality_score = 1.0
        
        return CompressionResult(
            original_content=content,
            compressed_content=compressed_content,
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=compression_ratio,
            compression_method="template",
            quality_score=quality_score
        )
    
    def decompress(self, compressed_content: str, context: Dict[str, Any] = None) -> str:
        """Decompress by replacing template references with actual content."""
        decompressed = compressed_content
        
        # Replace template references
        template_pattern = r'\{TEMPLATE_(\d+)\}'
        matches = re.findall(template_pattern, decompressed)
        
        for template_id in matches:
            if template_id in self.templates:
                template_ref = f"{{TEMPLATE_{template_id}}}"
                template_content = self.templates[template_id]
                decompressed = decompressed.replace(template_ref, template_content)
        
        return decompressed
    
    def _find_repeated_patterns(self, content: str) -> Dict[str, int]:
        """Find repeated text patterns."""
        patterns = {}
        
        # Look for repeated lines
        lines = content.split('\n')
        line_counts = {}
        
        for line in lines:
            line = line.strip()
            if len(line) > 10:  # Ignore short lines
                line_counts[line] = line_counts.get(line, 0) + 1
        
        # Add lines that appear multiple times
        for line, count in line_counts.items():
            if count > 1:
                patterns[line] = count
        
        # Look for repeated phrases (simplified)
        words = content.split()
        for i in range(len(words) - 4):  # 5-word phrases
            phrase = " ".join(words[i:i+5])
            if len(phrase) > 20:
                patterns[phrase] = patterns.get(phrase, 0) + 1
        
        return patterns
    
    def _create_template(self, pattern: str) -> str:
        """Create a new template and return its ID."""
        self.template_counter += 1
        template_id = str(self.template_counter)
        self.templates[template_id] = pattern
        return template_id


class HierarchicalCompressor:
    """Main compression system that applies different strategies based on content."""
    
    def __init__(self):
        self.compressors = {
            "summary": SummaryCompressor(),
            "template": TemplateCompressor()
        }
        self.logger = logging.getLogger("compression.hierarchical")
        
        # Compression statistics
        self.stats = {
            "total_compressions": 0,
            "total_tokens_saved": 0,
            "total_original_size": 0,
            "average_compression_ratio": 1.0,
            "compressions_by_method": {}
        }
    
    def compress_memory_item(self, item: MemoryItem, strategy: str = "auto") -> CompressionResult:
        """Compress a memory item using the best strategy."""
        
        # Convert memory item to text
        content = self._memory_item_to_text(item)
        
        # Select compression strategy
        if strategy == "auto":
            strategy = self._select_best_strategy(item)
        
        # Apply compression
        compressor = self.compressors.get(strategy, self.compressors["summary"])
        
        context = {
            "memory_level": item.level.value,
            "agent_id": item.agent_id,
            "sprint_id": item.sprint_id,
            "tags": list(item.tags)
        }
        
        result = compressor.compress(content, context)
        
        # Update statistics
        self._update_stats(result)
        
        self.logger.debug(
            f"Compressed memory item {item.id} using {strategy}: "
            f"{result.original_size} -> {result.compressed_size} tokens "
            f"({result.compression_ratio:.2f} ratio)"
        )
        
        return result
    
    def compress_context_batch(self, items: List[MemoryItem], max_total_size: int = 2000) -> CompressionResult:
        """Compress a batch of memory items to fit within token limit."""
        
        # Sort items by importance and recency
        sorted_items = sorted(
            items,
            key=lambda x: (x.importance_score, x.access_count, x.last_accessed),
            reverse=True
        )
        
        compressed_parts = []
        total_tokens = 0
        original_total = 0
        
        for item in sorted_items:
            if total_tokens >= max_total_size:
                break
            
            # Compress individual item
            compression_result = self.compress_memory_item(item)
            original_total += compression_result.original_size
            
            # Check if compressed item fits
            if total_tokens + compression_result.compressed_size <= max_total_size:
                compressed_parts.append(compression_result.compressed_content)
                total_tokens += compression_result.compressed_size
            else:
                # Try to fit a summary
                remaining_tokens = max_total_size - total_tokens
                if remaining_tokens > 50:  # Minimum size for useful summary
                    summary = self._create_ultra_compact_summary(item, remaining_tokens)
                    compressed_parts.append(summary)
                    total_tokens += self.compressors["summary"].estimate_tokens(summary)
                break
        
        # Combine all compressed parts
        final_content = "\n---\n".join(compressed_parts)
        final_size = self.compressors["summary"].estimate_tokens(final_content)
        
        return CompressionResult(
            original_content="",  # Not meaningful for batch
            compressed_content=final_content,
            original_size=original_total,
            compressed_size=final_size,
            compression_ratio=final_size / original_total if original_total > 0 else 1.0,
            compression_method="batch"
        )
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """Get comprehensive compression statistics."""
        if self.stats["total_compressions"] > 0:
            avg_ratio = self.stats["total_tokens_saved"] / self.stats["total_original_size"]
            self.stats["average_compression_ratio"] = 1.0 - avg_ratio
        
        return self.stats.copy()
    
    def _memory_item_to_text(self, item: MemoryItem) -> str:
        """Convert memory item to text for compression."""
        parts = []
        
        # Add tags
        if item.tags:
            parts.append(f"Tags: {', '.join(item.tags)}")
        
        # Add content
        if item.content:
            content_str = json.dumps(item.content, indent=2)
            parts.append(f"Content: {content_str}")
        
        # Add metadata
        metadata = []
        if item.agent_id:
            metadata.append(f"Agent: {item.agent_id}")
        if item.sprint_id:
            metadata.append(f"Sprint: {item.sprint_id}")
        if item.session_id:
            metadata.append(f"Session: {item.session_id}")
        
        if metadata:
            parts.append(f"Metadata: {', '.join(metadata)}")
        
        return "\n".join(parts)
    
    def _select_best_strategy(self, item: MemoryItem) -> str:
        """Select the best compression strategy for a memory item."""
        
        # Use summary compression for most content
        if item.level in [MemoryLevel.WORKING, MemoryLevel.EPISODIC]:
            return "summary"
        
        # Use template compression for procedural content
        elif item.level == MemoryLevel.PROCEDURAL:
            return "template"
        
        # Use summary for semantic content
        else:
            return "summary"
    
    def _create_ultra_compact_summary(self, item: MemoryItem, max_tokens: int) -> str:
        """Create an ultra-compact summary that fits in specified token limit."""
        
        # Start with most important information
        parts = []
        
        # Add most important tags
        if item.tags:
            important_tags = sorted(item.tags)[:3]  # First 3 tags alphabetically
            parts.append(f"#{', '.join(important_tags)}")
        
        # Add essential content
        if item.content:
            # Try to extract key-value pairs or important fields
            if isinstance(item.content, dict):
                important_keys = ["id", "title", "name", "type", "status", "result"]
                key_values = []
                for key in important_keys:
                    if key in item.content:
                        value = str(item.content[key])
                        if len(value) < 50:  # Only short values
                            key_values.append(f"{key}:{value}")
                
                if key_values:
                    parts.append(" | ".join(key_values))
        
        # Combine and truncate to fit
        summary = " • ".join(parts)
        
        # Estimate tokens and truncate if necessary
        estimated_tokens = self.compressors["summary"].estimate_tokens(summary)
        if estimated_tokens > max_tokens:
            # Rough truncation
            target_chars = max_tokens * 4
            summary = summary[:target_chars] + "..."
        
        return summary
    
    def _update_stats(self, result: CompressionResult) -> None:
        """Update compression statistics."""
        self.stats["total_compressions"] += 1
        self.stats["total_tokens_saved"] += result.get_token_savings()
        self.stats["total_original_size"] += result.original_size
        
        method = result.compression_method
        if method not in self.stats["compressions_by_method"]:
            self.stats["compressions_by_method"][method] = {
                "count": 0,
                "total_savings": 0,
                "average_ratio": 1.0
            }
        
        method_stats = self.stats["compressions_by_method"][method]
        method_stats["count"] += 1
        method_stats["total_savings"] += result.get_token_savings()
        
        if method_stats["count"] > 0:
            avg_savings_per_compression = method_stats["total_savings"] / method_stats["count"]
            method_stats["average_ratio"] = avg_savings_per_compression