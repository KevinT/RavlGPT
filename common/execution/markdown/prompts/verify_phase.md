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
  "regeneration_rationale": "Brief explanation of why regeneration would/wouldn't help"
}}
```
