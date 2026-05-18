"""
Hacker News fetcher.
Uses official HN Firebase API (no authentication required).
"""

import httpx
import asyncio
from datetime import datetime
from typing import List, Optional
from app.models import Story, NewsSource
from app.sources.base import NewsSourceBase
from app.utils.logger import setup_logger
from app.utils.errors import FetchError

logger = setup_logger(__name__)


class HackerNewsFetcher(NewsSourceBase):
    """Fetch top stories from Hacker News.
    
    API: https://hacker-news.firebaseio.com/v0
    No authentication required.
    Free tier: unlimited (public API)
    """

    source_type = NewsSource.HACKER_NEWS
    base_url = "https://hacker-news.firebaseio.com/v0"

    async def fetch(self, limit: int = 50) -> List[Story]:
        """Fetch top stories from Hacker News.

        Args:
            limit: Number of stories to fetch

        Returns:
            List of Story objects

        Raises:
            FetchError: If API fails
        """
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Get list of top story IDs
                logger.info("Fetching HN top story IDs...")
                resp = await client.get(f"{self.base_url}/topstories.json")
                resp.raise_for_status()

                story_ids = resp.json()
                logger.info(f"Got {len(story_ids)} total top story IDs")

                # Fetch extra to account for filtering
                story_ids_to_fetch = story_ids[: limit * 3]

                stories = []
                tasks = [
                    self._fetch_story(client, hn_id)
                    for hn_id in story_ids_to_fetch
                ]

                # Fetch in batches to avoid overwhelming the API
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    if isinstance(result, Exception):
                        logger.warning(f"Failed to fetch story: {result}")
                        continue
                    if result:
                        stories.append(result)
                    if len(stories) >= limit:
                        break

                logger.info(f"Fetched {len(stories)} valid HN stories")
                return stories[:limit]

        except Exception as e:
            raise FetchError(f"Hacker News fetch failed: {e}") from e

    async def _fetch_story(self, client: httpx.AsyncClient, hn_id: int) -> Optional[Story]:
        """Fetch a single HN story by ID.

        Args:
            client: httpx async client
            hn_id: HN story ID

        Returns:
            Story object or None if invalid/filtered

        Raises:
            Exception: Network or parsing errors (caught by caller)
        """
        try:
            resp = await client.get(
                f"{self.base_url}/item/{hn_id}.json",
                timeout=5
            )
            resp.raise_for_status()

            data = resp.json()

            # Filter: only stories (skip jobs, polls, ask HN if not technical)
            if data.get("type") != "story":
                return None

            # Filter: must have URL or text
            if not data.get("url") and not data.get("text"):
                return None

            title = data.get("title", "")
            if not title:
                return None

            # Determine URL
            url = data.get("url")
            if not url:
                # Self post on HN
                url = f"https://news.ycombinator.com/item?id={hn_id}"

            # Parse timestamps
            timestamp = data.get("time", 0)
            published_at = datetime.fromtimestamp(timestamp) if timestamp else datetime.utcnow()

            story = Story(
                id=f"hn:{hn_id}",
                title=title,
                url=url,
                source=NewsSource.HACKER_NEWS,
                content=data.get("text", "")[:1000],  # Truncate long text
                author=data.get("by", ""),
                published_at=published_at,
                metadata={
                    "score": data.get("score", 0),
                    "comments": data.get("descendants", 0),
                    "hn_id": hn_id,
                    "type": data.get("type"),
                }
            )

            return story

        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching HN story {hn_id}")
            return None
        except httpx.HTTPError as e:
            logger.warning(f"HTTP error fetching HN story {hn_id}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error parsing HN story {hn_id}: {e}")
            return None
