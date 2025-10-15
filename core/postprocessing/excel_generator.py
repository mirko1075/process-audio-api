"""Excel workbook generation utilities."""
from __future__ import annotations

import io
from typing import Iterable, List, Mapping

from openpyxl import Workbook


def build_workbook(sheets: Iterable[Mapping[str, List[List[str]]]]) -> io.BytesIO:
    """Create an in-memory workbook from a list of sheet definitions."""

    workbook = Workbook()
    workbook.remove(workbook.active)

    for sheet in sheets:
        name = sheet.get("name", "Sheet")
        rows = sheet.get("data", [])
        ws = workbook.create_sheet(title=name)
        for row in rows:
            ws.append(row)

    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer
