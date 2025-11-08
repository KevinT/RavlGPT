# RAVL Prompt Template System

RAVL uses a prompt template system for LLM-based loops. Prompts are stored as markdown files with variable substitution.

## Prompt Storage Locations

Prompts are organized hierarchically:

```
ravl_loops/my_loop/
├── config/
│   ├── prompt_*.md          # Loop-specific prompts
│   └── ravl.yml
```

Common locations:
- **Loop prompts**: `ravl_loops/my_loop/config/prompt_*.md`
- **Framework prompts**: `.ravl/common/execution/markdown/prompts/prompt_*.md`

## Using the PromptLoader

```python
from prompt_loader import PromptLoader

# Load from default location
loader = PromptLoader()
prompt = loader.load_prompt('prompt_analysis',
                           context="...",
                           data="...")

# Load from custom directory
loader = PromptLoader(prompts_dir='ravl_loops/my_loop/config')
prompt = loader.load_prompt('prompt_custom', variable="value")
```

## Prompt Template Format

Prompts use Python string formatting with `{variable_name}` placeholders:

```markdown
# Analysis Prompt

You are analyzing the following data:

## Context
{context}

## Data to Analyze
{data}

## Task
{task_description}

Please provide:
1. Key findings
2. Recommendations
3. Next steps
```

### Loading This Prompt

```python
loader = PromptLoader()
formatted = loader.load_prompt(
    'prompt_analysis',
    context="Historical patterns from previous runs...",
    data="Current state data...",
    task_description="Identify anomalies and suggest improvements"
)
```

## Common Prompt Types

### Act Phase Prompts

For generating code or analysis during the Act phase:

**File**: `config/prompt_act_phase.md` or `prompt_data_ingestion_codegen.md`

```markdown
# Act Phase: {task_name}

## Current State
{reflection_summary}

## Learned Patterns
{learned_patterns}

## Task
{instructions}

Generate code that accomplishes the task.
```

### Verify Phase Prompts

For validation during the Verify phase:

**File**: `config/prompt_verify_phase.md`

```markdown
# Verification: {verification_criteria}

## Expected Outcome
{expected_outcome}

## Actual Outcome
{actual_outcome}

## Task
Determine if the outcome meets the criteria.
```

### Diagnostic Prompts

For health check and failure analysis:

**Execution Health Check**: `.ravl/ravl_loops/health_checks/execution_health_check/config/` (code generation, DSL)
**Loop Health Check**: `.ravl/ravl_loops/health_checks/loop_health_check/config/` (domain learning, patterns)
**Legacy**: `.ravl/ravl_loops/health_checks/health_check_ravl/config/prompt_diagnostic_v2.md` (deprecated)

```markdown
# Diagnostic Analysis

## Loop Information
{loop_info}

## Error Messages
{error_summary}

## Task
Identify root cause and provide actionable steps.
```

## Best Practices

###1. Use Descriptive Variable Names

```markdown
❌ Bad: {d}, {x}, {info}
✅ Good: {data_summary}, {execution_context}, {loop_info}
```

### 2. Provide Context Hierarchy

Structure prompts from general to specific:

```markdown
# Task: {task_name}

## Background
{project_context}

## Current Situation
{loop_state}

## Specific Request
{detailed_instructions}
```

### 3. Include Examples When Possible

```markdown
## Expected Output Format

Example:
```json
{
  "finding": "...",
  "confidence": 0.85
}
```
```

### 4. Handle Missing Variables

The PromptLoader will raise `ValueError` if required variables are missing. Handle gracefully:

```python
try:
    prompt = loader.load_prompt('my_prompt', var1="value")
except ValueError as e:
    print(f"Missing prompt variable: {e}")
```

## Markdown Loop Integration

Markdown loops automatically load prompts based on phase:

**Reflect Phase**: Loads `prompt_reflect.md` (if exists)
**Act Phase**: Loads `prompt_act_phase.md` or `prompt_data_ingestion_codegen.md`
**Verify Phase**: Loads `prompt_verify_phase.md` (if exists)

The framework automatically substitutes:
- `{reflection}` - Output from Reflect phase
- `{action_result}` - Output from Act phase
- `{verification_criteria}` - From markdown Verify section
- `{learning_history}` - From learnings/

## Advanced: Multi-Step Prompts

For complex operations, chain prompts:

```python
# Step 1: Analyze
analysis = loader.load_prompt('prompt_analyze', data=raw_data)
analysis_result = llm.generate(analysis)

# Step 2: Synthesize (uses Step 1 output)
synthesis = loader.load_prompt('prompt_synthesize',
                              analysis=analysis_result,
                              context=context)
final_result = llm.generate(synthesis)
```

## Template Variable Validation

The framework validates template variables at load time. Ensure all `{variables}` have matching kwargs:

```python
# Template has: {context}, {data}, {task}
prompt = loader.load_prompt(
    'my_prompt',
    context="...",  # ✓
    data="...",     # ✓
    task="...",     # ✓
)  # Success!

# Missing 'task' → ValueError
prompt = loader.load_prompt(
    'my_prompt',
    context="...",
    data="..."
)  # Raises: Missing required prompt variable: 'task'
```

## See Also

- [CONFIG_FORMAT.md](CONFIG_FORMAT.md) - Loop configuration format
- [Markdown Loop Infrastructure](README.md) - Full markdown loop documentation
- [Health Check Diagnostics](../../ravl_loops/health_checks/) - Execution and loop health checks with real-world prompt examples
