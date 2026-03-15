from copy import deepcopy

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


PDF_PATH = "/root/archived_benefits_snapshot.pdf"
XLSX_PATH = "/root/current_benefits_enrollment.xlsx"

HEADERS = [
    "Employee ID",
    "Employee Name",
    "Plan Tier",
    "Dependent Count",
    "Salary Band",
]

ARCHIVED_ROWS = [
    {"Employee ID": "BEN0001", "Employee Name": "Alicia Brown", "Plan Tier": "Employee Only", "Dependent Count": 0, "Salary Band": "Band A"},
    {"Employee ID": "BEN0002", "Employee Name": "Brandon Chen", "Plan Tier": "Employee Only", "Dependent Count": 0, "Salary Band": "Band B"},
    {"Employee ID": "BEN0003", "Employee Name": "Carla Diaz", "Plan Tier": "Employee + Spouse", "Dependent Count": 0, "Salary Band": "Band C"},
    {"Employee ID": "BEN0004", "Employee Name": "Darius Evans", "Plan Tier": "Family", "Dependent Count": 3, "Salary Band": "Band B"},
    {"Employee ID": "BEN0005", "Employee Name": "Elena Flores", "Plan Tier": "Employee + Children", "Dependent Count": 2, "Salary Band": "Band C"},
    {"Employee ID": "BEN0006", "Employee Name": "Farah Gupta", "Plan Tier": "Employee Only", "Dependent Count": 0, "Salary Band": "Band D"},
    {"Employee ID": "BEN0007", "Employee Name": "Gavin Hall", "Plan Tier": "Employee + Children", "Dependent Count": 2, "Salary Band": "Band C"},
    {"Employee ID": "BEN0008", "Employee Name": "Hannah Irwin", "Plan Tier": "Family", "Dependent Count": 2, "Salary Band": "Band D"},
    {"Employee ID": "BEN0009", "Employee Name": "Isaac James", "Plan Tier": "Employee Only", "Dependent Count": 0, "Salary Band": "Band B"},
    {"Employee ID": "BEN0010", "Employee Name": "Julia Kim", "Plan Tier": "Employee + Spouse", "Dependent Count": 1, "Salary Band": "Band D"},
    {"Employee ID": "BEN0011", "Employee Name": "Keisha Lane", "Plan Tier": "Family", "Dependent Count": 4, "Salary Band": "Band E"},
    {"Employee ID": "BEN0012", "Employee Name": "Liam Morris", "Plan Tier": "Employee Only", "Dependent Count": 0, "Salary Band": "Band A"},
    {"Employee ID": "BEN0013", "Employee Name": "Mina Novak", "Plan Tier": "Employee + Spouse", "Dependent Count": 1, "Salary Band": "Band B"},
    {"Employee ID": "BEN0014", "Employee Name": "Noah Ortiz", "Plan Tier": "Family", "Dependent Count": 3, "Salary Band": "Band E"},
    {"Employee ID": "BEN0015", "Employee Name": "Olivia Patel", "Plan Tier": "Employee Only", "Dependent Count": 0, "Salary Band": "Band C"},
    {"Employee ID": "BEN0016", "Employee Name": "Priya Quinn", "Plan Tier": "Employee + Spouse", "Dependent Count": 1, "Salary Band": "Band B"},
    {"Employee ID": "BEN0017", "Employee Name": "Rafael Singh", "Plan Tier": "Employee + Children", "Dependent Count": 2, "Salary Band": "Band D"},
    {"Employee ID": "BEN0018", "Employee Name": "Sofia Turner", "Plan Tier": "Family", "Dependent Count": 2, "Salary Band": "Band C"},
]


def build_current_rows():
    current_rows = deepcopy(ARCHIVED_ROWS)
    current_rows = [row for row in current_rows if row["Employee ID"] not in {"BEN0005", "BEN0012"}]

    updates = {
        "BEN0002": {"Plan Tier": "Employee + Spouse"},
        "BEN0003": {"Dependent Count": 1},
        "BEN0004": {"Salary Band": "Band C"},
        "BEN0007": {"Plan Tier": "Family"},
        "BEN0008": {"Dependent Count": 3},
        "BEN0010": {"Salary Band": "Band E"},
        "BEN0014": {"Plan Tier": "Employee Only"},
        "BEN0016": {"Dependent Count": 0},
        "BEN0018": {"Salary Band": "Band B"},
    }

    for row in current_rows:
        row.update(updates.get(row["Employee ID"], {}))

    return current_rows


def write_excel(rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Enrollment"
    sheet.append(HEADERS)
    for row in rows:
        sheet.append([row[column] for column in HEADERS])

    for column_letter, width in {"A": 14, "B": 20, "C": 24, "D": 18, "E": 14}.items():
        sheet.column_dimensions[column_letter].width = width

    workbook.save(XLSX_PATH)


def table_data(chunk):
    return [HEADERS] + [[row[column] for column in HEADERS] for row in chunk]


def write_pdf(rows):
    doc = SimpleDocTemplate(
        PDF_PATH,
        pagesize=landscape(letter),
        leftMargin=24,
        rightMargin=24,
        topMargin=30,
        bottomMargin=24,
    )
    styles = getSampleStyleSheet()
    elements = []

    rows_per_page = 6
    for start in range(0, len(rows), rows_per_page):
        chunk = rows[start : start + rows_per_page]
        page_index = start // rows_per_page + 1
        elements.append(Paragraph(f"Archived Benefits Census Snapshot - Page {page_index}", styles["Heading2"]))
        elements.append(Spacer(1, 10))

        table = Table(
            table_data(chunk),
            colWidths=[90, 150, 165, 110, 90],
            repeatRows=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EAF4")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FA")]),
                ]
            )
        )
        elements.append(table)

        if start + rows_per_page < len(rows):
            elements.append(PageBreak())

    doc.build(elements)


def main():
    current_rows = build_current_rows()
    write_excel(current_rows)
    write_pdf(ARCHIVED_ROWS)


if __name__ == "__main__":
    main()
