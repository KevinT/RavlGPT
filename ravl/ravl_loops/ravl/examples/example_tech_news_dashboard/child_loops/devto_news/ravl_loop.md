# Dev.to News Child Loop

Fetches and parses Dev.to RSS feed.

---

# Act

Fetch Dev.to RSS feed and extract articles.

## Data Source
- **Feed URL**: https://dev.to/feed
- **Format**: RSS/XML

## Required Data
Extract from each item:
- title
- link
- pubDate
- description
- categories/tags

## Output Format
```json
{
  "stories": [
    {
      "title": "Article title",
      "link": "https://dev.to/article",
      "pubDate": "2025-11-08T14:30:00Z",
      "description": "Article description",
      "tags": ["python", "tutorial"]
    }
  ],
  "metadata": {
    "source": "devto_news",
    "fetch_timestamp": "2025-11-08T14:35:00Z",
    "story_count": 25
  }
}
```

Save to: `output/news_{date}.json`

---

# Verify

- Output file exists
- JSON is valid
- Contains 15-30 articles
- All articles have title, link, pubDate
- At least 50% have tags

Pass if 90%+ checks succeed.
