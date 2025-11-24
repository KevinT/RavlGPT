# VERIFY Phase

You are executing the VERIFY phase of a RAVL loop following the RAVL protocol.

## CRITICAL: Domain Quality Verification (Problem Space)

**You are verifying DOMAIN QUALITY** - whether the output meets business requirements.

**What to Verify** (Problem Space):
- ✅ Business rules satisfied (e.g., "stakeholder information present")
- ✅ Data completeness (e.g., "all required fields populated")
- ✅ Domain patterns recognized (e.g., "strategy follows expected structure")
- ✅ Quality thresholds met (e.g., "at least 3 outcomes listed")

**What NOT to Verify** (Solution Space - framework handles this):
- ❌ Code executed successfully
- ❌ API authentication worked
- ❌ Imports resolved
- ❌ No runtime errors occurred

**Why This Matters**:
- Verification failures (domain issues) are stored in `loop_learning/`
- Execution failures (infrastructure issues) are stored in `execution_learning/`
- These are diagnosed and fixed separately by different health checks
- Don't mix execution success with domain quality

**Your Job**: Check if the output is GOOD from a domain perspective, assuming execution succeeded. If code crashed, that's an execution failure (not a verification failure).

## VERIFICATION CRITERIA

{verify_instructions}

## CURRENT OUTPUT TO VERIFY

{action_result}

## CURRENT STATE/CONTEXT

{current_context}

## EVALUATION TASK

Evaluate the current output against each verification criterion.

Additionally, analyze whether regenerating the code would likely improve outcomes:
- **Consider recent execution history** (patterns of repeated failures)
- **Distinguish root causes**: Is this a code logic issue or external factor?
- **Code logic issues** (recommend regeneration): Wrong algorithm, missing logic, incorrect data handling
- **External issues** (don't recommend regeneration): API down, network timeout, rate limiting, authentication

**Regeneration Guidance**:
- Recommend if: Code approach is flawed, same failure pattern 3+ times, logic errors evident
- Don't recommend if: External service issue, transient errors, code working as designed but data unavailable
- **IMPORTANT**: If current context shows "Using CACHED CODE" and same error repeats across multiple attempts,
  this strongly indicates a CODE LOGIC issue (not a transient failure) → recommend regeneration

**Key Indicators for Regeneration**:
1. **Cached code + repeated identical failures** = Code logic issue → REGENERATE
2. **Framework-chosen values failing** (e.g., wrong URL, incorrect API endpoint, bad data source) = Code logic issue → REGENERATE
3. **External service errors** (rate limits, timeouts, authentication failures) = Transient issue → DON'T REGENERATE
4. **One-off failures** with variable errors = May be transient → DON'T REGENERATE (yet)
5. **First or second failure** = Give code benefit of doubt → DON'T REGENERATE (yet)

## Known Unknowns (Domain Questions)

While verifying, identify 3-5 **domain questions** that would help this loop improve:
- **Business context** you lack (e.g., "What defines healthcare delivery for this team?")
- **Missing information** affecting quality assessment (e.g., "What is the expected frequency of facts?")
- **Unclear requirements** that could lead to false positives/negatives
- **Domain concepts** needing clarification (e.g., "What qualifies as 'recent activity'?")

**DO NOT include**:
- Code execution issues (imports, syntax, runtime errors)
- Framework or RAVL implementation questions
- Implementation approach details (that's for ACT phase)

These questions will be saved for human review to improve loop definitions over time.

## SPECIAL CASE: Exploratory/Discovery Loops

**CRITICAL**: Some loops are designed for **progressive discovery** - each run should explore something NEW, not repeat the same exploration.

**Detecting Exploratory Loops** - Look for these patterns in the VERIFICATION CRITERIA or loop context:
- Keywords: "discover **new**", "explore **next**", "**each run**", "**progressive**", "**incremental**", "adds to knowledge", "map unknown territory"
- Explicit run-based progression (e.g., "runs 1-3 do X, runs 4+ do Y")
- Instructions to avoid repetition or to build on previous discoveries
- Goals about expanding knowledge over time

**If loop is exploratory:**
1. Check if current context shows "Using CACHED CODE"
2. If cached + exploratory → **ALWAYS recommend regeneration**
3. Rationale: "Loop requires discovering new things each run, but cached code will execute the same deterministic exploration. Fresh code generation is needed to explore different aspects."

**Exception**: Only skip regeneration recommendation if:
- Code explicitly implements randomization/variation logic
- Code reads previous discoveries and explicitly explores new areas
- Code has adaptive exploration strategy that changes based on history

**Bottom line**: Exploratory loops fundamentally conflict with code caching. When detected, prioritize the loop's learning goal over caching efficiency.

Respond in JSON format:
```json
{{
  "criteria_results": [
    {{"criterion": "description", "passed": true/false, "explanation": "..."}},
    ...
  ],
  "overall_passed": true/false,
  "suggestions": ["improvement 1", "improvement 2", ...],
  "recommend_code_regeneration": true/false,
  "regeneration_rationale": "Brief explanation of why regeneration would/wouldn't help",
  "known_loop_unknowns": [
    "Specific domain question 1?",
    "Specific domain question 2?",
    "Specific domain question 3?"
  ]
}}
```
