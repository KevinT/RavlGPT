# LLM-Based RAVL Loop Infrastructure

This directory contains infrastructure for creating LLM-interpreted RAVL loops defined in markdown.

## Overview

Instead of writing Python code, RAVL loops can be defined in markdown with Act and Verify instructions. The infrastructure automatically handles:
- **Reflect**: Scans learnings from this agent + parent/nested/sibling agents
- **Act**: Executes markdown instructions via LLM
- **Verify**: Evaluates outputs against markdown criteria via LLM
- **Learn**: Updates learning history (append-only)

## Two Approaches

### 1. Config-Based (Recommended for New Loops)

**No Python code needed!** Just create:
- `config.toml` - Loop configuration
- `ravl_loop.md` - Markdown instructions

```bash
python3 .ravl/common/llm/run_markdown_ravl.py \
  --loop-dir path/to/loop \
  --role "CTO"
```

**Pros:**
- Zero Python code
- Consistent CLI interface
- Self-documenting
- Easy to create new loops

**Documentation:** See [CONFIG_FORMAT.md](CONFIG_FORMAT.md)

### 2. Custom run.py (For Complex Needs)

Create a custom `run.py` that uses `MarkdownRAVLExecutor`.

**When to use:**
- Custom initialization logic needed
- Complex argument parsing
- Integration with other systems

**Example:** See `.ravl/agents/strategy_guardian/agents/role_ambitions/run.py`

## Quick Start: Create a New Loop

```bash
# 1. Create directory
mkdir -p .ravl/agents/my_group/agents/my_loop

# 2. Create config.toml
cat > .ravl/agents/my_group/agents/my_loop/config.toml <<EOF
name: my_loop
description: My loop description

template_variables:
  my_input:
    cli_arg: --input
    required: true
    help: Input parameter
EOF

# 3. Create ravl_loop.md
cat > .ravl/ravls/my_group/child_loops/my_loop/ravl_loop.md <<EOF
# Act
Process {my_input} and generate output

# Acceptance Criteria
1. Output was created
2. Output is valid
EOF

# 4. Run it!
python3 .ravl/common/llm/run_markdown_ravl.py \
  --loop-dir .ravl/ravls/my_group/child_loops/my_loop \
  --input "test"
```

## Files in This Directory

### Core Infrastructure

- **`markdown_ravl_executor.py`** - Executor that interprets markdown RAVL loops
- **`run_markdown_ravl.py`** - Generic config-based runner
- **`llm_providers.py`** - LLM provider abstraction (Anthropic, OpenAI, Google, Ollama)
- **`llm_logger.py`** - Logs all LLM interactions for debugging

### Prompts

- **`prompts/`** - LLM prompt templates
  - `act_phase.txt` - Act phase prompt
  - `verify_phase.txt` - Verify phase prompt
  - `README.md` - Prompt documentation

### Documentation

- **`CONFIG_FORMAT.md`** - Config file format specification
- **`README.md`** - This file

## Markdown Format

### Supported Headings

- `# Act` (required) - What to do
- `# Verify` or `# Acceptance Criteria` (optional) - Verification criteria
- `# Reflect` (optional, auto-generated if missing)
- `# Learn` (optional, auto-generated if missing)

### Template Variables

Use `{variable_name}` in markdown. Substituted from CLI args or config.

```markdown
# Act
I am the {role} at {company}. Generate a report.

# Acceptance Criteria
1. Report was created for {role}
2. Report includes all required sections
```

## Learning Structure

All loops create an append-only learning directory:

```
learnings/
├── action_result_*.json      # Timestamped outputs
├── verification_*.json       # Timestamped verifications
├── learning_history.jsonl    # Complete learning log
├── metrics_*.yml             # Performance metrics
└── logs/                     # Execution logs
```

**Key principle:** Never overwrite, only append. Full learning history preserved.

## Examples

### Example 1: Role Ambitions Loop

Generates role-specific ambitions based on handbook gaps.

**Location:** `.ravl/ravls/strategy_guardian/child_loops/role_ambitions/`

**Config:**
```yaml
name: role_ambitions
description: Generate role-specific ambitions

template_variables:
  organisational role:
    cli_arg: --role
    required: true
    help: Role to generate ambitions for
```

**Usage:**
```bash
python3 .ravl/common/llm/run_markdown_ravl.py \
  --loop-dir .ravl/ravls/strategy_guardian/child_loops/role_ambitions \
  --role "CTO" \
  --mode full
```

## LLM Providers

Supports multiple LLM providers (see `llm_providers.py`):

- **Anthropic Claude** (default)
- **OpenAI GPT**
- **Google Gemini**
- **Ollama** (local models)

Configure via environment variables:
```bash
export ANTHROPIC_API_KEY="..."
export OPENAI_API_KEY="..."
export GOOGLE_API_KEY="..."
```

## Common Options

All loops support standard RAVL options:

```bash
--mode fast|full              # Fast skips verify/learn
--no-deep-learning            # Skip verify/learn (same as fast)
--timeout SECONDS             # Timeout for LLM calls
--no-fetch-external           # Don't fetch external data
```

## Troubleshooting

### "Module not found: anthropic"
Install LLM provider packages:
```bash
pip install anthropic openai google-generativeai
```

### "Template variable not substituted"
Check variable name in markdown exactly matches config (including spaces/case).

### "Config file not found"
Ensure `config.toml` exists in loop directory or provide `--config path`.

### Verification always fails
This is expected during initial runs. The system learns and improves. Check:
```
📋 Current Verification Details:
   ✓ [1] Passing criterion
   ✗ [2] Failing criterion
```

## Best Practices

1. **Start with config-based approach** unless you need custom logic
2. **Use meaningful variable names** in config and markdown
3. **Write clear acceptance criteria** - specific and testable
4. **Test incrementally** - start with fast mode, add verification later
5. **Review learning history** to understand improvements over time

## Advanced Topics

### Custom Prompt Templates

Edit files in `prompts/` to customize LLM behavior globally.

### Reading Learnings

```python
import json
from pathlib import Path

history_file = Path('learnings/learning_history.jsonl')
with open(history_file) as f:
    for line in f:
        entry = json.loads(line)
        print(entry)
```

### Parent/Child Loop Relationships

Loops automatically discover relationships:
- **Parent**: Directory above `child_loops/`
- **Children**: Directories in `child_loops/`
- **Siblings**: Other directories in same `child_loops/`

All learnings from related loops are available in Reflect phase.

## Contributing

When adding new features:

1. Update `markdown_ravl_executor.py` for core functionality
2. Update `run_markdown_ravl.py` for CLI/config handling
3. Add prompt templates to `prompts/` if needed
4. Update this README and `CONFIG_FORMAT.md`
5. Add example in a test loop

## See Also

- [CONFIG_FORMAT.md](CONFIG_FORMAT.md) - Detailed config specification
- [prompts/README.md](prompts/README.md) - Prompt template documentation
- [../RAVL_PROTOCOL.md](../RAVL_PROTOCOL.md) - RAVL protocol specification
