---
description: Verify copyright headers are correctly formatted
argument-hint: [file-path or priority-level]
---

Verify that copyright headers are present and correctly formatted according to MPL 2.0 requirements.

# Running Verification

!`python3 .claude/scripts/copyright_manager.py validate $ARGUMENTS`

# What This Checks

Validation ensures:
- ✅ Header contains "Mozilla Public License, v. 2.0"
- ✅ Header contains copyright notice
- ✅ Header is properly positioned (after shebang, before docstrings)
- ✅ Header has correct formatting

# When to Use

Use this command:
- Before committing changes
- After manually editing headers
- To ensure compliance with MPL 2.0
- During code review

# Examples

```bash
# Verify a specific file
/copyright-verify common/ravl_base.py

# Verify all Priority 1 files
/copyright-verify --priority priority_1

# Verify all tracked files
/copyright-verify
```

# Common Issues

**Invalid Header Position:**
- Header should be after shebang (`#!/usr/bin/env python3`)
- Header should be before docstrings (`"""...`)
- Header should be before imports

**Missing Elements:**
- Must include "Mozilla Public License, v. 2.0"
- Must include "Copyright (c) 2025 Kevin Trethewey"
- Must include license URL

**Formatting:**
- Each line should start with `#`
- Blank line should follow copyright notice
- Consistent spacing

# Fixing Invalid Headers

If headers are invalid:

1. **Check the template:** See `.copyright-config.json` for the correct format
2. **Remove invalid header:** Manually delete the malformed header
3. **Re-add with command:** Run `/copyright-add [file]`
4. **Verify again:** Run `/copyright-verify [file]`

# Integration with CI/CD

This command can be used in pre-commit hooks or CI/CD pipelines to ensure all code has proper licensing.

See `.claude/settings.json` for hook configuration.

# Exit Status

- Exit 0: All headers valid
- Exit 1: One or more headers invalid or missing

This allows use in automated workflows.
