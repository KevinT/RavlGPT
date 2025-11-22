# Self-Healing Data Ingress RAVL Loops

## Overview

Self-healing data ingress loops use LLMs and Context7 API documentation to automatically generate, test, and fix API integration code. Once successful, the code is cached and reused until the API changes or an error occurs.

**Key benefit**: Describe *what* data you want, not *how* to get it. The framework handles everything else.

## Quick Start

### 1. Clone the Template

```bash
./ravl --clone data_ingress_template my_api_integration
```

This creates:
- `ravl_loops/my_api_integration/` directory
- `config/ravl.yml` configuration template
- `ravl_loop.md` loop definition template
- Documentation files

### 2. Customize Config

Edit `ravl_loops/my_api_integration/config/ravl.yml`:
```yaml
name: my_api_integration
api_endpoint: https://api.example.com/v1
api_auth_method: Bearer
context7_docs_path: /websites/api_example_com/llms.txt
```

### 3. Customize Loop Definition

Edit `ravl_loops/my_api_integration/ravl_loop.md`:

Edit `ravl_loop.md` - fill in only:

**ACT section**: What data do you need?
```markdown
# Act

## Required Data
- customer_id
- email
- name
- company

## Output Format
{
  "customers": [{
    "customer_id": "string",
    "email": "string",
    "name": "string",
    "company": "string"
  }]
}
```

**VERIFY section**: How to validate it?
```markdown
# Verify

- All required fields present
- Email contains @ symbol
- customer_id is non-empty

Pass if 90%+ of records pass all checks.
```

### 4. Set Credentials

```bash
export MY_API_TOKEN="your-token-here"
```

### 5. Run It

```bash
./.ravl/bin/ravl my_api_integration --mode fast
```

That's it! The framework will:
1. Fetch API docs from Context7
2. Have the LLM generate Python code based on your requirements
3. Execute the code
4. Validate the output
5. Cache the successful strategy

## How It Works

### First Run

```
┌─────────────────┐
│   User's Loop   │
│  (ACT + VERIFY) │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Framework REFLECT (automatic)       │
│  - Check for cached strategy         │
│  - Fetch Context7 API docs          │
│  - Review failure history           │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  LLM Generates Code                 │
│  - Sees: required fields            │
│  - Sees: API documentation          │
│  - Generates: working Python code   │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Execute Code                       │
│  - Run generated Python             │
│  - Capture output or error          │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  User's VERIFY (from ravl_loop.md)  │
│  - Check output format              │
│  - Validate data quality            │
│  - Pass or fail                     │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Framework LEARN (automatic)        │
│  - If success: cache code           │
│  - If fail: record error for retry  │
└─────────────────────────────────────┘
```

### Second Run (Success Path)

If the first run succeeded:

```
Framework REFLECT
  ↓
  └─→ Load cached code from current_strategy.json
      (No LLM call needed!)
         ↓
      Execute cached code
         ↓
      User's VERIFY
         ↓
      Framework LEARN
         └─→ Increment success counter
```

Much faster - no LLM calls, just execution.

### After Failure

If code fails (e.g., 401 Unauthorized):

```
Framework REFLECT
  ↓
  └─→ Load failure history
      See: "Last attempt got 401"
         ↓
      LLM sees failure + API docs
      Tries alternative strategy
      Generates DIFFERENT code
         ↓
      Execute new code
         ↓
      User's VERIFY
         ├─→ If success: save new strategy
         └─→ If fail: retry up to max_retries
```

The LLM learns from failures and tries alternatives.

### API Change (Cache Expiration)

By default, API docs are cached for 168 hours (1 week). When cache expires:

```
Framework REFLECT
  ↓
  └─→ Context7 cache is stale
      Fetch fresh API docs
      Docs might have changed
         ↓
      LLM re-analyzes new docs
      Might generate different code
         ↓
      Execute new code
         ↓
      User's VERIFY
         ├─→ If success: save updated strategy
         └─→ If fail: debug or adjust requirements
```

System auto-adapts when APIs change, without manual intervention.

## File Structure

```
ravl_loops/my_api_integration/
├── config/
│   └── ravl.yml                           # Configuration (API endpoint, auth, Context7 path)
├── ravl_loop.md                           # Loop definition (only ACT + VERIFY required)
└── learnings/
    ├── model.yml                          # Framework model (learning, strategy tracking)
    ├── current_strategy.json              # Currently cached working code
    ├── context7_docs_cache.txt            # Cached API documentation (1 week TTL)
    ├── failure_history.json               # Previous failures (for learning/retry)
    ├── action_result_*.json               # Latest execution results
    └── strategy_history/
        ├── 2025-10-16T12-00-00.json       # Timestamped copies of each strategy
        └── 2025-10-16T14-30-00.json
```

## Configuration Options

### config/ravl.yml

```yaml
# Required
name: loop_identifier
api_endpoint: https://api.example.com/v1
api_auth_method: Bearer  # or: ApiKey, BasicAuth, OAuth2
context7_docs_path: /websites/api_example_com/llms.txt

# Optional
context7_cache_ttl_hours: 168          # How long to cache API docs (default: 1 week)
max_retry_attempts: 3                  # Max failures before giving up (default: 3)
regenerate_on_failure_count: 2         # Failures before trying new code (default: 2)
execution_timeout: 300                  # Code execution timeout in seconds (default: 60)
strategy_cache_file: learnings/current_strategy.json  # Where to store working code
```

## Markdown Loop Definition

Only two sections required:

### ACT Section

Describe **what data** you want to fetch:

```markdown
# Act

## Required Data
- field1: Description
- field2: Description

## Output Format
```json
{
  "key": [
    { "field1": "type", "field2": "type" }
  ]
}
```

## Pagination (optional)
If the API supports pagination, describe it...

## Authentication (optional)
If there are auth details beyond config...
```

### VERIFY Section

Describe **how to validate** the returned data:

```markdown
# Verify

- Check 1
- Check 2
- Check 3

Pass if <criteria>
```

### Optional: REFLECT Section

Augment framework reflection with domain-specific logic:

```markdown
# Reflect

In addition to framework reflection, also consider:
- Custom logic specific to your API
- Domain-specific validation
```

### Optional: LEARN Section

Augment framework learning with domain-specific insights:

```markdown
# Learn

In addition to framework learning, also capture:
- Custom metrics
- Domain-specific patterns
```

## LLM Code Generation

The LLM generates Python code based on:

1. **Required fields** from ACT section
2. **Output format** from ACT section
3. **API documentation** from Context7
4. **Failure history** (if retrying)

Generated code includes:

- Proper API authentication
- Error handling and logging
- Pagination logic (if needed)
- Data transformation to match output format
- Timeout handling

Example generated code:

```python
def fetch_data():
    import requests
    import os

    token = os.getenv('MY_API_TOKEN')
    if not token:
        raise Exception("MY_API_TOKEN not set")

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    all_customers = []
    offset = 0

    while True:
        response = requests.get(
            'https://api.example.com/v1/customers',
            params={'limit': 100, 'offset': offset},
            headers=headers,
            timeout=30
        )

        if response.status_code != 200:
            raise Exception(f"API error: {response.status_code}")

        data = response.json()
        customers = data.get('results', [])

        if not customers:
            break

        all_customers.extend(customers)
        offset += len(customers)

    return {'customers': all_customers}
```

## Strategy Caching

Once code succeeds, it's cached in `learnings/current_strategy.json`:

```json
{
  "code": "import requests\ndef fetch_data():\n  ...",
  "code_hash": "abc123def456",
  "endpoint": "/api/customers",
  "auth_method": "Bearer",
  "first_generated": "2025-10-16T12:00:00Z",
  "last_used": "2025-10-16T14:30:00Z",
  "consecutive_successes": 5,
  "failure_count": 0
}
```

**Benefits**:
- No LLM calls on subsequent runs (faster, cheaper)
- Same code reused until failure
- Full history in strategy_history/ for debugging
- Automatic fallback if code fails

## Self-Healing Behavior

### Retry Logic

When code fails:

1. **First failure**: Record error, increment failure_count
2. **Second failure**: Increment failure_count, trigger code regeneration
3. **Third+ failures**: LLM keeps trying alternatives, incrementing attempt counter
4. **Max retries**: Stop, report detailed diagnostics

### Failure Detection

Failures are detected when:

- Code throws exception
- Code times out
- Output parsing fails
- VERIFY checks fail
- HTTP status codes indicate errors

### Recovery Strategies

LLM tries alternatives:

- Different API endpoints
- Different authentication methods
- Different pagination approaches
- Different field transformations
- Alternative request formats

Each attempt is recorded in `failure_history.json` for learning.

## Monitoring & Debugging

### Check Current Status

```bash
cat ravl_loops/my_api_integration/learnings/current_strategy.json
```

Shows: endpoint, auth method, success count, failure count.

### View Generated Code

The `code` field in current_strategy.json contains the working Python.

### Check Execution Results

```bash
cat ravl_loops/my_api_integration/learnings/action_result_*.json
```

Latest execution result with output/error/timing.

### Review Failure History

```bash
cat ravl_loops/my_api_integration/learnings/failure_history.json
```

Last 10 failures with error messages and timestamps.

### View Strategy History

```bash
ls -la ravl_loops/my_api_integration/learnings/strategy_history/
```

Timestamped copies of every strategy ever saved.

## Running Loops

### Interactive Development

```bash
# Fast mode (less thorough, good for testing)
./.ravl/bin/ravl my_api_integration --mode fast

# Full mode (complete analysis, verify, learn phases)
./.ravl/bin/ravl my_api_integration --mode full
```

### Scheduled Runs

Add to GitHub Actions workflow:

```yaml
- name: Run API ingestion
  run: |
    export MY_API_TOKEN=${{ secrets.MY_API_TOKEN }}
    ./.ravl/bin/ravl my_api_integration --mode full
```

### Environment Variables

Pass credentials via environment:

```bash
export MY_API_TOKEN="token123"
export MY_API_KEY="key456"
./.ravl/bin/ravl my_api_integration --mode fast
```

The generated code will automatically use these.

## Best Practices

### 1. Be Specific About Fields

❌ Bad:
```
## Required Data
- customer info
- contact details
```

✅ Good:
```
## Required Data
- customer_id: Unique identifier
- email: Work email address
- department: Department name
```

### 2. Show Real Output Format

❌ Bad:
```
## Output Format
{ "customers": [...] }
```

✅ Good:
```
## Output Format
{
  "customers": [
    {
      "id": "string",
      "email": "string",
      "name": "string",
      "department": "string"
    }
  ]
}
```

### 3. Realistic Validation

❌ Bad:
```
- All fields 100% present
- No nulls allowed
```

✅ Good:
```
- All required fields present
- 90%+ of records have department
- Email never null
- department can be null for contractors
```

### 4. Monitor First Run

After first successful run, inspect the generated code:
- Does it match your expectations?
- Is pagination logic correct?
- Are field mappings right?

If something's wrong, adjust ACT/VERIFY and run again.

### 5. Use Descriptive Loop Names

```
✅ ravl_loops/hibob_employee_sync/
✅ ravl_loops/stripe_transactions_fetch/
✅ ravl_loops/salesforce_accounts_ingestion/

❌ ravl_loops/api_fetch/
❌ ravl_loops/data_get/
```

## Troubleshooting

### "Module not found" Error

Install Python dependencies:
```bash
pip3 install -r .ravl/requirements.txt
```

### "Prompt too long" Error

LLM token limit hit. Try:
1. Reduce number of required fields
2. Simplify output format description
3. Run with `--mode fast` to skip some analysis

### API Returns 401 Unauthorized

LLM will try alternative auth methods automatically.

If it keeps failing after max_retries:
1. Check credentials are correct
2. Verify Context7 has latest API docs
3. Check if API requires additional headers
4. Manually inspect generated code in current_strategy.json

### Code Execution Timeout

If code takes >60 seconds:
1. Increase `execution_timeout` in config
2. API might be slow - check their status
3. Pagination might be fetching too much - adjust
4. Reduce `limit` parameter in pagination

### "Output verification failed"

Your VERIFY checks are too strict. Either:
1. Adjust VERIFY criteria to be more realistic
2. Check if API is actually returning expected fields
3. Review generated code for field mapping issues

### LLM Generates Wrong Endpoint

The generated code might use wrong endpoint because:
1. Context7 docs are outdated (manually refresh by deleting cache)
2. Your required fields don't match API response structure
3. API has multiple endpoints, LLM picked wrong one

Solution:
1. Delete `learnings/context7_docs_cache.txt`
2. Adjust required fields to match actual API
3. Run again - LLM will re-analyze and pick correct endpoint

## Examples

See `.ravl/templates/data-ingress-ravl_loop-full.md` for a complete example.

Real-world examples:
- `ravl_loops/hibob_api_ingestion/` - HR data from HiBob
- `ravl_loops/stripe_transactions/` - Payment data from Stripe (example)

## FAQ

**Q: Does the generated code run in production?**
A: Yes, it's tested and cached. But review generated code first to verify it's safe.

**Q: What if the API changes?**
A: Context7 cache expires weekly. Framework re-fetches docs and may regenerate code. System auto-adapts.

**Q: Can I use this without Context7?**
A: No - Context7 provides structured API docs that LLM needs. You must configure a `context7_docs_path`.

**Q: Is the code private?**
A: Yes. Code is stored locally in `learnings/current_strategy.json`, not sent anywhere after LLM generation.

**Q: Can I see what LLM generated?**
A: Yes. Open `learnings/current_strategy.json` and check the `code` field.

**Q: What if no Context7 docs exist for my API?**
A: Create them! See [Context7 Documentation](https://context7.com) on how to contribute.

**Q: How often should I run this?**
A: Depends on your needs. Daily, weekly, or triggered by events. GitHub Actions can automate it.

**Q: Can I customize the generated code?**
A: Directly modifying code isn't recommended. Instead, adjust your ACT/VERIFY sections and re-run.

## References

- [Context7](https://context7.com) - API documentation source
- [RAVL Framework](./README.md) - Core RAVL pattern documentation
- [Examples](.

/examples/) - Ready-to-run examples
