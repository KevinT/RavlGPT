# Self-Healing Data Ingress - Quick Start (5 Minutes)

## In 5 Steps

### 1. Clone the template

```bash
./.ravl/bin/ravl-clone data-ingress my_api
```

This creates `ravl_loops/my_api/` with config and loop definition ready to edit.

### 2. Edit config (`ravl_loops/my_api/config/ravl.yml`)

```yaml
name: my_api_integration
api_endpoint: https://api.example.com/v1
api_auth_method: Bearer
context7_docs_path: /websites/api_example_com/llms.txt
```

### 3. Edit loop (`ravl_loops/my_api/ravl_loop.md`)

**Fill in ACT section:**
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

**Fill in VERIFY section:**
```markdown
# Verify

- All required fields present
- Email contains @ symbol
- customer_id is non-empty

Pass if 90%+ of records pass all checks.
```

### 4. Set credentials

```bash
export MY_API_TOKEN="your-token-here"
```

### 5. Run

```bash
./.ravl/bin/ravl my_api --mode fast
```

## That's It!

The framework will:
- ✅ Fetch API docs from Context7
- ✅ Generate working Python code using LLM
- ✅ Execute the code
- ✅ Validate the output
- ✅ Cache the working code

On next run, it will:
- ✅ Reuse cached code (no LLM, very fast)
- ✅ Execute immediately
- ✅ Return data

## Check Results

```bash
# See the generated code
cat ravl_loops/my_api/learnings/current_strategy.json | jq '.code'

# See the fetched data
cat ravl_loops/my_api/learnings/action_result_*.json | jq '.data'

# See success stats
cat ravl_loops/my_api/learnings/current_strategy.json | jq '{endpoint, auth_method, consecutive_successes, failure_count}'
```

## Optional: Add Custom Logic

Edit `ravl_loop.md` to add **optional** REFLECT or LEARN sections:

```markdown
# Reflect

In addition to framework reflection, also consider:
- Check for rate limit headers
- Verify API version compatibility

# Learn

In addition to framework learning, also capture:
- API response time trends
- Field completeness metrics
```

These sections **augment** the framework, they don't replace it.

## If It Fails

Framework automatically retries with alternatives:

1. First attempt fails (e.g., 401 error)
2. LLM sees the error
3. Generates different code (alternative auth, different endpoint)
4. Executes new code
5. If success: saves new strategy
6. If still fails: retries up to max_retry_attempts

No manual intervention needed!

## Real Example

```bash
# Try the HiBob example
export HIBOB_SERVICE_USER_ID="your_service_id"
export HIBOB_API_TOKEN="your_token"
./.ravl/bin/ravl hibob_api_ingestion --mode fast
```

See `ravl_loops/hibob_api_ingestion/` for a complete working example.

## Key Concepts

| Concept | Meaning |
|---------|---------|
| **ACT** | What data do you want? (fields + format) |
| **VERIFY** | How to validate the data? (quality checks) |
| **Framework REFLECT** | Loads strategy cache + API docs (automatic) |
| **LLM generates code** | Creates Python based on API docs (automatic) |
| **Framework LEARN** | Saves successful code to cache (automatic) |
| **Self-healing** | Auto-retries with alternatives on failure (automatic) |
| **Strategy cache** | Saved code reused until failure (learnings/current_strategy.json) |

## Common Mistakes to Avoid

❌ **Don't try to write code yourself**
- Framework generates it - just describe what you need

❌ **Don't hardcode credentials**
- Use environment variables (CUSTOMER_API_TOKEN, etc.)

❌ **Don't skip the output format**
- Be specific: show JSON structure with exact field names

❌ **Don't require 100% perfect data**
- Be realistic: "90%+ of records" not "100%"

## Need Help?

- **User Guide**: `GUIDE.md` (in this folder)
- **Full Example**: `ravl_loop-full.md` (in this folder)
- **HiBob Example**: `ravl_loops/hibob_api_ingestion/README.md`
- **Implementation Details**: `IMPLEMENTATION.md` (in this folder)

## Success Checklist

After first run, verify:

- [ ] No errors printed
- [ ] `learnings/current_strategy.json` exists
- [ ] `learnings/current_strategy.json` contains `code` field
- [ ] `learnings/action_result_*.json` shows returned data
- [ ] Second run is MUCH faster

If any of these are missing, check:
1. Credentials are set correctly
2. ACT section specifies required fields
3. VERIFY section has pass criteria
4. API endpoint and Context7 path are correct

## Next Steps

1. **Customize for your API**: Edit config and ravl_loop.md
2. **Set credentials**: Export environment variables
3. **Run it**: `./.ravl/bin/ravl your_loop --mode fast`
4. **Monitor**: Check learnings/ directory for results
5. **Deploy**: Add to GitHub Actions for periodic runs

---

**That's it! You now have a self-healing API integration that generates code, runs it, caches it, and heals itself when things break.**

Start here: Clone template → Edit 2 sections → Run it.
