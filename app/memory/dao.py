import json
from datetime import datetime, timedelta
from typing import Optional, List
from app.models import Story, NewsSource, RankedStory, FeedbackType
from app.memory.database import Database
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class StoryDAO:
    """Data Access Object for Story operations."""

    def __init__(self, db: Database):
        self.db = db

    def save_story(self, story: Story) -> bool:
        """Save a story to database."""
        data = {
            "id": story.id,
            "title": story.title,
            "url": story.url,
            "source": story.source.value,
            "content": story.content,
            "author": story.author,
            "published_at": story.published_at.isoformat() if story.published_at else None,
            "fetched_at": story.fetched_at.isoformat() if story.fetched_at else None,
            "metadata": json.dumps(story.metadata) if story.metadata else None,
        }
        try:
            self.db.insert("stories", data)
            return True
        except Exception as e:
            logger.error(f"Failed to save story {story.id}: {e}")
            return False

    def save_stories(self, stories: List[Story]) -> int:
        """Save multiple stories. Returns count of successful saves."""
        count = 0
        for story in stories:
            if self.save_story(story):
                count += 1
        return count

    def get_story_by_id(self, story_id: str) -> Optional[Story]:
        """Retrieve a story by ID."""
        row = self.db.execute_one(
            "SELECT * FROM stories WHERE id = ?", (story_id,)
        )
        if not row:
            return None
        return self._row_to_story(dict(row))

    def get_stories_by_source(self, source: NewsSource, limit: int = 100) -> List[Story]:
        """Get stories from a specific source."""
        rows = self.db.execute(
            """
            SELECT * FROM stories 
            WHERE source = ? 
            ORDER BY fetched_at DESC 
            LIMIT ?
            """,
            (source.value, limit),
        )
        return [self._row_to_story(dict(row)) for row in rows]

    def get_recent_stories(self, hours: int = 24, limit: int = 100) -> List[Story]:
        """Get stories fetched in last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        rows = self.db.execute(
            """
            SELECT * FROM stories 
            WHERE fetched_at > ? 
            ORDER BY fetched_at DESC 
            LIMIT ?
            """,
            (cutoff.isoformat(), limit),
        )
        return [self._row_to_story(dict(row)) for row in rows]

    def story_exists(self, story_id: str) -> bool:
        """Check if story already in database."""
        row = self.db.execute_one(
            "SELECT 1 FROM stories WHERE id = ?", (story_id,)
        )
        return row is not None

    def get_stories_in_briefing(self, briefing_id: int) -> List[Story]:
        """Get all stories sent in a specific briefing."""
        # We'll track this in briefing_stories table (to be added)
        pass

    @staticmethod
    def _row_to_story(row: dict) -> Story:
        """Convert database row to Story object."""
        return Story(
            id=row["id"],
            title=row["title"],
            url=row["url"],
            source=NewsSource(row["source"]),
            content=row["content"],
            author=row["author"],
            published_at=datetime.fromisoformat(row["published_at"])
            if row.get("published_at")
            else None,
            fetched_at=datetime.fromisoformat(row["fetched_at"])
            if row.get("fetched_at")
            else None,
            metadata=json.loads(row["metadata"]) if row.get("metadata") else {},
        )


class ScoreDAO:
    """Data Access Object for story scores."""

    def __init__(self, db: Database):
        self.db = db

    def save_scores(self, ranked_story: RankedStory) -> bool:
        """Save ranking scores for a story."""
        data = {
            "story_id": ranked_story.id,
            "relevance_score": ranked_story.relevance_score,
            "virality_score": ranked_story.virality_score,
            "depth_score": ranked_story.depth_score,
            "novelty_score": ranked_story.novelty_score,
            "final_score": ranked_story.final_score,
            "rank": ranked_story.rank,
        }
        try:
            self.db.insert("story_scores", data)
            return True
        except Exception as e:
            logger.error(f"Failed to save scores for {ranked_story.id}: {e}")
            return False

    def get_scores(self, story_id: str) -> Optional[dict]:
        """Get scores for a story."""
        row = self.db.execute_one(
            "SELECT * FROM story_scores WHERE story_id = ?", (story_id,)
        )
        return dict(row) if row else None

    def get_top_scored_stories(self, limit: int = 50) -> List[dict]:
        """Get top-scored stories."""
        rows = self.db.execute(
            """
            SELECT * FROM story_scores 
            ORDER BY final_score DESC, rank ASC 
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in rows]


class FeedbackDAO:
    """Data Access Object for user feedback."""

    def __init__(self, db: Database):
        self.db = db

    def save_feedback(
        self, story_id: str, reaction: FeedbackType
    ) -> bool:
        """Save user feedback on a story."""
        data = {
            "story_id": story_id,
            "reaction": reaction.value,
        }
        try:
            self.db.insert("feedback", data)
            return True
        except Exception as e:
            logger.error(f"Failed to save feedback for {story_id}: {e}")
            return False

    def get_feedback_count(self, story_id: str) -> dict:
        """Get feedback counts for a story."""
        rows = self.db.execute(
            """
            SELECT reaction, COUNT(*) as count 
            FROM feedback 
            WHERE story_id = ? 
            GROUP BY reaction
            """,
            (story_id,),
        )
        result = {"like": 0, "dislike": 0, "bookmark": 0}
        for row in rows:
            result[row[0]] = row[1]
        return result

    def get_stories_by_feedback(self, reaction: FeedbackType, limit: int = 20) -> List[str]:
        """Get story IDs with a specific feedback type."""
        rows = self.db.execute(
            """
            SELECT DISTINCT story_id 
            FROM feedback 
            WHERE reaction = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
            """,
            (reaction.value, limit),
        )
        return [row[0] for row in rows]


class SourceQualityDAO:
    """Track quality of each news source."""

    def __init__(self, db: Database):
        self.db = db

    def init_source(self, source: NewsSource):
        """Initialize tracking for a source."""
        data = {
            "source": source.value,
            "total_items": 0,
            "total_likes": 0,
            "total_dislikes": 0,
        }
        self.db.insert("source_quality", data)

    def update_quality_score(self, source: NewsSource, like: bool):
        """Update quality score based on feedback."""
        field = "total_likes" if like else "total_dislikes"
        self.db.execute(
            f"""
            UPDATE source_quality 
            SET {field} = {field} + 1 
            WHERE source = ?
            """,
            (source.value,),
        )
        self._recalculate_score(source)

    def get_quality_score(self, source: NewsSource) -> float:
        """Get quality score for a source (0.0-1.0)."""
        row = self.db.execute_one(
            "SELECT * FROM source_quality WHERE source = ?", (source.value,)
        )
        if not row:
            return 0.5
        total = row["total_likes"] + row["total_dislikes"]
        if total == 0:
            return 0.5
        return row["total_likes"] / total

    def _recalculate_score(self, source: NewsSource):
        """Recalculate average engagement score."""
        row = self.db.execute_one(
            "SELECT * FROM source_quality WHERE source = ?", (source.value,)
        )
        if row:
            total = row["total_likes"] + row["total_dislikes"]
            if total > 0:
                score = row["total_likes"] / total
                self.db.update(
                    "source_quality",
                    {"avg_engagement_score": score},
                    {"source": source.value},
                )


class TopicEngagementDAO:
    """Track topic engagement from feedback."""

    def __init__(self, db: Database):
        self.db = db

    def track_topic_interaction(self, topic: str, liked: bool):
        """Track feedback on a topic."""
        row = self.db.execute_one(
            "SELECT * FROM topic_engagement WHERE topic = ?", (topic,)
        )

        if not row:
            # Initialize
            data = {
                "topic": topic,
                "keyword_occurrences": 1,
                "positive_feedback": 1 if liked else 0,
                "negative_feedback": 0 if liked else 1,
            }
            self.db.insert("topic_engagement", data)
        else:
            # Update
            new_pos = row["positive_feedback"] + (1 if liked else 0)
            new_neg = row["negative_feedback"] + (0 if liked else 1)
            score = new_pos / (new_pos + new_neg) if (new_pos + new_neg) > 0 else 0.5
            self.db.update(
                "topic_engagement",
                {
                    "positive_feedback": new_pos,
                    "negative_feedback": new_neg,
                    "engagement_score": score,
                },
                {"topic": topic},
            )

    def get_topic_score(self, topic: str) -> float:
        """Get engagement score for topic (0.0-1.0)."""
        row = self.db.execute_one(
            "SELECT engagement_score FROM topic_engagement WHERE topic = ?",
            (topic,),
        )
        return row["engagement_score"] if row else 0.5

    def get_top_topics(self, limit: int = 10) -> List[tuple]:
        """Get topics with highest engagement."""
        rows = self.db.execute(
            """
            SELECT topic, engagement_score 
            FROM topic_engagement 
            ORDER BY engagement_score DESC 
            LIMIT ?
            """,
            (limit,),
        )
        return [(row[0], row[1]) for row in rows]


class BriefingDAO:
    """Track briefing history."""

    def __init__(self, db: Database):
        self.db = db

    def save_briefing(self, story_ids: List[str], message_id: str = None) -> int:
        """Save briefing record. Returns briefing_id."""
        data = {
            "story_count": len(story_ids),
            "message_id": message_id,
            "metadata": json.dumps({"story_ids": story_ids}),
        }
        self.db.insert("briefings", data)
        row = self.db.execute_one(
            "SELECT id FROM briefings WHERE message_id = ? ORDER BY id DESC",
            (message_id,),
        )
        return row[0] if row else None

    def get_last_briefing(self) -> Optional[dict]:
        """Get most recent briefing."""
        row = self.db.execute_one(
            "SELECT * FROM briefings ORDER BY sent_at DESC LIMIT 1"
        )
        return dict(row) if row else None
