---
description: Add copyright headers to files missing them
argument-hint: [file-path or priority-level or "all"]
allowed-tools: Write(*.py), Edit(*.py)
---

Add MPL 2.0 copyright headers to files that are missing them.

# Usage

You can add headers to:
- A specific file
- A priority level
- All tracked files

# Examples

```bash
# Add to a specific file
/copyright-add common/new_file.py

# Add to all Priority 1 files missing headers
/copyright-add priority_1

# Add to all Priority 1-3 files (common use case)
/copyright-add priority_1 priority_2 priority_3

# Add to all tracked files
/copyright-add all
```

# What It Does

This command:
1. Checks if the file already has a copyright header
2. If missing, inserts the MPL 2.0 header:
   - After the shebang line (for scripts)
   - At the top of the file (for other files)
   - Before docstrings and imports
3. Preserves original file content exactly

# Header Format

The header added is:
```python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey
```

# Safe Operation

- Only modifies files missing headers
- Preserves existing headers (won't duplicate)
- Smart placement (after shebang, before docstrings)
- No changes to file logic or functionality

# Before Committing

Always run this before making commits to ensure new files have proper licensing:

```bash
# Check status
/copyright-check

# Add missing headers
/copyright-add all

# Verify
/copyright-check
```

# Dry Run

To see what would be changed without making modifications:
!`python3 .claude/scripts/copyright_manager.py add --priority $1 --dry-run`

# Processing Arguments

Let me add headers based on your request:

!`if [ "$1" = "all" ]; then
  for priority in priority_1 priority_2 priority_3 priority_4 priority_5; do
    python3 .claude/scripts/copyright_manager.py add --priority $priority
  done
else
  python3 .claude/scripts/copyright_manager.py add --priority $1
fi`

Done! The copyright headers have been added to files that were missing them.

Run `/copyright-check` to verify the changes.
