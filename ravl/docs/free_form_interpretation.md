# Free-Form Markdown Interpretation

## Overview

The RAVL framework can interpret free-form markdown descriptions into properly structured RAVL loops. This allows you to write naturally without requiring strict adherence to the `# Act`, `# Verify`, and `# Learn` section structure.

## When Interpretation Happens

When you write a `ravl_loop.md` file **without explicit phase headings** (no `# Act`, `# Verify`, etc.), the framework automatically:

1. Detects that no explicit phases exist
2. Sends your raw markdown to an LLM
3. Uses the LLM to interpret your intent into structured RAVL phases
4. Saves the enhanced structure to `learnings/current_state/ravl_loop_enhanced.md`
5. Executes the enhanced version
6. Shows you what was interpreted so you can refine it

## Why This Exists

### Problem It Solves

Users naturally write requirements in different ways:
- "Get all items from this Notion database and save them as markdown"
- Task lists, descriptive text, mixed formatting
- Instructions without explicit Act/Verify structure

Instead of forcing users into a rigid structure, the framework interprets their intent.

### Benefits

1. **Lower barrier to entry** - No need to memorize RAVL structure
2. **Feedback loop** - See what the system understood about your intent
3. **Refinement path** - Review the interpretation and update if needed
4. **Context-aware** - The LLM uses your related loops as pattern examples

## How to Use It

### Writing Your Loop

Just describe what you want the loop to do. For example, in `ravl_loop.md`:

```markdown
Get all the items in the [XYZ](urlhere) notion page and put them into a single markdown file in `_data/` folder
in the root of this repo.
```

### Running Your Loop

```bash
./.ravl/bin/ravl your_loop_name --mode fast
```

The framework will:
1. Detect no explicit phases
2. Interpret your intent
3. Show what it understood
4. Execute the interpreted version

### Reviewing the Interpretation

After the run completes, you'll see:

```
================================================================================
📚 INTERPRETATION APPLIED
================================================================================
   Your free-form markdown was structured into RAVL phases

   Review:  cat learnings/current_state/ravl_loop_enhanced.md
   Learn:   .ravl/docs/free_form_interpretation.md

   To refine for future runs:
     1. Review the enhanced version
     2. Update ravl_loop.md with any tweaks
     3. Next run will use your updated structure
```

View the enhanced structure:

```bash
cat learnings/current_state/ravl_loop_enhanced.md
```

This will show something like:

```markdown
# Act

- Query the Knowledge Commons Notion database at [URL]
- Extract all items
- Convert to markdown format
- Save with timestamp to _data/ directory
- Implement change detection

# Verify

* All items from the database are included
* Output is valid markdown format
* File has timestamp in name
* No duplicate files if data unchanged
```

### Refining for Future Runs

If you like what was interpreted:

1. Copy the structure from `learnings/current_state/ravl_loop_enhanced.md`
2. Update your original `ravl_loop.md` with it
3. Make any tweaks you want
4. Next run will use your structure directly (no re-interpretation)

Example refined `ravl_loop.md`:

```markdown
# Act

- Query Knowledge Commons Notion database
- Extract all items
- Convert to markdown format
- Save to _data/breadcrumbs_TIMESTAMP.md
- Check if data changed (use hash comparison)

# Verify

* All knowledge commons items included in markdown
* Valid markdown format with proper structure
* Filename includes date and time
* No new file created if data unchanged

# Learn

- Track which fields are most frequently accessed
- Improve field extraction if patterns change
```

## What the Interpretation Uses as Context

When interpreting your markdown, the LLM has access to:

1. **RAVL Protocol Documentation** - Explains what each phase should contain
2. **Related Loops** - If your loop has a parent or sibling loops, examples of how they're structured
3. **Your Loop Metadata** - Name, description from config
4. **Your Raw Markdown** - Your exact description

This provides enough context for accurate interpretation without being overly complex.

## Examples

### Example 1: Data Ingestion Loop

**Free-form input:**
```
Pull all entries from the product catalog database and convert
them to CSV format, saving with today's date in the filename.
```

**Interpreted as:**
```markdown
# Act
- Query product catalog database
- Extract all entries
- Convert to CSV format
- Generate timestamped filename
- Save to _data/ directory

# Verify
* All product entries present in CSV
* Valid CSV format
* Filename includes date
* No duplicate files if data unchanged
```

### Example 2: Monitoring Loop

**Free-form input:**
```
Check if the handbook content has any broken links or
inconsistent terminology. Report issues found.
```

**Interpreted as:**
```markdown
# Act
- Scan handbook markdown for links
- Check each link for validity
- Extract terminology and check consistency
- Generate report of issues found

# Verify
* All links checked
* Terminology scan complete
* Report is well-formatted
* Report saved with timestamp
```

## When Interpretation Happens (and Doesn't)

### Interpretation WILL trigger if:
- `ravl_loop.md` has NO `# Act` heading (and no other phase headings)
- File has content (not empty)

### Interpretation will NOT trigger if:
- `ravl_loop.md` has explicit `# Act` section
- File is empty

### Every Run:
- If you keep the free-form format, interpretation runs every time (shows fresh feedback)
- If you adopt the interpreted structure, it uses that directly (no re-interpretation)

## Disabling Interpretation

If you want to avoid interpretation (for example, if you prefer structured loops), just add a minimal `# Act` section to your `ravl_loop.md`:

```markdown
# Act

Your instructions here...
```

Even an empty `# Act` section will prevent interpretation.

## Troubleshooting

### "Interpretation doesn't match what I wanted"

1. The LLM made a reasonable guess from your text
2. Review `learnings/current_state/ravl_loop_enhanced.md`
3. Update your `ravl_loop.md` with corrections
4. Next run will use your updated version

### "I want to try a different interpretation"

Reset the learning files (which includes the cached interpretation):

```bash
./.ravl/bin/ravl-reset your_loop_name
```

Then run again - the framework will re-interpret with any changes you made.

### "Interpretation is too simple/complex"

You can:
1. Refine your `ravl_loop.md` to be clearer about your intent
2. Explicitly add `# Act` and `# Verify` sections with your desired structure
3. Both will guide the system toward what you want

## Technical Details

### What Gets Saved

- `learnings/current_state/ravl_loop_enhanced.md` - The LLM's enhanced version (persisted for review)
- `learnings/current_state/ravl_loop.md` - Copy of your original source
- `learnings/recent_attempts/attempt_N/` - Execution results from each run

### Performance

- First interpretation: ~5-10 seconds (LLM call + structure parsing)
- Subsequent runs: <1 second (uses your explicit structure)

### Caching

- Interpretation is NOT cached (always fresh)
- This means each run with free-form markdown gets current feedback
- Once you adopt explicit structure, caching applies to your code execution

## See Also

- [RAVL_PROTOCOL.md](./RAVL_PROTOCOL.md) - Core RAVL concepts explained
- [README.md](./README.md) - Framework overview
- Examples in `examples/` directory
