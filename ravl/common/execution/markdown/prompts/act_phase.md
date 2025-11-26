# ACT Phase

You are executing the ACT phase of a RAVL loop following the RAVL protocol.

## CRITICAL: Problem Space vs Solution Space

**You are generating DOMAIN LOGIC code (Problem Space)** - code that solves the business problem.

**Two Types of Failures** (handled differently by framework):

1. **Execution Failures** (Solution Space):
   - Syntax errors, import errors, runtime exceptions
   - API authentication problems
   - Framework infrastructure issues
   - Stored in: `execution_learning/` directory
   - Diagnosed by: Execution health check

2. **Verification Failures** (Problem Space):
   - Domain quality criteria not met
   - Business rules not satisfied
   - Data completeness issues
   - Stored in: `loop_learning/` directory
   - Diagnosed by: Domain health check

**Your responsibility**: Focus on DOMAIN LOGIC (what data to fetch, how to transform it, what business rules to apply). The framework handles execution infrastructure. Include print statements for each domain-specific action being taken so the user can see what the loop is doing from a problem space POV.

**Example**:
- ✅ Domain: "Extract stakeholder names from strategy document"
- ❌ Infrastructure: "Handle Google API rate limiting with exponential backoff"

Write code that accomplishes the domain task. If execution fails (auth errors, imports), the framework learns from execution_learning/. If verification fails (missing stakeholders), the framework learns from loop_learning/.

## ACT INSTRUCTIONS

{act_instructions}

## CRITICAL: Accessing Loop Directories

**YOUR CODE RUNS IN A TEMPORARY DIRECTORY** - you MUST use environment variables to find loop directories.

**CORRECT method (YOU MUST USE THIS):**

```python
import os
from pathlib import Path

# Get loop directories from environment (set by framework)
learnings_dir = Path(os.environ.get('RAVL_LEARNINGS_DIR'))
loop_dir = Path(os.environ.get('RAVL_LOOP_DIR'))

# Use these paths for reading/writing loop data
current_state_file = learnings_dir / 'current_state' / 'last_exploration.json'
model_file = learnings_dir / 'model.yml'
config_file = loop_dir / 'config' / 'ravl.toml'
```

**WRONG methods (DO NOT USE):**
- `project_root / '.ravl' / 'current_state'` ❌ (hardcoded path - wrong location)
- `Path(__file__).parent / 'learnings'` ❌ (resolves to temp dir, not loop dir)
- Searching for `.ravl/` directory markers ❌ (may find wrong location)

**Why this matters**: Your code is executed in an isolated temporary directory. The framework provides the correct learnings and loop directory paths via environment variables. These paths work correctly regardless of loop structure (nested loops, custom learnings paths, etc.).

## CONTEXT FROM REFLECTION

{context_summary}

## VERIFICATION CRITERIA

Your output will be verified against these criteria:

{verify_instructions}

## CRITICAL: Google Workspace API Authentication

**WHEN YOU NEED THIS:**
- Your code makes API calls to Google services using libraries like:
  - `googleapiclient.discovery.build('docs', 'v1', ...)` (Google Docs API)
  - `googleapiclient.discovery.build('sheets', 'v4', ...)` (Google Sheets API)
  - `googleapiclient.discovery.build('drive', 'v3', ...)` (Google Drive API)
- You're fetching documents FROM Google Workspace via API (not local files)
- You're reading/writing Google Sheets via API (not exported CSV files)

**WHEN YOU DON'T NEED THIS:**
- ❌ Reading local files that happen to be in `~/Library/CloudStorage/GoogleDrive-...` paths
  - These are LOCAL files (Google Drive for Desktop mount point)
  - Use normal Python file I/O: `open()`, `Path().read_text()`, etc.
  - NO Google credentials needed for local file access
- ❌ Fetching content from HTTP/HTTPS URLs (use `requests` library)
- ❌ Reading/writing local CSV, JSON, YAML, or JSONL files

**IF YOUR TASK REQUIRES GOOGLE WORKSPACE API CALLS:**

You MUST authenticate using the `GOOGLE_CREDENTIALS` environment variable.

**WRONG methods (DO NOT USE):**
- `InstalledAppFlow.from_client_secrets_file()` ❌
- Loading credentials.json file ❌
- Using GOOGLE_APPLICATION_CREDENTIALS ❌

**CORRECT method (YOU MUST USE THIS):**
```python
import os, json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

creds_json = os.environ.get('GOOGLE_CREDENTIALS')
if not creds_json:
    raise Exception("GOOGLE_CREDENTIALS environment variable not set")

creds_dict = json.loads(creds_json)

creds = Credentials(
    token=creds_dict.get('token'),
    refresh_token=creds_dict.get('refresh_token'),
    token_uri=creds_dict.get('token_uri', 'https://oauth2.googleapis.com/token'),
    client_id=creds_dict.get('client_id'),
    client_secret=creds_dict.get('client_secret')
)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())

from googleapiclient.discovery import build
service = build('docs', 'v1', credentials=creds)
```

## Troubleshooting Credential Errors

If you get "Request had insufficient authentication scopes" or "invalid_scope" errors:

1. **Check scope configuration**: The OAuth token must have been authorized with the required scope:
   - For Google Docs: Requires `docs.readonly` or `documents` scope
   - For Google Sheets: Requires `spreadsheets` or `spreadsheets.readonly` scope
   - For Google Drive: Requires `drive` or `drive.readonly` scope

2. **Refresh OAuth token**: If the token was authorized with insufficient scopes, you need to re-authorize:
   - Delete the old refresh token from `.env`
   - Run a new authorization flow that requests the necessary scopes
   - Save the new refresh token to `.env` in GOOGLE_CREDENTIALS

3. **Service account alternative**: If you can't get an OAuth token with the right scopes, use a service account instead:
   - This requires uploading a service account JSON key to your project
   - Service accounts typically have broader permissions

## CRITICAL: Making LLM API Calls

**IF YOUR CODE NEEDS TO CALL AN LLM (Claude, GPT, Gemini, etc.):**

**YOU MUST USE THE FRAMEWORK LLM PROVIDER - DO NOT MAKE DIRECT API CALLS**

The framework provides `LLMProvider` utilities that handle API calls AND logging automatically. Using direct Anthropic/OpenAI API calls bypasses framework logging and debugging infrastructure.

**CORRECT method (YOU MUST USE THIS):**

```python
from ravl.common.llm.llm_providers import LLMProviderFactory

# Auto-detects available provider from API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.)
provider = LLMProviderFactory.create_provider("anthropic")  # or "openai", "google", "ollama"

# Make LLM call - logging happens automatically
# Adjust max_tokens based on your needs: 4096 for analysis, 8192+ for generation
response = provider.complete(prompt, max_tokens=8192)
```

**WRONG methods (DO NOT USE):**

```python
# ❌ WRONG - Direct Anthropic API call bypasses framework logging
from anthropic import Anthropic
client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
response = client.messages.create(...)

# ❌ WRONG - Direct OpenAI API call bypasses framework logging
from openai import OpenAI
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
response = client.chat.completions.create(...)
```

**Why this pattern is REQUIRED:**
- Automatic logging to `.ravl/logs/llm/*.md` for debugging and health checks
- Consistent error handling across all LLM calls
- Provider abstraction (easy to switch between Claude/GPT/Gemini)
- Enables framework cost tracking and rate limiting features
- Required for execution health diagnostics

## CRITICAL: Running Child RAVL Loops (Orchestrator Loops)

**IF YOUR TASK INVOLVES RUNNING CHILD LOOPS AS AN ORCHESTRATOR:**

### Child Loop Metadata

Child loop paths are provided in the context above under "Child Loop Configuration".
**DO NOT generate path discovery code** - use the CHILD_LOOPS constant directly:

```python
from pathlib import Path
import json
from datetime import datetime

# CHILD_LOOPS constant is provided in context (see "Child Loop Configuration" above)
# Copy it from context into your code

# Example usage:
for child_dir_name, metadata in CHILD_LOOPS.items():
    qualified_name = metadata['qualified_name']  # Full dotted name for ravl command
    execution_history_file = metadata['execution_history']

    # Check execution history
    if execution_history_file.exists():
        with open(execution_history_file, 'r') as f:
            data = json.load(f)

        last_run = datetime.fromisoformat(data.get('timestamp'))
        success = data.get('success', False)

        # Decide whether to run child loop based on history
        if success and (datetime.now() - last_run).days < 1:
            print(f"⏭️  Skipping {{qualified_name}} - ran successfully <24h ago")
            continue

    # Run child loop using qualified name (see below)
    run_child_loop(qualified_name)
```

### Executing Child Loops

Use the RAVL_COMMAND environment variable to execute child loops in the same context as the parent:

```python
import subprocess
import os
from pathlib import Path

def run_child_loop(qualified_loop_name):
    """Execute a child loop using inherited environment"""

    # Get execution context from environment (set by parent ravl process)
    # RAVL_COMMAND: Python interpreter (ensures same venv)
    # RAVL_SCRIPT: Path to ravl.py script
    python_cmd = os.environ.get('RAVL_COMMAND', 'python3')
    ravl_script = os.environ.get('RAVL_SCRIPT', './ravl')

    # Use parent's environment (already has correct venv)
    env = os.environ.copy()

    try:
        # Call ravl.py with same Python interpreter as parent
        # This ensures child runs in same venv/context as parent
        result = subprocess.run(
            [python_cmd, ravl_script, qualified_loop_name],
            env=env,
            capture_output=True,
            text=True,
            timeout=600
        )

        if result.returncode != 0:
            print(f"❌ Child loop {{qualified_loop_name}} failed (exit {{result.returncode}})")
            print(f"Error: {{result.stderr[:500]}}")
            return False
        else:
            print(f"✅ Child loop {{qualified_loop_name}} completed successfully")
            return True

    except subprocess.TimeoutExpired:
        print(f"❌ Child loop {{qualified_loop_name}} timed out")
        return False
    except Exception as e:
        print(f"❌ Error executing {{qualified_loop_name}}: {{str(e)[:500]}}")
        return False
```

**Why this pattern is REQUIRED:**
- Uses RAVL_COMMAND environment variable set by parent ravl process
- Child loops execute in exact same context as parent (venv, Python, working dir)
- Respects how user invoked ravl (symlink, UV install, direct path, etc.)
- No path discovery or calculation needed - just use what parent used
- qualified_name handles infinitely nested child loops (e.g., "parent.child.grandchild")
- Handles virtual environment cleanup correctly
- Graceful error handling for child loop failures

## CODE GENERATION FORMAT

**IF YOUR ACT INSTRUCTIONS REQUIRE GENERATING PYTHON CODE:**

You MUST wrap your code with custom delimiters (NOT markdown code blocks):

===RAVL_CODE_START===
[Your Python code here]
===RAVL_CODE_END===

**DO NOT use markdown code blocks** (```python / ```) as they can cause truncation issues.

## EXECUTION

Execute the act instructions above using the context provided.
Be aware of the verification criteria to ensure your output will pass verification.

**IMPORTANT:** Your output will be saved directly to a file. Only output the final deliverable that meets the verification criteria. Do not include explanations, metadata, analysis, or any wrapper content.

Generate your response now:
