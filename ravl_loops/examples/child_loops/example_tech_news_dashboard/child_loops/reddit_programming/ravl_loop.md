# Reddit Programming Child Loop

Fetches and parses Reddit r/programming RSS feed.

---

# Act

Fetch Reddit programming RSS feed and extract posts.

## Data Source
- **Feed URL**: https://www.reddit.com/r/programming/.rss
- **Format**: RSS/XML

## Required Data
Extract from each item:
- title
- link
- pubDate
- description (post content/snippet)
- comments (Reddit comments link)

## Output Format
```json
{
  "stories": [
    {
      "title": "Post title",
      "link": "https://example.com",
      "pubDate": "2025-11-08T14:30:00Z",
      "description": "Post content snippet",
      "comments": "https://reddit.com/r/programming/comments/xyz"
    }
  ],
  "metadata": {
    "source": "reddit_programming",
    "fetch_timestamp": "2025-11-08T14:35:00Z",
    "story_count": 28
  }
}
```

Save to: `output/news_{date}.json`

---

# Verify

- Output file exists
- JSON is valid
- Contains 15-30 posts
- All posts have title, link, pubDate
- Comments links are valid Reddit URLs

Pass if 90%+ checks succeed.
