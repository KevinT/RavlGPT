# Self-Healing Data Ingress Loop

This is a minimal data ingress loop template. Copy this to ravl_loops/your_api_name/ravl_loop.md

**Note**: You only need to fill in the ACT and VERIFY sections. REFLECT and LEARN are handled automatically by the framework.

## Credential Setup

This template supports multiple APIs (Notion, HiBob, Google, etc.). Before running:

1. **Get your API credentials**:
   - Notion: https://www.notion.com/my-integrations
   - HiBob: https://apidocs.hibob.com
   - Google: https://developers.google.com/workspace/guides/create-credentials

2. **Set environment variable** (local testing):
   ```bash
   export NOTION_API_KEY="your-key-here"  # or your API's credential name
   ./.ravl/bin/ravl your_loop_name --mode full
   ```

3. **Add to GitHub Actions** (for CI/CD):
   - Go to: Settings → Secrets and variables → Actions
   - Add: NOTION_API_KEY (or your credential name)
   - The loop will automatically detect and use it

**Framework Support**: The framework automatically:
- Detects which APIs your generated code uses
- Validates credentials before execution
- Provides clear error messages if credentials are missing
- Supports Notion, HiBob, Google APIs, and custom APIs


---
DELETE THIS + EVERYTHING ABOVE THIS LINE BEFORE RUNNING

# Act

**Describe what data you want to fetch from the API.**

## Required Data

List the data fields you need to fetch. Format: `- field_name (description)` or just `- field_name`

Example:
```
- first_name
- last_name
- email
- department
- manager_id
```

## Pagination (optional)

If the API supports pagination, describe it here. This helps the LLM generate proper pagination logic.

Example:
```
Pagination: limit/offset, max 100 items per page
Example: GET /employees?limit=100&offset=0
```

## Output Format

Specify the exact format you want the data returned in. This is critical for verification.

Example:
```json
{
  "employees": [
    {
      "first_name": "string",
      "last_name": "string",
      "email": "string",
      "department": "string",
      "manager_id": "string or null"
    }
  ]
}
```

---

# Verify

**Specify how to validate the returned data.**

List validation checks as bullet points. The framework will verify:
- Output matches the structure specified in ACT
- No completely empty fields (indicates parsing failure)
- Specified validation rules pass

Example:
```
- All required fields present in each object
- Email field contains @ symbol (basic validation)
- At least 50% of records have manager_id (acceptance threshold)
- No more than 10% missing values in any field

Pass if 90%+ of records pass all checks.
```

---

## Optional: Reflect (augments framework reflection)

**OPTIONAL**: Only add this section if you want to provide domain-specific reflection hints.

The framework automatically:
- Loads the last successful strategy from cache
- Fetches fresh API documentation from Context7
- Reviews failure history

If you want to augment this, add a REFLECT section:

```markdown
# Reflect

In addition to framework reflection, also consider:
- Has the API version changed? (check changelog)
- Are there rate limit concerns?
- Have field names been deprecated?
```

---

## Optional: Learn (augments framework learning)

**OPTIONAL**: Only add this section if you want to record domain-specific learnings.

The framework automatically:
- Saves successful code to cache
- Tracks strategy success rates
- Updates failure history

If you want to augment this, add a LEARN section:

```markdown
# Learn

In addition to framework learning, also capture:
- Which field transformations were required (normalization, parsing, etc.)
- How frequently pagination was needed
- API response time patterns
```

---

## Tips

- **Keep ACT concise**: Just list fields and format, framework handles API details
- **Be specific in VERIFY**: More specific checks help the framework learn what matters
- **Use real data structures**: JSON examples are better than descriptions
- **Run locally first**: `./.ravl/bin/ravl your_loop_name --mode fast`
- **Check generated code**: Look at learnings/current_strategy.json after first successful run
