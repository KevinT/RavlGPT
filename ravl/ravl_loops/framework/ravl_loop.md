# Framework Loops

This parent loop lists all built-in RAVL framework loops.

## Child Loops

Framework loops provide core functionality:
- **content_coherence_ravl**: Analyzes internal consistency and coherence
- **google_docs_fetching**: Fetch Google Docs/Slides/Sheets with lineage tracking
- **health_checks**: Framework health analysis loops
- **release_notes**: Generate release notes from git history

To run a framework loop:
```bash
ravl framework.<loop_name>
```

Example:
```bash
ravl framework.health_checks
```
