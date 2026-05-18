"""AI-powered story summarization with Claude."""

import asyncio
from typing import Optional
from dataclasses import dataclass
import httpx

from app.models import Story
from app.config.settings import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class Summary:
    """Summarized story with context."""
    story_id: str
    title: str
    summary: str  # 2-3 line AI summary
    why_it_matters: str  # Personal relevance
    action: str  # What to do about it
    trend: str  # Category/trend it belongs to
    source: str
    url: str
    composite_score: float


class ClaudeSummarizer:
    """Summarize stories using Claude via OpenRouter."""
    
    def __init__(self):
        """Initialize Claude summarizer."""
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.base_url = "https://openrouter.ai/api/v1"
        self.client = None
        
    async def initialize(self):
        """Initialize async client."""
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "telegram-briefing-agent",
            }
        )
        logger.info("Claude summarizer initialized")
        
    async def close(self):
        """Close async client."""
        if self.client:
            await self.client.aclose()
            
    async def summarize(self, story: Story, composite_score: float) -> Summary:
        """Summarize a single story.
        
        Args:
            story: Story to summarize
            composite_score: Ranking score (0-1)
            
        Returns:
            Summary object with AI-generated insights
        """
        try:
            # Build context about user interests
            interests = ", ".join(settings.interest_keywords[:5])
            
            # Construct prompt
            prompt = self._build_prompt(story, interests)
            
            # Call Claude
            response = await self.client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500,
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Parse response (content can be null when Claude refuses or returns empty)
            content = result["choices"][0]["message"].get("content") or ""
            if not content.strip():
                logger.warning(f"Empty LLM response for {story.title[:60]}; using fallback")
                return self._fallback_summary(story, composite_score)
            parsed = self._parse_response(content)
            
            # Create summary
            summary = Summary(
                story_id=story.id,
                title=story.title,
                summary=parsed["summary"],
                why_it_matters=parsed["why_it_matters"],
                action=parsed["action"],
                trend=parsed["trend"],
                source=story.source.value,
                url=story.url,
                composite_score=composite_score,
            )
            
            logger.info(f"Summarized: {story.title[:60]}...")
            return summary
            
        except Exception as e:
            logger.error(f"Summarization error for {story.title}: {e}")
            # Return fallback summary
            return self._fallback_summary(story, composite_score)
    
    def _build_prompt(self, story: Story, interests: str) -> str:
        """Build Claude prompt for story summarization."""
        return f"""Summarize this tech news story for someone interested in: {interests}

Story Title: {story.title}
Story URL: {story.url}
Story Content: {story.content[:500] if story.content else 'N/A'}

Provide EXACTLY this format with one-line answers:

SUMMARY: [2-3 sentence summary of the news]

WHY_IT_MATTERS: [1 sentence: how this relates to {interests}]

ACTION: [1 sentence: what the reader should do about this]

TREND: [1-2 words: which category this belongs to (e.g., "LLM Optimization", "Distributed Systems")]

Be concise and actionable."""
    
    def _parse_response(self, content: str) -> dict:
        """Parse Claude response into structured summary."""
        parsed = {
            "summary": "",
            "why_it_matters": "",
            "action": "",
            "trend": ""
        }
        
        lines = content.split("\n")
        current_key = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith("SUMMARY:"):
                current_key = "summary"
                parsed["summary"] = line.replace("SUMMARY:", "").strip()
            elif line.startswith("WHY_IT_MATTERS:"):
                current_key = "why_it_matters"
                parsed["why_it_matters"] = line.replace("WHY_IT_MATTERS:", "").strip()
            elif line.startswith("ACTION:"):
                current_key = "action"
                parsed["action"] = line.replace("ACTION:", "").strip()
            elif line.startswith("TREND:"):
                current_key = "trend"
                parsed["trend"] = line.replace("TREND:", "").strip()
            elif current_key and line:
                # Continue previous value if it spans lines
                parsed[current_key] += " " + line
        
        # Fallback for missing fields
        if not parsed["summary"]:
            parsed["summary"] = "Breaking tech news story"
        if not parsed["trend"]:
            parsed["trend"] = "Technology"
        if not parsed["action"]:
            parsed["action"] = "Read the full story for details"
        if not parsed["why_it_matters"]:
            parsed["why_it_matters"] = "Relevant to tech industry"
        
        return parsed
    
    def _fallback_summary(self, story: Story, composite_score: float) -> Summary:
        """Create fallback summary when Claude fails."""
        # Extract first 100 chars as summary
        summary = (story.content or story.title)[:150].split('\n')[0]
        
        return Summary(
            story_id=story.id,
            title=story.title,
            summary=f"{summary}... (Read full story for details)",
            why_it_matters="Relevant to your tech interests",
            action="Read the full story to learn more",
            trend="Technology",
            source=story.source.value,
            url=story.url,
            composite_score=composite_score,
        )


class SummarizationManager:
    """Manage summarization of multiple stories."""
    
    def __init__(self):
        """Initialize manager."""
        self.summarizer = ClaudeSummarizer()
        
    async def summarize_stories(
        self, 
        ranked_stories: list[tuple[Story, float]],
        batch_size: int = 3
    ) -> list[Summary]:
        """Summarize multiple stories with rate limiting.
        
        Args:
            ranked_stories: List of (Story, composite_score) tuples
            batch_size: Number of parallel requests (API rate limit)
            
        Returns:
            List of Summary objects
        """
        await self.summarizer.initialize()
        
        try:
            summaries = []
            
            # Process in batches to respect rate limits
            for i in range(0, len(ranked_stories), batch_size):
                batch = ranked_stories[i:i + batch_size]
                batch_results = await asyncio.gather(
                    *[
                        self.summarizer.summarize(story, score)
                        for story, score in batch
                    ]
                )
                summaries.extend(batch_results)
                
                # Log progress
                logger.info(f"Summarized {len(summaries)}/{len(ranked_stories)} stories")
            
            return summaries
            
        finally:
            await self.summarizer.close()
    
    async def summarize_batch_with_retries(
        self,
        ranked_stories: list[tuple[Story, float]],
        max_retries: int = 2
    ) -> list[Summary]:
        """Summarize with retry logic for failed requests.
        
        Args:
            ranked_stories: List of (Story, composite_score) tuples
            max_retries: Number of retries for failed summaries
            
        Returns:
            List of Summary objects
        """
        summaries = []
        failed = []
        
        # First pass
        results = await self.summarize_stories(ranked_stories)
        
        # Check for fallback summaries (failed requests)
        for summary in results:
            if "Read full story" in summary.action:
                # This was a fallback, try again
                failed.append(summary)
            else:
                summaries.append(summary)
        
        # Retry failed
        if failed and max_retries > 0:
            logger.warning(f"Retrying {len(failed)} failed summaries...")
            # Find original stories for failed summaries
            retry_stories = [
                (s, score) for s, score in ranked_stories
                if s.id in [f.story_id for f in failed]
            ]
            
            # Retry with backoff
            await asyncio.sleep(2)
            retry_results = await self.summarize_stories(
                retry_stories,
                batch_size=1  # Slower for retries
            )
            summaries.extend(retry_results)
        
        return sorted(summaries, key=lambda s: s.composite_score, reverse=True)
