"""Test database setup and basic operations."""
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.memory.database import Database
from app.memory.dao import StoryDAO, FeedbackDAO, BriefingDAO
from app.models import Story, NewsSource, FeedbackType
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def test_database_init():
    """Test database initialization."""
    db_path = "./test_briefing.db"
    db = Database(db_path)
    logger.info(f"✓ Database initialized at {db_path}")
    return db


def test_story_dao(db: Database):
    """Test story CRUD operations."""
    story_dao = StoryDAO(db)

    # Create test story
    story = Story(
        id="hn:12345",
        title="vLLM Reaches 1M Tokens/sec",
        url="https://example.com/story",
        source=NewsSource.HACKER_NEWS,
        content="A breakthrough in LLM inference speed...",
        author="TestUser",
        published_at=datetime.utcnow(),
    )

    # Save story
    saved = story_dao.save_story(story)
    logger.info(f"✓ Story saved: {saved}")

    # Retrieve story
    retrieved = story_dao.get_story_by_id("hn:12345")
    assert retrieved is not None
    assert retrieved.title == story.title
    logger.info(f"✓ Story retrieved: {retrieved.title}")

    # Check existence
    exists = story_dao.story_exists("hn:12345")
    assert exists
    logger.info(f"✓ Story existence check passed")

    return story


def test_feedback_dao(db: Database):
    """Test feedback operations."""
    feedback_dao = FeedbackDAO(db)

    # Save feedback
    feedback_dao.save_feedback("hn:12345", FeedbackType.LIKE)
    feedback_dao.save_feedback("hn:12345", FeedbackType.LIKE)
    feedback_dao.save_feedback("hn:12345", FeedbackType.DISLIKE)

    # Get feedback counts
    counts = feedback_dao.get_feedback_count("hn:12345")
    logger.info(f"✓ Feedback counts: {counts}")
    assert counts["like"] == 2
    assert counts["dislike"] == 1

    # Get liked stories
    liked = feedback_dao.get_stories_by_feedback(FeedbackType.LIKE, limit=10)
    logger.info(f"✓ Liked stories: {liked}")
    assert "hn:12345" in liked


def test_briefing_dao(db: Database):
    """Test briefing tracking."""
    briefing_dao = BriefingDAO(db)

    story_ids = ["hn:12345", "hn:67890", "reddit:abc123"]
    briefing_id = briefing_dao.save_briefing(story_ids, message_id="tg:123456789")

    last_briefing = briefing_dao.get_last_briefing()
    logger.info(f"✓ Briefing saved: {last_briefing}")
    assert last_briefing["story_count"] == 3


def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("TESTING DATABASE LAYER")
    logger.info("=" * 60)

    try:
        db = test_database_init()
        story = test_story_dao(db)
        test_feedback_dao(db)
        test_briefing_dao(db)

        logger.info("=" * 60)
        logger.info("✓ ALL TESTS PASSED")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
