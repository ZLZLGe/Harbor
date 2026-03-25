import sys
from pathlib import Path


PAGE_WIDTH = 612
PAGE_HEIGHT = 792


def escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def rect_to_pdf(rect):
    left, bottom, right, top = rect
    return f"[{left} {bottom} {right} {top}]"


def stream_object(commands, extra_dict: str = "") -> bytes:
    body = "\n".join(commands).encode("latin-1")
    prefix = f"<< /Length {len(body)}"
    if extra_dict:
        prefix += f" {extra_dict}"
    prefix += " >>\nstream\n"
    return prefix.encode("latin-1") + body + b"\nendstream"


def add_object(objects, body: bytes) -> int:
    objects.append(body)
    return len(objects)


def text_cmd(text: str, x: int, y: int, size: int = 12) -> str:
    escaped = escape_pdf_text(text)
    return f"BT /F1 {size} Tf 1 0 0 1 {x} {y} Tm ({escaped}) Tj ET"


def rect_cmd(rect) -> str:
    left, bottom, right, top = rect
    return f"{left} {bottom} {right - left} {top - bottom} re S"


def checkbox_appearance(on: bool) -> bytes:
    commands = [
        "0.8 w",
        "1 1 12 12 re S",
    ]
    if on:
        commands.extend(
            [
                "2 2 m 11 11 l S",
                "2 11 m 11 2 l S",
            ]
        )
    return stream_object(commands, "/Type /XObject /Subtype /Form /BBox [0 0 14 14]")


def radio_appearance(on: bool) -> bytes:
    commands = [
        "0.8 w",
        "1 1 12 12 re S",
    ]
    if on:
        commands.append("4 4 6 6 re f")
    return stream_object(commands, "/Type /XObject /Subtype /Form /BBox [0 0 14 14]")


def page_one_stream() -> bytes:
    last_name = (180, 686, 360, 706)
    first_name = (180, 650, 360, 670)
    member_id = (180, 614, 320, 634)
    dob = (180, 578, 300, 598)
    mobile = (180, 542, 330, 562)
    plan = (180, 506, 360, 526)
    commands = [
        "0 0 0 RG",
        "0 0 0 rg",
        text_cmd("Harbor Benefits Enrollment Worksheet", 72, 748, 18),
        text_cmd("Section A: Employee Information", 72, 720, 12),
        text_cmd("Last name", 72, 692, 11),
        rect_cmd(last_name),
        text_cmd("First name", 72, 656, 11),
        rect_cmd(first_name),
        text_cmd("Member ID", 72, 620, 11),
        rect_cmd(member_id),
        text_cmd("Date of birth", 72, 584, 11),
        rect_cmd(dob),
        text_cmd("Mobile phone", 72, 548, 11),
        rect_cmd(mobile),
        text_cmd("Medical plan", 72, 512, 11),
        rect_cmd(plan),
        text_cmd("Coverage tier", 72, 474, 11),
        "180 450 14 14 re S",
        text_cmd("Employee only", 200, 453, 11),
        "305 450 14 14 re S",
        text_cmd("Employee + spouse", 325, 453, 11),
        "470 450 14 14 re S",
        text_cmd("Family", 490, 453, 11),
        text_cmd("Page 1 of 2", 500, 28, 9),
    ]
    return stream_object(commands)


def page_two_stream() -> bytes:
    spouse_name = (180, 686, 360, 706)
    effective = (180, 542, 300, 562)
    commands = [
        "0 0 0 RG",
        "0 0 0 rg",
        text_cmd("Section B: Household and Delivery Preferences", 72, 748, 12),
        text_cmd("Spouse name", 72, 692, 11),
        rect_cmd(spouse_name),
        "180 648 14 14 re S",
        text_cmd("Spouse uses tobacco", 200, 651, 11),
        "180 612 14 14 re S",
        text_cmd("Use paperless EOB notices", 200, 615, 11),
        text_cmd("Coverage effective date", 72, 548, 11),
        rect_cmd(effective),
        text_cmd("Page 2 of 2", 500, 28, 9),
    ]
    return stream_object(commands)


def text_field(name: str, rect, page_id: int) -> bytes:
    return (
        f"<< /Type /Annot /Subtype /Widget /FT /Tx /T ({escape_pdf_text(name)}) "
        f"/Rect {rect_to_pdf(rect)} /P {page_id} 0 R /F 4 "
        f"/DA (/Helv 11 Tf 0 g) /MK << /BC [0.2 0.2 0.2] /BG [1 1 1] >> "
        f"/BS << /W 1 /S /S >> /V () >>"
    ).encode("latin-1")


def choice_field(name: str, rect, page_id: int) -> bytes:
    opt = (
        "[[(HSA_2500) (Core HSA 2500)] "
        "[(PPO_1000) (Balanced PPO 1000)] "
        "[(EPO_500) (CityCare EPO 500)]]"
    )
    return (
        f"<< /Type /Annot /Subtype /Widget /FT /Ch /Ff 131072 /T ({escape_pdf_text(name)}) "
        f"/Rect {rect_to_pdf(rect)} /P {page_id} 0 R /F 4 /DA (/Helv 11 Tf 0 g) "
        f"/Opt {opt} /V (HSA_2500) /DV (HSA_2500) "
        f"/MK << /BC [0.2 0.2 0.2] /BG [1 1 1] >> /BS << /W 1 /S /S >> >>"
    ).encode("latin-1")


def checkbox_field(name: str, rect, page_id: int, checked_name: str, off_id: int, on_id: int) -> bytes:
    return (
        f"<< /Type /Annot /Subtype /Widget /FT /Btn /T ({escape_pdf_text(name)}) "
        f"/Rect {rect_to_pdf(rect)} /P {page_id} 0 R /F 4 /V /Off /AS /Off "
        f"/AP << /N << /Off {off_id} 0 R /{checked_name} {on_id} 0 R >> >> >>"
    ).encode("latin-1")


def radio_parent(name: str, kid_ids) -> bytes:
    kids = " ".join(f"{kid_id} 0 R" for kid_id in kid_ids)
    return (
        f"<< /FT /Btn /Ff 32768 /T ({escape_pdf_text(name)}) "
        f"/Kids [{kids}] /V /Off >>"
    ).encode("latin-1")


def radio_kid(parent_id: int, rect, page_id: int, on_name: str, off_id: int, on_id: int) -> bytes:
    return (
        f"<< /Type /Annot /Subtype /Widget /Parent {parent_id} 0 R "
        f"/Rect {rect_to_pdf(rect)} /P {page_id} 0 R /F 4 /AS /Off "
        f"/AP << /N << /Off {off_id} 0 R /{on_name} {on_id} 0 R >> >> >>"
    ).encode("latin-1")


def build_pdf() -> bytes:
    objects = []

    catalog_id = add_object(objects, b"")
    pages_id = add_object(objects, b"")
    font_id = add_object(objects, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    acroform_id = add_object(objects, b"")

    page1_content_id = add_object(objects, page_one_stream())
    page1_id = add_object(objects, b"")
    page2_content_id = add_object(objects, page_two_stream())
    page2_id = add_object(objects, b"")

    checkbox_off_id = add_object(objects, checkbox_appearance(False))
    checkbox_on_id = add_object(objects, checkbox_appearance(True))
    radio_off_id = add_object(objects, radio_appearance(False))
    radio_on_id = add_object(objects, radio_appearance(True))

    field_ids = []

    last_name_id = add_object(objects, text_field("subscr.ln", (180, 686, 360, 706), page1_id))
    field_ids.append(last_name_id)
    first_name_id = add_object(objects, text_field("subscr.fn", (180, 650, 360, 670), page1_id))
    field_ids.append(first_name_id)
    member_id_id = add_object(objects, text_field("member.id_4a", (180, 614, 320, 634), page1_id))
    field_ids.append(member_id_id)
    dob_id = add_object(objects, text_field("demog.dob", (180, 578, 300, 598), page1_id))
    field_ids.append(dob_id)
    mobile_id = add_object(objects, text_field("contact.sms", (180, 542, 330, 562), page1_id))
    field_ids.append(mobile_id)
    plan_id = add_object(objects, choice_field("plan.code_sel", (180, 506, 360, 526), page1_id))
    field_ids.append(plan_id)

    radio_parent_id = add_object(objects, b"")
    radio_emp_id = add_object(
        objects,
        radio_kid(radio_parent_id, (180, 450, 194, 464), page1_id, "EMP", radio_off_id, radio_on_id),
    )
    radio_spouse_id = add_object(
        objects,
        radio_kid(radio_parent_id, (305, 450, 319, 464), page1_id, "EE_SP", radio_off_id, radio_on_id),
    )
    radio_family_id = add_object(
        objects,
        radio_kid(radio_parent_id, (470, 450, 484, 464), page1_id, "FAM", radio_off_id, radio_on_id),
    )
    objects[radio_parent_id - 1] = radio_parent("cov.tier_rg", [radio_emp_id, radio_spouse_id, radio_family_id])
    field_ids.append(radio_parent_id)

    spouse_name_id = add_object(objects, text_field("dep.spouse_nm", (180, 686, 360, 706), page2_id))
    field_ids.append(spouse_name_id)
    spouse_tobacco_id = add_object(
        objects,
        checkbox_field("decl.sp_tob", (180, 648, 194, 662), page2_id, "TobYes", checkbox_off_id, checkbox_on_id),
    )
    field_ids.append(spouse_tobacco_id)
    paperless_id = add_object(
        objects,
        checkbox_field("prefs.paper_eob", (180, 612, 194, 626), page2_id, "EmailOnly", checkbox_off_id, checkbox_on_id),
    )
    field_ids.append(paperless_id)
    effective_id = add_object(objects, text_field("eff.dt", (180, 542, 300, 562), page2_id))
    field_ids.append(effective_id)

    page1_annots = " ".join(
        f"{obj_id} 0 R"
        for obj_id in [
            last_name_id,
            first_name_id,
            member_id_id,
            dob_id,
            mobile_id,
            plan_id,
            radio_emp_id,
            radio_spouse_id,
            radio_family_id,
        ]
    )
    page2_annots = " ".join(
        f"{obj_id} 0 R"
        for obj_id in [spouse_name_id, spouse_tobacco_id, paperless_id, effective_id]
    )

    objects[page1_id - 1] = (
        f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
        f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
        f"/Contents {page1_content_id} 0 R /Annots [{page1_annots}] >>"
    ).encode("latin-1")
    objects[page2_id - 1] = (
        f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
        f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
        f"/Contents {page2_content_id} 0 R /Annots [{page2_annots}] >>"
    ).encode("latin-1")

    field_refs = " ".join(f"{field_id} 0 R" for field_id in field_ids)
    objects[acroform_id - 1] = (
        f"<< /Fields [{field_refs}] /DR << /Font << /Helv {font_id} 0 R >> >> "
        f"/DA (/Helv 11 Tf 0 g) /NeedAppearances true >>"
    ).encode("latin-1")
    objects[catalog_id - 1] = (
        f"<< /Type /Catalog /Pages {pages_id} 0 R /AcroForm {acroform_id} 0 R >>"
    ).encode("latin-1")
    objects[pages_id - 1] = (
        f"<< /Type /Pages /Count 2 /Kids [{page1_id} 0 R {page2_id} 0 R] >>"
    ).encode("latin-1")

    chunks = [b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"]
    offsets = [0]
    cursor = len(chunks[0])

    for obj_id, body in enumerate(objects, start=1):
        obj = f"{obj_id} 0 obj\n".encode("latin-1") + body + b"\nendobj\n"
        offsets.append(cursor)
        chunks.append(obj)
        cursor += len(obj)

    xref_start = cursor
    xref_lines = [f"xref\n0 {len(objects) + 1}\n".encode("latin-1"), b"0000000000 65535 f \n"]
    for offset in offsets[1:]:
        xref_lines.append(f"{offset:010d} 00000 n \n".encode("latin-1"))

    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
        f"startxref\n{xref_start}\n%%EOF\n"
    ).encode("latin-1")

    return b"".join(chunks + xref_lines + [trailer])


def main(output_path: str):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(build_pdf())


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: build_enrollment_form.py <output.pdf>")
    main(sys.argv[1])
