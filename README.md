# RAVL Framework

**RAVL (Reflect-Act-Verify-Learn)** is an AI-native architecture for defining autonomous agentic loops that can continuously learn and improve with each iteration.

**This is pre-release software.** There are no guarantees of non-breaking changes. If the most recent version is not working, fall back to a tag or contact the authors.

📚 **[→ Read the Full Documentation](ravl/docs/README.md)** for architecture, philosophy, and detailed guides.

## 🚀 Installation

### Option 1: UV Install (Recommended)

Use this option if you want to explore RAVL and run a few local loops.

**[UV](https://docs.astral.sh/uv/)** is a Python package manager.

**Install UV:**
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Install RAVL globally:**
```bash
uv tool install ravl-framework --from git+https://github.com/KevinT/RavlGPT
```

This makes `ravl`, `ravl-list`, `ravl-health`, and all other RAVL commands available globally.

**Set up your API keys (at least one is required):**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."  # Get key from console.anthropic.com
export OPENAI_API_KEY="sk-svc-..."  # Get key from platform.openai.com
```

**Run your first loop:**
```bash
ravl ravl.examples.example_3_analysis_loop
```

### Option 2: Submodule Install

Use this option if you want to take a dependency on RAVL in your project, or be able to dig into how the framework works. Be warned though that RAVL is still in it's early stages, so expect breaking changes as it settles and stabilises into the most effective shape.

From the root directory of a git repository:

```bash
curl -sSL https://raw.githubusercontent.com/KevinT/RavlGPT/main/install.sh | bash
```

This automatically:
- Adds RAVL as a git submodule
- Sets up CLI tools
- Checks prerequisites
- Verifies your environment

**Then run your first loop:**
```bash
ravl ravl.examples.example_3_analysis_loop
```

📖 **[Full Installation Guide](INSTALL.md)** - Detailed instructions, troubleshooting, and manual installation.

**For existing projects with RAVL:**
```bash
git clone --recurse-submodules https://github.com/your-org/your-project.git
chmod +x .ravl/bin/*
```

**Update framework to latest:**
```bash
cd .ravl && git pull && cd ..
git add .ravl && git commit -m "Update RAVL framework"
```

## CLI Commands

RAVL comes with a set of powerful helper commands:

| Command | Description |
|---------|-------------|
| `ravl {loop name}` | Run a RAVL loop. Use `--help` for options |
| `ravl --list` | List all project RAVLs with last execution times |
| `ravl --clone {source} {dest}` | Clone a RAVL from existing loop or template |
| `ravl --clean {loop name}` | Remove all learning artifacts (keeps code) |
| `ravl --execution-health {loop}` | Diagnose execution/code generation issues |
| `ravl --loop-health {loop}` | Diagnose domain learning issues |
| `.ravl/bin/ravl-sync-claude` | Install `/ravl-*` slash commands in Claude Code |
| `.ravl/bin/ravl-sync-opencode` | Install `/ravl-*` slash commands in Opencode |

**Quick Access via Wrapper:**

The project includes a `./ravl` symlink that provides a unified interface:

```bash
# Make CLI tools executable
chmod +x .ravl/bin/*

# From project root, use the unified wrapper:
ravl --list              			# List all loops
ravl my_loop            			# Run a loop
ravl --clean my_loop    			# Clean up learnings
ravl --clone loop_name   	        # Clone a loop
ravl --loop-health my_loop   		# Check loop health
ravl --execution-health my_loop   	# Check loop health
ravl --help             			# Show all options
```

If the `./ravl` symlink doesn't exist in your project, create it:
```bash
ln -s .ravl/bin/ravl-wrapper ./ravl
```

**Optional: Add to PATH**

To use `ravl` commands from anywhere without needing `./`:

**For zsh (macOS):**
```bash
echo 'export PATH="$PATH:$(git rev-parse --show-toplevel)/.ravl/bin"' >> ~/.zshrc
source ~/.zshrc
```

**For bash:**
```bash
echo 'export PATH="$PATH:$(git rev-parse --show-toplevel)/.ravl/bin"' >> ~/.bashrc
source ~/.bashrc
```

Or create a symlink in a directory already on your PATH:
```bash
ln -s $(git rev-parse --show-toplevel)/.ravl/bin/ravl-wrapper /usr/local/bin/ravl
```

## Quick Start

**Using RAVL CLI:**
```bash
# List all loops in your project
$ ravl --list

# Run a loop
$ ravl ravl.examples.example_3_analysis_loop --mode fast

# Clone a new loop from template
$ ravl --clone ravl.templates.empty_loop ravl_loops/my_analytics

# Diagnose a failing loop (execution issues)
$ ravl --execution-health my_analytics

# Diagnose loop health (domain learning issues)
$ ravl --loop-health my_analytics

# Clean learning artifacts to start fresh
$ ravl --clean my_analytics
```

## 🔧 Key Framework Features

### Self-Healing Data Ingestion
Loops automatically detect, analyze, and learn from API errors:
- **ErrorSemanticAnalyzer**: Extracts error categories (resource_type, auth, schema, rate_limit, pagination, network)
- **Intelligent Failure Tracking**: Records semantic error context with actionable hints
- **Smart Cache Invalidation**: Detects repeated errors and forces code regeneration
- **LLM-Informed Adaptation**: Error hints guide next code generation attempt
- **API-Agnostic**: Works for any data source (Notion, REST APIs, GraphQL, file-based, etc.)

### LLM-Based Diagnostics
The **health check loop** provides intelligent diagnostics:
- Analyzes error messages and execution context
- Generates root cause analysis with specific suggestions
- Learns from previous successful diagnoses (few-shot learning)
- Persists diagnostic patterns for organizational learning

### Quiet Mode
Suppress framework output for cleaner logs:
```bash
ravl my_loop --hide-execution
```

### Dependency Management
Framework automatically manages dependencies for generated code:
- **UV-powered (when available)**: 10-100x faster dependency installation
- **Automatic fallback**: Uses pip if UV not installed
- **Whitelist-based security**: User approval required for new packages
- **Lock file generation**: Reproducible dependency resolution with UV

See project documentation for whitelist configuration and security details.

### Configurable Learning & Venv Paths
Store learning artifacts and virtual environments anywhere - see project documentation for configuration options.

### Prompt Normalization (Token Optimization)
**Reduce LLM token consumption by 40-70%** through intelligent deduplication of repeated blocks within prompts.

The PromptNormalizer detects repeated instructional patterns (Google Auth, LLM Provider usage, etc.) and replaces duplicates with concise references to the first occurrence. This dramatically reduces token costs while preserving full semantic meaning.

**Key Features:**
- **Deterministic**: Identical input → identical output
- **Semantic Preservation**: No meaning changes, only structural deduplication
- **Safety First**: Protected content (code, JSON, user queries) never modified
- **Performance**: <50ms overhead for typical prompts
- **Human-Readable**: Output remains clear and understandable

**Configure via interactive wizard:**
```bash
ravl --config
# Select: 3) LLM Defaults
# Then: 1) Prompt Normalization
```

**Or edit `.ravl/config/framework_defaults.toml` directly:**
```toml
[llm.prompt_normalization]
enabled = true  # Enabled by default (set to false to disable)
min_block_size = 200  # Minimum chars for deduplication
enable_logging = true  # Log reduction metrics

[llm.max_tokens]
code_generation = 16384
verification = 4096
default = 8192
```

**Or set environment variables:**
```bash
export RAVL_PROMPT_NORMALIZATION_ENABLED=true
export RAVL_PROMPT_NORMALIZATION_MIN_BLOCK_SIZE=200
export RAVL_MAX_TOKENS_CODE_GENERATION=16384
```

**Example reduction:**
```
Original prompt: 2,203 chars
Normalized: 1,632 chars
Reduction: 25.9% (saves ~571 tokens per call)
```

**Protected content:**
- Dynamic placeholders (`{variable}`)
- Code blocks (``` ```)
- JSON/YAML data
- User queries
- Small blocks (<200 chars)

See `.ravl/config/framework_defaults.toml` for full configuration options.

## 📚 Documentation

### Getting Started
- **[Framework Overview](ravl/docs/README.md)** - Architecture, philosophy, getting started
- **[RAVL Protocol](ravl/docs/RAVL_PROTOCOL.md)** - Core four-phase specification
- **[RAVL Vision](ravl/docs/RAVL_VISION.md)** - Design principles and philosophy
- **[Examples](ravl/ravl_loops/examples/)** - Ready-to-run Python and Markdown examples

### Advanced Topics
- **[Mixins Guide](ravl/docs/MIXINS.md)** - Add reusable functionality to loops
- **[LLM Infrastructure](ravl/docs/llm/README.md)** - Build LLM-powered loops
- **[Configuration Format](ravl/docs/llm/CONFIG_FORMAT.md)** - Loop configuration reference
- **[Prompt Templates](ravl/docs/llm/PROMPTS.md)** - Prompt template system

### Templates
- **[Data Ingestion](ravl/ravl_loops/ravl/child_loops/library/child_loops/data_ingress/)** - Self-healing API integration template
- **[Strategic Coherence](ravl/ravl_loops/ravl/child_loops/templates/child_loops/strategic_coherence/)** - Parent/child coordination template
- **[Empty Loop](ravl/ravl_loops/ravl/child_loops/templates/child_loops/empty_loop/)** - Minimal starter template

## 📄 License

RAVL is licensed under the [Mozilla Public License 2.0 (MPL-2.0)](LICENSE).

**What this means:**
- ✅ Free to use for commercial and non-commercial purposes
- ✅ You can modify and distribute RAVL
- ✅ Modifications to RAVL files must be shared under MPL-2.0
- ✅ You can build proprietary extensions in separate files
- ✅ Attribution is required (keep copyright notices)
- ✅ Patent grant included

See [LICENSE](LICENSE) for the full license text.

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Quick guidelines:**
1. Keep `ravl/common/` generic and reusable
2. Project-specific code goes in `ravl_loops/`
3. Documentation goes in `ravl/docs/`
4. Extract to mixins only when patterns emerge
5. Add tests for new features
6. Follow MPL-2.0 license requirements

---

**Framework Version**: 0.2.0
**Protocol Version**: 1.0
**Last Updated**: 2025-10-22

For detailed documentation, see **[ravl/docs/README.md](ravl/docs/README.md)**
