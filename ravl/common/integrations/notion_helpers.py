#!/usr/bin/env python3
"""
Notion Minimal Helpers

Stateless utility functions for parsing Notion API responses.
These helpers handle genuinely hard API nuances (like rich_text mention parsing)
while leaving workflow and orchestration to generated code.

Aligned with RAVL Vision Principle 5: Hybrid Intelligence
- Helpers are "system-level" utilities
- Generated code controls workflow
- Bias toward generation, helpers only for proven hard patterns
"""

from typing import List, Dict, Any


class NotionLinkExtractor:
    """
    Minimal utility for extracting linked page IDs from Notion rich_text arrays.

    Notion represents page links (mentions) in rich_text as:
    {
        "type": "mention",
        "mention": {
            "type": "page",
            "page": {"id": "page-id-here"}
        }
    }

    This helper extracts those IDs. Generated code decides what to do with them
    (fetch, recursively traverse, merge, etc.).
    """

    @staticmethod
    def extract_page_mentions(rich_text_array: List[Dict[str, Any]]) -> List[str]:
        """
        Extract page IDs from Notion rich_text mention objects.

        Args:
            rich_text_array: List of rich_text objects from Notion block response

        Returns:
            List of page IDs found in page mentions (may contain duplicates)

        Example:
            rich_text = block.get("paragraph", {}).get("rich_text", [])
            page_ids = NotionLinkExtractor.extract_page_mentions(rich_text)

            # Generated code decides workflow:
            for page_id in page_ids:
                content = fetch_page_content(page_id)  # LLM-generated logic
                merge_content(content)  # LLM-generated logic
        """
        page_ids = []

        # Handle None or empty array
        if not rich_text_array:
            return page_ids

        for text_obj in rich_text_array:
            # Check if this is a mention object
            if text_obj.get("type") == "mention":
                mention = text_obj.get("mention", {})

                # Check if mention is a page reference
                if mention.get("type") == "page":
                    page = mention.get("page", {})
                    page_id = page.get("id")

                    if page_id:
                        page_ids.append(page_id)

        return page_ids

    @staticmethod
    def extract_all_page_mentions_from_blocks(blocks: List[Dict[str, Any]]) -> List[str]:
        """
        Extract page mentions from all rich_text fields in a list of Notion blocks.

        Searches common block types that contain rich_text arrays:
        - paragraph, heading_1/2/3, bulleted_list_item, numbered_list_item,
          to_do, toggle, quote, callout

        Args:
            blocks: List of Notion block objects

        Returns:
            List of page IDs found across all blocks (may contain duplicates)

        Example:
            blocks_response = notion.blocks.children.list(page_id)
            blocks = blocks_response.get("results", [])
            all_linked_pages = NotionLinkExtractor.extract_all_page_mentions_from_blocks(blocks)

            # Dedupe and fetch
            for page_id in set(all_linked_pages):
                fetch_and_process(page_id)
        """
        all_page_ids = []

        # Block types that commonly contain rich_text
        rich_text_block_types = [
            "paragraph", "heading_1", "heading_2", "heading_3",
            "bulleted_list_item", "numbered_list_item",
            "to_do", "toggle", "quote", "callout"
        ]

        for block in blocks or []:
            # Check each possible block type for rich_text
            for block_type in rich_text_block_types:
                if block_type in block:
                    rich_text = block[block_type].get("rich_text", [])
                    page_ids = NotionLinkExtractor.extract_page_mentions(rich_text)
                    all_page_ids.extend(page_ids)

        return all_page_ids
