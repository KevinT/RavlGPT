# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Framework Overview

**RAVL** (Reflect-Act-Verify-Learn) is an AI-native, autonomous loop framework designed for continuous learning and self-improvement. It's used as a git submodule by projects that need intelligent data orchestration and autonomous agents.

**Key Characteristics:**
- Protocol-based architecture (structural typing) for maximum flexibility
- LLM-driven code generation from markdown-based loop definitions
- Continuous learning through model persistence and exponential moving averages
- Support for both Python classes and markdown-based loops
- Composable through mixins for enterprise integrations
- Health monitoring and self-diagnostic capabilities

## Architecture

### Module Organization

**Core Execution**
- `common/ravl_protocol.py` - Protocol definition (interface specification using Python Protocol)
- `common/ravl_base.py` - Base class with model persistence, history tracking, cross-loop communication
- `common/ravl_runner.py` - Main execution engine for running loops with discovery, validation, error handling

**Code Generation & Execution**
- `common/llm/` - LLM integrations and code generation:
  - `llm_providers.py` - Multi-provider support (Anthropic, OpenAI, Google, Ollama)
  - `run_markdown_ravl.py` - Executes markdown-based loop definitions
  - `prompts/` - LLM system and user prompts for code generation
- `common/execution/code/` - Python code executor with sandboxing and safety checks
- `common/execution/markdown/` - Markdown interpreter and section parser

**Framework Utilities**
- `common/core/` - Core services:
  - `learning/` - Model persistence, exponential moving averages, history tracking
  - `error_handling/` - Semantic error analysis, failure pattern detection
  - `verification/` - Schema validation, output verification
- `common/mixins/` - Reusable integrations:
  - `google_apis_mixin.py` - Google Workspace/Docs/Sheets access
  - `llm_mixin.py` - LLM analysis helpers
  - `credential_validator.py` - Token validation and environment extraction
- `common/integrations/` - External system connectors
- `common/utils/` - File I/O, constants, logging utilities

**CLI Tools**
- `bin/ravl` - Main loop execution entry point
- `bin/ravl-clean` - Remove learning artifacts (reset model state)
- `bin/ravl-clone` - Clone loops from templates or existing implementations
- `bin/ravl-list` - List all available loops with metadata
- `bin/ravl-health` - AI-powered diagnostic analysis of failing loops
- `bin/ravl-sync-claude` / `ravl-sync-opencode` - Install commands in AI REPLs
- `bin/ravl-wrapper` - Unified CLI interface

**Templates & Examples**
- `templates/` - Loop scaffolds for common patterns:
  - `data_ingress/` - API data fetching and transformation
  - `empty_loop/` - Minimal RAVL loop template
  - `strategic_coherence/` - Pattern-based decision making
- `examples/` - Complete example implementations

### Key Design Patterns

**1. Protocol-Based Architecture**
- Uses Python's `Protocol` for structural typing (duck typing) instead of inheritance
- Any class with `reflect()`, `act()`, `verify()`, `learn()` methods is a valid RAVL loop
- Enables markdown executors to wrap loop definitions without explicit inheritance
- Allows future loop formats without framework changes

**2. Utility Extraction & Separation of Concerns**
- Base classes provide only core infrastructure (model persistence, history)
- Functionality extracted into focused utility classes for testability
- Example: `CodeCacheManager`, `CodeGenerator`, `LoopContextBuilder` in projects using markdown loops

**3. Model Persistence & Exponential Moving Averages**
- Models stored as versioned YAML with timestamps
- EMA formula: `new_metric = (0.7 * historical) + (0.3 * current)`
- Enables adaptive learning without biasing toward recent runs
- Full history preserved for analysis and rollback

**4. Multi-Provider LLM Strategy**
- Pluggable LLM providers (Anthropic, OpenAI, Google, Ollama)
- Automatic provider detection from environment
- Graceful fallbacks if primary provider unavailable
- Credential validation with environment variable extraction

**5. Markdown-Based Loop Execution**
- Define complete loops in markdown with Reflect/Act/Verify/Learn sections
- LLM generates Python code from markdown prompts
- Code execution with error handling and caching
- Useful for rapid prototyping and exploration

## RAVL Protocol Specification

All loops must implement four sequential phases:

### 1. Reflect Phase
```python
def reflect(self) -> Dict[str, Any]:
```
**Purpose:** Pure observation and data gathering
**Responsibilities:**
- Collect raw data about current state
- Compute state signatures/hashes for change detection
- Load learned context from previous iterations
- Prepare observations for Act phase

**Anti-patterns:**
- Making decisions or strategy selection
- Data interpretation or analysis
- Modifying state

### 2. Act Phase
```python
def act(self, reflection: Dict[str, Any]) -> Dict[str, Any]:
```
**Purpose:** Execute decisions based on reflection
**Responsibilities:**
- Use learned models to make decisions
- Execute API calls, transformations, or other actions
- Handle errors gracefully with fallbacks
- Collect execution results for verification

### 3. Verify Phase
```python
def verify(self, actions: Dict[str, Any]) -> Dict[str, Any]:
```
**Purpose:** Validate results against quality metrics
**Responsibilities:**
- Check action outcomes against expectations
- Measure data quality and completeness
- Identify anomalies or failures
- Prepare metrics for learning

### 4. Learn Phase
```python
def learn(self, verification: Dict[str, Any]) -> None:
```
**Purpose:** Update models based on verification results
**Responsibilities:**
- Apply exponential moving averages to metrics
- Update strategy preferences based on success rates
- Persist models to disk with timestamps
- Log patterns for future analysis

## LLM Integration

### Provider Configuration

**Automatic Detection:**
```bash
export ANTHROPIC_API_KEY="..."  # Uses Anthropic Claude (priority)
export OPENAI_API_KEY="..."     # Falls back to OpenAI
export GOOGLE_API_KEY="..."     # Falls back to Google Gemini
export OLLAMA_HOST="..."        # Local LLM option
```

**Manual Configuration:**
Create `.ravl/common/llm/llm_config.yml`:
```yaml
default_provider: anthropic
providers:
  anthropic:
    model: claude-opus
    temperature: 0.7
  openai:
    model: gpt-4
    temperature: 0.7
```

### Markdown Loop Code Generation

The framework can execute loops defined entirely in markdown:

**Markdown Structure:**
```markdown
# Reflect Section
[Describe observations needed from data sources]

# Act Section
[Define transformations, API calls, or actions]

# Verify Section
[Define validation logic and quality checks]

# Learn Section
[Define patterns to track in learnings/model.yml]
```

**Execution Flow:**
1. Markdown parser extracts sections
2. LLM generates Python code from each section
3. Generated code is cached for reuse
4. Code executed with error handling
5. Failures cached to prevent retry of broken patterns

### Custom LLM Providers

Extend `common/llm/llm_providers.py`:

```python
from common.llm.llm_providers import BaseLLMProvider

class CustomProvider(BaseLLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def generate(self, prompt: str, context: str = "") -> str:
        # Implement code generation via your provider
        return generated_code

    def validate(self) -> bool:
        # Verify provider is available and credentials work
        return credentials_valid
```

## Testing Strategy

The framework uses a two-layer testing approach:

### Layer 1: Unit Tests (Fast Feedback, <5 seconds)
**Location:** `.ravl/tests/`

| Component | File | Coverage |
|-----------|------|----------|
| Loop Discovery | `test_loop_discovery.py` | Finding/loading loops, framework/project distinction |
| RAVL Protocol | `test_ravl_protocol.py` | Phase signatures, data flow validation |
| RAVL Base | `test_ravl_base.py` | Model persistence, read/write patterns |
| LLM Providers | `test_llm_providers.py` | Provider detection, interface consistency |
| Credentials | `test_credential_validator.py` | Token validation, env extraction |
| Schema Adapters | `test_schema_adapters.py` | Output transformation, schema mapping |

**Running Unit Tests:**

```bash
# Setup (first time)
cd .ravl
python3 -m venv venv
source venv/bin/activate
python3 -m pip install --quiet pytest pytest-cov pyyaml

# Run all tests
pytest tests/ -v

# Run specific test module
pytest tests/test_ravl_protocol.py -v

# Run with coverage report
pytest tests/ --cov=common --cov-report=html

# Run single test function
pytest tests/test_ravl_base.py::test_model_persistence -v
```

### Layer 2: Health Checks (Real-World Validation, 30-60 seconds)
**Location:** `.ravl/ravl_loops/health_checks/health_check_ravl/`

- Tests actual framework patterns end-to-end
- Runs after unit tests pass
- Validates data ingestion, learning, and loop execution
- Reports HEALTHY / DEGRADED / BROKEN status

**Running Health Checks:**

```bash
cd .ravl
./bin/ravl-health health_check_ravl
```

## Common Development Tasks

### Running a Single Test
```bash
cd .ravl
source venv/bin/activate
pytest tests/test_ravl_protocol.py::test_reflect_phase -v --tb=short
```

### Running Tests with Coverage
```bash
cd .ravl
source venv/bin/activate
pytest tests/ --cov=common --cov-report=term-missing
```

### Debugging a Failed Health Check
```bash
cd .ravl
./bin/ravl-health health_check_ravl
# View diagnostic output to identify framework issues
```

### Creating a New Loop Template
```bash
# Examine existing templates
ls templates/

# Create new template directory
mkdir templates/my_pattern/
cp -r templates/empty_loop/* templates/my_pattern/

# Customize ravl_loop.py and config/
# Add to templates/my_pattern/ravl_loop.py:
#  - Implement reflect(), act(), verify(), learn() methods
#  - Inherit from RAVLBase and relevant mixins
```

### Adding a New LLM Provider
```bash
# 1. Extend BaseLLMProvider in common/llm/llm_providers.py
# 2. Implement generate() and validate() methods
# 3. Add provider detection logic to __init__
# 4. Add test cases in tests/test_llm_providers.py
# 5. Update documentation with environment variable names
```

### Verifying CLI Tools Still Work
```bash
# After modifying bin scripts, verify they're executable
chmod +x bin/ravl bin/ravl-clean bin/ravl-clone

# Test from project root
./bin/ravl --list
./bin/ravl-clean health_check_ravl
```

## Extension Points

### 1. Custom Verification Logic
Override `verify()` in your loop to implement domain-specific quality checks:
```python
def verify(self, actions: Dict[str, Any]) -> Dict[str, Any]:
    results = actions.get("results", [])
    if len(results) < expected_minimum:
        return {"status": "degraded", "reason": "insufficient_data"}
    return {"status": "success", "count": len(results)}
```

### 2. Custom Learning Metrics
Extend exponential moving average tracking in `.ravl/common/core/learning/`:
```python
# Add new metric to learn phase
self.model["success_rate"] = exponential_moving_average(
    new=current_success_rate,
    historical=self.model.get("success_rate", 0),
    weight_new=0.3
)
```

### 3. Enterprise Mixins
Add organization-specific integrations as mixins:
```python
from common.mixins.google_apis_mixin import GoogleAPISMixin
from common.mixins.llm_mixin import LLMMixin

class MyLoop(LLMMixin, GoogleAPISMixin, RAVLBase):
    def reflect(self):
        docs = self.get_google_docs(folder_id)
        analysis = self.reflect_with_llm("analyze_docs")
```

### 4. Custom Credential Validators
Extend `common/integrations/credential_validator.py` for new auth patterns:
```python
def validate_custom_token(token: str) -> bool:
    # Add validation logic for your system
    return token.startswith("custom_") and len(token) == 32
```

## Important Patterns & Conventions

### Model Persistence
- Models stored in `learnings/model.yml` (current state)
- Historical models: `learnings/model-TIMESTAMP.yml`
- Aggregated history: `learnings/history/*.json`
- Each loop is responsible for its own model writes
- Parent loops can read child models (read-only pattern)

### Loop Discovery
- Framework loops: `.ravl/ravl_loops/`
- Project loops: `ravl_loops/` (at project root)
- Markdown loops: `ravl_loops/*/ravl_loop.md`
- Python loops: `ravl_loops/*/ravl_loop.py`
- Auto-detected by `.ravl/bin/ravl` runner

### Error Handling Strategy
- Semantic analysis: Extract patterns from error messages
- Failure tracking: Remember what caused failures
- Adaptive recovery: Adjust strategies based on failure history
- Graceful fallbacks: Never fail hard; downgrade to safe mode

### Versioning & Backward Compatibility
- Framework changes must maintain loop compatibility
- Use deprecation warnings before removing features
- Version tracking in model artifacts
- CI/CD should test against multiple loop patterns

### Problem Space vs Solution Space Learning Separation

**CRITICAL DESIGN PRINCIPLE**: RAVL loops learn about TWO completely distinct domains that must NEVER be mixed:

**Problem Space (Domain Learning)** - WHAT the loop learns about its business domain:
- Location: `loop_learning/`
- Content: Domain models, verification criteria, business patterns, data quality expectations
- Example: "FDE strategy documents must include stakeholder information"

**Solution Space (Execution Learning)** - HOW to make the RAVL framework infrastructure work:
- Location: `execution_learning/`
- Content: Code generation patterns, DSL iterations, execution errors, cache validation
- Example: "Google Docs API requires documents.readonly scope in credentials"

**Storage Structure:**
```
ravl_learning/
  {hierarchy}/
    {loop_name}/
      execution_learning/         # SOLUTION SPACE
        dsl_iteration_N.json
        verified_code.py
        verified_dsl.json
        history/failure_analysis.jsonl

      loop_learning/              # PROBLEM SPACE
        model.yml
        verification_*.yml
        history/domain_metrics.jsonl
        learned_patterns.jsonl
```

**Two Separate Health Checks:**
- `./bin/ravl --execution-health <loop>` - Diagnoses infrastructure problems (code gen, DSL, execution errors)
- `./bin/ravl --loop-health <loop>` - Diagnoses domain learning problems (verification failures, model stagnation)

**Rules for AI Assistants:**
1. **Never read from both spaces in the same operation** - Keep execution context and domain context completely separate
2. **Use the right health check** - Execution failures → execution health check; verification failures → loop health check
3. **Separate infrastructure** - Each space has its own LLMAnalyzer, ThreadManager, PatternRepository, DataDiscovery classes
4. **Explicit prompts** - All prompts state their focus space in CRITICAL warnings
5. **No cross-contamination** - Execution patterns stay in execution_patterns.jsonl; domain patterns in domain_patterns.jsonl

**Why This Matters:**
- **Clear Diagnostics**: Problems diagnosed at the correct abstraction level
- **Reliable Auto-Healing**: Framework self-corrects infrastructure without touching domain logic
- **Pattern Quality**: Patterns remain focused and actionable
- **Model Integrity**: Domain models evolve based on domain insights only

See [docs/learning_separation.md](docs/learning_separation.md) for deep dive on this principle.

## Important Notes

- **Submodule Updates:** Update .ravl framework with `cd .ravl && git pull && cd ..`
- **Testing Required:** Always run tests after framework changes
- **Documentation:** Update TESTING.md and this file when adding features
- **Backward Compatibility:** Framework changes must work with existing project loops
- **Health Checks:** Can indicate framework issues; don't ignore degraded status
- **Model Artifacts:** Committed to version control to preserve learning evolution
- **Protocol Flexibility:** New loop types (beyond Python classes) can be added via Protocol

## Dependency Management

- Framework dependencies: `requirements.txt`
- Test dependencies: `requirements-test.txt`
- LLM providers optional: Install only what you need
- Install with: `pip install -r .ravl/requirements.txt`

## Extending vs. Using

**When to modify the framework:**
- Adding new LLM providers
- Improving loop discovery or execution
- Enhancing learning or verification logic
- Adding health check patterns
- Fixing bugs or security issues

**When to use mixins/templates:**
- Adding organization-specific integrations
- Creating new loop patterns
- Implementing domain-specific verification
- Building custom learning metrics
