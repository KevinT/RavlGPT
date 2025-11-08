# External Alignment Template Loop

Generic loop template for detecting drift between internal documents and external sources.

## Reflect

Before analyzing, check that configuration is properly set up.

### Configuration Validation

Verify that `config/external_alignment_config.yml` has been properly configured:
- `document_folders` should list directories containing your internal content
- `external_sources` should list external sources to monitor (at least one enabled)
- Should NOT contain "# TODO:" placeholder text
- Configured paths/URLs should be accessible

If configuration is incomplete, log this to learnings/ so the user knows what to configure.

Next, review learned patterns:
- **Previous drift categories**: What types of drift have been detected?
- **Source reliability**: Which external sources are most useful?
- **Strategy performance**: Which analysis strategies were most effective?

Gather current state:
- Read internal documents from configured `document_folders`
- Fetch external sources (handle errors gracefully)
- Compute state hash for change detection

Include learned context from your own model and any cross-loop context (if running as child loop).

## Act

If configuration is incomplete, report it and stop.

Configuration incomplete? Log finding to learnings/:
```
timestamp: [ISO format]
issue: configuration_required
message: "External sources not configured in config/external_alignment_config.yml"
guidance:
  - "Edit config/external_alignment_config.yml"
  - "Configure at least one external source in external_sources section"
  - "Set enabled: true for sources you want to monitor"
  - "Run again: ./ravl external_alignment --mode fast"
paths_checked: [list of what was checked]
```

Configuration is valid? Proceed with analysis:

### Fetch External Sources

Retrieve content from configured external sources:
- Handle authentication (API keys, service accounts)
- Handle rate limiting
- Extract text from various formats (Google Docs, GitHub, HTML, etc.)
- Log any fetch failures

### Analyze Drift

Compare internal documents against external sources to find misalignments:

**Look for:**
- **Content Mismatches**: Information in internal docs that contradicts external sources
- **Outdated Sections**: Internal docs referencing outdated external information
- **Missing Updates**: External updates not reflected in internal docs
- **Terminology Drift**: Different names or definitions used
- **Process Drift**: Described processes that differ from external reality
- **Authority Gaps**: Important external information not documented internally

For each drift found, provide:
- `drift_category`: Type of misalignment
- `severity`: info, warning, or critical
- `internal_file`: Which internal document has the issue
- `external_source`: Which external source contradicts it
- `description`: What the drift is
- `details`: Specific details and evidence
- `confidence`: 0.0-1.0 confidence this is real drift

Save issues to timestamped file in learnings/

## Verify

Check if previous drift issues have been resolved.

For each previous drift issue:
- Has the internal document been updated?
- Has the external source changed?
- Is the drift still present?
- Mark as: `fixed`, `ignored`, `resolved_externally`, or `false_positive`

Calculate summary metrics:
- Total drift issues checked
- Fixed: issues resolved in internal docs
- Ignored: issues still present
- False positives: weren't real drift

## Learn

Update learning model based on verification outcomes:

**Update drift weights**: Drift categories that users fixed should be weighted higher. Those that were ignored or false positives should be weighted lower.

**Update source reliability**: Track which external sources provided the most accurate and useful drift detection.

**Update strategy performance**: Track which analysis strategies found the most actionable drift.

Save updated model to learnings/model.yml with:
- Incremented learning_iterations
- Updated drift_weights
- Updated source_reliability scores
- Updated strategy_performance
- Last learned timestamp
