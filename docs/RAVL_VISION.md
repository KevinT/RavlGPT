# RAVL Vision: AI-Native Autonomous Agents Through Continuous Learning

**Document Purpose**: Define the philosophical vision, core design principles, and end-state goals of the RAVL framework.

**Audience**: Framework developers, AI coding assistants, and evaluators deciding if RAVL aligns with their goals.

---

## Vision Statement

**RAVL enables developers to build autonomous agents that **minimize explicit code and configuration by maximizing the problem-solving power of AI at every step**.**

Instead of programmers writing procedures ("do this, then that, handle these error cases"), they express **intent imperatively**, and the system uses digital intelligence to iteratively triangulate toward working solutions through continuous learning.

RAVL is built for a world where:
- LLMs understand context and can creatively solve problems
- Failure is information that improves future attempts
- Agents learn from their own experience and from patterns across the ecosystem
- Code is generated, not written—and improved through iteration, not debate

---

## Core Principles

### 1. **Imperative Intent Over Declarative Configuration**

**The Principle**: Users express WHAT they want in natural language, not DECLARE how to handle every case.

**Why This Matters**:
- Declarative specs (if/then/else error handling) force picking winners upfront, limiting what LLMs can do
- Imperative specs preserve flexibility—LLMs see the full intent and creatively solve
- When first attempts fail, failures become context for better approaches next time

**Implication**: RAVL loops capture intent, not execution steps. The system infers structure, error handling, and recovery strategies from that intent. As LLMs get more powerful, the loops gets more accurate and their agency increases.

---

### 2. **User Intent Owns Source, System Owns Generated**

**The Principle**: Clear ownership prevents confusion. Users control source files. System controls generated artifacts.

**What Users Own**:
- Loop source code (`ravl_loop.md` or `ravl_loop.py`)
- Configuration choices (`config/ravl.yml`)
- Nothing else

**What System Owns**:
- Interpreted loop structure (auto-generated from user intent)
- Execution results and failure history
- Learned models and patterns

**Why This Matters**: Users always know exactly what they control. System can safely regenerate artifacts without losing user intent. No confusion about "which version is the source of truth?"

---

### 3. **Inferred Completeness with Intelligent Augmentation**

**The Principle**: System infers missing pieces and intelligently augments intent.

**What Happens**:
- User provides any subset of RAVL phases (ACT required, others optional)
- System infers missing phases from what's provided + learning history
- System augments with opportunities that improve success likelihood (error handling, validation, retry patterns)
- But only at the **imperative code level**—never adds declarative branching

**Why This Matters**: Less boilerplate for users, more power for LLMs to solve creatively. Augmentation stays flexible and imperative.

---

### 4. **Self-Healing Through Iteration, Not Retry Loops**

**The Principle**: One attempt per run. Failures flow to the next run where better approaches emerge.

**What Happens**:
1. User runs loop → System executes **once**
2. Success? → Cache code for future runs (skip inference/generation)
3. Failure? → Capture error and context in learnings
4. Next run: System reads failure history, LLM triangulates better approach
5. Repeat until success

**Why This Matters**:
- Retry loops within a run hide failure patterns
- Failures as **context** (multi-run triangulation) are more powerful than local recovery logic
- System learns **patterns** from repeated failures, not just "try again"
- One attempt per run keeps it simple: execute, evaluate, learn

---

### 5. **Hybrid Intelligence: Templated LLM Calls + Code-Generated LLM Calls**

**The Principle**: Two kinds of LLM intelligence, each used where it's strongest.

**System-Level Templated Calls** (framework infrastructure):
- Parse user intent into RAVL phases
- Generate code from specifications
- **LEARN Phase**: Analyze entire run (REFLECT+ACT+VERIFY) to extract domain patterns
- **REFLECT Phase**: Synthesize previous learnings into actionable context for ACT
- Diagnose failures and patterns
- Coach on long-term improvements

**Code-Generated LLM Calls** (within generated code):
- Recognize when a task needs AI (parse freeform text, understand errors, fetch current info from web)
- Dynamically compose LLM prompts with local context
- Execute and incorporate results into code flow

**Cross-Run Learning Flow**:
- **Run N LEARN**: LLM analyzes full RAVL cycle → persists domain insights
- **Run N+1 REFLECT**: LLM synthesizes persisted insights → builds ACT context
- **Run N+1 ACT**: Applies agency using synthesized wisdom
- Loop continues with accumulated intelligence

**Why This Matters**: Framework handles the "big picture" intelligence. Generated code handles "creative problem-solving" intelligence. LLM synthesis ensures each run learns from previous attempts. Together they create a self-improving system.

---

### 6. **Context-Driven Code Generation**

**The Principle**: Generated code stays imperative and flexible. It doesn't try to predict all cases.

**What Gets Generated**:
- Python code that **does one thing** imperatively
- Error handling for known patterns
- LLM calls for uncertain/creative operations

**What Doesn't Get Generated**:
- Declarative branching logic ("if this error type, do that")
- Pre-planned recovery paths ("try approach A, if that fails try B")
- Configuration parsing (keeps code focused on intent)

**Why This Matters**: Flexibility is the point. Generated code should be able to respond to emergent situations, not be locked into pre-planned branches.

---

### 7. **Security-First Dependency Management**

**The Principle**: Generated code can install packages at runtime, but only those explicitly approved by the user.

**What Happens**:
- Generated code uses try/except patterns to install missing dependencies dynamically
- Before caching, framework validates all pip install calls against a whitelist
- If a package isn't approved, code is rejected with clear guidance
- User approves packages by adding them to the `allowed_dependencies` section in `config/ravl.yml`
- Approval is explicit (git history shows what was added and when)
- Hierarchical: Loops inherit project defaults, can override locally

**Why This Matters**:
- Keeps code generation focused on logic, not infrastructure concerns
- Prevents supply chain attacks (only approved packages can be installed)
- Audit trail (whitelists are version controlled)
- Users maintain control (must intentionally approve new packages)
- Works in restricted environments (avoids surprise pip installation failures)

---

### 8. **Infrastructure Transparency and User Control**

**The Principle**: Infrastructure decisions (venvs, dependencies, requirements) should be transparent and user-controllable, never hidden or automatic.

**What This Means**:
- **Requirements Transparency**: Generated code has visible, scannable requirements that users can inspect and approve
- **Dependency Approval**: Users explicitly whitelist packages; there's a clear audit trail (git history)
- **Virtual Environment Control**: Venvs are configurable (location, sharing, isolation level), not black boxes
- **Generated Code Visibility**: Requirements.txt is auto-generated and stored in loop directory, easily reviewable
- **Failure Clarity**: If infrastructure operations fail, messages explain exactly what happened and why

**Concrete Implementation**:
- Generated code calls → RequirementsGenerator scans imports → Creates visible requirements.txt
- DependencyValidator checks against whitelist before execution
- VenvManager creates/manages isolated environments with configurable paths
- Error messages guide users to approval workflows step-by-step

**Why This Matters**:
- Non-technical users can understand what's happening without Python expertise
- Infrastructure decisions stay under user control (can share venvs, store on different drives)
- Mistakes are obvious and fixable (unapproved package? Clear error, clear fix)
- Security is human-verifiable (whitelist is git history, audit trail is complete)
- Failures provide actionable guidance (errors explain exactly what to do)

---

### 9. **Problem Space and Solution Space Learning Separation**

**The Principle**: RAVL loops learn about TWO distinct domains that must NEVER be mixed:
1. **Problem Space (Domain Learning)**: WHAT the loop learns about its domain—the business problem it's solving
2. **Solution Space (Execution Learning)**: HOW to make the RAVL framework infrastructure work correctly

**What This Means**:

**Problem Space (loop_learning/)** captures:
- Domain models and business concepts
- Verification criteria for domain quality
- Domain-specific patterns and insights
- What makes good output for this domain
- Example: "FDE Operating Strategy must include stakeholder information"

**Solution Space (execution_learning/)** captures:
- Code generation success/failure patterns
- DSL convergence and iteration history
- Execution errors (syntax, runtime, imports)
- Cache validation and invalidation
- Framework infrastructure behaviors
- Example: "Google Sheets API requires OAuth scopes in credentials"

**Why This Matters**:
- **Clear Context Setting**: When loop runs, it gets domain context (problem) + execution context (solution) separately
- **Independent Health Checks**: Execution failures don't contaminate domain learning and vice versa
- **Specialized Diagnostics**: LLM analyzes execution issues separately from domain issues
- **Auto-Healing Precision**: Framework self-corrects infrastructure problems without affecting domain logic
- **Prevents Cross-Contamination**: Execution errors don't pollute verification criteria; domain changes don't affect code generation patterns

**Storage Structure**:
```
ravl_learning/
  {hierarchy}/
    {loop_name}/
      execution_learning/         # SOLUTION SPACE: How to make it work
        dsl_iteration_N.json      # DSL generation attempts
        verified_code.py          # Cached working code
        verified_dsl.json         # Cached working DSL
        history/
          failure_analysis.jsonl  # Execution error patterns
          initialization_failures/ # Pre-RAVL failures

      loop_learning/              # PROBLEM SPACE: What it learns
        model.yml                 # Current domain model
        model-TIMESTAMP.yml       # Historical models
        verification_*.yml        # Domain verification results
        history/
          domain_metrics.jsonl    # Domain quality metrics
        learned_patterns.jsonl    # Domain patterns
```

**LLM Synthesis in Each Space**:

**Execution Learning Synthesis** (Solution Space):
- DSL inference engine reads `execution_learning/` history
- Identifies code generation patterns that work/fail
- Adjusts prompts and strategies for better code generation
- Example: "When accessing Google Sheets, always include OAuth scopes"

**Domain Learning Synthesis** (Problem Space):
- LEARN phase analyzes full run (REFLECT+ACT+VERIFY)
- Persists insights about domain effectiveness to `loop_learning/`
- REFLECT phase synthesizes insights into ACT context
- Example: "FDE documents need stakeholder validation, email field is critical"

**Concrete Example**:
- **Problem Space**: Loop learns that "FDE Operating Strategy documents always have 3 sections: Context, Approach, Outcomes. Previous VERIFY suggested adding stakeholder validation."
- **Solution Space**: Loop learns that "Google Docs API requires documents.readonly scope in OAuth credentials. Code generation improved after using LLMProviderFactory pattern."

These are completely different kinds of knowledge, use different synthesis approaches, and must be treated separately.

---

### 10. **Failure Analysis and Cross-Run Triangulation**

**The Principle**: Failures are data that improves future attempts through LLM-powered synthesis.

**What Happens**:
- Execution captures: error messages, verification failures, context, timestamps
- **LEARN phase**: Uses LLM to analyze entire run, extract patterns, persist insights
- Failures accumulated in learnings across multiple runs
- **REFLECT phase**: Uses LLM to synthesize failure history into actionable guidance
- **ACT phase**: Receives synthesized insights, not raw failure logs
- Health check analyzes long-term patterns and provides coaching

**Cross-Run Intelligence Flow**:
1. **Run N**: Fails with specific issues → VERIFY suggests improvements
2. **LEARN**: LLM analyzes why it failed (context? decisions? outcomes?)
3. **Persists**: Domain insights saved to `loop_learning/`
4. **Run N+1 REFLECT**: LLM reads insights, synthesizes guidance
5. **Run N+1 ACT**: Sees "Priority: address X, avoid Y, try Z"
6. **Triangulation**: Each run adds wisdom, patterns emerge

**Why This Matters**:
- Patterns emerge from multiple attempts (failure A + failure B → insight C)
- LLM synthesis transforms raw failures into actionable guidance
- ACT gets direct instructions, not just "here are 5 failure logs"
- Health check sees what individual runs miss
- Framework becomes smarter the more it fails
- "Learning" isn't just tracking success—it's synthesizing wisdom from failure patterns

---

## Design Decisions and Rationale

### Why Separate One Attempt Per Run from Retry?

**Decision**: Never retry within a run. Failures become context for next run.

**Rationale**:
- Retry loops are local optimization—they solve the immediate problem
- Multi-run triangulation is global optimization—it learns patterns
- One attempt keeps state simple: ran? success or failure? that's it.
- Full failure context flows forward for better next attempts

### Why Not Declarative Configuration?

**Decision**: Avoid if/then/else specs. Use imperative user intent instead.

**Rationale**:
- Declarative specs pre-decide error handling, limiting LLM flexibility
- Imperative specs preserve the intent; LLM stays flexible
- Declarative locks you in; imperative leaves room for creativity
- If you're declarative about "what if Google Docs API isn't available?", you've already decided the answer. Imperative just says "fetch the doc" and lets LLM handle the details

### Why Augment, Not Require?

**Decision**: System infers missing pieces and adds opportunities.

**Rationale**:
- Requiring all phases makes barriers to entry high
- Inferring phases lets people start simple ("here's what I want")
- Augmentation only improves success likelihood; it's optional intelligence
- User can still be explicit if they want to override

---

## Alignment Questions

These questions help evaluate if RAVL aligns with your goals:

1. **Do you want to write less code?** RAVL generates code from intent.
2. **Do you value learning from failures?** RAVL captures failure patterns across runs.
3. **Do you want agents that get smarter over time?** RAVL's Learn phase updates models continuously.
4. **Are you building for AI-assisted systems?** RAVL is designed with AI copilots in mind.
5. **Do you prefer flexibility over rigid specs?** RAVL stays imperative to preserve flexibility.
6. **Do you need transparency about what the system inferred?** RAVL saves interpreted structures so you can inspect and refine.

If you said "yes" to most of these, RAVL might be a good fit.

---

## What RAVL Is NOT

- **Not a task scheduler** - RAVL is for agents that learn and adapt, not workflows
- **Not a retry framework** - Failures trigger triangulation next run, not immediate retry
- **Not a configuration engine** - User intent drives behavior, not config files
- **Not a LLM wrapper** - RAVL is a loop pattern that happens to use LLMs effectively
- **Not a perfect system** - Agents make mistakes; the point is learning from them

---

## The End State

A mature RAVL loop:
- Runs, learns from results, improves autonomously
- Handles edge cases gracefully through learned patterns
- Coordinates with other loops (parent/child, sibling sharing)
- Requires minimal maintenance (configuration is already learned)
- Improves over time as failure patterns are captured
- Can be understood by reading user intent, not generated code

A mature RAVL ecosystem:
- Patterns learned in one loop inform others
- Developers focus on describing intent, not writing error handling
- Health checks diagnose problems no human could spot in raw logs
- The system is "smarter" than any single developer because it learns across all loops
- New problems are solved by feeding failure context to LLMs, not writing new code

---

## Principles for Contributors

If you're extending or improving RAVL:

1. **Preserve Imperative Intent**: Don't add declarative configuration options—infer from intent instead
2. **Minimize User Specification**: If the system can figure it out, don't make users specify it
3. **Maximize LLM Intelligence**: When uncertain, ask an LLM with full context rather than hard-code a decision
4. **Respect Iteration**: One attempt per run. Failures flow forward.
5. **Honor Ownership**: Users own source and config. System owns generated and learned.
6. **Think Long-Term**: Features should improve the system over time, not just for one run
7. **Prioritize Security**: Generated code should be validated before caching. Whitelisting is better than denying. Audit trails matter.
8. **Ensure Infrastructure Transparency**: Don't hide infrastructure decisions (venvs, deps, requirements). Make everything visible, auditable, and user-controllable. Errors should guide users to fixes.
9. **Maintain Problem/Solution Space Separation**: Keep execution learning (HOW framework works) completely separate from domain learning (WHAT loop learns about its domain). Never mix these contexts. Use separate storage, separate health checks, separate diagnostics.

---

## Next Steps

**Want to learn about the specifics?**
- See [RAVL Protocol](RAVL_PROTOCOL.md) for the four-phase specification
- Check [examples](examples/) for working implementations
- Try [templates](../templates/) to get started

**Want to evaluate alignment?**
- Read the "Alignment Questions" above
- Try building a loop and see if the vision matches your experience
- Ask: "Does this feel like a system designed for learning and triangulation?"

---

## Vision Evolution

This vision document describes the **goals and principles**, not the implementation. As the framework evolves:
- The vision should remain stable (the "why" doesn't change)
- The implementation will improve (the "how" evolves)
- Protocol changes should be evaluated against these principles
- New features should serve the vision, not drift from it
