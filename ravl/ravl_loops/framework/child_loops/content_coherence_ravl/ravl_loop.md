# Content Coherence Gap Detection

Loop for analyzing internal consistency within document collections and identifying gaps, and then learning which gaps are closed over time to bias the loop for detecting those sorts of gaps in future, under the assumption that gaps that are closed quickly are more likely to have been significant, and gaps that are detected but not closed are likely to not be false positives in the detection system.

## Reflect

Before analyzing, check that configuration is properly set up.

### Configuration Validation

Verify that `config/content_coherence_config.yml` has been properly configured:
- `scan_paths` should list directories containing your content files
- Should NOT contain "# TODO:" placeholder text
- Configured paths should exist in the project

If configuration is incomplete, log this to learnings/ so the user knows what to configure.

Next, review learned patterns from previous runs:
- **Previous gap categories**: What types of consistency issues have been found?
- **Terminology clusters**: What terminology patterns have been identified?
- **Strategy performance**: Which analysis strategies worked best previously?

Gather current state of documents:
- List all markdown files in configured `scan_paths`
- Compute state hash to detect changes since last run
- Read file contents (filter out base64 images to save tokens)

Include learned context from your own model and any cross-loop context (if running as a child loop).

## Act

If configuration is incomplete, report it and stop (do not proceed with analysis).

Configuration incomplete? Log finding to learnings/:
```
timestamp: [ISO format]
issue: configuration_required
message: "scan_paths in config/content_coherence_config.yml is not configured"
guidance:
  - "Edit config/content_coherence_config.yml"
  - "Replace scan_paths placeholder with actual directories: ['docs/', 'content/']"
  - "Run again: ./ravl content_coherence --mode fast"
paths_checked: [list of paths that failed validation]
```

Configuration is valid? Proceed with analysis:

### Select Analysis Strategy

Based on learned patterns and current content volume, select an analysis strategy:
- **broad_survey**: Full content of all files (when file count is small)
- **deep_dive**: Full content of fewer files (detailed analysis)
- **focused_scan**: Target specific files based on previous findings
- **hybrid**: Mix of approaches

### Analyze Content

Perform coherence analysis on prepared content to identify gaps:

**Look for:**
- **Terminology inconsistencies**: Same concept referred to differently across documents
- **Structural inconsistencies**: Formatting or organization that varies unexpectedly
- **Missing sections**: Expected content that is absent
- **Outdated information**: Content that references past versions
- **Conflicting statements**: Contradictions between documents
- **Incomplete references**: Links or references that don't match content

For each gap found, provide:
- `gap_category`: Type of inconsistency
- `severity`: info, warning, or critical
- `file`: Document where gap was detected
- `description`: What the gap is
- `details`: Specific details (line numbers, exact inconsistency, etc.)
- `confidence`: 0.0-1.0 how confident this is a real issue

Save gaps to timestamped file in the configured learnings directory location

## Verify

Check if previous gaps have been resolved by comparing previous run findings with current document state.

For each previous gap:
- Did the document change?
- Is the gap still present in the current content?
- Mark as: `fixed` (issue resolved), `ignored` (still present), or `false_positive` (was not a real issue)

Calculate summary metrics:
- Total gaps checked
- Fixed: gaps that no longer exist
- Ignored: gaps still present in content
- False positives: gaps that weren't real issues

## Learn

Update learning model based on verification outcomes:

**Update gap weights**: Gaps that users fixed should be weighted higher in future runs. Gaps that were ignored or false positives should be weighted lower.

**Update strategy performance**: Track which analysis strategies found the most accurate gaps.

**Update performance metrics**: Track precision (of gaps found), false positive rate, and suggestion acceptance rate.

Save updated model to learnings/model.yml with:
- Incremented learning_iterations
- Updated gap_weights
- Updated strategy_performance
- Updated performance metrics
- Last learned timestamp
