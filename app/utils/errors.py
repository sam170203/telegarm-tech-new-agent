class BriefingError(Exception):
    """Base exception for briefing agent."""

    pass


class FetchError(BriefingError):
    """Error fetching news from source."""

    pass


class RankingError(BriefingError):
    """Error in ranking engine."""

    pass


class SummarizeError(BriefingError):
    """Error in summarization."""

    pass


class TelegramError(BriefingError):
    """Error sending telegram message."""

    pass


class DatabaseError(BriefingError):
    """Database operation error."""

    pass
