"""Ranking manager to score and select top stories."""

from typing import Optional
from app.models import Story
from app.ranking.scorer import CompositeScorer, create_scorer
from app.utils.logger import logger


class RankingManager:
    """Orchestrate story ranking and top-N selection."""
    
    def __init__(self, scorer: Optional[CompositeScorer] = None):
        """Initialize with a scorer.
        
        Args:
            scorer: CompositeScorer instance. If None, creates from settings.
        """
        self.scorer = scorer or create_scorer()
        logger.info("RankingManager initialized")
    
    def rank_stories(self, stories: list[Story]) -> list[tuple[Story, float]]:
        """Rank stories by composite score.
        
        Args:
            stories: List of stories to rank
            
        Returns:
            List of (story, score) tuples sorted by score descending
        """
        if not stories:
            logger.warning("No stories to rank")
            return []
        
        ranked = []
        for story in stories:
            score = self.scorer.score(story)
            ranked.append((story, score))
        
        # Sort by score descending
        ranked.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"Ranked {len(ranked)} stories")
        return ranked
    
    def select_top_n(self, stories: list[Story], n: int = 10) -> list[Story]:
        """Select top N stories by composite score.
        
        Args:
            stories: List of stories to select from
            n: Number of top stories to return
            
        Returns:
            List of top N stories, sorted by score descending
        """
        ranked = self.rank_stories(stories)
        top_n = ranked[:n]
        
        logger.info(f"Selected top {len(top_n)} stories from {len(stories)} total")
        
        return [story for story, score in top_n]
    
    def get_ranked_with_scores(self, stories: list[Story]) -> list[dict]:
        """Get stories with detailed scoring breakdown.
        
        Args:
            stories: List of stories to rank
            
        Returns:
            List of dicts with story and score details
        """
        if not stories:
            return []
        
        results = []
        for story in stories:
            breakdown = self.scorer.score_with_breakdown(story)
            results.append({
                "story": story,
                "score": breakdown["composite"],
                "breakdown": breakdown,
            })
        
        # Sort by composite score
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return results
    
    def format_ranking_report(self, stories: list[Story], n: int = 10) -> str:
        """Generate a human-readable ranking report.
        
        Args:
            stories: Stories to rank
            n: Number of top stories to show
            
        Returns:
            Formatted report string
        """
        ranked = self.get_ranked_with_scores(stories)[:n]
        
        if not ranked:
            return "No stories to rank"
        
        report = f"Top {len(ranked)} Stories by Relevance\n"
        report += "=" * 60 + "\n\n"
        
        for i, item in enumerate(ranked, 1):
            story = item["story"]
            score = item["score"]
            breakdown = item["breakdown"]
            
            report += f"{i}. {story.title}\n"
            report += f"   Score: {score:.3f}\n"
            report += f"   Source: {story.source} | {story.url}\n"
            report += f"   Relevance: {breakdown['relevance']:.3f} | "
            report += f"Virality: {breakdown['virality']:.3f} | "
            report += f"Depth: {breakdown['depth']:.3f} | "
            report += f"Novelty: {breakdown['novelty']:.3f}\n"
            report += "\n"
        
        return report
