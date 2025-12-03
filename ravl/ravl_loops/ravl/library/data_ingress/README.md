# Data-Ingress RAVL Loop Template

Self-healing data ingestion loop template for automatically generating, testing, and fixing API integration code.

## Quick Start

### Clone this template to create a new loop:

```bash
# Clone to create my_api loop
./ravl --clone ravl.library.data_ingress my_api

# Clone and rename in one step
./ravl --clone ravl.library.data_ingress my_hibob_employees
```

This creates a new loop directory with:
- `config/ravl.toml` - Configuration template (edit this!)
- `ravl_loop.md` - Loop definition (edit this!)
- `ravl_loop-full.md` - Complete example with optional REFLECT/LEARN
- `QUICKSTART.md`, `GUIDE.md`, `IMPLEMENTATION.md` - Documentation
- `README.md` - Loop-specific readme

### Setup your loop:

1. **Edit config** (`config/ravl.toml`):
   ```yaml
   name: my_api_integration
   api_endpoint: https://api.example.com/v1
   api_auth_method: Bearer
   context7_docs_path: /websites/api_example_com/llms.txt
   ```

2. **Edit loop definition** (`ravl_loop.md`):

   Fill **ACT** section (what data to fetch):
   ```markdown
   # Act

   ## Required Data
   - field1
   - field2
   - field3

   ## Output Format
   {
     "data": [{
       "field1": "type",
       "field2": "type",
       "field3": "type"
     }]
   }
   ```

   Fill **VERIFY** section (how to validate):
   ```markdown
   # Verify

   - All required fields present
   - field1 is non-empty
   - field2 matches expected format

   Pass if 90%+ of records pass all checks.
   ```

3. **Set credentials**:
   ```bash
   export MY_API_TOKEN="your-token-here"
   ```

4. **Run the loop**:
   ```bash
   cd /path/to/repo
   ./ravl my_api --mode fast
   ```

## What Happens

### First Run
1. Framework loads your ACT and VERIFY sections
2. Fetches API documentation from Context7
3. LLM generates Python code to fetch the required data
4. Executes the generated code
5. Validates output against your VERIFY rules
6. Saves the working code to `learnings/current_strategy.json`

### Subsequent Runs
1. Loads cached code (no LLM call!)
2. Executes code immediately
3. Validates output
4. Much faster than first run

### On Failure
1. Framework detects the failure
2. LLM re-analyzes the API documentation
3. Generates alternative code (tries different endpoints, auth methods, etc.)
4. Automatically retries
5. Continues until success or max retries

## Template Files

- **`ravl_loop.md`** - Minimal template with just ACT + VERIFY sections
- **`ravl_loop-full.md`** - Complete example showing optional REFLECT and LEARN sections
- **`config/ravl.toml`** - Configuration template with all available options

## Understanding the Sections

### ACT (User specifies)
Describe **what data** you want to fetch:
- List of required data fields
- Example output format (JSON)
- Pagination info if applicable
- Authentication details if special

### VERIFY (User specifies)
Describe **how to validate** the returned data:
- Quality checks (fields present, format valid, etc.)
- Pass criteria (e.g., "90%+ of records pass all checks")

### REFLECT (User specifies - optional)
**Augments** (doesn't replace) framework reflection:
- Domain-specific reflection hints
- Custom analysis of the API

### LEARN (User specifies - optional)
**Augments** (doesn't replace) framework learning:
- Custom metrics to track
- Domain-specific insights

## Configuration Options

### Required

```yaml
name: loop_name
api_endpoint: https://api.example.com/v1
api_auth_method: Bearer
context7_docs_path: /websites/api_example_com/llms.txt
```

### Optional

```yaml
context7_cache_ttl_hours: 168              # Cache API docs for 1 week
max_retry_attempts: 3                      # Max failures before giving up
regenerate_on_failure_count: 2             # Failures before trying new code
execution_timeout: 300                      # Code timeout in seconds
strategy_cache_file: learnings/current_strategy.json
```

## Debugging

After cloning and running, check results:

```bash
# See generated code
cat ravl_loops/my_api/learnings/current_strategy.json | jq '.code'

# See fetched data
cat ravl_loops/my_api/learnings/action_result_*.json | jq '.data'

# See stats
cat ravl_loops/my_api/learnings/current_strategy.json | jq '{endpoint, consecutive_successes, failure_count}'

# See failure history
cat ravl_loops/my_api/learnings/failure_history.json
```

## Learn More

- **[GUIDE.md](GUIDE.md)** - Comprehensive user guide for this template
- **[QUICKSTART.md](QUICKSTART.md)** - Quick start guide for this template
- **[IMPLEMENTATION.md](IMPLEMENTATION.md)** - Implementation details

## Key Points

✅ Only need to fill in ACT + VERIFY sections
✅ Framework handles code generation automatically
✅ Successful code is cached for speed
✅ Automatically heals failures by trying alternatives
✅ Adapts when APIs change

## Common Mistakes

❌ Don't try to write code yourself - framework generates it
❌ Don't hardcode credentials - use environment variables
❌ Don't require 100% perfect data - be realistic with validation
❌ Don't skip the output format - be specific with JSON structure

## Support

Check the template documentation for:
- **GUIDE.md** - Complete user guide, troubleshooting, FAQ, and best practices
- **QUICKSTART.md** - Fast setup instructions
- **IMPLEMENTATION.md** - Technical implementation details
