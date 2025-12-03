# Tech News Dashboard - Parent/Child Delegation Example

An advanced RAVL example demonstrating parent/child delegation. The parent orchestrates 3 child loops to create a comprehensive tech news dashboard with meta-insights.

## What It Does

**Parent Loop** (`example_tech_news_dashboard`):
- Coordinates 3 child loops to fetch news from different sources
- Aggregates results from all children
- Generates meta-insights across sources
- Identifies cross-platform trends
- Ranks stories by source diversity and quality

**Child Loops** (run automatically by parent):
- `hacker_news` - Fetches Hacker News RSS
- `devto_news` - Fetches Dev.to RSS
- `reddit_programming` - Fetches Reddit r/programming RSS

## What You'll Learn

### Parent/Child Delegation Pattern
- How parent loops coordinate multiple children
- Using `run_child` directives in markdown
- Sequential vs parallel child execution
- Parent reading child outputs (read-anywhere pattern)

### Real-Time Output Streaming
- Watch each child execute in real-time
- See progress as children fetch and process data
- Monitor success/failure of each child
- Understand subprocess coordination

### Hierarchical Learning
- **Children learn**: Source-specific patterns (feed formats, timing, reliability)
- **Parent learns**: Cross-source patterns (topic correlation, source quality, aggregation strategies)
- Learning flows: Children → Parent (bottom-up intelligence)

### Meta-Synthesis
- Parent generates insights children cannot
- Cross-source topic identification
- Trend detection across platforms
- Source quality scoring
- Diversity-based ranking

### Fault Tolerance
- Parent handles child failures gracefully
- Continues with successful children
- Learns from partial failures
- Adaptive strategy selection

## Prerequisites

```bash
# Set your Anthropic API key (for LLM synthesis)
export ANTHROPIC_API_KEY="your-key-here"
```

No other setup - all RSS feeds are public!

## How to Run

### Run Complete Dashboard (Parent + All Children)

```bash
# From framework root
./ravl examples/example_tech_news_dashboard
```

This executes:
1. Parent REFLECT phase
2. Child 1 (hacker_news) - full RAVL cycle
3. Child 2 (devto_news) - full RAVL cycle
4. Child 3 (reddit_programming) - full RAVL cycle
5. Parent ACT phase (aggregation + meta-synthesis)
6. Parent VERIFY phase
7. Parent LEARN phase

### Run Individual Children

```bash
# Run just Hacker News child
./ravl examples/example_tech_news_dashboard/hacker_news

# Run just Dev.to child
./ravl examples/example_tech_news_dashboard/devto_news

# Run just Reddit child
./ravl examples/example_tech_news_dashboard/reddit_programming
```

## Expected Output

```
🚀 Starting Tech News Dashboard
================================================================================

================================================================================
 Step 1 of 4: [R]EFLECT
================================================================================

  ℹ️  Loading parent model...
  📊 Previous orchestration runs: 0

================================================================================
 Step 2 of 4: [A]CT
================================================================================

🔄 Executing child loop: hacker_news
────────────────────────────────────────────────────────────────────────────────
🚀 Starting Hacker News Child Loop
Fetching https://news.ycombinator.com/rss...
✅ Fetched 30 stories
💾 Saved to: output/news_2025-11-08.json
✅ Hacker News Child Loop completed successfully
────────────────────────────────────────────────────────────────────────────────

🔄 Executing child loop: devto_news
────────────────────────────────────────────────────────────────────────────────
🚀 Starting Dev.to News Child Loop
Fetching https://dev.to/feed...
✅ Fetched 25 articles
💾 Saved to: output/news_2025-11-08.json
✅ Dev.to News Child Loop completed successfully
────────────────────────────────────────────────────────────────────────────────

🔄 Executing child loop: reddit_programming
────────────────────────────────────────────────────────────────────────────────
🚀 Starting Reddit Programming Child Loop
Fetching https://www.reddit.com/r/programming/.rss...
✅ Fetched 28 posts
💾 Saved to: output/news_2025-11-08.json
✅ Reddit Programming Child Loop completed successfully
────────────────────────────────────────────────────────────────────────────────

🤖 Aggregating results from 3 children...
📊 Total stories collected: 83
🧠 Generating meta-insights with LLM...

✅ Identified 12 cross-source topics
✅ Detected 3 emerging trends
✅ Ranked top 10 stories by source diversity

💾 Saved dashboard to: output/dashboard_2025-11-08.json

================================================================================
 Step 3 of 4: [V]ERIFY
================================================================================

🔍 Verification Results:
   ✅ All 3 children executed successfully
   ✅ Combined story count: 83 (>= 50)
   ✅ Meta-insights generated
   ✅ Cross-source topics: 12 (>= 3)
   ✅ Top stories ranked: 10
   ✅ All diversity scores valid (0-1 range)

✅ All checks passed!

================================================================================
 Step 4 of 4: [L]EARN
================================================================================

📈 Orchestration Learnings:
   Child success rate: 100% (3/3)
   Average stories per child: 27.7
   Cross-source topic overlap: 42%

💾 Model saved to learnings/loop_learning/

================================================================================
✅ Tech News Dashboard completed successfully
================================================================================
```

## Output Example

`output/dashboard_2025-11-08.json`:

```json
{
  "meta_insights": {
    "cross_source_topics": [
      {
        "topic": "AI Agents & Multi-Agent Systems",
        "sources": ["hacker_news", "devto_news", "reddit_programming"],
        "story_count": 8,
        "trend": "rising",
        "keywords": ["agents", "openai", "swarm", "orchestration"]
      },
      {
        "topic": "Rust System Programming",
        "sources": ["hacker_news", "reddit_programming"],
        "story_count": 5,
        "trend": "stable",
        "keywords": ["rust", "performance", "systems"]
      }
    ],
    "source_quality_today": {
      "hacker_news": {
        "avg_score": 7.8,
        "story_count": 30,
        "best_for": ["systems", "deep-tech", "research"]
      },
      "devto_news": {
        "avg_score": 6.5,
        "story_count": 25,
        "best_for": ["tutorials", "web-dev", "beginners"]
      },
      "reddit_programming": {
        "avg_score": 7.2,
        "story_count": 28,
        "best_for": ["discussion", "opinions", "community"]
      }
    },
    "emerging_trends": ["multi-agent systems", "local-first software", "ai code generation"],
    "declining_trends": ["blockchain", "web3", "metaverse"]
  },
  "top_stories_aggregated": [
    {
      "title": "Show HN: Open Source Multi-Agent Framework",
      "sources": ["hacker_news", "reddit_programming"],
      "aggregate_score": 26,
      "source_diversity": 0.67,
      "trend_momentum": "rising",
      "recommended_rank": 1,
      "why_top": "High technical depth, appearing on multiple platforms, rising trend"
    }
  ],
  "child_run_summary": {
    "hacker_news": {"status": "success", "stories_fetched": 30, "duration_sec": 8.2},
    "devto_news": {"status": "success", "stories_fetched": 25, "duration_sec": 6.8},
    "reddit_programming": {"status": "success", "stories_fetched": 28, "duration_sec": 7.5}
  },
  "metadata": {
    "dashboard_timestamp": "2025-11-08T15:00:00Z",
    "total_stories_analyzed": 83,
    "orchestration_duration_sec": 45.3
  }
}
```

## File Structure

```
example_tech_news_dashboard/
├── ravl_loop.md                          # Parent orchestrator spec
├── config/
│   └── ravl.toml                         # Parent configuration
├── ravl_loops/                          # Children
│   ├── hacker_news/
│   │   ├── ravl_loop.md                # Child 1 spec
│   │   ├── config/ravl.toml             # Child 1 config
│   │   ├── learnings/loop_learning/    # Child 1 learnings
│   │   └── output/news_*.json          # Child 1 output
│   ├── devto_news/
│   │   ├── ravl_loop.md                # Child 2 spec
│   │   ├── config/ravl.toml             # Child 2 config
│   │   ├── learnings/loop_learning/    # Child 2 learnings
│   │   └── output/news_*.json          # Child 2 output
│   └── reddit_programming/
│       ├── ravl_loop.md                # Child 3 spec
│       ├── config/ravl.toml             # Child 3 config
│       ├── learnings/loop_learning/    # Child 3 learnings
│       └── output/news_*.json          # Child 3 output
├── learnings/
│   └── loop_learning/                   # Parent learnings (orchestration patterns)
│       ├── model.yml
│       └── model-2025-11-08-150022.yml
└── output/
    └── dashboard_2025-11-08.json       # Aggregated dashboard
```

## Key Concepts

### 1. Delegation Pattern

Parent uses `run_child` directives:

```markdown
# Act

```run_child
hacker_news
```

```run_child
devto_news
```
```

Framework automatically:
- Locates child loop in `ravl_loops/hacker_news/`
- Executes child's full RAVL cycle
- Streams child output in real-time
- Captures child's result for parent

### 2. Read-Anywhere Pattern

Children don't know about parent. Parent reads child outputs:

```python
# Parent reads child outputs
hn_data = json.load(open('ravl_loops/hacker_news/output/news_*.json'))
devto_data = json.load(open('ravl_loops/devto_news/output/news_*.json'))
reddit_data = json.load(open('ravl_loops/reddit_programming/output/news_*.json'))

# Parent synthesizes
meta_insights = synthesize_across_sources(hn_data, devto_data, reddit_data)
```

### 3. Hierarchical Learning

**Children learn** (in `ravl_loops/*/learnings/loop_learning/model.yml`):
- Source-specific patterns
- Feed format quirks
- Optimal fetch timing
- Reliability patterns

**Parent learns** (in `learnings/loop_learning/model.yml`):
```yaml
orchestration_patterns:
  child_reliability:
    hacker_news: 0.95
    devto_news: 0.92
    reddit_programming: 0.88
  cross_source_topics:
    frequently_shared: ["AI", "systems", "web-dev"]
    source_specific: {"rust": ["hacker_news", "reddit"]}
  optimal_aggregation:
    weight_by_quality: true
    source_diversity_threshold: 0.5
```

### 4. Fault Tolerance

If a child fails:

```
🔄 Executing child loop: devto_news
❌ Dev.to News Child Loop failed (network timeout)

🤖 Aggregating results from 2 successful children...
⚠️  Reduced dataset - proceeding with partial results
```

Parent continues with successful children, tracks failure patterns.

### 5. Meta-Synthesis Example

Children report individual stories. Parent synthesizes:

- **Hacker News**: Story A about "AI Agents" (score: 8)
- **Reddit**: Story B about "Multi-Agent Systems" (score: 7)
- **Dev.to**: Story C about "Agent Orchestration" (score: 6)

**Parent synthesis**:
```json
{
  "cross_source_topics": [{
    "topic": "AI Agents & Multi-Agent Systems",
    "sources": ["hacker_news", "reddit_programming", "devto_news"],
    "story_count": 3,
    "trend": "rising",
    "aggregate_score": 21
  }]
}
```

Parent identifies this is the SAME topic across 3 sources → high importance signal.

## Customization Ideas

### Add More Children
Create new child loop in `ravl_loops/`:
```bash
cp -r ravl_loops/hacker_news ravl_loops/lobsters
# Edit ravl_loops/lobsters/ravl_loop.md
# Add `run_child lobsters` to parent
```

### Different Aggregation Strategies
Modify parent's Act phase:
- Weight by source reliability
- Filter by topic categories
- Time-based trending (recent vs evergreen)
- Sentiment analysis

### Alert on Patterns
Add to parent Learn phase:
- Email/Slack if emerging trend detected
- Alert if topic appears on all 3 sources
- Notify if source reliability drops

### Visualization
Generate charts from parent output:
- Topic frequency over time
- Source quality trends
- Cross-source correlation matrix

## Common Issues

### Children not executing
- Verify child paths: `ravl_loops/<child_name>/ravl_loop.md`
- Check child config files exist
- Ensure ANTHROPIC_API_KEY is set

### Parent can't read child outputs
- Children must save to `output/` directory
- Parent looks for `output/news_*.json` pattern
- Check file permissions

### Meta-synthesis fails
- Verify child outputs have consistent format
- Check parent has enough data (50+ stories minimum)
- Ensure LLM synthesis prompt is clear

## Comparison with Simpler Examples

| Feature | hello_ravl | example_tech_news_curator | example_github_trending_tracker | example_tech_news_dashboard |
|---------|-----------|------------------|------------------------|---------------------|
| Loops | 1 | 1 | 1 | 4 (1 parent + 3 children) |
| Delegation | No | No | No | Yes |
| Real-time streaming | No | No | No | Yes (children) |
| API calls | 0 | 1 (RSS) | 1 (GitHub) | 3 (RSS feeds) |
| Meta-synthesis | No | No | No | Yes (cross-source) |
| Hierarchical learning | No | No | No | Yes |
| Complexity | Minimal | Low | Medium | High |

## Next Steps

1. **Run the dashboard** and watch children execute in real-time
2. **Read parent learnings** in `learnings/loop_learning/model.yml`
3. **Read child learnings** in each `ravl_loops/*/learnings/loop_learning/model.yml`
4. **Compare outputs** across multiple runs to see pattern evolution
5. **Experiment** with adding/removing children
6. **Modify aggregation** logic in parent's Act phase

## Further Reading

- `.ravl/docs/RAVL_PROTOCOL.md` - Coordination patterns
- `.ravl/templates/strategic_coherence_template/` - Another delegation example
- Project `ravl_loops/clickup_intelligence/` - Real-world orchestrator loop
