from __future__ import annotations

import json

from common import DATA_ROOT, card_availability, card_handle, predictive_group_key, read_collection_soup, read_predictive_soup, read_report, run_build


COLLECTION_CONTEXT_PATH = DATA_ROOT / "collection_context.json"
CATALOG_PATH = DATA_ROOT / "catalog_products.json"
PREDICTIVE_PATH = DATA_ROOT / "predictive_search_snapshot.json"


def test_mutation_updates_outputs() -> None:
    original_collection = COLLECTION_CONTEXT_PATH.read_text(encoding="utf-8")
    original_catalog = CATALOG_PATH.read_text(encoding="utf-8")
    original_predictive = PREDICTIVE_PATH.read_text(encoding="utf-8")

    try:
        collection_context = json.loads(original_collection)
        catalog = json.loads(original_catalog)
        predictive = json.loads(original_predictive)

        collection_context["featured_handles"] = ["floral-white-top", "classic-varsity-top", "classic-leather-jacket"]
        predictive["queries"][0] = "capsule silk layer"

        for product in catalog:
            if product["handle"] == "floral-white-top":
                for variant in product["variants"]:
                    variant["inventory"] = 5
                    variant["available"] = True

        COLLECTION_CONTEXT_PATH.write_text(json.dumps(collection_context, indent=2) + "\n", encoding="utf-8")
        CATALOG_PATH.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
        PREDICTIVE_PATH.write_text(json.dumps(predictive, indent=2) + "\n", encoding="utf-8")
        run_build()

        collection_soup = read_collection_soup()
        predictive_soup = read_predictive_soup()
        report = read_report()

        floral_card = None
        for node in collection_soup.select("[data-product-card]"):
            if card_handle(node) == "floral-white-top":
                floral_card = node
                break
        if floral_card is None or card_availability(floral_card) != "in_stock":
            raise AssertionError("floral-white-top availability did not update after mutation")
        if "Sold out" in floral_card.get_text(" ", strip=True):
            raise AssertionError("floral-white-top still shows sold-out text after mutation")

        first_query = None
        for group in predictive_soup.select(".predictive-search__group[data-group], [data-predictive-group]"):
            if predictive_group_key(group) == "queries":
                first_query = group.select_one("li")
                break
        if first_query is None or first_query.get_text(strip=True) != "capsule silk layer":
            raise AssertionError("predictive search query group did not refresh after mutation")

        report_cards = {entry["handle"]: entry for entry in report["product_cards"]}
        report_value = report_cards["floral-white-top"]["availability"]
        if report_value in {"Sold out", "Low stock", "In stock"}:
            report_value = {"Sold out": "out_of_stock", "Low stock": "in_stock", "In stock": "in_stock"}[report_value]
        if report_value != "in_stock":
            raise AssertionError("report did not refresh floral-white-top availability after mutation")
    finally:
        COLLECTION_CONTEXT_PATH.write_text(original_collection, encoding="utf-8")
        CATALOG_PATH.write_text(original_catalog, encoding="utf-8")
        PREDICTIVE_PATH.write_text(original_predictive, encoding="utf-8")
        run_build()
