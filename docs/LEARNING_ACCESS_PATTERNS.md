# RAVL Learning Access Patterns

## Overview

The RAVL framework implements a **two-dimensional learning architecture** that separates concerns along two axes:

1. **Vertical Separation**: Execution learning vs Domain learning
2. **Horizontal Separation**: Loop hierarchy (parent/child/sibling access control)

This document explains how loops access learning artifacts across the hierarchy, the isolation rules, and troubleshooting tips.

---

## Two-Dimensional Learning Architecture

```
                    ┌─────────────────────────────────────┐
                    │   Horizontal: Loop Hierarchy        │
                    │   (Parent/Child/Sibling Access)     │
                    └─────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
    ┌───▼───┐                  ┌───▼───┐                  ┌───▼───┐
    │Parent │                  │ Self  │                  │Sibling│
    │ Loop  │                  │ Loop  │                  │ Loop  │
    └───┬───┘                  └───┬───┘                  └───┬───┘
        │                          │                          │
  ┌─────▼────────────────────┬─────▼────────────────────┬─────▼────────────────┐
  │ Vertical: Learning Type  │                          │                      │
  │ (Execution vs Domain)    │                          │                      │
  └──────────────────────────┴──────────────────────────┴──────────────────────┘
        │                          │                          │
  ┌─────▼──────┐            ┌─────▼──────┐            ┌─────▼──────┐
  │execution_  │            │execution_  │            │execution_  │
  │learning/   │            │learning/   │            │learning/   │
  │ (HOW)      │            │ (HOW)      │            │ (HOW)      │
  └────────────┘            └────────────┘            └────────────┘
  ┌────────────┐            ┌────────────┐            ┌────────────┐
  │loop_       │            │loop_       │            │loop_       │
  │learning/   │            │learning/   │            │learning/   │
  │ (WHAT)     │            │ (WHAT)     │            │ (WHAT)     │
  └────────────┘            └────────────┘            └────────────┘
```

---

## Vertical Separation: Execution vs Domain Learning

### Execution Learning (`learnings/execution_learning/`)

**Purpose**: Learn HOW to make the loop RUN without errors

**Managed by**: `ExecutionLearningManager` (`.ravl/common/core/learning/execution_learning_manager.py`)

**Contains**:
- Code generation attempts and DSL iterations
- Infrastructure failures (dependency errors, API auth issues, syntax errors)
- Code caching and verification
- Execution warnings and deprecations

**Directory Structure**:
```
execution_learning/
├── current_state/           # Latest execution state
│   ├── generated_code.py
│   ├── latest_dsl.json
│   └── execution_result.json
├── recent_attempts/         # Last N execution attempts
│   ├── attempt_1/
│   │   ├── generated_code.py
│   │   ├── execution_result.json
│   │   ├── dsl_used.json
│   │   ├── spec_hash.txt
│   │   └── run_insights_*.json  # From LEARN phase
│   └── attempt_2/
├── history/                 # Aggregated execution history
│   ├── execution_failures.jsonl
│   ├── dsl_iterations.jsonl
│   └── code_strategies.jsonl
└── verified_code.py         # Cached working code
```

### Domain Learning (`learnings/loop_learning/`)

**Purpose**: Learn WHAT the loop discovers about its domain (THE "L" IN RAVL)

**Managed by**: `LoopLearningManager` (`.ravl/common/core/learning/loop_learning_manager.py`)

**Contains**:
- Domain patterns and insights
- Business logic improvements
- Data quality observations
- Strategy evolution

**Directory Structure**:
```
loop_learning/
├── current_state/           # Latest domain state
│   ├── latest_action.json
│   ├── latest_verification.json
│   └── latest_metrics.yml
├── recent_attempts/         # Last N domain attempts
│   ├── attempt_1/
│   │   ├── domain_action.json
│   │   ├── domain_verification.json
│   │   └── domain_metrics.yml
│   └── attempt_2/
├── history/                 # Aggregated domain history
│   ├── domain_failures.jsonl
│   ├── domain_successes.jsonl
│   └── pattern_evolution.jsonl
└── model.yml                # Current domain model
```

### Why Separate?

- **Execution learning** helps loops RUN successfully (infrastructure concerns)
- **Domain learning** helps loops run WELL (business logic concerns)
- **Never mix**: DSL iterations should never influence domain patterns
- **Different lifecycles**: Execution converges fast, domain evolves slowly

---

## Horizontal Separation: Loop Hierarchy Access Control

### Access Rules

1. **Top-level parents CANNOT see each other's learning**
   - Enforces organizational separation
   - Each top-level parent is isolated
   - Example: `clickup_intelligence/` cannot read `frontier_engineering/` learning

2. **Child loops CAN see:**
   - Their own learning (read/write)
   - Parent loop learning (read-only)
   - Sibling loop learning (read-only)
   - Their own children's learning (read-only)

3. **Parent loops CAN see:**
   - Their own learning (read/write)
   - All children's learning (read-only)
   - Their own parent's learning (read-only) - if not top-level

### Loop Hierarchy Example

```
ravl_loops/
├── clickup_intelligence/          # Top-level parent A
│   ├── learnings/
│   └── ravl_loops/
│       ├── task_velocity/         # Child of A
│       │   └── learnings/
│       └── team_workload/         # Child of A (sibling of task_velocity)
│           └── learnings/
├── frontier_engineering/          # Top-level parent B (ISOLATED from A)
│   ├── learnings/
│   └── ravl_loops/
│       └── context_management/    # Child of B
│           └── learnings/
```

**Access Matrix**:

| Loop | Can Read Learning From |
|------|----------------------|
| `clickup_intelligence` | Own, children (`task_velocity`, `team_workload`) |
| `task_velocity` | Own, parent (`clickup_intelligence`), sibling (`team_workload`) |
| `team_workload` | Own, parent (`clickup_intelligence`), sibling (`task_velocity`) |
| `frontier_engineering` | Own, children (`context_management`) |
| `context_management` | Own, parent (`frontier_engineering`) |

**Isolation Enforcement**:
- `clickup_intelligence` CANNOT read `frontier_engineering` learning
- `task_velocity` CANNOT read `context_management` learning (different top-level parent)

---

## Using LearningAccessHelper

### Basic Usage

```python
from core.learning.learning_access_helper import LearningAccessHelper

# Initialize helper
helper = LearningAccessHelper(
    loop_dir=Path('/path/to/loop'),
    learnings_dir=Path('/path/to/learnings'),
    debug=True  # Enable verbose logging
)

# Check if this is a top-level parent
if helper.is_top_level_parent():
    print("This loop is isolated from other top-level parents")

# Get parent learning path
parent_path = helper.get_parent_learning_path()
if parent_path:
    print(f"Parent learning at: {parent_path}")

# Get sibling learning path
sibling_path = helper.get_sibling_learning_path('cross_source_synthesizer')
if sibling_path:
    print(f"Sibling learning at: {sibling_path}")

# Get child learning path
child_path = helper.get_child_learning_path('data_collector')
if child_path:
    print(f"Child learning at: {child_path}")

# Read sibling model (convenience method)
sibling_model = helper.read_sibling_model('cross_source_synthesizer')
if sibling_model:
    print(f"Sibling model: {sibling_model}")

# Discover all siblings (excludes top-level parents by default)
siblings = helper.discover_siblings(exclude_top_level_parents=True)
print(f"Sibling loops: {siblings}")

# Discover all children
children = helper.discover_children()
print(f"Child loops: {children}")
```

### In BaseRAVLLoop Subclasses

```python
from pathlib import Path
from ravl_base import BaseRAVLLoop

class MyLoop(BaseRAVLLoop):
    def __init__(self, model_path: Path, loop_dir: Path):
        super().__init__(
            model_path=model_path,
            loop_name='my_loop',
            loop_dir=loop_dir  # Required for cross-loop access
        )

    def reflect(self):
        # Read parent model
        parent_model = self.read_parent_model()
        if parent_model:
            print(f"Parent model: {parent_model}")

        # Read sibling model
        sibling_model = self.read_sibling_model('other_loop')
        if sibling_model:
            print(f"Sibling model: {sibling_model}")
```

### In Generated Code

Generated code can use the helper directly:

```python
from pathlib import Path
from core.learning.learning_access_helper import LearningAccessHelper

# Initialize helper
loop_dir = Path('/path/to/current/loop')
learnings_dir = Path('/path/to/learnings')
helper = LearningAccessHelper(loop_dir, learnings_dir)

# Read sibling data
sibling_path = helper.get_sibling_learning_path('cross_source_synthesizer')
if sibling_path:
    # Read sibling's domain action
    action_file = sibling_path / 'loop_learning' / 'current_state' / 'latest_action.json'
    if action_file.exists():
        import json
        with open(action_file, 'r') as f:
            sibling_data = json.load(f)
            print(f"Sibling produced: {sibling_data}")
```

---

## Automatic Discovery in REFLECT Phase

The markdown-based RAVL executor automatically discovers and loads all accessible learning in the REFLECT phase:

```python
# Automatically happens during reflect()
reflection = {
    'learnings': {
        'this_loop': {
            'files': {...},        # Top-level learning files
            'subdirs': {
                'execution_learning': {...},
                'loop_learning': {...}
            }
        },
        'parent_loop': {         # If parent exists
            'files': {...},
            'subdirs': {...}
        },
        'child_loops': {         # If children exist
            'child_1': {...},
            'child_2': {...}
        },
        'sibling_loops': {       # If siblings exist (respects top-level isolation)
            'sibling_1': {...},
            'sibling_2': {...}
        }
    }
}
```

**Note**: Top-level parents automatically excluded from siblings list.

---

## Configurable Learning Paths

Learning paths follow a 6-level priority hierarchy:

1. **CLI flag**: `./ravl my_loop --learning-path /custom/path` (highest priority)
2. **Loop config**: `learning_path` in `config/ravl.yml`
3. **Parent configs**: Walk parent chain for `learning_path`
4. **Project config**: `ravl_loops/config/ravl.yml` learning_path
5. **Environment file**: `RAVL_DEFAULT_LEARNING_DIRECTORY` in `.env`
6. **Default**: `loop_dir/learnings` (lowest priority)

### Example Configurations

**In loop's config/ravl.yml**:
```yaml
learning_path: /data/ravl-learning/my_loop
```

**In project .env**:
```bash
RAVL_DEFAULT_LEARNING_DIRECTORY=/data/ravl-learning
```

**CLI override**:
```bash
./ravl my_loop --learning-path /tmp/debug-learning
```

### Child Loop Path Inheritance

Children automatically inherit parent's learning path structure:

- Parent: `/data/ravl/org_context/learnings`
- Child: `/data/ravl/org_context/google_workspace/learnings`
- Grandchild: `/data/ravl/org_context/google_workspace/enrichment/learnings`

---

## Troubleshooting

### Problem: Loop Can't Find Sibling Data

**Symptoms**:
- `read_sibling_model()` returns `None`
- Error: "No sibling loop found at {path}"
- REFLECT shows 0 siblings when you expect some

**Diagnosis**:
1. Check if both loops are at same level in hierarchy
2. Verify sibling has `config/ravl.yml`
3. Check if you're a top-level parent (isolated from other top-level parents)
4. Enable debug logging: `helper = LearningAccessHelper(..., debug=True)`

**Solution**:
```python
# Enable debug logging to see path resolution
from core.learning.learning_access_helper import LearningAccessHelper

helper = LearningAccessHelper(loop_dir, learnings_dir, debug=True)
sibling_path = helper.get_sibling_learning_path('expected_sibling')
# Check logs for detailed path resolution attempts
```

### Problem: Path Resolution Failing with Configurable Paths

**Symptoms**:
- Works with default learning paths
- Fails when using `RAVL_DEFAULT_LEARNING_DIRECTORY`
- Error: "Using legacy sibling path resolution (loop_dir not provided)"

**Cause**:
- `BaseRAVLLoop` initialized without `loop_dir` parameter
- Falls back to hardcoded `parent.parent` navigation (doesn't respect custom paths)

**Solution**:
```python
# WRONG: Missing loop_dir
loop = BaseRAVLLoop(model_path, loop_name)

# RIGHT: Include loop_dir
loop = BaseRAVLLoop(model_path, loop_name, loop_dir=Path('/path/to/loop'))
```

### Problem: Top-Level Parents Seeing Each Other

**Symptoms**:
- Sibling discovery includes other top-level parents
- Isolation not enforced

**Cause**:
- `discover_related_loops(exclude_top_level_parents=False)` called explicitly
- Or using old code before isolation enforcement

**Solution**:
```python
# Ensure top-level isolation is enabled (default)
related_loops = context_builder.discover_related_loops(exclude_top_level_parents=True)
```

### Problem: No Learnings Found During REFLECT

**Symptoms**:
- REFLECT shows empty learnings
- "No prior domain learnings (fresh start)" message

**Possible Causes**:
1. **Learning path misconfiguration**: Loop looking in wrong directory
2. **First run**: No learnings exist yet (expected)
3. **Permission issues**: Can't read learning directory

**Diagnosis**:
```bash
# Check where loop expects to find learnings
./ravl my_loop --debug

# Verify learning directory exists and has files
ls -la /path/to/expected/learnings/

# Check permissions
ls -ld /path/to/expected/learnings/
```

---

## Best Practices

### 1. Always Provide `loop_dir` to BaseRAVLLoop

```python
# GOOD
loop = BaseRAVLLoop(
    model_path=model_path,
    loop_name='my_loop',
    loop_dir=loop_dir  # Enables proper cross-loop access
)

# BAD (legacy only)
loop = BaseRAVLLoop(model_path, loop_name)
```

### 2. Use LearningAccessHelper for Path Resolution

```python
# GOOD
from core.learning.learning_access_helper import LearningAccessHelper
helper = LearningAccessHelper(loop_dir, learnings_dir)
sibling_path = helper.get_sibling_learning_path('other_loop')

# BAD (hardcoded paths)
sibling_path = loop_dir.parent / 'other_loop' / 'learnings'
```

### 3. Check Return Values

```python
# GOOD
sibling_model = helper.read_sibling_model('other_loop')
if sibling_model is None:
    log_execution("Sibling not found, using default", status='warning')
    sibling_model = default_model()

# BAD (assumes exists)
sibling_model = helper.read_sibling_model('other_loop')
data = sibling_model['key']  # Crashes if None
```

### 4. Enable Debug Logging During Development

```python
# Development
helper = LearningAccessHelper(loop_dir, learnings_dir, debug=True)

# Production
helper = LearningAccessHelper(loop_dir, learnings_dir, debug=False)
```

### 5. Document Loop Dependencies

In your loop's README or config, document which loops it reads from:

```yaml
# config/ravl.yml
dependencies:
  parent: org_context
  siblings:
    - cross_source_synthesizer
    - data_collector
  children:
    - enrichment
```

---

## Advanced Topics

### Custom Learning Retention Policies

Control how many attempts are kept:

```yaml
# config/ravl.yml
execution_learning:
  retention_policy:
    recent_attempts_limit: 5  # Keep last 5 attempts
    max_age_days: 30          # Delete older than 30 days

loop_learning:
  retention_policy:
    recent_attempts_limit: 10
    max_age_days: 90
```

### Shared Learning Across Machines

Use network-accessible learning paths for team coordination:

```bash
# .env
RAVL_DEFAULT_LEARNING_DIRECTORY=/mnt/shared-learning
```

All team members see same learning artifacts in real-time.

### Learning Access in Child Loop Generators

When a parent generates code for children, provide learning path explicitly:

```python
# Parent loop generates child loop code
child_code = f"""
from core.learning.learning_access_helper import LearningAccessHelper

# Child inherits parent's learning path structure
helper = LearningAccessHelper(
    loop_dir=Path('{child_loop_dir}'),
    learnings_dir=Path('{child_learnings_dir}')
)

# Read parent's learning
parent_model = helper.read_parent_model()
"""
```

---

## Summary

The RAVL framework's two-dimensional learning architecture provides:

1. **Clear separation** between infrastructure learning (execution) and domain learning (loop)
2. **Hierarchical access control** with top-level parent isolation
3. **Flexible learning path configuration** for diverse deployment scenarios
4. **Automatic discovery** in REFLECT phase with full context
5. **Debugging tools** for troubleshooting path resolution issues

Use `LearningAccessHelper` for all cross-loop learning access to ensure proper path resolution and respect for isolation rules.
