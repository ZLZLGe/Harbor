from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

from bs4 import BeautifulSoup


DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/app/data"))
WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
OUT_ROOT = WORKSPACE_ROOT / "out"
REFERENCE_HASH_PATH = Path(os.environ.get("REFERENCE_HASH_PATH", "/opt/task-data.sha256"))


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def run_cmd(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PATH"] = f"{WORKSPACE_ROOT / 'bin'}:{env.get('PATH', '')}"
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True, env=env)
    if check and proc.returncode != 0:
        raise AssertionError(f"command failed: {' '.join(cmd)}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
    return proc


def run_build() -> None:
    run_cmd(["bash", str(WORKSPACE_ROOT / "build_preview.sh")], cwd=WORKSPACE_ROOT, check=True)


def task_inputs() -> tuple[list[dict], dict, dict, dict, dict]:
    return (
        load_json(DATA_ROOT / "catalog_products.json"),
        load_json(DATA_ROOT / "collection_context.json"),
        load_json(DATA_ROOT / "predictive_search_snapshot.json"),
        load_json(DATA_ROOT / "theme_section_blueprint.json"),
        load_json(DATA_ROOT / "theme_quality_rules.json"),
    )


def total_inventory(product: dict) -> int:
    return sum(int(variant["inventory"]) for variant in product["variants"])


def availability_state(product: dict, threshold: int) -> tuple[str, str]:
    total = total_inventory(product)
    if total <= 0:
        return ("out_of_stock", "Sold out")
    if total <= threshold:
        return ("in_stock", "Low stock")
    return ("in_stock", "In stock")


def expected_products(catalog: list[dict], collection_context: dict) -> list[dict]:
    threshold = int(collection_context["low_stock_threshold"])
    featured = {handle: idx for idx, handle in enumerate(collection_context["featured_handles"])}
    by_handle = {product["handle"]: product for product in catalog}
    out = []
    for handle in collection_context["product_order"]:
        product = by_handle[handle]
        state, label = availability_state(product, threshold)
        price = min(float(variant["price"]) for variant in product["variants"])
        badges = []
        if handle in featured:
            badges.append(collection_context["badge_labels"]["featured"])
        if label == "Low stock":
            badges.append(collection_context["badge_labels"]["low_stock"])
        out.append(
            {
                "handle": handle,
                "title": product["title"],
                "vendor": product["vendor"],
                "price": f"{price:.2f}",
                "availability": state,
                "availability_label": label,
                "material": product["material"],
                "image": product["featured_image"],
                "image_alt": product["featured_image_alt"],
                "badges": badges,
                "sort_key": (0 if handle in featured else 1, featured.get(handle, 999), collection_context["product_order"].index(handle)),
            }
        )
    out.sort(key=lambda item: item["sort_key"])
    return out


def expected_filters(catalog: list[dict], collection_context: dict) -> list[dict]:
    products = {product["handle"]: product for product in catalog}
    threshold = int(collection_context["low_stock_threshold"])
    selected = [products[handle] for handle in collection_context["product_order"]]
    out = []
    for filter_def in collection_context["filters"]:
        counts: dict[str, int] = {}
        for product in selected:
            if filter_def["source"] == "product_type":
                value = product["product_type"]
            elif filter_def["source"] == "material":
                value = product["material"]
            elif filter_def["source"] == "color":
                value = product["color"]
            else:
                value = availability_state(product, threshold)[1]
            counts[value] = counts.get(value, 0) + 1
        values = []
        for value in filter_def["order"]:
            if value in counts:
                values.append({"label": value, "count": counts[value]})
        out.append({"id": filter_def["id"], "label": filter_def["label"], "values": values})
    return out


def expected_search_groups(predictive_search: dict) -> list[dict]:
    return [
        {"key": "queries", "label": "Suggestions", "count": len(predictive_search["queries"])},
        {"key": "collections", "label": "Collections", "count": len(predictive_search["collections"])},
        {"key": "products", "label": "Products", "count": len(predictive_search["products"])},
    ]


def card_handle(node) -> str | None:
    return node.get("data-handle") or node.get("data-product-handle")


def normalized_availability(value: str | None) -> str | None:
    mapping = {
        "sold_out": "out_of_stock",
        "low_stock": "in_stock",
        "in_stock": "in_stock",
        "out_of_stock": "out_of_stock",
    }
    return mapping.get(value, value)


def card_availability(node) -> str | None:
    return normalized_availability(node.get("data-availability"))


def predictive_group_key(node) -> str | None:
    return node.get("data-group") or node.get("data-predictive-group")


def read_collection_soup() -> BeautifulSoup:
    return BeautifulSoup((OUT_ROOT / "collection.html").read_text(encoding="utf-8"), "html.parser")


def read_predictive_soup() -> BeautifulSoup:
    return BeautifulSoup((OUT_ROOT / "predictive-search.html").read_text(encoding="utf-8"), "html.parser")


def read_report() -> dict:
    return load_json(OUT_ROOT / "theme_preview_report.json")


def compute_data_hashes() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(DATA_ROOT.rglob("*")):
        if path.is_file():
            hashes[str(path.relative_to(DATA_ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def reference_hashes() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for line in REFERENCE_HASH_PATH.read_text(encoding="utf-8").splitlines():
        digest, raw_path = line.strip().split(maxsplit=1)
        file_path = Path(raw_path)
        hashes[str(file_path.relative_to(DATA_ROOT))] = digest
    return hashes
