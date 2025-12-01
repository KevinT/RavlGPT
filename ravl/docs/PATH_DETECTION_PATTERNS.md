# Path Detection Patterns in RAVL Framework

## Installation Methods

RAVL supports two installation methods equally:

### 1. UV/pip Package Install

```bash
uv tool install ravl
```

- **Framework location**: `site-packages/ravl/`
- **Config location**: `~/.config/ravl/config.toml`
- **No `.ravl/` directory**
- System-wide installation

### 2. Git Submodule

```bash
git submodule add https://github.com/KevinT/RavlGPT .ravl
```

- **Framework location**: `<project>/.ravl/ravl/`
- **Config location**: `<project>/.ravl/config.toml`
- **Has `.ravl/` directory** (convention, not requirement)
- Project-local installation

## Three Distinct Concepts

The framework must distinguish between three separate concepts:

### 1. Framework Location
**Where the RAVL Python package lives**

```python
import ravl
from pathlib import Path

framework_root = Path(ravl.__file__).parent.parent
```

- UV install: `site-packages/ravl/`
- Submodule: `<project>/.ravl/ravl/`
- Discovered via Python imports
- Always exists (framework is installed)

### 2. Project Location
**Where user content (loops, data) lives - OPTIONAL!**

```python
from ravl.common.cli.ravl_cli_base import RAVLCLIBase

project_root = RAVLCLIBase.find_project_root(required=False)
```

- **Project marker**: `ravl_loops/` directory
- May not exist yet (new users running `ravl --init`)
- Optional for some commands (like `ravl --config`)
- User can have framework installed without having a project

### 3. Working Directory
**Where command runs from - ARBITRARY**

```python
from pathlib import Path

cwd = Path.cwd()
```

- User can run commands from anywhere
- Not reliable for finding project or framework

## Project Detection

### Correct Marker: `ravl_loops/` Directory

```python
# ✅ CORRECT:
from ravl.common.cli.ravl_cli_base import RAVLCLIBase

project_root = RAVLCLIBase.find_project_root(required=False)
# Searches up directory tree for ravl_loops/ directory
```

**Why `ravl_loops/` is correct:**
- Exists in UV installations (user creates it with `ravl --init`)
- Exists in submodule installations
- Clearly indicates user has a RAVL project
- Created by users, not by framework installation

### Wrong Markers

```python
# ❌ WRONG: Searching for .ravl/
# Does NOT exist in UV installations!
if (current / '.ravl').exists():
    return current

# ❌ WRONG: Searching for .git/
# This is version control, not project marker
# May find wrong root in monorepos
if (current / '.git').exists():
    return current
```

## Installation Type Detection

```python
from ravl.common.cli.ravl_cli_base import RAVLCLIBase

install_type = RAVLCLIBase.get_installation_type()
# Returns: 'package' or 'submodule'
```

**Detection logic:**
1. Check if framework path contains `.ravl` in parts
2. If yes → `'submodule'`
3. If no → `'package'`

**Used for:**
- Determining config file location
- Displaying installation info to user
- Adjusting behavior for installation method

## Configuration Path Resolution

```python
from ravl.common.cli.ravl_cli_base import RAVLCLIBase

config_path = RAVLCLIBase.get_config_path()
```

**Resolution logic:**
1. Detect installation type
2. If submodule + project exists → `<project>/.ravl/config.toml`
3. Otherwise → `~/.config/ravl/config.toml`

**Benefits:**
- UV users get system-wide config
- Submodule users get project-local config
- Graceful fallback for edge cases

## Correct Usage Patterns

### Pattern 1: Finding Project (Optional)

```python
from ravl.common.cli.ravl_cli_base import RAVLCLIBase

# For commands that work without a project (like --config)
project_root = RAVLCLIBase.find_project_root(required=False)

if (project_root / 'ravl_loops').exists():
    print(f"Found project at: {project_root}")
else:
    print("No project found. Run 'ravl --init' to create one.")
```

### Pattern 2: Finding Project (Required)

```python
from ravl.common.cli.ravl_cli_base import RAVLCLIBase

# For commands that need a project (like running a loop)
try:
    project_root = RAVLCLIBase.find_project_root(required=True)
except RuntimeError as e:
    print(f"Error: {e}")
    print("Use 'ravl --init' to create a new project.")
    sys.exit(1)
```

### Pattern 3: Finding Framework

```python
from ravl.common.cli.ravl_cli_base import RAVLCLIBase

framework_root = RAVLCLIBase.find_framework_root()
# Always succeeds (framework is installed)
```

### Pattern 4: In Generated Code

Generated code should use environment variables, not path detection:

```python
import os
from pathlib import Path

# ✅ CORRECT: Use environment variables
learnings_dir = Path(os.environ.get('RAVL_LEARNINGS_DIR'))
loop_dir = Path(os.environ.get('RAVL_LOOP_DIR'))

# ❌ WRONG: Hardcoded path walking in generated code
# Never do parent.parent.parent or manual directory searching
```

**Why environment variables:**
- Framework sets up correct paths before execution
- Generated code stays simple and portable
- No assumptions about directory structure

## Testing Requirements

All path detection code MUST handle these scenarios:

### Required Test Cases

✅ **UV installation** (no `.ravl/` directory)
```python
def test_uv_install_no_ravl_directory():
    """Test that code works when .ravl/ doesn't exist"""
```

✅ **Submodule installation** (has `.ravl/` directory)
```python
def test_submodule_install_with_ravl_directory():
    """Test that code works with .ravl/ present"""
```

✅ **No project yet** (no `ravl_loops/` directory)
```python
def test_no_project_yet():
    """Test that commands work before ravl --init"""
```

✅ **Commands outside project**
```python
def test_command_from_outside_project():
    """Test running commands from arbitrary directories"""
```

✅ **Multiple nested projects**
```python
def test_finds_nearest_ravl_loops():
    """Test that nearest ravl_loops/ is found, not outer one"""
```

### Running Tests

```bash
cd .ravl
pytest tests/test_path_detection.py -v
```

## Common Mistakes to Avoid

### Mistake 1: Assuming `.ravl/` Exists

```python
# ❌ BAD:
project_root = Path.cwd()
while project_root != project_root.parent:
    if (project_root / '.ravl').exists():
        return project_root
# Fails for UV users!
```

```python
# ✅ GOOD:
from ravl.common.cli.ravl_cli_base import RAVLCLIBase
project_root = RAVLCLIBase.find_project_root(required=False)
```

### Mistake 2: Using `.git` as Project Marker

```python
# ❌ BAD:
if (current / '.git').exists():
    return current
# This finds version control root, not project root
# Fails in monorepos with multiple RAVL projects
```

```python
# ✅ GOOD:
if (current / 'ravl_loops').exists():
    return current
```

### Mistake 3: Hardcoding Paths in Generated Code

```python
# ❌ BAD (in generated code):
project_root = Path(__file__).parent.parent.parent
learnings_dir = project_root / 'ravl_learning'
# Breaks if directory structure changes
```

```python
# ✅ GOOD (in generated code):
import os
learnings_dir = Path(os.environ['RAVL_LEARNINGS_DIR'])
# Framework sets this correctly before execution
```

### Mistake 4: Not Handling Missing Project

```python
# ❌ BAD:
project_root = RAVLCLIBase.find_project_root(required=True)
# Crashes for `ravl --config` before ravl --init
```

```python
# ✅ GOOD:
try:
    project_root = RAVLCLIBase.find_project_root(required=False)
    if (project_root / 'ravl_loops').exists():
        # Have project
    else:
        # No project yet
except Exception:
    # Handle gracefully
```

## Architecture Decision Records

### Why `ravl_loops/` Instead of `.ravl/`?

**Decision**: Use `ravl_loops/` as project marker

**Rationale:**
1. `.ravl/` doesn't exist in UV installations (most users)
2. `.ravl/` is a submodule convention, not a requirement
3. `ravl_loops/` is what users actually create for their content
4. `ravl_loops/` works identically for both installation methods

### Why Support Both Installation Methods?

**Decision**: Framework must work equally well for UV and submodule installs

**Rationale:**
1. UV is recommended installation method (faster, easier)
2. Submodule gives contributors direct access to framework code
3. Mixed teams may use different methods
4. Framework shouldn't dictate installation preference

### Why Separate Framework Location from Project Location?

**Decision**: Three distinct concepts (framework, project, working directory)

**Rationale:**
1. Framework can be installed without having a project
2. Users may have multiple projects using same framework
3. Commands like `ravl --config` work before project exists
4. Separation of concerns: installation vs. content

## Migration Guide

### Updating Existing Code

If you have code that uses old path detection:

**Step 1: Replace hardcoded directory walking**

```python
# Before:
project_root = Path.cwd()
while project_root != project_root.parent:
    if (project_root / '.ravl').exists():
        break

# After:
from ravl.common.cli.ravl_cli_base import RAVLCLIBase
project_root = RAVLCLIBase.find_project_root(required=False)
```

**Step 2: Use correct marker**

```python
# Before:
if (current / '.git').exists():
    return current

# After:
if (current / 'ravl_loops').exists():
    return current
```

**Step 3: Handle optional projects**

```python
# Before:
project_root = find_project()
if not project_root:
    sys.exit(1)

# After:
try:
    project_root = RAVLCLIBase.find_project_root(required=False)
    if not (project_root / 'ravl_loops').exists():
        print("Run 'ravl --init' to create a project")
except Exception as e:
    # Handle gracefully
```

## See Also

- [RAVL_VISION.md](RAVL_VISION.md) - Framework philosophy
- [RAVL_PROTOCOL.md](RAVL_PROTOCOL.md) - Core specification
- [INSTALL.md](../../INSTALL.md) - Installation instructions
- [tests/test_path_detection.py](../../tests/test_path_detection.py) - Test examples
