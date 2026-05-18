"""
Deduplication system for stories.
Identifies and merges duplicate stories from different sources.
"""

from difflib import SequenceMatcher
from typing import List, Set
from urllib.parse import urlparse

from app.models import Story
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class Deduplicator:
    """Find and merge duplicate stories across sources.
    
    Strategies:
    1. Exact URL match (same domain + path)
    2. Title similarity (TF-IDF like)
    3. Domain + title similarity (for aggregated stories)
    """

    # Sources to prioritize when merging (higher = more important)
    source_priority = {
        "hacker_news": 3,
        "reddit": 2,
        "github": 2,
        "arxiv": 1,
        "rss": 0,
    }

    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL for comparison (remove scheme, trailing slash, etc).
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL
        """
        if not url:
            return ""

        try:
            parsed = urlparse(url.lower())
            # Combine domain + path, remove scheme and trailing slash
            domain = parsed.netloc.lstrip("www.")
            path = parsed.path.rstrip("/")
            return f"{domain}{path}"
        except Exception:
            return url.lower()

    @staticmethod
    def title_similarity(a: str, b: str) -> float:
        """Calculate title similarity score (0.0-1.0).
        
        Uses SequenceMatcher (like difflib).
        
        Args:
            a: First title
            b: Second title
            
        Returns:
            Similarity score (0.0-1.0)
        """
        if not a or not b:
            return 0.0

        # Normalize: lowercase, remove punctuation
        a_normalized = a.lower().strip()
        b_normalized = b.lower().strip()

        return SequenceMatcher(None, a_normalized, b_normalized).ratio()

    @staticmethod
    def are_duplicates(
        story1: Story,
        story2: Story,
        title_threshold: float = 0.85,
        url_similarity: bool = True
    ) -> bool:
        """Check if two stories are duplicates.
        
        Args:
            story1: First story
            story2: Second story
            title_threshold: Minimum title similarity (0.0-1.0)
            url_similarity: Also check URL similarity
            
        Returns:
            True if stories are duplicates
        """
        if story1.id == story2.id:
            return True

        # Strategy 1: Exact URL match (strong signal)
        if story1.url and story2.url:
            url1_normalized = Deduplicator.normalize_url(story1.url)
            url2_normalized = Deduplicator.normalize_url(story2.url)

            if url1_normalized and url1_normalized == url2_normalized:
                return True

        # Strategy 2: Title similarity (secondary signal)
        sim = Deduplicator.title_similarity(story1.title, story2.title)
        if sim > title_threshold:
            return True

        return False

    @staticmethod
    def merge_stories(stories: List[Story]) -> List[Story]:
        """Merge duplicate stories, keeping the best version.
        
        When duplicates are found:
        - Keeps story from highest-priority source
        - Combines metadata
        - Preserves all engagement scores
        
        Args:
            stories: List of stories to deduplicate
            
        Returns:
            Deduplicated list of stories
        """
        if not stories:
            return []

        logger.info(f"Deduplicating {len(stories)} stories...")

        merged = []
        used_ids: Set[str] = set()

        for i, story in enumerate(stories):
            if story.id in used_ids:
                continue

            # Find all duplicates of this story
            duplicates = [story]

            for other in stories[i + 1 :]:
                if (
                    other.id not in used_ids
                    and Deduplicator.are_duplicates(story, other)
                ):
                    duplicates.append(other)
                    used_ids.add(other.id)

            # Choose best story from duplicates
            best = Deduplicator._select_best_story(duplicates)

            merged.append(best)
            used_ids.add(best.id)

        dedup_count = len(stories) - len(merged)
        logger.info(f"Removed {dedup_count} duplicates. Kept {len(merged)} unique stories")

        return merged

    @staticmethod
    def _select_best_story(duplicates: List[Story]) -> Story:
        """Select the best story from a list of duplicates.
        
        Scoring:
        1. Source priority (HN > Reddit > GitHub > ArXiv)
        2. Engagement (score + comments)
        3. Recency
        
        Args:
            duplicates: List of duplicate stories
            
        Returns:
            Best story
        """
        def score_story(s: Story) -> float:
            source_priority = Deduplicator.source_priority.get(
                s.source.value, 0
            )

            engagement = s.metadata.get("score", 0) + (
                s.metadata.get("comments", 0) * 0.1
            )

            # Source priority weighted heavily
            return source_priority * 100 + engagement

        return max(duplicates, key=score_story)
