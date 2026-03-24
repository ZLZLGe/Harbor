import hashlib
import json
from pathlib import Path

from pypdf import PdfReader


OUTPUT_PDF = Path("/root/investment_committee_briefing.pdf")
HOLDINGS_PATH = Path("/root/portfolio_holdings.csv")
ATTRIBUTION_PATH = Path("/root/performance_attribution.csv")
RISK_PATH = Path("/root/risk_notes.json")

EXPECTED_HASHES = {
    HOLDINGS_PATH: "f67bbb9868c33e9c0ed1bc7ad9c1572e083942dce412bd88e748864044e7edad",
    ATTRIBUTION_PATH: "02b8151aa01d1185fa454bff8a1037fb720238a3e23b4d926347a637e6efec9e",
    RISK_PATH: "c49d328135f13e37492a4becb98dde12f21156bc62a00afc9ab38a1b90c42c12",
}

EXPECTED_PAGE_HEADINGS = [
    ["Investment Committee Briefing", "North Harbor Multi-Asset Portfolio", "Report Period: Q1 2026"],
    ["Executive Summary", "ahead of the 60/20/10/10 Policy Blend by 63 bps", "top five holdings represented 37.2% of the portfolio"],
    ["Performance Attribution", "Public Equities", "Real Assets", "Contribution (bps)"],
    ["Risk Watchlist", "Semiconductor concentration remains elevated", "Escalation Note:"],
]

EXPECTED_SUMMARY_SNIPPETS = [
    "The top holding was NVDA at 9.4% of capital",
    "Public Equities was the strongest attribution sleeve at 412 bps",
    "Real Assets was the weakest at -10 bps",
    "net exposure at 96%, gross exposure at 118%, tracking error at 4.2%, and five-day liquidity at 87%",
]

EXPECTED_RISK_LINES = [
    "Severity: High",
    "Owner: Public Equities",
    "Mitigation: Reduce NVIDIA exposure if position weight closes above 10%.",
    "Owner: Real Assets",
    "Owner: Private Credit",
    "Escalate immediately if tracking error rises above 5.0% or five-day liquidity falls below 80%.",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize(text: str) -> str:
    return " ".join((text or "").split())


class TestOutputs:
    def test_inputs_exist_and_match_expected_hashes(self):
        for path, expected in EXPECTED_HASHES.items():
            assert path.exists(), f"Missing input file: {path}"
            actual = sha256(path)
            assert actual == expected, f"Unexpected hash for {path}: {actual}"

    def test_output_pdf_exists(self):
        assert OUTPUT_PDF.exists(), f"Missing output file: {OUTPUT_PDF}"

    def test_output_pdf_has_four_pages(self):
        reader = PdfReader(str(OUTPUT_PDF))
        assert len(reader.pages) == 4, "The briefing must be a four-page PDF"

    def test_page_order_and_headings(self):
        reader = PdfReader(str(OUTPUT_PDF))
        page_texts = [normalize(page.extract_text() or "") for page in reader.pages]

        for page_text, expected_fragments in zip(page_texts, EXPECTED_PAGE_HEADINGS, strict=True):
            for fragment in expected_fragments:
                assert fragment in page_text, f"Missing {fragment!r} in page text: {page_text!r}"

    def test_summary_page_contains_required_metrics(self):
        reader = PdfReader(str(OUTPUT_PDF))
        summary_text = normalize(reader.pages[1].extract_text() or "")
        for snippet in EXPECTED_SUMMARY_SNIPPETS:
            assert snippet in summary_text, f"Missing summary snippet {snippet!r}"

    def test_performance_table_rows_present(self):
        reader = PdfReader(str(OUTPUT_PDF))
        table_text = normalize(reader.pages[2].extract_text() or "")
        expected_rows = [
            "Public Equities 7.4 5.9 412",
            "Private Credit 2.1 1.7 38",
            "Real Assets -0.8 0.5 -10",
            "Hedging Book 1.3 0.6 21",
        ]
        for row in expected_rows:
            assert row in table_text, f"Missing attribution row {row!r}"

    def test_risk_watchlist_contains_all_items(self):
        reader = PdfReader(str(OUTPUT_PDF))
        risk_text = normalize(reader.pages[3].extract_text() or "")
        with RISK_PATH.open("r", encoding="utf-8") as f:
            risk_data = json.load(f)

        for item in risk_data["risk_items"]:
            assert item["title"] in risk_text

        for line in EXPECTED_RISK_LINES:
            assert line in risk_text, f"Missing risk snippet {line!r}"
