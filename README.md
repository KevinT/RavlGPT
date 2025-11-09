# RAVL Framework

**RAVL (Reflect-Act-Verify-Learn)** is an AI-native architecture for defining autonomous agentic loops that can continuously learn and improve with each iteration.

📚 **[→ Read the Full Documentation](docs/README.md)** for architecture, philosophy, and detailed guides.

## 🚀 Installation

**Quick Install (Recommended):**

From your project root directory:

```bash
curl -sSL https://raw.githubusercontent.com/KevinT/RavlGPT/main/install.sh | bash
```

This automatically:
- Adds RAVL as a git submodule
- Sets up CLI tools
- Checks prerequisites
- Verifies your environment

**Set up your API key:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."  # Get key from console.anthropic.com
```

**Run your first loop:**
```bash
./ravl example_1_rugby_tips
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
| `./ravl {loop name}` | Run a RAVL loop. Use `--help` for options |
| `./ravl --list` | List all project RAVLs with last execution times |
| `./ravl --clone {source} {dest}` | Clone a RAVL from existing loop or template |
| `./ravl --clean {loop name}` | Remove all learning artifacts (keeps code) |
| `./ravl --execution-health {loop}` | Diagnose execution/code generation issues |
| `./ravl --loop-health {loop}` | Diagnose domain learning issues |
| `.ravl/bin/ravl-sync-claude` | Install `/ravl-*` slash commands in Claude Code |
| `.ravl/bin/ravl-sync-opencode` | Install `/ravl-*` slash commands in Opencode |

**Quick Access via Wrapper:**

The project includes a `./ravl` symlink that provides a unified interface:

```bash
# Make CLI tools executable
chmod +x .ravl/bin/*

# From project root, use the unified wrapper:
./ravl --list              # List all loops
./ravl my_loop            # Run a loop
./ravl --clean my_loop    # Clean up learnings
./ravl --clone            # Clone a loop
./ravl --health my_loop   # Check loop health
./ravl --help             # Show all options
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

**New to RAVL?** Start with the examples:
- [Rugby Tips](examples/example_1_rugby_tips/) - Simple Markdown RAVL loop
- [Simple Learning Loop](examples/example_2_simple_learning_loop/) - Demonstrates basic learning patterns
- [Examples Overview](examples/README.md) - Detailed guide to all examples

**Using RAVL CLI:**
```bash
# List all loops in your project
./ravl --list

# Run a loop
./ravl example_1_rugby_tips --mode fast

# Clone a new loop from template
./ravl --clone empty_loop_template ravl_loops/my_analytics

# Diagnose a failing loop (execution issues)
./ravl --execution-health my_analytics

# Diagnose loop health (domain learning issues)
./ravl --loop-health my_analytics

# Clean learning artifacts to start fresh
./ravl --clean my_analytics
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
./ravl my_loop --quiet
```

### Dependency Management
Framework uses whitelist-based security for generated code dependencies - see project documentation for details.

### Configurable Learning & Venv Paths
Store learning artifacts and virtual environments anywhere - see project documentation for configuration options.

## 📚 Documentation

### Getting Started
- **[Framework Overview](docs/README.md)** - Architecture, philosophy, getting started
- **[RAVL Protocol](docs/RAVL_PROTOCOL.md)** - Core four-phase specification
- **[RAVL Vision](docs/RAVL_VISION.md)** - Design principles and philosophy
- **[Examples](examples/)** - Ready-to-run Python and Markdown examples

### Advanced Topics
- **[Mixins Guide](docs/MIXINS.md)** - Add reusable functionality to loops
- **[LLM Infrastructure](docs/llm/README.md)** - Build LLM-powered loops
- **[Configuration Format](docs/llm/CONFIG_FORMAT.md)** - Loop configuration reference
- **[Prompt Templates](docs/llm/PROMPTS.md)** - Prompt template system

### Templates
- **[Data Ingestion](templates/data_ingress_template/)** - Self-healing API integration template
- **[Strategic Coherence](templates/strategic_coherence_template/)** - Parent/child coordination template
- **[Empty Loop](templates/empty_loop_template/)** - Minimal starter template

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
1. Keep `common/` generic and reusable
2. Project-specific code goes in `ravl_loops/`
3. Documentation goes in `docs/`
4. Extract to mixins only when patterns emerge
5. Add tests for new features
6. Follow MPL-2.0 license requirements

---

**Framework Version**: 0.2.0
**Protocol Version**: 1.0
**Last Updated**: 2025-10-22

For detailed documentation, see **[docs/README.md](docs/README.md)**
