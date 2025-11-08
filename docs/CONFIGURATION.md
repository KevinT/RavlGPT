# RAVL Configuration Guide

Complete reference for configuring RAVL loops at every level: CLI flags, configuration files, environment variables, and framework defaults.

## Quick Reference

| Configuration Aspect | CLI Flag | Config File | Environment Variable | Default |
|---------------------|----------|-------------|---------------------|---------|
| Learning path | `--learning-path PATH` | `learning_path:` | `RAVL_DEFAULT_LEARNING_DIRECTORY` | `{loop_dir}/learnings` |
| Virtual environment | `--venv-path PATH` | `venv_path:` | `RAVL_DEFAULT_VENV_DIRECTORY` | `.ravl/venv` |
| Loop directory | `--loop-dir PATH` | N/A | `RAVL_DEFAULT_LOOP_DIRECTORY` | `ravl_loops/` |
| Execution mode | `--mode {fast,full}` | N/A | N/A | `full` |
| Quiet output | `--quiet` | N/A | N/A | `false` |
| Timeout | `--timeout SECONDS` | N/A | N/A | `300` |
| Deep learning | `--no-deep-learning` | N/A | N/A | `true` |
| Dependencies | N/A | `allowed_dependencies:` | N/A | Framework defaults |
| LLM provider | N/A | N/A | `ANTHROPIC_API_KEY`, etc. | N/A |
| Google credentials | N/A | N/A | `GOOGLE_CREDENTIALS` | N/A |

**Configuration Priority (Highest to Lowest):**
1. CLI flag
2. Loop config file (`ravl_loops/my_loop/config/ravl.yml`)
3. Parent config file (for child loops)
4. Project config file (`ravl_loops/config/ravl.yml`)
5. Environment variable (`.env` file)
6. Framework defaults

---

## Configuration Methods

### 1. CLI Flags (Highest Priority)

Command-line flags override all other configuration:

```bash
./ravl my_loop --learning-path /custom/path --quiet --mode fast
```

Use CLI flags for:
- One-off overrides during development
- Testing with different paths
- CI/CD pipelines with specific requirements

**Available Flags:**

```bash
./ravl my_loop --help

Options:
  --mode {fast,full}        Execution mode (default: full)
  --learning-path PATH      Override learning directory
  --venv-path PATH          Override venv directory
  --loop-dir PATH           Override loop base directory
  --quiet                   Suppress framework output
  --timeout SECONDS         Execution timeout (default: 300)
  --no-deep-learning        Disable deep learning features
```

### 2. Configuration Files (ravl.yml)

YAML configuration files provide persistent, version-controlled settings:

```yaml
name: my_loop
description: Example loop with custom configuration
emoji: 🔄
type: markdown  # or 'python' (default)

# Custom paths
learning_path: /data/ravl_learning/my_loop
venv_path: /data/venvs/my_loop

# Dependency whitelist
allowed_dependencies:
  pandas:
    min_version: '2.0.0'
    max_version: '3.0.0'

  requests:
    min_version: '2.31.0'
    max_version: '3.0.0'

# Template variables (markdown loops only)
template_variables:
  data_source:
    cli_arg: --data-source
    required: true
    help: Data source URL
    type: string
```

**Configuration Hierarchy:**

RAVL resolves configuration using inheritance:

```
Framework config (.ravl/config/ravl.yml)
    ↓ inherits
Project config (ravl_loops/config/ravl.yml)
    ↓ inherits
Parent loop config (ravl_loops/parent/config/ravl.yml)
    ↓ inherits
Loop config (ravl_loops/parent/child/config/ravl.yml) ← HIGHEST PRIORITY
```

Child loops automatically inherit parent settings unless they override them.

**See [CONFIG_FORMAT.md](llm/CONFIG_FORMAT.md) for complete ravl.yml format reference.**

### 3. Environment Variables (.env)

Environment variables provide project-wide defaults:

```bash
# .env file at project root
RAVL_DEFAULT_LEARNING_DIRECTORY=/data/ravl_learning
RAVL_DEFAULT_VENV_DIRECTORY=/data/venvs/shared
RAVL_DEFAULT_LOOP_DIRECTORY=ravl_loops

# LLM provider API keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Google Workspace credentials
GOOGLE_CREDENTIALS='{"type":"authorized_user","client_id":"...","client_secret":"...","refresh_token":"..."}'
```

Use environment variables for:
- Project-wide paths shared by all loops
- API keys and credentials (never commit these!)
- Team collaboration with shared resources

**Important:** Add `.env` to `.gitignore` to prevent committing secrets.

### 4. Framework Defaults (Lowest Priority)

If no configuration is provided, RAVL uses sensible defaults:

- Learning path: `{loop_dir}/learnings`
- Venv path: `.ravl/venv`
- Loop directory: `ravl_loops/`
- Execution mode: `full`
- Timeout: 300 seconds

---

## Complete Configuration Precedence

### Learning Path Resolution

**Priority (highest to lowest):**

1. **CLI flag**: `./ravl my_loop --learning-path /tmp/test`
2. **Loop config**: `learning_path: /custom/path` in `config/ravl.yml`
3. **Parent config**: Child loops inherit parent's `learning_path` (appends child name)
4. **Project config**: `ravl_loops/config/ravl.yml`
5. **Environment variable**: `RAVL_DEFAULT_LEARNING_DIRECTORY=/data/learning`
6. **Default**: `{loop_dir}/learnings`

**Child Loop Inheritance:**

```python
# Parent learning path: /data/ravl/parent_loop
# Child loop name: child_loop
# Result: /data/ravl/parent_loop/child_loop/learnings
```

### Virtual Environment Path Resolution

**Priority (highest to lowest):**

1. **CLI flag**: `./ravl my_loop --venv-path /tmp/venv`
2. **Loop config**: `venv_path: /custom/venv` in `config/ravl.yml`
3. **Project config**: `ravl_loops/config/ravl.yml`
4. **Environment variable**: `RAVL_DEFAULT_VENV_DIRECTORY=/data/venvs`
5. **Default**: `.ravl/venv`

**Note:** Unlike learning paths, venv paths do NOT inherit from parent loops. Each loop can specify its own venv or share a project-wide venv.

### Dependency Whitelist Resolution

**Priority (highest to lowest):**

1. **Loop config**: `allowed_dependencies:` in loop's `config/ravl.yml`
2. **Parent config**: Inherited from parent loop
3. **Project config**: `ravl_loops/config/ravl.yml`
4. **Framework defaults**: `.ravl/config/ravl.yml`

Whitelists are **additive**: child loops inherit parent approvals and can add more.

### LLM Provider Selection

**Priority (highest to lowest):**

1. **ANTHROPIC_API_KEY** → Claude (Anthropic)
2. **OPENAI_API_KEY** → GPT (OpenAI)
3. **GOOGLE_API_KEY** → Gemini (Google)

The first available API key determines the provider. If multiple keys exist, Anthropic takes precedence.

---

## Detailed Configuration Sections

### Loop Metadata

Required in every `config/ravl.yml`:

```yaml
name: my_loop
description: Brief description of loop purpose
emoji: 🔄
type: python  # or 'markdown'
```

### Learning Path Configuration

Learning paths store model state, execution history, and failure analysis:

**Default behavior:**
```
ravl_loops/my_loop/learnings/
├── model.yml              # Current model state
├── current_state/         # Latest execution data
├── recent_attempts/       # Recent run metadata
└── history/               # Aggregated metrics
```

**Custom configuration:**

```yaml
# In config/ravl.yml
learning_path: /mnt/shared/ravl_learning/my_loop
```

**Team sharing:**

```bash
# In .env
RAVL_DEFAULT_LEARNING_DIRECTORY=/mnt/team_share/ravl_learning
```

All loops will store learning artifacts in `/mnt/team_share/ravl_learning/{loop_name}/learnings`.

**Child loop example:**

```
Parent: /data/learning/parent_loop
Child:  /data/learning/parent_loop/child_loop/learnings  # Automatic
```

### Virtual Environment Configuration

Virtual environments isolate generated code dependencies:

**Shared venv (recommended for teams):**

```bash
# In .env
RAVL_DEFAULT_VENV_DIRECTORY=/data/venvs/shared
```

All loops use `/data/venvs/shared`, reducing disk usage and install time.

**Per-loop venv:**

```yaml
# In config/ravl.yml
venv_path: /data/venvs/my_loop_venv
```

Useful when loops need conflicting package versions.

**CI/CD venv:**

```bash
./ravl my_loop --venv-path /tmp/ci_venv_${BUILD_ID}
```

Ephemeral venv for each build.

### Dependency Management (Whitelist)

Generated code can install packages, but only with approval:

```yaml
# In config/ravl.yml
allowed_dependencies:
  pandas:
    min_version: '2.0.0'    # Prevents too-old versions
    max_version: '3.0.0'    # Prevents breaking major updates

  google-api-python-client:
    min_version: '2.100.0'
    max_version: '3.0.0'

  pydantic:
    min_version: '2.0.0'
    max_version: '3.0.0'
```

**Approval workflow:**

1. Loop generates code needing `pandas v2.5.0`
2. Framework checks whitelist
3. If not approved → Error with instructions
4. User adds `pandas:` to `config/ravl.yml`
5. Re-run → Package installed

**Hierarchical approval:**

- Framework defaults: Common packages (requests, pyyaml, etc.)
- Project config: Organization-approved packages
- Loop config: Loop-specific packages

Whitelists are **additive**: child loops get parent approvals + their own.

### LLM Provider Configuration

**Anthropic (Claude):**

```bash
# In .env
ANTHROPIC_API_KEY=sk-ant-...
```

**OpenAI (GPT):**

```bash
# In .env
OPENAI_API_KEY=sk-...
```

**Google (Gemini):**

```bash
# In .env
GOOGLE_API_KEY=...
```

**Custom models (Advanced):**

Create `.ravl/config/llm_config.yml`:

```yaml
anthropic:
  model: claude-sonnet-4.0
  temperature: 0.7
  max_tokens: 4000

openai:
  model: gpt-4-turbo
  temperature: 0.5
```

### Template Variables (Markdown Loops)

For markdown-based loops that need dynamic input:

```yaml
# In config/ravl.yml
type: markdown
markdown_file: ravl_loop.md

template_variables:
  data_source:
    cli_arg: --data-source
    required: true
    help: URL of data source
    type: string

  start_date:
    cli_arg: --start-date
    required: false
    default: "2024-01-01"
    help: Start date for data fetch
    type: string
```

**Usage:**

```bash
./ravl my_loop --data-source https://api.example.com --start-date 2024-06-01
```

Variables are substituted into the markdown loop definition.

### Runtime Options

**Quiet mode** (suppress framework output):

```bash
./ravl my_loop --quiet
```

Useful for cron jobs or when piping output.

**Execution mode:**

```bash
./ravl my_loop --mode fast  # Skip expensive analysis
./ravl my_loop --mode full  # Complete execution (default)
```

**Timeout:**

```bash
./ravl my_loop --timeout 600  # 10 minutes
```

Prevents hung processes.

**Disable deep learning:**

```bash
./ravl my_loop --no-deep-learning
```

Skips model-based pattern learning.

### Google Workspace Integration

**Setup (one-time):**

1. Create OAuth 2.0 credentials in Google Cloud Console
2. Download credentials JSON
3. Add to `.env`:

```bash
# In .env
GOOGLE_CREDENTIALS='{"type":"authorized_user","client_id":"...","client_secret":"...","refresh_token":"...","universe_domain":"googleapis.com"}'
```

**Usage in generated code:**

Generated code automatically reads `GOOGLE_CREDENTIALS` from environment and creates authenticated API clients.

**Multi-team options:**

- **Shared credentials**: All developers use same `.env`
- **Per-developer**: Each developer has own `.env.local` (in `.gitignore`)
- **CI/CD**: Pipeline injects credentials as environment variable

---

## Decision Guide: Which Configuration Method?

### Use CLI Flags When:

- Testing with temporary paths
- One-off execution with special settings
- CI/CD pipeline needs per-build configuration
- Debugging with different options

```bash
# Example: Test with isolated learning path
./ravl my_loop --learning-path /tmp/test_learning --quiet
```

### Use Configuration Files (ravl.yml) When:

- Settings should persist across runs
- Configuration should be version-controlled
- Team needs to share loop setup
- Defining loop-specific dependencies

```yaml
# config/ravl.yml - committed to git
learning_path: /data/project_learning/my_loop
allowed_dependencies:
  custom-package:
    min_version: '1.0.0'
    max_version: '2.0.0'
```

### Use Environment Variables (.env) When:

- Storing secrets (API keys, credentials)
- Defining project-wide defaults
- Sharing configuration across all loops
- Team collaboration with shared resources

```bash
# .env - NOT committed to git
ANTHROPIC_API_KEY=sk-ant-...
RAVL_DEFAULT_LEARNING_DIRECTORY=/mnt/shared/learning
```

### Decision Flowchart

```
Need to configure?
│
├─ Secret/credential? → Use .env
├─ One-time test? → Use CLI flag
├─ Project-wide default? → Use .env
├─ Loop-specific persistent setting? → Use config/ravl.yml
└─ Team-shared loop config? → Use config/ravl.yml (committed)
```

---

## Real-World Configuration Examples

### Example 1: Single Developer (Defaults)

**Scenario:** Solo developer, all defaults work fine.

**Configuration:** None needed!

```bash
# Just run the loop
./ravl my_loop
```

Learning artifacts go to `ravl_loops/my_loop/learnings/`, venv at `.ravl/venv`.

### Example 2: Team with Shared Learning & Venv

**Scenario:** Team of 3 developers, want to share learning artifacts and venv on network drive.

**.env (all developers):**

```bash
RAVL_DEFAULT_LEARNING_DIRECTORY=/mnt/team_share/ravl_learning
RAVL_DEFAULT_VENV_DIRECTORY=/mnt/team_share/venvs/project_venv

ANTHROPIC_API_KEY=sk-ant-...  # Shared key
```

**Result:**

- All loops store learning in `/mnt/team_share/ravl_learning/{loop_name}/learnings`
- All loops use shared venv at `/mnt/team_share/venvs/project_venv`
- Model improvements benefit entire team
- No duplicate package installations

### Example 3: CI/CD Pipeline

**Scenario:** GitHub Actions runs loops on every commit.

**Workflow YAML:**

```yaml
- name: Run RAVL loop
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    RAVL_DEFAULT_LEARNING_DIRECTORY: /tmp/ci_learning_${{ github.run_id }}
    RAVL_DEFAULT_VENV_DIRECTORY: /tmp/ci_venv_${{ github.run_id }}
  run: |
    ./ravl my_loop --mode fast --timeout 300 --quiet
```

**Result:**

- Ephemeral learning path per build (isolated)
- Ephemeral venv per build (clean environment)
- Fast mode for quick validation
- Quiet output for cleaner logs

### Example 4: Multi-Project Setup

**Scenario:** Developer working on 3 projects, each with different RAVL configs.

**Project A (.env):**

```bash
RAVL_DEFAULT_LEARNING_DIRECTORY=/data/projectA/learning
RAVL_DEFAULT_VENV_DIRECTORY=/data/projectA/venv
ANTHROPIC_API_KEY=sk-ant-projectA...
```

**Project B (.env):**

```bash
RAVL_DEFAULT_LEARNING_DIRECTORY=/data/projectB/learning
RAVL_DEFAULT_VENV_DIRECTORY=/data/shared_venv  # Shared across projects
ANTHROPIC_API_KEY=sk-ant-projectB...
```

**Project C (.env):**

```bash
# Use defaults (learnings in project, venv in .ravl/venv)
ANTHROPIC_API_KEY=sk-ant-projectC...
```

**Result:** Each project has isolated learning, flexible venv strategy, separate API keys.

### Example 5: Loop-Specific Dependency Whitelist

**Scenario:** Parent loop with 3 child loops, one child needs special package.

**Parent config (ravl_loops/parent/config/ravl.yml):**

```yaml
name: parent_loop
description: Coordinator loop
emoji: 🔄

allowed_dependencies:
  pandas:
    min_version: '2.0.0'
    max_version: '3.0.0'
  requests:
    min_version: '2.31.0'
    max_version: '3.0.0'
```

**Child loop config (ravl_loops/parent/special_child/config/ravl.yml):**

```yaml
name: special_child
description: Needs ML packages
emoji: 🤖

allowed_dependencies:
  scikit-learn:
    min_version: '1.3.0'
    max_version: '2.0.0'
  numpy:
    min_version: '1.24.0'
    max_version: '2.0.0'
```

**Result:**

- All child loops can use `pandas` and `requests` (inherited from parent)
- `special_child` can additionally use `scikit-learn` and `numpy`
- Other children cannot use ML packages (not in their whitelist)

---

## Troubleshooting & FAQs

### Q: Where are my learning artifacts stored?

**A:** Run with verbose output to see resolved path:

```bash
./ravl my_loop
# Look for: "Learning path: /actual/resolved/path"
```

Or check health output:

```bash
./ravl-execution-health my_loop
# Shows execution health and learning artifacts location
# Or use: ./ravl-loop-health my_loop (for domain learning health)
```

### Q: Why isn't my environment variable working?

**A:** Check loading order:

1. Is `.env` file at project root? (not in subdirectory)
2. Is variable name correct? (case-sensitive)
3. Does CLI flag or config file override it?

```bash
# Debug: Check if .env is loaded
cat .env | grep RAVL_DEFAULT_LEARNING_DIRECTORY

# Verify priority
./ravl my_loop --learning-path /tmp/test  # CLI overrides .env
```

### Q: How do I share configuration across a team?

**A:**

- **Commit to git**: `config/ravl.yml` files (loop configuration)
- **Share externally**: `.env` file if it contains secrets (use shared password manager or secrets service)
- **Use .env.example**: Commit template, team members copy to `.env` and fill in secrets

### Q: Can child loops override parent configuration?

**A:** Yes! Child config always takes precedence:

```yaml
# Parent: learning_path: /data/parent
# Child:  learning_path: /data/child_override
# Result: Child uses /data/child_override (NOT /data/parent/child_name)
```

### Q: What if I need different venvs for different loops?

**A:** Configure per-loop:

```yaml
# Loop A config
venv_path: /data/venvs/loop_a_venv

# Loop B config
venv_path: /data/venvs/loop_b_venv
```

### Q: How do I migrate from default paths to custom paths?

**A:**

1. **Plan new paths**:
   - Learning: `/data/ravl_learning`
   - Venv: `/data/venvs/shared`

2. **Copy existing learning artifacts**:
   ```bash
   cp -r ravl_loops/my_loop/learnings /data/ravl_learning/my_loop/
   ```

3. **Update configuration**:
   ```bash
   # In .env
   RAVL_DEFAULT_LEARNING_DIRECTORY=/data/ravl_learning
   RAVL_DEFAULT_VENV_DIRECTORY=/data/venvs/shared
   ```

4. **Verify**:
   ```bash
   ./ravl my_loop
   # Check logs confirm new paths
   ```

5. **Clean old artifacts** (optional):
   ```bash
   rm -rf ravl_loops/my_loop/learnings
   rm -rf .ravl/venv
   ```

---

## See Also

- **[CONFIG_FORMAT.md](llm/CONFIG_FORMAT.md)** - Complete ravl.yml format reference
- **[.env.example](../../.env.example)** - Environment variable template with detailed comments
- **[RAVL_PROTOCOL.md](RAVL_PROTOCOL.md)** - Four-phase loop specification
- **[RAVL_VISION.md](RAVL_VISION.md)** - Design principles and philosophy
- **CLI Help**: Run `./ravl --help` for flag reference

**For LLM-specific configuration:**
- **[llm/README.md](llm/README.md)** - LLM infrastructure overview
- **[llm/PROMPTS.md](llm/PROMPTS.md)** - Prompt template system

**For dependency management:**
- See [CONFIG_FORMAT.md](llm/CONFIG_FORMAT.md) "Dependency Whitelist" section

---

**Last Updated:** 2025-10-30
**Framework Version:** 0.2.0
