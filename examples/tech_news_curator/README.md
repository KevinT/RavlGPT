# Tech News Curator - Markdown RAVL Loop Example

A markdown-based RAVL loop that fetches Hacker News RSS and uses LLM to curate the best technical stories.

## What It Does

1. Fetches the Hacker News RSS feed (~30 latest stories)
2. Uses LLM to score each story on:
   - Technical depth (how substantial the technical content is)
   - Practical applicability (how useful it is to practicing engineers)
   - Novelty (how interesting or surprising it is)
3. Generates a one-sentence summary explaining why each story matters
4. Returns top 10 stories ranked by combined score
5. Learns over time what makes stories valuable

## What You'll Learn

### Markdown-Based Loops
- How to define loops in markdown (describe WHAT, not HOW)
- The framework's LLM generates Python code from your markdown
- No Python coding required - just describe your intent

### LLM-Powered Code Generation
- Framework reads `ravl_loop.md` and generates Python code
- Code is cached after successful verification
- Code regenerates automatically if failures occur (self-healing)
- See generated code in `learnings/execution_learning/dsl_iteration_*.json`

### Self-Healing Data Ingestion
- If RSS feed format changes, loop adapts automatically
- LLM analyzes errors and generates new code
- Failures become learning context for next run
- No manual intervention needed

### Dual Learning Architecture
- **Execution learning** (`execution_learning/`): How to fetch/parse RSS
- **Domain learning** (`loop_learning/`): What makes stories valuable
- These learning spaces are kept separate
- Both improve over multiple runs

### Code Caching
- Successful code is cached and reused
- Cache invalidates on verification failures
- Avoids LLM calls when code works
- Efficient and cost-effective

## Prerequisites

```bash
# Set your Anthropic API key (for LLM curation)
export ANTHROPIC_API_KEY="your-key-here"
```

No other setup needed - Hacker News RSS is public!

## How to Run

```bash
# From framework root
./ravl examples/tech_news_curator

# Or from example directory
cd docs/examples/tech_news_curator
python3 ../../../common/llm/run_markdown_ravl.py ravl_loop.md
```

## Expected Output

**First Run** (code generation):
```
🚀 Starting Tech News Curator Loop
================================================================================

================================================================================
 Step 1 of 4: [R]EFLECT
================================================================================

  ℹ️  No cached code found - will generate new code
  📚 Loading API documentation from Context7...
  🔍 Analyzing markdown specification...

================================================================================
 Step 2 of 4: [A]CT
================================================================================

🤖 Generating Python code from markdown specification...
✅ Code generated successfully
🏃 Executing generated code...

Fetching Hacker News RSS feed...
Parsing 30 stories...
Analyzing stories with LLM curator...
Scoring stories...
Ranking by combined score...

✅ Curated 10 stories
💾 Saved to: output/curated_news_2025-11-08.json

================================================================================
 Step 3 of 4: [V]ERIFY
================================================================================

🔍 Verification Results:
   ✅ Output file exists
   ✅ JSON is valid
   ✅ Contains 10 curated stories
   ✅ All stories have required fields
   ✅ All scores are valid (0-10 range)
   ✅ Stories sorted by total score
   ✅ 80% of stories have technical_depth >= 5
   ✅ 60% of stories have total score >= 18

All checks passed! ✅

================================================================================
 Step 4 of 4: [L]EARN
================================================================================

💾 Code cached to execution_learning/code_cache.json
📊 Updated domain model with story patterns
📈 Success rate: 100% (1/1 runs)

================================================================================
✅ Tech News Curator completed successfully
================================================================================
```

**Subsequent Runs** (cached code):
```
  ℹ️  Using cached code from previous successful run
  ⚡ Skipping code generation (cache hit)
```

## Output Example

```json
{
  "curated_stories": [
    {
      "title": "Show HN: I built a distributed database in Rust",
      "link": "https://example.com/my-db",
      "pubDate": "2025-11-08T10:30:00Z",
      "scores": {
        "technical_depth": 9,
        "practical_applicability": 7,
        "novelty": 8,
        "total": 24
      },
      "curator_summary": "Deep dive into consensus algorithms and zero-copy parsing with real-world benchmarks",
      "hn_comments": "https://news.ycombinator.com/item?id=12345"
    },
    {
      "title": "How We Reduced API Latency by 80% at Scale",
      "link": "https://example.com/latency",
      "pubDate": "2025-11-08T09:15:00Z",
      "scores": {
        "technical_depth": 7,
        "practical_applicability": 9,
        "novelty": 6,
        "total": 22
      },
      "curator_summary": "Practical patterns for caching, connection pooling, and async processing with code examples",
      "hn_comments": "https://news.ycombinator.com/item?id=12346"
    }
  ],
  "metadata": {
    "total_stories_analyzed": 30,
    "curation_timestamp": "2025-11-08T10:45:22Z",
    "feed_url": "https://news.ycombinator.com/rss"
  }
}
```

## File Structure

After running:

```
tech_news_curator/
├── ravl_loop.md                    # Markdown specification (what you write)
├── config/
│   ├── ravl.yml                   # Loop configuration
│   └── prompt_curation.md         # LLM curation prompt
├── learnings/
│   ├── execution_learning/        # How to fetch/parse RSS
│   │   ├── code_cache.json       # Cached working code
│   │   └── dsl_iteration_1.json  # Generated code history
│   └── loop_learning/             # What makes stories valuable
│       ├── model.yml             # Domain patterns learned
│       └── model-2025-11-08-104522.yml
└── output/
    └── curated_news_2025-11-08.json  # Curated stories
```

## Key Concepts

### 1. Markdown → Python Transformation

You write this in `ravl_loop.md`:
```markdown
# Act
Fetch RSS feed and extract title, link, pubDate from each story.
```

Framework generates Python code like:
```python
import feedparser
feed = feedparser.parse('https://news.ycombinator.com/rss')
stories = [{'title': e.title, 'link': e.link, 'pubDate': e.published} for e in feed.entries]
```

### 2. Self-Healing Example

**Scenario**: RSS feed adds a new required field `author`

- **Run N**: Code fails verification (missing author field)
- **Framework**: Analyzes error, invalidates cache
- **Run N+1**: LLM sees error, generates new code including author
- **Result**: Loop self-heals without manual intervention

### 3. Domain Learning Over Time

The loop learns patterns in `loop_learning/model.yml`:

```yaml
domain_patterns:
  high_quality_topics:
    - distributed_systems: 85% high scores
    - systems_programming: 80% high scores
    - machine_learning: 70% high scores
  low_quality_signals:
    - clickbait_titles: 90% low novelty scores
    - opinion_pieces: 60% low technical_depth
  curation_effectiveness:
    - false_positives: 15% (stories scored high but not interesting)
    - false_negatives: 10% (stories scored low but were good)
```

Over time, curation improves as patterns are learned.

### 4. Code Caching Benefits

| Run | Code Generated? | LLM Calls | Duration | Cost |
|-----|----------------|-----------|----------|------|
| 1   | ✅ Yes          | ~5        | 45s      | $0.10 |
| 2   | ❌ No (cached)  | 1 (curation only) | 8s | $0.02 |
| 3   | ❌ No (cached)  | 1         | 8s       | $0.02 |
| 4   | ✅ Yes (error)  | ~5        | 45s      | $0.10 |
| 5   | ❌ No (fixed)   | 1         | 8s       | $0.02 |

Caching makes loops fast and cost-effective.

## Customization Ideas

Modify the markdown to explore:

1. **Different RSS Feeds**: Change to Dev.to, Reddit, Medium
2. **Different Criteria**: Score for "controversy", "learning value", "career relevance"
3. **Filter by Topic**: Only include AI/ML stories, or exclude crypto
4. **Summarization**: Have LLM generate longer summaries
5. **Notification**: Email/Slack top stories daily

Remember: Just update the markdown, framework handles the code!

## Common Issues

### No curated stories returned
- Check ANTHROPIC_API_KEY is set
- Verify Hacker News RSS is accessible
- Check learnings/execution_learning/ for error details

### Code regenerates every run
- Verification might be failing
- Check learnings/execution_learning/failure_analysis.json
- Adjust verification criteria in markdown

### Low-quality curation
- Improve prompt_curation.md with better instructions
- Add examples of high/low quality stories
- Adjust scoring rubric

## Next Steps

Once you understand markdown loops:

1. **github_trending_tracker** - See Python class-based loops with API integration
2. **tech_news_dashboard** - Master delegation with parent/child coordination

## Further Reading

- `.ravl/docs/RAVL_PROTOCOL.md` - Understanding RAVL phases
- `.ravl/docs/RAVL_VISION.md` - Framework design principles
- `.ravl/common/execution/markdown/` - How markdown loops execute
