# PHASE 1.2: NEWS FETCHERS
## Implementation Guide

**Effort**: ~2-3 hours
**Complexity**: Medium (async HTTP, data parsing)
**Output**: Fetchers for HN, Reddit, deduplication

---

## Architecture

### 1. Base Class

All sources inherit from `NewsSource`:

```python
# app/sources/base.py

from abc import ABC, abstractmethod
from app.models import Story, NewsSource

class NewsSourceBase(ABC):
    """Abstract base for news sources."""

    source_type: NewsSource

    @abstractmethod
    async def fetch(self, limit: int = 50) -> List[Story]:
        """Fetch stories from source.
        
        Returns:
            List of Story objects
        """
        pass

    async def fetch_and_save(self, dao, limit: int = 50) -> int:
        """Fetch and save, dedup by ID.
        
        Returns:
            Count of new stories saved
        """
        stories = await self.fetch(limit)
        count = 0
        for story in stories:
            if not dao.story_exists(story.id):
                dao.save_story(story)
                count += 1
        return count
```

### 2. Hacker News Fetcher

```python
# app/sources/hacker_news.py

import httpx
from app.models import Story, NewsSource

class HackerNewsFetcher(NewsSourceBase):
    source_type = NewsSource.HACKER_NEWS
    base_url = "https://hacker-news.firebaseio.com/v0"

    async def fetch(self, limit: int = 50) -> List[Story]:
        """Fetch top stories from HN."""
        async with httpx.AsyncClient(timeout=10) as client:
            # Get top story IDs
            resp = await client.get(f"{self.base_url}/topstories.json")
            story_ids = resp.json()[:limit * 2]  # Fetch extra for filtering

            stories = []
            for hn_id in story_ids:
                story = await self._fetch_story(client, hn_id)
                if story:
                    stories.append(story)
                if len(stories) >= limit:
                    break
            return stories

    async def _fetch_story(self, client, hn_id: int) -> Optional[Story]:
        """Fetch single HN story."""
        try:
            resp = await client.get(f"{self.base_url}/item/{hn_id}.json")
            data = resp.json()

            # Filter: comments only (skip jobs, polls)
            if data.get("type") != "story":
                return None

            return Story(
                id=f"hn:{hn_id}",
                title=data.get("title", ""),
                url=data.get("url", f"https://news.ycombinator.com/item?id={hn_id}"),
                source=NewsSource.HACKER_NEWS,
                content=data.get("title", ""),
                author=data.get("by", ""),
                published_at=datetime.fromtimestamp(data.get("time", 0)),
                metadata={
                    "score": data.get("score", 0),
                    "comments": data.get("descendants", 0),
                    "hn_id": hn_id,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to fetch HN story {hn_id}: {e}")
            return None
```

### 3. Reddit Fetcher

```python
# app/sources/reddit_fetcher.py

import praw
from app.models import Story, NewsSource

class RedditFetcher(NewsSourceBase):
    source_type = NewsSource.REDDIT

    def __init__(self):
        self.reddit = praw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent="briefing-bot/1.0"
        )
        self.subreddits = [
            "MachineLearning",
            "LocalLLaMA",
            "artificial",
            "singularity",
            "programming",
        ]

    async def fetch(self, limit: int = 200) -> List[Story]:
        """Fetch from multiple subreddits."""
        stories = []
        per_sub = limit // len(self.subreddits)

        for subreddit_name in self.subreddits:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                for post in subreddit.hot(limit=per_sub * 2):
                    story = self._parse_post(post)
                    if story:
                        stories.append(story)
                    if len(stories) >= limit:
                        return stories
            except Exception as e:
                logger.warning(f"Reddit fetch failed for r/{subreddit_name}: {e}")

        return stories

    def _parse_post(self, post) -> Optional[Story]:
        """Parse Reddit post to Story."""
        # Skip stickies, deleted, archived
        if post.stickied or post.author is None or post.archived:
            return None

        url = post.url
        if post.is_self:
            url = f"https://reddit.com{post.permalink}"

        return Story(
            id=f"reddit:{post.id}",
            title=post.title,
            url=url,
            source=NewsSource.REDDIT,
            content=post.selftext[:500] if post.is_self else "",
            author=str(post.author),
            published_at=datetime.fromtimestamp(post.created_utc),
            metadata={
                "score": post.score,
                "comments": post.num_comments,
                "subreddit": post.subreddit.display_name,
            }
        )
```

### 4. Source Manager

```python
# app/sources/manager.py

class NewsManager:
    """Orchestrate all news sources."""

    def __init__(self, dao):
        self.dao = dao
        self.sources = {
            NewsSource.HACKER_NEWS: HackerNewsFetcher(),
            NewsSource.REDDIT: RedditFetcher(),
            # Add GitHub, ArXiv in Phase 3
        }

    async def fetch_all(self) -> dict:
        """Fetch from all sources in parallel."""
        results = {}
        tasks = []

        for source_type, fetcher in self.sources.items():
            limit = getattr(settings, f"{source_type.value}_fetch_limit")
            tasks.append(fetcher.fetch_and_save(self.dao, limit))

        counts = await asyncio.gather(*tasks, return_exceptions=True)

        for (source_type, _), count in zip(self.sources.items(), counts):
            if isinstance(count, Exception):
                logger.error(f"Fetch failed for {source_type}: {count}")
                results[source_type] = 0
            else:
                results[source_type] = count

        return results
```

### 5. Deduplication

```python
# app/sources/deduplicator.py

from difflib import SequenceMatcher

class Deduplicator:
    """Find and merge duplicate stories."""

    @staticmethod
    def similarity(a: str, b: str) -> float:
        """Calculate title similarity (0.0-1.0)."""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    @staticmethod
    def are_duplicates(story1: Story, story2: Story, threshold=0.85) -> bool:
        """Check if two stories are duplicates."""
        # Exact URL match
        if story1.url == story2.url and story1.url:
            return True

        # Similar title
        sim = Deduplicator.similarity(story1.title, story2.title)
        return sim > threshold

    @staticmethod
    def merge_duplicates(stories: List[Story]) -> List[Story]:
        """Merge duplicate stories, keeping highest-scored version."""
        merged = []
        used_ids = set()

        for story in stories:
            if story.id in used_ids:
                continue

            duplicates = [story]
            for other in stories:
                if other.id != story.id and Deduplicator.are_duplicates(story, other):
                    duplicates.append(other)
                    used_ids.add(other.id)

            # Keep story with highest metadata score
            best = max(duplicates, key=lambda s: s.metadata.get("score", 0))
            merged.append(best)
            used_ids.add(best.id)

        return merged
```

---

## Testing

```python
# tests/test_sources.py

@pytest.mark.asyncio
async def test_hacker_news_fetch():
    fetcher = HackerNewsFetcher()
    stories = await fetcher.fetch(limit=5)
    assert len(stories) <= 5
    assert all(isinstance(s, Story) for s in stories)
    assert all(s.source == NewsSource.HACKER_NEWS for s in stories)

@pytest.mark.asyncio
async def test_deduplication():
    story1 = Story(id="1", title="vLLM wins", url="example.com", ...)
    story2 = Story(id="2", title="vLLM Wins", url="example.com", ...)
    assert Deduplicator.are_duplicates(story1, story2)

@pytest.mark.asyncio
async def test_news_manager():
    db = Database(":memory:")
    dao = StoryDAO(db)
    manager = NewsManager(dao)
    
    results = await manager.fetch_all()
    assert NewsSource.HACKER_NEWS in results
    assert isinstance(results[NewsSource.HACKER_NEWS], int)
```

---

## Integration Checklist

- [ ] Add to `requirements.txt`: praw (Reddit library)
- [ ] Update `.env.example` with Reddit client IDs (optional)
- [ ] Add to `app/sources/__init__.py`: Import fetchers
- [ ] Create `tests/test_sources.py` with async tests
- [ ] Update `main.py` to test fetch: `await manager.fetch_all()`
- [ ] Verify HN fetcher works (public API, no auth)
- [ ] Add Reddit credentials to `.env` for Phase 2 testing

---

## Success Criteria

Run:
```bash
python3 -c "
import asyncio
from app.sources.hacker_news import HackerNewsFetcher

async def test():
    fetcher = HackerNewsFetcher()
    stories = await fetcher.fetch(limit=5)
    print(f'✓ Fetched {len(stories)} HN stories')
    print(f'  Sample: {stories[0].title[:60]}...')

asyncio.run(test())
"
```

Expected: Prints 5 HN stories with titles.

---

## Next Phase (1.3)

Once Phase 1.2 is done:
- 100+ stories fetched from HN + Reddit
- All stored in database
- Ready for ranking algorithm
