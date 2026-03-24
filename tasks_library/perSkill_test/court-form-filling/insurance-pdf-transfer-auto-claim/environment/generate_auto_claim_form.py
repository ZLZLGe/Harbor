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
    pdf.drawString(40, height - 40, "Auto Damage Claim Form")
    pdf.setFont("Helvetica", 9)
    pdf.drawString(40, height - 58, "Complete only the items supported by the claim packet.")

    y = height - 92
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y, "1. Policyholder")

    y -= 24
    label(pdf, 40, y + 5, "Name")
    text_field(form, "policyholder_name", 140, y, 180)
    label(pdf, 340, y + 5, "Policy number")
    text_field(form, "policy_number", 430, y, 110)

    y -= 30
    label(pdf, 40, y + 5, "Phone")
    text_field(form, "contact_phone", 140, y, 140)
    label(pdf, 300, y + 5, "Email")
    text_field(form, "contact_email", 350, y, 190)

    y -= 30
    label(pdf, 40, y + 5, "Mailing address")
    text_field(form, "mailing_address", 140, y, 400)

    y -= 42
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y + 12, "2. Insured Vehicle")

    y -= 18
    label(pdf, 40, y + 5, "Year")
    text_field(form, "vehicle_year", 140, y, 70)
    label(pdf, 230, y + 5, "Make / model")
    text_field(form, "vehicle_make_model", 320, y, 220)

    y -= 30
    label(pdf, 40, y + 5, "License plate")
    text_field(form, "license_plate", 140, y, 140)
    label(pdf, 300, y + 5, "Adjuster claim #")
    text_field(form, "adjuster_claim_number", 400, y, 140)

    y -= 42
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y + 12, "3. Accident Facts")

    y -= 18
    label(pdf, 40, y + 5, "Accident date")
    text_field(form, "accident_date", 140, y, 110)
    label(pdf, 270, y + 5, "Time")
    text_field(form, "accident_time", 320, y, 80)

    y -= 30
    label(pdf, 40, y + 5, "Location")
    text_field(form, "accident_location", 140, y, 400)

    y -= 30
    label(pdf, 40, y + 5, "What happened")
    text_field(form, "accident_summary", 140, y, 400)

    y -= 30
    label(pdf, 40, y + 5, "Other driver name")
    text_field(form, "other_driver_name", 140, y, 180)
    label(pdf, 340, y + 5, "Witness contact")
    text_field(form, "witness_contact", 430, y, 110)

    pdf.showPage()

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, height - 40, "Auto Damage Claim Form")
    pdf.setFont("Helvetica", 9)
    pdf.drawString(40, height - 58, "Damage details and declaration.")

    y = height - 92
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y, "4. Damage Details")

    y -= 24
    label(pdf, 40, y + 5, "Damaged parts")
    text_field(form, "damaged_parts", 140, y, 400)

    y -= 30
    label(pdf, 40, y + 5, "Estimated damage (USD)")
    text_field(form, "estimated_damage", 180, y, 100)

    y -= 42
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y + 12, "5. Claim Checkboxes")

    y -= 18
    checkbox(form, "single_vehicle_incident", 40, y + 1)
    label(pdf, 58, y + 5, "Single-vehicle incident")
    checkbox(form, "insured_driver_responsible", 250, y + 1)
    label(pdf, 268, y + 5, "Insured driver responsible")

    y -= 30
    checkbox(form, "vehicle_drivable", 40, y + 1)
    label(pdf, 58, y + 5, "Vehicle drivable after incident")
    checkbox(form, "vehicle_towed", 250, y + 1)
    label(pdf, 268, y + 5, "Vehicle was towed")

    y -= 30
    checkbox(form, "police_report_filed", 40, y + 1)
    label(pdf, 58, y + 5, "Police report filed")
    checkbox(form, "injuries_reported", 250, y + 1)
    label(pdf, 268, y + 5, "Injuries reported")

    y -= 42
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y + 12, "6. Adjuster Use Only")

    y -= 18
    label(pdf, 40, y + 5, "Adjuster notes")
    text_field(form, "adjuster_notes", 140, y, 400)

    y -= 42
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y + 12, "7. Signature")

    y -= 18
    label(pdf, 40, y + 5, "Signature name")
    text_field(form, "signature_name", 140, y, 180)
    label(pdf, 340, y + 5, "Date")
    text_field(form, "signature_date", 430, y, 110)

    pdf.save()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: generate_auto_claim_form.py OUTPUT_PDF")
    build_form(sys.argv[1])
