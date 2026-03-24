from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


REQUEST_PACKET_PATH = "/root/equipment_request_packet.pdf"
FORM_PATH = "/root/equipment_checkout_form.pdf"


def draw_request_packet():
    c = canvas.Canvas(REQUEST_PACKET_PATH, pagesize=letter)
    width, height = letter

    y = height - 54
    c.setFont("Helvetica-Bold", 16)
    c.drawString(54, y, "Equipment Checkout Request Packet")
    y -= 28

    c.setFont("Helvetica", 11)
    lines = [
        "Request ID: ECO-0419",
        "Employee Name: Nora Patel",
        "Employee ID: FO-318",
        "Department: Field Operations",
        "Phone Extension: x4512",
        "Equipment Description: Portable thermal camera kit",
        "Asset Tag: EQ-THERM-204",
        "Serial Number: SN-TC8841",
        "Checkout Date: 2026-04-09",
        "Due Date: 2026-04-16",
        "Primary Use: Transformer yard inspection",
        "Approving Supervisor: Mei Chen",
        "",
        "Use the release checklist on page 2 before issuing the kit.",
    ]
    for line in lines:
        c.drawString(54, y, line)
        y -= 18

    c.showPage()
    y = height - 54
    c.setFont("Helvetica-Bold", 15)
    c.drawString(54, y, "Release Checklist")
    y -= 30
    c.setFont("Helvetica", 11)
    checklist_lines = [
        "Issue Accessories:",
        "- Charger: Yes",
        "- Tripod: Yes",
        "- Carrying Case: No",
        "",
        "Release Checks:",
        "- Equipment inspected and operational: Yes",
        "- Safety briefing completed: Yes",
        "",
        "Pickup Window: 08:30-09:00",
        "Return Location: North cage counter",
    ]
    for line in checklist_lines:
        c.drawString(54, y, line)
        y -= 18

    c.save()


def text_field(form, name, x, y, width, height=20):
    form.textfield(
        name=name,
        tooltip=name,
        x=x,
        y=y,
        width=width,
        height=height,
        borderWidth=1,
        forceBorder=True,
        fontName="Helvetica",
        fontSize=11,
    )


def checkbox(form, name, x, y):
    form.checkbox(
        name=name,
        tooltip=name,
        x=x,
        y=y,
        buttonStyle="check",
        borderWidth=1,
        forceBorder=True,
        checked=False,
    )


def draw_form():
    c = canvas.Canvas(FORM_PATH, pagesize=letter)
    width, height = letter
    form = c.acroForm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(54, height - 50, "Equipment Checkout Form")

    c.setFont("Helvetica", 11)
    c.drawString(54, height - 88, "Employee Name")
    text_field(form, "employee_name", 170, height - 96, 240)

    c.drawString(430, height - 88, "Employee ID")
    text_field(form, "employee_id", 500, height - 96, 58)

    c.drawString(54, height - 124, "Department")
    text_field(form, "department", 170, height - 132, 180)

    c.drawString(370, height - 124, "Phone Extension")
    text_field(form, "phone_extension", 485, height - 132, 73)

    c.drawString(54, height - 160, "Equipment Description")
    text_field(form, "equipment_description", 170, height - 168, 388)

    c.drawString(54, height - 196, "Asset Tag")
    text_field(form, "asset_tag", 170, height - 204, 150)

    c.drawString(340, height - 196, "Serial Number")
    text_field(form, "serial_number", 430, height - 204, 128)

    c.drawString(54, height - 232, "Checkout Date")
    text_field(form, "checkout_date", 170, height - 240, 120)

    c.drawString(330, height - 232, "Due Date")
    text_field(form, "due_date", 430, height - 240, 128)

    c.drawString(54, height - 268, "Primary Use")
    text_field(form, "primary_use", 170, height - 276, 388)

    c.drawString(54, height - 304, "Approving Supervisor")
    text_field(form, "approving_supervisor", 170, height - 312, 240)

    c.setFont("Helvetica-Bold", 12)
    c.drawString(54, height - 356, "Accessories")
    c.setFont("Helvetica", 11)

    checkbox(form, "accessory_charger", 170, height - 367)
    c.drawString(190, height - 356, "Charger")

    checkbox(form, "accessory_tripod", 290, height - 367)
    c.drawString(310, height - 356, "Tripod")

    checkbox(form, "accessory_case", 400, height - 367)
    c.drawString(420, height - 356, "Carrying Case")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(54, height - 406, "Release Checks")
    c.setFont("Helvetica", 11)

    checkbox(form, "inspected_operational", 170, height - 417)
    c.drawString(190, height - 406, "Inspected and operational")

    checkbox(form, "safety_briefing_completed", 400, height - 417)
    c.drawString(420, height - 406, "Safety briefing completed")

    c.save()


if __name__ == "__main__":
    draw_request_packet()
    draw_form()
