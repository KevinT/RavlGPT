# RAVL Framework

**RAVL (Reflect-Act-Verify-Learn)** is an AI-native architecture for autonomous agents that continuously learn and improve.

This directory contains the **RAVL framework** - reusable infrastructure for building intelligent agents. Project-specific agents live in `ravl_loops/` at the project root.

## Quick Navigation

**Understanding RAVL?** Start with philosophy, then learn the mechanics:

1. **[RAVL Vision](RAVL_VISION.md)** - Why RAVL exists: Design principles, philosophy, end-state goals
2. **[RAVL Protocol](RAVL_PROTOCOL.md)** - How RAVL works: The four phases (Reflect → Act → Verify → Learn)
3. **[Examples](../ravl_loops/ravl/child_loops/examples/)** - See working implementations:
   - [Rugby Tips](../ravl_loops/ravl/child_loops/examples/child_loops/example_3_analysis_loop/) - Simple Markdown RAVL loop
   - [Simple Learning Loop](../ravl_loops/ravl/child_loops/examples/child_loops/example_4_learning_loop/) - Demonstrates basic learning patterns
   - [Tech News Curator](../ravl_loops/ravl/child_loops/examples/child_loops/example_tech_news_curator/) - Multi-source aggregation with nested loops
4. **[Templates](../ravl_loops/ravl/child_loops/templates/)** - Ready-to-use blueprints:
   - [Data Ingestion](../ravl_loops/ravl/child_loops/library/child_loops/data_ingress/) - Auto-generate API integration code (library loop)
   - [Strategic Coherence](../ravl_loops/ravl/child_loops/templates/child_loops/strategic_coherence/) - Parent/child coordination pattern
   - [Empty Loop](../ravl_loops/ravl/child_loops/templates/child_loops/empty_loop/) - Minimal starter template

**Advanced Features?**

- **[Free-Form Interpretation](free_form_interpretation.md)** - Write markdown without strict phase structure
- **[Mixins Guide](MIXINS.md)** - Add reusable functionality to loops
- **[LLM Infrastructure](llm/README.md)** - Build LLM-powered loops

**Configuring RAVL?**

- **[Configuration Guide](CONFIGURATION.md)** - Comprehensive guide to all configuration methods (CLI flags, ravl.toml, .env)
- **[CONFIG_FORMAT.md](llm/CONFIG_FORMAT.md)** - Complete ravl.toml format reference
- **[PROMPTS.md](llm/PROMPTS.md)** - Prompt template system

**Using Templates?**

See each template's own documentation for full details:
- [Data Ingestion Guide](../ravl_loops/ravl/child_loops/library/child_loops/data_ingress/README.md) - API data ingestion loops
- [Strategic Coherence Guide](../ravl_loops/ravl/child_loops/templates/child_loops/strategic_coherence/config/ravl.toml) - Multi-agent coordination

## Architecture Philosophy

**For the big-picture vision and design principles**, see [RAVL Vision](RAVL_VISION.md).

RAVL loops are **outcome-oriented autonomous agents** that:
- Follow a four-phase learning cycle (Reflect → Act → Verify → Learn)
- Share learned intelligence through persistent models
- Can be standalone or coordinate nested agents recursively
- Follow **read-anywhere, write-own** model access pattern
- Are **fully portable** - any agent can be moved anywhere in the hierarchy

## Core Concept: Four-Phase Learning Cycle

Every RAVL loop implements the same four phases:

1. **Reflect**: Observe current state without taking action
   - Review learned patterns from previous runs
   - Consider context from sibling/parent agents
   - Plan strategy based on reflection

2. **Act**: Execute based on reflection
   - Take actions toward desired outcome
   - Produce findings, data, or changes
   - Record what was attempted

3. **Verify**: Check if actions had desired impact
   - **Reuse reflection** (never re-reflect!)
   - Measure quality of outcomes
   - Detect anomalies or issues

4. **Learn**: Update intelligence based on verification
   - Adjust model weights
   - Refine patterns for future runs
   - Save timestamped model

**Key Insight:** Verify phase must reuse reflection data to ensure learning is based on what was *planned* vs what *happened*.

## Directory Structure

```
project/                              # Your project repository
├── .ravl/                            # RAVL framework (can be git submodule)
│   ├── ravl/
│   │   ├── docs/                    # 📚 Framework documentation
│   │   │   ├── README.md            # Framework overview (this file)
│   │   │   ├── RAVL_VISION.md       # Design philosophy and principles
│   │   │   ├── RAVL_PROTOCOL.md     # Detailed protocol specification
│   │   │   ├── MIXINS.md            # Mixin system guide
│   │   │   └── llm/                 # LLM infrastructure docs
│   │   │       └── README.md        # LLM-based loops guide
│   │   ├── ravl_loops/              # Framework loops
│   │   │   └── ravl/                # RAVL namespace
│   │   │       ├── examples/        # 🎯 Ready-to-run example loops
│   │   │       │   ├── example_3_analysis_loop/
│   │   │       │   ├── example_4_learning_loop/
│   │   │       │   └── example_tech_news_curator/
│   │   │       ├── templates/       # 📝 Starter blueprints
│   │   │       │   ├── empty_loop/
│   │   │       │   └── strategic_coherence/
│   │   │       ├── library/         # Delegatable patterns
│   │   │       │   ├── data_ingress/
│   │   │       │   ├── content_coherence/
│   │   │       │   └── google_docs_fetching/
│   │   │       └── framework/       # Core diagnostic tools
│   │   │           └── health_checks/
│   │   ├── bin/                     # CLI commands
│   │   │   ├── ravl                 # Main RAVL runner
│   │   │   ├── ravl-list            # List all loops
│   │   │   ├── ravl-clone           # Clone templates or existing loops
│   │   │   ├── ravl-clean           # Clean loop learnings
│   │   │   ├── ravl-execution-health # Analyze code generation & DSL (solution space)
│   │   │   ├── ravl-loop-health     # Analyze domain learning & patterns (problem space)
│   │   │   ├── ravl-sync-claude     # Sync commands to Claude Code
│   │   │   └── ravl-sync-opencode   # Sync commands to Opencode
│   │   ├── common/                  # 🔧 Framework code
│   │   ├── ravl_base.py             # Core base class (model persistence, cross-loop communication)
│   │   ├── ravl_protocol.py         # Protocol definition for type checking
│   │   ├── ravl_runner.py           # Runner utilities (CLI parsing, phase execution)
│   │   ├── prompt_loader.py         # Prompt template loading
│   │   ├── core/                    # Core RAVL framework phases
│   │   │   ├── learning/            # Learn phase (model updates)
│   │   │   ├── error_handling/      # Error analysis & recovery
│   │   │   └── verification/        # Verify phase support
│   │   ├── execution/               # Loop execution strategies
│   │   │   ├── markdown/            # Markdown-based loop execution
│   │   │   └── code/                # Code generation & execution
│   │   ├── integrations/            # External system integrations
│   │   │   ├── credential_validator.py
│   │   │   └── google_apis_mixin.py
│   │   ├── llm/                     # LLM provider abstraction
│   │   │   ├── llm_providers.py    # Factory for Anthropic, OpenAI, Google, Ollama
│   │   │   └── llm_logger.py       # LLM call logging
│   │   ├── mixins/                  # Optional functionality mixins
│   │   ├── utils/                   # Utility functions
│   │   └── cli/                     # CLI utilities
│   │       └── loop_discovery.py    # Discover loops in project
│   └── logs/                        # Runtime logs
│
└── ravl_loops/                     # Your project-specific agents
    ├── my_monitor/                  # Example: Cloned from template
    │   ├── ravl_loop.md            # Agent implementation
    │   ├── config/                 # Agent configuration
    │   ├── learnings/              # Agent's learned intelligence
    │   │   ├── model.yml           # Current model (git tracked)
    │   │   ├── model-*.yml         # Timestamped model history (git tracked)
    │   │   └── gaps_*.yml          # Output data (gitignored)
    │   └── ravl_loops/            # Nested agents (recursive!)
    │       ├── child_1/
    │       └── child_2/
    └── existing_agent/             # Another agent
        ├── ravl_loop.py            # Agent implementation
        ├── config/                 # Agent configuration
        ├── learnings/
        │   ├── model.yml
        │   └── gaps_*.json
        └── requirements.txt        # Python dependencies
```

**Separation of Concerns:**
- `.ravl/` = Framework (generic, reusable)
- `ravl_loops/` = Project code (specific to your use case)

## Model Access Pattern: Read-Anywhere, Write-Own

**Read Access** (readonly):
- Parent loops can read their children's models
- Children can read parent's model
- Siblings can read each other's models
- No cross-reading between unrelated agent hierarchies

**Write Access**:
- Each agent ONLY writes to its own `learnings/` directory
- Never write to another agent's models

**Example Information Flow:**
```
quality_guardian/
  ├── learnings/model.yml              # Parent writes here only
  └── ravl_loops/
      ├── code_quality/
      │   └── learnings/model.yml      # Code quality writes here only
      └── test_coverage/
          └── learnings/model.yml      # Test coverage writes here only

code_quality agent can read:
  ✅ Its own model (code_quality/learnings/model.yml)
  ✅ Parent model (quality_guardian/learnings/model.yml) - readonly
  ✅ Sibling model (test_coverage/learnings/model.yml) - readonly

code_quality agent writes:
  ✅ ONLY to its own model (code_quality/learnings/model.yml)
  ❌ Never to parent or sibling models
```

**Benefits:**
- No circular dependencies
- Clear debugging (changes trace to one agent)
- Eventual consistency (agents read past state)
- Hierarchical learning (children learn from parent's meta-patterns)

## Agent Patterns

### Standalone Agent
Single `ravl_loop.py` with no nested agents. Focused on one outcome.

```python
class MyLoop(BaseRAVLLoop):
    def reflect(self) -> Dict:
        # Observe and plan
        pass

    def act(self, reflection: Dict) -> Dict:
        # Execute based on plan
        pass

    def verify(self, previous_findings: Dict, reflection: Dict) -> Dict:
        # Check quality (reuse reflection!)
        pass

    def learn(self, verification: Dict, action_result: Dict):
        # Update model
        pass
```

### Parent/Coordinator Agent
Has `ravl_loops/` subdirectory with nested agents. Coordinates multiple specialized agents.

```python
class ParentLoop(BaseRAVLLoop):
    def __init__(self, child1: RAVLLoop, child2: RAVLLoop):
        super().__init__(...)
        self.child1 = child1
        self.child2 = child2

    def reflect(self) -> Dict:
        # Read children's models (readonly)
        child1_patterns = self.child1.model.get('learning')
        return {'coordination_strategy': ...}

    def act(self, reflection: Dict) -> Dict:
        # Run children and merge results
        result1 = self.child1.run()
        result2 = self.child2.run()
        return {'merged': ...}

    def verify(self, previous_findings: Dict, reflection: Dict) -> Dict:
        # Verify children and overall quality
        child1_verify = self.child1.verify(...)
        return {'overall_quality': ...}

    def learn(self, verification: Dict, action_result: Dict):
        # Children learn first, then parent learns meta-patterns
        self.child1.learn(...)
        self.child2.learn(...)
        # Update parent's coordination patterns
        self.model['coordination_patterns'] = ...
```

## Agent Portability Principle

**Every agent must be self-contained and relocatable.**

Each agent folder contains everything it needs:
- Own `config/` with all configuration
- Own `learnings/` with models and history
- Own `ravl_loop.py` implementation
- No hard dependencies on parent structure

**Why this matters:**
- ✅ Can move agents to any hierarchy level
- ✅ Can test in isolation
- ✅ Can reuse in different projects
- ✅ Clear ownership boundaries
- ✅ Enables fractal nesting

**Trade-off:** Config duplication is intentional (design coupling vs structural coupling).

## Using Mixins

The framework provides optional mixins for common functionality:

```python
from ravl_base import BaseRAVLLoop
from llm.llm_mixin import LLMMixin
from integrations.google_apis_mixin import GoogleAPIsMixin

class MyLoop(BaseRAVLLoop, LLMMixin, GoogleAPIsMixin):
    """Agent that needs LLM and Google APIs"""

    def act(self, reflection):
        # Use LLM mixin
        provider = self.detect_llm_provider()
        response = provider.generate(prompt)
        data = self.extract_json(response)

        # Use Google APIs mixin
        doc_content = self.fetch_google_doc(url)
```

**Available Framework Mixins:**
- `LLMMixin` - LLM provider detection, JSON extraction
- `GoogleAPIsMixin` - Google Docs/Slides/Sheets/Workspace APIs

**Project-Specific Mixins:**
Create in your `ravl_loops/agent_name/mixins/` for domain-specific functionality.

## Creating a New Agent

```bash
# 1. Create agent structure
mkdir -p ravl_loops/my_agent/{learnings,config}

# 2. Implement ravl_loop.py
cat > ravl_loops/my_agent/ravl_loop.py << 'EOF'
from ravl_base import BaseRAVLLoop

class MyAgentLoop(BaseRAVLLoop):
    def reflect(self): ...
    def act(self, reflection): ...
    def verify(self, previous, reflection): ...
    def learn(self, verification, action): ...
EOF

# 3. Add run.py entry point
cp ravl_loops/example_agent/run.py ravl_loops/my_agent/run.py

# 4. Create default model
cat > ravl_loops/my_agent/learnings/model.yml << 'EOF'
version: '1.0'
learning: {}
EOF
```

## Recursive Nesting

Agents can nest infinitely:

```
quality_guardian/              # Parent
├── ravl_loops/
│   ├── code_quality/         # Child
│   │   └── ravl_loops/
│   │       └── linting/      # Grandchild
│   │           └── ravl_loops/
│   │               └── ...   # Great-grandchild (fractal!)
```

**Each level** is a full RAVL loop with all four phases.

## Design Principles

### 1. Everything is a RAVL Loop
- Parent loops are RAVL loops that coordinate
- Child loops are RAVL loops that specialize
- Standalone loops are RAVL loops without children
- Same interface everywhere

### 2. Phase Discipline
- Strict separation of R-A-V-L phases
- Verify MUST reuse reflection (no re-reflection!)
- Learn phase updates model only
- Each phase has clear purpose

### 3. Model Ownership
- Write to your own models only
- Read anywhere (up/down/sideways)
- Clear debugging (one writer per model)

### 4. Gradual Abstraction
- Don't extract to framework until patterns emerge
- Let implementation guide abstraction
- Prefer duplication over premature abstraction

### 5. Agent Portability
- Self-contained with own config/learnings
- Can be relocated anywhere
- No hidden dependencies

## Framework Components

### Core Classes

**`BaseRAVLLoop`** - Base class for all agents
- Model persistence with timestamps
- Cross-loop communication (read_sibling_model, read_parent_model)
- Model history tracking
- ~240 lines of core functionality

**`RAVLRunner`** - CLI and execution utilities
- Argument parsing
- Logging setup
- Phase execution helpers
- Timeout handling

**`RAVLProtocol`** - Type protocol for structural typing
- Defines required methods (reflect, act, verify, learn)
- Enables type checking without inheritance

### Mixins

**`LLMMixin`** - LLM integrations
- Auto-detect provider (Anthropic, OpenAI, Google, Ollama)
- JSON extraction from responses

**`GoogleAPIsMixin`** - Google service integrations
- Docs, Slides, Sheets reading
- Workspace Admin SDK

### LLM Providers

**`LLMProviderFactory`** - Unified LLM interface
- Supports: Anthropic Claude, OpenAI GPT, Google Gemini, Local Ollama
- Consistent API across providers
- Auto-configuration from environment

## Getting Started

```bash
# Install framework dependencies
pip install -r .ravl/ravl/common/requirements.txt

# List all agents
python3 .ravl/ravl/common/cli/list_agents.py

# Run an agent
python3 ravl_loops/my_agent/run.py --mode full
```

## Contributing

When adding to the framework:
1. Keep `.ravl/ravl/common/` generic and reusable
2. Project-specific code goes in `ravl_loops/`
3. Extract to mixins only when patterns emerge
4. Document in `.ravl/docs/`
5. Update `RAVL_PROTOCOL.md` for protocol changes

---

**Framework Version**: 0.2.0
**Protocol Version**: 1.0
**Last Updated**: 2025-10-22
