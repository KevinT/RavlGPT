#!/usr/bin/env python3
"""
Google Slides Exporter Workflow

Handles extraction of content from Google Slides and conversion to markdown format.

Inherits from GoogleAPIsMixin to access Google Slides service.
"""

import re
from datetime import datetime, timezone
from typing import Dict, Any, List


class GoogleSlidesExporter:
    """
    Exports content from Google Slides to markdown format.

    Usage:
        exporter = GoogleSlidesExporter(loop)  # loop must inherit GoogleAPIsMixin
        slides = exporter.fetch(url)
        markdown = exporter.export_as_markdown(url)
    """

    def __init__(self, loop_with_mixin):
        """
        Initialize with a loop that has GoogleAPIsMixin.

        Args:
            loop_with_mixin: A RAVL loop instance that inherits GoogleAPIsMixin
        """
        self.loop = loop_with_mixin

    def fetch(self, url: str) -> Dict[str, Any]:
        """
        Fetch content from Google Slides using the Slides API.

        Args:
            url: Google Slides URL

        Returns:
            Dict with:
            - 'text': Full markdown text content (converted from slides)
            - 'title': Presentation title
            - 'last_modified': ISO timestamp of last modification
            - 'doc_id': Extracted presentation ID from URL

        Raises:
            ValueError: If URL is invalid
            Exception: If API request fails
        """
        if not self.loop.google_slides_service:
            self.loop.init_google_services()

        # Extract presentation ID from URL
        pres_id_match = re.search(r'/presentation/d/([a-zA-Z0-9-_]+)', url)
        if not pres_id_match:
            raise ValueError(f"Invalid Google Slides URL: {url}")

        pres_id = pres_id_match.group(1)

        # Get presentation from Slides API
        try:
            presentation = self.loop.google_slides_service.presentations().get(
                presentationId=pres_id
            ).execute()
        except Exception as e:
            raise Exception(f"Failed to fetch presentation: {e}")

        # Convert slides to markdown
        markdown_content = self._convert_presentation_to_markdown(presentation)

        # Get modification time from Drive API (Slides API doesn't provide it)
        last_modified = datetime.now(timezone.utc).isoformat() + '+00:00'
        try:
            if self.loop.google_drive_service:
                file_metadata = self.loop.google_drive_service.files().get(
                    fileId=pres_id,
                    fields='modifiedTime',
                    supportsAllDrives=True
                ).execute()
                last_modified = file_metadata.get('modifiedTime', last_modified)
        except Exception:
            # If Drive API fails, use current time
            pass

        return {
            'text': markdown_content,
            'title': presentation.get('title', ''),
            'last_modified': last_modified,
            'doc_id': pres_id
        }

    def export_as_markdown(self, url: str) -> str:
        """
        Fetch presentation and return as markdown string.

        Args:
            url: Google Slides URL

        Returns:
            Markdown formatted string

        Raises:
            ValueError: If URL is invalid
            Exception: If API request fails
        """
        slides = self.fetch(url)
        return slides['text']

    def _convert_presentation_to_markdown(self, presentation: Dict[str, Any]) -> str:
        """
        Convert a Google Slides presentation to markdown format.

        Args:
            presentation: Presentation object from Slides API

        Returns:
            Markdown formatted string
        """
        markdown_lines = []

        # Add title
        title = presentation.get('title', 'Untitled Presentation')
        markdown_lines.append(f"# {title}\n")

        # Process each slide
        slides = presentation.get('slides', [])
        for slide_num, slide in enumerate(slides, start=1):
            # Add slide heading
            markdown_lines.append(f"## Slide {slide_num}\n")

            # Extract text from all page elements
            text_content = self._extract_text_from_slide(slide)
            if text_content:
                markdown_lines.append(text_content)
            else:
                markdown_lines.append("*(No text content)*\n")

            # Add speaker notes if present
            notes = self._extract_speaker_notes(slide)
            if notes:
                markdown_lines.append(f"\n**Speaker Notes:**\n{notes}\n")

            markdown_lines.append("")  # Blank line between slides

        return "\n".join(markdown_lines)

    def _extract_text_from_slide(self, slide: Dict[str, Any]) -> str:
        """
        Extract all text content from a slide.

        Args:
            slide: Slide object from Slides API

        Returns:
            Text content as string
        """
        text_parts = []

        page_elements = slide.get('pageElements', [])
        for element in page_elements:
            # Check if element has shape with text
            if 'shape' in element:
                shape = element['shape']
                if 'text' in shape:
                    text = self._extract_text_from_shape(shape['text'])
                    if text:
                        text_parts.append(text)

            # Check if element is a table
            elif 'table' in element:
                table = element['table']
                table_text = self._extract_text_from_table(table)
                if table_text:
                    text_parts.append(table_text)

        return "\n\n".join(text_parts)

    def _extract_text_from_shape(self, text_object: Dict[str, Any]) -> str:
        """
        Extract text from a shape's text object.

        Args:
            text_object: Text object from Slides API

        Returns:
            Extracted text
        """
        text_parts = []

        text_elements = text_object.get('textElements', [])
        for element in text_elements:
            if 'textRun' in element:
                content = element['textRun'].get('content', '')
                text_parts.append(content)

        return "".join(text_parts).strip()

    def _extract_text_from_table(self, table: Dict[str, Any]) -> str:
        """
        Extract text from a table.

        Args:
            table: Table object from Slides API

        Returns:
            Table text as markdown table
        """
        rows = table.get('tableRows', [])
        if not rows:
            return ""

        table_lines = []
        for row_idx, row in enumerate(rows):
            cells = row.get('tableCells', [])
            row_text = []

            for cell in cells:
                cell_text = self._extract_text_from_shape(cell.get('text', {}))
                row_text.append(cell_text if cell_text else " ")

            # Format as markdown table
            table_lines.append("| " + " | ".join(row_text) + " |")

            # Add separator after header row
            if row_idx == 0:
                table_lines.append("| " + " | ".join(["---"] * len(row_text)) + " |")

        return "\n".join(table_lines)

    def _extract_speaker_notes(self, slide: Dict[str, Any]) -> str:
        """
        Extract speaker notes from a slide.

        Args:
            slide: Slide object from Slides API

        Returns:
            Speaker notes text or empty string
        """
        notes_properties = slide.get('slideProperties', {}).get('notesPage', {})
        if not notes_properties:
            return ""

        # Speaker notes are in the notes page's page elements
        notes_elements = notes_properties.get('pageElements', [])
        notes_text_parts = []

        for element in notes_elements:
            if 'shape' in element:
                shape = element['shape']
                if 'text' in shape:
                    text = self._extract_text_from_shape(shape['text'])
                    if text:
                        notes_text_parts.append(text)

        return "\n".join(notes_text_parts).strip()
