"""CSV and Excel export utilities for WarehouseIQ."""

import csv
import io
import logging
from datetime import datetime
from typing import Any

from django.http import HttpResponse

logger = logging.getLogger(__name__)


def export_queryset_to_csv(
    queryset,
    fields: list[str],
    headers: list[str] | None = None,
    filename: str = "export",
) -> HttpResponse:
    """
    Export a Django queryset to a CSV file response.

    Args:
        queryset: The queryset to export.
        fields: List of field names / lookups to include as columns.
        headers: Optional list of display headers. Uses field names if not provided.
        filename: Base filename (without extension).

    Returns:
        HttpResponse with CSV content-type and attachment disposition.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_filename = f"{filename}_{timestamp}.csv"

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{full_filename}"'

    writer = csv.writer(response)
    writer.writerow(headers or fields)

    for obj in queryset:
        row = []
        for field in fields:
            value = _resolve_field(obj, field)
            row.append(str(value) if value is not None else "")
        writer.writerow(row)

    return response


def export_data_to_csv(
    data: list[dict[str, Any]],
    fields: list[str],
    headers: list[str] | None = None,
    filename: str = "export",
) -> HttpResponse:
    """
    Export a list of dictionaries to a CSV file response.

    Args:
        data: List of dicts to export.
        fields: Keys to include as columns.
        headers: Optional display headers.
        filename: Base filename.

    Returns:
        HttpResponse with CSV content and attachment headers.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_filename = f"{filename}_{timestamp}.csv"

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{full_filename}"'

    writer = csv.writer(response)
    writer.writerow(headers or fields)

    for item in data:
        row = [str(item.get(field, "")) for field in fields]
        writer.writerow(row)

    return response


def export_queryset_to_excel(
    queryset,
    fields: list[str],
    headers: list[str] | None = None,
    filename: str = "export",
    sheet_name: str = "Data",
) -> HttpResponse:
    """
    Export a Django queryset to an Excel (.xlsx) file response.

    Requires openpyxl.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name

    # Style the header row
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_alignment = Alignment(horizontal="center")

    display_headers = headers or fields
    for col_idx, header in enumerate(display_headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment

    # Write data rows
    for row_idx, obj in enumerate(queryset, 2):
        for col_idx, field in enumerate(fields, 1):
            value = _resolve_field(obj, field)
            ws.cell(row=row_idx, column=col_idx, value=value)

    # Auto-width columns
    for col_idx, header in enumerate(display_headers, 1):
        col_letter = ws.cell(row=1, column=col_idx).column_letter
        max_length = len(str(header))
        for row in ws.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx):
            for cell in row:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max_length + 4, 50)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_filename = f"{filename}_{timestamp}.xlsx"

    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{full_filename}"'
    return response


def _resolve_field(obj, field_path: str) -> Any:
    """Resolve a dot/dunder-separated field path on a model instance."""
    parts = field_path.replace("__", ".").split(".")
    current = obj
    for part in parts:
        if current is None:
            return None
        if hasattr(current, part):
            current = getattr(current, part)
            if callable(current):
                current = current()
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current
