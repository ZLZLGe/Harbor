#!/usr/bin/env python3
"""Build the literary contest manuscript fixture PDF with embedded metadata and links."""

from __future__ import annotations

import sys
from pathlib import Path


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class PDFBuilder:
    def __init__(self) -> None:
        self.objects: list[str] = []

    def add_object(self, content: str) -> int:
        self.objects.append(content)
        return len(self.objects)

    def render(self, info_id: int) -> bytes:
        binary_marker = "".join(chr(value) for value in (0xE2, 0xE3, 0xCF, 0xD3))
        output = [f"%PDF-1.4\n%{binary_marker}\n"]
        offsets = [0]
        position = len(output[0].encode("latin1"))

        for index, obj in enumerate(self.objects, start=1):
            chunk = f"{index} 0 obj\n{obj}\nendobj\n"
            offsets.append(position)
            output.append(chunk)
            position += len(chunk.encode("latin1"))

        xref_position = position
        xref = [f"xref\n0 {len(self.objects) + 1}\n", "0000000000 65535 f \n"]
        for offset in offsets[1:]:
            xref.append(f"{offset:010d} 00000 n \n")

        trailer = (
            f"trailer\n<< /Size {len(self.objects) + 1} /Root 1 0 R /Info {info_id} 0 R >>\n"
            f"startxref\n{xref_position}\n%%EOF\n"
        )
        return "".join(output + xref + [trailer]).encode("latin1")


def build_text_stream(lines: list[str], font_size: int, leading: int, start_x: int, start_y: int) -> str:
    body = "\n".join(f"({pdf_escape(line)}) Tj T*" for line in lines)
    return (
        "BT\n"
        f"/F1 {font_size} Tf\n"
        f"{leading} TL\n"
        f"{start_x} {start_y} Td\n"
        f"{body}\n"
        "ET"
    )


def create_fixture(output_path: Path) -> None:
    pages = [
        [
            "GLASS HARBOR",
            "Lantern Prize novella submission",
            "",
            "Author: Mara Ellison",
            "Represented by Northbank Literary Agency",
            "Website: www.maraellisonwrites.com",
            "Contact: mara@northbanklit.com | +1 212-555-0199",
            "Awards: Winner of the 2023 Halcyon Prize; shortlisted for the Aurora Quill Award",
            "",
            "Opening note to the jury:",
            "The following manuscript excerpt begins with Chapter I and keeps the original footnotes and section breaks used in the contest copy.",
        ],
        [
            "Mara Ellison | Glass Harbor",
            "Chapter I",
            "The harbor bells started before dawn, each iron note rolling over the tide flats like a warning that could not decide whom it belonged to.",
            "Leonie kept the tide book tucked inside her coat because paper was the only thing in Barrow Point that still answered to weather better than people did.",
            "By the time the first ferry lantern rocked awake, she had already crossed the breakwater twice and memorized the names on every crate waiting at pier seven.",
            "No one else bothered to count the gulls, but the gulls always knew which boats carried sugar, which boats carried rumors, and which boats carried the kind of grief that could not stay hidden.",
            "Footnote 1. Tide book is the dockside ledger used by ferry clerks to track wind, cargo, and delayed departures.",
            "Leonie copied the ledger by hand because the original clerk had vanished in autumn, leaving behind only a brass key and three pages torn cleanly from the back of the book.",
            "She told herself the missing pages were nothing more than bookkeeping, yet every blank edge looked like a mouth holding back testimony.",
            "2",
        ],
        [
            "Mara Ellison | Glass Harbor",
            "Chapter II",
            "At noon the committee hall filled with the smell of wet wool, lamp oil, and the pepper biscuits Mrs. Vale baked whenever the town expected bad news.",
            "Leonie spread the copied entries across the long table and watched the aldermen pretend the dates did not line up with the storm memorial carved outside the chapel.",
            "One line mentioned a passenger listed only as Witness, another marked an unsigned trunk for return to North Reef, and a third ended with the phrase keep from the singers.",
            "The mayor asked where she had found the notebook, but what he meant was whether anyone else had seen it first.",
            "Footnote 2. The singers are volunteer mourners paid to stand on the seawall and recite the names of those lost offshore.",
            "When Leonie answered that the book had been sitting beneath the signal map all winter, three men in black ferry coats looked toward the window instead of toward her.",
            "That was the moment she understood the ledger had not been misplaced. It had been hidden in plain sight, among tools everyone thought too ordinary to matter.",
            "3",
        ],
        [
            "Mara Ellison | Glass Harbor",
            "Chapter III",
            "Night returned with a glassy calm that made the harbor look staged, as if the moon had polished every wave until the water resembled hammered tin.",
            "Leonie carried the torn pages to the beacon house, matching the ragged edges against the copied entries until the names, numbers, and tide marks finally locked together.",
            "The last missing note was not an inventory mark at all but a direction: ring the bells only after the witness is ashore.",
            "She heard boots on the stairwell then, slow and careful, the pace of someone who believed patience could pass for innocence.",
            "Instead of turning, Leonie struck the old signal gong once and let the sound split open the quiet harbor below.",
            "Footnote 3. Beacon houses once stored emergency charts, storm flags, and hand-cranked sirens for the ferry marshals.",
            "By morning the town would argue over what the bells had meant, but the manuscript ends here, with Leonie choosing noise over silence and testimony over ceremony.",
            "4",
        ],
    ]

    annotations = {
        0: [
            ("https://www.maraellisonwrites.com", [168, 670, 360, 684]),
            ("mailto:mara@northbanklit.com", [128, 652, 320, 666]),
        ]
    }

    builder = PDFBuilder()
    catalog_id = builder.add_object("<<>>")
    pages_id = builder.add_object("<<>>")
    font_id = builder.add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids: list[int] = []

    for page_index, lines in enumerate(pages):
        stream = build_text_stream(
            lines=lines,
            font_size=12 if page_index == 0 else 11,
            leading=18 if page_index == 0 else 16,
            start_x=72,
            start_y=720 if page_index == 0 else 742,
        )
        content_id = builder.add_object(
            f"<< /Length {len(stream.encode('latin1'))} >>\nstream\n{stream}\nendstream"
        )

        annot_refs: list[int] = []
        for uri, rect in annotations.get(page_index, []):
            annot_id = builder.add_object(
                "<< /Type /Annot /Subtype /Link "
                f"/Rect [{' '.join(str(value) for value in rect)}] "
                "/Border [0 0 0] "
                f"/A << /S /URI /URI ({pdf_escape(uri)}) >> >>"
            )
            annot_refs.append(annot_id)

        annots_part = ""
        if annot_refs:
            annots_part = " /Annots [" + " ".join(f"{annot_id} 0 R" for annot_id in annot_refs) + "]"

        page_id = builder.add_object(
            "<< /Type /Page "
            f"/Parent {pages_id} 0 R "
            "/MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
            f"/Contents {content_id} 0 R"
            f"{annots_part} >>"
        )
        page_ids.append(page_id)

    builder.objects[catalog_id - 1] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>"
    builder.objects[pages_id - 1] = (
        f"<< /Type /Pages /Count {len(page_ids)} /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] >>"
    )

    info_id = builder.add_object(
        "<< /Title (Glass Harbor Manuscript) "
        "/Author (Mara Ellison) "
        "/Creator (Northbank Literary PDF Desk) "
        "/Producer (FixtureBuilder) "
        "/Subject (Lantern Prize contest copy) >>"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(builder.render(info_id))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: build_manuscript_fixture.py <output_path>")
    create_fixture(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
