# RAVL Loop Configuration Format

This document describes the `config/ravl.toml` format for RAVL loops.

## Basic Configuration

Every RAVL loop requires a `config/ravl.toml` file with at minimum:

```yaml
name: my_loop
description: Brief description of what this loop does
emoji: ➿
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Loop identifier (matches directory name) |
| `description` | string | Human-readable description |
| `emoji` | string | Single emoji for display |

## Loop Types

### Python Loops

Default type. Requires `ravl_loop.py` implementation.

```yaml
name: example_github_trending_tracker
description: Track GitHub trending repositories
emoji: ⭐
```

### Markdown Loops

For LLM-interpreted markdown-based loops.

```yaml
name: example_tech_news_curator
description: Curate and score tech news stories
emoji: 📰
type: markdown
```

## Advanced Configuration

### Template Variables

For markdown loops that need dynamic input:

```yaml
template_variables:
  week_number:
    cli_arg: --week
    required: false
    help: Week number to analyze
    type: string
    default: current
```

### Learning Path Configuration

Custom location for learning artifacts (see main project CLAUDE.md):

```yaml
learning_path: /custom/path/to/learnings
```

### Virtual Environment Path

Custom venv location for generated code dependencies.

**Configuration Priority (highest to lowest):**

1. **CLI flag**: `./ravl my_loop --venv-path /tmp/venv`
2. **Loop config**: `venv_path: /custom/venv` in `config/ravl.toml`
3. **Project config**: `ravl_loops/config/ravl.toml`
4. **Environment variable**: `RAVL_DEFAULT_VENV_DIRECTORY=/data/venvs`
5. **Default**: `.ravl/venv`

```yaml
venv_path: /custom/path/to/venv
```

**Note:** Unlike learning paths, venv paths do NOT inherit from parent loops. Each loop can specify its own venv or share a project-wide venv configured via environment variable.

### Dependency Whitelist

Approved packages for generated code (hierarchical):

```yaml
allowed_dependencies:
  google-api-python-client:
    min_version: '2.100.0'
    max_version: '3.0.0'

  pandas:
    min_version: '2.0.0'
    max_version: '3.0.0'
```

**Resolution Order**: Loop config → Parent config → Project config → Framework config

### Google Workspace Configuration

For loops using Google APIs:

```yaml
max_google_file_revisions_to_track: 100
```

### Runtime Options

Runtime options are configured via CLI flags only (not in `ravl.toml`):

**Quiet Mode** (suppress framework output):
```bash
./ravl my_loop --hide-execution
```

**Execution Mode** (fast vs full analysis):
```bash
./ravl my_loop --mode fast  # Skip expensive analysis
./ravl my_loop --mode full  # Complete execution (default)
```

**Timeout** (max execution time):
```bash
./ravl my_loop --timeout 600  # 10 minutes (default: 300)
```

**Disable Deep Learning** (skip model-based learning):
```bash
./ravl my_loop --no-deep-learning
```

**See full list**: `./ravl --help`

## API Integration Configuration

For loops that integrate with external APIs (data ingestion, API automation), configure API endpoints and Context7 documentation paths.

### Single API Integration

```yaml
# Simple single-API configuration
apis:
  notion:
    context7_path: /websites/developers_notion
```

### Multiple API Integrations

Loops can integrate with multiple APIs simultaneously:

```yaml
# Multi-API configuration
apis:
  notion:
    context7_path: /websites/developers_notion

  clickup:
    context7_path: /websites/developer_clickup

  google_docs:
    context7_path: /websites/developers_google_com
```

**How It Works:**
- Framework fetches API documentation from Context7 for each configured API
- Context7 docs are cached per-API: `learnings/context7_docs_cache_{api_name}.txt`
- Cache TTL defaults to 168 hours (1 week)
- Generated code receives documentation for all configured APIs
- LLM determines how to integrate with each API based on ACT section requirements

**Context7 Cache Configuration:**

```yaml
apis:
  notion:
    context7_path: /websites/developers_notion
    context7_cache_ttl_hours: 72  # Override default cache TTL
```

**Custom API (Not on Context7):**

```yaml
apis:
  custom_internal_api:
    endpoint: https://api.internal.company.com/v1
    auth_method: Bearer
    # No context7_path - provide inline documentation via ACT section
```

**When to Use Multi-API:**
- Loop needs data from multiple sources (e.g., Notion + ClickUp task data)
- Loop coordinates between APIs (e.g., sync Google Docs to Notion)
- Loop cross-references data (e.g., match HiBob employees to ClickUp users)

**Alternative Pattern:** For complex multi-source scenarios, consider using child loops where each child handles one API and the parent coordinates.

## Configuration Hierarchy

RAVL uses hierarchical configuration with this priority (highest to lowest):

1. **Loop config**: `ravl_loops/my_loop/config/ravl.toml`
2. **Parent config**: `ravl_loops/parent_loop/config/ravl.toml`
3. **Project config**: `ravl_loops/config/ravl.toml`
4. **Framework config**: `.ravl/config/ravl.toml`

Child loops automatically inherit parent configurations unless overridden.

## Complete Example

```yaml
name: api_data_ingestion
description: Ingest data from external API with self-healing
emoji: 🔄
type: markdown

# Custom paths (can also use RAVL_DEFAULT_VENV_DIRECTORY in .env)
learning_path: /data/ravl_learning/api_ingestion  # CLI: --learning-path
venv_path: /data/venvs/api_ingestion             # CLI: --venv-path, env: RAVL_DEFAULT_VENV_DIRECTORY

# Template variables for markdown
template_variables:
  api_endpoint:
    cli_arg: --endpoint
    required: true
    help: API endpoint URL
    type: string

  start_date:
    cli_arg: --start-date
    required: false
    help: Start date for data fetch (YYYY-MM-DD)
    type: string

# Approved dependencies
allowed_dependencies:
  requests:
    min_version: '2.31.0'
    max_version: '3.0.0'

  pydantic:
    min_version: '2.0.0'
    max_version: '3.0.0'

# Google integration
max_google_file_revisions_to_track: 50
```

## See Also

- [Markdown Loop Infrastructure](README.md) - Full markdown loop documentation
- [PROMPTS.md](PROMPTS.md) - Prompt template system
- Project CLAUDE.md - Configurable paths and dependency management
