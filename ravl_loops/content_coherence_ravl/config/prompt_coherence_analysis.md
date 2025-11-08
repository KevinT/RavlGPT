# Content Coherence Analysis Prompt

You are analyzing a collection of documents for internal consistency and coherence issues.

## Context

{context}

## Documents to Analyze

{file_summaries}

## Analysis Strategy

Using the {strategy} strategy, analyze these documents for inconsistencies.

## Instructions

Identify gaps in coherence:

1. **Terminology Inconsistencies**: Same concepts or terms used differently across documents
   - Different names for the same thing
   - Conflicting definitions
   - Inconsistent abbreviations

2. **Structural Inconsistencies**: Unexpected variations in how documents are organized or formatted

3. **Missing Content**: Expected sections or information that are absent

4. **Outdated Information**: Content that references outdated versions or past decisions

5. **Conflicting Statements**: Direct contradictions between documents or sections

6. **Incomplete References**: Internal links or references that don't match content

## Output Format

Return a JSON array of gaps found:

```json
[
  {
    "gap_category": "terminology_inconsistency",
    "severity": "warning",
    "file": "path/to/file.md",
    "description": "Brief description of the gap",
    "details": {
      "term1": "how it's used in document A",
      "term2": "how it's used in document B",
      "location": "specific line or section"
    },
    "confidence": 0.85
  }
]
```

Return ONLY the JSON array, no other text.
