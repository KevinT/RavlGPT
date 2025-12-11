#!/usr/bin/env python3
"""
Google Sheets to Markdown Converter

Shared utilities for converting Google Sheets data structures to markdown tables.
Used by both GoogleSheetsAnalyzer (current state) and GoogleSheetsRevisionTracker (history).

Extracted from GoogleSheetsAnalyzer to avoid code duplication.
"""

from typing import List, Dict, Any


def sheets_to_markdown(title: str, sheets_data: List[Dict[str, Any]]) -> str:
    """
    Convert sheets data to markdown format.

    Args:
        title: Spreadsheet title
        sheets_data: List of sheet data dicts with keys:
            - 'title': Sheet name
            - 'values': 2D list of cell values
            - 'error': Optional error message

    Returns:
        Markdown formatted string with title and all sheets
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
        markdown_parts.append(values_to_markdown_table(values))

    return "\n".join(markdown_parts)


def values_to_markdown_table(values: List[List[str]]) -> str:
    """
    Convert 2D array of values to markdown table.

    Args:
        values: 2D list of cell values (rows and columns)

    Returns:
        Markdown table string with proper column alignment
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


def is_empty_row(row: List[str]) -> bool:
    """
    Check if a row contains only empty or whitespace strings.

    Args:
        row: List of cell values as strings

    Returns:
        True if row is completely empty, False otherwise
    """
    return all(cell.strip() == '' for cell in row)


def trim_empty_columns(values: List[List[str]]) -> List[List[str]]:
    """
    Remove trailing empty columns from all rows in a dataset.

    Args:
        values: 2D list of cell values

    Returns:
        2D list with trailing empty columns removed
    """
    if not values:
        return values

    # Find the maximum column index that contains non-empty data
    max_col_with_data = 0
    for row in values:
        for i, cell in enumerate(row):
            if cell.strip() != '':
                max_col_with_data = max(max_col_with_data, i)

    # Trim all rows to max_col_with_data + 1 (convert index to count)
    trimmed_values = [row[:max_col_with_data + 1] for row in values]

    return trimmed_values
