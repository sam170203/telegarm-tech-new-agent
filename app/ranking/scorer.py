"""Ranking scorer for news stories using composite scoring algorithm."""

import math
import re
from datetime import datetime, timedelta
from typing import Optional
from app.models import Story
from app.config.settings import settings
from app.utils.logger import logger


class RelevanceScorer:
    """Calculate relevance score using TF-IDF-like matching."""
    
    def __init__(self, interest_keywords: list[str]):
        """Initialize with user interest keywords.
        
        Args:
            interest_keywords: List of keywords user is interested in
        """
        self.keywords = [k.lower() for k in interest_keywords]
    
    def score(self, story: Story) -> float:
        """Score relevance of a story (0.0 to 1.0).
        
        Matches keywords in:
        - Title (higher weight)
        - URL (medium weight)
        - Content (lower weight)
        
        Args:
            story: Story to score
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        if not story.title:
            return 0.0
        
        matches = 0
        max_matches = len(self.keywords)
        
        # Normalize text
        title = story.title.lower()
        url = (story.url or "").lower()
        content = (story.content or "").lower()
        
        # Score each keyword
        title_weight = 3.0
        url_weight = 2.0
        content_weight = 1.0
        max_weight = max_matches * (title_weight + url_weight + content_weight)
        
        weighted_score = 0.0
        
        for keyword in self.keywords:
            keyword_lower = keyword.lower()
            
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(keyword_lower) + r'\b'
            
            # Count matches (with diminishing returns per keyword)
            if re.search(pattern, title):
                weighted_score += title_weight
            if re.search(pattern, url):
                weighted_score += url_weight
            if re.search(pattern, content):
                weighted_score += content_weight
        
        # Normalize to 0.0 - 1.0
        score = weighted_score / max_weight if max_weight > 0 else 0.0
        return min(score, 1.0)


class VaralityScorer:
    """Calculate virality score based on engagement metrics."""
    
    def score(self, story: Story) -> float:
        """Score virality based on HN/Reddit metrics (0.0 to 1.0).
        
        Uses logarithmic scaling to prevent outliers from dominating.
        
        Args:
            story: Story to score
            
        Returns:
            Virality score between 0.0 and 1.0
        """
        # Extract engagement metrics
        hn_score = story.metadata.get("hn_score", 0) if story.metadata else 0
        reddit_upvotes = story.metadata.get("reddit_upvotes", 0) if story.metadata else 0
        reddit_comments = story.metadata.get("reddit_comments", 0) if story.metadata else 0
        
        # Normalize using logarithmic scaling
        # log(1+x) prevents zero from being penalized
        hn_normalized = math.log(1 + hn_score) / math.log(1 + 500)  # 500 is typical top HN
        reddit_normalized = (
            math.log(1 + reddit_upvotes + reddit_comments * 0.5) / math.log(1 + 1000)
        )  # 1000 is typical top Reddit engagement
        
        # Average them
        score = (hn_normalized + reddit_normalized) / 2.0
        return min(score, 1.0)


class DepthScorer:
    """Score technical depth of content."""
    
    def __init__(self):
        """Initialize with technical indicators."""
        self.technical_keywords = [
            "algorithm", "architecture", "benchmark", "framework",
            "implementation", "optimization", "performance", "research",
            "paper", "github", "code", "open source", "systems design",
            "protocol", "cryptography", "networking", "database",
            "machine learning", "deep learning", "neural", "transformer",
            "cuda", "gpu", "distributed", "concurrent", "async",
        ]
    
    def score(self, story: Story) -> float:
        """Score technical depth (0.0 to 1.0).
        
        Higher for:
        - Technical keywords in title
        - Longer descriptions (indicates more content)
        - Academic/research sources
        
        Args:
            story: Story to score
            
        Returns:
            Depth score between 0.0 and 1.0
        """
        if not story.title:
            return 0.0
        
        score = 0.0
        
        # Check for technical keywords
        title_lower = story.title.lower()
        content_lower = (story.content or "").lower()
        url_lower = (story.url or "").lower()
        
        keyword_matches = sum(
            1 for keyword in self.technical_keywords
            if keyword in title_lower or keyword in content_lower or keyword in url_lower
        )
        
        score += min(keyword_matches / 3.0, 1.0) * 0.5
        
        # Length-based scoring (longer = more detail)
        content_length = len(story.content or "")
        length_score = min(content_length / 500.0, 1.0) * 0.3
        score += length_score
        
        # Source credibility (ArXiv, GitHub, etc.)
        from app.models import NewsSource
        if story.source == NewsSource.ARXIV:
            score += 0.2
        elif story.source == NewsSource.GITHUB:
            score += 0.15
        elif story.source == NewsSource.HACKER_NEWS:
            score += 0.1
        
        return min(score, 1.0)


class NoveltyScorer:
    """Score how recent/novel a story is."""
    
    def score(self, story: Story) -> float:
        """Score novelty based on recency (0.0 to 1.0).
        
        Recent stories score higher. Uses exponential decay.
        
        Args:
            story: Story to score
            
        Returns:
            Novelty score between 0.0 and 1.0
        """
        if not story.published_at:
            # If no date, assume recent
            return 0.8
        
        now = datetime.now(story.published_at.tzinfo) if story.published_at.tzinfo else datetime.now()
        age_seconds = (now - story.published_at).total_seconds()
        age_days = age_seconds / (24 * 3600)
        
        # Exponential decay: e^(-age_days/7) where half-life is 7 days
        half_life = 7.0
        decay = math.exp(-age_days / half_life)
        
        return min(decay, 1.0)


class CompositeScorer:
    """Combine all scoring dimensions into a single composite score."""
    
    def __init__(
        self,
        interest_keywords: list[str],
        weight_relevance: float = 0.4,
        weight_virality: float = 0.3,
        weight_depth: float = 0.2,
        weight_novelty: float = 0.1,
    ):
        """Initialize composite scorer with weights.
        
        Args:
            interest_keywords: User's interest keywords
            weight_relevance: Weight for relevance (0.0-1.0)
            weight_virality: Weight for virality (0.0-1.0)
            weight_depth: Weight for technical depth (0.0-1.0)
            weight_novelty: Weight for novelty/recency (0.0-1.0)
        """
        self.relevance_scorer = RelevanceScorer(interest_keywords)
        self.virality_scorer = VaralityScorer()
        self.depth_scorer = DepthScorer()
        self.novelty_scorer = NoveltyScorer()
        
        # Normalize weights
        total = weight_relevance + weight_virality + weight_depth + weight_novelty
        self.w_relevance = weight_relevance / total
        self.w_virality = weight_virality / total
        self.w_depth = weight_depth / total
        self.w_novelty = weight_novelty / total
        
        logger.info(
            f"Scorer initialized: "
            f"relevance={self.w_relevance:.2f}, "
            f"virality={self.w_virality:.2f}, "
            f"depth={self.w_depth:.2f}, "
            f"novelty={self.w_novelty:.2f}"
        )
    
    def score(self, story: Story) -> float:
        """Calculate composite score for a story (0.0 to 1.0).
        
        Args:
            story: Story to score
            
        Returns:
            Composite score between 0.0 and 1.0
        """
        relevance = self.relevance_scorer.score(story)
        virality = self.virality_scorer.score(story)
        depth = self.depth_scorer.score(story)
        novelty = self.novelty_scorer.score(story)
        
        composite = (
            self.w_relevance * relevance
            + self.w_virality * virality
            + self.w_depth * depth
            + self.w_novelty * novelty
        )
        
        return min(composite, 1.0)
    
    def score_with_breakdown(self, story: Story) -> dict:
        """Calculate score and return detailed breakdown.
        
        Args:
            story: Story to score
            
        Returns:
            Dict with composite score and individual component scores
        """
        relevance = self.relevance_scorer.score(story)
        virality = self.virality_scorer.score(story)
        depth = self.depth_scorer.score(story)
        novelty = self.novelty_scorer.score(story)
        
        composite = (
            self.w_relevance * relevance
            + self.w_virality * virality
            + self.w_depth * depth
            + self.w_novelty * novelty
        )
        
        return {
            "composite": min(composite, 1.0),
            "relevance": relevance,
            "virality": virality,
            "depth": depth,
            "novelty": novelty,
            "weights": {
                "relevance": self.w_relevance,
                "virality": self.w_virality,
                "depth": self.w_depth,
                "novelty": self.w_novelty,
            },
        }


def create_scorer() -> CompositeScorer:
    """Factory function to create a scorer from settings."""
    return CompositeScorer(
        interest_keywords=settings.interest_list,
        weight_relevance=settings.rank_weight_relevance,
        weight_virality=settings.rank_weight_virality,
        weight_depth=settings.rank_weight_depth,
        weight_novelty=settings.rank_weight_novelty,
    )
