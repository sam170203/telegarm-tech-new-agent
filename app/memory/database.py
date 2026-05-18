import sqlite3
from pathlib import Path
from contextlib import contextmanager
from app.config.settings import settings
from app.utils.logger import setup_logger
from app.utils.errors import DatabaseError

logger = setup_logger(__name__)


class Database:
    """SQLite connection manager."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.db_path
        self._ensure_path()
        self._init_schema()

    def _ensure_path(self):
        """Create database directory."""
        path = Path(self.db_path)
        path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise DatabaseError(f"Database operation failed: {e}") from e
        finally:
            conn.close()

    def _init_schema(self):
        """Initialize database schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Stories table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS stories (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    source TEXT NOT NULL,
                    content TEXT,
                    author TEXT,
                    published_at TIMESTAMP,
                    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Ranking scores table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS story_scores (
                    story_id TEXT PRIMARY KEY,
                    relevance_score REAL DEFAULT 0.0,
                    virality_score REAL DEFAULT 0.0,
                    depth_score REAL DEFAULT 0.0,
                    novelty_score REAL DEFAULT 0.0,
                    final_score REAL DEFAULT 0.0,
                    rank INTEGER,
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (story_id) REFERENCES stories(id)
                )
                """
            )

            # Summaries table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    story_id TEXT NOT NULL UNIQUE,
                    summary TEXT,
                    why_it_matters TEXT,
                    practical_implications TEXT,
                    tags JSON,
                    trend_context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (story_id) REFERENCES stories(id)
                )
                """
            )

            # User feedback table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    story_id TEXT NOT NULL,
                    reaction TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (story_id) REFERENCES stories(id)
                )
                """
            )

            # Briefing history table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS briefings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    story_count INTEGER,
                    message_id TEXT,
                    metadata JSON
                )
                """
            )

            # Source quality tracking
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS source_quality (
                    source TEXT PRIMARY KEY,
                    total_items INTEGER DEFAULT 0,
                    total_likes INTEGER DEFAULT 0,
                    total_dislikes INTEGER DEFAULT 0,
                    avg_engagement_score REAL DEFAULT 0.5,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Topic engagement tracking
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS topic_engagement (
                    topic TEXT PRIMARY KEY,
                    keyword_occurrences INTEGER DEFAULT 0,
                    positive_feedback INTEGER DEFAULT 0,
                    negative_feedback INTEGER DEFAULT 0,
                    engagement_score REAL DEFAULT 0.5,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Engagement metrics per story
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS engagement_metrics (
                    story_id TEXT PRIMARY KEY,
                    view_count INTEGER DEFAULT 0,
                    click_count INTEGER DEFAULT 0,
                    reaction_count INTEGER DEFAULT 0,
                    time_spent_seconds INTEGER DEFAULT 0,
                    engagement_score REAL DEFAULT 0.0,
                    FOREIGN KEY (story_id) REFERENCES stories(id)
                )
                """
            )

            # Indexes for common queries
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_stories_fetched_at
                ON stories(fetched_at DESC)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_stories_source
                ON stories(source)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_feedback_story_id
                ON feedback(story_id)
                """
            )

            conn.commit()
            logger.info(f"Database schema initialized at {self.db_path}")

    def execute(self, query: str, params: tuple = None):
        """Execute query with parameters."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()

    def execute_one(self, query: str, params: tuple = None):
        """Execute query, return single row."""
        results = self.execute(query, params)
        return results[0] if results else None

    def insert(self, table: str, data: dict):
        """Insert row into table."""
        keys = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        query = f"INSERT OR IGNORE INTO {table} ({keys}) VALUES ({placeholders})"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(data.values()))
            conn.commit()

    def update(self, table: str, data: dict, where: dict):
        """Update rows in table."""
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        where_clause = " AND ".join([f"{k} = ?" for k in where.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        values = list(data.values()) + list(where.values())
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
