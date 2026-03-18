from datetime import date, datetime

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


PDF_PATH = "/root/archived_training_rosters.pdf"
XLSX_PATH = "/root/current_training_compliance_tracker.xlsx"

PDF_HEADERS = [
    "Employee ID",
    "Employee Name",
    "Course Code",
    "Archived Status",
    "Renewal Due",
]

ARCHIVED_ROWS = [
    {"Employee ID": "EMP3001", "Employee Name": "Alice Ng", "Course Code": "CPR-101", "Archived Status": "Complete", "Renewal Due": "15-Apr-2026"},
    {"Employee ID": "EMP3002", "Employee Name": "Ben Ortiz", "Course Code": "HAZ-201", "Archived Status": "Complete", "Renewal Due": "01-Jun-2026"},
    {"Employee ID": "EMP3003", "Employee Name": "Carla Ruiz", "Course Code": "FIRE-150", "Archived Status": "Grace", "Renewal Due": "31-Mar-2026"},
    {"Employee ID": "EMP3004", "Employee Name": "Dina Shah", "Course Code": "FORK-110", "Archived Status": "Complete", "Renewal Due": "30-Sep-2026"},
    {"Employee ID": "EMP3005", "Employee Name": "Eli Turner", "Course Code": "DATA-SEC", "Archived Status": "Complete", "Renewal Due": "15-Aug-2026"},
    {"Employee ID": "EMP3006", "Employee Name": "Farah Ali", "Course Code": "CPR-101", "Archived Status": "Expired", "Renewal Due": "01-Dec-2025"},
    {"Employee ID": "EMP3007", "Employee Name": "Gus Meyer", "Course Code": "HAZ-201", "Archived Status": "Complete", "Renewal Due": "20-Jul-2026"},
    {"Employee ID": "EMP3008", "Employee Name": "Hana Park", "Course Code": "FIRE-150", "Archived Status": "Complete", "Renewal Due": "10-May-2026"},
    {"Employee ID": "EMP3009", "Employee Name": "Ivan Soto", "Course Code": "CPR-101", "Archived Status": "Grace", "Renewal Due": "28-Feb-2026"},
    {"Employee ID": "EMP3010", "Employee Name": "Jia Lin", "Course Code": "DATA-SEC", "Archived Status": "Complete", "Renewal Due": "11-Nov-2026"},
    {"Employee ID": "EMP3011", "Employee Name": "Kyle West", "Course Code": "FORK-110", "Archived Status": "Complete", "Renewal Due": "05-Oct-2026"},
    {"Employee ID": "EMP3012", "Employee Name": "Lana Brooks", "Course Code": "FIRE-150", "Archived Status": "Complete", "Renewal Due": "19-Dec-2026"},
]

TRACKER_HEADERS = [
    "Employee ID",
    "Employee Name",
    "Course Code",
    "Tracker Status",
    "Renewal Date",
]

TRACKER_ROWS = [
    {"Employee ID": "EMP3001", "Employee Name": "Alice Ng", "Course Code": "CPR-101", "Tracker Status": "Green", "Renewal Date": date(2026, 4, 15)},
    {"Employee ID": "EMP3002", "Employee Name": "Ben Ortiz", "Course Code": "HAZ-201", "Tracker Status": "Amber", "Renewal Date": date(2026, 6, 1)},
    {"Employee ID": "EMP3004", "Employee Name": "Dina Shah", "Course Code": "FORK-110", "Tracker Status": "Green", "Renewal Date": date(2026, 10, 31)},
    {"Employee ID": "EMP3005", "Employee Name": "Eli Turner", "Course Code": "DATA-SEC", "Tracker Status": "Green", "Renewal Date": date(2026, 8, 15)},
    {"Employee ID": "EMP3006", "Employee Name": "Farah Ali", "Course Code": "CPR-101", "Tracker Status": "Red", "Renewal Date": date(2025, 12, 1)},
    {"Employee ID": "EMP3007", "Employee Name": "Gus Meyer", "Course Code": "HAZ-201", "Tracker Status": "Red", "Renewal Date": date(2026, 7, 20)},
    {"Employee ID": "EMP3008", "Employee Name": "Hana Park", "Course Code": "FIRE-150", "Tracker Status": "Green", "Renewal Date": date(2026, 6, 10)},
    {"Employee ID": "EMP3009", "Employee Name": "Ivan Soto", "Course Code": "CPR-101", "Tracker Status": "Green", "Renewal Date": date(2026, 2, 28)},
    {"Employee ID": "EMP3010", "Employee Name": "Jia Lin", "Course Code": "DATA-SEC", "Tracker Status": "Amber", "Renewal Date": date(2026, 11, 11)},
    {"Employee ID": "EMP3011", "Employee Name": "Kyle West", "Course Code": "FORK-110", "Tracker Status": "Green", "Renewal Date": date(2026, 10, 5)},
    {"Employee ID": "EMP3013", "Employee Name": "Mona Dean", "Course Code": "HAZ-201", "Tracker Status": "Green", "Renewal Date": date(2026, 8, 8)},
]

STATUS_GUIDE_ROWS = [
    {"Tracker Status": "Green", "Normalized Status": "Current", "Severity Rank": 3},
    {"Tracker Status": "Amber", "Normalized Status": "Grace Period", "Severity Rank": 2},
    {"Tracker Status": "Red", "Normalized Status": "Expired", "Severity Rank": 1},
]


def write_workbook():
    workbook = Workbook()

    tracker_sheet = workbook.active
    tracker_sheet.title = "Compliance Tracker"
    tracker_sheet.append(TRACKER_HEADERS)
    for row in TRACKER_ROWS:
        tracker_sheet.append([row[column] for column in TRACKER_HEADERS])

    for cell in tracker_sheet["E"][1:]:
        cell.number_format = "yyyy-mm-dd"

    guide_sheet = workbook.create_sheet("Status Guide")
    guide_headers = ["Tracker Status", "Normalized Status", "Severity Rank"]
    guide_sheet.append(guide_headers)
    for row in STATUS_GUIDE_ROWS:
        guide_sheet.append([row[column] for column in guide_headers])

    for sheet in workbook.worksheets:
        for column_letter in ["A", "B", "C", "D", "E"]:
            sheet.column_dimensions[column_letter].width = 20

    workbook.save(XLSX_PATH)


def pdf_table_data(chunk):
    return [PDF_HEADERS] + [[row[column] for column in PDF_HEADERS] for row in chunk]


def write_pdf():
    document = SimpleDocTemplate(
        PDF_PATH,
        pagesize=landscape(letter),
        leftMargin=22,
        rightMargin=22,
        topMargin=28,
        bottomMargin=24,
    )
    styles = getSampleStyleSheet()
    elements = []

    rows_per_page = 4
    for start in range(0, len(ARCHIVED_ROWS), rows_per_page):
        page_number = start // rows_per_page + 1
        chunk = ARCHIVED_ROWS[start : start + rows_per_page]
        generated_at = datetime(2026, 3, 1, 9, 0).strftime("%Y-%m-%d %H:%M")

        elements.append(Paragraph(f"Archived Training Completion Roster - Page {page_number}", styles["Heading2"]))
        elements.append(Paragraph(f"Archive export generated {generated_at}", styles["BodyText"]))
        elements.append(Spacer(1, 10))

        table = Table(
            pdf_table_data(chunk),
            colWidths=[86, 116, 90, 92, 92],
            repeatRows=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9E8F5")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FA")]),
                ]
            )
        )
        elements.append(table)

        if start + rows_per_page < len(ARCHIVED_ROWS):
            elements.append(PageBreak())

    document.build(elements)


def main():
    write_workbook()
    write_pdf()


if __name__ == "__main__":
    main()
