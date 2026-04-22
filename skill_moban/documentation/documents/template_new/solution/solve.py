from __future__ import annotations

import subprocess


def main() -> None:
    subprocess.run(
        [
            "python3",
            "/app/.codex/skills/word-redline-workflows/scripts/apply_redline_decisions.py",
            "--input",
            "/app/vendor_addendum_redline.docx",
            "--decisions",
            "/app/review_decisions.json",
            "--output",
            "/app/output/vendor_addendum_final.docx",
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
