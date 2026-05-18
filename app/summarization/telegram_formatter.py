"""Format summaries for Telegram delivery."""

from typing import Optional
from datetime import datetime
from app.summarization.summarizer import Summary
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class TelegramFormatter:
    """Format summaries as Telegram messages."""
    
    def __init__(self, max_message_length: int = 4096):
        """Initialize formatter.
        
        Args:
            max_message_length: Max length per Telegram message (4096 is API limit)
        """
        self.max_length = max_message_length
        
    def format_briefing(
        self,
        summaries: list[Summary],
        title: Optional[str] = None
    ) -> str:
        """Format all summaries as a single briefing message.
        
        Args:
            summaries: List of Summary objects
            title: Optional briefing title
            
        Returns:
            Formatted message for Telegram
        """
        if not summaries:
            return "📰 No stories found for today's briefing"
        
        # Build header
        timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        header = title or "📰 Daily Tech Briefing"
        message = f"{header}\n{timestamp}\n\n"
        message += f"✨ Top {len(summaries)} stories for you\n"
        message += "=" * 50 + "\n\n"
        
        # Add each summary
        for idx, summary in enumerate(summaries, 1):
            # Build story section
            story_section = self._format_story(summary, idx)
            
            # Check if we can fit it
            if len(message) + len(story_section) > self.max_length - 100:
                # Too long, truncate and stop
                logger.warning(f"Briefing message too long, truncating at story {idx}")
                message += "\n... (More stories available)"
                break
            
            message += story_section
        
        # Add footer
        message += "\n" + "=" * 50
        message += "\n\n🔗 Click story titles to read full articles"
        
        return message
    
    def format_story(self, summary: Summary, index: Optional[int] = None) -> str:
        """Format a single story for display.
        
        Args:
            summary: Summary object
            index: Optional index for ordering
            
        Returns:
            Formatted story
        """
        return self._format_story(summary, index)
    
    def _format_story(self, summary: Summary, index: Optional[int] = None) -> str:
        """Internal story formatting."""
        lines = []
        
        # Title with index and score
        if index:
            lines.append(f"{index}. <b>{summary.title}</b>")
        else:
            lines.append(f"<b>{summary.title}</b>")
        
        # Trend tag
        trend_tag = f"#{summary.trend.replace(' ', '_')}"
        lines.append(f"   <i>{trend_tag}</i>")
        
        # Summary
        lines.append(f"\n{summary.summary}")
        
        # Why it matters
        lines.append(f"\n💡 <b>Why it matters:</b> {summary.why_it_matters}")
        
        # Action
        lines.append(f"✓ {summary.action}")
        
        # Source and link
        lines.append(f"\n📍 {summary.source} • "
                    f"<a href='{summary.url}'>Read full story</a>")
        
        # Score
        lines.append(f"⭐ Relevance: {summary.composite_score:.1%}\n")
        
        return "\n".join(lines)
    
    def format_as_thread(self, summaries: list[Summary]) -> list[str]:
        """Format briefing as a thread of separate messages.
        
        Each message is a separate story, staying under Telegram's limit.
        
        Args:
            summaries: List of Summary objects
            
        Returns:
            List of messages (one per story)
        """
        messages = []
        
        # Header message
        timestamp = datetime.now().strftime("%B %d, %Y")
        header = (
            f"📰 <b>Daily Tech Briefing - {timestamp}</b>\n"
            f"✨ Top {len(summaries)} stories\n\n"
        )
        messages.append(header + "Reading 1/" + str(len(summaries)))
        
        # Story messages
        for idx, summary in enumerate(summaries, 1):
            msg = f"#{idx}. {self._format_story(summary)}"
            messages.append(msg)
        
        # Footer
        messages.append(
            f"✅ That's today's briefing ({len(summaries)} stories)\n\n"
            "See you tomorrow at 9 AM!"
        )
        
        return messages
    
    def format_summary_only(self, summary: Summary) -> str:
        """Format just the summary text, minimal formatting.
        
        Args:
            summary: Summary object
            
        Returns:
            Plain text summary
        """
        return (
            f"{summary.title}\n\n"
            f"{summary.summary}\n\n"
            f"Why it matters: {summary.why_it_matters}\n"
            f"Action: {summary.action}\n"
            f"Trend: {summary.trend}\n"
            f"Source: {summary.source}\n"
            f"Read: {summary.url}"
        )
    
    def estimate_message_length(self, summaries: list[Summary]) -> int:
        """Estimate total message length for a briefing.
        
        Args:
            summaries: List of Summary objects
            
        Returns:
            Estimated character count
        """
        total = 0
        for summary in summaries:
            total += len(self._format_story(summary))
        
        # Add header and footer
        total += 200
        
        return total
    
    def split_briefing(
        self,
        summaries: list[Summary],
        max_per_message: int = 3
    ) -> list[str]:
        """Split briefing into multiple messages if needed.
        
        Args:
            summaries: List of Summary objects
            max_per_message: Max stories per message
            
        Returns:
            List of messages
        """
        messages = []
        
        for i in range(0, len(summaries), max_per_message):
            batch = summaries[i:i + max_per_message]
            message = self.format_briefing(
                batch,
                title=f"📰 Daily Tech Briefing (Part {i // max_per_message + 1})"
            )
            messages.append(message)
        
        return messages
