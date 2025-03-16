from fpdf import FPDF
import os

class PDFGenerator:
    def __init__(self, title):
        self.title = title
        self.pdf = FPDF()
        self.pdf.set_auto_page_break(auto=True, margin=15)
        self.pdf.add_page()

        # Add and use Roboto font
        font_path = os.path.join(os.path.dirname(__file__), "fonts", "Roboto-Regular.ttf")
        self.pdf.add_font("Roboto", "", font_path, uni=True)
        self.pdf.add_font("Roboto", "B", font_path, uni=True)
        self.pdf.set_font("Roboto", "", 12)

        # Title
        self.pdf.set_font("Roboto", "B", 16)
        self.pdf.cell(200, 10, self.title, ln=True, align="C")
        self.pdf.ln(10)

    def add_table(self, data):
        if not data:
            self.pdf.cell(0, 10, "No data available", ln=True)
            return

        # Automatically detect correct column names
        headers = list(data[0].keys())
        col_widths = [40, 50, 25, 30, 30, 20]  # Adjust based on column count

        # Header styling
        self.pdf.set_font("Roboto", "B", 12)
        self.pdf.set_fill_color(200, 200, 200)  # Light gray background
        for i, header in enumerate(headers):
            self.pdf.cell(col_widths[i], 10, header, border=1, align="C", fill=True)
        self.pdf.ln()

        # Row styling
        self.pdf.set_font("Roboto", "", 10)
        fill = False
        total_minutes = 0
        total_cost = 0

        for row in data:
            try:
                duration = float(row.get("Durata (minuti)", 0))
                total_minutes += duration
                total_cost += float(row.get("Costo Totale (€)", 0))
            except ValueError:
                duration = 0  # Prevent errors if value is missing or incorrect format

            for i, key in enumerate(headers):
                value = str(row[key])
                self.pdf.cell(col_widths[i], 8, value, border=1, align="C", fill=fill)
            self.pdf.ln()
            fill = not fill  # Alternate row colors

        self.pdf.ln(10)
        self.add_summary(total_minutes, total_cost)

    def add_summary(self, total_minutes, total_cost):
        self.pdf.set_font("Roboto", "", 12)
        self.pdf.cell(0, 10, f"Total Minutes Used: {total_minutes:.2f} min", ln=True)
        self.pdf.cell(0, 10, f"Total Billed Amount: €{total_cost:.2f}", ln=True)
        self.pdf.ln(10)

    def save_pdf(self, filename):
        self.pdf.output(filename)
