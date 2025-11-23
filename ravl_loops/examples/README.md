# RAVL Framework Examples

Progressive examples demonstrating the RAVL framework from simple to advanced.

## Learning Path

These examples are designed to be studied in order, building from basic concepts to advanced patterns:

1. **example_3_analysis_loop** - Simplest markdown loop (5 min)
2. **example_4_learning_loop** - Understanding learning (15 min)
3. **example_tech_news_curator** - Data ingestion patterns (15 min)
4. **example_github_trending_tracker** - API integration in Python (20 min)
5. **example_communication_learner** - Multi-dimensional optimization (25 min)
6. **example_tech_news_dashboard** - Advanced orchestration (30 min)

---

## 1. Rugby Tips - Your First Loop

**Path**: `example_3_analysis_loop/`
**Type**: Markdown
**Level**: Beginner
**Time**: 5 minutes
**Prerequisites**: ANTHROPIC_API_KEY

### What You'll Learn
- How markdown loops work (describe WHAT, not HOW)
- Framework generates Python code from your description
- Basic RAVL phases (Reflect → Act → Verify → Learn)
- File-based outputs

### What It Does
Tracks Springbok rugby game results, analyzes player performance, and generates coaching tips for Rassie (the coach). Stores results in JSON and creates markdown coaching tips.

### Run It
```bash
export ANTHROPIC_API_KEY="your-key"
./ravl example_3_analysis_loop
```

### Key Concepts
- Markdown loop structure
- Simple Act phase (data gathering + analysis)
- File-based persistence
- Conditional outputs (only generate tips if new games found)

---

## 2. Simple Learning Loop - Environment Explorer

**Path**: `example_4_learning_loop/`
**Type**: Markdown
**Level**: Beginner
**Time**: 15 minutes
**Prerequisites**: ANTHROPIC_API_KEY

### What You'll Learn
- How loops evolve across multiple runs
- Strategic learning (not just data collection)
- Knowledge persistence and accumulation
- Progressive sophistication

### What It Does
Starts with zero knowledge and explores its environment. Each run decides what to explore next based on previous learning. Builds a knowledge map that gets strategically smarter over time.

### Run It
```bash
export ANTHROPIC_API_KEY="your-key"
./ravl example_4_learning_loop
./ravl example_4_learning_loop  # Run multiple times to see learning!
./ravl example_4_learning_loop
```

### Key Concepts
- Learning accumulation across runs
- Strategic exploration (not random)
- Model-driven decision making
- Evolution from naive to sophisticated

**Important**: Run this example 3-5 times to see how it learns and evolves!

---

## 3. Tech News Curator - Data Ingestion

**Path**: `example_tech_news_curator/`
**Type**: Markdown
**Level**: Intermediate
**Time**: 15 minutes
**Prerequisites**: ANTHROPIC_API_KEY

### What You'll Learn
- Self-healing data ingestion (handles format changes)
- LLM-powered content scoring
- Code caching (reuses verified code)
- Dual learning spaces (execution + domain)

### What It Does
Fetches Hacker News RSS, uses LLM to score stories by technical depth, practical applicability, and novelty. Returns top 10 curated stories.

### Run It
```bash
export ANTHROPIC_API_KEY="your-key"
./ravl example_tech_news_curator
```

### Key Concepts
- Markdown → Python code generation
- Self-healing RSS parsing
- Dual learning spaces:
  - Execution learning: How to parse RSS
  - Domain learning: What makes good content
- LLM synthesis for curation

---

## 4. GitHub Trending Tracker - API Integration

**Path**: `example_github_trending_tracker/`
**Type**: Python
**Level**: Intermediate
**Time**: 20 minutes
**Prerequisites**: None (uses public GitHub API)

### What You'll Learn
- API integration patterns in RAVL
- Handling rate limits and API errors gracefully
- Exponential moving average for pattern learning
- Multi-layer verification (API + data quality)
- Python loop structure

### What It Does
Tracks GitHub trending repositories (recently created, high stars). Analyzes trending patterns in languages, topics, and stars. Learns patterns using 70/30 exponential moving average.

### Run It
```bash
./ravl example_github_trending_tracker
```

### Key Concepts
- Clean API integration (timeout, error handling, rate limits)
- Self-healing recovery from 403 errors
- EMA learning (70% history + 30% current)
- Hierarchical verification layers
- Data quality thresholds
- Python class-based loop implementation

---

## 5. Communication Learner - Multi-Dimensional Optimization

**Path**: `example_communication_learner/`
**Type**: Markdown
**Level**: Advanced
**Time**: 25 minutes
**Prerequisites**: ANTHROPIC_API_KEY, Understanding of example_2

### What You'll Learn
- Multi-dimensional optimization (4 scoring dimensions)
- Exploration vs exploitation tradeoffs
- Strategic hypothesis formation and testing
- Plateau detection and breaking
- Meta-learning (learning how to learn better)

### What It Does
Discovers effective communication strategies through experimentation. Optimizes across clarity, engagement, completeness, and memorability. Forms hypotheses, tests them, and learns from results.

### Run It
```bash
export ANTHROPIC_API_KEY="your-key"
./ravl example_communication_learner
./ravl example_communication_learner  # Run 5-10 times to see evolution!
```

### Key Concepts
- Multi-dimensional optimization vs pass/fail
- Exploration vs exploitation balance
- Hypothesis-driven learning
- Pattern recognition across dimensions
- Sophisticated meta-strategy evolution

**Important**: Run 5-10 times to watch strategy evolution from exploration to exploitation!

---

## 6. Tech News Dashboard - Orchestration

**Path**: `example_tech_news_dashboard/`
**Type**: Parent + 3 Children (Markdown)
**Level**: Advanced
**Time**: 30 minutes
**Prerequisites**: ANTHROPIC_API_KEY

### What You'll Learn
- Parent/child delegation patterns
- Orchestrator loops coordinating multiple children
- Real-time output streaming (watch children execute)
- Hierarchical learning (children → parent synthesis)
- Meta-insight generation across sources
- Fault-tolerant coordination

### What It Does
**Parent** orchestrates 3 children to fetch news from:
- Hacker News RSS
- Dev.to RSS
- Reddit r/programming RSS

Parent aggregates results, identifies cross-source topics, detects emerging trends, ranks stories by source diversity.

### Run It
```bash
export ANTHROPIC_API_KEY="your-key"
./ravl example_tech_news_dashboard
```

### Key Concepts
- `run_child` directives in markdown
- Read-anywhere pattern (parent reads children, children don't know parent)
- Subprocess coordination with real-time output
- Hierarchical learning layers:
  - Children: Source-specific patterns
  - Parent: Cross-source meta-patterns
- Graceful child failure handling

---

## Quick Comparison

| Example | Type | Loops | External APIs | Learning Complexity | Time |
|---------|------|-------|---------------|-------------------|------|
| rugby_tips | Markdown | 1 | 0 | Basic | 5 min |
| simple_learning_loop | Markdown | 1 | 0 | Strategic | 15 min |
| example_tech_news_curator | Markdown | 1 | 1 (RSS) | Dual-space | 15 min |
| example_github_trending_tracker | Python | 1 | 1 (GitHub) | EMA patterns | 20 min |
| example_communication_learner | Markdown | 1 | 0 | Multi-dimensional | 25 min |
| example_tech_news_dashboard | Markdown | 4 (1+3) | 3 (RSS feeds) | Hierarchical | 30 min |

---

## Python vs Markdown Loops

### Use Python When:
- Complex logic or algorithms required
- Need fine-grained control over execution
- Performance is critical
- Building production systems
- Want to use mixins for shared functionality

**Example**: example_github_trending_tracker

### Use Markdown When:
- Primarily data ingestion or LLM analysis
- Want framework to handle implementation
- Rapid prototyping
- Self-healing is more important than control
- Non-programmers building loops

**Examples**: rugby_tips, simple_learning_loop, example_tech_news_curator, example_communication_learner, example_tech_news_dashboard

---

## Common Patterns

### 1. RAVL Protocol
All loops follow the four phases:

```python
reflection = loop.reflect()          # Phase 1: Observe
action = loop.act(reflection)        # Phase 2: Execute
verification = loop.verify(...)      # Phase 3: Check
loop.learn(verification, action)     # Phase 4: Improve
```

### 2. Model Persistence

```yaml
# learnings/loop_learning/model.yml
statistics:
  total_runs: 10
  successful_runs: 9
  success_rate: 0.9
patterns:
  learned_topic_preferences: ["AI", "systems", "rust"]
  quality_indicators: ["technical_depth > 7", "multiple_sources"]
```

Models automatically save with timestamps: `model-2025-11-08-143022.yml`

### 3. Dual Learning Spaces

**Execution Learning** (`learnings/execution_learning/`):
- How to make the framework work
- Code generation strategies
- DSL convergence patterns
- Error recovery strategies

**Domain Learning** (`learnings/loop_learning/`):
- What the loop learns about its domain
- Business patterns and insights
- Quality metrics
- Trend patterns

These spaces never mix - clean separation of concerns.

### 4. Verification as Learning Signal

```python
verification = {
    'passed': True,
    'checks': {
        'data_quality': 0.95,
        'completeness': 0.98,
        'format_valid': True
    }
}

# Learn phase uses this to update model
if verification['passed']:
    model['success_patterns'].append(action['strategy'])
else:
    model['failure_patterns'].append(action['strategy'])
```

---

## Running Examples

### From Framework Root

```bash
# Simple markdown starter (requires ANTHROPIC_API_KEY)
./ravl example_3_analysis_loop

# Learning evolution demo (requires ANTHROPIC_API_KEY, run multiple times!)
./ravl example_4_learning_loop

# Markdown loop with RSS (requires ANTHROPIC_API_KEY)
./ravl example_tech_news_curator

# API integration (Python)
./ravl example_github_trending_tracker

# Advanced learning (requires ANTHROPIC_API_KEY, run 5-10 times!)
./ravl example_communication_learner

# Orchestration (requires ANTHROPIC_API_KEY)
./ravl example_tech_news_dashboard
```

**Note**: Framework auto-strips `example_N_` prefix when running, so you can also use:
```bash
./ravl rugby_tips
./ravl simple_learning_loop
```

---

## File Structure Pattern

All examples follow this structure:

```
example_name/
├── ravl_loop.{py|md}              # Loop implementation
├── config/
│   └── ravl.yml                   # Loop metadata
├── learnings/
│   ├── execution_learning/        # How to execute (markdown loops)
│   └── loop_learning/             # What was learned (all loops)
│       ├── model.yml             # Current model
│       └── model-{timestamp}.yml # Historical snapshots
├── output/                        # Generated outputs
└── README.md                      # Documentation (some examples)
```

Orchestration examples add:
```
parent_loop/
├── ravl_loops/                    # Children
│   ├── child1/
│   ├── child2/
│   └── child3/
```

---

## Next Steps

### After Examples

1. **Explore Templates**: See `templates/` for production-ready loop templates
2. **Read Framework Docs**:
   - [RAVL_PROTOCOL.md](../docs/RAVL_PROTOCOL.md) - Deep dive into phases
   - [RAVL_VISION.md](../docs/RAVL_VISION.md) - Design principles
   - [CHANGELOG.md](../CHANGELOG.md) - Feature history
3. **Real-World Loops**: Check project's `ravl_loops/` for production examples (if any)
4. **Build Your Own**: Start with an example as template

### Creating Your Loop

```bash
# Option 1: Clone an example (simplest)
./ravl --clone example_3_analysis_loop ravl_loops/my_markdown_loop

# Option 2: Clone learning example
./ravl --clone example_4_learning_loop ravl_loops/my_learner

# Option 3: Use framework templates
./ravl --clone empty_loop_template ravl_loops/my_loop

# Edit and run
vim ravl_loops/my_loop/ravl_loop.md  # or .py
./ravl my_loop
```

---

## Learning Resources

- **Visual Learner?** Watch the real-time output as loops execute
- **Code Learner?** Read `example_github_trending_tracker/ravl_loop.py` - Python implementation
- **Markdown Learner?** Read `example_3_analysis_loop/ravl_loop.md` - plain language specs
- **Concept Learner?** Read example READMEs for detailed explanations
- **Hands-On Learner?** Modify examples and see what breaks

---

## Troubleshooting

### ANTHROPIC_API_KEY not set
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Required for: rugby_tips, simple_learning_loop, example_tech_news_curator, example_communication_learner, example_tech_news_dashboard

### GitHub rate limit (403)
GitHub allows 60 requests/hour without auth. Wait an hour or add token:
```bash
export GITHUB_TOKEN="ghp_..."
```

### Code generation fails
- Check internet connection (markdown loops need LLM access)
- Verify ANTHROPIC_API_KEY is valid
- Check `learnings/execution_learning/` for error details

### Children not executing (dashboard)
- Verify child paths exist: `ravl_loops/{child}/ravl_loop.md`
- Check child config files
- Ensure parent can read child outputs

---

## Questions?

- Check individual example READMEs for detailed docs (where available)
- Review framework documentation in `docs/`
- Look at production loops in project's `ravl_loops/` (if any)
- Read RAVL protocol specification: [RAVL_PROTOCOL.md](../docs/RAVL_PROTOCOL.md)
