#!/usr/bin/env python3
"""Demo: Fetch news and rank them with Phase 1.3 ranking engine."""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from app.memory.database import Database
from app.memory.dao import StoryDAO
from app.sources.manager import NewsManager
from app.ranking.manager import RankingManager
from app.config.settings import settings

async def main():
    print("=" * 70)
    print("TELEGRAM BRIEFING BOT - PHASE 1.3: RANKING ENGINE DEMO")
    print("=" * 70)
    print()
    
    # Initialize database for demo
    db_path = "./data/briefing_demo.db"
    db = Database(db_path)
    dao = StoryDAO(db)
    
    # Step 1: Fetch news from all sources
    print("📰 Step 1: Fetching news from HN and Reddit...")
    print()
    
    manager = NewsManager(dao)
    stats = await manager.fetch_all()
    
    # Get stories from database
    stories = dao.get_recent_stories(hours=24, limit=100)
    
    print(f"✓ Fetched {len(stories)} unique stories")
    print(f"  Sources: {set(s.source.value for s in stories)}")
    print()
    
    # Step 2: Rank stories
    print("📊 Step 2: Ranking stories with composite scoring...")
    print(f"  Weights: Relevance 40%, Virality 30%, Depth 20%, Novelty 10%")
    print(f"  Your interests: {', '.join(settings.interest_list)}")
    print()
    
    ranker = RankingManager()
    ranked = ranker.get_ranked_with_scores(stories)
    
    # Step 3: Display top 10
    print("🏆 Top 10 Stories for Your Briefing:")
    print("=" * 70)
    print()
    
    for i, item in enumerate(ranked[:10], 1):
        story = item["story"]
        score = item["score"]
        breakdown = item["breakdown"]
        
        print(f"{i}. {story.title}")
        print(f"   URL: {story.url}")
        print(f"   Source: {story.source.value.upper()}")
        print(f"   Score: {score:.3f}")
        print(f"   │ Relevance: {breakdown['relevance']:.3f}")
        print(f"   │ Virality:  {breakdown['virality']:.3f}")
        print(f"   │ Depth:     {breakdown['depth']:.3f}")
        print(f"   │ Novelty:   {breakdown['novelty']:.3f}")
        print()
    
    # Step 4: Show statistics
    print("=" * 70)
    print("📈 Statistics:")
    print(f"  Total stories fetched: {len(stories)}")
    print(f"  Top 10 avg score: {sum(r['score'] for r in ranked[:10]) / 10:.3f}")
    print(f"  Top 10 avg relevance: {sum(r['breakdown']['relevance'] for r in ranked[:10]) / 10:.3f}")
    print(f"  Top 10 avg virality: {sum(r['breakdown']['virality'] for r in ranked[:10]) / 10:.3f}")
    print()
    
    # Step 5: Show next phase info
    print("=" * 70)
    print("✅ PHASE 1.3 COMPLETE")
    print()
    print("Next: Phase 1.4 - LLM Summarization")
    print("  - Summarize top 10 stories with Claude")
    print("  - Add personal angles based on your interests")
    print("  - Format for Telegram delivery")
    print()

if __name__ == "__main__":
    asyncio.run(main())
