"""Helper for generating Word documents from text content."""
from __future__ import annotations

from pathlib import Path

from docx import Document


def create_word_document(content: str, filename: str) -> Path:
    output_path = Path("/tmp") / filename
    document = Document()
    for paragraph in content.split("\n"):
        document.add_paragraph(paragraph)
    document.save(output_path)
    return output_path
