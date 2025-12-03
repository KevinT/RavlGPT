# Self-Healing Data Ingress - Implementation Guide

This guide explains how to integrate the self-healing data ingress pattern into the RAVL framework for other projects.

## Architecture Overview

The data ingress pattern consists of four main components:

1. **DataIngressExecutor** (.ravl/common/llm/data_ingress_executor.py)
   - Parses markdown loop definitions
   - Orchestrates LLM-based code generation
   - Executes and validates generated code
   - Manages strategy caching

2. **Templates** (.ravl/templates/)
   - data-ingress-config.yml: Configuration template
   - data-ingress-ravl_loop.md: Minimal loop example
   - data-ingress-ravl_loop-full.md: Full example with optional sections

3. **Documentation** (.ravl/docs/)
   - data-ingress.md: User guide
   - data-ingress-implementation.md: This file

4. **Example** (ravl_loops/hibob_api_ingestion/)
   - Working example using the pattern

## How It Works

### User Perspective (Simple)

User creates one markdown file with just two sections:

```markdown
# Act
[Describe what data to fetch]

# Verify
[Describe how to validate]
```

Optional sections (augment, don't replace framework):

```markdown
# Reflect
[Domain-specific reflection hints]

# Learn
[Custom learning insights]
```

### Framework Perspective (Complex)

When user runs `ravl my_api_integration --mode fast`:

1. **Framework REFLECT** (automatic):
   - Uses DataIngressExecutor to load cached strategy
   - Fetches fresh API docs from Context7
   - Prepares metadata for code generation

2. **LLM Generates Code** (inside ACT):
   - LLM receives: required fields, output format, API docs, failure history
   - LLM generates: complete Python fetch_data() function
   - DataIngressExecutor validates and returns code

3. **Execute Code** (inside ACT):
   - DataIngressExecutor runs generated code safely
   - Captures: output, errors, execution time

4. **User's VERIFY** (from ravl_loop.md):
   - User-specified validation rules executed
   - DataIngressExecutor checks output quality

5. **Framework LEARN** (automatic):
   - DataIngressExecutor saves successful code to cache
   - Updates model with strategy effectiveness
   - Records failures for next retry

## Integration Points

### 1. Markdown Runner Integration

The existing markdown runner needs to detect and handle data-ingress loops:

**File**: `.ravl/common/llm/markdown_ravl_executor.py`

**Add to run_markdown_ravl() method**:

```python
def is_data_ingress_loop(markdown_content: str) -> bool:
    """Check if this is a data-ingress loop (has ACT + VERIFY)"""
    has_act = re.search(r'^# Act\b', markdown_content, re.MULTILINE | re.IGNORECASE)
    has_verify = re.search(r'^# Verify\b', markdown_content, re.MULTILINE | re.IGNORECASE)
    has_reflect = re.search(r'^# Reflect\b', markdown_content, re.MULTILINE | re.IGNORECASE)
    has_learn = re.search(r'^# Learn\b', markdown_content, re.MULTILINE | re.IGNORECASE)

    # Data-ingress if has ACT + VERIFY (REFLECT/LEARN optional)
    return has_act and has_verify

def execute_data_ingress_loop(loop_path: Path, executor: DataIngressExecutor, llm_provider):
    """Execute data-ingress loop workflow"""

    # User's optional REFLECT section
    user_reflect = executor.extract_section('Reflect')
    if user_reflect:
        print("  • Running user's REFLECT augmentation...")
        # Could call LLM to analyze user's reflect hints
        # For now, just log them

    # Framework's automatic REFLECT
    print("  • Framework REFLECT: loading strategy cache and API docs...")

    # ACT + LLM code generation + execution
    print("  • ACT: generating and executing code...")
    result = executor.execute_full_workflow()

    # User's VERIFY
    print("  • VERIFY: validating output...")

    # User's optional LEARN section
    user_learn = executor.extract_section('Learn')
    if user_learn:
        print("  • Running user's LEARN augmentation...")
        # Could record additional metrics beyond framework learning
        # For now, just log them

    # Framework's automatic LEARN
    print("  • Framework LEARN: updating strategy cache...")

    return result
```

**In markdown execution flow**:

```python
# Before executing ACT/VERIFY/REFLECT/LEARN, check:
markdown_content = self.ravl_loop_file.read_text()

if is_data_ingress_loop(markdown_content):
    # Route to data-ingress handler
    executor = DataIngressExecutor(self.loop_path, self.llm_provider)
    result = execute_data_ingress_loop(self.loop_path, executor, self.llm_provider)
    return result
else:
    # Execute normal markdown RAVL loop
    return execute_standard_markdown_loop(...)
```

### 2. LLM Provider Integration

DataIngressExecutor expects an llm_provider with this interface:

```python
class LLMProvider:
    def generate(self, prompt: str, max_tokens: int) -> str:
        """Generate text from LLM"""
        pass
```

Already supported:
- Anthropic Claude
- OpenAI GPT
- Google Gemini
- Ollama (local)

Usage:

```python
from llm.llm_providers import LLMProviderFactory

llm_provider = LLMProviderFactory.create_provider()
executor = DataIngressExecutor(loop_path, llm_provider)
```

### 3. Configuration File Integration

DataIngressExecutor reads standard RAVL config format:

```yaml
name: loop_name
api_endpoint: https://api.example.com
api_auth_method: Bearer
context7_docs_path: /websites/api_example_com/llms.txt
```

Extends standard with data-ingress fields:
- `api_endpoint`: API URL
- `api_auth_method`: Authentication type
- `context7_docs_path`: Path to API docs on Context7
- `context7_cache_ttl_hours`: Cache duration
- `max_retry_attempts`: Max retries on failure
- `execution_timeout`: Code execution timeout

## File Organization

After integration, structure looks like:

```
.ravl/
├── common/
│   ├── llm/
│   │   ├── data_ingress_executor.py        ← NEW: Core executor
│   │   ├── markdown_ravl_executor.py       ← MODIFY: Route data-ingress loops
│   │   ├── llm_providers.py                ← Use existing
│   │   └── ...
│   ├── ravl_base.py                        ← Use existing
│   ├── ravl_protocol.py                    ← Use existing
│   └── ...
├── docs/
│   ├── data-ingress.md                     ← NEW: User guide
│   ├── data-ingress-implementation.md      ← NEW: This file
│   ├── README.md                           ← Update to mention data-ingress
│   └── ...
├── templates/
│   ├── data-ingress-config.yml             ← NEW: Config template
│   ├── data-ingress-ravl_loop.md           ← NEW: Minimal loop template
│   ├── data-ingress-ravl_loop-full.md      ← NEW: Full loop template
│   └── ...
└── ...

ravl_loops/
├── hibob_api_ingestion/                    ← NEW: Example loop
│   ├── config/ravl.toml
│   ├── ravl_loop.md
│   ├── README.md
│   └── learnings/
└── ...
```

## Testing

### Unit Tests

Test DataIngressExecutor methods:

```python
# test_data_ingress_executor.py

def test_extract_act_section():
    executor = DataIngressExecutor(loop_path)
    act = executor.extract_act_section()
    assert 'required_fields' in act
    assert 'output_format' in act

def test_extract_verify_section():
    executor = DataIngressExecutor(loop_path)
    verify = executor.extract_verify_section()
    assert len(verify) > 0
    assert any('pass' in rule.lower() for rule in verify)

def test_execute_code():
    executor = DataIngressExecutor(loop_path)
    code = "def fetch_data():\n    return {'data': [1, 2, 3]}"
    result = executor.execute_code(code)
    assert result['success']
    assert result['data']['data'] == [1, 2, 3]

def test_code_timeout():
    executor = DataIngressExecutor(loop_path)
    code = "def fetch_data():\n    import time\n    time.sleep(120)"
    result = executor.execute_code(code, timeout=1)
    assert not result['success']
    assert 'timeout' in result['error'].lower()

def test_strategy_caching():
    executor = DataIngressExecutor(loop_path)
    strategy = executor.get_current_strategy()
    # First run: no strategy
    assert strategy is None

    # Save strategy
    test_strategy = {'code': 'def fetch_data(): pass', 'endpoint': '/test'}
    executor.save_strategy(test_strategy)

    # Second run: strategy exists
    strategy = executor.get_current_strategy()
    assert strategy is not None
    assert strategy['code'] == test_strategy['code']
```

### Integration Tests

Test full workflow:

```python
def test_first_run_workflow(mock_llm, mock_context7):
    """Test: first run generates code and saves strategy"""
    executor = DataIngressExecutor(loop_path, mock_llm)

    # Mock LLM to return working code
    mock_llm.generate.return_value = """
def fetch_data():
    return {'customers': [{'id': '1', 'name': 'Test'}]}
"""

    # Mock Context7 docs
    mock_context7.get.return_value = "API documentation..."

    result = executor.execute_full_workflow()

    assert result['success']
    assert result['code_generated']
    assert result['verified']

    # Verify strategy was cached
    strategy = executor.get_current_strategy()
    assert strategy is not None

def test_reuse_cached_strategy(mock_llm):
    """Test: second run reuses cached strategy without LLM call"""
    executor = DataIngressExecutor(loop_path, mock_llm)

    # First run (already cached from previous test)
    result1 = executor.execute_full_workflow()
    llm_calls_1 = mock_llm.generate.call_count

    # Second run
    result2 = executor.execute_full_workflow()
    llm_calls_2 = mock_llm.generate.call_count

    # No new LLM calls on second run
    assert llm_calls_2 == llm_calls_1
    assert result2['strategy_reused']

def test_failure_recovery(mock_llm, mock_context7):
    """Test: auto-healing retry after failure"""
    executor = DataIngressExecutor(loop_path, mock_llm)

    # First generation fails (401)
    first_code = "def fetch_data(): raise Exception('401 Unauthorized')"

    # Second generation succeeds (alternative auth)
    second_code = "def fetch_data(): return {'data': []}"

    mock_llm.generate.side_effect = [first_code, second_code]

    # Monkey-patch execute_code to fail first, succeed second
    call_count = 0
    original_execute = executor.execute_code

    def mock_execute(code, timeout=300):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {'success': False, 'error': '401 Unauthorized'}
        return original_execute(second_code, timeout)

    executor.execute_code = mock_execute

    result = executor.execute_full_workflow()

    # Should eventually succeed
    assert result['success']
```

### Manual Testing

Test with HiBob example:

```bash
# Set credentials
export HIBOB_SERVICE_USER_ID="test_id"
export HIBOB_API_TOKEN="test_token"

# First run
./.ravl/bin/ravl hibob_api_ingestion --mode fast

# Check generated code
cat ravl_loops/hibob_api_ingestion/learnings/current_strategy.json | jq '.code'

# Check results
cat ravl_loops/hibob_api_ingestion/learnings/action_result_*.json | jq '.'

# Second run (reuses cache)
./.ravl/bin/ravl hibob_api_ingestion --mode fast

# Verify no new code was generated
cat ravl_loops/hibob_api_ingestion/learnings/strategy_history/ | wc -l
```

## Extending the Pattern

### Custom Data Transformations

Users can define custom Python in REFLECT/LEARN sections:

```markdown
# Reflect

Special handling for this API:
```python
def transform_fields(raw_data):
    # Custom field mapping
    return {k.lower(): v for k, v in raw_data.items()}
```
```

### Custom Verification

Users can add complex VERIFY logic:

```markdown
# Verify

- Email format validation:
```python
import re
emails = [e['email'] for e in data['users']]
valid = all(re.match(r'^[^@]+@[^@]+$', e) for e in emails)
assert len([e for e in emails if valid]) > 0.9 * len(emails)
```

### Alternative Auth Methods

Support for multiple auth types:

```python
def apply_auth(headers, auth_method, credentials):
    if auth_method == 'Bearer':
        headers['Authorization'] = f'Bearer {credentials["token"]}'
    elif auth_method == 'ApiKey':
        headers[credentials.get('header', 'X-API-Key')] = credentials['key']
    elif auth_method == 'BasicAuth':
        import base64
        creds = f"{credentials['user']}:{credentials['pass']}"
        headers['Authorization'] = f'Basic {base64.b64encode(creds.encode()).decode()}'
    elif auth_method == 'OAuth2':
        # Implement OAuth2 token refresh
        pass
    return headers
```

## Performance Considerations

### Code Generation Cost

- First run: LLM API call (~2-5 seconds + API latency)
- Cached runs: No LLM call (~100ms + code execution time)
- Failure retry: LLM API call (~2-5 seconds)

### Caching Strategy

- Context7 docs: 168 hours (1 week) by default
- Current strategy: Forever until failure
- Failure history: Last 10 failures

### Optimization Tips

1. **Increase Context7 cache TTL** if API rarely changes:
   ```yaml
   context7_cache_ttl_hours: 720  # 30 days
   ```

2. **Reduce timeout for faster failures**:
   ```yaml
   execution_timeout: 30  # 30 seconds instead of 60
   ```

3. **Batch multiple runs** to amortize startup cost

## Security Considerations

### Code Execution

Generated code runs in subprocess with:
- Timeout protection (prevents infinite loops)
- Isolated environment (can't access parent process)
- No network access except through requests library
- No file system access except for reading cache

Never runs untrusted code directly in main process.

### Credentials

- Credentials passed via environment variables only
- Never stored in model.yml or ravl_loop.md
- Never logged or cached
- Generated code looks for standard variable names

### Data Privacy

- User data stays local (unless synced to external storage)
- No data sent to Anthropic, OpenAI, etc. (except LLM prompts)
- Strategy cache is local, not uploaded

## Troubleshooting Integration

### Import Errors

If `from llm.data_ingress_executor import DataIngressExecutor` fails:

```bash
# Ensure .ravl is in Python path
export PYTHONPATH="$PWD/.ravl/common:$PYTHONPATH"
```

### LLM Provider Not Initialized

If LLMProviderFactory returns None:

```bash
# Check environment variables
echo $ANTHROPIC_API_KEY
echo $OPENAI_API_KEY
echo $GOOGLE_API_KEY

# Or configure explicitly
cat > .ravl/common/llm/llm_config.yml <<EOF
provider: anthropic
model: claude-sonnet-4-5-20250929
EOF
```

### Context7 Fetch Failure

If "Context7 fetch failed":

```bash
# Check Context7 connectivity
curl https://context7.com/websites/apidocs_hibob_com/llms.txt

# Check network connectivity
ping context7.com

# Manually cache docs
curl https://context7.com/websites/your_api_com/llms.txt > \
  ravl_loops/your_loop/learnings/context7_docs_cache.txt
```

## Future Enhancements

1. **Parallel strategy generation**: Try multiple LLMs in parallel
2. **Strategy ranking**: Score strategies by speed/reliability
3. **Incremental learning**: Save performance metrics across runs
4. **User feedback loop**: Collect which generated code is best
5. **A/B testing**: Compare different strategies over time
6. **Auto-documentation**: Generate README from loop definition
7. **Schema inference**: Detect output format changes automatically
8. **Multi-step workflows**: Chain multiple data transformations
9. **Data diff**: Track what changed between runs
10. **Alert system**: Notify when data quality degrades

## References

- [Data Ingress User Guide](./data-ingress.md)
- [DataIngressExecutor Source](.../llm/data_ingress_executor.py)
- [HiBob Example](../../ravl_loops/hibob_api_ingestion/)
- [RAVL Framework Documentation](./README.md)
