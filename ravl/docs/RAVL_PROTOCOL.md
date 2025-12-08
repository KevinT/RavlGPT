# RAVL Loop Protocol Specification

## Overview

RAVL (Reflect-Act-Verify-Learn) is a four-phase loop pattern for autonomous agents that continuously improve through learning.

See [RAVL Vision](RAVL_VISION.md) for the ambitions of the RAVL framework that this protocol specification is a part of.

This specification defines the contract that all RAVL loops must implement, regardless of implementation language or execution method (Python, LLM-interpreted markdown, etc.).

## Core Principles

1. **Stateless Phases**: Each phase operates independently, in sequence, with clear inputs/outputs
2. **Decoupled Execution**: Loops can be run separately or composed together
3. **Read-Anywhere, Write-Own**: Loops can read any model, but only write to their own
4. **Learned Intelligence**: Each loop maintains a model that improves over time

## The Four Phases

### 1. REFLECT Phase

**Purpose**: Pure observation and data gathering - NO decision making. Can use LLMs to synthesize learnings into actionable context.

**Inputs**: None (reads from environment/state and previous learnings)

**Outputs**: `Dict[str, Any]` containing observations and synthesized domain guidance

**Responsibilities**:
- Gather raw data about current state
- Compute state signatures/hashes for change detection
- Load learned context from previous runs
- **Use LLM to synthesize domain learnings into actionable guidance for ACT**
- Prepare enriched context for Act phase

**LLM Synthesis**:
- Reads `loop_learning/` and `execution_learning/` directories (previous run insights, verification suggestions, metrics)
- Uses LLM to analyze patterns: what worked, what failed, what to try
- Creates structured guidance: priority focus, patterns to repeat/avoid, new strategies
- Passes synthesized insights to ACT (can include raw learning files)

**Anti-patterns**:
- ❌ Making decisions or selecting strategies on behalf of ACT phase
- ❌ Taking actions or modifying state
- ❌ Passing raw learning files without meta-synthesis

**Example Output Structure**:
```json
{
  "timestamp": "2025-10-04T12:00:00+00:00",
  "state_hash": "abc123...",
  "files_found": 64,
  "domain_guidance": {
    "priority_focus": ["Address VERIFY suggestions from last run"],
    "successful_patterns": ["Using incremental validation worked"],
    "failed_patterns": ["Batch processing caused timeouts"],
    "new_strategies_to_try": ["Try streaming approach"]
  },
  "learned_context": {
    "previous_precision": 0.75,
    "strategy_performance": {...}
  }
}
```

---

### 2. ACT Phase

**Purpose**: Apply bounded agency - make domain decisions and/or take actions. Receives synthesized guidance from REFLECT.

**Inputs**:
- `reflection: Dict[str, Any]` - Output from Reflect phase (includes synthesized domain guidance)

**Outputs**: `Dict[str, Any]` containing actions taken and results

**About Agency**:
- ACT is where the loop applies its agency (decisions OR actions)
- Can make domain decisions (strategy selection, analysis)
- Can take actions (API calls, data processing, file operations)
- Bounded by learning loop for self-healing and course correction
- Uses synthesized insights from REFLECT to inform decisions

**Responsibilities**:
- Receive and use domain guidance from REFLECT
- Select strategies/approaches using learned intelligence
- Perform analysis (LLM calls, comparisons, etc.)
- Take actions (API calls, data transforms, etc.)
- Generate findings/gaps/recommendations
- Return structured results

**Anti-patterns**:
- ❌ Re-gathering data (use reflection)
- ❌ Ignoring guidance from REFLECT
- ❌ Verification (save for Verify phase)
- ❌ Learning/updating models (save for Learn phase)


**Example Output Structure**:
```json
{
  "strategy_used": {
    "name": "broad_survey",
    "reasoning": "..."
  },
  "gaps_found": [...],
  "metadata": {
    "llm_calls": 3,
    "tokens_used": 12000
  }
}
```

---

### 3. VERIFY Phase

**Purpose**: Check if previous actions achieved intended outcomes

**Inputs**:
- `previous_action: Optional[Dict[str, Any]]` - Results from previous run's Act phase
- `current_reflection: Dict[str, Any]` - Current reflection (reused, not re-computed)

**Outputs**: `Dict[str, Any]` containing verification results

**Responsibilities**:
- Start with most recent outcomes of Act step
- Compare previous issues with current state
- Detect which issues were fixed (disappeared from current state)
- Detect which issues were ignored (still present)
- Identify false positives (flagged but not actually problems)
- Calculate verification metrics

**Anti-patterns**:
- ❌ Updating models (save for Learn phase)
- ❌ Re-running reflections that have already been done in Reflect step
- ❌ Taking new actions

**Example Output Structure**:
```json
{
  "outcomes": {
    "fixed": ["GAP-001", "GAP-003"],
    "ignored": ["GAP-002"],
    "false_positives": ["GAP-004"]
  },
  "fix_rate": 0.5,
  "precision": 0.75,
  "confidence": 0.8
}
```

---

### 4. LEARN Phase

**Purpose**: Update model based on verification outcomes. Uses LLM to analyze entire run and persist insights for next REFLECT.

**Inputs**:
- `verification: Dict[str, Any]` - Output from Verify phase
- `action_result: Dict[str, Any]` - Output from Act phase
- (Internal: `reflection` from earlier in the run)

**Outputs**: `None` (updates model and persists insights to disk)

**Responsibilities**:
- **Use LLM to analyze entire run (REFLECT→ACT→VERIFY) and extract domain patterns**
- Update learned weights based on what worked
- Add any new items to model that might improve outcomes in next run
- Adjust strategy selection based on outcomes
- Identify and record false positive patterns
- **Persist synthesized insights for next REFLECT to use**
- Update performance metrics
- Persist updated model

**LLM Synthesis**:
- Analyzes full RAVL cycle: context quality, agency effectiveness, verification outcomes
- Identifies cross-phase patterns (e.g., "REFLECT missed X, so ACT failed at Y")
- Generates strategic insights and recommendations
- Persists to `execution_learning/recent_attempts/attempt_N/run_insights_*.json`
- Next REFLECT reads these insights and synthesizes them into ACT guidance

**CRITICAL Separation**:
- **Execution learning** (`execution_learning/`): Code generation patterns (already handled by DSL)
- **Domain learning** (`loop_learning/`): Agency patterns, decision effectiveness (LEARN synthesizes this)
- Must never mix these concerns

**Anti-patterns**:
- ❌ Taking new actions
- ❌ Re-analyzing data
- ❌ Writing to other loops' models
- ❌ Mixing execution learning with domain learning

**Example Model Update**:
```yaml
gap_weights:
  terminology_inconsistency: 0.8  # Increased - humans fix these
  minor_typo: 0.2                 # Decreased - humans ignore these

strategy_performance:
  broad_survey:
    success_rate: 0.75
    avg_true_positives: 3.2
```

**Example Run Insights** (persisted for next REFLECT):
```json
{
  "context_quality": {
    "assessment": "REFLECT provided good stakeholder context",
    "gaps": ["Missing historical validation patterns"]
  },
  "agency_effectiveness": {
    "assessment": "ACT addressed previous VERIFY suggestions",
    "what_worked": ["Incremental validation pattern"],
    "what_failed": ["Batch processing approach"]
  },
  "recommendations_for_next_run": [
    "Continue incremental validation",
    "Add historical pattern analysis to REFLECT"
  ]
}
```

---

## Execution Patterns

### Full RAVL Cycle
```
reflection = loop.reflect()
action = loop.act(reflection)
verification = loop.verify(previous_action, reflection)
loop.learn(verification, action)
```

### Fast Mode (Skip Learning)
```
reflection = loop.reflect()
action = loop.act(reflection)
# Skip verify + learn for speed during development
```

### Coordination Pattern (Parent + Children)
```
# Parent reflects on child state
parent_reflection = parent.reflect()

# Parent coordinates child execution
for child in children:
    child_reflection = child.reflect()
    child_action = child.act(child_reflection)

# Parent generates meta-insights
parent_action = parent.act(parent_reflection)

# Parent coordinates learning
parent_verification = parent.verify(previous, parent_reflection)
for child in children:
    child_verification = child.verify(previous_child, child_reflection)
    child.learn(child_verification, child_action)
parent.learn(parent_verification, parent_action)
```

---

## Implementation Guidelines

### For Python Implementations

Use the `RAVLLoop` Protocol from `.ravl/ravl/common/ravl_loop.py`:

```python
from typing import Dict, Any, Optional

class MyRAVLLoop:
    def reflect(self) -> Dict[str, Any]:
        """Pure observation - no decisions"""
        pass

    def act(self, reflection: Dict[str, Any]) -> Dict[str, Any]:
        """Decisions and actions"""
        pass

    def verify(self, previous_action: Optional[Dict[str, Any]],
               current_reflection: Dict[str, Any]) -> Dict[str, Any]:
        """Outcome verification"""
        pass

    def learn(self, verification: Dict[str, Any],
              action_result: Dict[str, Any]) -> None:
        """Model updates"""
        pass
```

### For LLM-Interpreted Markdown Implementations

Define loops as markdown documents with clear phase instructions.

**CRITICAL: Phase headings MUST use H1 format (single #):**

```markdown
# Reflect

<Instructions for LLM to gather observations>

# Act

<Instructions for LLM to take actions>

# Verify

<Instructions for LLM to verify outcomes>

# Learn

<Instructions for LLM to update model>
```

**Note:** The markdown parser requires H1 headings (`# Act`) for phase names. Using H2 (`## Act`) or other formats will cause parsing to fail.

An executor interprets these and maintains state between phases.

---

## Design Philosophy

**Why Four Phases?**
- **Reflect**: Separates observation from decision (clarity)
- **Act**: Isolated decision-making (testable)
- **Verify**: Explicit outcome measurement (accountability)
- **Learn**: Continuous improvement (adaptability)

**Why Stateless?**
- Each phase can be tested independently
- Phases can be cached/optimized separately
- Easy to debug (clear inputs/outputs)
- Supports different execution modes (fast/full)

**Why Read-Anywhere, Write-Own?**
- Prevents model corruption
- Enables cross-loop insights
- Clear ownership boundaries
- Safe parallel execution

---

## Loop Locking (Production Stability)

### Overview
Loops can be "locked" to execute specific verified code, bypassing the full RAVL cycle. This supports production deployments where consistency is prioritized over continuous learning.

### Locked Execution Behavior
When a loop is locked:
- **Reflect/Act/Verify/Learn phases are skipped entirely**
- **Locked code executes directly** in the loop's venv
- **No learning occurs** - models remain unchanged
- **No code generation** - cached code runs as-is
- **Faster execution** - no LLM calls or interpretation

### Lock Management

**Locking a Loop**:
```bash
# Lock to most recent successful execution
ravl --lock my_loop

# Lock to specific attempt
ravl --lock my_loop --attempt 3

# Force lock (even if verification failed)
ravl --lock my_loop --force
```

**Unlocking a Loop**:
```bash
ravl --unlock my_loop
```

**Checking Lock Status**:
```bash
# View lock status in config
ravl my_loop --show-config

# See locked loops in list
ravl --list  # Shows 🔒 next to locked loops
```

### Lock Configuration
Lock status is stored in `config/ravl.toml`:
```toml
loop_locked = "./learnings/execution_learning/recent_attempts/attempt_3/generated_code.py"
```

### Validation
By default, only successful attempts can be locked:
- Attempt must exist
- `execution_result.json` must show `"passed": true`
- Use `--force` to bypass verification check

**Security**: Locked code path MUST be within the loop's learnings directory:
- Prevents executing arbitrary code from elsewhere on filesystem
- Validation cannot be bypassed (even with `--force`)
- Manual config edits pointing outside learnings will cause execution to fail with security error

### Use Cases
- **Production Deployments**: Lock loops for consistent behavior
- **Compliance**: Freeze code for auditing
- **Debugging**: Lock to isolate issues
- **Performance**: Skip code generation overhead

### Philosophy
Loop locking is opt-in infrastructure control that balances:
- **Continuous Learning** (default): Loops adapt and improve
- **Production Stability** (locked): Behavior remains consistent

Users choose the balance for each loop based on their needs.

---

## Version History

- **v1.0** (2025-10-04): Initial protocol specification
