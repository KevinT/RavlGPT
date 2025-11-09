# Hello RAVL - Environment Explorer

Your first learning loop. Watch as it discovers and maps its environment through exploration.

## What Makes This a Learning Loop

This isn't a task that executes the same way each time. It's an agent that:
- **Starts with zero knowledge** about its environment
- **Decides what to explore** based on what it's learned
- **Discovers facts** through investigation
- **Builds a knowledge map** that persists across runs
- **Gets strategically smarter** about what to explore next

## The RAVL Mental Model

Think of this loop as a curious explorer, not a task executor:

```
Run 1: "I know nothing. Let me check the date and time..."
Run 2: "I know when I run. Let me explore the filesystem..."
Run 3: "I found interesting directories. Let me investigate deeper..."
Run 5: "I've mapped the basics. Let me discover Python capabilities..."
Run 10: "I understand my world. Let me find hidden patterns..."
```

Each run builds on previous learning. The loop becomes more sophisticated.

## How to Run

```bash
# From framework root (will clone to ravl_loops/ on first run)
./ravl simple_learning_loop

# Watch multiple runs to see learning
./ravl simple_learning_loop
./ravl simple_learning_loop
./ravl simple_learning_loop  # By run 3-4, you'll see strategic exploration
```

## What You'll See

### Early Runs (Naive Exploration)
```
🧠 REFLECT: No prior knowledge. Starting with basic environment discovery.

🔍 ACT: Exploring current date and time...
   Discovered: Running at 2025-11-09 14:30:45 UTC
   Discovered: Timezone is UTC
   Saved to: output/exploration_log.md

✅ VERIFY: Discovery Value: 8/10 (genuinely new information)
          Insight Depth: 5/10 (basic facts)
          Efficiency: 7/10 (good starting point)
          Overall: 6.7/10 ✅

📊 LEARN: Added time facts to knowledge base.
         Next priority: Explore filesystem structure.
```

### Middle Runs (Pattern Recognition)
```
🧠 REFLECT: I know time context and basic file structure.
           Found pattern: .git directory suggests version control.
           Strategy: Investigate version control details.

🔍 ACT: Exploring git repository information...
   Discovered: Repository has 1,247 commits
   Discovered: 3 active branches (main, dev, feature-xyz)
   Discovered: Last commit was 2 hours ago
   Pattern: Active development repository

✅ VERIFY: Overall: 8.3/10 ✅ (deeper insights emerging)

📊 LEARN: Repository patterns suggest active project.
         Hypothesis: Check for CI/CD configuration next.
```

### Later Runs (Sophisticated Understanding)
```
🧠 REFLECT: Comprehensive environment map established.
           Know: file structure, git details, Python capabilities.
           Strategy: Look for hidden patterns and connections.

🔍 ACT: Analyzing relationships between discoveries...
   Insight: Test files mirror source structure (good practice)
   Insight: Virtual environments suggest multiple Python projects
   Insight: Log timestamps correlate with git commit times

✅ VERIFY: Overall: 9.2/10 ✅ (high-value meta-insights)

📊 LEARN: Moving from facts to understanding.
         Environment fully mapped. Quality of insights increasing.
```

## Understanding the Learning

Check `learnings/loop_learning/model.yml` after several runs:

```yaml
# After 5 runs
environment:
  time:
    first_run: "2025-11-09T14:30:45Z"
    timezone: "UTC"
    typical_runtime: "~3 seconds"

  location:
    cwd: "/Users/you/ravl_loops/simple_learning_loop"
    project_root: "/Users/you/project"
    in_git_repo: true

  structure:
    important_dirs: [".ravl", "ravl_loops", "learnings", "output"]
    config_files: ["ravl.yml", ".env"]
    total_files_discovered: 47

exploration_history:
  explored_areas:
    - "time_context"
    - "filesystem_basics"
    - "git_repository"
    - "python_environment"
    - "file_patterns"

  fully_mapped:
    - "time_context"
    - "filesystem_basics"

  worth_revisiting:
    - "git_history"  # Changes over time
    - "log_files"     # New entries appear

strategic_insights:
  successful_strategies:
    - "Start with immediate context"
    - "Follow interesting findings"
    - "Look for patterns, not just facts"

  total_facts_discovered: 52
  discovery_rate_trend: "decreasing"  # Natural as environment gets mapped
  insight_quality_trend: "increasing" # Moving from facts to patterns
```

## Key Observations

### 1. Real Learning, Not Just Execution
- Builds persistent knowledge across runs
- Makes strategic decisions based on accumulated wisdom
- Discovery rate naturally decreases as knowledge saturates

### 2. Observable Intelligence
- Early runs: Random exploration
- Middle runs: Focused investigation
- Later runs: Pattern synthesis

### 3. No Code Generation Focus
This example shows that markdown loops aren't just about generating code. They're about defining intelligent behavior that learns and adapts.

## File Structure

```
simple_learning_loop/
├── ravl_loop.md              # Loop definition (what you read)
├── README.md                 # This file
├── config/
│   └── ravl.yml             # Configuration
├── learnings/
│   ├── execution_learning/   # Framework's learning (how to run)
│   └── loop_learning/        # Domain learning (what was discovered)
│       └── model.yml        # Growing knowledge base ← Watch this!
└── output/
    └── exploration_log.md   # Chronicle of discoveries
```

## The Learning Trajectory

```
Runs 1-3:   Naive → Basic Facts
Runs 4-6:   Facts → Structure Understanding
Runs 7-9:   Structure → Pattern Recognition
Runs 10+:   Patterns → Strategic Insights
```

This is observable intelligence emerging from simple exploration rules.

## Common Patterns You'll See

1. **Knowledge Saturation**: After ~10-15 runs, discovery rate drops as environment becomes fully mapped
2. **Strategy Evolution**: Loop naturally shifts from breadth-first to depth-first exploration
3. **Insight Sophistication**: Progresses from "file exists" to "these files follow pattern X which suggests Y"
4. **Hypothesis Formation**: Loop starts making predictions about what it might find

## Customization Ideas

Try modifying the loop to:
- Focus on specific areas (only Python capabilities, only git history)
- Score different types of discoveries differently
- Add hypothesis testing ("I predict X exists... let me check")
- Reset and watch it relearn with different strategies

## What You're Learning

### About RAVL
- Loops that start ignorant and become knowledgeable
- Decision-making based on accumulated learning
- Model persistence across runs
- Natural progression from simple to sophisticated

### About Learning Systems
- Exploration vs. exploitation tradeoffs
- Knowledge representation in models
- How discovery rate changes over time
- Emergent strategic behavior

## Next Steps

1. **Run it 10 times**: Watch the complete learning trajectory
2. **Read exploration_log.md**: See the chronicle of discoveries
3. **Study model.yml**: Understand how knowledge accumulates
4. **Try communication_learner**: See advanced learning strategies

## The Power of RAVL

Traditional automation:
```python
# You program exact steps
def explore():
    check_date()
    list_files()
    read_configs()
    # Same every time
```

RAVL learning loops:
```markdown
# You define learning behavior
Explore something you don't know yet.
Learn from what you discover.
Decide what to explore next.
# Different each time, based on learning
```

---

**Welcome to RAVL**: Where loops learn, adapt, and become more intelligent over time.