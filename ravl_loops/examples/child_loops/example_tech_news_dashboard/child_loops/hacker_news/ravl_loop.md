# Hacker News Child Loop

Fetches and parses Hacker News RSS feed.

---

# Act

Fetch Hacker News RSS feed and extract stories.

## Data Source
- **Feed URL**: https://news.ycombinator.com/rss
- **Format**: RSS/XML

## Required Data
Extract from each item:
- title
- link
- pubDate
- description
- comments (if available)

## Output Format
```json
{
  "stories": [
    {
      "title": "Story title",
      "link": "https://example.com",
      "pubDate": "2025-11-08T14:30:00Z",
      "description": "Story description",
      "comments": "https://news.ycombinator.com/item?id=123"
    }
  ],
  "metadata": {
    "source": "hacker_news",
    "fetch_timestamp": "2025-11-08T14:35:00Z",
    "story_count": 30
  }
}
```

Save to: `output/news_{date}.json`

---

# Verify

- Output file exists
- JSON is valid
- Contains 15-30 stories
- All stories have title, link, pubDate
- No duplicate titles

Pass if 90%+ checks succeed.
