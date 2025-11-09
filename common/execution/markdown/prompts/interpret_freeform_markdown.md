# Interpret and Enhance Markdown RAVL Loop

You are validating, enhancing, and/or interpreting a RAVL loop defined in markdown.

## CRITICAL: Preserve User Intent

**Your job is to structure the user's instructions into RAVL phases, NOT to rewrite or filter them.**

**DO:**
- ✅ Preserve user instructions verbatim
- ✅ Structure their intent into Act/Verify sections
- ✅ Keep all user-specified methods and approaches (including "use an LLM", "parse with regex", etc.)

**DO NOT:**
- ❌ Remove or rewrite user instructions
- ❌ Add infrastructure details the user didn't specify
- ❌ Second-guess the user's choice of methods

**Example**:

User says: "Use an LLM call to combine FDE data into structured JSON"
- ✅ CORRECT: Keep "Use an LLM call to combine..." verbatim in Act section
- ❌ WRONG: Rewrite to "Combine FDE data into structured JSON" (removes user's instruction to use LLM)

User says: "Parse files and extract email addresses"
- ✅ CORRECT: Keep "Parse files and extract..." verbatim
- ❌ WRONG: Don't add "Use OAuth2 authentication..." (user didn't ask for this)

**Your role**: Structure user intent, don't filter it. Trust the user knows what they want.

## RAVL PROTOCOL (Key Concepts)

{protocol_text}

## EXAMPLES OF WELL-STRUCTURED RAVL LOOPS

{examples_text}

## PREVIOUS RUN INSIGHTS

{run_insights}

Consider these learned insights when structuring the loop. If previous runs identified successful patterns, incorporate them. If previous runs identified failed patterns, avoid them in your enhancement.

{domain_guidance}

## How to Use Domain Guidance

When fresh domain guidance is provided above:

1. **Priority Focus**: Structure ACT instructions to address these priorities first
2. **Successful Patterns**: Incorporate these approaches into ACT guidance - they worked before
3. **Failed Patterns**: Add warnings or avoid these in ACT instructions - they failed before
4. **Verification Failures**: Structure VERIFY criteria to catch these specific issues

The enhanced ACT section should directly address domain learnings from REFLECT, not just translate user's raw instructions.

## USER'S LOOP INTENT

**Name:** {loop_name}

**Raw markdown:**

```
{raw_markdown}
```
{existing_phases}
## Task

Your goal is to produce a complete, well-structured RAVL loop with all required sections.

**Two Scenarios:**

1. **Enhancement Mode** (existing sections provided above):
   - If a section is well-written and complete, preserve it EXACTLY as-is
   - If a section is incomplete or unclear, enhance it with proper structure
   - Fill in any missing sections (Act, Verify, etc.)
   - Validate that all sections follow RAVL protocol

2. **Interpretation Mode** (no existing sections):
   - Interpret the user's intent from raw markdown
   - Create properly structured RAVL phases from scratch

**Output Requirements:**

Output ONLY the structured markdown with these sections (use exact headings):

### # Act

[Specific actionable steps - preserve existing if good, otherwise enhance/create]

### # Verify

[Clear, testable acceptance criteria - preserve existing if good, otherwise enhance/create]

**IMPORTANT:**
- Do not include explanations or meta-commentary
- Output only the structured markdown
- Preserve user's well-written content verbatim
- Always include both Act and Verify sections at minimum
