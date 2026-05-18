"""Telegram bot client for delivering briefings."""

import asyncio
from typing import Optional

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import RetryAfter, TimedOut, NetworkError

from app.config.settings import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

TELEGRAM_MAX_LENGTH = 4096


class TelegramClient:
    """Send messages to a Telegram chat."""

    def __init__(
        self,
        token: Optional[str] = None,
        chat_id: Optional[str] = None,
    ):
        self.token = token or settings.telegram_bot_token
        self.chat_id = chat_id or settings.telegram_chat_id
        self.bot = Bot(token=self.token)

    async def send_message(
        self,
        text: str,
        parse_mode: str = ParseMode.HTML,
        disable_web_page_preview: bool = True,
    ) -> Optional[int]:
        """Send a single message. Returns the message_id, or None on failure."""
        try:
            msg = await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
            )
            return msg.message_id
        except RetryAfter as e:
            logger.warning(f"Rate limited, sleeping {e.retry_after}s then retrying")
            await asyncio.sleep(e.retry_after + 1)
            return await self.send_message(text, parse_mode, disable_web_page_preview)
        except (TimedOut, NetworkError) as e:
            logger.error(f"Telegram network error: {e}")
            return None
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return None

    async def send_briefing(self, html: str) -> list[int]:
        """Send a briefing. Splits into chunks if over Telegram's 4096-char limit.

        Returns the list of message_ids sent.
        """
        chunks = self._split_safely(html, TELEGRAM_MAX_LENGTH - 64)
        logger.info(f"Sending briefing as {len(chunks)} message(s)")

        message_ids: list[int] = []
        for i, chunk in enumerate(chunks, 1):
            mid = await self.send_message(chunk)
            if mid is None:
                logger.error(f"Failed to send chunk {i}/{len(chunks)}, aborting")
                break
            message_ids.append(mid)
            # Small gap between messages to be polite to Telegram
            if i < len(chunks):
                await asyncio.sleep(0.5)

        return message_ids

    @staticmethod
    def _split_safely(text: str, limit: int) -> list[str]:
        """Split text on paragraph boundaries, never exceeding `limit` chars per chunk."""
        if len(text) <= limit:
            return [text]

        chunks: list[str] = []
        remaining = text
        while len(remaining) > limit:
            # Prefer splitting on double-newline (between stories), then single newline
            cut = remaining.rfind("\n\n", 0, limit)
            if cut < limit // 2:
                cut = remaining.rfind("\n", 0, limit)
            if cut < limit // 2:
                cut = limit
            chunks.append(remaining[:cut].rstrip())
            remaining = remaining[cut:].lstrip()
        if remaining:
            chunks.append(remaining)
        return chunks
