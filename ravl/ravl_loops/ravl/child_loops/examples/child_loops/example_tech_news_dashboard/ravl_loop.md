# Tech News Dashboard - Delegation Example

This is a **parent orchestrator loop** that coordinates three child loops to create a comprehensive tech news dashboard.

**Learning Objectives:**
- Understand parent/child delegation patterns
- See how orchestrator loops coordinate children
- Learn how parent synthesizes insights from multiple sources
- Master hierarchical learning (children → parent)
- Watch real-time output streaming as children execute

---

# Architecture

```
tech_news_dashboard/ (PARENT)
├── ravl_loops/
│   ├── hacker_news/ (CHILD 1) - Fetches HN RSS
│   ├── devto_news/ (CHILD 2) - Fetches Dev.to RSS
│   └── reddit_programming/ (CHILD 3) - Fetches Reddit RSS
```

Parent reads all child outputs and generates meta-insights.

---

# Act

## Step 1: Run Child Loops

Execute all three child loops to fetch news from their respective sources:

```run_child
hacker_news
```

```run_child
devto_news
```

```run_child
reddit_programming
```

## Step 2: Aggregate Child Outputs

Read outputs from all children:
- `ravl_loops/hacker_news/output/news_*.json`
- `ravl_loops/devto_news/output/news_*.json`
- `ravl_loops/reddit_programming/output/news_*.json`

## Step 3: Synthesize Meta-Insights

Analyze aggregated news to identify:

### Cross-Source Patterns
- Topics appearing in multiple sources (signals importance)
- Stories gaining traction across platforms
- Emerging trends (new topics appearing)
- Declining trends (topics fading away)

### Source Quality Analysis
- Which source had highest quality stories today?
- Which topics are each source best for?
- Reliability patterns per source

### Meta-Recommendations
Generate top 10 stories across all sources with:
- Source diversity score (coverage across platforms)
- Trend momentum (increasing vs declining attention)
- Technical depth aggregate (average across sources)
- Recommended reading order

## Output Format

```json
{
  "meta_insights": {
    "cross_source_topics": [
      {
        "topic": "AI Agents",
        "sources": ["hacker_news", "devto_news", "reddit_programming"],
        "story_count": 8,
        "trend": "rising"
      }
    ],
    "source_quality_today": {
      "hacker_news": {"avg_score": 7.8, "story_count": 30},
      "devto_news": {"avg_score": 6.5, "story_count": 25},
      "reddit_programming": {"avg_score": 7.2, "story_count": 28}
    },
    "emerging_trends": ["multi-agent systems", "local-first software"],
    "declining_trends": ["blockchain", "web3"]
  },
  "top_stories_aggregated": [
    {
      "title": "Story title",
      "sources": ["hacker_news", "reddit"],
      "aggregate_score": 24,
      "source_diversity": 0.67,
      "trend_momentum": "rising",
      "recommended_rank": 1
    }
  ],
  "child_run_summary": {
    "hacker_news": {"status": "success", "stories_fetched": 30},
    "devto_news": {"status": "success", "stories_fetched": 25},
    "reddit_programming": {"status": "success", "stories_fetched": 28}
  },
  "metadata": {
    "dashboard_timestamp": "2025-11-08T15:00:00Z",
    "total_stories_analyzed": 83
  }
}
```

Save to: `output/dashboard_{date}.json`

---

# Verify

Validate the aggregated dashboard:

## Child Execution Checks
- All 3 children executed successfully
- Each child produced output file
- Each child's output is valid JSON
- Combined story count >= 50 (reasonable data volume)

## Aggregation Quality
- `meta_insights` object present and complete
- `cross_source_topics` has at least 3 topics
- `top_stories_aggregated` has 10 stories
- All stories have `source_diversity` score (0-1 range)
- All trend indicators are valid ("rising", "stable", "declining")

## Meta-Analysis Quality
- At least one emerging trend identified
- Source quality scores are reasonable (0-10 range)
- Recommended ranks are unique (no duplicates)

**Pass if 90%+ of checks succeed.**

---

# Learn

In addition to framework learning, track orchestration patterns:

## Orchestration Effectiveness
- How often do children all succeed vs some fail?
- Optimal child execution order (if dependencies exist)
- Whether parallel execution causes issues

## Cross-Source Intelligence
- Which topic combinations are most valuable?
- Source correlation patterns (sources that agree/disagree)
- Best time of day for each source

## Meta-Learning Quality
- Are cross-source insights actually useful?
- Is source diversity a good quality signal?
- Do emerging/declining trend predictions hold?

Store in model.yml under `orchestration_patterns`.

---

## Notes

This example demonstrates:

1. **Delegation Pattern**: Parent coordinates multiple children
2. **Subprocess Execution**: Uses `run_child` directives
3. **Real-Time Streaming**: Watch children execute in real-time
4. **Hierarchical Learning**: Children learn sources, parent learns meta-patterns
5. **Read-Anywhere Pattern**: Parent reads child outputs (children don't know about parent)
6. **Meta-Synthesis**: Parent generates insights children cannot

**To run:**
```bash
./ravl examples/tech_news_dashboard
```

This will:
1. Execute hacker_news child (you'll see its output live)
2. Execute devto_news child (you'll see its output live)
3. Execute reddit_programming child (you'll see its output live)
4. Aggregate results and generate meta-insights
5. Learn both child patterns and orchestration patterns

Children can be run independently:
```bash
./ravl examples/tech_news_dashboard/hacker_news
```

Over time, the dashboard learns:
- Which sources are most reliable
- Which topics are trending across platforms
- Optimal aggregation strategies
- Quality prediction models
