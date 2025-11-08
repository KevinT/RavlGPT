---
description: Check copyright header status across the codebase
argument-hint: [priority-level]
---

Check the status of copyright headers in the RAVL codebase.

# Running the Check

!`python3 .claude/scripts/copyright_manager.py check $ARGUMENTS`

# What This Shows

This command scans files and shows:
- ✅ Files with valid MPL 2.0 headers
- ❌ Files missing copyright headers
- ⚠️  Files with invalid/malformed headers
- ⚠️  Files that don't exist

# Priority Levels

You can check specific priority levels:

- `priority_1` - Core framework (ravl_protocol, ravl_base, ravl_runner)
- `priority_2` - Main executors (markdown, code generation)
- `priority_3` - Key utilities (learning, error handling, verification)
- `priority_4` - Integrations (LLM providers, mixins, credentials)
- `priority_5` - CLI scripts (bin/ directory)

# Examples

```bash
# Check all files
/copyright-check

# Check only Priority 1 files
/copyright-check --priority priority_1

# Check Priority 1-3 files
/copyright-check --priority priority_1 && /copyright-check --priority priority_2 && /copyright-check --priority priority_3
```

# What Files Are Checked?

Configuration is in `.copyright-config.json`. The following files are tracked:

**Priority 1 (Core Framework):**
- common/ravl_protocol.py
- common/ravl_base.py
- common/ravl_runner.py

**Priority 2 (Main Executors):**
- common/llm/run_markdown_ravl.py
- common/execution/markdown/markdown_ravl_executor.py
- common/execution/code/data_ingress_executor.py

**Priority 3 (Key Utilities):**
- common/core/learning/learning_manager.py
- common/core/error_handling/error_semantic_analyzer.py
- common/core/verification/schema_adapters.py

**Priority 4 (Integrations):**
- common/llm/llm_providers.py
- common/mixins/llm_mixin.py
- common/integrations/google_apis_mixin.py
- common/integrations/credential_validator.py

**Priority 5 (CLI Scripts):**
- All bin/ scripts

# Fixing Issues

If files are missing headers, use:
```bash
/copyright-add
```

If headers are malformed, manually fix them using the template in `.copyright-config.json`.
