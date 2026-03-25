#!/usr/bin/env python3

from pathlib import Path
import sys


PAGE_WIDTH = 612
PAGE_HEIGHT = 792


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def text_line(x: int, y: int, size: int, text: str) -> str:
    return f"BT /F1 {size} Tf {x} {y} Td ({pdf_escape(text)}) Tj ET"


def rectangle(x: int, y: int, width: int, height: int) -> str:
    return f"{x} {y} {width} {height} re S"


def stream_object(stream_bytes: bytes, extra_dict: str = "") -> bytes:
    dictionary = f"<< /Length {len(stream_bytes)}"
    if extra_dict:
        dictionary += f" {extra_dict}"
    dictionary += " >>"
    return (
        dictionary.encode("ascii")
        + b"\nstream\n"
        + stream_bytes
        + b"\nendstream"
    )


def build_pdf() -> bytes:
    objects: list[bytes] = []

    def add_object(content: str | bytes) -> int:
        if isinstance(content, str):
            content_bytes = content.encode("latin-1")
        else:
            content_bytes = content
        objects.append(content_bytes)
        return len(objects)

    content_parts = [
        "0.2 w",
        text_line(54, 744, 18, "Harbor Family Health"),
        text_line(54, 722, 14, "Outpatient Registration"),
        text_line(54, 698, 9, "Complete the editable fields and keep the form readable by software."),
        text_line(54, 667, 11, "Last Name"),
        rectangle(200, 658, 300, 22),
        text_line(54, 632, 11, "Preferred First Name"),
        rectangle(200, 623, 300, 22),
        text_line(54, 597, 11, "Date of Birth (YYYY-MM-DD)"),
        rectangle(270, 588, 160, 22),
        text_line(54, 562, 11, "Mobile Phone"),
        rectangle(200, 553, 190, 22),
        text_line(54, 527, 11, "Known Allergies"),
        rectangle(200, 518, 300, 22),
        text_line(54, 487, 11, "Visit Type"),
        rectangle(205, 480, 12, 12),
        text_line(223, 483, 10, "New patient"),
        rectangle(340, 480, 12, 12),
        text_line(358, 483, 10, "Follow-up"),
        text_line(54, 442, 11, "Communication"),
        rectangle(255, 435, 12, 12),
        text_line(273, 438, 10, "Text appointment reminders"),
        text_line(54, 412, 11, "Acknowledgement"),
        rectangle(255, 405, 12, 12),
        text_line(273, 408, 10, "Received privacy notice"),
        text_line(54, 368, 9, "Clinic use only: form version HFH-INTAKE-03"),
    ]
    content_stream = "\n".join(content_parts).encode("ascii")

    checkbox_off = b"q 0 0 0 RG 1 w 0.5 0.5 11 11 re S Q"
    checkbox_on = b"q 0 0 0 RG 1 w 0.5 0.5 11 11 re S 2 2 m 10 10 l S 2 10 m 10 2 l S Q"
    radio_off = b"q 0 0 0 RG 1 w 0.5 0.5 11 11 re S Q"
    radio_on = b"q 0 0 0 RG 1 w 0.5 0.5 11 11 re S 3 3 6 6 re f Q"

    add_object("<< /Type /Catalog /Pages 2 0 R /AcroForm 6 0 R >>")
    add_object("<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    add_object(
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Resources << /Font << /F1 4 0 R >> >> "
        "/Contents 5 0 R "
        "/Annots [7 0 R 8 0 R 9 0 R 10 0 R 11 0 R 12 0 R 13 0 R 15 0 R 16 0 R] >>"
    )
    add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    add_object(stream_object(content_stream))
    add_object(
        "<< /Fields [7 0 R 8 0 R 9 0 R 10 0 R 11 0 R 12 0 R 13 0 R 14 0 R] "
        "/NeedAppearances true "
        "/DR << /Font << /Helv 4 0 R >> >> "
        "/DA (/Helv 11 Tf 0 g) >>"
    )
    add_object(
        "<< /Type /Annot /Subtype /Widget /FT /Tx /T (pt_last_name) "
        "/TU (Last Name) /Rect [200 658 500 680] /P 3 0 R "
        "/V () /DV () /DA (/Helv 11 Tf 0 g) "
        "/MK << /BC [0 0 0] /BG [1 1 1] >> >>"
    )
    add_object(
        "<< /Type /Annot /Subtype /Widget /FT /Tx /T (pt_first_name) "
        "/TU (Preferred First Name) /Rect [200 623 500 645] /P 3 0 R "
        "/V () /DV () /DA (/Helv 11 Tf 0 g) "
        "/MK << /BC [0 0 0] /BG [1 1 1] >> >>"
    )
    add_object(
        "<< /Type /Annot /Subtype /Widget /FT /Tx /T (pt_birth_date) "
        "/TU (Date of Birth) /Rect [270 588 430 610] /P 3 0 R "
        "/V () /DV () /DA (/Helv 11 Tf 0 g) "
        "/MK << /BC [0 0 0] /BG [1 1 1] >> >>"
    )
    add_object(
        "<< /Type /Annot /Subtype /Widget /FT /Tx /T (pt_mobile_phone) "
        "/TU (Mobile Phone) /Rect [200 553 390 575] /P 3 0 R "
        "/V () /DV () /DA (/Helv 11 Tf 0 g) "
        "/MK << /BC [0 0 0] /BG [1 1 1] >> >>"
    )
    add_object(
        "<< /Type /Annot /Subtype /Widget /FT /Tx /T (pt_allergies) "
        "/TU (Known Allergies) /Rect [200 518 500 540] /P 3 0 R "
        "/V () /DV () /DA (/Helv 11 Tf 0 g) "
        "/MK << /BC [0 0 0] /BG [1 1 1] >> >>"
    )
    add_object(
        "<< /Type /Annot /Subtype /Widget /FT /Btn /T (cb_sms) "
        "/TU (Text appointment reminders) /Rect [255 435 267 447] /P 3 0 R "
        "/V /Yes /DV /Yes /AS /Yes "
        "/AP << /N << /Off 17 0 R /Yes 18 0 R >> >> >>"
    )
    add_object(
        "<< /Type /Annot /Subtype /Widget /FT /Btn /T (cb_privacy) "
        "/TU (Received privacy notice) /Rect [255 405 267 417] /P 3 0 R "
        "/V /Off /DV /Off /AS /Off "
        "/AP << /N << /Off 17 0 R /Yes 18 0 R >> >> >>"
    )
    add_object(
        "<< /FT /Btn /Ff 32768 /T (visit_type) /TU (Visit Type) "
        "/V /NewPatient /DV /NewPatient /Kids [15 0 R 16 0 R] >>"
    )
    add_object(
        "<< /Type /Annot /Subtype /Widget /Parent 14 0 R /Rect [205 480 217 492] "
        "/P 3 0 R /AS /NewPatient "
        "/AP << /N << /Off 19 0 R /NewPatient 20 0 R >> >> >>"
    )
    add_object(
        "<< /Type /Annot /Subtype /Widget /Parent 14 0 R /Rect [340 480 352 492] "
        "/P 3 0 R /AS /Off "
        "/AP << /N << /Off 19 0 R /FollowUp 20 0 R >> >> >>"
    )
    add_object(stream_object(checkbox_off, "/Type /XObject /Subtype /Form /BBox [0 0 12 12]"))
    add_object(stream_object(checkbox_on, "/Type /XObject /Subtype /Form /BBox [0 0 12 12]"))
    add_object(stream_object(radio_off, "/Type /XObject /Subtype /Form /BBox [0 0 12 12]"))
    add_object(stream_object(radio_on, "/Type /XObject /Subtype /Form /BBox [0 0 12 12]"))

    output = bytearray()
    output.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]

    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii"))
        output.extend(obj)
        if not obj.endswith(b"\n"):
            output.extend(b"\n")
        output.extend(b"endobj\n")

    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(output)


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: create_intake_assets.py [patient_json] [output_form_path]")
        return 1

    patient_json = Path(sys.argv[1])
    output_form = Path(sys.argv[2])

    if not patient_json.exists():
        print(f"Missing patient JSON: {patient_json}")
        return 1

    output_form.write_bytes(build_pdf())
    print(f"Wrote form to {output_form}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
