"""Quality metrics for healthcare chatbot outputs."""

from __future__ import annotations

import time
from dataclasses import dataclass, asdict
from typing import Optional
from collections import defaultdict
import statistics

import numpy as np
from app.services.embedding import EmbeddingService


@dataclass
class OutputQuality:
    """Measured quality metrics for a single response."""

    # Relevance: semantic similarity between query and response
    relevance_score: float  # 0-1
    
    # Coherence: linguistic quality and structure
    coherence_score: float  # 0-1
    
    # Response latency in milliseconds
    response_time_ms: float
    
    # Coverage: how well the response addresses the query
    coverage_score: float  # 0-1
    
    # Confidence: model confidence in the response (if available)
    confidence_score: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    def overall_score(self) -> float:
        """Calculate weighted overall quality score."""
        weights = {
            'relevance_score': 0.35,
            'coherence_score': 0.20,
            'coverage_score': 0.35,
            'response_time_ms': 0.10,  # Negative: lower is better
        }
        
        # Normalize response time (treat >5000ms as 0 score)
        time_score = max(0, 1 - (self.response_time_ms / 5000))
        
        overall = (
            self.relevance_score * weights['relevance_score'] +
            self.coherence_score * weights['coherence_score'] +
            self.coverage_score * weights['coverage_score'] +
            time_score * weights['response_time_ms']
        )
        
        return round(overall, 3)


class QualityMetricsCalculator:
    """Calculate quality metrics for healthcare chatbot responses."""
    
    def __init__(self):
        self.embedder = EmbeddingService()
        self.medical_keywords = {
            'symptoms': ['đau', 'sốt', 'ho', 'buồn nôn', 'mệt mỏi', 'chóng mặt', 'ngứa', 'sưng'],
            'treatments': ['uống', 'bôi', 'tiêm', 'phẫu thuật', 'liệu pháp', 'thuốc', 'điều trị'],
            'advice': ['nên', 'không nên', 'cần', 'tránh', 'hạn chế', 'khuyến cáo', 'lưu ý'],
        }
    
    def calculate_relevance(self, query: str, response: str) -> float:
        """
        Calculate semantic relevance between query and response.
        Returns 0-1 score based on cosine similarity.
        """
        try:
            query_embedding = self.embedder.embed_text(query)
            response_embedding = self.embedder.embed_text(response)
            
            # Cosine similarity
            similarity = float(np.dot(query_embedding, response_embedding))
            # Normalize to 0-1 range (embeddings are already normalized)
            return max(0, min(1, (similarity + 1) / 2))
        except Exception:
            return 0.5  # Default to neutral if embedding fails
    
    def calculate_coherence(self, response: str) -> float:
        """
        Calculate coherence based on text structure and length.
        Penalizes very short or extremely fragmented responses.
        """
        sentences = [s.strip() for s in response.split('.') if s.strip()]
        words = response.split()
        
        if not sentences or not words:
            return 0.1
        
        avg_words_per_sentence = len(words) / len(sentences)
        
        # Ideal: 10-20 words per sentence
        if 5 <= avg_words_per_sentence <= 25:
            coherence = 0.9
        elif 3 <= avg_words_per_sentence <= 30:
            coherence = 0.7
        else:
            coherence = 0.4
        
        # Bonus: multiple sentences (shows structured response)
        if len(sentences) >= 2:
            coherence = min(1.0, coherence + 0.1)
        
        return min(1.0, coherence)
    
    def calculate_coverage(self, query: str, response: str) -> float:
        """
        Calculate how well the response addresses the query.
        Looks for medical keywords and key terms matching.
        """
        query_words = set(query.lower().split())
        response_words = set(response.lower().split())
        
        # Overlap of non-stop words
        overlap_words = query_words & response_words
        
        # Count medical keywords in response
        medical_score = 0
        for category_words in self.medical_keywords.values():
            medical_score += sum(1 for word in response_words if any(kw in word for kw in category_words))
        
        # Query has medical keywords?
        query_has_medical = any(
            any(kw in q for q in query_words for kw in kws)
            for kws in self.medical_keywords.values()
        )
        
        if query_has_medical:
            # If query is medical, response should have medical keywords
            coverage = min(1.0, 0.5 + (medical_score / 5) * 0.5)
        else:
            # Otherwise, check word overlap
            coverage = len(overlap_words) / max(len(query_words), 1)
            coverage = min(1.0, coverage)
        
        return round(coverage, 3)
    
    def calculate_quality(
        self,
        query: str,
        response: str,
        response_time_ms: float,
        confidence_score: Optional[float] = None,
    ) -> OutputQuality:
        """
        Calculate all quality metrics for a response.
        
        Args:
            query: User's input message
            response: Chatbot's response
            response_time_ms: How long the response took
            confidence_score: Optional model confidence (0-1)
        
        Returns:
            OutputQuality object with all metrics
        """
        return OutputQuality(
            relevance_score=self.calculate_relevance(query, response),
            coherence_score=self.calculate_coherence(response),
            response_time_ms=response_time_ms,
            coverage_score=self.calculate_coverage(query, response),
            confidence_score=confidence_score,
        )


class SystemMetrics:
    """Collect and aggregate system-level performance metrics."""
    
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.response_times: list[float] = []
        self.quality_scores: list[float] = []
        self.user_sessions: set[str] = set()
        self.start_time = time.time()
    
    def record_request(self, duration_ms: float, success: bool = True, user_id: Optional[str] = None):
        """Record a request."""
        self.request_count += 1
        if success:
            self.response_times.append(duration_ms)
        else:
            self.error_count += 1
        
        if user_id:
            self.user_sessions.add(user_id)
    
    def record_quality_score(self, score: float):
        """Record a quality score."""
        self.quality_scores.append(score)
    
    def get_summary(self) -> dict:
        """Get system metrics summary."""
        uptime_seconds = time.time() - self.start_time
        
        if self.response_times:
            avg_latency = statistics.mean(self.response_times)
            p95_latency = self._percentile(self.response_times, 95)
            p99_latency = self._percentile(self.response_times, 99)
            min_latency = min(self.response_times)
            max_latency = max(self.response_times)
        else:
            avg_latency = p95_latency = p99_latency = min_latency = max_latency = 0
        
        if self.quality_scores:
            avg_quality = statistics.mean(self.quality_scores)
            min_quality = min(self.quality_scores)
            max_quality = max(self.quality_scores)
        else:
            avg_quality = min_quality = max_quality = 0
        
        error_rate = self.error_count / max(self.request_count, 1)
        throughput = self.request_count / max(uptime_seconds, 1)
        
        return {
            'total_requests': self.request_count,
            'successful_requests': self.request_count - self.error_count,
            'error_count': self.error_count,
            'error_rate_percent': round(error_rate * 100, 2),
            'active_users': len(self.user_sessions),
            'latency_ms': {
                'avg': round(avg_latency, 2),
                'p95': round(p95_latency, 2),
                'p99': round(p99_latency, 2),
                'min': round(min_latency, 2),
                'max': round(max_latency, 2),
            },
            'quality': {
                'avg_score': round(avg_quality, 3),
                'min_score': round(min_quality, 3),
                'max_score': round(max_quality, 3),
                'measurements': len(self.quality_scores),
            },
            'throughput_req_per_sec': round(throughput, 2),
            'uptime_seconds': round(uptime_seconds, 2),
        }
    
    @staticmethod
    def _percentile(values: list[float], percentile: int) -> float:
        """Calculate percentile of a list."""
        if not values:
            return 0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
