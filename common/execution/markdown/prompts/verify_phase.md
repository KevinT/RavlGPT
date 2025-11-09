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

Respond in JSON format:
```json
{{
  "criteria_results": [
    {{"criterion": "description", "passed": true/false, "explanation": "..."}},
    ...
  ],
  "overall_passed": true/false,
  "suggestions": ["improvement 1", "improvement 2", ...]
}}
```
