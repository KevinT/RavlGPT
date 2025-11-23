# Self-Healing Data Ingress Loop - Full Example

This example shows a complete data ingress loop including optional Reflect and Learn sections.

---

# Reflect (optional - augments framework reflection)

Before fetching data, review:
- Previous strategy success/failure rates
- Any API documentation changes that might affect field names
- Rate limit status from last runs

The framework will automatically:
- Load last successful strategy if available
- Fetch fresh API documentation from Context7
- Check failure history

---

# Act

**Define what data to fetch and the desired output format.**

## Required Data

These are the fields we need from the API:

- customer_id: Unique identifier for the customer
- first_name: Customer's first name
- last_name: Customer's last name
- email: Email address
- company: Company name
- phone: Phone number
- address: Mailing address
- registration_date: Date customer was registered
- account_status: Active/Inactive/Suspended

## Pagination

The API supports pagination via limit/offset:
- Max 100 items per request
- Endpoint: GET /customers?limit=100&offset={offset}
- Increment offset by 100 for each page
- Stop when response contains fewer than 100 items

## Authentication

Uses Bearer token authentication:
- Header: Authorization: Bearer {token}
- Token provided via CUSTOMER_API_TOKEN environment variable

## Output Format

Return data in this exact format:

```json
{
  "customers": [
    {
      "customer_id": "string",
      "first_name": "string",
      "last_name": "string",
      "email": "string",
      "company": "string",
      "phone": "string",
      "address": "string",
      "registration_date": "ISO8601 date string",
      "account_status": "string"
    }
  ],
  "total_count": 12345,
  "fetch_timestamp": "ISO8601 timestamp",
  "records_fetched": 12345
}
```

---

# Verify

**Specify validation rules for the fetched data.**

Validation rules:
- Output contains "customers" array
- Each customer object has all 9 required fields
- customer_id is unique across all records
- email matches basic email pattern (contains @)
- registration_date is valid ISO8601 format
- account_status is one of: Active, Inactive, Suspended
- No more than 5% of records have missing non-required fields
- total_count matches length of customers array

Pass criteria:
- 100% of records have all required fields
- 99%+ of records pass all validation checks
- total_count is accurate

---

# Reflect (augments framework)

When reflection happens, the framework will:
1. Load current_strategy.json if it exists (last working code)
2. Fetch API docs from Context7 (with caching)
3. Check failure history and retry counter

Additionally, consider:
- **Rate limits**: Log any rate limit headers from API responses
- **Field deprecations**: Check API changelog for removed/renamed fields
- **Performance**: Track which API endpoints are fastest
- **Data quality**: Note if certain fields are frequently missing
- **Alternative endpoints**: Some APIs have multiple endpoints for same data

---

# Learn (augments framework)

When learning happens, the framework will:
1. Save successful code to current_strategy.json
2. Update strategy success counter
3. Record failure reasons and retry history

Additionally, capture:
- **Field transformations**: Which fields needed normalization/parsing?
  - Email lowercasing?
  - Date format conversions?
  - Phone number standardization?
- **Pagination efficiency**: How many API calls were needed?
- **Performance metrics**: Response time per request?
- **Data coverage**: What % of requested fields were actually present?
- **Retry effectiveness**: Did LLM-generated alternatives solve issues?

These insights help the loop improve over time and make better decisions on future runs.

---

## Real-World Example: HiBob API

Here's what this looks like for the HiBob HR API:

### Config (config/ravl.toml)
```yaml
name: hibob_integration
description: Fetch employee data from HiBob
api_endpoint: https://api.hibob.com/v1
api_auth_method: Bearer
context7_docs_path: /websites/apidocs_hibob_com/llms.txt
```

### Act Section
```
## Required Data
- id: Employee ID in HiBob
- email: Work email
- work.title: Job title
- work.department: Department name
- work.manager: Manager's employee ID
- work.startDate: Start date
```

### Verify Section
```
- All employees have id and email
- work.title and work.department present (or marked as null)
- 90%+ of employees have work.manager assigned
- startDate is valid ISO date or null

Pass if 95%+ of records have complete required fields.
```

---

## How Self-Healing Works

### First Run
1. Framework detects no cached strategy
2. LLM sees: required fields + output format + API docs → generates Python code
3. Code executes and fetches data
4. Verification checks output
5. If success: code saved to cache
6. If failure: error recorded for next iteration

### Subsequent Runs (Success Path)
1. Load cached code from current_strategy.json
2. Execute same code (no LLM call needed)
3. Verify output
4. Increment success counter

### After Failure
1. Load cached code that failed
2. Check failure history
3. LLM sees error + API docs + previous attempt
4. LLM generates DIFFERENT code (tries alternative endpoint or auth)
5. Execute new code
6. If success: save new code and reset failure counter
7. If fail again: repeat up to max_retry_attempts

### When API Changes
1. Context7 cache expires (weekly by default)
2. Framework fetches fresh API docs
3. If docs are different: LLM re-analyzes
4. Generates updated code if needed
5. System auto-adapts without manual intervention

---

## Tips for Best Results

1. **Be specific about fields**
   - ✅ Good: `- work.department: Department name from work object`
   - ❌ Avoid: `- department info`

2. **Show exact output format**
   - Include JSON examples with all fields
   - Show nested structure clearly
   - Use exact field names

3. **Realistic validation**
   - Don't require 100% if data isn't that clean
   - Focus on critical fields (IDs, emails)
   - Allow nulls for optional fields

4. **Monitor first run**
   - Check learnings/current_strategy.json after first success
   - Review generated code to ensure it matches your needs
   - If code looks wrong, adjust ACT/VERIFY and retry

5. **Use environment variables**
   - Never hardcode credentials
   - Generated code will look for standard env var names
   - Example: HIBOB_API_TOKEN, CUSTOMER_API_KEY, etc.

---

## Files & Structure

```
ravl_loops/my_api_ingestion/
├── config/
│   └── ravl.toml                      # Config (endpoint, auth, Context7 path)
├── ravl_loop.md                      # This file (ACT, VERIFY, optional REFLECT/LEARN)
└── learnings/
    ├── model.yml                     # Framework-managed learning model
    ├── current_strategy.json         # Currently cached/working code
    ├── context7_docs_cache.txt       # Cached API documentation
    ├── failure_history.json          # Failures for learning/retry
    └── strategy_history/             # Timestamped copies of all strategies
        ├── 2025-10-16T12-00-00.json
        └── 2025-10-16T14-30-00.json
```
