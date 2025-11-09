# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Framework Overview

**RAVL** (Reflect-Act-Verify-Learn) is an AI-native autonomous loop framework for continuous learning and self-improvement. It's designed to be used as a git submodule (`.ravl/`) by projects requiring intelligent data orchestration and autonomous agents.

**Key Characteristics:**
- Protocol-based architecture using Python's structural typing for flexibility
- LLM-driven code generation from markdown-based loop definitions
- Continuous learning via model persistence and exponential moving averages
- Composable through mixins for enterprise integrations
- Self-healing data ingestion with semantic error analysis

## Common Development Commands

### Setup
```bash
# Initial setup
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-test.txt

# Make CLI tools executable
chmod +x bin/*
```

### Running Tests
```bash
# Run all unit tests
pytest tests/ -v

# Run specific test module
pytest tests/test_ravl_protocol.py -v

# Run with coverage
pytest tests/ --cov=common --cov-report=term-missing

# Run with detailed output
pytest tests/ --tb=short -v

# Run single test function
pytest tests/test_ravl_base.py::test_model_persistence -v
```

### Running RAVL Loops
```bash
# List all available loops
./bin/ravl-list
# or with wrapper: ./ravl --list

# Run a loop
./bin/ravl {loop_name}
./bin/ravl {loop_name} --mode fast
./bin/ravl {loop_name} --quiet

# Health check (AI-powered diagnostics)
./bin/ravl-health {loop_name}

# Clean learning artifacts
./bin/ravl-clean {loop_name}

# Clone a loop from template
./bin/ravl-clone .ravl/examples/habit_tracker ravl_loops/my_new_loop
```

### Working with Submodules (for parent projects)
```bash
# Add RAVL as submodule to a project
git submodule add https://github.com/KevinT/RavlGPT .ravl

# Update RAVL to latest version
cd .ravl && git pull && cd ..
git add .ravl
```

## Architecture

### Module Organization

**Core Execution Layer**
- `common/ravl_protocol.py` - Protocol (interface) defining the four RAVL phases using Python's Protocol for structural typing
- `common/ravl_base.py` - Base class providing model persistence, history tracking, cross-loop communication
- `common/ravl_runner.py` - Main execution engine handling loop discovery, validation, and error handling

**LLM & Code Generation**
- `common/llm/llm_providers.py` - Multi-provider LLM support (Anthropic, OpenAI, Google Gemini, Ollama)
- `common/llm/run_markdown_ravl.py` - Executes markdown-based loop definitions
- `common/llm/prompts/` - System and user prompts for LLM code generation
- `common/execution/code/` - Python code executor with sandboxing
- `common/execution/markdown/` - Markdown interpreter and section parser

**Framework Services**
- `common/core/learning/` - Model persistence, exponential moving averages, history tracking
- `common/core/error_handling/` - Semantic error analysis, failure pattern detection
- `common/core/verification/` - Schema validation, output verification

**Reusable Components**
- `common/mixins/` - Composable functionality:
  - `google_apis_mixin.py` - Google Workspace/Docs/Sheets integration
  - `llm_mixin.py` - LLM analysis helpers
  - `credential_validator.py` - Token validation and environment extraction
- `common/integrations/` - External system connectors
- `common/utils/` - File I/O, constants, logging

**Templates & Examples**
- `templates/data_ingress/` - Self-healing API integration template
- `templates/strategic_coherence/` - Parent/child coordination template
- `templates/empty_loop/` - Minimal starter template
- `examples/` - Complete working examples (habit tracker, weekly reflection)

### RAVL Protocol (Four-Phase Loop)

All RAVL loops implement four sequential phases:

1. **Reflect** - Pure observation and data gathering
   - Collect raw data about current state
   - Compute state hashes for change detection
   - Load learned context from previous runs
   - **Anti-pattern:** Making decisions, analyzing data, or modifying state

2. **Act** - Execute decisions based on reflection
   - Use learned models to make decisions
   - Execute API calls, transformations, or other actions
   - Handle errors gracefully with fallbacks
   - **Anti-pattern:** Re-gathering data or updating models

3. **Verify** - Validate results against quality metrics
   - Check action outcomes against expectations
   - Measure data quality and completeness
   - Identify anomalies or failures
   - **Anti-pattern:** Taking new actions or updating models

4. **Learn** - Update models based on verification
   - Apply exponential moving averages: `new = (0.7 * old) + (0.3 * current)`
   - Update strategy preferences based on success rates
   - Persist models to disk with timestamps
   - **Anti-pattern:** Taking actions or re-analyzing data

### Key Design Patterns

**Protocol-Based Architecture**
- Uses Python's `Protocol` for structural typing (duck typing) instead of inheritance
- Any class with `reflect()`, `act()`, `verify()`, `learn()` methods is a valid RAVL loop
- Enables future loop formats without framework changes

**Model Persistence Strategy**
- Current state: `learnings/model.yml`
- Historical versions: `learnings/model-YYYY-MM-DD-HHMMSS.yml`
- Only creates new timestamped file if model actually changed
- Exponential moving average formula prevents recency bias

**Learning Space Separation (CRITICAL)**

RAVL separates two distinct learning domains that must NEVER be mixed:

**Problem Space (Domain Learning)** - WHAT the loop learns:
- Location: `loop_learning/`
- Contains: Domain models, verification criteria, business patterns
- Example: "FDE documents must include stakeholder information"

**Solution Space (Execution Learning)** - HOW the infrastructure works:
- Location: `execution_learning/`
- Contains: Code generation patterns, DSL iterations, execution errors
- Example: "Google Docs API requires documents.readonly scope"

Structure:
```
ravl_learning/{hierarchy}/{loop_name}/
  execution_learning/    # Infrastructure: code gen, DSL, errors
    dsl_iteration_N.json
    verified_code.py
    history/failure_analysis.jsonl
  
  loop_learning/         # Domain: models, patterns, metrics
    model.yml
    verification_*.yml
    history/domain_metrics.jsonl
```

Two separate health checks:
- `./bin/ravl --execution-health {loop}` - Infrastructure diagnostics
- `./bin/ravl --loop-health {loop}` - Domain learning diagnostics

**Self-Healing Data Ingestion**
- `ErrorSemanticAnalyzer` extracts error categories (auth, schema, rate_limit, etc.)
- Smart cache invalidation detects repeated errors and forces code regeneration
- Error hints guide next LLM code generation attempt

## File Organization

When extending the framework:

- **Framework code** → `common/`
- **Project-specific loops** → `ravl_loops/`
- **Templates** → `templates/`
- **Documentation** → `docs/`
- **Unit tests** → `tests/`
- **CLI tools** → `bin/`

Keep `common/` generic and reusable. Project-specific code belongs in `ravl_loops/`.

## Loop Discovery

Loops are auto-discovered from:
- Framework loops: `.ravl/ravl_loops/`
- Project loops: `ravl_loops/` (at project root)
- Markdown loops: `ravl_loops/*/ravl_loop.md`
- Python loops: `ravl_loops/*/ravl_loop.py`

## LLM Provider Configuration

**Automatic Detection:**
```bash
export ANTHROPIC_API_KEY="..."  # Priority
export OPENAI_API_KEY="..."     # Fallback
export GOOGLE_API_KEY="..."     # Fallback
export OLLAMA_HOST="..."        # Local LLM
```

**Manual Configuration:**
Create `.ravl/common/llm/llm_config.yml`:
```yaml
default_provider: anthropic
providers:
  anthropic:
    model: claude-opus
    temperature: 0.7
```

## Creating New Components

### New Loop Template
```bash
# Copy empty template
cp -r templates/empty_loop/ templates/my_pattern/

# Edit ravl_loop.py to implement:
# - reflect(), act(), verify(), learn() methods
# - Inherit from RAVLBase and relevant mixins
```

### New LLM Provider
```python
# Extend BaseLLMProvider in common/llm/llm_providers.py
from common.llm.llm_providers import BaseLLMProvider

class CustomProvider(BaseLLMProvider):
    def generate(self, prompt: str, context: str = "") -> str:
        # Implement code generation
        return generated_code
    
    def validate(self) -> bool:
        # Verify credentials work
        return True
```

### New Mixin
```python
# Add to common/mixins/
from common.ravl_base import BaseRAVLLoop

class MyIntegrationMixin(BaseRAVLLoop):
    def fetch_from_api(self):
        # Reusable integration logic
        pass
```

## Testing Strategy

**Fast Unit Tests** (tests/)
- Run before each commit
- Target: <5 seconds total
- Coverage: Framework components, protocol compliance, utilities

**Health Checks** (ravl_loops/health_checks/)
- End-to-end validation
- Run after framework changes
- Tests actual loop patterns with real LLM calls

## Important Conventions

### Cross-Loop Communication
- Parent loops can **read** child models (read-only pattern)
- Each loop writes only to its own model
- Use `get_model_history()` for meta-reflection

### Error Handling Strategy
- Semantic analysis extracts patterns from error messages
- Failure tracking remembers what caused failures
- Adaptive recovery adjusts strategies based on history
- Graceful fallbacks prevent hard failures

### Version Compatibility
- Framework changes must maintain backward compatibility with existing loops
- Use deprecation warnings before removing features
- Model artifacts include version tracking

### Code Style
- Follow PEP 8
- Use meaningful names
- Add docstrings to public functions and classes
- Keep functions focused and single-purpose

## License

Mozilla Public License 2.0 (MPL-2.0):
- Free to use commercially
- Modifications to RAVL files must be shared under MPL-2.0
- Can build proprietary extensions in separate files
- Keep copyright notices intact

## Common Workflows

### Add Test Coverage
```bash
cd .ravl
source venv/bin/activate
pytest tests/test_ravl_protocol.py --cov=common/ravl_protocol --cov-report=html
open htmlcov/index.html
```

### Debug Failed Health Check
```bash
./bin/ravl-health health_check_ravl
# View diagnostic output with root cause analysis
```

### Sync Commands to AI REPL
```bash
# For Claude Code
./bin/ravl-sync-claude

# For Opencode
./bin/ravl-sync-opencode
```

### Update Submodule in Parent Project
```bash
cd .ravl
git pull origin main
cd ..
git add .ravl
```

## Extension Points

1. **Custom Verification Logic** - Override `verify()` in your loop
2. **Custom Learning Metrics** - Add EMA tracking in `learn()`
3. **Enterprise Mixins** - Add org-specific integrations as mixins
4. **Custom Credential Validators** - Extend `credential_validator.py`

## Key Files to Understand

- `common/ravl_protocol.py` - The contract all loops must follow
- `common/ravl_base.py` - Core persistence and communication infrastructure
- `common/ravl_runner.py` - How loops are discovered and executed
- `common/llm/run_markdown_ravl.py` - Markdown loop execution flow
- `templates/data_ingress/` - Reference implementation for API integration

## Documentation

- **[Framework Overview](docs/README.md)** - Architecture and philosophy
- **[RAVL Protocol](docs/RAVL_PROTOCOL.md)** - Four-phase specification
- **[Mixins Guide](docs/MIXINS.md)** - Composable functionality
- **[LLM Infrastructure](docs/llm/README.md)** - Building LLM-powered loops
- **[Examples](examples/)** - Ready-to-run implementations
