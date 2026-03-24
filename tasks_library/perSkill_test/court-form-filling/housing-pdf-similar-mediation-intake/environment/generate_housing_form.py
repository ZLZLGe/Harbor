#!/usr/bin/env python3

import sys

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def label(pdf, x, y, text, size=9):
    pdf.setFont("Helvetica", size)
    pdf.drawString(x, y, text)


def text_field(form, name, x, y, width, height=18):
    form.textfield(
        name=name,
        x=x,
        y=y,
        width=width,
        height=height,
        borderStyle="inset",
        forceBorder=True,
        fontName="Helvetica",
        fontSize=9,
    )


def checkbox(form, name, x, y):
    form.checkbox(
        name=name,
        x=x,
        y=y,
        size=12,
        buttonStyle="check",
        borderWidth=1,
        forceBorder=True,
        checked=False,
    )


def build_form(output_path):
    pdf = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    form = pdf.acroForm

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, height - 40, "Housing Mediation Intake Form")
    pdf.setFont("Helvetica", 9)
    pdf.drawString(40, height - 58, "Complete only the fields that apply. Staff section is for office use only.")

    y = height - 90
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y, "1. Applicant")
    y -= 24

    label(pdf, 40, y + 5, "Name")
    text_field(form, "applicant_name", 150, y, 220)
    label(pdf, 390, y + 5, "Role")
    checkbox(form, "applicant_role_tenant", 430, y + 1)
    label(pdf, 446, y + 5, "Tenant")
    checkbox(form, "applicant_role_landlord", 500, y + 1)
    label(pdf, 516, y + 5, "Landlord")

    y -= 30
    label(pdf, 40, y + 5, "Mailing address")
    text_field(form, "applicant_address", 150, y, 390)

    y -= 30
    label(pdf, 40, y + 5, "City")
    text_field(form, "applicant_city", 150, y, 145)
    label(pdf, 310, y + 5, "State")
    text_field(form, "applicant_state", 360, y, 45)
    label(pdf, 420, y + 5, "ZIP")
    text_field(form, "applicant_zip", 450, y, 90)

    y -= 30
    label(pdf, 40, y + 5, "Phone")
    text_field(form, "applicant_phone", 150, y, 145)
    label(pdf, 310, y + 5, "Email")
    text_field(form, "applicant_email", 360, y, 180)

    y -= 42
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y + 12, "2. Respondent")

    y -= 18
    label(pdf, 40, y + 5, "Name")
    text_field(form, "respondent_name", 150, y, 220)
    label(pdf, 390, y + 5, "Role")
    checkbox(form, "respondent_role_tenant", 430, y + 1)
    label(pdf, 446, y + 5, "Tenant")
    checkbox(form, "respondent_role_landlord", 500, y + 1)
    label(pdf, 516, y + 5, "Landlord")

    y -= 30
    label(pdf, 40, y + 5, "Phone")
    text_field(form, "respondent_phone", 150, y, 145)
    label(pdf, 310, y + 5, "Email")
    text_field(form, "respondent_email", 360, y, 180)

    y -= 42
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y + 12, "3. Rental Property")

    y -= 18
    label(pdf, 40, y + 5, "Property address")
    text_field(form, "rental_address", 150, y, 390)

    y -= 30
    label(pdf, 40, y + 5, "City")
    text_field(form, "rental_city", 150, y, 145)
    label(pdf, 310, y + 5, "State")
    text_field(form, "rental_state", 360, y, 45)
    label(pdf, 420, y + 5, "ZIP")
    text_field(form, "rental_zip", 450, y, 90)

    y -= 30
    label(pdf, 40, y + 5, "Lease start")
    text_field(form, "lease_start", 150, y, 145)
    label(pdf, 310, y + 5, "Move-out date")
    text_field(form, "move_out_date", 410, y, 130)

    y -= 42
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y + 12, "4. For Office Use Only")

    y -= 18
    label(pdf, 40, y + 5, "Case number")
    text_field(form, "staff_case_number", 150, y, 145)
    label(pdf, 310, y + 5, "Intake date")
    text_field(form, "staff_intake_date", 410, y, 130)

    y -= 30
    label(pdf, 40, y + 5, "Screened by staff")
    checkbox(form, "staff_screened", 150, y + 1)
    label(pdf, 170, y + 5, "Reviewed")

    y -= 30
    label(pdf, 40, y + 5, "Staff notes")
    text_field(form, "staff_notes", 150, y, 390)

    pdf.showPage()

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, height - 40, "Housing Mediation Intake Form")
    pdf.setFont("Helvetica", 9)
    pdf.drawString(40, height - 58, "Describe the dispute and the requested outcome.")

    y = height - 95
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y, "5. Dispute Details")
    y -= 24

    checkbox(form, "issue_security_deposit", 40, y + 1)
    label(pdf, 58, y + 5, "Security deposit")
    checkbox(form, "issue_repair_bill", 190, y + 1)
    label(pdf, 208, y + 5, "Repair charges")
    checkbox(form, "issue_unpaid_rent", 340, y + 1)
    label(pdf, 358, y + 5, "Unpaid rent")

    y -= 30
    label(pdf, 40, y + 5, "Deposit paid")
    text_field(form, "deposit_paid", 150, y, 90)
    label(pdf, 260, y + 5, "Returned")
    text_field(form, "amount_already_returned", 320, y, 90)
    label(pdf, 430, y + 5, "Requested")
    text_field(form, "amount_requested", 490, y, 50)

    y -= 30
    label(pdf, 40, y + 5, "Dispute start")
    text_field(form, "dispute_start", 150, y, 120)
    label(pdf, 290, y + 5, "Dispute end")
    text_field(form, "dispute_end", 390, y, 150)

    y -= 30
    label(pdf, 40, y + 5, "Attempts to resolve")
    text_field(form, "prior_attempts", 150, y, 390)

    y -= 42
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y + 12, "6. Mediation Preferences")

    y -= 18
    label(pdf, 40, y + 5, "Preferred contact")
    checkbox(form, "preferred_contact_email", 150, y + 1)
    label(pdf, 168, y + 5, "Email")
    checkbox(form, "preferred_contact_phone", 230, y + 1)
    label(pdf, 248, y + 5, "Phone")

    y -= 30
    label(pdf, 40, y + 5, "Availability")
    text_field(form, "availability", 150, y, 390)

    y -= 30
    label(pdf, 40, y + 5, "Requested outcome")
    text_field(form, "requested_outcome", 150, y, 390)

    y -= 42
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y + 12, "7. Signature")

    y -= 18
    label(pdf, 40, y + 5, "Signature name")
    text_field(form, "signature_name", 150, y, 220)
    label(pdf, 390, y + 5, "Date")
    text_field(form, "signature_date", 430, y, 110)

    pdf.save()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: generate_housing_form.py OUTPUT_PDF")
    build_form(sys.argv[1])
