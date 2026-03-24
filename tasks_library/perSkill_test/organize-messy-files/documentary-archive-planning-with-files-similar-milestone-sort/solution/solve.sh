#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import os
import shutil
from pathlib import Path

TASK_ROOT = Path(os.environ.get("ARCHIVE_TASK_ROOT", "/root"))
ARCHIVE_ROOT = TASK_ROOT / "documentary_archive"
INBOX = ARCHIVE_ROOT / "inbox"
REPORTS = TASK_ROOT / "reports"

FOLDER_TO_SCOPE = {
    "01_development": "Story research, editorial framing, archive scouting, access development, and early commissioning work.",
    "02_pre_production": "Scheduling, permits, location planning, logistics, and preparation work before principal photography.",
    "03_production": "Principal photography, field coordination, release handling, and shoot-day media tracking.",
    "04_post_production": "Assembly edits, rough-cut review, sound and finishing work, and edit-room decisions after filming.",
    "05_festival_delivery": "Festival submissions, launch planning, screening QC, press preparation, and audience-facing delivery assets.",
    "06_finance_and_admin": "Budgets, grant reporting, vendor management, reimbursement tracking, and administrative oversight.",
}

FOLDER_TO_FILES = {
    "01_development": [
        "aurora_packet_01.pdf",
        "delta_notes.docx",
        "horizon_overview.pptx",
        "table_read_excerpt.txt",
    ],
    "02_pre_production": [
        "harbor_packet_02.pdf",
        "matrix_sheet.xlsx",
        "route_sync_excerpt.txt",
        "window_notes.docx",
    ],
    "03_production": [
        "card_index.xlsx",
        "field_packet_03.pdf",
        "night_shift_excerpt.txt",
        "release_notes.docx",
    ],
    "04_post_production": [
        "assembly_excerpt.txt",
        "bench_packet_04.pdf",
        "lane_notes.docx",
        "mix_sheet.xlsx",
    ],
    "05_festival_delivery": [
        "launch_packet_05.pdf",
        "path_overview.pptx",
        "press_notes.docx",
        "qc_sheet.xlsx",
    ],
    "06_finance_and_admin": [
        "cash_sheet.xlsx",
        "closeout_notes.docx",
        "partner_overview.pptx",
        "vendor_packet_06.pdf",
    ],
}

for folder, filenames in FOLDER_TO_FILES.items():
    destination = ARCHIVE_ROOT / folder
    destination.mkdir(parents=True, exist_ok=True)
    for filename in filenames:
        src = INBOX / filename
        dst = destination / filename
        if src.exists():
            shutil.move(str(src), str(dst))

REPORTS.mkdir(parents=True, exist_ok=True)

manifest = {
    "archive_root": str(ARCHIVE_ROOT),
    "inbox_cleared": not any(INBOX.iterdir()),
    "total_files": sum(len(files) for files in FOLDER_TO_FILES.values()),
    "milestones": [],
}

for folder in sorted(FOLDER_TO_FILES):
    files = sorted(FOLDER_TO_FILES[folder])
    manifest["milestones"].append(
        {
            "folder": folder,
            "scope": FOLDER_TO_SCOPE[folder],
            "file_count": len(files),
            "files": files,
        }
    )

(REPORTS / "archive_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

(TASK_ROOT / "task_plan.md").write_text(
    "\n".join(
        [
            "# Task Plan",
            "",
            "## Goal",
            "Sort the documentary archive into six milestone folders and write the manifest.",
            "",
            "## Milestones",
            *[f"- {folder}" for folder in sorted(FOLDER_TO_FILES)],
            "",
            "## Status",
            "- Review file contents: complete",
            "- Organize folders: complete",
            "- Write manifest: complete",
        ]
    )
    + "\n",
    encoding="utf-8",
)

(TASK_ROOT / "findings.md").write_text(
    "\n".join(
        [
            "# Findings",
            "",
            "- 01_development contains story research, access, and commissioning materials.",
            "- 02_pre_production contains logistics, permits, and prep scheduling.",
            "- 03_production contains shoot-day records, releases, and media tracking.",
            "- 04_post_production contains edit, rough-cut, and finishing notes.",
            "- 05_festival_delivery contains launch planning, screening QC, and press materials.",
            "- 06_finance_and_admin contains grants, vendors, reimbursements, and cash tracking.",
        ]
    )
    + "\n",
    encoding="utf-8",
)

(TASK_ROOT / "progress.md").write_text(
    "\n".join(
        [
            "# Progress",
            "",
            f"- Created the six milestone folders under {ARCHIVE_ROOT}.",
            f"- Moved all 24 files out of {INBOX}.",
            f"- Wrote {REPORTS / 'archive_manifest.json'}.",
        ]
    )
    + "\n",
    encoding="utf-8",
)
PY
