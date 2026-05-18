# Telegram AI Briefing Agent

An autonomous AI-powered Telegram bot that delivers a curated daily tech + AI + systems engineering briefing at 9:00 AM.

**Status**: Phase 1.1 (Config + Database) ✓ Complete

## Features

- 🤖 **Intelligent News Aggregation**: Fetches from Hacker News, Reddit, GitHub, ArXiv
- 🧠 **LLM-Powered Summarization**: Uses Claude for smart summaries
- 🎯 **Personalized Ranking**: Learns your interests through feedback
- 📊 **Engagement Tracking**: Implicit learning from your reactions
- 🔄 **Source Quality Scoring**: Improves recommendations over time
- 💾 **SQLite Memory**: Persistent storage for stories, feedback, trends

## Tech Stack

- **Language**: Python 3.9+
- **Async**: aiohttp, APScheduler
- **Database**: SQLite
- **LLM**: OpenRouter (Claude 3.5 Sonnet)
- **Telegram**: python-telegram-bot
- **Config**: Pydantic, python-dotenv

## Project Structure

```
telegram-briefing-agent/
├── app/
│   ├── config/          # Settings & environment
│   ├── sources/         # News fetchers (HN, Reddit, GitHub, ArXiv)
│   ├── ranking/         # Scoring & ranking engine
│   ├── summarizer/      # LLM summarization
│   ├── memory/          # SQLite database & DAOs
│   ├── telegram/        # Bot client & formatters
│   ├── scheduler/       # APScheduler tasks
│   ├── utils/           # Logging, errors
│   └── models.py        # Data models
├── tests/               # Unit tests
├── requirements.txt     # Dependencies
├── .env                 # Secrets (create from .env.example)
└── main.py             # Entry point
```

## Quick Start

### 1. Clone & Setup

```bash
cd telegram-briefing-agent
pip install -r requirements.txt
cp .env.example .env
```

### 2. Configure Secrets

Edit `.env`:

```env
# Required
TELEGRAM_BOT_TOKEN=your_token_from_@BotFather
TELEGRAM_CHAT_ID=your_chat_id
LLM_API_KEY=your_openrouter_api_key

# Optional
BRIEFING_HOUR=9
BRIEFING_MINUTE=0
TIMEZONE=America/Los_Angeles
```

### 3. Test Database

```bash
python3 test_db.py
```

Expected output: ✓ ALL TESTS PASSED

### 4. Run Daily Briefing

(Coming in Phase 1.2)

```bash
python3 main.py
```

## Architecture

### Data Flow

```
[Scheduler: 9 AM]
    ↓
[Fetch News (Parallel)]
  - Hacker News (50 items)
  - Reddit (200 items)
  - GitHub (100 repos)
  - ArXiv (50 papers)
    ↓
[Rank Stories]
  - Relevance scoring (keywords)
  - Virality scoring (upvotes)
  - Depth scoring (technical detail)
  - Novelty scoring (deduplication)
    ↓
[Top 30 candidates → LLM]
    ↓
[Summarize & Format]
    ↓
[Send to Telegram]
    ↓
[Track Feedback]
  - User reactions (❤️/👎)
  - Source quality updates
  - Topic engagement learning
```

## Database Schema

### Core Tables

- **stories**: All fetched news items
- **story_scores**: Ranking scores per story
- **summaries**: LLM-generated summaries
- **feedback**: User reactions (like/dislike/bookmark)
- **briefings**: History of sent briefings

### Learning Tables

- **source_quality**: Quality score by source
- **topic_engagement**: Engagement metrics by topic
- **engagement_metrics**: Per-story view/click/reaction time

## Configuration

### Ranking Weights

Customize in `.env`:

```env
RANK_WEIGHT_RELEVANCE=0.4   # Topic match importance
RANK_WEIGHT_VIRALITY=0.3    # Upvotes/engagement
RANK_WEIGHT_DEPTH=0.2       # Technical detail
RANK_WEIGHT_NOVELTY=0.1     # Recency bonus
```

### Interest Keywords

```env
INTEREST_KEYWORDS=vLLM,CUDA,distributed systems,agentic AI,robotics,ML infrastructure,reasoning models,edge AI,MCP,RAG
```

## Phase Roadmap

### Phase 1: Core Pipeline ✓

- [x] 1.1: Config + Database (CURRENT)
- [ ] 1.2: News Fetchers (HN, Reddit basic)
- [ ] 1.3: Ranking Engine
- [ ] 1.4: Telegram Formatter & Sender

### Phase 2: Intelligence

- [ ] 2.1: LLM Summarizer
- [ ] 2.2: Feedback Handlers
- [ ] 2.3: Source Quality Learning

### Phase 3: Scale Sources

- [ ] 3.1: Full Reddit Integration
- [ ] 3.2: GitHub Trending
- [ ] 3.3: ArXiv Papers

### Phase 4: Learning

- [ ] 4.1: Engagement Metrics
- [ ] 4.2: Topic Preference Learning
- [ ] 4.3: Trend Detection

### Phase 5: Deployment

- [ ] 5.1: Systemd Service
- [ ] 5.2: Logging & Monitoring
- [ ] 5.3: Production Hardening

## API Keys Setup

### Telegram Bot

1. Message @BotFather on Telegram
2. `/newbot` → name it → get token
3. Get your chat ID: Message @userinfobot

### LLM (OpenRouter)

1. Sign up: https://openrouter.ai
2. Get API key from settings
3. Add to `.env` as `LLM_API_KEY`

### Reddit (Optional for Phase 3)

1. Visit https://www.reddit.com/prefs/apps
2. Create script app
3. Get client_id, client_secret

## Testing

```bash
# Test database layer
python3 test_db.py

# Run all tests (coming in Phase 2)
pytest tests/
```

## Development

### Adding a New Source

1. Create `app/sources/new_source.py`
2. Inherit from `NewsSource` base class
3. Implement `async def fetch()` method
4. Register in `app/sources/manager.py`

### Modifying Ranking

Edit `app/ranking/scorer.py`:
- `calculate_relevance_score()`
- `calculate_virality_score()`
- `calculate_depth_score()`
- `calculate_novelty_score()`

### Custom LLM Models

Update `.env`:

```env
LLM_MODEL=claude-3-5-sonnet  # or haiku, opus, etc.
```

## Notes

- **First Run**: Database initializes automatically
- **Deduplication**: Stories with same title/URL merged
- **Timezone**: Set to your local timezone for 9 AM precision
- **Testing**: Use `test_briefing.db` to avoid production data

## Next Steps

→ **Phase 1.2**: Build Hacker News & Reddit fetchers

→ **Phase 1.3**: Implement ranking engine

→ **Phase 1.4**: Create Telegram formatter & send

## Contributing

This is a personal project but open to improvements. Areas for contribution:

- [ ] Additional news sources (Product Hunt, Lobsters, etc.)
- [ ] Improved NLP ranking
- [ ] Web dashboard for feedback
- [ ] REST API for remote control
- [ ] Cloud deployment (AWS Lambda, GCP Cloud Run)

## License

MIT
