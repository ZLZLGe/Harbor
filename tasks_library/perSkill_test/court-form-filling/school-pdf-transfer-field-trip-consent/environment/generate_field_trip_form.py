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
    pdf.drawString(40, height - 40, "Field Trip Parent Consent Form")
    pdf.setFont("Helvetica", 9)
    pdf.drawString(40, height - 58, "Complete only the fields supported by the registration packet.")

    y = height - 92
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y, "1. Student")

    y -= 24
    label(pdf, 40, y + 5, "Student name")
    text_field(form, "student_name", 150, y, 220)
    label(pdf, 390, y + 5, "Student ID")
    text_field(form, "student_id", 460, y, 80)

    y -= 30
    label(pdf, 40, y + 5, "Grade")
    text_field(form, "grade", 110, y, 45)
    label(pdf, 180, y + 5, "Homeroom")
    text_field(form, "homeroom", 255, y, 95)
    label(pdf, 370, y + 5, "Birth date")
    text_field(form, "birth_date", 435, y, 105)

    y -= 42
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y + 12, "2. Trip Details")

    y -= 18
    label(pdf, 40, y + 5, "Program")
    text_field(form, "trip_name", 150, y, 390)

    y -= 30
    label(pdf, 40, y + 5, "Destination")
    text_field(form, "destination", 150, y, 390)

    y -= 30
    label(pdf, 40, y + 5, "Trip date")
    text_field(form, "trip_date", 150, y, 100)
    label(pdf, 270, y + 5, "Depart")
    text_field(form, "departure_time", 320, y, 70)
    label(pdf, 410, y + 5, "Return")
    text_field(form, "return_time", 460, y, 80)

    y -= 30
    label(pdf, 40, y + 5, "Transportation")
    text_field(form, "transportation", 150, y, 390)

    y -= 42
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y + 12, "3. Parent or Guardian")

    y -= 18
    label(pdf, 40, y + 5, "Name")
    text_field(form, "guardian_name", 150, y, 180)
    label(pdf, 350, y + 5, "Relationship")
    text_field(form, "guardian_relationship", 430, y, 110)

    y -= 30
    label(pdf, 40, y + 5, "Phone")
    text_field(form, "guardian_phone", 150, y, 140)
    label(pdf, 310, y + 5, "Email")
    text_field(form, "guardian_email", 360, y, 180)

    pdf.showPage()

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, height - 40, "Field Trip Parent Consent Form")
    pdf.setFont("Helvetica", 9)
    pdf.drawString(40, height - 58, "Health, authorization, and signature.")

    y = height - 92
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y, "4. Emergency Contact")

    y -= 24
    label(pdf, 40, y + 5, "Name")
    text_field(form, "emergency_name", 150, y, 180)
    label(pdf, 350, y + 5, "Relationship")
    text_field(form, "emergency_relationship", 430, y, 110)

    y -= 30
    label(pdf, 40, y + 5, "Day phone")
    text_field(form, "emergency_phone_day", 150, y, 140)
    label(pdf, 310, y + 5, "Evening phone")
    text_field(form, "emergency_phone_evening", 410, y, 130)

    y -= 42
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y + 12, "5. Health Information")

    y -= 18
    label(pdf, 40, y + 5, "Allergies")
    text_field(form, "allergies", 150, y, 390)

    y -= 30
    label(pdf, 40, y + 5, "Medications")
    text_field(form, "medications", 150, y, 390)

    y -= 30
    label(pdf, 40, y + 5, "Physician")
    text_field(form, "physician_name", 150, y, 180)
    label(pdf, 350, y + 5, "Phone")
    text_field(form, "physician_phone", 430, y, 110)

    y -= 42
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y + 12, "6. Authorizations")

    y -= 22
    label(pdf, 40, y + 5, "Emergency medical treatment")
    checkbox(form, "medical_consent_yes", 250, y + 1)
    label(pdf, 268, y + 5, "Yes")
    checkbox(form, "medical_consent_no", 320, y + 1)
    label(pdf, 338, y + 5, "No")

    y -= 28
    label(pdf, 40, y + 5, "School may give non-prescription medication")
    checkbox(form, "otc_meds_yes", 250, y + 1)
    label(pdf, 268, y + 5, "Yes")
    checkbox(form, "otc_meds_no", 320, y + 1)
    label(pdf, 338, y + 5, "No")

    y -= 28
    label(pdf, 40, y + 5, "Photo/video release for school use")
    checkbox(form, "photo_release_yes", 250, y + 1)
    label(pdf, 268, y + 5, "Yes")
    checkbox(form, "photo_release_no", 320, y + 1)
    label(pdf, 338, y + 5, "No")

    y -= 28
    label(pdf, 40, y + 5, "Student may self-carry epinephrine")
    checkbox(form, "self_carry_epipen_yes", 250, y + 1)
    label(pdf, 268, y + 5, "Yes")
    checkbox(form, "self_carry_epipen_no", 320, y + 1)
    label(pdf, 338, y + 5, "No")

    y -= 42
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y + 12, "7. Pickup Authorization")

    y -= 18
    label(pdf, 40, y + 5, "Authorized adult")
    text_field(form, "pickup_name", 150, y, 180)
    label(pdf, 350, y + 5, "Phone")
    text_field(form, "pickup_phone", 430, y, 110)

    y -= 42
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y + 12, "8. School Use Only")

    y -= 18
    label(pdf, 40, y + 5, "Received date")
    text_field(form, "school_receipt_date", 150, y, 120)
    label(pdf, 300, y + 5, "Nurse reviewed by")
    text_field(form, "nurse_reviewed_by", 410, y, 130)

    y -= 30
    label(pdf, 40, y + 5, "Volunteer chaperone")
    text_field(form, "volunteer_chaperone", 150, y, 180)
    label(pdf, 350, y + 5, "Teacher notes")
    text_field(form, "teacher_notes", 430, y, 110)

    y -= 42
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y + 12, "9. Signature")

    y -= 18
    label(pdf, 40, y + 5, "Parent/guardian signature")
    text_field(form, "signature_name", 190, y, 180)
    label(pdf, 390, y + 5, "Date")
    text_field(form, "signature_date", 430, y, 110)

    pdf.save()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: generate_field_trip_form.py OUTPUT_PDF")
    build_form(sys.argv[1])
