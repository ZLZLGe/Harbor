import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


ASSETS_DIR = Path("/tmp/build_assets")
PROFILE_SOURCE = ASSETS_DIR / "employee_profile.json"
PROFILE_TARGET = Path("/root/employee_profile.json")
PDF_TARGET = Path("/root/benefits_enrollment_packet.pdf")


def text_field(pdf, form, label, name, x, y, width, height=20):
    pdf.setFont("Helvetica", 10)
    pdf.drawString(x, y + 6, label)
    form.textfield(
        name=name,
        x=x + 118,
        y=y - 2,
        width=width,
        height=height,
        borderStyle="inset",
        borderWidth=1,
        forceBorder=True,
        textColor=colors.black,
        borderColor=colors.HexColor("#5F6B73"),
        fillColor=colors.white,
        fontName="Helvetica",
        fontSize=10,
    )


def radio_group(pdf, form, label, name, options, x, y):
    pdf.setFont("Helvetica", 10)
    pdf.drawString(x, y + 4, label)
    offset_x = x + 125
    for value, option_label in options:
        form.radio(
            name=name,
            value=value,
            selected=False,
            x=offset_x,
            y=y - 3,
            buttonStyle="circle",
            borderStyle="solid",
            borderWidth=1,
            size=14,
        )
        pdf.drawString(offset_x + 20, y + 1, option_label)
        offset_x += 112


def checkbox(pdf, form, label, name, x, y):
    pdf.setFont("Helvetica", 10)
    pdf.drawString(x, y + 4, label)
    form.checkbox(
        name=name,
        x=x + 125,
        y=y - 3,
        size=14,
        checked=False,
        buttonStyle="check",
        borderStyle="solid",
        borderWidth=1,
        borderColor=colors.black,
        fillColor=colors.white,
        textColor=colors.black,
        forceBorder=True,
    )


def page_footer(pdf, page_number):
    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(colors.HexColor("#5F6B73"))
    pdf.drawRightString(575, 24, f"Page {page_number} of 2")
    pdf.setFillColor(colors.black)


def build_packet():
    pdf = canvas.Canvas(str(PDF_TARGET), pagesize=letter)
    form = pdf.acroForm
    width, height = letter

    pdf.setTitle("Benefits Enrollment Packet")
    pdf.setAuthor("OpenAI Codex")

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(40, height - 44, "Harbor Benefits Enrollment Packet")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, height - 62, "Complete all sections and return the finished packet to HR.")

    pdf.setStrokeColor(colors.HexColor("#B9C7CF"))
    pdf.line(40, height - 72, width - 40, height - 72)
    pdf.setStrokeColor(colors.black)

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(40, height - 100, "Employee Information")

    y = height - 132
    text_field(pdf, form, "Employee Name", "worker_full", 40, y, 240)
    y -= 34
    text_field(pdf, form, "Employee ID", "worker_id", 40, y, 150)
    y -= 34
    text_field(pdf, form, "Department", "org_unit", 40, y, 190)
    y -= 34
    text_field(pdf, form, "Work Email", "mail_box", 40, y, 260)
    y -= 34
    text_field(pdf, form, "Phone", "call_back", 40, y, 160)
    y -= 34
    text_field(pdf, form, "Home Address", "street_box", 40, y, 320)
    y -= 34
    text_field(pdf, form, "Hire Date", "hire_box", 40, y, 120)

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, 208, "Instructions")
    pdf.setFont("Helvetica", 10)
    instructions = [
        "Use this packet to record the employee's medical, dental, and reimbursement elections.",
        "Only the first two listed dependents should appear in this form.",
        "Amounts in the FSA section should be entered as whole-dollar elections.",
    ]
    y_text = 188
    for line in instructions:
        pdf.drawString(52, y_text, f"- {line}")
        y_text -= 16

    page_footer(pdf, 1)
    pdf.showPage()

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(40, height - 44, "Benefits Elections")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, height - 62, "Select one option in each section unless the packet states otherwise.")
    pdf.setStrokeColor(colors.HexColor("#B9C7CF"))
    pdf.line(40, height - 72, width - 40, height - 72)
    pdf.setStrokeColor(colors.black)

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(40, height - 100, "Plan Elections")
    radio_group(
        pdf,
        form,
        "Medical Plan",
        "med_plan",
        [
            ("bronze", "Bronze HSA"),
            ("ppo", "PPO Plus"),
            ("epo", "EPO Saver"),
        ],
        40,
        height - 132,
    )
    radio_group(
        pdf,
        form,
        "Coverage Tier",
        "coverage_level",
        [
            ("employee_only", "Employee Only"),
            ("employee_spouse", "Employee + Spouse"),
            ("family", "Family"),
        ],
        40,
        height - 168,
    )
    radio_group(
        pdf,
        form,
        "Dental Option",
        "dental_level",
        [
            ("basic", "Basic Dental"),
            ("enhanced", "Enhanced Dental"),
            ("waive", "Waive Dental"),
        ],
        40,
        height - 204,
    )
    checkbox(pdf, form, "Vision Enrollment", "vision_opt_in", 40, height - 240)
    radio_group(
        pdf,
        form,
        "Tobacco Use",
        "tobacco_state",
        [
            ("yes", "Yes"),
            ("no", "No"),
        ],
        40,
        height - 276,
    )

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(40, height - 322, "Flexible Spending Elections")
    text_field(pdf, form, "Healthcare FSA", "fsa_health", 40, height - 352, 100)
    text_field(pdf, form, "Dependent Care FSA", "fsa_family", 40, height - 386, 100)

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(40, height - 428, "Dependents")
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(40, height - 448, "Name")
    pdf.drawString(265, height - 448, "Relationship")
    pdf.drawString(420, height - 448, "Date of Birth")
    form.textfield(name="dep_a_name", x=40, y=height - 474, width=200, height=20, borderStyle="inset", forceBorder=True, fontSize=10)
    form.textfield(name="dep_a_relation", x=265, y=height - 474, width=120, height=20, borderStyle="inset", forceBorder=True, fontSize=10)
    form.textfield(name="dep_a_dob", x=420, y=height - 474, width=120, height=20, borderStyle="inset", forceBorder=True, fontSize=10)
    form.textfield(name="dep_b_name", x=40, y=height - 506, width=200, height=20, borderStyle="inset", forceBorder=True, fontSize=10)
    form.textfield(name="dep_b_relation", x=265, y=height - 506, width=120, height=20, borderStyle="inset", forceBorder=True, fontSize=10)
    form.textfield(name="dep_b_dob", x=420, y=height - 506, width=120, height=20, borderStyle="inset", forceBorder=True, fontSize=10)

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(40, 100, "Employee Signature")
    form.textfield(name="sign_name", x=40, y=70, width=220, height=20, borderStyle="inset", forceBorder=True, fontSize=10)
    form.textfield(name="sign_date", x=310, y=70, width=120, height=20, borderStyle="inset", forceBorder=True, fontSize=10)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, 58, "Signature")
    pdf.drawString(310, 58, "Date")

    page_footer(pdf, 2)
    pdf.save()


def main():
    build_packet()
    with PROFILE_SOURCE.open() as handle:
        profile = json.load(handle)
    with PROFILE_TARGET.open("w") as handle:
        json.dump(profile, handle, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    main()
