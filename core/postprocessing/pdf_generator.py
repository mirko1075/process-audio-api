"""PDF generation helpers for summary reports."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from fpdf import FPDF


@dataclass
class PDFGenerator:
    """Generate simple tabular PDF reports."""

    title: str

    def build(self, rows: Iterable[Mapping[str, str]], output_path: Path) -> Path:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(200, 10, self.title, ln=True, align="C")
        pdf.ln(10)

        rows = list(rows)
        if not rows:
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, "No data available", ln=True)
            pdf.output(str(output_path))
            return output_path

        headers = list(rows[0].keys())
        pdf.set_font("Arial", "B", 12)
        for header in headers:
            pdf.cell(40, 10, header, border=1, align="C")
        pdf.ln()

        pdf.set_font("Arial", size=10)
        for row in rows:
            for header in headers:
                pdf.cell(40, 8, str(row.get(header, "")), border=1, align="C")
            pdf.ln()

        pdf.output(str(output_path))
        return output_path
