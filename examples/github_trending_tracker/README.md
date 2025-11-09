# GitHub Trending Tracker - Python RAVL Loop with API Integration

A Python-based RAVL loop that tracks GitHub trending repositories and learns patterns over time.

## What It Does

1. Fetches recently created repositories with high stars (trending proxy)
2. Extracts repository data (stars, language, topics, description)
3. Analyzes trending patterns (languages, topics, star counts)
4. Tracks API health and success rates
5. Learns trending patterns using exponential moving average
6. Persists learnings across runs

No GitHub authentication required - uses public API with 60 requests/hour limit.

## What You'll Learn

### API Integration Patterns
- How to integrate external APIs in RAVL loops
- Handling API errors and rate limits gracefully
- Timeout and retry strategies
- Response validation and error recovery

### Self-Healing Data Ingestion
- Detecting and handling rate limit errors (403 responses)
- Graceful degradation when APIs fail
- Verification-driven retry logic
- Error classification (rate_limit, api_error, data_quality)

### Dual Learning Architecture
- **Execution learning**: API strategies, error patterns, optimal request timing
- **Domain learning**: Trending patterns, language popularity, topic evolution
- Exponential moving average (70% history, 30% current)
- Pattern tracking across multiple runs

### Data Quality Verification
- Multiple verification layers (API success, data completeness, minimum thresholds)
- Quantitative quality checks (90%+ complete records)
- Graceful failure handling
- Verification results inform learning

## How to Run

```bash
# From framework root
./ravl examples/github_trending_tracker

# Or directly
cd examples/github_trending_tracker
python3 ravl_loop.py
```

**No setup required** - uses public GitHub API!

## Expected Output

```
🚀 Starting GitHub Trending Tracker
================================================================================

================================================================================
 Step 1 of 4: [R]EFLECT
================================================================================

  ℹ️  GitHub Trending Tracker: No existing model found, initializing new model

📊 Previous Learnings:
   Total runs: 0
   Top trending topics: []
   API success rate: 0.0%

💡 First run - establishing baseline trending patterns

================================================================================
 Step 2 of 4: [A]CT
================================================================================

🔍 Fetching trending repos from GitHub...
   Query: created after 2025-11-01, sorted by stars

✅ Fetched 30 trending repositories

📊 Trending Analysis:
   Top languages: ['Python', 'TypeScript', 'Rust', 'Go', 'JavaScript']
   Top topics: ['machine-learning', 'ai', 'cli', 'api', 'framework']
   Avg stars: 1245

💾 Saved to: output/trending_2025-11-08.json

================================================================================
 Step 3 of 4: [V]ERIFY
================================================================================

🔍 Verification Results:
   ✅ no_api_errors
   ✅ has_repositories
   ✅ min_repos_fetched
   ✅ has_analysis
   ✅ data_completeness

✅ All checks passed!

================================================================================
 Step 4 of 4: [L]EARN
================================================================================

📈 Updated Learnings:
   Total runs: 1
   Success rate: 100.0%
   Learned topics: 15

💾 Model saved to learnings/loop_learning/

================================================================================
✅ GitHub Trending Tracker completed successfully
================================================================================
```

## Output Example

```json
{
  "repositories": [
    {
      "name": "openai/swarm",
      "description": "Educational framework for multi-agent orchestration",
      "stars": 15234,
      "forks": 892,
      "language": "Python",
      "topics": ["ai", "agents", "framework", "openai"],
      "created_at": "2025-11-01T10:30:00Z",
      "url": "https://github.com/openai/swarm"
    },
    ...
  ],
  "analysis": {
    "languages": {
      "Python": 12,
      "TypeScript": 8,
      "Rust": 5,
      "Go": 3,
      "JavaScript": 2
    },
    "topics": {
      "ai": 18,
      "machine-learning": 14,
      "cli": 8,
      "api": 6,
      "framework": 5
    },
    "avg_stars": 1245,
    "total_repos": 30
  },
  "metadata": {
    "fetch_timestamp": "2025-11-08T14:45:22Z",
    "query_date": "2025-11-01",
    "total_repos": 30
  }
}
```

## Learned Model Example

After multiple runs, `learnings/loop_learning/model.yml`:

```yaml
statistics:
  total_runs: 10
  successful_runs: 9
  failed_runs: 1  # One rate limit error

api_health:
  success_rate: 0.9
  last_response_code: 200

trending_patterns:
  top_languages:
    Python: 45
    TypeScript: 32
    Rust: 28
    Go: 15
    JavaScript: 12
  top_topics:
    ai: 67
    machine-learning: 54
    cli: 34
    api: 28
    framework: 25
  avg_stars_trend:
    - 1245
    - 1189
    - 1567
    - 1423
    - 1334
    - 1298
    - 1445
    - 1512
    - 1389
    - 1467

last_run_timestamp: "2025-11-08T14:45:22Z"
```

## File Structure

```
github_trending_tracker/
├── ravl_loop.py                    # Loop implementation (read this!)
├── config/
│   └── ravl.yml                   # Configuration
├── learnings/
│   └── loop_learning/             # Trending patterns learned
│       ├── model.yml             # Current model
│       └── model-2025-11-08-144522.yml  # Timestamped snapshot
└── output/
    └── trending_2025-11-08.json  # Daily trending data
```

## Key Concepts

### 1. API Integration Pattern

The loop demonstrates clean API integration:

```python
# Fetch data
response = requests.get(url, params=params, timeout=10)

# Handle rate limits
if response.status_code == 403:
    return {'error': 'rate_limit_exceeded', 'repositories': []}

# Validate response
response.raise_for_status()
data = response.json()
```

### 2. Self-Healing Example

**Scenario**: Hit GitHub rate limit (60 requests/hour)

- **Run N**: Gets 403 response, returns `rate_limit_exceeded` error
- **Verification**: Fails (`no_api_errors` check fails)
- **Learning**: Model tracks failure, `success_rate` drops to 0.9
- **Run N+1** (after hour passes): Succeeds, `success_rate` recovers

No manual intervention needed - loop tracks health and recovers automatically.

### 3. Exponential Moving Average Learning

Trending patterns use EMA (70% history, 30% current):

```python
# Run 1: Python appears 12 times
top_languages = {'Python': 12}

# Run 2: Python appears 10 times
# Updated: 12 * 0.7 + 10 * 0.3 = 8.4 + 3 = 11.4 ≈ 11
top_languages = {'Python': 11}

# Run 3: Python appears 15 times
# Updated: 11 * 0.7 + 15 * 0.3 = 7.7 + 4.5 = 12.2 ≈ 12
top_languages = {'Python': 12}
```

This smooths short-term fluctuations, reveals long-term trends.

### 4. Verification Hierarchy

Multiple verification layers ensure data quality:

1. **API Level**: No errors, successful response code
2. **Data Level**: Has repositories, minimum count met
3. **Quality Level**: 90%+ records have complete data
4. **Analysis Level**: Analysis object present

All must pass for run to be considered successful.

## Customization Ideas

Modify the loop to explore:

1. **Different Queries**: Track specific languages, topics, or organizations
2. **Deeper Analysis**: Analyze commit frequency, contributor counts, issue activity
3. **Trend Detection**: Alert when sudden spikes occur
4. **Visualization**: Generate charts of language/topic trends
5. **Recommendations**: Suggest repos to star based on learned preferences

## Common Issues

### Rate Limit Exceeded (403)
- GitHub allows 60 requests/hour unauthenticated
- Loop handles this gracefully (returns error, doesn't crash)
- Wait an hour or add GitHub token for 5000 requests/hour:
  ```bash
  export GITHUB_TOKEN="your-token-here"
  # Modify loop to use auth header
  ```

### No Trending Repos Found
- Adjust date range (more than 7 days ago)
- Lower star threshold (change `stars:>100` to `stars:>50`)
- Check internet connection

### Verification Failing
- Check `learnings/loop_learning/model.yml` for error patterns
- Verify GitHub API is accessible
- Adjust verification thresholds in `verify()` method

## Next Steps

Once you understand API integration:

1. **tech_news_dashboard** - See delegation with multiple API sources
2. Read the code in `ravl_loop.py` - it's heavily commented
3. Experiment with different GitHub queries
4. Add your own verification checks

## Comparison with hello_ravl

| Feature | hello_ravl | github_trending_tracker |
|---------|-----------|------------------------|
| Complexity | Minimal | Intermediate |
| External API | No | Yes (GitHub) |
| Error Handling | Basic | Rate limits, timeouts, API errors |
| Learning | Run statistics | Trending patterns with EMA |
| Verification | File exists | Multi-layer (API + data quality) |
| Self-Healing | No | Yes (rate limit recovery) |

## Further Reading

- `.ravl/docs/RAVL_PROTOCOL.md` - RAVL phases deep dive
- `.ravl/docs/RAVL_VISION.md` - Framework design principles
- GitHub API docs: https://docs.github.com/en/rest
