"""
Abstract base class for news sources.
All news sources inherit from this.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from app.models import Story, NewsSource
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class NewsSourceBase(ABC):
    """Abstract base class for news sources.
    
    All concrete news sources (HN, Reddit, GitHub, etc.) must:
    1. Set the source_type class variable
    2. Implement the fetch() method
    """

    source_type: NewsSource

    @abstractmethod
    async def fetch(self, limit: int = 50) -> List[Story]:
        """Fetch stories from this news source.

        Args:
            limit: Maximum number of stories to fetch

        Returns:
            List of Story objects

        Raises:
            FetchError: If fetching fails
        """
        pass

    async def fetch_and_save(self, dao, limit: int = 50) -> int:
        """Fetch stories and save to database, deduplicating by ID.

        Args:
            dao: StoryDAO instance for persistence
            limit: Maximum stories to fetch

        Returns:
            Count of new stories saved (not including duplicates)
        """
        try:
            stories = await self.fetch(limit)
            logger.info(f"Fetched {len(stories)} stories from {self.source_type.value}")

            count = 0
            for story in stories:
                # Only save if story doesn't already exist
                if not dao.story_exists(story.id):
                    if dao.save_story(story):
                        count += 1
                        logger.debug(f"Saved: {story.title[:50]}...")

            logger.info(
                f"{self.source_type.value}: Saved {count} new stories "
                f"({len(stories) - count} duplicates skipped)"
            )
            return count

        except Exception as e:
            logger.error(f"Error fetching from {self.source_type.value}: {e}")
            raise

    def __str__(self):
        return f"{self.__class__.__name__}({self.source_type.value})"
