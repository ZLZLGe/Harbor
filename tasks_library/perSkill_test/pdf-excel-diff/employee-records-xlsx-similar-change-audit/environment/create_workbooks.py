#!/usr/bin/env python3

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


ARCHIVE_WORKBOOK = [
    (
        "Archive Guide",
        [
            ["Employee archive workbook"],
            ["Use the roster sheet for comparison."],
            ["Snapshot Date", "2025-12-31"],
        ],
    ),
    (
        "Roster Archive",
        [
            ["Employee Roster Archive"],
            ["Confidential"],
            [],
            ["Employee ID", "Full Name", "Department", "Location", "Salary", "Bonus %", "Status"],
            ["EMP00101", "Alice Chen", "Finance", "New York", 92000, 0.08, "Active"],
            ["EMP00102", "Brian Diaz", "Sales", "Chicago", 87000, 0.05, "Active"],
            ["EMP00103", "Carla Evans", "Operations", "Austin", 91000, 0.07, "Leave"],
            ["EMP00104", "Daniel Ford", "Engineering", "Seattle", 118000, 0.12, "Active"],
            ["EMP00105", "Ella Green", "Support", "Denver", 68000, 0.04, "Active"],
            ["EMP00106", "Farah Hussain", "HR", "Boston", 83000, 0.06, "Active"],
            ["EMP00107", "Gavin Ito", "Legal", "San Francisco", 105000, 0.09, "Active"],
            ["EMP00109", "Ian King", "Procurement", "Miami", 76000, 0.05, "Active"],
        ],
    ),
]

CURRENT_WORKBOOK = [
    (
        "Change Notes",
        [
            ["Current employee workbook"],
            ["Includes one newly added employee that should not be reported as deleted."],
        ],
    ),
    (
        "Current Roster",
        [
            ["Current Employee Workbook"],
            ["Prepared for Q1 staffing review"],
            [],
            ["Columns may appear in a different order than the archived copy."],
            ["Full Name", "Employee ID", "Status", "Department", "Location", "Salary", "Bonus %"],
            ["Alice Chen", "EMP00101", "Active", "Finance", "New York", "96000", 0.08],
            ["Brian Diaz", "EMP00102", "Active", "Revenue ", "Chicago", 87000, "0.055"],
            ["Carla Evans", "EMP00103", "Active", "Operations", "Austin", 91000, 0.07],
            ["Daniel Ford", "EMP00104", "Active", "Engineering", "Portland", 118000, 0.12],
            ["Farah Hussain", "EMP00106", "Active", "People", "Boston", 83000, 0.06],
            ["Gavin Ito", "EMP00107", "Active", "Legal", "San Francisco", 105000, "0.1"],
            ["Hana Jones", "EMP00108", "Active", "Support", "Denver", 71000, 0.04],
        ],
    ),
]


def column_letter(index: int) -> str:
    result = []
    while index:
        index, remainder = divmod(index - 1, 26)
        result.append(chr(65 + remainder))
    return "".join(reversed(result))


def cell_xml(cell_ref: str, value: object) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return f'<c r="{cell_ref}" t="b"><v>{1 if value else 0}</v></c>'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{cell_ref}"><v>{value}</v></c>'
    return f'<c r="{cell_ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'


def worksheet_xml(rows: list[list[object]]) -> str:
    max_rows = max(len(rows), 1)
    max_cols = max((len(row) for row in rows), default=1)
    dimension = f"A1:{column_letter(max_cols)}{max_rows}"
    row_xml = []
    for row_index, row in enumerate(rows, start=1):
        cell_parts = []
        for col_index, value in enumerate(row, start=1):
            xml = cell_xml(f"{column_letter(col_index)}{row_index}", value)
            if xml:
                cell_parts.append(xml)
        row_xml.append(f'<row r="{row_index}">{"".join(cell_parts)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<dimension ref=\"{dimension}\"/>"
        "<sheetViews><sheetView workbookViewId=\"0\"/></sheetViews>"
        "<sheetFormatPr defaultRowHeight=\"15\"/>"
        f"<sheetData>{''.join(row_xml)}</sheetData>"
        "</worksheet>"
    )


def workbook_xml(sheets: list[tuple[str, list[list[object]]]]) -> str:
    sheet_entries = []
    for index, (name, _) in enumerate(sheets, start=1):
        sheet_entries.append(
            f'<sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<bookViews><workbookView xWindow=\"0\" yWindow=\"0\" windowWidth=\"24000\" windowHeight=\"12000\"/></bookViews>"
        f"<sheets>{''.join(sheet_entries)}</sheets>"
        "</workbook>"
    )


def workbook_rels_xml(sheets: list[tuple[str, list[list[object]]]]) -> str:
    relationships = []
    for index, _sheet in enumerate(sheets, start=1):
        relationships.append(
            f'<Relationship Id="rId{index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
        )
    relationships.append(
        '<Relationship Id="rIdStyles" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{''.join(relationships)}"
        "</Relationships>"
    )


def content_types_xml(sheet_count: int) -> str:
    overrides = [
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
        '<Override PartName="/docProps/core.xml" '
        'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
    ]
    for index in range(1, sheet_count + 1):
        overrides.append(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        f"{''.join(overrides)}"
        "</Types>"
    )


def package_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" '
        'Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" '
        'Target="docProps/app.xml"/>'
        "</Relationships>"
    )


def styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border/></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        "</styleSheet>"
    )


def app_xml(sheet_names: list[str]) -> str:
    parts = "".join(f"<vt:lpstr>{escape(name)}</vt:lpstr>" for name in sheet_names)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        "<Application>Microsoft Excel</Application>"
        f"<TitlesOfParts><vt:vector size=\"{len(sheet_names)}\" baseType=\"lpstr\">{parts}</vt:vector></TitlesOfParts>"
        "</Properties>"
    )


def core_xml() -> str:
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        "<dc:creator>OpenAI</dc:creator>"
        "<cp:lastModifiedBy>OpenAI</cp:lastModifiedBy>"
        f"<dcterms:created xsi:type=\"dcterms:W3CDTF\">{created}</dcterms:created>"
        f"<dcterms:modified xsi:type=\"dcterms:W3CDTF\">{created}</dcterms:modified>"
        "</cp:coreProperties>"
    )


def write_workbook(path: Path, sheets: list[tuple[str, list[list[object]]]]) -> None:
    with ZipFile(path, "w", ZIP_DEFLATED) as workbook:
        workbook.writestr("[Content_Types].xml", content_types_xml(len(sheets)))
        workbook.writestr("_rels/.rels", package_rels_xml())
        workbook.writestr("xl/workbook.xml", workbook_xml(sheets))
        workbook.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml(sheets))
        workbook.writestr("xl/styles.xml", styles_xml())
        workbook.writestr("docProps/app.xml", app_xml([name for name, _ in sheets]))
        workbook.writestr("docProps/core.xml", core_xml())
        for index, (_name, rows) in enumerate(sheets, start=1):
            workbook.writestr(f"xl/worksheets/sheet{index}.xml", worksheet_xml(rows))


def main() -> None:
    output_dir = Path(os.environ.get("WORKBOOK_OUTPUT_DIR", "/root"))
    output_dir.mkdir(parents=True, exist_ok=True)
    write_workbook(output_dir / "employee_records_archive.xlsx", ARCHIVE_WORKBOOK)
    write_workbook(output_dir / "employee_records_current.xlsx", CURRENT_WORKBOOK)


if __name__ == "__main__":
    main()
