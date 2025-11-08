# Hello RAVL (Python) - Your First RAVL Loop

The simplest possible Python-based RAVL loop. Perfect for understanding the basics.

**Also see**: `hello_ravl_md` for the same behavior using markdown (even simpler!).

## What It Does

Generates timestamped greetings and tracks how many times it has run. Each run:
1. Loads previous statistics
2. Creates a new greeting
3. Verifies the output was created
4. Updates the model with run counts

No external APIs, no complexity - just the pure RAVL pattern.

## What You'll Learn

### RAVL Phases
- **REFLECT**: Load previous model, observe current state
- **ACT**: Take action based on reflection
- **VERIFY**: Check that action succeeded
- **LEARN**: Update model with new insights

### Model Persistence
- How models are loaded from `learnings/loop_learning/model.yml`
- How timestamped model snapshots are created (`model-2025-11-08-143022.yml`)
- How models track statistics across runs

### Learning Evolution
Run this multiple times and watch:
- `total_runs` increment
- `success_rate` track reliability
- Model history accumulate in `learnings/loop_learning/`

## How to Run

```bash
# From framework root
./ravl examples/hello_ravl

# Or directly
cd docs/examples/hello_ravl
python3 ravl_loop.py
```

## Expected Output

**First run:**
```
🚀 Starting Hello RAVL Loop
================================================================================

================================================================================
 Step 1 of 4: [R]EFLECT
================================================================================

  ℹ️  Hello RAVL: No existing model found, initializing new model

📊 Previous State:
   Total runs: 0
   Last run: never

💡 This is our first run! Let's create our first greeting.

================================================================================
 Step 2 of 4: [A]CT
================================================================================

✍️  Generating greeting:
   Hello from RAVL! (Run #1 at 2025-11-08 14:30:45 UTC)

💾 Saved to: output/greetings_2025-11-08.txt

================================================================================
 Step 3 of 4: [V]ERIFY
================================================================================

🔍 Verification Results:
   Output file exists: ✅
   Output has content: ✅ (58 bytes)

All checks passed! ✅

================================================================================
 Step 4 of 4: [L]EARN
================================================================================

📈 Updated Statistics:
   Total runs: 1
   Successful: 1
   Failed: 0
   Success rate: 100.0%

💾 Model saved to learnings/loop_learning/

================================================================================
✅ Hello RAVL Loop completed successfully
================================================================================
```

**Subsequent runs:**
The loop will show increasing run counts and maintain a success rate history.

## File Structure

After running, you'll see:

```
hello_ravl/
├── ravl_loop.py              # The loop implementation
├── config/
│   └── ravl.yml             # Loop configuration
├── learnings/
│   └── loop_learning/       # Domain learning (run statistics)
│       ├── model.yml        # Current model
│       └── model-2025-11-08-143045.yml  # Timestamped snapshot
└── output/
    └── greetings_2025-11-08.txt  # Generated greetings
```

## Key Concepts

### 1. Model Structure
```yaml
total_runs: 3
successful_runs: 3
failed_runs: 0
last_run_timestamp: "2025-11-08T14:32:15.123456+00:00"
success_rate: 1.0
metadata:
  last_greeting: "Hello from RAVL! (Run #3 at 2025-11-08 14:32:15 UTC)"
  last_output_file: "output/greetings_2025-11-08.txt"
```

### 2. Learning Over Time
Each run updates the model:
- **Run 1**: Creates baseline (total_runs=1, success_rate=100%)
- **Run 2**: Increments counts (total_runs=2, success_rate=100%)
- **Run 3**: Continues tracking (total_runs=3, success_rate=100%)

If a run fails verification, `failed_runs` increments and `success_rate` adjusts.

### 3. Read the Code
The `ravl_loop.py` file is heavily commented. Read it to understand:
- How `BaseRAVLLoop` provides core functionality
- How each RAVL phase is implemented
- How models are loaded and saved
- How verification determines success/failure

## Next Steps

Once you understand this example:

1. **tech_news_curator** - See markdown-based loops with LLM code generation
2. **github_trending_tracker** - Learn API integration and self-healing
3. **tech_news_dashboard** - Master parent/child delegation patterns

## Customization Ideas

Modify this example to learn by doing:

1. **Add More Verification**: Check greeting length, format, content
2. **Track More Metrics**: Average greeting length, time between runs
3. **Add Failure Scenarios**: Simulate errors to see how learning tracks failures
4. **Multiple Outputs**: Generate JSON, CSV, or other formats
5. **Pattern Detection**: Learn which time of day runs occur most often

Remember: The goal isn't complexity, it's understanding the RAVL pattern!
