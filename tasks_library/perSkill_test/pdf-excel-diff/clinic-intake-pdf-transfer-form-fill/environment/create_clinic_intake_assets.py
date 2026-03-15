from pathlib import Path

from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


OUTPUT_PDF = Path("/root/clinic_intake_form.pdf")


def draw_label(pdf, label, x, y):
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(x, y, label)


def add_text_field(form, name, x, y, width, height=20):
    form.textfield(
        name=name,
        tooltip=name,
        x=x,
        y=y,
        width=width,
        height=height,
        borderStyle="underlined",
        borderWidth=1,
        borderColor=black,
        fillColor=white,
        textColor=black,
        forceBorder=True,
        fontName="Helvetica",
        fontSize=10,
    )


def add_checkbox(form, name, x, y, size=14):
    form.checkbox(
        name=name,
        tooltip=name,
        x=x,
        y=y,
        size=size,
        buttonStyle="check",
        borderWidth=1,
        borderColor=black,
        fillColor=white,
        textColor=black,
        checked=False,
        forceBorder=True,
    )


def build_pdf():
    pdf = canvas.Canvas(str(OUTPUT_PDF), pagesize=letter)
    width, height = letter
    form = pdf.acroForm

    pdf.setTitle("Hospital Intake Form")
    pdf.setStrokeColor(HexColor("#1F4E79"))
    pdf.setLineWidth(2)
    pdf.line(40, height - 58, width - 40, height - 58)

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(40, height - 42, "Harbor Community Hospital")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(40, height - 72, "Admission Intake Form")

    rows = [
        ("Patient Name", "patient_name", 40, 665, 360),
        ("Date of Birth", "date_of_birth", 420, 665, 150),
        ("Medical Record Number", "medical_record_number", 40, 620, 220),
        ("Admission Date", "admission_date", 290, 620, 130),
        ("Room Number", "room_number", 440, 620, 130),
        ("Attending Physician", "attending_physician", 40, 575, 530),
        ("Chief Complaint", "chief_complaint", 40, 530, 530),
        ("Allergies", "allergies", 40, 485, 530),
        ("Current Medications", "current_medications", 40, 440, 530),
        ("Preferred Language", "preferred_language", 40, 395, 200),
        ("Code Status", "code_status", 270, 395, 140),
        ("Insurance Provider", "insurance_provider", 40, 350, 300),
        ("Policy Number", "policy_number", 360, 350, 210),
        ("Emergency Contact", "emergency_contact_name", 40, 305, 300),
        ("Emergency Phone", "emergency_contact_phone", 360, 305, 210),
    ]

    for label, name, x, y, field_width in rows:
        draw_label(pdf, label, x, y + 24)
        add_text_field(form, name, x, y, field_width)

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, 250, "Clinical Flags")
    pdf.setFont("Helvetica", 10)

    draw_label(pdf, "Interpreter Required", 65, 218)
    add_checkbox(form, "interpreter_required", 42, 206)

    draw_label(pdf, "Droplet Isolation", 255, 218)
    add_checkbox(form, "droplet_isolation", 232, 206)

    draw_label(pdf, "Fall Risk", 430, 218)
    add_checkbox(form, "fall_risk", 407, 206)

    pdf.setFont("Helvetica-Oblique", 9)
    pdf.setFillColor(HexColor("#555555"))
    pdf.drawString(40, 176, "Complete all applicable fields before finalizing the admission packet.")

    pdf.save()


if __name__ == "__main__":
    build_pdf()
