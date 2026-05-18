# Development Guide: Telegram Briefing Agent

## Overview

This guide helps you understand the codebase and contribute effectively.

## Module Map

```
app/
│
├── config/
│   └── settings.py           ← Configuration & env vars
│       ✓ Pydantic validation
│       ✓ Singleton instance
│
├── models.py                 ← Data models
│       ✓ Story (base model)
│       ✓ RankedStory (scored)
│       ✓ BriefingSummary (LLM output)
│       ✓ TelegramMessage (formatted output)
│
├── memory/
│   ├── database.py           ← SQLite connection & schema
│   │       ✓ Context managers
│   │       ✓ Automatic initialization
│   │
│   └── dao.py                ← Data access objects
│           ✓ StoryDAO
│           ✓ ScoreDAO
│           ✓ FeedbackDAO
│           ✓ SourceQualityDAO
│           ✓ TopicEngagementDAO
│           ✓ BriefingDAO
│
├── sources/ (TODO: Phase 1.2)
│   ├── base.py               ← Abstract NewsSource
│   ├── hacker_news.py        ← HN fetcher
│   ├── reddit_fetcher.py     ← Reddit fetcher
│   ├── github_trending.py    ← GitHub (Phase 3)
│   ├── arxiv_fetcher.py      ← ArXiv (Phase 3)
│   ├── deduplicator.py       ← Merge duplicates
│   └── manager.py            ← Orchestrate all sources
│
├── ranking/ (TODO: Phase 1.3)
│   ├── scorer.py             ← Scoring algorithm
│   │       - relevance_score()
│   │       - virality_score()
│   │       - depth_score()
│   │       - novelty_score()
│   │       - final_score()
│   │
│   └── ranker.py             ← Rank & filter top N
│
├── summarizer/ (TODO: Phase 2.1)
│   └── llm_summarizer.py     ← LLM integration
│           ✓ Batch summarization
│           ✓ Trend detection
│           ✓ OpenRouter client
│
├── telegram/ (TODO: Phase 1.4)
│   ├── client.py             ← Telegram API wrapper
│   ├── formatter.py          ← Markdown formatting
│   └── handlers.py           ← Feedback buttons
│
├── scheduler/ (TODO: Phase 4)
│   └── tasks.py              ← APScheduler jobs
│
└── utils/
    ├── logger.py             ← Structured logging
    └── errors.py             ← Exception hierarchy
```

## Development Workflow

### 1. Before Coding

- Read the README.md for overview
- Read PHASE_1_1_REPORT.md for completed work
- Check PHASE_1_2_SPEC.md for next phase details

### 2. Running Code

```bash
# Test database layer
python3 test_db.py

# Run main (currently just prints status)
python3 main.py

# Test a module
python3 -m pytest tests/test_sources.py -v
```

### 3. Adding Features

**Example: Add GitHub Trending Source**

1. Create `app/sources/github_trending.py`
2. Inherit from `NewsSourceBase`
3. Implement `async def fetch()` method
4. Register in `NewsManager` in `app/sources/manager.py`
5. Write test in `tests/test_sources.py`
6. Update `requirements.txt` if new library

**Example: Modify Ranking Algorithm**

1. Edit `app/ranking/scorer.py`
2. Adjust weights in `.env`
3. Run `test_ranking.py` to verify
4. Check final scores in database

## Code Quality Standards

### Python Style

- Follow PEP 8 (use black formatter)
- Type hints for all functions
- Docstrings for classes & public methods
- snake_case for variables
- UPPER_CASE for constants

### Error Handling

```python
from app.utils.errors import FetchError

try:
    result = await fetcher.fetch()
except FetchError as e:
    logger.error(f"Fetch failed: {e}")
    return []
```

### Logging

```python
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

logger.info("Starting fetch...")
logger.warning(f"Slow response: {duration}ms")
logger.error(f"Failed: {exception}")
```

### Database Operations

```python
from app.memory.database import Database
from app.memory.dao import StoryDAO

db = Database()
dao = StoryDAO(db)

# Always use DAOs, never raw SQL
if not dao.story_exists(story.id):
    dao.save_story(story)
```

## Testing Philosophy

- Unit tests for logic (ranking, formatting)
- Integration tests for data flow
- Mock external APIs (don't call HN/Reddit in tests)
- Use in-memory SQLite for DB tests

## Common Tasks

### Debug a Story

```python
from app.memory.database import Database
from app.memory.dao import StoryDAO

db = Database()
dao = StoryDAO(db)

story = dao.get_story_by_id("hn:12345")
print(f"Title: {story.title}")
print(f"Source: {story.source}")
print(f"Metadata: {story.metadata}")
```

### Check Feedback Counts

```python
from app.memory.dao import FeedbackDAO

feedback_dao = FeedbackDAO(db)
counts = feedback_dao.get_feedback_count("hn:12345")
print(f"Likes: {counts['like']}, Dislikes: {counts['dislike']}")
```

### Clear Database (Testing)

```bash
rm ./data/briefing.db
# Next run will create fresh schema
```

## Architecture Patterns

### 1. Async/Await

All I/O operations (HTTP, DB) are async:

```python
async def main():
    manager = NewsManager(dao)
    results = await manager.fetch_all()  # Non-blocking
```

### 2. Dependency Injection

DAOs receive db instance:

```python
db = Database()
story_dao = StoryDAO(db)
score_dao = ScoreDAO(db)
```

### 3. Separation of Concerns

- **sources/**: Fetch raw data
- **ranking/**: Score & filter
- **summarizer/**: LLM processing
- **telegram/**: Format & send
- **memory/**: Persist everything

### 4. Config First

All tuning parameters in `.env`, not hardcoded:

```python
# ✓ Good
relevance_score = settings.rank_weight_relevance * tfidf_score

# ✗ Bad
relevance_score = 0.4 * tfidf_score  # Magic number!
```

## Performance Tips

- **Batch operations**: Use `save_stories()` not `save_story()`
- **Parallel fetching**: Use `asyncio.gather()` for sources
- **Database indexes**: Already added for common queries
- **Lazy loading**: Don't fetch unnecessary fields

## Debugging

### Enable verbose logging

```bash
LOG_LEVEL=DEBUG python3 main.py
```

### Print database state

```bash
sqlite3 ./data/briefing.db
sqlite> SELECT COUNT(*) FROM stories;
sqlite> SELECT * FROM stories LIMIT 1;
```

### Trace async issues

```python
import asyncio
asyncio.run(main(), debug=True)
```

## Next Steps

1. **Phase 1.2**: Implement news fetchers (HN, Reddit)
2. **Phase 1.3**: Build ranking algorithm
3. **Phase 1.4**: Create Telegram formatter & sender

## Resources

- Pydantic docs: https://docs.pydantic.dev/
- aiohttp docs: https://docs.aiohttp.org/
- SQLite tutorial: https://www.sqlite.org/cli.html
- python-telegram-bot: https://github.com/python-telegram-bot/python-telegram-bot

---

**Questions?** Check the inline docstrings in each module!
