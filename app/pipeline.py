"""End-to-end briefing pipeline: fetch -> rank -> summarize -> format -> send."""

from app.config.settings import settings
from app.memory.database import Database
from app.memory.dao import StoryDAO, BriefingDAO
from app.sources.manager import NewsManager
from app.ranking.manager import RankingManager
from app.summarization.summarizer import SummarizationManager
from app.summarization.telegram_formatter import TelegramFormatter
from app.telegram.client import TelegramClient
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


async def run_briefing(dry_run: bool = False) -> dict:
    """Run one full briefing cycle. Returns a stats dict."""
    logger.info("=" * 60)
    logger.info(f"BRIEFING RUN — dry_run={dry_run}")
    logger.info("=" * 60)

    db = Database(settings.db_path)
    story_dao = StoryDAO(db)
    briefing_dao = BriefingDAO(db)

    # 1. Fetch news from all enabled sources (saves to DB)
    news_manager = NewsManager(story_dao)
    fetch_stats = await news_manager.fetch_all()

    # 2. Pull recent stories (last 24h) as ranking candidates
    candidates = story_dao.get_recent_stories(hours=24, limit=300)
    logger.info(f"Ranking {len(candidates)} candidate stories")
    if not candidates:
        logger.error("No candidate stories to rank — aborting briefing")
        return {"status": "no_candidates", **fetch_stats}

    # 3. Rank
    ranker = RankingManager()
    ranked = ranker.rank_stories(candidates)
    top_n = ranked[: settings.items_per_briefing]
    logger.info(f"Selected top {len(top_n)} stories")

    # 4. Summarize with Claude
    summarizer = SummarizationManager()
    summaries = await summarizer.summarize_stories(top_n)
    logger.info(f"Summarized {len(summaries)} stories")

    # 5. Format for Telegram
    formatter = TelegramFormatter()
    html = formatter.format_briefing(summaries)
    logger.info(f"Formatted briefing: {len(html)} chars")

    # 6. Send (or print)
    message_ids: list[int] = []
    if dry_run:
        logger.info("DRY RUN — printing briefing instead of sending")
        print("\n" + "=" * 60)
        print("BRIEFING PREVIEW (dry run, not sent to Telegram)")
        print("=" * 60)
        print(html)
        print("=" * 60 + "\n")
    else:
        client = TelegramClient()
        message_ids = await client.send_briefing(html)
        if not message_ids:
            logger.error("Telegram send failed entirely")
            return {"status": "send_failed", "fetch": fetch_stats, "ranked": len(top_n)}

    # 7. Record the briefing
    story_ids = [s.story_id for s in summaries]
    if not dry_run and message_ids:
        briefing_dao.save_briefing(story_ids, message_id=str(message_ids[0]))

    logger.info("=" * 60)
    logger.info(f"BRIEFING COMPLETE — sent {len(message_ids)} message(s)")
    logger.info("=" * 60)

    return {
        "status": "ok",
        "fetch": fetch_stats,
        "ranked": len(top_n),
        "summarized": len(summaries),
        "messages_sent": len(message_ids),
        "story_ids": story_ids,
    }
