#!/usr/bin/env python3
"""
Health check & setup verification for Telegram Briefing Agent.
Run this to verify everything is installed and configured.
"""

import sys
import os
from pathlib import Path

def check(condition: bool, name: str, detail: str = ""):
    """Print check status."""
    status = "✓" if condition else "✗"
    msg = f"{status} {name}"
    if detail:
        msg += f" ({detail})"
    print(msg)
    return condition


def main():
    print("\n" + "=" * 60)
    print("TELEGRAM BRIEFING AGENT - HEALTH CHECK")
    print("=" * 60 + "\n")

    all_pass = True

    # 1. Python version
    py_version = sys.version_info
    all_pass &= check(
        py_version.major >= 3 and py_version.minor >= 9,
        "Python version",
        f"{py_version.major}.{py_version.minor}"
    )

    # 2. Project structure
    required_dirs = [
        "app/config",
        "app/memory",
        "app/sources",
        "app/ranking",
        "app/summarizer",
        "app/telegram",
        "app/scheduler",
        "app/utils",
        "data",
    ]
    for dir_name in required_dirs:
        all_pass &= check(
            Path(dir_name).exists(),
            f"Directory: {dir_name}",
        )

    # 3. Required files
    required_files = [
        "app/config/settings.py",
        "app/memory/database.py",
        "app/memory/dao.py",
        "app/models.py",
        "app/utils/logger.py",
        "app/utils/errors.py",
        "README.md",
        "requirements.txt",
        ".env",
    ]
    for file_name in required_files:
        all_pass &= check(
            Path(file_name).exists(),
            f"File: {file_name}",
        )

    # 4. Import key modules
    print("\nImporting modules...")
    try:
        from app.config.settings import settings
        check(True, "app.config.settings")
    except Exception as e:
        check(False, "app.config.settings", str(e))
        all_pass = False

    try:
        from app.memory.database import Database
        check(True, "app.memory.database")
    except Exception as e:
        check(False, "app.memory.database", str(e))
        all_pass = False

    try:
        from app.memory.dao import StoryDAO, FeedbackDAO
        check(True, "app.memory.dao")
    except Exception as e:
        check(False, "app.memory.dao", str(e))
        all_pass = False

    try:
        from app.models import Story, NewsSource
        check(True, "app.models")
    except Exception as e:
        check(False, "app.models", str(e))
        all_pass = False

    # 5. Database initialization
    print("\nDatabase check...")
    try:
        from app.memory.database import Database
        db = Database("./data/briefing_health.db")
        check(True, "Database initialization")

        # Clean up test db
        Path("./data/briefing_health.db").unlink(missing_ok=True)
    except Exception as e:
        check(False, "Database initialization", str(e))
        all_pass = False

    # 6. Configuration
    print("\nConfiguration check...")
    try:
        from app.config.settings import settings
        check(
            len(settings.telegram_bot_token or "") > 0,
            "TELEGRAM_BOT_TOKEN",
            "Set in .env" if not settings.telegram_bot_token else "Configured"
        )
        check(
            len(settings.llm_api_key or "") > 0,
            "LLM_API_KEY",
            "Set in .env" if not settings.llm_api_key else "Configured"
        )
        check(
            settings.briefing_hour >= 0 and settings.briefing_hour < 24,
            "Briefing time",
            f"{settings.briefing_hour:02d}:{settings.briefing_minute:02d}"
        )
    except Exception as e:
        check(False, "Configuration", str(e))
        all_pass = False

    # 7. Dependencies
    print("\nDependency check...")
    packages = [
        ("pydantic", "Pydantic"),
        ("aiohttp", "aiohttp"),
        ("httpx", "httpx"),
        ("apscheduler", "APScheduler"),
        ("telegram", "python-telegram-bot"),
    ]
    for import_name, display_name in packages:
        try:
            __import__(import_name)
            check(True, f"Package: {display_name}")
        except ImportError:
            check(False, f"Package: {display_name}", "Not installed")
            all_pass = False

    # Final status
    print("\n" + "=" * 60)
    if all_pass:
        print("✓ ALL CHECKS PASSED - Ready to go!")
        print("\nNext steps:")
        print("  1. Read README.md for overview")
        print("  2. Run: python3 main.py")
        print("  3. Check: python3 test_db.py")
        print("  4. Phase 1.2: Implement news fetchers")
        print("=" * 60 + "\n")
        return 0
    else:
        print("✗ SOME CHECKS FAILED - See details above")
        print("=" * 60 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
