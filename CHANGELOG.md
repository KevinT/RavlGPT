# RAVL Framework Changelog

All notable changes to the RAVL (Reflect-Act-Verify-Learn) framework will be documented in this file.

The RAVL framework is an autonomous agent system for building self-improving loops that continuously learn from their execution and domain experience.

---

## November 2025

### Installation & Setup
- One-command installation via curl (no manual setup required)
- Comprehensive installation guide with prerequisites and troubleshooting
- Simplified getting started experience

### Reliability & Self-Healing
- Intelligent cache invalidation: loops automatically detect when cached code is causing repeated failures and regenerate it
- Framework now distinguishes between code logic issues vs transient failures for smarter recovery
- Reduced "stuck loop" scenarios where the same broken code runs repeatedly

### Execution & Output Improvements
- Real-time output streaming for generated code (print statements visible during execution, better UX for long-running operations)
- Self-healing execution failure tracking and cache invalidation (loops recover from failures automatically)
- Path resolution fixes for orchestrator loops and stdlib module detection
- Custom delimiter support for code extraction from LLM responses
- Cross-platform compatibility improvements for subprocess execution

### Learning Architecture
- **LLM-based cross-run learning system**: Synthesizes domain insights from previous runs and feeds them back into next iteration
- **Split learning contexts**: Separated execution learning (solution space: code generation, DSL) from loop learning (problem space: domain patterns)
  - `learnings/execution_learning/` - Infrastructure and code generation learning
  - `learnings/loop_learning/` - Domain knowledge and patterns (the "L" in RAVL)
- **Hierarchical learning access control**: Top-level parent loops remain isolated while children can share insights with siblings
  - Top-level parents cannot see each other's learning (organizational boundary enforcement)
  - Child loops automatically discover and access parent, sibling, and child learning
  - Proper path resolution with configurable learning directories
- LLM call logging with JSONL format for debugging and analysis
- Run insights synthesis in both LEARN and REFLECT phases

### Health Check System
- Split health checks into execution health (code generation issues) and loop health (domain learning issues)
- Separate CLI commands: `ravl-execution-health` and `ravl-loop-health`
- Enhanced diagnostics with actionable recommendations and pattern tracking
- Fuzzy matching for loop names with helpful suggestions
- Deprecated old unified `--health` flag in favor of specialized checks

### Code Generation & LLM
- Dynamic token limits externalized to configuration (adjustable per model)
- Improved prompt template formatting and escaping
- Framework LLM utilities available to generated code
- Fixed ModuleNotFoundError issues with correct import namespaces
- DSL guidance optimizations for token efficiency

### Google Workspace Integration
- **Google Sheets support** with markdown table export (converts spreadsheets to structured markdown)
- **Excel file support**: Read and process Excel files from Google Drive
- **Shared Drive access**: Support for enterprise Google Workspace Shared Drives
- Google Docs/Sheets/Slides unified interface with consistent APIs
- Proper timestamp handling for Sheets without Drive API dependency
- Revision tracking fixes for Google Docs

### Framework Loops
- Added `content_coherence_ravl` framework loop (analyzes document consistency, terminology inconsistencies, structural gaps)
- Delegation support with runtime config merging (`config_files` + `config_overrides`)
- Strategic coherence template for content analysis

### Configuration & Debugging
- Recent attempts retention now configurable (default: unlimited)
- Markdown-only logging for LLM interactions (removed redundant .log files)
- Pass raw execution learning files to LLM for better context
- Execution verification fixes for all loop types

---

## October 2025

### Initial Framework Release
- Core RAVL protocol implementation (Reflect, Act, Verify, Learn phases)
- Markdown-based loop specifications for rapid development
- Python-based loop support for complex logic

### Virtual Environment & Dependency Management
- **Automatic virtual environment creation and management** per loop
- **Requirements extraction** from generated code imports (scans `import` statements)
- **Dependency whitelist security model** with hierarchical approval
  - Loop-level: `config/allowed_dependencies.yml`
  - Parent-level: Inherit from parent loop
  - Project-level: Project-wide defaults
  - Framework-level: Framework defaults
- **Version constraint support**: min/max versions prevent breaking changes
- Configurable venv paths with hierarchy: CLI flag → loop config → project config → .env → default
- Clear error messages guide users through approval workflow

### Google Workspace Framework
- **Reusable workflow classes** for Google integrations
  - `GoogleDocsExporter`: Fetch and export Google Docs as markdown
  - `GoogleDocsRevisionTracker`: Track document revision history with full lineage
  - `GoogleSheetsAnalyzer`: Analyze and fetch Google Sheets data
  - `GoogleSlidesExporter`: Export Google Slides as markdown
  - `GoogleWorkspaceUserFetcher`: Fetch users from Google Workspace Directory
- **Generic GoogleDocsSourcingLoop base class**: Reduces new loops to 15-line class + config file
- **Full revision history tracking** with markdown export (captures complete edit lineage)
- **OAuth2 and service account** credential support
- Hash-based change detection for efficient updates
- Configuration-driven design (all config via `ravl.yml`)

### Self-Healing & Learning System
- **Smart learning file organization**: Structured storage with attempt tracking
- **Iterative learning foundation**: Loops learn from previous failures
- **Semantic error analysis**: Understands error patterns and suggests corrections
- **DSL inference engine**: LLM-based code generation with adaptive prompts
- **Code caching system**: Reuses verified code, invalidates on failures
- **Failure analysis tracking**: Aggregates patterns across runs
- **Schema-adaptive code generation**: Adjusts to different data structures
- Context7 integration for dynamic API documentation discovery

### Framework Organization
- **Major code reorganization**: Moved from monolithic structure to logical directories
  - `common/core/learning/` - Model updates and learning management
  - `common/core/error_handling/` - Error analysis and semantic understanding
  - `common/core/verification/` - Schema validation and quality checks
  - `common/execution/markdown/` - Markdown loop execution engine
  - `common/execution/code/` - Code generation and execution
  - `common/integrations/` - External system integrations (Google, etc.)
- **Backward compatibility layer** maintained in `common/llm/__init__.py`
- Documentation cleanup (60% reduction in duplicate files)
- Improved README with clear entry points and navigation

### CLI Tools & Commands
- **ravl-clone**: Create new loops from templates or examples
  - Support for nested destination paths
  - Nested source path support
  - Template discovery and selection
- **ravl-list**: Display all available loops with hierarchy
  - Tree view with visual nesting
  - Run status and last execution time
  - Framework loops vs project loops separation
  - Templates and examples section
  - Loop name collision detection
- **ravl-health**: Diagnostic analysis for loop health (later split into execution and loop health)
- **ravl-reset**: Clear learning artifacts to start fresh
- **ravl wrapper**: Unified command interface with automatic loop-type detection
- All CLI tools work with custom learning paths

### Configuration System
- **Hierarchical loop resolution**: Child loops inherit parent configurations
- **Learning path configuration**: CLI → loop config → parent config → .env → default
- **Venv path configuration**: Same hierarchical resolution as learning paths
- **Config file merging**: Framework supports config inheritance and overrides
- Tilde expansion support for home directory paths
- Relative path resolution with proper normalization

### Loop Templates & Examples
- **data_ingress_template**: Self-healing data ingestion with automatic retry
- **empty_loop_template**: Basic loop scaffold
- **new_markdown_loop_template**: Markdown-based loop scaffold
- **strategic_coherence_template**: Content analysis and coherence checking
- **habit_tracker** example: Simple habit tracking demonstration
- **weekly_reflection** example: Personal reflection loop
- All templates renamed with `_template` suffix for clarity

### Testing & Quality
- Comprehensive unit testing infrastructure (pytest)
- Tests for schema adapters, protocol validation, learning managers
- Framework stability tests for core components
- CI/CD ready test suite

### Documentation
- Comprehensive framework README with architecture overview
- RAVL_VISION.md: Framework principles and design philosophy
- RAVL_PROTOCOL.md: Detailed protocol specification for all four phases
- CONFIG_FORMAT.md: Configuration guide with examples
- TESTING.md: Testing guide for framework contributors
- Beginner-friendly navigation and setup guides

### Core Features
- **Markdown-based loop execution**: Free-form markdown interpretation with LLM
- **Python loop execution**: Traditional class-based loops for complex logic
- **Model persistence**: Automatic model saving with timestamps and versioning
- **History tracking**: Maintains learning history across runs
- **Credential validation**: Secure credential management with validation
- **Subprocess execution**: Proper timeout handling and cleanup
- **Framework loops**: Reusable loops that ship with framework (health checks, content analysis, etc.)
- **Loop delegation**: Loops can delegate to other loops with config merging
- **Initialization failure tracking**: Captures and reports setup issues

---

## Project History

**Initial Release**: October 14, 2025

The RAVL framework is a standalone, reusable system for building autonomous agent loops. It requires only python and some python package dependencies, along with one or more LLM API Keys to make template based prompt calls.

The framework implements the RAVL pattern (Reflect-Act-Verify-Learn) with self-healing capabilities, LLM-powered code generation, and comprehensive learning systems. The RAVL pattern was envisoned by Kevin Trethewey and was originally documented [here](https://kevintrethewey.com/blog/professional/2025-09-19-agents/).