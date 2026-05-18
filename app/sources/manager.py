"""
News manager: orchestrates all news sources.
Fetches from all sources in parallel, deduplicates, saves to database.
"""

import asyncio
from typing import Dict, List

from app.models import Story, NewsSource
from app.sources.base import NewsSourceBase
from app.sources.hacker_news import HackerNewsFetcher
from app.sources.reddit_fetcher import RedditFetcher
from app.sources.deduplicator import Deduplicator
from app.memory.dao import StoryDAO
from app.config.settings import settings
from app.utils.logger import setup_logger
from app.utils.errors import FetchError

logger = setup_logger(__name__)


class NewsManager:
    """Orchestrate all news sources.
    
    Responsibilities:
    - Fetch from all sources in parallel
    - Deduplicate stories
    - Save to database
    - Track fetch statistics
    """

    def __init__(self, dao: StoryDAO):
        """Initialize news manager.
        
        Args:
            dao: StoryDAO for persistence
        """
        self.dao = dao
        self.sources: Dict[NewsSource, NewsSourceBase] = {
            NewsSource.HACKER_NEWS: HackerNewsFetcher(),
            NewsSource.REDDIT: RedditFetcher(),
            # Add more sources here in Phase 3:
            # NewsSource.GITHUB: GitHubFetcher(),
            # NewsSource.ARXIV: ArxivFetcher(),
        }

    async def fetch_all(self) -> Dict[str, int]:
        """Fetch from all enabled sources in parallel.
        
        Returns:
            Dict mapping source name -> count of new stories saved
            
        Example:
            {
                'hacker_news': 42,
                'reddit': 156,
                'total': 198,
                'duplicates_removed': 47
            }
        """
        logger.info("=" * 60)
        logger.info("STARTING NEWS FETCH FROM ALL SOURCES")
        logger.info("=" * 60)

        # Build fetch tasks
        tasks = []
        source_list = []

        for source_type, fetcher in self.sources.items():
            limit = getattr(
                settings,
                f"{source_type.value}_fetch_limit",
                100
            )
            tasks.append(fetcher.fetch(limit))
            source_list.append((source_type, fetcher))

        # Fetch in parallel
        logger.info(f"Fetching from {len(tasks)} sources in parallel...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        all_stories: List[Story] = []
        fetch_stats = {}

        for (source_type, fetcher), result in zip(source_list, results):
            if isinstance(result, Exception):
                logger.error(f"✗ {source_type.value}: {result}")
                fetch_stats[source_type.value] = 0
            elif result:
                logger.info(f"✓ {source_type.value}: {len(result)} stories")
                all_stories.extend(result)
                fetch_stats[source_type.value] = len(result)
            else:
                fetch_stats[source_type.value] = 0

        logger.info(f"\nTotal stories fetched: {len(all_stories)}")

        # Deduplicate
        logger.info("Deduplicating across sources...")
        unique_stories = Deduplicator.merge_stories(all_stories)
        duplicates_removed = len(all_stories) - len(unique_stories)

        # Save to database
        logger.info(f"Saving {len(unique_stories)} stories to database...")
        saved_count = self.dao.save_stories(unique_stories)

        # Summary
        logger.info("=" * 60)
        logger.info("FETCH COMPLETE")
        logger.info("=" * 60)
        for source, count in fetch_stats.items():
            logger.info(f"  {source}: {count} stories")
        logger.info(f"  Total fetched: {len(all_stories)} stories")
        logger.info(f"  Duplicates removed: {duplicates_removed}")
        logger.info(f"  New stories saved: {saved_count}")
        logger.info("=" * 60)

        return {
            **fetch_stats,
            "total_fetched": len(all_stories),
            "duplicates_removed": duplicates_removed,
            "new_stories_saved": saved_count,
        }

    async def fetch_source(
        self,
        source_type: NewsSource,
        limit: int = None
    ) -> int:
        """Fetch from a single source and save.
        
        Args:
            source_type: Which source to fetch
            limit: Max stories (uses settings if None)
            
        Returns:
            Count of new stories saved
        """
        if source_type not in self.sources:
            raise FetchError(f"Unknown source: {source_type}")

        fetcher = self.sources[source_type]

        if limit is None:
            limit = getattr(
                settings,
                f"{source_type.value}_fetch_limit",
                100
            )

        logger.info(f"Fetching {limit} stories from {source_type.value}...")

        try:
            stories = await fetcher.fetch(limit)
            saved = self.dao.save_stories(stories)
            logger.info(f"Saved {saved} new stories from {source_type.value}")
            return saved
        except Exception as e:
            logger.error(f"Failed to fetch {source_type.value}: {e}")
            return 0

    def get_enabled_sources(self) -> List[str]:
        """Get list of enabled source names.
        
        Returns:
            List of source names (e.g., ['hacker_news', 'reddit'])
        """
        return [source.value for source in self.sources.keys()]
