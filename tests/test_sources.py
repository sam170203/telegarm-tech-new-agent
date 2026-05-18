"""
Tests for news sources and fetchers.
Run with: pytest tests/test_sources.py -v
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from app.models import Story, NewsSource
from app.sources.base import NewsSourceBase
from app.sources.hacker_news import HackerNewsFetcher
from app.sources.reddit_fetcher import RedditFetcher
from app.sources.deduplicator import Deduplicator
from app.sources.manager import NewsManager
from app.memory.dao import StoryDAO
from app.memory.database import Database


class TestHackerNewsFetcher:
    """Test Hacker News fetcher."""

    @pytest.mark.asyncio
    async def test_fetch_returns_stories(self):
        """Test that fetch returns Story objects."""
        fetcher = HackerNewsFetcher()

        # Test with small limit
        stories = await fetcher.fetch(limit=3)

        assert isinstance(stories, list)
        assert len(stories) <= 3
        assert all(isinstance(s, Story) for s in stories)

    @pytest.mark.asyncio
    async def test_all_stories_are_hn_source(self):
        """Test that all fetched stories are marked as HN source."""
        fetcher = HackerNewsFetcher()
        stories = await fetcher.fetch(limit=5)

        assert all(s.source == NewsSource.HACKER_NEWS for s in stories)

    @pytest.mark.asyncio
    async def test_stories_have_required_fields(self):
        """Test that stories have all required fields."""
        fetcher = HackerNewsFetcher()
        stories = await fetcher.fetch(limit=3)

        for story in stories:
            assert story.id
            assert story.title
            assert story.url
            assert story.source
            assert story.metadata.get("hn_id")
            assert "score" in story.metadata
            assert "comments" in story.metadata

    @pytest.mark.asyncio
    async def test_story_id_format(self):
        """Test that story IDs are in correct format."""
        fetcher = HackerNewsFetcher()
        stories = await fetcher.fetch(limit=3)

        for story in stories:
            assert story.id.startswith("hn:")

    @pytest.mark.asyncio
    async def test_fetch_and_save(self):
        """Test fetch_and_save with database."""
        db = Database(":memory:")
        dao = StoryDAO(db)

        fetcher = HackerNewsFetcher()
        saved_count = await fetcher.fetch_and_save(dao, limit=5)

        assert saved_count >= 0
        assert isinstance(saved_count, int)

    @pytest.mark.asyncio
    async def test_deduplication_on_fetch_and_save(self):
        """Test that duplicate stories aren't saved twice."""
        db = Database(":memory:")
        dao = StoryDAO(db)

        fetcher = HackerNewsFetcher()

        # First fetch
        count1 = await fetcher.fetch_and_save(dao, limit=3)
        total1 = len(db.execute("SELECT * FROM stories"))

        # Second fetch (should not re-save same stories)
        count2 = await fetcher.fetch_and_save(dao, limit=3)
        total2 = len(db.execute("SELECT * FROM stories"))

        assert total2 == total1  # No new stories added


class TestDeduplicator:
    """Test deduplication logic."""

    def test_title_similarity(self):
        """Test title similarity calculation."""
        # Identical titles
        assert Deduplicator.title_similarity("vLLM wins", "vLLM wins") == 1.0

        # Very similar
        sim = Deduplicator.title_similarity("vLLM wins", "vLLM Win")
        assert 0.85 < sim < 1.0

        # Different
        sim = Deduplicator.title_similarity("vLLM wins", "different title")
        assert sim < 0.5

        # Empty
        assert Deduplicator.title_similarity("", "test") == 0.0

    def test_url_normalization(self):
        """Test URL normalization."""
        # Same URLs, different schemes
        url1 = "https://www.example.com/article/test"
        url2 = "http://example.com/article/test"
        assert Deduplicator.normalize_url(url1) == Deduplicator.normalize_url(url2)

        # Same URL with trailing slash
        url3 = "https://example.com/article/"
        url4 = "https://example.com/article"
        assert Deduplicator.normalize_url(url3) == Deduplicator.normalize_url(url4)

    def test_are_duplicates_exact_url(self):
        """Test duplicate detection by exact URL."""
        story1 = Story(
            id="1",
            title="Test",
            url="https://example.com/test",
            source=NewsSource.HACKER_NEWS,
            content="",
        )
        story2 = Story(
            id="2",
            title="Different",
            url="https://example.com/test",
            source=NewsSource.REDDIT,
            content="",
        )

        assert Deduplicator.are_duplicates(story1, story2)

    def test_are_duplicates_title_similarity(self):
        """Test duplicate detection by title similarity."""
        story1 = Story(
            id="1",
            title="vLLM Reaches 1M Tokens Per Second",
            url="https://example.com/1",
            source=NewsSource.HACKER_NEWS,
            content="",
        )
        story2 = Story(
            id="2",
            title="vLLM reaches 1M tokens per second",
            url="https://example.com/2",
            source=NewsSource.REDDIT,
            content="",
        )

        assert Deduplicator.are_duplicates(story1, story2, title_threshold=0.9)

    def test_are_duplicates_false(self):
        """Test that different stories aren't marked as duplicates."""
        story1 = Story(
            id="1",
            title="vLLM Wins",
            url="https://example.com/1",
            source=NewsSource.HACKER_NEWS,
            content="",
        )
        story2 = Story(
            id="2",
            title="TensorFlow Loses",
            url="https://example.com/2",
            source=NewsSource.REDDIT,
            content="",
        )

        assert not Deduplicator.are_duplicates(story1, story2)

    def test_merge_stories(self):
        """Test merging duplicate stories."""
        stories = [
            Story(
                id="hn:1",
                title="vLLM wins",
                url="https://example.com/story",
                source=NewsSource.HACKER_NEWS,
                content="",
                metadata={"score": 100},
            ),
            Story(
                id="reddit:1",
                title="vLLM Wins",
                url="https://example.com/story",
                source=NewsSource.REDDIT,
                content="",
                metadata={"score": 50},
            ),
            Story(
                id="hn:2",
                title="Different story",
                url="https://other.com/story",
                source=NewsSource.HACKER_NEWS,
                content="",
            ),
        ]

        merged = Deduplicator.merge_stories(stories)

        # Should have 2 unique stories (HN preferred over Reddit)
        assert len(merged) == 2
        assert merged[0].id == "hn:1"  # HN kept due to priority

    def test_merge_stories_preserves_unique(self):
        """Test that unique stories are preserved during merge."""
        stories = [
            Story(
                id="1",
                title="Story A - Unique First",
                url="https://a.com",
                source=NewsSource.HACKER_NEWS,
                content="",
            ),
            Story(
                id="2",
                title="Story B - Very Different Topic",
                url="https://b.com",
                source=NewsSource.REDDIT,
                content="",
            ),
        ]

        merged = Deduplicator.merge_stories(stories)

        assert len(merged) == 2
        ids = {s.id for s in merged}
        assert "1" in ids
        assert "2" in ids


class TestNewsManager:
    """Test news manager orchestration."""

    @pytest.mark.asyncio
    async def test_fetch_all_basic(self):
        """Test that fetch_all returns stats."""
        db = Database(":memory:")
        dao = StoryDAO(db)
        manager = NewsManager(dao)

        results = await manager.fetch_all()

        assert isinstance(results, dict)
        assert "hacker_news" in results
        assert "total_fetched" in results
        assert "duplicates_removed" in results
        assert "new_stories_saved" in results

    @pytest.mark.asyncio
    async def test_fetch_all_saves_to_db(self):
        """Test that fetch_all actually saves stories."""
        db = Database(":memory:")
        dao = StoryDAO(db)
        manager = NewsManager(dao)

        await manager.fetch_all()

        # Check that stories were saved
        rows = db.execute("SELECT COUNT(*) as count FROM stories")
        count = rows[0][0]

        assert count > 0

    def test_get_enabled_sources(self):
        """Test getting list of enabled sources."""
        db = Database(":memory:")
        dao = StoryDAO(db)
        manager = NewsManager(dao)

        sources = manager.get_enabled_sources()

        assert isinstance(sources, list)
        assert "hacker_news" in sources
        assert "reddit" in sources


class TestRedditFetcher:
    """Test Reddit fetcher (mocked to avoid API calls)."""

    def test_reddit_fetcher_init_without_credentials(self):
        """Test that Reddit fetcher handles missing credentials gracefully."""
        # This will initialize but reddit client will be None
        fetcher = RedditFetcher()
        # Should not raise an exception
        assert fetcher is not None

    def test_reddit_subreddits(self):
        """Test that correct subreddits are configured."""
        fetcher = RedditFetcher()
        assert "MachineLearning" in fetcher.subreddits
        assert "LocalLLaMA" in fetcher.subreddits
        assert "artificial" in fetcher.subreddits

    def test_parse_post_filters_deleted(self):
        """Test that deleted posts are filtered."""
        fetcher = RedditFetcher()

        # Create mock deleted post
        mock_post = Mock()
        mock_post.author = None
        mock_post.stickied = False
        mock_post.archived = False

        result = fetcher._parse_post(mock_post, "test")
        assert result is None

    def test_parse_post_filters_low_score(self):
        """Test that low-scoring posts are filtered."""
        fetcher = RedditFetcher()

        # Create mock low-score post
        mock_post = Mock()
        mock_post.author = Mock()
        mock_post.stickied = False
        mock_post.archived = False
        mock_post.score = 5  # Too low
        mock_post.title = "Test"

        result = fetcher._parse_post(mock_post, "test")
        assert result is None


# Integration tests (real API calls)

@pytest.mark.asyncio
@pytest.mark.integration
async def test_hn_real_fetch():
    """Real test against HN API. Mark with @pytest.mark.integration to skip normally."""
    fetcher = HackerNewsFetcher()
    stories = await fetcher.fetch(limit=5)

    assert len(stories) > 0
    assert all(isinstance(s, Story) for s in stories)

    print(f"\nFetched {len(stories)} HN stories:")
    for story in stories[:3]:
        print(f"  - {story.title}")


# Run with: pytest tests/test_sources.py -v
# Run integration tests: pytest tests/test_sources.py -v -m integration
