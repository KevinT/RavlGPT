# External Alignment Analysis Prompt

You are analyzing for drift between internal documents and external authoritative sources.

## Context

{context}

## Internal Documents

{internal_documents}

## External Source Content

Source ID: {source_id}
Source Name: {source_name}

{external_content}

## Analysis Strategy

Using the {strategy} strategy, detect misalignments between internal and external content.

## Instructions

Identify drift (misalignments) between internal and external content:

1. **Content Mismatches**: Information that contradicts between internal and external sources
   - Different definitions
   - Conflicting procedures
   - Different organizational information

2. **Outdated Information**: Internal docs with outdated external information

3. **Missing Updates**: External updates not yet reflected internally

4. **Terminology Drift**: Different names or terminology used

5. **Process Drift**: Procedures described differently

6. **Authority Gaps**: Important external information not documented internally

## Output Format

Return a JSON array of drift issues found:

```json
[
  {
    "drift_category": "content_mismatch",
    "severity": "warning",
    "internal_file": "path/to/internal/doc.md",
    "external_source": "source_id",
    "description": "Brief description of the drift",
    "details": {
      "internal_claim": "what internal doc says",
      "external_claim": "what external source says",
      "location": "specific section or line"
    },
    "confidence": 0.85
  }
]
```

Return ONLY the JSON array, no other text.
