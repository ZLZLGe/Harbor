import json
import os


OUTPUT_PATH = os.environ.get("PRIMARY_OUTPUT_FILE", "/root/restricted_listing_matches.json")

EXPECTED_MATCHES = [
    {
        "listing_id": "ML-002",
        "seller_id": "S-101",
        "listing_title": "Asteron Nova X-2 sat phone w/ wall charger",
        "matched_catalog_id": "RC-101",
        "matched_canonical_title": "Asteron Nova X2 Satellite Phone",
        "restriction_reason": "Export Controlled Device",
    },
    {
        "listing_id": "ML-003",
        "seller_id": "S-101",
        "listing_title": "Bio Luxe derma pen pro microneedle kit sealed",
        "matched_catalog_id": "RC-102",
        "matched_canonical_title": "BioLuxe DermaPen Pro Microneedling Kit",
        "restriction_reason": "Medical Device Restriction",
    },
    {
        "listing_id": "ML-005",
        "seller_id": "S-103",
        "listing_title": "Cloud Peak Rngr 8 thermal scope bundle",
        "matched_catalog_id": "RC-103",
        "matched_canonical_title": "CloudPeak Ranger 8 Thermal Scope",
        "restriction_reason": "Restricted Optics",
    },
    {
        "listing_id": "ML-006",
        "seller_id": "S-104",
        "listing_title": "Ever Volt V12 av battery pack - new",
        "matched_catalog_id": "RC-104",
        "matched_canonical_title": "EverVolt V12 Aviation Battery Pack",
        "restriction_reason": "Hazardous Goods",
    },
    {
        "listing_id": "ML-009",
        "seller_id": "S-106",
        "listing_title": "Red Line RX-900 radar det + case",
        "matched_catalog_id": "RC-105",
        "matched_canonical_title": "Redline RX900 Radar Detector",
        "restriction_reason": "Brand Protection Program",
    },
    {
        "listing_id": "ML-010",
        "seller_id": "S-107",
        "listing_title": "Luma Forge smooth beam IPL handset with pouch",
        "matched_catalog_id": "RC-108",
        "matched_canonical_title": "LumaForge IPL SmoothBeam Handset",
        "restriction_reason": "Personal Care Device Restriction",
    },
]

EXCLUDED_LISTING_IDS = {"ML-001", "ML-004", "ML-007", "ML-008", "ML-011", "ML-012"}


class TestOutputs:
    def test_file_exists(self):
        assert os.path.exists(OUTPUT_PATH)

    def test_exact_matches(self):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as handle:
            actual = json.load(handle)

        assert isinstance(actual, list), "Output must be a JSON array."
        assert actual == EXPECTED_MATCHES

    def test_safe_and_ambiguous_listings_are_excluded(self):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as handle:
            actual = json.load(handle)

        flagged_ids = {item["listing_id"] for item in actual}
        assert not (flagged_ids & EXCLUDED_LISTING_IDS), (
            f"Safe or ambiguous listings were incorrectly included: {sorted(flagged_ids & EXCLUDED_LISTING_IDS)}"
        )
