# RAVL Framework Examples

Progressive examples demonstrating the RAVL framework from simple to advanced.

## Learning Path

These examples are designed to be studied in order, building from basic concepts to advanced patterns:

1. **hello_ravl_py** & **hello_ravl_md** - Learn the basics (5 min each)
2. **tech_news_curator** - Understand markdown loops (15 min)
3. **github_trending_tracker** - Master API integration (20 min)
4. **tech_news_dashboard** - Advanced delegation (30 min)

---

## 1. Hello RAVL - Your First Loop (Python & Markdown)

The absolute simplest RAVL loops - same behavior, two implementations!

### 1a. Hello RAVL (Python)

**Path**: `hello_ravl_py/`
**Type**: Python class-based
**Level**: Beginner
**Time**: 5 minutes

#### What You'll Learn
- The four RAVL phases (Reflect → Act → Verify → Learn)
- How Python loops are structured
- Model persistence with timestamps
- Basic verification patterns

#### Run It
```bash
./ravl examples/hello_ravl_py
```

[Read full documentation →](hello_ravl_py/README.md)

### 1b. Hello RAVL (Markdown)

**Path**: `hello_ravl_md/`
**Type**: Markdown with code generation
**Level**: Beginner
**Time**: 5 minutes
**Prerequisites**: ANTHROPIC_API_KEY

#### What You'll Learn
- How markdown loops work (describe WHAT, not HOW)
- Framework generates Python code from your description
- Code caching (reuses successful code)
- Compare: ~200 lines Python vs ~60 lines markdown!

#### Run It
```bash
export ANTHROPIC_API_KEY="your-key"
./ravl examples/hello_ravl_md
```

[Read full documentation →](hello_ravl_md/README.md)

### Key Concepts (Both)
- RAVL protocol basics
- Model loading/saving
- Verification as learning signal
- Statistical tracking

**Start with Python version** to understand structure, then **try Markdown version** to see framework magic!

---

## 2. Tech News Curator - Markdown Loops

**Path**: `tech_news_curator/`
**Type**: Markdown
**Level**: Intermediate
**Time**: 15 minutes
**Prerequisites**: ANTHROPIC_API_KEY

### What You'll Learn
- Markdown-based loop definitions (describe WHAT, not HOW)
- LLM-powered code generation from natural language
- Self-healing data ingestion (handles format changes)
- Code caching (reuses verified code)
- Domain learning (what makes content valuable)

### What It Does
Fetches Hacker News RSS, uses LLM to score stories by technical depth, practical applicability, and novelty. Returns top 10 curated stories.

### Run It
```bash
export ANTHROPIC_API_KEY="your-key"
./ravl examples/tech_news_curator
```

### Key Concepts
- Markdown → Python code generation
- Self-healing RSS parsing
- Dual learning spaces:
  - Execution learning: How to parse RSS
  - Domain learning: What makes good content
- LLM synthesis for curation

[Read full documentation →](tech_news_curator/README.md)

---

## 3. GitHub Trending Tracker - API Integration

**Path**: `github_trending_tracker/`
**Type**: Python
**Level**: Intermediate
**Time**: 20 minutes
**Prerequisites**: None (uses public GitHub API)

### What You'll Learn
- API integration patterns in RAVL
- Handling rate limits and API errors gracefully
- Exponential moving average for pattern learning
- Multi-layer verification (API + data quality)
- Execution vs domain learning separation

### What It Does
Tracks GitHub trending repositories (recently created, high stars). Analyzes trending patterns in languages, topics, and stars. Learns patterns using 70/30 exponential moving average.

### Run It
```bash
./ravl examples/github_trending_tracker
```

### Key Concepts
- Clean API integration (timeout, error handling, rate limits)
- Self-healing recovery from 403 errors
- EMA learning (70% history + 30% current)
- Hierarchical verification layers
- Data quality thresholds

[Read full documentation →](github_trending_tracker/README.md)

---

## 4. Tech News Dashboard - Delegation

**Path**: `tech_news_dashboard/`
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
./ravl examples/tech_news_dashboard
```

### Key Concepts
- `run_child` directives in markdown
- Read-anywhere pattern (parent reads children, children don't know parent)
- Subprocess coordination with real-time output
- Hierarchical learning layers:
  - Children: Source-specific patterns
  - Parent: Cross-source meta-patterns
- Graceful child failure handling

[Read full documentation →](tech_news_dashboard/README.md)

---

## Quick Comparison

| Example | Type | Loops | External APIs | Learning Spaces | Complexity |
|---------|------|-------|---------------|-----------------|------------|
| hello_ravl_py | Python | 1 | 0 | 1 (domain) | Minimal |
| hello_ravl_md | Markdown | 1 | 0 | 2 (execution + domain) | Minimal |
| tech_news_curator | Markdown | 1 | 1 (RSS) | 2 (execution + domain) | Low |
| github_trending_tracker | Python | 1 | 1 (GitHub) | 2 (execution + domain) | Medium |
| tech_news_dashboard | Markdown | 4 (1+3) | 3 (RSS feeds) | 2×4 (hierarchical) | High |

---

## Python vs Markdown Loops

### Use Python When:
- Complex logic or algorithms required
- Need fine-grained control over execution
- Performance is critical
- Building production systems
- Want to use mixins for shared functionality

**Examples**: hello_ravl_py, github_trending_tracker

### Use Markdown When:
- Primarily data ingestion or LLM analysis
- Want framework to handle implementation
- Rapid prototyping
- Self-healing is more important than control
- Non-programmers building loops

**Examples**: hello_ravl_md, tech_news_curator, tech_news_dashboard

---

## Key Framework Features Demonstrated

### Across All Examples

| Feature | hello_py | hello_md | curator | tracker | dashboard |
|---------|----------|----------|---------|---------|-----------|
| **Core RAVL** | | | | | |
| Reflect phase | ✅ | ✅ | ✅ | ✅ | ✅ |
| Act phase | ✅ | ✅ | ✅ | ✅ | ✅ |
| Verify phase | ✅ | ✅ | ✅ | ✅ | ✅ |
| Learn phase | ✅ | ✅ | ✅ | ✅ | ✅ |
| Model persistence | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Advanced** | | | | | |
| Markdown loops | - | ✅ | ✅ | - | ✅ |
| Python loops | ✅ | - | - | ✅ | - |
| LLM code generation | - | ✅ | ✅ | - | ✅ |
| Self-healing | - | ✅ | ✅ | ✅ | ✅ |
| API integration | - | - | ✅ | ✅ | ✅ |
| Code caching | - | ✅ | ✅ | - | ✅ |
| **Learning** | | | | | |
| Domain learning | ✅ | ✅ | ✅ | ✅ | ✅ |
| Execution learning | - | ✅ | ✅ | ✅ | ✅ |
| Hierarchical learning | - | - | - | - | ✅ |
| EMA pattern tracking | - | - | - | ✅ | - |
| **Orchestration** | | | | | |
| Delegation | - | - | - | - | ✅ |
| Real-time streaming | - | - | - | - | ✅ |
| Meta-synthesis | - | - | - | - | ✅ |

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
# Simple Python starter
./ravl examples/hello_ravl_py

# Simple markdown starter (requires ANTHROPIC_API_KEY)
./ravl examples/hello_ravl_md

# Markdown loop with RSS (requires ANTHROPIC_API_KEY)
./ravl examples/tech_news_curator

# API integration
./ravl examples/github_trending_tracker

# Orchestration (requires ANTHROPIC_API_KEY)
./ravl examples/tech_news_dashboard
```

### From Examples Directory

```bash
cd .ravl/examples

# Run Python example directly
cd hello_ravl_py && python3 ravl_loop.py

# Or use framework CLI
../../bin/ravl hello_ravl_py
../../bin/ravl hello_ravl_md
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
└── README.md                      # Documentation
```

Delegation examples add:
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

1. **Explore Templates**: See `.ravl/templates/` for production-ready loop templates
2. **Read Framework Docs**:
   - [RAVL_PROTOCOL.md](../RAVL_PROTOCOL.md) - Deep dive into phases
   - [RAVL_VISION.md](../RAVL_VISION.md) - Design principles
   - [CHANGELOG.md](../../CHANGELOG.md) - Feature history
3. **Real-World Loops**: Check project's `ravl_loops/` for production examples
4. **Build Your Own**: Start with an example as template

### Creating Your Loop

```bash
# Option 1: Clone an example (Python)
cp -r .ravl/examples/hello_ravl_py ravl_loops/my_loop

# Option 2: Clone an example (Markdown)
cp -r .ravl/examples/hello_ravl_md ravl_loops/my_loop

# Option 3: Use framework templates
./.ravl/bin/ravl-clone data_ingress_template my_api_loop

# Edit and run
vim ravl_loops/my_loop/ravl_loop.py  # or .md
./ravl my_loop
```

---

## Learning Resources

- **Visual Learner?** Watch the real-time output as loops execute
- **Code Learner?** Read `hello_ravl_py/ravl_loop.py` - heavily commented
- **Markdown Learner?** Read `hello_ravl_md/ravl_loop.md` - plain language specs
- **Concept Learner?** Read example READMEs for detailed explanations
- **Hands-On Learner?** Modify examples and see what breaks

---

## Troubleshooting

### ANTHROPIC_API_KEY not set
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Required for: tech_news_curator, tech_news_dashboard

### GitHub rate limit (403)
GitHub allows 60 requests/hour without auth. Wait an hour or add token:
```bash
export GITHUB_TOKEN="ghp_..."
```

### Code generation fails
- Check internet connection (needs to fetch API docs from Context7)
- Verify ANTHROPIC_API_KEY is valid
- Check `learnings/execution_learning/` for error details

### Children not executing (dashboard)
- Verify child paths exist: `ravl_loops/{child}/ravl_loop.md`
- Check child config files
- Ensure parent can read child outputs

---

## Questions?

- Check individual example READMEs for detailed docs
- Review framework documentation in `.ravl/docs/`
- Look at production loops in project's `ravl_loops/`
- Read RAVL protocol specification: [RAVL_PROTOCOL.md](../RAVL_PROTOCOL.md)
