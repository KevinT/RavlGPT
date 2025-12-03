# Tech News Curator - Markdown RAVL Loop

A markdown-based RAVL loop that fetches Hacker News RSS feed and uses LLM to curate the best stories.

**Learning Objectives:**
- See how markdown loops work (describe WHAT, not HOW)
- Watch LLM generate Python code from natural language
- Understand self-healing (handles feed format changes automatically)
- Learn how code caching works (reuses verified code)
- See domain learning (what makes stories valuable)

---

# Act

Fetch the Hacker News RSS feed and curate the best technology stories.

## Data Source

- **Feed URL**: https://news.ycombinator.com/rss
- **Format**: RSS/XML feed
- **Update frequency**: Continuous (check latest ~30 stories)

## Required Data

Extract these fields from each story:
- title (story headline)
- link (URL to story or discussion)
- pubDate (publication timestamp)
- description (story summary/first comment)
- comments (HN comments link if available)

## Processing Steps

1. Fetch RSS feed from Hacker News
2. Parse XML to extract story data
3. Use LLM to analyze and curate stories:
   - Score each story for technical depth (0-10)
   - Score for practical applicability (0-10)
   - Score for novelty/interest (0-10)
   - Generate 1-sentence summary explaining value
4. Rank stories by combined score
5. Return top 10 stories with scores and summaries

## Output Format

```json
{
  "curated_stories": [
    {
      "title": "Story headline",
      "link": "https://example.com/story",
      "pubDate": "2025-11-08T14:30:00Z",
      "scores": {
        "technical_depth": 8,
        "practical_applicability": 7,
        "novelty": 9,
        "total": 24
      },
      "curator_summary": "Why this story matters in one sentence",
      "hn_comments": "https://news.ycombinator.com/item?id=12345"
    }
  ],
  "metadata": {
    "total_stories_analyzed": 30,
    "curation_timestamp": "2025-11-08T14:35:22Z",
    "feed_url": "https://news.ycombinator.com/rss"
  }
}
```

Save output to: `output/curated_news_{date}.json`

---

# Verify

Validate the curated news output:

## Required Checks

- Output file exists at `output/curated_news_{today}.json`
- JSON is valid and parseable
- `curated_stories` list contains 5-10 items (quality over quantity)
- All stories have required fields: title, link, scores, curator_summary
- All technical_depth scores are 0-10 (no invalid scores)
- All practical_applicability scores are 0-10
- All novelty scores are 0-10
- All curator_summary fields are non-empty strings
- Stories are sorted by total score (descending)
- metadata.total_stories_analyzed >= 10 (feed had data)

## Quality Thresholds

- At least 50% of curated stories have total score >= 18 (high quality bar)
- At least 80% of curated stories have technical_depth >= 5 (technical focus)
- No duplicate story titles (deduplication works)

**Pass if 90%+ of checks succeed.**

---

# Learn

In addition to framework learning (code caching, failure patterns), track domain patterns:

## What to Learn

- **Story Quality Patterns**: What characteristics correlate with high scores?
  - Track topics that consistently score well (AI/ML, systems programming, etc.)
  - Track sources that produce high-quality content
  - Learn what "technical depth" means in practice

- **Feed Behavior**: How does HN RSS behave?
  - Typical number of stories in feed
  - Update frequency patterns
  - Whether certain times have better content

- **Curation Effectiveness**: Is the LLM curation useful?
  - Track whether top-scored stories are genuinely interesting
  - Learn if scoring criteria need adjustment
  - Identify false positives (low-value stories scored high)

Store learnings in model.yml under `domain_patterns` section.

---

## Notes

This example demonstrates:

1. **Markdown Simplicity**: You describe WHAT you want, LLM figures out HOW
2. **LLM Code Generation**: Framework generates Python code from this markdown
3. **Self-Healing**: If RSS format changes, LLM adapts code automatically
4. **Code Caching**: Successful code is cached and reused until failure
5. **Domain Learning**: Loop learns what makes stories valuable over time
6. **Dual Learning Spaces**:
   - Execution learning: How to parse RSS, call LLM, handle errors
   - Domain learning: What makes tech news valuable

Run this daily to get curated tech news. Over time, curation improves as the loop learns your interests.
