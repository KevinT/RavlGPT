# RAVL Health Checks: Execution vs Domain Learning

## Overview

RAVL provides **two distinct health check systems**, each analyzing a different dimension of loop behavior:

1. **Execution Health Check** - Analyzes SOLUTION SPACE (HOW the framework infrastructure works)
2. **Loop Health Check** - Analyzes PROBLEM SPACE (WHAT the loop learns about its domain)

These health checks are **completely separate** and must never be mixed. They analyze different learning contexts, use separate pattern repositories, and provide different kinds of diagnostics.

---

## The Two Learning Contexts

### Execution Learning (Solution Space)

**Location**: `execution_learning/` directory

**Focus**: HOW to make the RAVL framework infrastructure work correctly

**What It Learns**:
- Code generation success/failure patterns
- DSL convergence and iteration history
- Execution errors (syntax, runtime, imports)
- Cache validation and invalidation
- Framework infrastructure behaviors
- Dependency resolution patterns
- Virtual environment setup issues

**Example Learnings**:
- "Google Sheets API requires OAuth scopes in credentials"
- "DSL inference fails when prompt lacks data source specification"
- "Cached code is invalidated when pip install fails"
- "Import errors indicate missing dependencies in requirements.txt"

**Health Check**: `./ravl --execution-health <loop_name>`

**Purpose**: Diagnose and fix infrastructure problems so the loop can execute successfully

---

### Domain Learning (Problem Space)

**Location**: `loop_learning/` directory

**Focus**: WHAT the loop learns about its business domain

**What It Learns**:
- Domain models and business concepts
- Verification criteria for domain quality
- Domain-specific patterns and insights
- What makes good output for this domain
- Business rules and relationships
- Data quality expectations

**Example Learnings**:
- "FDE Operating Strategy must include stakeholder information"
- "User records should have email, name, and department fields"
- "Documentation imports should preserve hierarchical structure"
- "Verification passes when all required domain fields are present"

**Health Check**: `./ravl --loop-health <loop_name>`

**Purpose**: Diagnose and improve domain knowledge acquisition and verification quality

---

## Health Check Architecture

### Shared Infrastructure Pattern

Both health checks use the same sophisticated architecture, but with **completely separate implementations**:

1. **LLM-Powered Diagnostics**
   - Execution: `ExecutionLLMAnalyzer` with `prompts/execution_diagnosis.md`
   - Domain: `DomainLLMAnalyzer` with `prompts/domain_diagnosis.md`

2. **Persistent Thread Management**
   - Execution: `ExecutionThreadManager` storing in `threads/execution_{loop}.jsonl`
   - Domain: `DomainThreadManager` storing in `threads/domain_{loop}.jsonl`

3. **Cross-Loop Pattern Learning**
   - Execution: `ExecutionPatternRepository` storing in `execution_patterns.jsonl`
   - Domain: `DomainPatternRepository` storing in `domain_patterns.jsonl`

4. **Data Discovery**
   - Execution: `ExecutionDataDiscovery` reading from `execution_learning/`
   - Domain: `DomainDataDiscovery` reading from `loop_learning/`

5. **Multiple Report Types**
   - Both: healthy, failing, stale, moderate
   - But analyze completely different metrics

6. **State Transition Detection**
   - Both: Track broken → fixed recoveries
   - But for different problem spaces

---

## When to Use Each Health Check

### Use Execution Health Check When:

- ❌ Loop fails to start or crashes during execution
- ❌ Code generation is failing or producing invalid code
- ❌ DSL inference isn't converging
- ❌ Execution errors (syntax, imports, runtime exceptions)
- ❌ Cache invalidation is happening repeatedly
- ❌ Dependency installation problems
- ❌ Virtual environment setup issues

**Command**: `./ravl --execution-health <loop_name>`

**Example Output**:
```
❌ Execution Health: FAILING
   Success rate: 20%

🔍 Root Cause: Generated code lacks proper OAuth scopes for Google API authentication

💡 Recommended Steps:
   1. Review credentials pattern in code generation prompt
   2. Update prompt to include scope specification
   3. Add scope validation to credential setup
   4. Clear code cache to force regeneration
```

---

### Use Loop Health Check When:

- ✅ Loop executes successfully BUT verification is failing
- ✅ Domain model isn't evolving or capturing key concepts
- ✅ Verification criteria are consistently not met
- ✅ Domain patterns aren't being recognized
- ✅ Business rules aren't being learned
- ✅ Data quality is poor despite successful execution

**Command**: `./ravl --loop-health <loop_name>`

**Example Output**:
```
❌ Domain Learning Health: FAILING
   Verification pass rate: 30%

🔍 Root Cause: Domain model not capturing stakeholder information from source documents

💡 Recommended Steps:
   1. Review verification criteria to understand required domain fields
   2. Check if data source provides stakeholder information
   3. Update domain model schema to include stakeholder fields
   4. Adjust pattern recognition to extract stakeholder data
```

---

## Health Check Workflow

### Execution Health Check Workflow

```
1. REFLECT
   - Discover DSL iterations, code cache, execution logs
   - Load failure analysis history
   - Check recent execution success rate

2. ACT
   - Route to report type (healthy/failing/stale/moderate)
   - For failures: Analyze with LLM using execution context
   - Use cross-loop patterns for few-shot learning
   - Generate actionable infrastructure fixes

3. VERIFY
   - Confirm diagnostic was successful
   - Extract domain health status

4. LEARN
   - Extract high-confidence diagnoses as patterns
   - Track state transitions (broken → fixed)
   - Update execution pattern repository
   - Append to persistent diagnostic thread
```

### Loop Health Check Workflow

```
1. REFLECT
   - Discover domain models, verification results
   - Load domain metrics and learned patterns
   - Check verification pass rate and model evolution

2. ACT
   - Route to report type (healthy/failing/stale/moderate)
   - For failures: Analyze with LLM using domain context
   - Use cross-loop domain patterns for few-shot learning
   - Generate actionable domain improvements

3. VERIFY
   - Confirm diagnostic was successful
   - Extract domain health status

4. LEARN
   - Extract high-confidence diagnoses as domain patterns
   - Track state transitions (broken → fixed)
   - Update domain pattern repository
   - Append to persistent diagnostic thread
```

---

## Cross-Loop Pattern Learning

### Execution Patterns

**Storage**: `.ravl/ravl_loops/health_checks/execution_health_check/learnings/execution_patterns.jsonl`

**Pattern Structure**:
```json
{
  "id": "execution_loop123_20250101_120000",
  "source_loop": "loop_name",
  "issue_type": "code_generation|dsl|cache|execution_error",
  "root_cause": "Description of infrastructure problem",
  "solution_steps": ["Step 1", "Step 2", "Step 3"],
  "confidence": 0.85,
  "timestamp": "2025-01-01T12:00:00Z",
  "success_count": 3,
  "pattern_type": "execution"
}
```

**Used By**: ExecutionLLMAnalyzer as few-shot examples when diagnosing similar execution failures

---

### Domain Patterns

**Storage**: `.ravl/ravl_loops/health_checks/loop_health_check/learnings/domain_patterns.jsonl`

**Pattern Structure**:
```json
{
  "id": "domain_loop456_20250101_120000",
  "source_loop": "loop_name",
  "issue_type": "domain",
  "root_cause": "Description of domain learning problem",
  "solution_steps": ["Step 1", "Step 2", "Step 3"],
  "confidence": 0.90,
  "timestamp": "2025-01-01T12:00:00Z",
  "success_count": 2,
  "pattern_type": "domain"
}
```

**Used By**: DomainLLMAnalyzer as few-shot examples when diagnosing similar domain learning failures

---

## Persistent Diagnostic Threads

Both health checks maintain **separate conversation threads** that accumulate over time:

### Execution Thread

**Storage**: `.ravl/ravl_loops/health_checks/execution_health_check/learnings/threads/execution_{loop_name}.jsonl`

**Purpose**: Build up diagnostic history for infrastructure problems across multiple runs

**Format**:
```json
{
  "turn_number": 1,
  "timestamp": "2025-01-01T12:00:00Z",
  "diagnostic_type": "execution",
  "input": {"failures": [...], "context": {...}},
  "output": {"root_cause": "...", "steps": [...], "confidence": 85}
}
```

---

### Domain Thread

**Storage**: `.ravl/ravl_loops/health_checks/loop_health_check/learnings/threads/domain_{loop_name}.jsonl`

**Purpose**: Build up diagnostic history for domain learning problems across multiple runs

**Format**:
```json
{
  "turn_number": 1,
  "timestamp": "2025-01-01T12:00:00Z",
  "diagnostic_type": "domain",
  "input": {"verification_failures": [...], "context": {...}},
  "output": {"root_cause": "...", "steps": [...], "confidence": 90}
}
```

---

## Report Types

Both health checks provide four report types, but analyze completely different metrics:

### Healthy Reports

**Execution**: Execution success rate > 80%, DSL convergence stable, no recent failures
**Domain**: Verification pass rate > 80%, model actively evolving, patterns being learned

**Output**: Proactive improvement suggestions for optimization

---

### Failing Reports

**Execution**: Execution success rate < 30%, repeated failures, DSL not converging
**Domain**: Verification pass rate < 30%, model stagnant, criteria not being met

**Output**: LLM-powered root cause analysis + actionable steps

---

### Stale Reports

**Execution**: No recent execution attempts in execution_learning/
**Domain**: No recent verification attempts in loop_learning/

**Output**: Simple message indicating no activity

---

### Moderate Reports

**Execution**: Success rate between 30-80%, some execution issues
**Domain**: Pass rate between 30-80%, some verification issues

**Output**: List of specific issues with severity levels

---

## Examples

### Example 1: Execution Failure

**Scenario**: Loop is crashing with import errors

**Command**: `./ravl --execution-health my_loop`

**Diagnosis**:
```
❌ Execution Health: FAILING

🔍 Root Cause: Generated code imports google-auth-oauthlib but package not in requirements

💡 Recommended Steps:
   1. Check learnings/execution_learning/generated_requirements.txt for missing packages
   2. Add google-auth-oauthlib to allowed_dependencies in config/ravl.yml
   3. Re-run loop to install approved dependency
   4. Verify execution succeeds
```

**Learning Stored**: Execution pattern about dependency approval workflow

---

### Example 2: Domain Learning Failure

**Scenario**: Loop runs successfully but verification always fails

**Command**: `./ravl --loop-health my_loop`

**Diagnosis**:
```
❌ Domain Learning Health: FAILING

🔍 Root Cause: Domain model missing stakeholder fields required by verification criteria

💡 Recommended Steps:
   1. Review verification criteria in loop_learning/verification_*.yml
   2. Identify required stakeholder fields
   3. Update domain model schema to capture stakeholders
   4. Re-run loop to validate improved model
```

**Learning Stored**: Domain pattern about model completeness and verification alignment

---

### Example 3: Healthy Loop with Improvement Suggestions

**Command**: `./ravl --loop-health my_loop`

**Output**:
```
✅ Domain Learning Health: HEALTHY
   Verification pass rate: 85%

💡 Domain Improvement Suggestions:

1. **Enrich Stakeholder Context**: Model currently captures stakeholder names but not roles
   - Implementation: Add role field to stakeholder schema; extract from "Role:" patterns in docs

2. **Add Temporal Tracking**: Capture when strategy documents were last updated
   - Implementation: Add last_updated field; extract from document metadata

3. **Pattern Recognition Enhancement**: Detect cross-document references
   - Implementation: Add reference_graph to model; parse hyperlinks and @mentions
```

---

## Design Principles

### Why Separate Health Checks?

1. **Clear Context Setting**: Each health check provides focused context to LLM for diagnosis
2. **Prevents Cross-Contamination**: Execution errors don't pollute domain learning
3. **Specialized Prompts**: Execution prompts focus on infrastructure; domain prompts focus on business logic
4. **Independent Pattern Learning**: Execution patterns and domain patterns serve different purposes
5. **Precise Diagnostics**: Problems are diagnosed at the right level of abstraction

### Why Never Mix Them?

- Mixing execution and domain context creates **ambiguous diagnostics**
- LLM can't provide focused advice when problem space is unclear
- Patterns lose meaning when they span different abstraction levels
- Health checks become generic rather than specialized
- Auto-healing becomes unreliable

---

## CLI Usage

### Running Health Checks

```bash
# Check execution infrastructure health
./ravl --execution-health <loop_name>

# Check domain learning health
./ravl --loop-health <loop_name>

# Run both (sequentially)
./ravl --execution-health <loop_name> && ./ravl --loop-health <loop_name>
```

### Health Check Output Location

Both health checks store their own learning artifacts:

```
.ravl/ravl_loops/health_checks/
  execution_health_check/
    learnings/
      execution_patterns.jsonl      # Cross-loop execution patterns
      threads/
        execution_{loop}.jsonl      # Per-loop diagnostic threads
      model.yml                     # Health check's own model

  loop_health_check/
    learnings/
      domain_patterns.jsonl         # Cross-loop domain patterns
      threads/
        domain_{loop}.jsonl         # Per-loop diagnostic threads
      model.yml                     # Health check's own model
```

---

## Integration with RAVL Workflow

Health checks are **diagnostic tools**, not part of normal loop execution:

1. **Normal Loop Run**: Loop executes, learns, stores results in execution_learning/ and loop_learning/
2. **When Things Break**: Run appropriate health check to diagnose
3. **Health Check Analyzes**: Reads learning artifacts, generates diagnosis
4. **Developer Acts**: Follows recommended steps to fix issue
5. **Re-run Loop**: Verify fix worked
6. **Health Check Learns**: Extracts successful diagnosis as pattern for future use

Health checks **do not modify** the target loop. They only analyze and advise.

---

## Advanced Features

### State Transition Detection

Both health checks detect when loops recover from failures:

```python
# Detected in learn() phase
prev_state = self.model.get('previous_states', {}).get(target_loop)
current_state = action_result.get('status')

if prev_state == 'failing' and current_state == 'healthy':
    print(f"✅ State transition detected: {target_loop} recovered!")
```

This helps track which diagnostic actions led to successful recovery.

---

### Few-Shot Learning with Patterns

When diagnosing failures, health checks use top 5 most relevant patterns as examples:

```python
# Get cross-loop patterns
patterns = self.pattern_repository.get_patterns_for_loop(target_loop)

# Use in LLM prompt
diagnosis = self.llm_analyzer.analyze_execution_failure(
    failures=failures,
    execution_context=context,
    learned_patterns=patterns[:5]  # Top 5 patterns as few-shot examples
)
```

This enables transfer learning from similar problems in other loops.

---

### Confidence-Based Pattern Extraction

Only high-confidence diagnoses become patterns:

```python
if diagnosis.get('confidence', 0) < 0.7:
    return  # Don't extract low-confidence patterns
```

This ensures pattern repository quality remains high.

---

## Summary

| Aspect | Execution Health Check | Loop Health Check |
|--------|----------------------|-------------------|
| **Focus** | Solution Space (HOW framework works) | Problem Space (WHAT loop learns) |
| **Data Source** | `execution_learning/` | `loop_learning/` |
| **Diagnoses** | Code gen, DSL, execution errors | Verification failures, model stagnation |
| **Pattern Storage** | `execution_patterns.jsonl` | `domain_patterns.jsonl` |
| **Thread Storage** | `threads/execution_{loop}.jsonl` | `threads/domain_{loop}.jsonl` |
| **CLI Command** | `./ravl --execution-health <loop>` | `./ravl --loop-health <loop>` |
| **LLM Analyzer** | `ExecutionLLMAnalyzer` | `DomainLLMAnalyzer` |
| **Example Issue** | "Missing OAuth scopes in credentials" | "Model missing stakeholder fields" |

---

## Next Steps

**To use health checks effectively**:
1. Run normal loop: `./ravl my_loop`
2. If execution fails → `./ravl --execution-health my_loop`
3. If verification fails → `./ravl --loop-health my_loop`
4. Follow recommended steps
5. Re-run and verify fix worked

**To learn more**:
- See [learning_separation.md](learning_separation.md) for deep dive on problem/solution space separation
- See [RAVL_VISION.md](RAVL_VISION.md) Principle 9 for philosophical foundation
- Check health check source code in `.ravl/ravl_loops/health_checks/`
