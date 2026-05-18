import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load .env
load_dotenv()


class Settings(BaseSettings):
    """Application configuration from environment variables."""

    # Telegram
    telegram_bot_token: str = Field(..., validation_alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(..., validation_alias="TELEGRAM_CHAT_ID")

    # LLM
    llm_provider: str = Field(default="openrouter", validation_alias="LLM_PROVIDER")
    llm_api_key: str = Field(..., validation_alias="LLM_API_KEY")
    llm_model: str = Field(
        default="claude-3-5-sonnet", validation_alias="LLM_MODEL"
    )

    # App
    briefing_hour: int = Field(default=9, validation_alias="BRIEFING_HOUR")
    briefing_minute: int = Field(default=0, validation_alias="BRIEFING_MINUTE")
    timezone: str = Field(default="UTC", validation_alias="TIMEZONE")
    db_path: str = Field(default="./data/briefing.db", validation_alias="DB_PATH")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    # News Source Limits
    hn_fetch_limit: int = Field(default=50, validation_alias="HN_FETCH_LIMIT")
    reddit_fetch_limit: int = Field(
        default=200, validation_alias="REDDIT_FETCH_LIMIT"
    )
    github_fetch_limit: int = Field(
        default=100, validation_alias="GITHUB_FETCH_LIMIT"
    )
    arxiv_fetch_limit: int = Field(default=50, validation_alias="ARXIV_FETCH_LIMIT")

    # Ranking Weights
    rank_weight_relevance: float = Field(
        default=0.4, validation_alias="RANK_WEIGHT_RELEVANCE"
    )
    rank_weight_virality: float = Field(
        default=0.3, validation_alias="RANK_WEIGHT_VIRALITY"
    )
    rank_weight_depth: float = Field(
        default=0.2, validation_alias="RANK_WEIGHT_DEPTH"
    )
    rank_weight_novelty: float = Field(
        default=0.1, validation_alias="RANK_WEIGHT_NOVELTY"
    )

    # Output
    items_per_briefing: int = Field(
        default=10, validation_alias="ITEMS_PER_BRIEFING"
    )

    # Interest Keywords (comma-separated)
    interest_keywords: str = Field(
        default="vLLM,CUDA,distributed systems,agentic AI,robotics,ML infrastructure,reasoning models,edge AI,MCP,RAG",
        validation_alias="INTEREST_KEYWORDS",
    )

    # Reddit API (Optional, for Phase 1.2)
    reddit_client_id: str = Field(default="", validation_alias="REDDIT_CLIENT_ID")
    reddit_client_secret: str = Field(default="", validation_alias="REDDIT_CLIENT_SECRET")
    
    # Groq API (Optional fallback LLM)
    groq_api_key: str = Field(default="", validation_alias="GROQ_API_KEY")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields in .env

    @property
    def interest_list(self) -> list[str]:
        """Parse interest keywords."""
        return [k.strip() for k in self.interest_keywords.split(",") if k.strip()]

    def ensure_db_dir(self):
        """Create database directory if it doesn't exist."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)


# Singleton instance
settings = Settings()
settings.ensure_db_dir()
