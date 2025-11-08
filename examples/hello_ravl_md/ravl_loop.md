# Hello RAVL - Markdown Version

The simplest possible markdown-based RAVL loop. Demonstrates how you can describe behavior in plain language and let the framework generate the code.

**Learning Objectives:**
- See how markdown loops work (describe WHAT, not HOW)
- Understand that you don't need to write Python code
- Watch the framework generate and execute code from your description
- Compare with hello_ravl_py to see the difference

---

# Act

Generate a timestamped greeting and save it to a file.

## What to Do

1. Get the current timestamp (UTC)
2. Create a greeting message: "Hello from RAVL! (Run #{run_number} at {timestamp})"
3. Save the greeting to: `output/greetings_{today_date}.txt` (append mode)
4. The run number should increment with each run (starting from 1)

## Output Format

Each line in the output file should be a complete greeting with timestamp:
```
Hello from RAVL! (Run #1 at 2025-11-08 14:30:45 UTC)
Hello from RAVL! (Run #2 at 2025-11-08 15:22:10 UTC)
Hello from RAVL! (Run #3 at 2025-11-08 16:45:33 UTC)
```

---

# Verify

Validate that the greeting was saved successfully:

## Required Checks

- Output file exists at `output/greetings_{today}.txt`
- File has content (size > 0 bytes)
- File contains the greeting text
- Greeting includes current run number
- Greeting includes timestamp

**Pass if all checks succeed.**

---

# Learn

Track run statistics across executions:

## What to Learn

Store in model.yml:
- `total_runs`: Total number of times this loop has run
- `successful_runs`: Number of successful runs (verification passed)
- `failed_runs`: Number of failed runs
- `last_run_timestamp`: Timestamp of last run
- `success_rate`: successful_runs / total_runs

Update these counters each run and save to learnings/loop_learning/model.yml.

---

## Notes

This markdown loop does the same thing as `hello_ravl_py` but without writing Python code. The framework:

1. **Reads this markdown** and understands what you want
2. **Generates Python code** to implement it
3. **Executes the code** and captures output
4. **Caches successful code** for future runs (no regeneration needed)

**Compare with hello_ravl_py:**
- Python version: ~200 lines of code you write
- Markdown version: ~60 lines of description

Both produce identical results!

**When to use markdown:**
- Simple data fetching or transformation
- Don't need fine-grained control
- Want self-healing (framework adapts code if things change)
- Rapid prototyping

**When to use Python:**
- Complex logic or algorithms
- Need precise control over execution
- Performance critical
- Building production systems
