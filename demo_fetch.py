#!/usr/bin/env python3
"""
Demonstration script for Phase 1.2: News Fetchers
Shows the fetching, deduplication, and database persistence in action.

Run with: python3 demo_fetch.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from app.memory.database import Database
from app.memory.dao import StoryDAO
from app.sources.manager import NewsManager
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


async def main():
    """Run the demo."""
    print("\n" + "=" * 70)
    print("TELEGRAM BRIEFING AGENT - PHASE 1.2 DEMO")
    print("News Fetchers + Deduplication + Database Persistence")
    print("=" * 70 + "\n")

    # Initialize database
    db_path = "./data/briefing_demo.db"
    print(f"[*] Initializing database at {db_path}")
    db = Database(db_path)
    dao = StoryDAO(db)
    print("    ✓ Database ready\n")

    # Create news manager
    print("[*] Creating news manager")
    manager = NewsManager(dao)
    enabled = manager.get_enabled_sources()
    print(f"    ✓ Enabled sources: {', '.join(enabled)}\n")

    # Fetch from all sources
    print("[*] Fetching news from all sources (this takes ~30 seconds)...")
    print("    HN: 50 stories")
    print("    Reddit: 200 stories (from 6 subreddits)")
    print()

    stats = await manager.fetch_all()

    # Display results
    print("\n" + "=" * 70)
    print("FETCH RESULTS")
    print("=" * 70)
    print(f"Hacker News:       {stats['hacker_news']} stories")
    print(f"Reddit:            {stats['reddit']} stories")
    print(f"Total Fetched:     {stats['total_fetched']} stories")
    print(f"Duplicates Removed: {stats['duplicates_removed']}")
    print(f"Saved to DB:       {stats['new_stories_saved']} stories")
    print("=" * 70 + "\n")

    # Show top stories from database
    print("[*] Top 10 stories in database (by score):\n")

    stories = dao.get_latest_stories(limit=10)

    for i, story in enumerate(stories, 1):
        score = story.metadata.get("score", 0)
        comments = story.metadata.get("comments", 0)
        source = story.source.value.replace("_", " ").title()

        print(f"{i}. [{source}] {story.title[:70]}")
        print(f"   URL: {story.url[:70]}...")
        print(f"   Score: {score} | Comments: {comments}")
        print()

    # Statistics
    print("=" * 70)
    print("DATABASE STATISTICS")
    print("=" * 70)

    total_stories = len(db.execute("SELECT * FROM stories"))
    print(f"Total stories in database: {total_stories}")

    source_counts = db.execute("""
        SELECT source, COUNT(*) as count 
        FROM stories 
        GROUP BY source 
        ORDER BY count DESC
    """)
    print("\nStories by source:")
    for source, count in source_counts:
        print(f"  {source}: {count}")

    # Engagement stats
    feedback_count = len(db.execute("SELECT * FROM user_feedback"))
    print(f"\nUser feedback entries: {feedback_count}")

    print("=" * 70 + "\n")

    print("✓ Demo complete!")
    print("\nNext steps:")
    print("  1. Check database with: sqlite3 ./data/briefing_demo.db")
    print("  2. Run tests with: pytest tests/test_sources.py -v")
    print("  3. Phase 1.3: Ranking engine (coming next)")


if __name__ == "__main__":
    asyncio.run(main())
