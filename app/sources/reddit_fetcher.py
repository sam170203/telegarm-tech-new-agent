"""
Reddit fetcher.
Uses PRAW (Python Reddit API Wrapper).
Fetches from multiple subreddits.
"""

from datetime import datetime
from typing import List, Optional
import praw

from app.models import Story, NewsSource
from app.sources.base import NewsSourceBase
from app.config.settings import settings
from app.utils.logger import setup_logger
from app.utils.errors import FetchError

logger = setup_logger(__name__)


class RedditFetcher(NewsSourceBase):
    """Fetch stories from multiple Reddit subreddits.
    
    Requires Reddit API credentials (set in .env):
    - REDDIT_CLIENT_ID
    - REDDIT_CLIENT_SECRET
    
    Free tier: 60 requests/minute (plenty for daily use)
    """

    source_type = NewsSource.REDDIT

    # Subreddits to fetch from, in order of priority
    subreddits = [
        "MachineLearning",
        "LocalLLaMA",
        "artificial",
        "singularity",
        "programming",
        "learnprogramming",
    ]

    def __init__(self):
        """Initialize Reddit API client.
        
        Raises:
            FetchError: If credentials missing or invalid
        """
        try:
            # Check for credentials
            client_id = getattr(settings, "reddit_client_id", None)
            client_secret = getattr(settings, "reddit_client_secret", None)

            if not client_id or not client_secret:
                logger.warning(
                    "Reddit API credentials not configured. "
                    "Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env"
                )
                self.reddit = None
                return

            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent="telegram-briefing-bot/1.0 (personal use)"
            )

            # Test authentication
            _ = self.reddit.user.me()
            logger.info("Reddit API authenticated successfully")

        except praw.exceptions.PrawException as e:
            logger.error(f"Reddit API authentication failed: {e}")
            self.reddit = None
        except Exception as e:
            logger.error(f"Reddit initialization error: {e}")
            self.reddit = None

    async def fetch(self, limit: int = 200) -> List[Story]:
        """Fetch stories from multiple subreddits.

        Args:
            limit: Total stories to fetch (distributed across subreddits)

        Returns:
            List of Story objects

        Raises:
            FetchError: If Reddit API fails or not authenticated
        """
        if not self.reddit:
            raise FetchError(
                "Reddit API not authenticated. "
                "Configure REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env"
            )

        try:
            stories = []
            per_subreddit = limit // len(self.subreddits) + 1

            for subreddit_name in self.subreddits:
                try:
                    logger.info(f"Fetching from r/{subreddit_name}...")
                    subreddit = self.reddit.subreddit(subreddit_name)

                    # Fetch from 'hot' feed (good balance of recency + engagement)
                    for post in subreddit.hot(limit=per_subreddit):
                        story = self._parse_post(post, subreddit_name)
                        if story:
                            stories.append(story)

                        if len(stories) >= limit:
                            return stories[:limit]

                except Exception as e:
                    logger.warning(f"Error fetching r/{subreddit_name}: {e}")
                    continue

            logger.info(f"Fetched {len(stories)} stories from {len(self.subreddits)} subreddits")
            return stories[:limit]

        except Exception as e:
            raise FetchError(f"Reddit fetch failed: {e}") from e

    def _parse_post(self, post, subreddit_name: str) -> Optional[Story]:
        """Parse a Reddit post to Story object.

        Args:
            post: praw.models.Submission object
            subreddit_name: Name of subreddit for tracking

        Returns:
            Story object or None if should be filtered
        """
        try:
            # Filter: skip deleted posts, stickies, archived
            if post.author is None or post.stickied or post.archived:
                return None

            # Filter: skip very low-scoring posts (likely spam)
            if post.score < 10:
                return None

            title = post.title
            if not title or len(title) < 5:
                return None

            # Determine URL
            if post.is_self:
                # Self post
                url = f"https://reddit.com{post.permalink}"
                content = post.selftext[:500]
            else:
                # Link post
                url = post.url
                content = ""

            # Parse timestamp
            published_at = datetime.fromtimestamp(post.created_utc)

            story = Story(
                id=f"reddit:{post.id}",
                title=title,
                url=url,
                source=NewsSource.REDDIT,
                content=content,
                author=str(post.author),
                published_at=published_at,
                metadata={
                    "score": post.score,
                    "comments": post.num_comments,
                    "subreddit": subreddit_name,
                    "upvote_ratio": post.upvote_ratio,
                    "reddit_id": post.id,
                }
            )

            return story

        except Exception as e:
            logger.warning(f"Error parsing Reddit post: {e}")
            return None
