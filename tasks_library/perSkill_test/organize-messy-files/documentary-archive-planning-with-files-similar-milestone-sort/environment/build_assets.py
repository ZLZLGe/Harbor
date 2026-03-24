#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

TASK_ROOT = Path(os.environ.get("ARCHIVE_TASK_ROOT", "/root"))
ROOT = TASK_ROOT / "documentary_archive" / "inbox"

FILES = [
    {
        "folder": "01_development",
        "name": "aurora_packet_01.pdf",
        "kind": "pdf",
        "content": [
            "Aurora packet 01 compiles the documentary team's development-phase research.",
            "It covers story framing, archive scouting, early access conversations, and commissioning follow-up.",
            "These notes belong before any permit booking, crew scheduling, field shooting, or final delivery work.",
        ],
    },
    {
        "folder": "01_development",
        "name": "delta_notes.docx",
        "kind": "docx",
        "content": [
            "Development memo for character shortlist and editorial thesis.",
            "Use this file with research interviews, archive requests, and early funding conversations.",
            "It does not belong with pre-production logistics, production media tracking, or finance closeout.",
        ],
    },
    {
        "folder": "01_development",
        "name": "table_read_excerpt.txt",
        "kind": "txt",
        "content": [
            "Transcript excerpt",
            "Producer: We are still shaping the story spine and deciding which archival leads to pursue.",
            "Director: Keep this with development because cameras are not scheduled yet.",
        ],
    },
    {
        "folder": "01_development",
        "name": "horizon_overview.pptx",
        "kind": "pptx",
        "slides": [
            {
                "title": "Editorial Thesis",
                "bullets": [
                    "Early story framing for the feature documentary",
                    "Research leads and archive approach",
                    "Commissioning deck for development conversations",
                ],
            },
            {
                "title": "What This Is Not",
                "bullets": [
                    "Not a prep schedule",
                    "Not a shoot-day record",
                    "Not a festival launch deck",
                ],
            },
        ],
    },
    {
        "folder": "02_pre_production",
        "name": "harbor_packet_02.pdf",
        "kind": "pdf",
        "content": [
            "Harbor packet 02 groups pre-production planning materials.",
            "It tracks permit timing, location access, crew movement, equipment reservations, and call-sheet preparation.",
            "This belongs after story development but before principal photography starts.",
        ],
    },
    {
        "folder": "02_pre_production",
        "name": "window_notes.docx",
        "kind": "docx",
        "content": [
            "Pre-production note set for location windows, contributor travel, and release prep before filming.",
            "Keep with scheduling and logistics rather than daily field reports or edit-room feedback.",
        ],
    },
    {
        "folder": "02_pre_production",
        "name": "matrix_sheet.xlsx",
        "kind": "xlsx",
        "sheet": "Prep Matrix",
        "rows": [
            ["Task", "Owner", "Status"],
            ["Scout industrial waterfront", "Field producer", "locked for prep"],
            ["Reserve long-lens package", "Camera team", "scheduled before shoot"],
            ["Prepare draft call sheet", "Production manager", "pending final crew confirmation"],
        ],
    },
    {
        "folder": "02_pre_production",
        "name": "route_sync_excerpt.txt",
        "kind": "txt",
        "content": [
            "Roundtable transcript",
            "Coordinator: We need the prep recce finished before camera day one.",
            "PM: Put this in pre-production with the permits, transport plan, and crew logistics.",
        ],
    },
    {
        "folder": "03_production",
        "name": "field_packet_03.pdf",
        "kind": "pdf",
        "content": [
            "Field packet 03 documents active production work.",
            "It mentions shoot-day coverage, on-set problem solving, media handoff, and producer check-ins during filming.",
            "This is for principal photography, not prep, post, launch, or finance.",
        ],
    },
    {
        "folder": "03_production",
        "name": "release_notes.docx",
        "kind": "docx",
        "content": [
            "Production note set for appearance releases signed during fieldwork.",
            "Store with filming operations, camera media, and shoot-day coordination.",
        ],
    },
    {
        "folder": "03_production",
        "name": "card_index.xlsx",
        "kind": "xlsx",
        "sheet": "Media Cards",
        "rows": [
            ["Card", "Shoot Day", "Status"],
            ["A014", "Day 06 waterfront interviews", "backed up"],
            ["B003", "Day 07 night exterior", "awaiting checksum"],
            ["C011", "Day 08 factory floor", "cleared for archive"],
        ],
    },
    {
        "folder": "03_production",
        "name": "night_shift_excerpt.txt",
        "kind": "txt",
        "content": [
            "Shoot debrief transcript",
            "AC: Tonight's production run wrapped at 02:10 after the handheld river sequence.",
            "Producer: Keep this with principal photography paperwork and daily field notes.",
        ],
    },
    {
        "folder": "04_post_production",
        "name": "bench_packet_04.pdf",
        "kind": "pdf",
        "content": [
            "Bench packet 04 is a post-production file.",
            "It covers paper edits, rough-cut structure, sound mix issues, and finishing review after filming is complete.",
            "This belongs in the edit phase rather than on-set production or festival delivery.",
        ],
    },
    {
        "folder": "04_post_production",
        "name": "lane_notes.docx",
        "kind": "docx",
        "content": [
            "Post-production notes on sequence order, rough-cut response, and editor handoff.",
            "Use with assembly decisions and finishing feedback after principal photography.",
        ],
    },
    {
        "folder": "04_post_production",
        "name": "mix_sheet.xlsx",
        "kind": "xlsx",
        "sheet": "Mix Pass",
        "rows": [
            ["Cue", "Issue", "Action"],
            ["Dock ambiences", "dialog buried", "lift lav track in mix pass 2"],
            ["Factory hum", "too sharp", "smooth during final online"],
            ["Voice-over stem", "timing late", "pull two frames before export"],
        ],
    },
    {
        "folder": "04_post_production",
        "name": "assembly_excerpt.txt",
        "kind": "txt",
        "content": [
            "Edit bench transcript",
            "Editor: The assembly is long, but the final act works once the rough cut loses the extra exposition.",
            "Director: Keep this in post-production with cut feedback and sound notes.",
        ],
    },
    {
        "folder": "05_festival_delivery",
        "name": "launch_packet_05.pdf",
        "kind": "pdf",
        "content": [
            "Launch packet 05 focuses on festival and delivery activity.",
            "It tracks premiere targets, screening deliverables, press outreach, and audience-facing rollout plans.",
            "This is after post-production, and it is separate from general finance administration.",
        ],
    },
    {
        "folder": "05_festival_delivery",
        "name": "press_notes.docx",
        "kind": "docx",
        "content": [
            "Festival delivery notes for synopsis polishing, press kit assembly, and submission copy.",
            "Keep with launch planning, exhibition preparation, and final screening packages.",
        ],
    },
    {
        "folder": "05_festival_delivery",
        "name": "path_overview.pptx",
        "kind": "pptx",
        "slides": [
            {
                "title": "Launch Path",
                "bullets": [
                    "Festival premiere sequence",
                    "Publicity beats and press kit timing",
                    "Audience Q and A planning after final export",
                ],
            },
            {
                "title": "Screening Delivery",
                "bullets": [
                    "DCP and screener handoff",
                    "QC checklist before projection",
                    "Materials for programming teams",
                ],
            },
        ],
    },
    {
        "folder": "05_festival_delivery",
        "name": "qc_sheet.xlsx",
        "kind": "xlsx",
        "sheet": "Festival QC",
        "rows": [
            ["Item", "Check", "Result"],
            ["Subtitle burn-in", "festival screener", "passed"],
            ["Stereo fold-down", "theater test", "passed"],
            ["Press stills bundle", "publicist delivery", "ready"],
        ],
    },
    {
        "folder": "06_finance_and_admin",
        "name": "vendor_packet_06.pdf",
        "kind": "pdf",
        "content": [
            "Vendor packet 06 belongs to finance and administrative tracking.",
            "It summarizes invoice follow-up, grant reporting, reimbursement review, and partner paperwork.",
            "Even when it mentions travel or festivals, its home is finance and admin.",
        ],
    },
    {
        "folder": "06_finance_and_admin",
        "name": "closeout_notes.docx",
        "kind": "docx",
        "content": [
            "Administrative closeout notes for grant reports, vendor reconciliations, and payment status.",
            "Keep this with budgets and reimbursement tracking rather than creative delivery assets.",
        ],
    },
    {
        "folder": "06_finance_and_admin",
        "name": "cash_sheet.xlsx",
        "kind": "xlsx",
        "sheet": "Cash Watch",
        "rows": [
            ["Line", "Forecast", "Comment"],
            ["Archive licensing", "18000", "awaiting invoice approval"],
            ["Crew reimbursements", "4200", "batching after final receipts"],
            ["Grant milestone", "25000", "report due at administrative closeout"],
        ],
    },
    {
        "folder": "06_finance_and_admin",
        "name": "partner_overview.pptx",
        "kind": "pptx",
        "slides": [
            {
                "title": "Administrative Status",
                "bullets": [
                    "Partner reporting calendar",
                    "Budget variance and cash watch",
                    "Outstanding vendor paperwork",
                ],
            },
            {
                "title": "Why This Folder",
                "bullets": [
                    "Finance and admin only",
                    "Not for post-production editorial notes",
                    "Not for festival launch materials",
                ],
            },
        ],
    },
]


def ensure_root() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)


def pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_pdf(path: Path, lines: list[str]) -> None:
    stream = "BT\n/F1 12 Tf\n50 760 Td\n16 TL\n"
    for line in lines:
        stream += f"({pdf_escape(line)}) Tj T*\n"
    stream += "ET\n"
    stream_bytes = stream.encode("utf-8")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream_bytes), stream_bytes),
    ]

    parts = [b"%PDF-1.4\n"]
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(sum(len(part) for part in parts))
        parts.append(f"{index} 0 obj\n".encode("ascii"))
        parts.append(obj)
        parts.append(b"\nendobj\n")

    xref_offset = sum(len(part) for part in parts)
    parts.append(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    parts.append(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        parts.append(f"{offset:010d} 00000 n \n".encode("ascii"))
    parts.append(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("ascii"))
    parts.append(f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii"))

    path.write_bytes(b"".join(parts))


def write_docx(path: Path, paragraphs: list[str]) -> None:
    body = "".join(
        f"<w:p><w:r><w:t xml:space=\"preserve\">{escape(paragraph)}</w:t></w:r></w:p>"
        for paragraph in paragraphs
    )
    document_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">"
        f"<w:body>{body}</w:body>"
        "</w:document>"
    )
    content_types = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
        "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
        "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
        "<Override PartName=\"/word/document.xml\" "
        "ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>"
        "</Types>"
    )
    rels = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        "<Relationship Id=\"rId1\" "
        "Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" "
        "Target=\"word/document.xml\"/>"
        "</Relationships>"
    )
    with ZipFile(path, "w", ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", document_xml)


def write_txt(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_xlsx(path: Path, sheet_name: str, rows: list[list[str]]) -> None:
    def cell_ref(column_index: int, row_index: int) -> str:
        return f"{chr(ord('A') + column_index)}{row_index}"

    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row):
            ref = cell_ref(column_index, row_index)
            cells.append(
                f"<c r=\"{ref}\" t=\"inlineStr\"><is><t>{escape(str(value))}</t></is></c>"
            )
        sheet_rows.append(f"<row r=\"{row_index}\">{''.join(cells)}</row>")

    worksheet_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">"
        f"<sheetData>{''.join(sheet_rows)}</sheetData>"
        "</worksheet>"
    )
    workbook_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" "
        "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\">"
        f"<sheets><sheet name=\"{escape(sheet_name)}\" sheetId=\"1\" r:id=\"rId1\"/></sheets>"
        "</workbook>"
    )
    workbook_rels = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        "<Relationship Id=\"rId1\" "
        "Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" "
        "Target=\"worksheets/sheet1.xml\"/>"
        "</Relationships>"
    )
    content_types = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
        "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
        "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
        "<Override PartName=\"/xl/workbook.xml\" "
        "ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/>"
        "<Override PartName=\"/xl/worksheets/sheet1.xml\" "
        "ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/>"
        "</Types>"
    )
    root_rels = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        "<Relationship Id=\"rId1\" "
        "Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" "
        "Target=\"xl/workbook.xml\"/>"
        "</Relationships>"
    )

    with ZipFile(path, "w", ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        zf.writestr("xl/worksheets/sheet1.xml", worksheet_xml)


def write_pptx(path: Path, slides: list[dict[str, list[str]]]) -> None:
    content_types = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>",
        "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">",
        "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>",
        "<Default Extension=\"xml\" ContentType=\"application/xml\"/>",
        "<Override PartName=\"/ppt/presentation.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml\"/>",
    ]
    for index in range(1, len(slides) + 1):
        content_types.append(
            f"<Override PartName=\"/ppt/slides/slide{index}.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slide+xml\"/>"
        )
    content_types.append("</Types>")

    root_rels = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        "<Relationship Id=\"rId1\" "
        "Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" "
        "Target=\"ppt/presentation.xml\"/>"
        "</Relationships>"
    )

    slide_refs = "".join(
        f"<p:sldId id=\"{255 + index}\" r:id=\"rId{index}\"/>"
        for index in range(1, len(slides) + 1)
    )
    presentation_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<p:presentation xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" "
        "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" "
        "xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\">"
        f"<p:sldIdLst>{slide_refs}</p:sldIdLst>"
        "</p:presentation>"
    )

    presentation_rels = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>",
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">",
    ]
    for index in range(1, len(slides) + 1):
        presentation_rels.append(
            f"<Relationship Id=\"rId{index}\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide\" Target=\"slides/slide{index}.xml\"/>"
        )
    presentation_rels.append("</Relationships>")

    with ZipFile(path, "w", ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", "".join(content_types))
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("ppt/presentation.xml", presentation_xml)
        zf.writestr("ppt/_rels/presentation.xml.rels", "".join(presentation_rels))

        for index, slide in enumerate(slides, start=1):
            bullet_text = " ".join(slide["bullets"])
            slide_xml = (
                "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                "<slide>"
                f"<title>{escape(slide['title'])}</title>"
                f"<body>{escape(bullet_text)}</body>"
                "</slide>"
            )
            zf.writestr(f"ppt/slides/slide{index}.xml", slide_xml)


def write_file(item: dict[str, object]) -> None:
    path = ROOT / str(item["name"])
    kind = item["kind"]
    if kind == "pdf":
        write_pdf(path, list(item["content"]))
    elif kind == "docx":
        write_docx(path, list(item["content"]))
    elif kind == "txt":
        write_txt(path, list(item["content"]))
    elif kind == "xlsx":
        write_xlsx(path, str(item["sheet"]), list(item["rows"]))
    elif kind == "pptx":
        write_pptx(path, list(item["slides"]))
    else:
        raise ValueError(f"Unsupported kind: {kind}")


def write_manifest_hint() -> None:
    hint_path = TASK_ROOT / "documentary_archive" / "README.txt"
    hint_path.write_text(
        "Sort the files from inbox into the six milestone folders and write reports/archive_manifest.json.\n",
        encoding="utf-8",
    )


def main() -> None:
    ensure_root()
    for item in FILES:
        write_file(item)

    summary = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "file_count": len(FILES),
        "kinds": sorted({item["kind"] for item in FILES}),
    }
    (TASK_ROOT / "documentary_archive" / ".build_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    write_manifest_hint()


if __name__ == "__main__":
    main()
