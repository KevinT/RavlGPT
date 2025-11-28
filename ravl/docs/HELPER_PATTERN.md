# Helper-Augmented Generation Pattern

## Overview

RAVL uses a **"bias toward code generation"** approach where most logic is LLM-generated for maximum adaptability. However, some API patterns are genuinely hard and benefit from reusable helper utilities. This document describes when and how to create helpers that augment (not replace) code generation.

## The Pattern

**Minimal utility helpers + LLM-generated workflows = Resilience + Reliability**

- **Helpers** handle genuinely hard API nuances (parsing, extraction, type conversion)
- **Generated code** owns workflow, orchestration, and business logic
- **Helpers are OPTIONAL** - LLMs can choose to use them or roll their own

## Alignment with RAVL Vision

This pattern aligns with [RAVL_VISION.md](RAVL_VISION.md):

- ✅ **Principle 3 (Inferred Completeness)**: Helpers are "opportunities" that improve success likelihood, not requirements
- ✅ **Principle 5 (Hybrid Intelligence)**: Helpers are "system-level" infrastructure, generated code uses them flexibly
- ✅ **Principle 6 (Context-Driven Generation)**: Generated code stays imperative, helpers are just utilities

## When to Create a Helper

Create a helper when **all** of these are true:

1. **Pattern is genuinely hard**: The API structure is complex and unintuitive (e.g., Notion's nested mention objects)
2. **Pattern has failed repeatedly**: Generated code has struggled with this pattern across multiple attempts
3. **Pattern is stable**: The API structure won't change frequently
4. **One correct implementation exists**: There's a clear "right way" to handle the pattern

## When NOT to Create a Helper

Don't create a helper if:

- ❌ The pattern is straightforward REST API calls
- ❌ The pattern might change based on business needs
- ❌ The pattern involves orchestration or workflow
- ❌ Only one loop needs this functionality

## Helper Design Principles

### 1. Stateless and Focused

**Good - Minimal utility:**
```python
class NotionLinkExtractor:
    @staticmethod
    def extract_page_mentions(rich_text_array: List[Dict]) -> List[str]:
        """Extract page IDs from Notion rich_text mention objects."""
        page_ids = []
        for text_obj in rich_text_array:
            if text_obj.get("type") == "mention":
                mention = text_obj.get("mention", {})
                if mention.get("type") == "page":
                    page_id = mention.get("page", {}).get("id")
                    if page_id:
                        page_ids.append(page_id)
        return page_ids
```

**Bad - Workflow helper:**
```python
class NotionWorkflowHelper:
    def __init__(self, loop_instance):
        self.loop = loop_instance  # ❌ Stateful

    def fetch_and_merge_pages(self, page_id):  # ❌ Owns workflow
        content = self.fetch_page(page_id)
        linked = self.follow_links(content)
        return self.merge(content, linked)
```

### 2. Parse/Extract Only - No Workflow

Helpers should:
- ✅ Parse complex structures
- ✅ Extract specific data
- ✅ Convert between formats
- ❌ Fetch from APIs
- ❌ Make orchestration decisions
- ❌ Handle entire workflows

### 3. No Dependencies on Loop State

**Good:**
```python
@staticmethod
def extract_page_mentions(rich_text_array: List[Dict]) -> List[str]:
    # Pure function - no external dependencies
```

**Bad:**
```python
def extract_page_mentions(self):
    return self.loop.process_rich_text(self.loop.current_page)  # ❌ Loop coupling
```

## Integration with DSL Inference

Helpers are made discoverable through three mechanisms:

### 1. Link Following Detection

`dsl_inference_engine.py:_analyze_act_section()`:
```python
# Check for link following requirements
link_keywords = ['follow link', 'linked page', 'recursively', 'traverse']
if any(keyword in act_section.lower() for keyword in link_keywords):
    requirements['needs_link_following'] = True
```

### 2. API-Aware Guidance

`dsl_inference_engine.py:_generate_llm_guidance()`:
```python
# Link following guidance (API-aware)
if act_req.get('needs_link_following'):
    api_type = (act_req.get('api_type') or '').lower()

    if 'notion' in api_type:
        guidance_lines.append("- OPTIONAL HELPER: from ravl.common.integrations.notion_helpers import NotionLinkExtractor")
        guidance_lines.append("- Use NotionLinkExtractor.extract_page_mentions(rich_text) to get linked page IDs")
        guidance_lines.append("- Or implement your own parsing logic")
```

### 3. Example Templates

`schema_adapters.py:enhance_llm_guidance_with_schema_adaptation()`:
```python
# Add link following example if guidance mentions both notion and link following
if 'notion' in base_lower and 'link following' in base_lower:
    enhanced += NOTION_LINK_FOLLOWING_EXAMPLE
```

## Example: Notion Link Following

### The Problem

Notion page links appear in rich_text as nested mention objects:
```json
{
  "type": "mention",
  "mention": {
    "type": "page",
    "page": {"id": "abc123"}
  }
}
```

This is **genuinely hard** - 4 levels of nesting with type checks at each level.

### The Helper

**File**: `.ravl/ravl/common/integrations/notion_helpers.py`

```python
class NotionLinkExtractor:
    """Minimal utility for extracting linked page IDs from Notion rich_text arrays."""

    @staticmethod
    def extract_page_mentions(rich_text_array: List[Dict[str, Any]]) -> List[str]:
        """Extract page IDs from Notion rich_text mention objects."""
        page_ids = []
        if not rich_text_array:
            return page_ids

        for text_obj in rich_text_array:
            if text_obj.get("type") == "mention":
                mention = text_obj.get("mention", {})
                if mention.get("type") == "page":
                    page_id = mention.get("page", {}).get("id")
                    if page_id:
                        page_ids.append(page_id)
        return page_ids
```

### Generated Code Usage

The LLM has three options:

**Option A - Use the helper:**
```python
from ravl.common.integrations.notion_helpers import NotionLinkExtractor

rich_text = block.get("paragraph", {}).get("rich_text", [])
linked_page_ids = NotionLinkExtractor.extract_page_mentions(rich_text)
```

**Option B - Implement inline:**
```python
def extract_page_mentions(rich_text_array):
    page_ids = []
    for text_obj in rich_text_array:
        if text_obj.get("type") == "mention":
            mention = text_obj.get("mention", {})
            if mention.get("type") == "page"):
                page_id = mention.get("page", {}).get("id")
                if page_id:
                    page_ids.append(page_id)
    return page_ids
```

**Option C - Custom variant:**
```python
# LLM might choose different logic based on specific needs
```

All three are valid! The helper is infrastructure, not a requirement.

## Comparison: Workflow vs Minimal Helpers

### Google Helpers (Existing - Workflow-Oriented)

**File**: `.ravl/ravl/common/integrations/google_docs_exporter.py`

```python
class GoogleDocsExporter:
    def __init__(self, loop_with_mixin):
        self.loop = loop_with_mixin  # Stateful

    def export_as_markdown(self, url: str) -> str:
        # Handles full workflow:
        doc_id = extract_from_url(url)
        document = docs_service.get(documentId=doc_id).execute()
        markdown = drive_service.export(fileId=doc_id, mimeType='text/markdown')
        return markdown  # Makes decisions about what to return
```

**Trade-offs:**
- ✅ Very stable and reliable
- ✅ Well-tested
- ❌ Less adaptable (fixed workflow)
- ❌ Requires mixin inheritance
- ❌ Less aligned with RAVL Vision

**Status**: Keeping as-is (already works, no breaking changes needed)

### Notion Helper (New - Minimal Pattern)

```python
class NotionLinkExtractor:
    @staticmethod
    def extract_page_mentions(rich_text_array: List[Dict]) -> List[str]:
        # Just parsing - workflow is up to generated code
```

**Trade-offs:**
- ✅ Fully adaptable (generated code owns workflow)
- ✅ Stateless (no coupling)
- ✅ Aligned with RAVL Vision
- ⚠️  Requires testing the pattern

**Status**: New pattern - test case for minimal helpers

## Migration Strategy

### Phase 1: Coexistence

- Keep existing Google workflow helpers (stable, working)
- Add new Notion minimal helpers (test the pattern)
- Document both approaches
- Let loops choose based on needs

### Phase 2: Evaluation

After 3-6 months:
- Compare failure rates (workflow vs minimal)
- Assess adaptability (how often do loops customize?)
- Gather developer feedback

### Phase 3: Decision

Based on evidence:
- **If minimal pattern wins**: Gradually deprecate workflow helpers
- **If workflow pattern wins**: Continue using both patterns
- **If mixed**: Document when to use each pattern

## Creating a New Helper

### Step 1: Identify the Hard Pattern

Example: Notion rich_text mention parsing

### Step 2: Create Minimal Helper

```python
# .ravl/ravl/common/integrations/{api}_helpers.py

class {API}Helper:
    """Minimal utility for {specific hard pattern}"""

    @staticmethod
    def {method_name}({input_data}) -> {output_type}:
        """
        {What it does - parsing/extraction only}

        Args:
            {input_data}: {Description}

        Returns:
            {output_type}: {Description}

        Example:
            >>> data = get_api_response()
            >>> result = {API}Helper.{method_name}(data)
            >>> # Generated code decides what to do with result
        """
        # Implementation
```

### Step 3: Add Detection Logic

`dsl_inference_engine.py:_analyze_act_section()`:
```python
# Check for {pattern} requirements
if any(word in act_section.lower() for word in ['{keyword1}', '{keyword2}']):
    requirements['needs_{pattern}'] = True
```

### Step 4: Add API-Aware Guidance

`dsl_inference_engine.py:_generate_llm_guidance()`:
```python
if act_req.get('needs_{pattern}'):
    api_type = (act_req.get('api_type') or '').lower()

    if '{api}' in api_type:
        guidance_lines.append("- OPTIONAL HELPER: from ravl.common.integrations.{api}_helpers import {Helper}")
        guidance_lines.append("- Use {Helper}.{method}() to {purpose}")
        guidance_lines.append("- Or implement your own logic")
```

### Step 5: Add Example Template (Optional)

`schema_adapters.py`:
```python
{API}_{PATTERN}_EXAMPLE = '''
# Complete example showing how to use the helper
'''

# In enhance_llm_guidance_with_schema_adaptation():
if '{api}' in base_lower and '{pattern}' in base_lower:
    enhanced += {API}_{PATTERN}_EXAMPLE
```

### Step 6: Test

1. Clear learning artifacts for test loop
2. Run loop and verify generated code includes pattern handling
3. Check if LLM uses helper or implements inline
4. Verify workflow logic is correct

### Step 7: Document

Add section to this document with:
- Problem description
- Helper implementation
- Generated code example
- Trade-offs

## Key Principles Summary

1. **Bias toward generation**: Always prefer generated code when possible
2. **Helpers are infrastructure**: They're utilities, not workflows
3. **OPTIONAL, not required**: LLMs can choose to use helpers or not
4. **Minimal and focused**: Parse/extract only, no orchestration
5. **Stateless**: No dependencies on loop state or config
6. **API-aware guidance**: Make helpers discoverable through DSL inference
7. **Test the pattern**: New helpers should prove their value before widespread adoption

## Success Metrics

A helper is successful when:
- ✅ Generated code reliably handles the hard pattern (with or without the helper)
- ✅ LLMs use the helper appropriately (when helpful, not always)
- ✅ Loops can still adapt workflows to specific needs
- ✅ Failure rates for the pattern decrease
- ✅ No one is confused about what the helper does

A helper needs revision when:
- ❌ LLMs always use it (too much dependency, reduces adaptability)
- ❌ LLMs never use it (not helpful enough, remove it)
- ❌ Loops frequently customize around it (helper is wrong abstraction)
- ❌ Helper changes frequently (pattern isn't stable enough)

## Questions and Decisions

**Q: Should every API have a helper?**
A: No. Only create helpers for genuinely hard patterns that have proven difficult.

**Q: Can helpers call other helpers?**
A: Yes, but keep the dependency tree shallow (max 1-2 levels).

**Q: Should helpers handle authentication?**
A: No. Authentication is handled by mixins or generated code.

**Q: What if a helper needs configuration?**
A: Pass config as parameters, don't access global state.

**Q: Can helpers be async?**
A: Yes, if the API pattern requires it. But keep them simple.

**Q: Should I refactor existing workflow helpers?**
A: Not immediately. Test the minimal pattern first, then decide based on evidence.

## Related Documentation

- [RAVL_VISION.md](RAVL_VISION.md) - Core principles and design philosophy
- [RAVL_PROTOCOL.md](RAVL_PROTOCOL.md) - Four-phase loop specification
- Schema adapters documentation (in code comments)
- DSL inference documentation (in code comments)
