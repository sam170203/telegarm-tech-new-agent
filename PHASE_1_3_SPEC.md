# PHASE 1.3 SPECIFICATION
## Ranking Engine

**Estimated Time**: 3-4 hours
**Complexity**: High (algorithms, tuning)
**Deliverable**: RankingEngine with 4-factor composite scoring

---

## Overview

Right now you have:
- ✓ 180 unique stories from HN + Reddit
- ✗ No way to pick the top 10 that matter most to you

Phase 1.3 will:
1. Score each story on 4 dimensions
2. Combine into composite ranking
3. Return top 10-12 stories
4. Make it tunable via .env

---

## The 4 Scoring Factors

### 1. RELEVANCE (40% weight)

**Goal**: Match your interests (vLLM, CUDA, distributed systems, etc.)

**Algorithm**: TF-IDF-like keyword matching

```python
interests = [
    "vLLM", "CUDA", "distributed systems", "agentic AI",
    "robotics", "ML infrastructure", "reasoning models",
    "edge AI", "MCP", "RAG", "Tinygrad", "open-source"
]

def relevance_score(story: Story) -> float:
    # Search title + content for interest keywords
    # Boost matches in title (more important)
    # Normalize by story length (longer ≠ more relevant)
    # Result: 0.0-1.0
    pass
```

**Example**:
- "vLLM reaches 1M tokens/second" → 0.95 (perfect match)
- "New CUDA optimization for ML" → 0.85 (matches 2 terms)
- "Python 3.9 release notes" → 0.1 (no interest keywords)

### 2. VIRALITY (30% weight)

**Goal**: Stories people are talking about

**Algorithm**: Normalize source scores to 0-1 scale

```python
def virality_score(story: Story) -> float:
    # HN: normalize score to 0-1 (typical max ~500)
    # Reddit: normalize upvotes + comments
    # Combine as average
    # Result: 0.0-1.0
    pass
```

**Example**:
- HN story with 450 points → ~0.9 (engagement)
- Reddit post with 1000 upvotes, 200 comments → ~0.95
- Low engagement story → 0.3

### 3. DEPTH (20% weight)

**Goal**: Technical substance vs. fluff

**Algorithm**: Presence of technical markers

```python
def depth_score(story: Story) -> float:
    # Check for:
    # - Code snippets (``` in content)
    # - Papers (arxiv.org, doi.org, pdf)
    # - Benchmarks (data, metrics, numbers)
    # - Systems content (distributed, concurrent, etc.)
    # Result: 0.0-1.0
    pass
```

**Example**:
- "vLLM implementation guide with code" → 0.9
- "Research paper on transformers" → 0.95
- "Look at this cool startup" → 0.4

### 4. NOVELTY (10% weight)

**Goal**: Fresh news > old news

**Algorithm**: Time-based decay

```python
def novelty_score(story: Story) -> float:
    # Published today → 1.0
    # Published 1 day ago → 0.9
    # Published 7 days ago → 0.1
    # Older → 0.0
    # Result: 0.0-1.0
    pass
```

**Example**:
- News from today → 1.0
- News from 2 days ago → 0.7
- News from 1 week ago → 0.0

---

## Composite Score

```python
def composite_score(story: Story) -> float:
    r = relevance_score(story)    # 0-1
    v = virality_score(story)      # 0-1
    d = depth_score(story)         # 0-1
    n = novelty_score(story)       # 0-1

    weights = {
        'relevance': 0.4,
        'virality': 0.3,
        'depth': 0.2,
        'novelty': 0.1,
    }

    score = (
        weights['relevance'] * r +
        weights['virality'] * v +
        weights['depth'] * d +
        weights['novelty'] * n
    )

    return score  # 0-1
```

**Tunable via .env**:
```bash
RANK_WEIGHT_RELEVANCE=0.4
RANK_WEIGHT_VIRALITY=0.3
RANK_WEIGHT_DEPTH=0.2
RANK_WEIGHT_NOVELTY=0.1
```

---

## Implementation Plan

### File Structure

```
app/ranking/
├── __init__.py
├── scorer.py          ← Individual scoring functions
├── engine.py          ← RankingEngine orchestrator
└── keywords.py        ← Interest keywords + config
```

### Module: `app/ranking/scorer.py`

```python
class RelevanceScorer:
    """TF-IDF keyword matching."""
    def __init__(self, interests: List[str]):
        pass
    
    def score(self, story: Story) -> float:
        """0-1 relevance score."""
        pass

class ViralityScorer:
    """Normalize engagement across sources."""
    def score(self, story: Story) -> float:
        """0-1 virality score."""
        pass

class DepthScorer:
    """Detect technical substance."""
    def score(self, story: Story) -> float:
        """0-1 depth score."""
        pass

class NoveltyScorer:
    """Time-based decay."""
    def score(self, story: Story) -> float:
        """0-1 novelty score."""
        pass
```

### Module: `app/ranking/engine.py`

```python
class RankingEngine:
    """Orchestrate all scoring and return ranked stories."""
    
    def __init__(self, settings: Settings):
        self.relevance = RelevanceScorer(...)
        self.virality = ViralityScorer()
        self.depth = DepthScorer()
        self.novelty = NoveltyScorer()
        self.weights = settings.rank_weights
    
    def rank(self, stories: List[Story]) -> List[RankedStory]:
        """Score and rank stories.
        
        Args:
            stories: List of stories to rank
            
        Returns:
            List[RankedStory] sorted by score (highest first)
        """
        ranked = []
        for story in stories:
            score = self._composite_score(story)
            ranked.append(RankedStory(
                story=story,
                relevance_score=...,
                virality_score=...,
                depth_score=...,
                novelty_score=...,
                composite_score=score,
            ))
        
        return sorted(ranked, key=lambda x: x.composite_score, reverse=True)
    
    def get_top_stories(self, stories: List[Story], n: int = 10) -> List[RankedStory]:
        """Get top N stories."""
        ranked = self.rank(stories)
        return ranked[:n]
```

### Data Model: `RankedStory`

Add to `app/models.py`:

```python
@dataclass
class RankedStory:
    """Story with ranking scores."""
    story: Story
    relevance_score: float      # 0-1
    virality_score: float       # 0-1
    depth_score: float          # 0-1
    novelty_score: float        # 0-1
    composite_score: float      # 0-1 (weighted sum)
    rank: int = 0               # 1-indexed position
```

---

## Testing Strategy

### Unit Tests (`tests/test_ranking.py`)

```python
class TestRelevanceScorer:
    def test_exact_interest_match(self):
        """vLLM title → high score"""
        pass
    
    def test_multiple_keywords(self):
        """Multiple matches boost score"""
        pass
    
    def test_no_match(self):
        """Unrelated story → low score"""
        pass

class TestViralityScorer:
    def test_high_engagement(self):
        """High score/upvotes → high score"""
        pass
    
    def test_low_engagement(self):
        """Low engagement → low score"""
        pass
    
    def test_source_normalization(self):
        """HN and Reddit scores comparable"""
        pass

class TestDepthScorer:
    def test_detects_code(self):
        """Code snippets boost score"""
        pass
    
    def test_detects_papers(self):
        """Research papers boost score"""
        pass
    
    def test_detects_benchmarks(self):
        """Numbers/metrics boost score"""
        pass

class TestNoveltyScorer:
    def test_today_max_score(self):
        """Today's news → 1.0"""
        pass
    
    def test_week_old_low_score(self):
        """Week-old news → low score"""
        pass

class TestRankingEngine:
    def test_rank_returns_sorted(self):
        """Results sorted by composite score"""
        pass
    
    def test_get_top_n(self):
        """Returns exactly N top stories"""
        pass
    
    def test_composite_score_calculation(self):
        """Weights applied correctly"""
        pass
```

### Integration Test

```python
async def test_full_pipeline():
    """Fetch → Deduplicate → Rank → Select top 10"""
    # Fetch from all sources
    manager = NewsManager(dao)
    await manager.fetch_all()
    
    # Get stories from DB
    stories = dao.get_latest_stories(limit=200)
    
    # Rank
    engine = RankingEngine(settings)
    top_10 = engine.get_top_stories(stories, n=10)
    
    # Verify
    assert len(top_10) == 10
    assert all(s.relevance_score > 0 for s in top_10)
    assert top_10[0].composite_score >= top_10[1].composite_score
    
    # Show results
    for i, ranked in enumerate(top_10, 1):
        print(f"{i}. {ranked.story.title}")
        print(f"   Score: {ranked.composite_score:.2f}")
        print(f"   Relevance: {ranked.relevance_score:.2f}")
        print(f"   Virality: {ranked.virality_score:.2f}")
        print(f"   Depth: {ranked.depth_score:.2f}")
        print(f"   Novelty: {ranked.novelty_score:.2f}")
```

---

## Known Challenges & Solutions

### Challenge 1: Tuning Weights

The default weights (0.4, 0.3, 0.2, 0.1) are suggestions. You might want:
- Higher relevance (0.5) if you care only about your interests
- Higher virality (0.5) if you want what's trending
- Higher depth (0.4) if you want technical substance

**Solution**: Make weights configurable in .env. Let data guide tuning.

### Challenge 2: Keyword Matching

Simple substring matching ("CUDA" in title) is fragile.

**Solution**:
- Case-insensitive matching
- Partial matching (CUDA matches cuda, CUDA, Cuda)
- Synonym expansion later (GPT = LLM, GPU = CUDA)

### Challenge 3: Novelty vs. Quality

Old stories might be high-quality. New stories might be noise.

**Solution**:
- Novelty weight is only 10% (secondary)
- Quality (relevance + depth + virality) is 90%

### Challenge 4: Source-Specific Signals

Reddit upvotes aren't comparable to HN points.

**Solution**:
- Normalize each source independently
- HN: score / typical_max (e.g., /500)
- Reddit: (upvotes + comments*0.1) / typical_max

---

## Files to Create/Modify

### New Files
- `app/ranking/scorer.py` (300 lines)
- `app/ranking/engine.py` (150 lines)
- `app/ranking/keywords.py` (50 lines)
- `tests/test_ranking.py` (300 lines)

### Modified Files
- `app/models.py` - Add RankedStory dataclass
- `app/config/settings.py` - Add rank weights
- `.env.example` - Add rank weight configs

---

## Success Criteria

After Phase 1.3:

- [ ] Can fetch 200+ stories
- [ ] Can rank them on 4 dimensions
- [ ] Top 10 ranked stories feel relevant to your interests
- [ ] Can tune weights in .env
- [ ] All tests passing
- [ ] Documentation updated

---

## What You'll Be Able To Do

```python
from app.ranking.engine import RankingEngine
from app.sources.manager import NewsManager

# Fetch
manager = NewsManager(dao)
await manager.fetch_all()  # 250 stories

# Rank
engine = RankingEngine(settings)
stories = dao.get_latest_stories(limit=250)
top_10 = engine.get_top_stories(stories, n=10)

# Result: 10 personalized, ranked, AI-focused stories
for ranked_story in top_10:
    print(f"{ranked_story.story.title} (score: {ranked_story.composite_score:.2f})")
```

---

## Ready?

When you say "yes", I'll build:

1. Scoring functions (relevance, virality, depth, novelty)
2. RankingEngine orchestrator
3. 30+ tests covering all scenarios
4. Demo showing top 10 ranked stories
5. Tuning guide (how to adjust weights)

Should take 3-4 hours start to finish.
