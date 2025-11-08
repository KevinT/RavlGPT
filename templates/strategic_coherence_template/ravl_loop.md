# Strategic Coherence - Parent Loop

Generic parent loop template for coordinating content coherence and external alignment monitoring.

## Reflect

Before coordinating child loops, review the parent loop's learning history to understand patterns and context from previous coordination runs.

Key context to review:
- **Recent meta-learnings** (learnings/): Review the last 3-5 meta-learning files to understand what coordination patterns were discovered
- **Execution history**: Note any recurring execution issues or child loop health trends
- **Coordination patterns** (learnings/model.yml): Review which cross-loop patterns have appeared most frequently

This historical context will inform how you analyze today's child loop findings and what patterns to look for.

## Act

Execute the two child loops in sequence to gather comprehensive findings about content quality and alignment.

```run_child
content_coherence --mode fast
```

```run_child
external_alignment --mode fast --no-fetch-external
```

Now that both child loops have executed, analyze their combined findings to identify cross-loop patterns and meta-insights.

Review the findings from:
1. **Content Coherence**: Gaps and inconsistencies within the documents
2. **External Alignment**: Drift between documents and external sources

Identify cross-loop patterns such as:
- **Terminology Conflicts**: Do terminology issues appear in both child loops? This suggests systemic problems needing coordinated resolution.
- **Structural Misalignments**: Are there structural inconsistencies detected by content coherence that correlate with differences from external sources?
- **High Gap Correlation**: When both loops report high gap counts, this suggests systematic content quality issues.
- **Coverage Gaps**: Are there sections that are both internally inconsistent AND externally misaligned?

For each pattern identified, provide:
- Pattern name
- Severity (info, warning, critical)
- Affected areas (specific sections or gap counts)
- Actionable recommendation

Generate a meta-insights report summarizing:
1. Cross-loop patterns detected (cite actual gaps)
2. Overall content health assessment
3. Priority recommendations for maintainers
4. Coordination suggestions (which gaps should be addressed together)

## Verify

Check that the meta-insights report meets quality standards:

1. **Cross-Loop Analysis**: Meta-insights identify actual patterns across multiple child loops
2. **Evidence-Based**: Each pattern cites specific gaps from child loops as evidence
3. **Actionable Recommendations**: Each insight includes a clear, actionable recommendation
4. **Prioritization**: Insights are prioritized by severity and impact
5. **Novel Insights**: Meta-insights identify correlations and patterns that only emerge when viewing all loops together
6. **Coordination Value**: Recommendations help coordinate responses across loops

## Learn

Analyze execution logs from child loops and extract operational learnings.

**Focus on:**
- Recurring patterns in execution (timeouts, errors, warnings)
- Changes in child loop performance or behavior over time
- Execution issues and their patterns
- Signs of child loop health degradation

**Output:** Write 2-4 concise bullet points summarizing the most important meta-learnings about operational health.

Save these to learnings/ with timestamp to inform future runs.

Track which cross-loop patterns appear most frequently over time and whether meta-insights lead to fewer gaps in future runs.

Update the parent model (learnings/model.yml) with:
- Pattern frequencies (increment counters for patterns found today)
- Coordination learnings
- Execution health trends
- Learning iteration count
