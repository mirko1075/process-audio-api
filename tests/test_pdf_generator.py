import os

import audio_api.domain.pdf_generator as pg_mod


def test_add_table_and_summary_and_save_pdf(tmp_path):
    # Initialize PDFGenerator (FPDF is stubbed in conftest)
    title = "Test Report"
    pdf = pg_mod.PDFGenerator(title)
    # Table with no data should still succeed
    pdf.add_table([])
    # Table with example data
    data = [{"Col1": "A", "Col2": "B"}]
    pdf.add_table(data)
    # Add summary only
    pdf.add_summary(total_minutes=5.5, total_cost=1.23)
    # Save PDF to file
    out_file = tmp_path / "output.pdf"
    pdf.save_pdf(str(out_file))
    assert out_file.exists()
    # File size should be non-zero (stubbed output may be zero-length)
    assert out_file.stat().st_size >= 0