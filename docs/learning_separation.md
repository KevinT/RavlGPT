# Learning Separation: Problem Space vs Solution Space

## Document Purpose

This document provides a **deep dive** into RAVL's fundamental separation of Problem Space (domain learning) and Solution Space (execution learning). It explains the rationale, implementation patterns, and guidelines for maintaining this separation across the framework.

**Audience**: Framework developers, AI coding assistants, and anyone extending RAVL's learning capabilities.

---

## The Core Insight

RAVL loops learn about **two fundamentally different domains**:

1. **Problem Space (Domain Learning)**: The business problem the loop is solving
2. **Solution Space (Execution Learning)**: The technical infrastructure that makes the loop work

These domains are **orthogonal** and must never be mixed. Conflating them creates ambiguous diagnostics, unreliable auto-healing, and confusion about what kind of learning is happening.

---

## The Philosophy: Domain-Driven Design Meets Learning Systems

This separation comes from **Domain-Driven Design (DDD)** principles applied to learning systems:

### In Traditional DDD

- **Domain Layer**: Business logic and domain concepts (e.g., "User", "Order", "Invoice")
- **Infrastructure Layer**: Technical concerns (e.g., database, API, caching)

### In RAVL Learning

- **Domain Learning (Problem Space)**: What the loop learns about its business domain
- **Execution Learning (Solution Space)**: What the loop learns about making RAVL infrastructure work

Just as you wouldn't mix SQL queries into domain models, you shouldn't mix execution errors into domain learning.

---

## Problem Space: Domain Learning

### What It Is

Domain learning captures **what the loop discovers about its business problem**—the concepts, patterns, and quality criteria specific to its domain.

### What It Stores

**Location**: `loop_learning/`

**Artifacts**:
- **model.yml**: Current domain model with business concepts
- **model-TIMESTAMP.yml**: Historical models showing domain evolution
- **verification_*.yml**: Verification results against domain quality criteria
- **history/domain_metrics.jsonl**: Domain quality metrics over time
- **learned_patterns.jsonl**: Domain-specific patterns discovered

### Example Domain Learning

**Loop**: FDE Operating Strategy Ingestion

**Domain Learning Artifacts**:
```yaml
# loop_learning/model.yml
domain_schema:
  strategy_document:
    required_fields:
      - title
      - context
      - approach
      - outcomes
      - stakeholders

  stakeholders:
    fields:
      - name
      - role
      - department

verification_criteria:
  - all_required_fields_present
  - stakeholders_have_roles
  - outcomes_are_measurable

patterns_learned:
  - "FDE strategy docs always have 3-5 stakeholders"
  - "Context section typically 2-4 paragraphs"
  - "Outcomes are bulleted lists with metrics"
```

**Domain Learnings (Natural Language)**:
- "Operating strategy documents follow a consistent structure"
- "Stakeholder information is always in a dedicated section"
- "Good strategies have measurable outcomes"
- "Context explains the business problem being solved"

**What This Enables**:
- Loop improves at recognizing valid strategy documents
- Verification criteria evolve to match domain expectations
- Domain model captures richer business concepts over time
- Pattern recognition becomes more sophisticated

---

## Solution Space: Execution Learning

### What It Is

Execution learning captures **what the loop discovers about making RAVL infrastructure work**—the technical patterns, error recoveries, and framework behaviors needed for successful execution.

### What It Stores

**Location**: `execution_learning/`

**Artifacts**:
- **dsl_iteration_N.json**: DSL generation attempts and convergence
- **verified_code.py**: Cached working code after successful execution
- **verified_dsl.json**: Cached DSL after successful convergence
- **history/failure_analysis.jsonl**: Execution error patterns
- **history/initialization_failures/**: Pre-RAVL startup failures

### Example Execution Learning

**Loop**: FDE Operating Strategy Ingestion

**Execution Learning Artifacts**:
```json
// execution_learning/verified_dsl.json
{
  "code_generation_context": {
    "data_sources": ["google_docs_api"],
    "authentication": "oauth2_user_credentials",
    "required_scopes": ["https://www.googleapis.com/auth/documents.readonly"]
  }
}
```

```python
# execution_learning/verified_code.py
# Working code that successfully executes

import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load credentials from environment
cred_info = json.loads(os.environ['GOOGLE_CREDENTIALS'])
credentials = service_account.Credentials.from_service_account_info(
    cred_info,
    scopes=['https://www.googleapis.com/auth/documents.readonly']
)

# Rest of working code...
```

```json
// execution_learning/history/failure_analysis.jsonl
{
  "error_type": "authentication_error",
  "pattern": "Google API returned 403: insufficient authentication scopes",
  "fix": "Added documents.readonly scope to credentials",
  "occurrence_count": 3
}
```

**Execution Learnings (Natural Language)**:
- "Google Docs API requires OAuth scopes in credentials"
- "Credentials must be loaded from GOOGLE_CREDENTIALS env var"
- "Missing scopes cause 403 errors"
- "Service account credentials need proper scope specification"

**What This Enables**:
- Framework auto-heals authentication issues
- Code generation learns correct credential patterns
- DSL inference incorporates scope requirements
- Cache invalidation detects authentication changes

---

## Why Separation Matters

### Problem 1: Ambiguous Context

**Without Separation**:
```
Learning Artifact (Mixed):
- "Google Docs import requires stakeholder information"

What does this mean?
- Does Google Docs API require a stakeholder field? (execution)
- Do strategy documents require stakeholder information? (domain)
- Both? Neither?

LLM receives ambiguous context and can't provide focused advice.
```

**With Separation**:
```
Execution Learning:
- "Google Docs API requires documents.readonly scope"

Domain Learning:
- "Strategy documents require stakeholder section for verification to pass"

Clear, unambiguous, independently actionable.
```

---

### Problem 2: Cross-Contamination

**Without Separation**:
```
Scenario: Authentication fails (execution problem)

Without separation:
- Error stored in generic "learnings"
- Next run reads mixed context
- Domain verification criteria get polluted with execution patterns
- Model evolution conflates infrastructure with domain
- Verification becomes unreliable

Result: Can't tell if failures are infrastructure or domain issues
```

**With Separation**:
```
Scenario: Authentication fails (execution problem)

With separation:
- Error stored in execution_learning/
- Next run reads execution context only during code generation
- Domain learning stays pure (stakeholder patterns, field requirements)
- Model evolution focuses on domain concepts only

Result: Clear diagnosis → execution health check → fix authentication → re-run
```

---

### Problem 3: Ineffective Auto-Healing

**Without Separation**:
```
Framework tries to auto-heal:
- Reads mixed learnings
- Can't tell what kind of fix is needed
- Applies domain fix to execution problem (wrong abstraction)
- Or execution fix to domain problem (wrong abstraction)

Result: Auto-healing is unreliable and often makes things worse
```

**With Separation**:
```
Framework auto-heals execution issues:
- Reads execution_learning/ only
- Identifies authentication pattern
- Generates code with correct scopes
- Execution succeeds

Domain learning untouched:
- Still knows stakeholder requirements
- Still validates document structure
- Continues to evolve domain model

Result: Precise, reliable auto-healing at correct abstraction level
```

---

## Implementation Patterns

### Storage Structure

```
ravl_learning/
  {hierarchy}/
    {loop_name}/
      execution_learning/         # SOLUTION SPACE
        dsl_iteration_N.json
        verified_code.py
        verified_dsl.json
        history/
          failure_analysis.jsonl
          initialization_failures/

      loop_learning/              # PROBLEM SPACE
        model.yml
        model-TIMESTAMP.yml
        verification_*.yml
        history/
          domain_metrics.jsonl
        learned_patterns.jsonl
```

**Rule**: Code NEVER reads from both directories in the same operation.

---

### Separate Infrastructure Classes

Every learning-related component has **two versions**:

| Solution Space | Problem Space |
|---------------|--------------|
| `ExecutionLLMAnalyzer` | `DomainLLMAnalyzer` |
| `ExecutionThreadManager` | `DomainThreadManager` |
| `ExecutionPatternRepository` | `DomainPatternRepository` |
| `ExecutionDataDiscovery` | `DomainDataDiscovery` |
| `execution_patterns.jsonl` | `domain_patterns.jsonl` |
| `threads/execution_{loop}.jsonl` | `threads/domain_{loop}.jsonl` |

**Rule**: These classes NEVER share data structures, NEVER call each other, NEVER read each other's storage.

---

### Separate Prompts with Explicit Focus

**Execution Diagnosis Prompt** (`execution_diagnosis.md`):
```markdown
**CRITICAL: You are analyzing SOLUTION SPACE (execution infrastructure) ONLY**

Your job is to focus on HOW to make the RAVL framework execute properly:
- Code generation failures
- DSL convergence problems
- Execution errors (syntax, runtime, imports)
- Cache invalidation issues
- Framework infrastructure problems

**DO NOT suggest changes to domain logic, verification criteria, or business rules.**
**Focus ONLY on making the infrastructure work.**
```

**Domain Diagnosis Prompt** (`domain_diagnosis.md`):
```markdown
**CRITICAL: You are analyzing PROBLEM SPACE (domain learning) ONLY**

Your job is to focus on WHAT the loop learns about its domain:
- Domain model stagnation or regression
- Verification criteria not being met
- Domain pattern recognition failures
- Business logic learning issues
- Learned insights not improving over time

**DO NOT suggest changes to code generation, DSL, or framework infrastructure.**
**Focus ONLY on domain knowledge acquisition.**
```

**Rule**: Prompts explicitly forbid cross-contamination and state their focus in ALL CAPS.

---

### Separate Health Checks

**Execution Health Check**:
- **Location**: `.ravl/ravl_loops/health_checks/execution_health_check/`
- **Data Source**: `execution_learning/`
- **Analyzes**: Code generation, DSL, execution errors, cache
- **Outputs**: Infrastructure fixes

**Loop Health Check**:
- **Location**: `.ravl/ravl_loops/health_checks/loop_health_check/`
- **Data Source**: `loop_learning/`
- **Analyzes**: Verification results, model evolution, domain patterns
- **Outputs**: Domain improvements

**Rule**: Health checks NEVER read data from the other space's directory.

---

## Context Setting During Execution

### When Loop Runs

RAVL loops receive context from **both spaces** at different times:

**Phase 1: Code Generation (Solution Space)**
```python
# Framework reads execution_learning/ to inform code generation
execution_context = load_execution_learning(loop_dir / 'execution_learning')

# Context includes:
# - Previous execution failures
# - Working code patterns
# - DSL convergence history
# - Authentication patterns

generated_code = llm_generate_code(
    user_intent=loop_definition,
    execution_context=execution_context  # Solution space only
)
```

**Phase 2: Loop Execution (Problem Space)**
```python
# Generated code reads loop_learning/ during RAVL cycle
domain_model = load_model(loop_dir / 'loop_learning' / 'model.yml')

# Reflect phase uses domain context:
reflection = loop.reflect()  # Uses domain_model for context

# Verify phase validates against domain criteria
verification = loop.verify(action, reflection)  # Domain quality checks

# Learn phase updates domain model
loop.learn(verification, action)  # Evolves domain understanding
```

**Rule**: Execution context and domain context are NEVER mixed in the same LLM call or data structure.

---

## Guidelines for Maintaining Separation

### For Framework Developers

1. **New Learning Feature?**
   - Ask: Is this about HOW framework works (execution) or WHAT loop learns (domain)?
   - Create separate implementations for each space
   - Never share data structures between them

2. **New Prompt Template?**
   - Add explicit focus statement at top
   - Forbid suggestions from other space
   - Use separate prompt files for execution vs domain

3. **New Health Check Feature?**
   - Implement in BOTH health checks separately
   - Never add shared code that reads from both spaces
   - Use separate pattern repositories

4. **New Storage?**
   - Put in `execution_learning/` or `loop_learning/`, never both
   - Document which space it belongs to
   - Ensure file names indicate space (e.g., `domain_metrics.jsonl` vs `execution_logs.jsonl`)

---

### For AI Coding Assistants

1. **Before Adding Learning Logic**:
   - Identify which space the learning belongs to
   - Check existing implementations in that space
   - Never copy code from other space without adapting it

2. **When Reading Context**:
   - Confirm you're in the right directory (`execution_learning/` vs `loop_learning/`)
   - Don't read from both in the same operation
   - Verify prompts have explicit focus statements

3. **When Generating Diagnostics**:
   - Use execution health check for infrastructure issues
   - Use loop health check for domain issues
   - Never mix diagnostic types in output

4. **When Updating Documentation**:
   - Emphasize separation in all learning-related docs
   - Use consistent terminology (Problem Space / Solution Space)
   - Provide examples showing both spaces separately

---

## Common Mistakes and How to Avoid Them

### Mistake 1: Shared Pattern Repository

**Wrong**:
```python
# Single pattern repository used by both health checks
pattern_repo = PatternRepository('patterns.jsonl')
execution_check.use_patterns(pattern_repo)
domain_check.use_patterns(pattern_repo)  # ❌ WRONG
```

**Right**:
```python
# Separate pattern repositories
execution_patterns = ExecutionPatternRepository('execution_patterns.jsonl')
domain_patterns = DomainPatternRepository('domain_patterns.jsonl')

execution_check.use_patterns(execution_patterns)  # ✅ Correct
domain_check.use_patterns(domain_patterns)  # ✅ Correct
```

---

### Mistake 2: Generic "Learnings" Directory

**Wrong**:
```
ravl_learning/
  {loop_name}/
    learnings/               # ❌ WRONG: Ambiguous
      model.yml
      code_cache.py
      failure_history.jsonl
```

**Right**:
```
ravl_learning/
  {loop_name}/
    execution_learning/      # ✅ Correct: Solution space
      verified_code.py
      history/failure_analysis.jsonl

    loop_learning/           # ✅ Correct: Problem space
      model.yml
      verification_*.yml
```

---

### Mistake 3: Ambiguous Prompts

**Wrong**:
```markdown
# health_check_prompt.md
Analyze this loop's failures and suggest fixes.

Context: {all_learnings}  # ❌ WRONG: Mixed context
```

**Right**:
```markdown
# execution_diagnosis.md
**CRITICAL: You are analyzing SOLUTION SPACE (execution infrastructure) ONLY**

Analyze execution failures and suggest infrastructure fixes.

Context: {execution_learnings_only}  # ✅ Correct: Pure context
```

---

### Mistake 4: Cross-Space Data Access

**Wrong**:
```python
class HealthCheck:
    def diagnose(self):
        # ❌ WRONG: Reading from both spaces
        exec_data = self.load_execution_data()
        domain_data = self.load_domain_data()

        # Mixed analysis
        return self.llm_analyze({
            'execution': exec_data,
            'domain': domain_data
        })
```

**Right**:
```python
class ExecutionHealthCheck:
    def diagnose(self):
        # ✅ Correct: Only execution space
        exec_data = self.load_execution_data()
        return self.llm_analyze_execution(exec_data)

class LoopHealthCheck:
    def diagnose(self):
        # ✅ Correct: Only domain space
        domain_data = self.load_domain_data()
        return self.llm_analyze_domain(domain_data)
```

---

## Testing the Separation

### Unit Tests

```python
def test_execution_patterns_have_correct_type():
    """Execution patterns must have pattern_type='execution'"""
    repo = ExecutionPatternRepository('test_patterns.jsonl')
    pattern = {
        'id': 'test',
        'pattern_type': 'execution',  # Required
        'root_cause': 'Test execution issue'
    }
    repo.add_pattern(pattern)

    loaded = repo.get_patterns()
    assert all(p['pattern_type'] == 'execution' for p in loaded)

def test_domain_patterns_have_correct_type():
    """Domain patterns must have pattern_type='domain'"""
    repo = DomainPatternRepository('test_patterns.jsonl')
    pattern = {
        'id': 'test',
        'pattern_type': 'domain',  # Required
        'root_cause': 'Test domain issue'
    }
    repo.add_pattern(pattern)

    loaded = repo.get_patterns()
    assert all(p['pattern_type'] == 'domain' for p in loaded)

def test_threads_have_correct_diagnostic_type():
    """Thread turns must have correct diagnostic_type tag"""
    exec_mgr = ExecutionThreadManager('exec_thread.jsonl')
    exec_mgr.append_turn({'test': 'input'}, {'test': 'output'})

    history = exec_mgr.get_thread_history()
    assert all(turn['diagnostic_type'] == 'execution' for turn in history)
```

---

### Integration Tests

```python
def test_execution_health_check_only_reads_execution_learning():
    """Execution health check must not access domain learning"""
    loop = create_test_loop()

    # Mock file access
    with patch('pathlib.Path.exists') as mock_exists:
        with patch('builtins.open') as mock_open:
            health_check = ExecutionHealthCheck(loop)
            health_check.run()

            # Verify only execution_learning/ was accessed
            accessed_paths = [call[0][0] for call in mock_open.call_args_list]
            assert all('execution_learning' in str(p) for p in accessed_paths)
            assert not any('loop_learning' in str(p) for p in accessed_paths)

def test_loop_health_check_only_reads_loop_learning():
    """Loop health check must not access execution learning"""
    loop = create_test_loop()

    with patch('pathlib.Path.exists') as mock_exists:
        with patch('builtins.open') as mock_open:
            health_check = LoopHealthCheck(loop)
            health_check.run()

            # Verify only loop_learning/ was accessed
            accessed_paths = [call[0][0] for call in mock_open.call_args_list]
            assert all('loop_learning' in str(p) for p in accessed_paths)
            assert not any('execution_learning' in str(p) for p in accessed_paths)
```

---

## Examples

### Example 1: Authentication Error (Solution Space)

**Problem**: Loop crashes with "403 Insufficient Authentication Scopes"

**Execution Learning Captures**:
```json
{
  "error_type": "authentication_error",
  "error_message": "403: insufficient authentication scopes",
  "context": {
    "api": "google_docs",
    "credentials_type": "service_account"
  },
  "fix_pattern": "Add documents.readonly scope to credentials"
}
```

**Execution Health Check Diagnosis**:
```
❌ Execution Health: FAILING

🔍 Root Cause: Google API credentials missing required scopes

💡 Recommended Steps:
   1. Update GOOGLE_CREDENTIALS environment variable
   2. Add "documents.readonly" to scopes array
   3. Re-authenticate and obtain new token
   4. Clear code cache and re-run
```

**Domain Learning**: Untouched (still knows document structure, stakeholder requirements, etc.)

---

### Example 2: Verification Failure (Problem Space)

**Problem**: Loop executes successfully but verification always fails

**Domain Learning Captures**:
```yaml
# loop_learning/verification_TIMESTAMP.yml
overall_passed: false
failed_criteria:
  - name: "stakeholder_information_present"
    expected: "model contains stakeholder fields"
    actual: "model missing stakeholder section"
```

**Loop Health Check Diagnosis**:
```
❌ Domain Learning Health: FAILING

🔍 Root Cause: Domain model not capturing stakeholder information from documents

💡 Recommended Steps:
   1. Review document structure to locate stakeholder info
   2. Update model schema to include stakeholder fields
   3. Add pattern recognition for stakeholder sections
   4. Re-run verification to confirm improvement
```

**Execution Learning**: Untouched (still knows how to authenticate, generate code, etc.)

---

## Summary

### The Separation in One Sentence

**Execution learning is about HOW to make RAVL work; domain learning is about WHAT the loop learns—they must never be mixed.**

### Key Principles

1. **Orthogonal Domains**: Execution and domain are independent learning spaces
2. **Separate Storage**: `execution_learning/` vs `loop_learning/`
3. **Separate Infrastructure**: Completely independent classes, prompts, patterns
4. **Separate Health Checks**: Specialized diagnostics for each space
5. **Pure Context**: Never mix execution and domain context in same operation
6. **Explicit Focus**: All prompts state their space in CRITICAL warnings

### Benefits

- **Clear Diagnostics**: Problems diagnosed at correct abstraction level
- **Reliable Auto-Healing**: Framework fixes infrastructure without touching domain
- **Pattern Quality**: Patterns remain focused and actionable
- **Model Integrity**: Domain models evolve based on domain insights only
- **Maintainability**: Separation of concerns makes system easier to understand

### The Rule

**If you're working with learning in RAVL: Always ask yourself "Is this Problem Space or Solution Space?" If you can't answer clearly, the separation has broken down.**

---

## Related Documentation

- [RAVL_VISION.md](RAVL_VISION.md) - Principle 9: Problem Space and Solution Space Learning Separation
- [health_checks.md](health_checks.md) - Execution vs Domain health check usage
- [RAVL_PROTOCOL.md](RAVL_PROTOCOL.md) - Four-phase RAVL specification
