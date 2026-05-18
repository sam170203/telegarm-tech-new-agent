from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class NewsSource(Enum):
    """Supported news sources."""

    HACKER_NEWS = "hacker_news"
    REDDIT = "reddit"
    GITHUB = "github"
    ARXIV = "arxiv"
    RSS = "rss"


class FeedbackType(Enum):
    """User feedback reactions."""

    LIKE = "like"
    DISLIKE = "dislike"
    BOOKMARK = "bookmark"


@dataclass
class Story:
    """Represents a news story."""

    id: str  # Unique identifier (source:id format)
    title: str
    url: str
    source: NewsSource
    content: str  # Summary or excerpt
    author: str = ""
    published_at: datetime = field(default_factory=datetime.utcnow)
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)  # Source-specific data

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, Story):
            return False
        return self.id == other.id


@dataclass
class RankedStory(Story):
    """Story with ranking scores."""

    relevance_score: float = 0.0
    virality_score: float = 0.0
    depth_score: float = 0.0
    novelty_score: float = 0.0
    final_score: float = 0.0
    rank: int = 0

    @property
    def scores_dict(self) -> dict:
        return {
            "relevance": self.relevance_score,
            "virality": self.virality_score,
            "depth": self.depth_score,
            "novelty": self.novelty_score,
            "final": self.final_score,
        }


@dataclass
class BriefingSummary:
    """LLM-generated summary of a story."""

    story_id: str
    summary: str  # 2-3 line concise summary
    why_it_matters: str  # Impact explanation
    practical_implications: str  # What devs should do
    tags: list[str] = field(default_factory=list)
    trend_context: str = ""  # If part of a trend


@dataclass
class TelegramMessage:
    """Telegram briefing message."""

    header: str
    sections: dict  # name -> content
    items: list[dict]  # Formatted story items
    footer: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_markdown(self) -> str:
        """Render as Telegram markdown."""
        # Implementation in formatter.py
        pass
