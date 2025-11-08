# Hello RAVL (Markdown) - Your First Markdown Loop

The simplest possible markdown-based RAVL loop. Same behavior as `hello_ravl_py` but defined in plain language!

**Also see**: `hello_ravl_py` to see how Python loops work.

## What It Does

Generates timestamped greetings and tracks run statistics. Identical to `hello_ravl_py` but:
- **Python version**: You write ~200 lines of code
- **Markdown version**: You write ~60 lines of description
- **Result**: Exactly the same!

## What You'll Learn

### Markdown Loops
- How to define loops in plain language
- Framework generates Python code from your markdown
- You describe WHAT you want, not HOW to do it

### Code Generation
- Framework reads your markdown specification
- LLM generates Python code to implement it
- Code is cached after successful run
- Self-healing: Code regenerates if failures occur

### Same Power, Less Code
- All RAVL phases work (Reflect → Act → Verify → Learn)
- Model persistence works the same
- Verification and learning work the same
- Less code to maintain

## Prerequisites

```bash
# Markdown loops need ANTHROPIC_API_KEY for code generation
export ANTHROPIC_API_KEY="your-key-here"
```

## How to Run

```bash
# From framework root
./ravl examples/hello_ravl_md

# Or from example directory
cd docs/examples/hello_ravl_md
python3 ../../../common/llm/run_markdown_ravl.py ravl_loop.md
```

## Expected Output

**First Run** (code generation):
```
🚀 Starting Hello RAVL Markdown Loop
================================================================================

================================================================================
 Step 1 of 4: [R]EFLECT
================================================================================

  ℹ️  No cached code found - will generate new code
  🔍 Analyzing markdown specification...

================================================================================
 Step 2 of 4: [A]CT
================================================================================

🤖 Generating Python code from markdown...
✅ Code generated successfully
🏃 Executing generated code...

Hello from RAVL! (Run #1 at 2025-11-08 14:30:45 UTC)
💾 Saved to: output/greetings_2025-11-08.txt

================================================================================
 Step 3 of 4: [V]ERIFY
================================================================================

🔍 Verification Results:
   ✅ Output file exists
   ✅ File has content (58 bytes)
   ✅ Greeting text present
   ✅ Run number included
   ✅ Timestamp included

All checks passed! ✅

================================================================================
 Step 4 of 4: [L]EARN
================================================================================

📈 Updated Statistics:
   Total runs: 1
   Successful: 1
   Failed: 0
   Success rate: 100.0%

💾 Code cached to execution_learning/code_cache.json
💾 Model saved to learnings/loop_learning/

================================================================================
✅ Hello RAVL Markdown Loop completed successfully
================================================================================
```

**Subsequent Runs** (cached code):
```
  ℹ️  Using cached code from previous successful run
  ⚡ Skipping code generation (cache hit)
```

Much faster because code is reused!

## File Structure

After running:

```
hello_ravl_md/
├── ravl_loop.md                    # Your markdown spec (what you write)
├── config/
│   └── ravl.yml                   # Loop configuration
├── learnings/
│   ├── execution_learning/        # How to execute (generated code)
│   │   ├── code_cache.json       # Cached Python code
│   │   └── dsl_iteration_1.json  # Code generation history
│   └── loop_learning/             # What was learned (run stats)
│       ├── model.yml             # Current model
│       └── model-2025-11-08-143045.yml
└── output/
    └── greetings_2025-11-08.txt  # Generated greetings
```

## Key Concepts

### 1. Markdown → Python Transformation

**You write in ravl_loop.md:**
```markdown
# Act
Generate a timestamped greeting and save it to output/greetings_{today}.txt
```

**Framework generates Python code:**
```python
from datetime import datetime, timezone
timestamp = datetime.now(timezone.utc)
greeting = f"Hello from RAVL! (Run #{run_num} at {timestamp})"
with open('output/greetings_2025-11-08.txt', 'a') as f:
    f.write(greeting + '\n')
```

You never see this Python code - it's generated, cached, and executed automatically.

### 2. Code Caching

| Run | Code Generated? | Duration | Why |
|-----|----------------|----------|-----|
| 1   | ✅ Yes          | 15s      | First run, no cache |
| 2   | ❌ No (cached)  | 2s       | Cache hit, reuse code |
| 3   | ❌ No (cached)  | 2s       | Cache hit, reuse code |
| 4   | ✅ Yes (error)  | 15s      | Verification failed, regenerate |
| 5   | ❌ No (fixed)   | 2s       | New code cached |

Caching makes loops fast and cost-effective.

### 3. Dual Learning Spaces

**Execution Learning** (`learnings/execution_learning/`):
- How to generate timestamped greetings
- How to write to files
- Optimal code patterns

**Domain Learning** (`learnings/loop_learning/`):
- Run statistics
- Success rates
- Pattern tracking

These spaces are separate - clean architecture.

### 4. Self-Healing Example

**Scenario**: Output directory permission changes

- **Run N**: Code fails (can't write to output/)
- **Verification**: Fails (no output file)
- **Framework**: Invalidates code cache
- **Run N+1**: Generates new code with proper directory creation
- **Result**: Loop self-heals without manual intervention

## Comparison with hello_ravl_py

| Feature | hello_ravl_py | hello_ravl_md |
|---------|--------------|---------------|
| **Lines of code you write** | ~200 | ~60 |
| **Python skills required** | Yes | No |
| **Code generation** | No | Yes (automatic) |
| **Self-healing** | No | Yes (automatic) |
| **Execution speed** | Fast (native) | Fast (cached) |
| **When to use** | Complex logic, production | Simple tasks, prototyping |

## Common Issues

### ANTHROPIC_API_KEY not set
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Required for markdown loops (code generation needs LLM).

### Code regenerates every run
- Verification might be failing
- Check `learnings/execution_learning/` for errors
- Adjust verification criteria in markdown

### Generated code has errors
- Check markdown is clear and specific
- Provide examples of desired output
- Framework learns from failures and improves

## Customization Ideas

Modify the markdown to explore:

1. **Different Output**: Generate JSON, CSV, HTML instead of text
2. **Multiple Files**: Create separate files per run
3. **Data Processing**: Add calculations, transformations
4. **External Data**: Fetch from URLs or APIs

Remember: Just update the markdown, framework generates new code!

## Next Steps

Once you understand markdown loops:

1. **Compare with hello_ravl_py**: See the code difference
2. **tech_news_curator**: More complex markdown loop with RSS and LLM
3. **github_trending_tracker**: See when Python is better choice
4. **tech_news_dashboard**: Advanced markdown orchestration

## Further Reading

- `.ravl/docs/RAVL_PROTOCOL.md` - Understanding RAVL phases
- `.ravl/docs/RAVL_VISION.md` - Framework design principles
- `.ravl/common/execution/markdown/` - How markdown loops execute
- `tech_news_curator/README.md` - Next markdown loop example
