# LEARN Phase: Code Regeneration Analysis

You are analyzing whether generated code should be regenerated on the next run.

## CRITICAL: When Code Should Be Regenerated

**Code regeneration is needed when:**
1. **Loop is exploratory/discovery-based** - Each run should explore something NEW
2. **Results are repetitive** - Same discoveries/outcomes across multiple runs
3. **Code is deterministic but loop requires variation** - Code doesn't adapt based on previous learnings
4. **Loop definition explicitly requires progression** - Instructions indicate building on previous runs
5. **Verification keeps failing with same issue** - Code logic is flawed (not transient)

**Code regeneration is NOT needed when:**
1. **Loop is routine/stable** - Same operation each time by design
2. **External issues causing failures** - API down, rate limiting, authentication problems
3. **Code is working well** - High verification scores, meeting objectives
4. **First or second run** - Give code benefit of doubt
5. **Code has adaptive logic** - Already implements variation/progression

## LOOP DEFINITION

### Act Section
{act_instructions}

### Verify Section
{verify_instructions}

## CURRENT RUN ANALYSIS

### Reflection Context
{reflection_summary}

### Action Outcome
{action_summary}

### Verification Results
{verification_summary}

## EXECUTION HISTORY

{execution_history}

## ANALYSIS TASK

Based on the loop definition, current run, and execution history, analyze whether code should be regenerated for the next run.

**Consider:**
1. **Loop Intent** - What is this loop designed to do? Is it exploratory, routine, creative, analytical?
2. **Progression Requirement** - Does the loop explicitly require different behavior each run?
3. **Result Patterns** - Are outcomes repetitive or varied? Are they progressing?
4. **Code Quality** - Is the code achieving its purpose? Are verification scores improving or stagnant?
5. **Failure Patterns** - Are failures due to code logic or external factors?

**Respond in JSON format:**
```json
{{
  "loop_type": "exploratory|routine|creative|analytical",
  "loop_intent": "Brief description of what the loop is designed to do",
  "requires_progression": true/false,
  "progression_evidence": "What in the loop definition indicates progression is needed",
  "result_pattern": "repetitive|varied|improving|degrading",
  "result_pattern_evidence": "Evidence from execution history",
  "code_quality": "excellent|good|fair|poor",
  "code_quality_rationale": "Brief assessment of code effectiveness",
  "recommend_regeneration": true/false,
  "rationale": "Clear, concise explanation of why code should/shouldn't be regenerated",
  "confidence": "high|medium|low"
}}
```

**Examples:**

**Exploratory Loop Example:**
```json
{{
  "loop_type": "exploratory",
  "loop_intent": "Progressively discover and map execution environment",
  "requires_progression": true,
  "progression_evidence": "Act section says 'explore next', 'each run adds to map', 'discover new things'",
  "result_pattern": "repetitive",
  "result_pattern_evidence": "Last 3 runs explored same directories, generated identical insights",
  "code_quality": "good",
  "code_quality_rationale": "Code executes successfully but explores same territory repeatedly",
  "recommend_regeneration": true,
  "rationale": "Exploratory loop with deterministic code = repetitive exploration. Fresh code needed to explore different aspects.",
  "confidence": "high"
}}
```

**Routine Loop Example:**
```json
{{
  "loop_type": "routine",
  "loop_intent": "Fetch daily sales data and compute metrics",
  "requires_progression": false,
  "progression_evidence": "None - loop designed to repeat same operation daily",
  "result_pattern": "varied",
  "result_pattern_evidence": "Data varies by date but operation is consistent (as intended)",
  "code_quality": "excellent",
  "code_quality_rationale": "Code successfully fetches data and computes metrics with 100% pass rate",
  "recommend_regeneration": false,
  "rationale": "Routine loop working perfectly. Code is stable and reliable. No need for regeneration.",
  "confidence": "high"
}}
```
