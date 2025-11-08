#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
Schema-Adaptive Code Templates

Provides LLM-friendly templates for working with APIs/databases without hardcoded schema.
The generated code inspects the actual schema first, then adapts to it.

This solves the "empty_result_set" problem: code runs but gets 0 items because it's
looking for hardcoded property names that don't exist in the actual database.

Strategy:
1. Query API/database to discover actual schema/properties
2. Dynamically map discovered properties to expected fields
3. Extract data using discovered property names
4. Fall back gracefully if properties don't exist
"""


NOTION_ADAPTIVE_TEMPLATE = '''
"""
Notion API Data Extraction with Schema Adaptation

This code:
1. Queries the Notion database schema
2. Discovers actual property names and types
3. Adapts extraction logic to actual schema
4. Falls back gracefully for missing properties
"""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
import requests

# Configuration
NOTION_API_KEY = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN") or os.environ.get("NOTION_API_TOKEN")
DATABASE_ID = "{database_id}"
NOTION_VERSION = "2022-06-28"

if not NOTION_API_KEY:
    raise ValueError("Notion API key not found in environment")

headers = {{
    "Authorization": f"Bearer {{NOTION_API_KEY}}",
    "Content-Type": "application/json",
    "Notion-Version": "{{NOTION_VERSION}}"
}}

# Step 1: Query database to get schema and data
try:
    query_url = f"https://api.notion.com/v1/databases/{{DATABASE_ID}}/query"
    response = requests.post(query_url, headers=headers, json={{}})
    response.raise_for_status()
    data = response.json()
except requests.exceptions.RequestException as e:
    print(f"ERROR: Failed to query Notion database: {{e}}")
    exit(1)

# Step 2: Analyze schema from first page
schema = {{}
if data.get("results"):
    first_page = data["results"][0]
    schema = first_page.get("properties", {{}})
    print(f"DEBUG: Discovered {{len(schema)}} properties in Notion database")
    print(f"DEBUG: Property names: {{list(schema.keys())}}")
else:
    print("WARNING: Database returned no results")

# Step 3: Map discovered properties to expected fields
property_types = {{}}
property_mapping = {{}}

for prop_name, prop_data in schema.items():
    prop_type = prop_data.get("type", "unknown")
    property_types[prop_name] = prop_type
    print(f"DEBUG: Property '{{prop_name}}' is type '{{prop_type}}'")

# Step 4: Extract data using discovered schema
activities = []
for page in data.get("results", []):
    properties = page.get("properties", {{}})

    item = {{
        "id": page.get("id"),
        "name": "",
        "activity": "",
        "responsible": [],
        "accountable": [],
        "consulted": [],
        "informed": []
    }}

    # Try to find name/title field (could be "Name", "Title", "Activity", etc.)
    for title_field in ["Name", "Title", "Activity Name", "Project", "Title", "Name"]:
        if title_field in properties:
            prop_value = properties[title_field]
            prop_type = prop_value.get("type")

            if prop_type == "title":
                title_list = prop_value.get("title", [])
                if title_list:
                    item["name"] = title_list[0].get("plain_text", "")
                    item["activity"] = item["name"]
                break
            elif prop_type in ["rich_text", "text"]:
                text_content = prop_value.get("rich_text", []) or prop_value.get("text", [])
                if text_content:
                    item["name"] = text_content[0].get("plain_text", "")
                    item["activity"] = item["name"]
                break

    # Try to extract RACI assignments
    # Look for properties that match RACI keywords
    for prop_name, prop_data in properties.items():
        prop_type = prop_data.get("type")
        prop_lower = prop_name.lower()

        # Handle people-type fields
        if prop_type == "people":
            people_list = prop_data.get("people", [])
            people_names = [p.get("name") for p in people_list]

            if "responsible" in prop_lower:
                item["responsible"] = people_names
            elif "accountable" in prop_lower:
                item["accountable"] = people_names
            elif "consulted" in prop_lower:
                item["consulted"] = people_names
            elif "informed" in prop_lower:
                item["informed"] = people_names

        # Handle multi_select fields (fallback for RACI)
        elif prop_type == "multi_select":
            options = [opt.get("name") for opt in prop_data.get("multi_select", [])]

            if "responsible" in prop_lower:
                item["responsible"] = options
            elif "accountable" in prop_lower:
                item["accountable"] = options
            elif "consulted" in prop_lower:
                item["consulted"] = options
            elif "informed" in prop_lower:
                item["informed"] = options

    activities.append(item)

print(f"DEBUG: Extracted {{len(activities)}} activities from Notion")

# Step 5: Create output with metadata
output_data = {{
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "record_count": len(activities),
    "data_changed": True,
    "activities": activities,
    "extraction_notes": f"Extracted {{len(activities)}} from {{len(schema)}} properties"
}}

# Step 6: Implement change detection
current_hash = hashlib.sha256(
    json.dumps(activities, sort_keys=True).encode()
).hexdigest()

data_dir = Path("_data")
data_dir.mkdir(exist_ok=True)

data_changed = True
existing_files = sorted(data_dir.glob("alpha_project_raci_*.json"))

if existing_files:
    with open(existing_files[-1], "r") as f:
        previous_data = json.load(f)
        previous_activities = previous_data.get("activities", [])
        previous_hash = hashlib.sha256(
            json.dumps(previous_activities, sort_keys=True).encode()
        ).hexdigest()
        data_changed = (current_hash != previous_hash)

# Step 7: Save to file only if changed
if data_changed:
    output_data["data_changed"] = True
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = data_dir / f"alpha_project_raci_{{timestamp_str}}.json"

    with open(filename, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"Data saved to {{filename}}")
else:
    print("No changes detected. File not created.")

# Step 8: Output JSON to stdout for verification
print(json.dumps(output_data, indent=2))
'''


NOTION_LINK_FOLLOWING_EXAMPLE = '''
"""
Notion Page Link Following Example

Demonstrates how to extract and follow page mentions (links) in Notion blocks.
Uses NotionLinkExtractor helper to parse rich_text arrays for page IDs.
"""

import os
import json
import requests
from ravl.common.integrations.notion_helpers import NotionLinkExtractor

# Configuration
NOTION_API_KEY = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN")
PAGE_ID = "{page_id}"  # Replace with your page ID
NOTION_VERSION = "2022-06-28"

if not NOTION_API_KEY:
    raise ValueError("Notion API key not found in environment")

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION
}


def fetch_page_content(page_id: str, visited_pages: set = None) -> dict:
    """
    Fetch page content and recursively follow linked pages.

    Args:
        page_id: Notion page ID to fetch
        visited_pages: Set of already visited page IDs (prevents infinite loops)

    Returns:
        Dict with page content and linked page content
    """
    if visited_pages is None:
        visited_pages = set()

    # Prevent infinite loops
    if page_id in visited_pages:
        return {"page_id": page_id, "content": "[Already visited]", "linked_pages": []}

    visited_pages.add(page_id)

    # Fetch page blocks
    blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    response = requests.get(blocks_url, headers=headers)
    response.raise_for_status()
    blocks_data = response.json()

    blocks = blocks_data.get("results", [])

    # Extract main content (simplified markdown conversion)
    main_content = []
    for block in blocks:
        block_type = block.get("type")
        if block_type == "paragraph":
            rich_text = block.get("paragraph", {}).get("rich_text", [])
            text = " ".join([t.get("plain_text", "") for t in rich_text])
            main_content.append(text)
        elif block_type in ["heading_1", "heading_2", "heading_3"]:
            rich_text = block.get(block_type, {}).get("rich_text", [])
            text = " ".join([t.get("plain_text", "") for t in rich_text])
            main_content.append(f"# {text}")

    # Extract all page mentions using helper
    linked_page_ids = NotionLinkExtractor.extract_all_page_mentions_from_blocks(blocks)

    # Deduplicate linked pages
    unique_linked_pages = list(set(linked_page_ids))

    # Recursively fetch linked pages
    linked_page_contents = []
    for linked_id in unique_linked_pages:
        try:
            linked_content = fetch_page_content(linked_id, visited_pages)
            linked_page_contents.append(linked_content)
        except Exception as e:
            print(f"Warning: Could not fetch linked page {linked_id}: {e}")
            linked_page_contents.append({
                "page_id": linked_id,
                "content": f"[Error: {str(e)}]",
                "linked_pages": []
            })

    return {
        "page_id": page_id,
        "content": "\\n".join(main_content),
        "linked_pages": linked_page_contents
    }


# Fetch main page and all linked pages
try:
    full_content = fetch_page_content(PAGE_ID)
    print(json.dumps(full_content, indent=2))
except Exception as e:
    print(f"ERROR: Failed to fetch page content: {e}")
    exit(1)
'''


def get_notion_adaptive_template(database_id: str) -> str:
    """
    Get schema-adaptive template for Notion with specific database ID.

    Args:
        database_id: The Notion database ID

    Returns:
        Python code string ready for LLM to use/modify
    """
    return NOTION_ADAPTIVE_TEMPLATE.format(database_id=database_id)


SCHEMA_INSPECTION_PROMPT = '''
When generating code for extracting data from APIs or databases:

1. **ALWAYS inspect the schema first**
   - Query the API to discover actual property names and types
   - Log discovered properties to stderr for debugging (NOT stdout)
   - Don't assume property names exist

2. **Dynamically map properties**
   - Look for properties that match keywords (e.g., "Name", "Title" for names)
   - Check property types (people, multi_select, rich_text, etc.)
   - Adapt extraction based on what you find

3. **Handle missing properties gracefully**
   - Use defensive fallbacks for property names
   - Don't crash if a property isn't found
   - Leave field empty if property doesn't exist

4. **Output ONLY JSON to stdout (no debug output)**
   - Save data to file (if persistence required)
   - Print ONLY valid JSON to stdout (NO debug messages)
   - stdout must be pure JSON for verification
   - Use stderr for debug output instead

5. **Debug output goes to stderr, NOT stdout**
   - Print "DEBUG: " messages to sys.stderr only
   - Print "ERROR: " messages to sys.stderr only
   - This helps diagnose issues WITHOUT breaking JSON verification
   - Verification expects clean JSON on stdout

Example pattern:
```python
import sys
import json

# Debug output to stderr (visible in logs but doesn't break stdout JSON)
print("DEBUG: Discovering properties...", file=sys.stderr)
for prop_name, prop_data in properties.items():
    print(f"DEBUG: Found '{{prop_name}}' of type '{{prop_data.get('type')}}'", file=sys.stderr)

# ONLY JSON to stdout
print(json.dumps(output_data, indent=2))  # NO print(..., file=sys.stderr)
```

This approach handles schema variations automatically while keeping stdout clean for verification.
'''


def enhance_llm_guidance_with_schema_adaptation(base_guidance: str) -> str:
    """
    Enhance LLM guidance with schema-adaptive code generation instructions.
    Also adds link following examples when appropriate.

    Args:
        base_guidance: The base DSL guidance

    Returns:
        Enhanced guidance with schema adaptation and optional link following examples
    """
    enhanced = base_guidance + "\n\n" + SCHEMA_INSPECTION_PROMPT

    # Add link following example if guidance mentions both notion and link following
    base_lower = base_guidance.lower()
    if 'notion' in base_lower and 'link following' in base_lower:
        enhanced += "\n\n# EXAMPLE: Notion Page Link Following\n\n"
        enhanced += "Here's a complete example showing how to extract and follow page mentions:\n\n"
        enhanced += NOTION_LINK_FOLLOWING_EXAMPLE

    return enhanced
