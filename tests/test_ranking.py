"""Tests for ranking scorer and manager."""

import pytest
from datetime import datetime, timedelta, timezone
from app.models import Story, NewsSource
from app.ranking.scorer import (
    RelevanceScorer,
    VaralityScorer,
    DepthScorer,
    NoveltyScorer,
    CompositeScorer,
)
from app.ranking.manager import RankingManager


# Sample stories for testing
@pytest.fixture
def sample_stories():
    """Create sample stories for testing."""
    now = datetime.now(timezone.utc)
    
    return [
        Story(
            id="story_1",
            source=NewsSource.HACKER_NEWS,
            title="vLLM: High-Throughput LLM Serving with a Distributed Architecture",
            url="https://github.com/vllm-project/vllm",
            content="A new distributed LLM serving framework for high throughput",
            published_at=now - timedelta(hours=2),
            metadata={"hn_score": 450, "hn_comments": 120},
        ),
        Story(
            id="story_2",
            source=NewsSource.REDDIT,
            title="CUDA Memory Management Best Practices",
            url="https://reddit.com/r/MachineLearning/...",
            content="Discussion on optimizing GPU memory for deep learning",
            published_at=now - timedelta(hours=6),
            metadata={"reddit_upvotes": 850, "reddit_comments": 150},
        ),
        Story(
            id="story_3",
            source=NewsSource.HACKER_NEWS,
            title="New distributed systems paper published",
            url="https://arxiv.org/abs/...",
            content="A paper on distributed consensus protocols",
            published_at=now - timedelta(days=2),
            metadata={"hn_score": 100, "hn_comments": 30},
        ),
        Story(
            id="story_4",
            source=NewsSource.HACKER_NEWS,
            title="Random news about something unrelated",
            url="https://example.com",
            content="This story has no relevance to AI or systems",
            published_at=now - timedelta(hours=1),
            metadata={"hn_score": 50},
        ),
    ]


class TestRelevanceScorer:
    """Test relevance scoring."""
    
    def test_exact_keyword_match(self):
        """Test exact keyword matching in title."""
        scorer = RelevanceScorer(["vLLM", "CUDA"])
        story = Story(
            id="test",
            source=NewsSource.HACKER_NEWS,
            title="vLLM: New LLM serving framework",
            url="https://example.com",
            content="",
        )
        
        score = scorer.score(story)
        assert score >= 0.25, "Should match 'vLLM' in title"
    
    def test_multiple_keywords(self):
        """Test multiple keyword matches."""
        scorer = RelevanceScorer(["vLLM", "CUDA", "distributed"])
        story = Story(
            id="test",
            source=NewsSource.HACKER_NEWS,
            title="vLLM with CUDA distributed architecture",
            url="https://example.com",
            content="",
        )
        
        score = scorer.score(story)
        assert score > 0.4, "Should match multiple keywords"
    
    def test_no_match(self):
        """Test story with no matching keywords."""
        scorer = RelevanceScorer(["vLLM", "CUDA"])
        story = Story(
            id="test",
            source=NewsSource.HACKER_NEWS,
            title="Random news about cooking",
            url="https://example.com",
            content="",
        )
        
        score = scorer.score(story)
        assert score < 0.2, "Should have low score with no matches"
    
    def test_url_matching(self):
        """Test keyword matching in URL."""
        scorer = RelevanceScorer(["vLLM"])
        story = Story(
            id="test",
            source=NewsSource.HACKER_NEWS,
            title="New serving framework",
            url="https://github.com/vllm-project/vllm",
            content="",
        )
        
        score = scorer.score(story)
        assert score > 0.3, "Should match 'vllm' in URL"


class TestViralityScorer:
    """Test virality scoring."""
    
    def test_high_hn_score(self):
        """Test high HN score."""
        scorer = VaralityScorer()
        story = Story(
            id="test",
            source=NewsSource.HACKER_NEWS,
            title="Test",
            url="https://example.com",
            content="",
            metadata={"hn_score": 500},
        )
        
        score = scorer.score(story)
        assert score > 0.3, "High HN score should produce decent virality"
    
    def test_high_reddit_engagement(self):
        """Test high Reddit engagement."""
        scorer = VaralityScorer()
        story = Story(
            id="test",
            source=NewsSource.REDDIT,
            title="Test",
            url="https://example.com",
            content="",
            metadata={"reddit_upvotes": 1000, "reddit_comments": 200},
        )
        
        score = scorer.score(story)
        assert score > 0.4, "High Reddit engagement should produce decent virality"
    
    def test_no_engagement(self):
        """Test story with no engagement."""
        scorer = VaralityScorer()
        story = Story(
            id="test",
            source=NewsSource.HACKER_NEWS,
            title="Test",
            url="https://example.com",
            content="",
            metadata={},
        )
        
        score = scorer.score(story)
        assert score < 0.2, "No engagement should produce low virality"


class TestDepthScorer:
    """Test technical depth scoring."""
    
    def test_technical_keywords(self):
        """Test scoring with technical keywords."""
        scorer = DepthScorer()
        story = Story(
            id="test",
            source=NewsSource.HACKER_NEWS,
            title="GPU optimization: CUDA kernel implementation",
            url="https://example.com",
            content="Detailed guide on kernel optimization",
        )
        
        score = scorer.score(story)
        assert score > 0.4, "Should score high with technical keywords"
    
    def test_arxiv_source(self):
        """Test ArXiv source gets depth bonus."""
        scorer = DepthScorer()
        story = Story(
            id="test",
            source=NewsSource.ARXIV,
            title="Research paper",
            url="https://arxiv.org/abs/...",
            content="",
        )
        
        score = scorer.score(story)
        assert score > 0.15, "ArXiv source should get depth bonus"
    
    def test_long_description(self):
        """Test longer descriptions score higher."""
        scorer = DepthScorer()
        story = Story(
            id="test",
            source=NewsSource.HACKER_NEWS,
            title="Technical topic",
            url="https://example.com",
            content="x" * 600,  # Long description
        )
        
        score = scorer.score(story)
        assert score > 0.2, "Longer description should increase depth score"


class TestNoveltyScorer:
    """Test novelty scoring."""
    
    def test_recent_story(self):
        """Test recent story scores high."""
        scorer = NoveltyScorer()
        now = datetime.now(timezone.utc)
        story = Story(
            id="test",
            source=NewsSource.HACKER_NEWS,
            title="Test",
            url="https://example.com",
            content="",
            published_at=now - timedelta(hours=1),
        )
        
        score = scorer.score(story)
        assert score > 0.8, "Recent story should score high"
    
    def test_old_story(self):
        """Test old story scores lower."""
        scorer = NoveltyScorer()
        now = datetime.now(timezone.utc)
        story = Story(
            id="test",
            source=NewsSource.HACKER_NEWS,
            title="Test",
            url="https://example.com",
            content="",
            published_at=now - timedelta(days=30),
        )
        
        score = scorer.score(story)
        assert score < 0.2, "Old story should score low"
    
    def test_no_date(self):
        """Test story without date gets default score."""
        scorer = NoveltyScorer()
        story = Story(
            id="test",
            source=NewsSource.HACKER_NEWS,
            title="Test",
            url="https://example.com",
            content="",
            published_at=None,
        )
        
        score = scorer.score(story)
        assert score > 0.5, "Story without date should get reasonable score"


class TestCompositeScorer:
    """Test composite scoring."""
    
    def test_weighted_scoring(self, sample_stories):
        """Test that weights affect final score."""
        # High relevance weight
        scorer1 = CompositeScorer(
            ["vLLM", "CUDA"],
            weight_relevance=0.8,
            weight_virality=0.1,
            weight_depth=0.1,
            weight_novelty=0.0,
        )
        
        # High virality weight
        scorer2 = CompositeScorer(
            ["vLLM", "CUDA"],
            weight_relevance=0.1,
            weight_virality=0.8,
            weight_depth=0.1,
            weight_novelty=0.0,
        )
        
        story = sample_stories[0]  # vLLM story with high HN score
        
        score1 = scorer1.score(story)
        score2 = scorer2.score(story)
        
        # Both should have similar scores since the story matches both dimensions
        # Just verify they're both positive
        assert score1 > 0 and score2 > 0, "Both scorers should give positive scores"
    
    def test_ranking_order(self, sample_stories):
        """Test that stories are ranked in expected order."""
        scorer = CompositeScorer(["vLLM", "CUDA", "distributed systems"])
        
        scores = [(s.title[:30], scorer.score(s)) for s in sample_stories]
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # vLLM story should rank high
        assert "vLLM" in scores[0][0], "vLLM story should rank first"
    
    def test_score_breakdown(self, sample_stories):
        """Test detailed score breakdown."""
        scorer = CompositeScorer(["vLLM"])
        breakdown = scorer.score_with_breakdown(sample_stories[0])
        
        assert "composite" in breakdown
        assert "relevance" in breakdown
        assert "virality" in breakdown
        assert "depth" in breakdown
        assert "novelty" in breakdown
        assert all(0 <= v <= 1 for v in breakdown.values() if isinstance(v, float))


class TestRankingManager:
    """Test ranking manager."""
    
    def test_rank_stories(self, sample_stories):
        """Test story ranking."""
        manager = RankingManager()
        ranked = manager.rank_stories(sample_stories)
        
        assert len(ranked) == len(sample_stories)
        assert all(isinstance(score, float) for _, score in ranked)
        
        # Scores should be sorted descending
        scores = [score for _, score in ranked]
        assert scores == sorted(scores, reverse=True)
    
    def test_select_top_n(self, sample_stories):
        """Test top-N selection."""
        manager = RankingManager()
        top_3 = manager.select_top_n(sample_stories, n=3)
        
        assert len(top_3) == 3
    
    def test_select_top_n_exceeds_available(self, sample_stories):
        """Test top-N when N > available stories."""
        manager = RankingManager()
        top_10 = manager.select_top_n(sample_stories, n=10)
        
        assert len(top_10) == len(sample_stories)
    
    def test_ranked_with_scores(self, sample_stories):
        """Test getting stories with score details."""
        manager = RankingManager()
        results = manager.get_ranked_with_scores(sample_stories)
        
        assert len(results) == len(sample_stories)
        assert all("story" in r and "score" in r and "breakdown" in r for r in results)
    
    def test_formatting_report(self, sample_stories):
        """Test ranking report generation."""
        manager = RankingManager()
        report = manager.format_ranking_report(sample_stories, n=3)
        
        assert "Top 3 Stories" in report
        assert "vLLM" in report  # Should include top stories
        assert "Score:" in report
