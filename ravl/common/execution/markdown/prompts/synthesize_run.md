# Synthesize Insights from Full RAVL Run

You are analyzing a complete RAVL run (REFLECT → ACT → VERIFY) to extract domain learning insights that will improve future iterations.

## CRITICAL: Focus on Domain, Not Infrastructure

**Domain concerns** (what you SHOULD analyze):
- Quality of context preparation in REFLECT
- Effectiveness of domain decisions/actions in ACT
- Domain quality issues identified in VERIFY
- Business patterns that emerged
- Agency effectiveness

**Infrastructure concerns** (what you should IGNORE):
- Code execution errors
- API authentication issues
- Framework problems
- Dependency/import errors

If VERIFY failed due to execution errors, focus on what domain insights can still be extracted, not the error itself.

## REFLECT Phase Output

{reflection}

## ACT Phase Output

{action_result}

## VERIFY Phase Output

{verification}

## Task

Analyze what happened across the entire run to identify domain learning insights:

### 1. Context Quality Assessment
- Did REFLECT provide useful context to ACT?
- Was relevant historical learning included?
- Were focus areas clear?

### 2. Agency Effectiveness Assessment
- Did ACT make appropriate domain decisions?
- Did ACT take the right actions for the problem?
- Were previous VERIFY suggestions addressed?

### 3. Outcome Quality Assessment
- What did VERIFY say about the results?
- Which domain criteria passed/failed?
- What specific improvements were suggested?

### 4. Pattern Identification
- What domain patterns worked well?
- What domain patterns failed?
- What should be tried differently next time?

## Output Format

Return ONLY valid JSON (no markdown, no explanations):

```json
{{
  "context_quality": {{
    "assessment": "brief assessment of REFLECT context quality",
    "gaps": ["missing context item 1", "missing context item 2"]
  }},
  "agency_effectiveness": {{
    "assessment": "brief assessment of ACT effectiveness",
    "what_worked": ["effective pattern 1", "effective pattern 2"],
    "what_failed": ["ineffective pattern 1"]
  }},
  "verification_outcomes": {{
    "overall_passed": true/false,
    "key_issues": ["issue 1", "issue 2"],
    "suggestions": ["suggestion from VERIFY 1", "suggestion 2"]
  }},
  "strategic_insights": [
    "Cross-phase insight 1",
    "Cross-phase insight 2"
  ],
  "recommendations_for_next_run": [
    "Specific recommendation 1",
    "Specific recommendation 2",
    "Specific recommendation 3"
  ]
}}
```

Focus on actionable insights that will help the next REFLECT prepare better context and the next ACT apply agency more effectively.
