# Synthesize Domain Learnings for ACT Context

You are building actionable context for the ACT phase by synthesizing domain learnings from previous RAVL iterations.

## CRITICAL: Focus on Domain Guidance, Not Infrastructure

**Domain guidance** (what you SHOULD provide):
- Business patterns that worked/failed
- Domain decisions that were effective/ineffective
- Verification suggestions about domain quality
- Agency strategies to try
- Focus areas for domain improvement

**Infrastructure guidance** (what you should IGNORE):
- Code execution fixes
- API authentication solutions
- Framework improvements
- Dependency management

ACT needs to know HOW to apply its agency effectively in the problem domain, not how to fix code.

## Previous Run Insights

{run_insights}

## Recent Verification Suggestions

{verification_suggestions}

## Performance Metrics

{performance_metrics}

## Historical Patterns

{historical_patterns}

## Task

Create clear, actionable guidance for the next ACT phase based on these learnings.

### What to Extract:

1. **Priority Focus**: Most important domain concerns to address (from VERIFY suggestions)
2. **Successful Patterns**: Domain approaches that worked well and should be repeated
3. **Failed Patterns**: Domain approaches that didn't work and should be avoided
4. **New Strategies**: Ideas for different domain approaches to try
5. **Context Gaps**: What additional context would help ACT be more effective

### Guidelines:

- Be specific and actionable (not "improve quality" but "add validation for X field")
- Focus on domain decisions, not code implementation
- Prioritize suggestions from recent VERIFY failures
- Include patterns that repeatedly succeed or fail
- Suggest concrete next steps

## Output Format

Return ONLY valid JSON (no markdown, no explanations):

```json
{{
  "priority_focus": [
    "Most critical domain issue to address this run"
  ],
  "successful_patterns": [
    "Domain pattern 1 that consistently works",
    "Domain pattern 2 that consistently works"
  ],
  "failed_patterns": [
    "Domain pattern 1 that consistently fails",
    "Domain pattern 2 that consistently fails"
  ],
  "new_strategies_to_try": [
    "Specific new domain approach 1",
    "Specific new domain approach 2"
  ],
  "context_needs": [
    "Additional context that would help ACT",
    "Data or insights currently missing"
  ],
  "verification_notes": {{
    "recent_failures": ["Domain issue 1", "Domain issue 2"],
    "success_criteria": ["What VERIFY looks for in good results"]
  }}
}}
```

This guidance will be passed directly to ACT in its prompt, so make it clear, specific, and immediately actionable.
