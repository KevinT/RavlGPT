#!/usr/bin/env python3
"""
Google Sheets Analyzer Workflow

Handles extraction and analysis of data from Google Sheets.

Inherits from GoogleAPIsMixin to access Google Sheets service.
"""

import re
import sys
from datetime import datetime
from typing import Dict, Any, List


class GoogleSheetsAnalyzer:
    """
    Analyzes and extracts data from Google Sheets.

    Usage:
        analyzer = GoogleSheetsAnalyzer(loop)  # loop must inherit GoogleAPIsMixin
        sheet_data = analyzer.fetch(url)
        markdown = analyzer.export_as_markdown(url)
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
        Fetch content from Google Sheets using the API.

        Args:
            url: Google Sheets URL

        Returns:
            Dict with:
            - 'text': Markdown formatted representation of all sheets
            - 'title': Spreadsheet title
            - 'last_modified': ISO timestamp of last modification
            - 'spreadsheet_id': Extracted spreadsheet ID from URL
            - 'sheets': List of sheet data (name, values)

        Raises:
            ValueError: If URL is invalid
            Exception: If API request fails
        """
        if not self.loop.google_sheets_service or not self.loop.google_drive_service:
            self.loop.init_google_services()

        # Extract spreadsheet ID from URL
        # Format: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit...
        spreadsheet_id_match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
        if not spreadsheet_id_match:
            raise ValueError(f"Invalid Google Sheets URL: {url}")

        spreadsheet_id = spreadsheet_id_match.group(1)

        try:
            # Get spreadsheet metadata and all sheets
            spreadsheet = self.loop.google_sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()

            title = spreadsheet.get('properties', {}).get('title', 'Untitled Spreadsheet')
            sheets = spreadsheet.get('sheets', [])

            # Note: Sheets API does not provide modification timestamps
            # Drive API may not have access to personal drive files even when Sheets API does
            # Set to None to be explicit that this information is unavailable
            last_modified = None

            # Fetch data for each sheet
            sheets_data = []
            for sheet in sheets:
                sheet_properties = sheet.get('properties', {})
                sheet_title = sheet_properties.get('title', 'Untitled Sheet')
                sheet_id = sheet_properties.get('sheetId')

                try:
                    # Get all values for this sheet
                    result = self.loop.google_sheets_service.spreadsheets().values().get(
                        spreadsheetId=spreadsheet_id,
                        range=sheet_title  # Use sheet title as range to get all data
                    ).execute()

                    values = result.get('values', [])

                    sheets_data.append({
                        'title': sheet_title,
                        'sheet_id': sheet_id,
                        'values': values
                    })

                except Exception as e:
                    from pathlib import Path
                    _utils_dir = Path(__file__).parent.parent / 'utils'
                    import sys
                    if str(_utils_dir) not in sys.path:
                        sys.path.insert(0, str(_utils_dir))
                    from logging_utils import log_execution
                    log_execution(f"Could not fetch data for sheet '{sheet_title}': {e}", status='error')
                    sheets_data.append({
                        'title': sheet_title,
                        'sheet_id': sheet_id,
                        'values': [],
                        'error': str(e)
                    })

            # Convert to markdown
            markdown_text = self._sheets_to_markdown(title, sheets_data)

            return {
                'text': markdown_text,
                'title': title,
                'last_modified': last_modified,
                'spreadsheet_id': spreadsheet_id,
                'sheets': sheets_data
            }

        except Exception as e:
            raise Exception(f"Failed to fetch spreadsheet: {e}")

    def export_as_markdown(self, url: str) -> str:
        """
        Fetch sheets and return as markdown string.

        Args:
            url: Google Sheets URL

        Returns:
            Markdown formatted string

        Raises:
            ValueError: If URL is invalid
            Exception: If API request fails
        """
        sheet_data = self.fetch(url)
        return sheet_data['text']

    def _sheets_to_markdown(self, title: str, sheets_data: List[Dict[str, Any]]) -> str:
        """
        Convert sheets data to markdown format.

        Args:
            title: Spreadsheet title
            sheets_data: List of sheet data dicts

        Returns:
            Markdown formatted string
        """
        markdown_parts = [f"# {title}\n"]

        for sheet in sheets_data:
            sheet_title = sheet.get('title', 'Untitled Sheet')
            values = sheet.get('values', [])
            error = sheet.get('error')

            markdown_parts.append(f"\n## {sheet_title}\n")

            if error:
                markdown_parts.append(f"*Error fetching sheet data: {error}*\n")
                continue

            if not values:
                markdown_parts.append("*No data in this sheet*\n")
                continue

            # Convert to markdown table
            markdown_parts.append(self._values_to_markdown_table(values))

        return "\n".join(markdown_parts)

    def _values_to_markdown_table(self, values: List[List[str]]) -> str:
        """
        Convert 2D array of values to markdown table.

        Args:
            values: 2D list of cell values

        Returns:
            Markdown table string
        """
        if not values:
            return ""

        # Find maximum number of columns
        max_cols = max(len(row) for row in values) if values else 0

        if max_cols == 0:
            return ""

        # Normalize all rows to have same number of columns (pad with empty strings)
        normalized_rows = []
        for row in values:
            normalized_row = list(row) + [''] * (max_cols - len(row))
            normalized_rows.append(normalized_row)

        # Calculate column widths
        col_widths = [0] * max_cols
        for row in normalized_rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))

        # Minimum width of 3 for each column
        col_widths = [max(3, width) for width in col_widths]

        # Build markdown table
        lines = []

        # Header row (first row of data)
        if normalized_rows:
            header_cells = [str(cell).ljust(col_widths[i]) for i, cell in enumerate(normalized_rows[0])]
            lines.append("| " + " | ".join(header_cells) + " |")

            # Separator row
            separators = ["-" * col_widths[i] for i in range(max_cols)]
            lines.append("| " + " | ".join(separators) + " |")

            # Data rows
            for row in normalized_rows[1:]:
                row_cells = [str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)]
                lines.append("| " + " | ".join(row_cells) + " |")

        return "\n".join(lines) + "\n"
