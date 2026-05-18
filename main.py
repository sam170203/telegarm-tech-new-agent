"""Telegram AI Briefing Agent — main entry point.

Usage:
    python3 main.py              # daemon mode: cron at BRIEFING_HOUR:BRIEFING_MINUTE daily
    python3 main.py run-now      # send one briefing immediately and exit
    python3 main.py run-now --dry-run   # build a briefing, print it, do not send
"""

import argparse
import asyncio
import sys

from app.config.settings import settings
from app.pipeline import run_briefing
from app.scheduler.scheduler import BriefingScheduler
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Telegram AI Briefing Agent")
    subparsers = parser.add_subparsers(dest="command")

    run_now = subparsers.add_parser("run-now", help="Send one briefing immediately and exit")
    run_now.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the briefing and print it; do not send to Telegram",
    )

    return parser.parse_args(argv)


async def _daemon():
    logger.info(
        f"Starting daemon — briefing daily at "
        f"{settings.briefing_hour:02d}:{settings.briefing_minute:02d} ({settings.timezone})"
    )
    scheduler = BriefingScheduler(callback=lambda: run_briefing(dry_run=False))
    await scheduler.run_forever()


def main(argv: list[str] = None):
    args = parse_args(argv if argv is not None else sys.argv[1:])

    logger.info("=" * 60)
    logger.info("TELEGRAM AI BRIEFING AGENT")
    logger.info("=" * 60)
    logger.info(f"Timezone: {settings.timezone}")
    logger.info(f"Items per briefing: {settings.items_per_briefing}")
    logger.info(f"Interests: {', '.join(settings.interest_list[:5])}...")

    if args.command == "run-now":
        result = asyncio.run(run_briefing(dry_run=args.dry_run))
        logger.info(f"Run finished: {result.get('status')}")
        sys.exit(0 if result.get("status") == "ok" else 1)
    else:
        asyncio.run(_daemon())


if __name__ == "__main__":
    main()
