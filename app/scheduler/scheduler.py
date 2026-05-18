"""APScheduler wrapper that fires the briefing job on a daily cron."""

import asyncio
import signal
from typing import Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone as pytz_timezone

from app.config.settings import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class BriefingScheduler:
    """Run an async callback daily at a configured local time."""

    def __init__(
        self,
        callback: Callable[[], Awaitable[None]],
        hour: int = None,
        minute: int = None,
        tz: str = None,
    ):
        self.callback = callback
        self.hour = hour if hour is not None else settings.briefing_hour
        self.minute = minute if minute is not None else settings.briefing_minute
        self.tz = tz or settings.timezone
        self.scheduler = AsyncIOScheduler(timezone=pytz_timezone(self.tz))

    async def _wrapped(self):
        """Invoke the callback with broad error handling so the scheduler keeps running."""
        try:
            await self.callback()
        except Exception:
            logger.exception("Briefing job failed; scheduler will continue")

    async def run_forever(self):
        """Start the scheduler and block until SIGINT/SIGTERM."""
        trigger = CronTrigger(hour=self.hour, minute=self.minute, timezone=pytz_timezone(self.tz))
        self.scheduler.add_job(self._wrapped, trigger, id="daily_briefing", replace_existing=True)
        self.scheduler.start()

        next_run = self.scheduler.get_job("daily_briefing").next_run_time
        logger.info(f"Scheduler started — next briefing at {next_run.isoformat()} ({self.tz})")

        stop_event = asyncio.Event()
        loop = asyncio.get_event_loop()

        def _stop():
            logger.info("Shutdown signal received")
            stop_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _stop)
            except NotImplementedError:
                # add_signal_handler isn't available on Windows
                pass

        await stop_event.wait()
        self.scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
