from __future__ import annotations

from common import (
    card_availability,
    card_handle,
    expected_filters,
    expected_products,
    expected_search_groups,
    predictive_group_key,
    read_collection_soup,
    read_predictive_soup,
    read_report,
    run_cmd,
    task_inputs,
)


def test_collection_html() -> None:
    catalog, collection_context, _predictive_search, _blueprint, quality_rules = task_inputs()
    expected = expected_products(catalog, collection_context)
    soup = read_collection_soup()

    title = soup.select_one("[data-collection-handle] h1")
    if title is None or title.get_text(strip=True) != collection_context["collection"]["title"]:
        raise AssertionError("missing collection title")
    if soup.select_one("[data-sort-control]") is None:
        raise AssertionError("missing collection toolbar")

    cards = soup.select("[data-product-card]")
    if len(cards) != len(expected):
        raise AssertionError(f"product card count mismatch: got={len(cards)} expected={len(expected)}")

    handles = [card_handle(card) for card in cards]
    expected_handles = [item["handle"] for item in expected]
    if sorted(handles) != sorted(expected_handles):
        raise AssertionError(f"product card handles mismatch: got={handles} expected={expected_handles}")

    for idx, (card, item) in enumerate(zip(cards, expected), start=1):
        card_text = card.get_text(" ", strip=True)
        if f"${item['price']}" not in card_text:
            raise AssertionError(f"price mismatch for {item['handle']}")
        if card_availability(card) != item["availability"]:
            raise AssertionError(f"availability attr mismatch for {item['handle']}")
        image = card.select_one("img")
        if image is None:
            raise AssertionError(f"missing image for {item['handle']}")
        for attr in quality_rules["required_image_attributes"]:
            if not image.get(attr):
                raise AssertionError(f"image missing {attr} for {item['handle']}")
        title_node = card.select_one(".product-card__title, [data-product-title]")
        if title_node is None or title_node.get_text(strip=True) != item["title"]:
            raise AssertionError(f"title mismatch for {item['handle']}")
        vendor_node = card.select_one(".product-card__vendor, [data-product-vendor]")
        if vendor_node is None or vendor_node.get_text(strip=True) != item["vendor"]:
            raise AssertionError(f"vendor mismatch for {item['handle']}")
        availability_node = card.select_one(".product-card__availability, [data-product-availability]")
        if availability_node is None or availability_node.get_text(strip=True) != item["availability_label"]:
            raise AssertionError(f"availability label mismatch for {item['handle']}")
        badges = [
            node.get_text(strip=True)
            for node in card.select(".product-card__badges li, .product-card__badges [data-badge], .product-card__badges span")
        ]
        if badges != item["badges"]:
            raise AssertionError(f"badges mismatch for {item['handle']}: got={badges} expected={item['badges']}")


def test_filters_and_sorts() -> None:
    catalog, collection_context, _predictive_search, _blueprint, _rules = task_inputs()
    expected = expected_filters(catalog, collection_context)
    soup = read_collection_soup()

    groups = soup.select(".filter-group[data-filter-id]")
    if len(groups) != len(expected):
        raise AssertionError(f"filter group count mismatch: got={len(groups)} expected={len(expected)}")

    for node, expected_group in zip(groups, expected):
        if node["data-filter-id"] != expected_group["id"]:
            raise AssertionError("filter id mismatch")
        if node.select_one("h2").get_text(strip=True) != expected_group["label"]:
            raise AssertionError("filter label mismatch")
        values = []
        for item in node.select("li"):
            label_node = item.select_one(".filter-label")
            count_node = item.select_one(".filter-count")
            if label_node is not None and count_node is not None:
                values.append(f"{label_node.get_text(strip=True)} ({count_node.get_text(strip=True)})")
            else:
                values.append(item.get_text(" ", strip=True))
        expected_values = [f"{item['label']} ({item['count']})" for item in expected_group["values"]]
        if values != expected_values:
            raise AssertionError(f"filter values mismatch for {expected_group['id']}: got={values} expected={expected_values}")

    sort_labels = []
    for option in soup.select("[data-sort-control] option, [data-sort-option]"):
        label = option.get_text(strip=True)
        if label.endswith("Current"):
            label = label[: -len("Current")].rstrip()
        sort_labels.append(label)
    expected_sorts = [item["label"] for item in collection_context["sort_options"]]
    if sort_labels != expected_sorts:
        raise AssertionError(f"sort labels mismatch: got={sort_labels} expected={expected_sorts}")


def test_predictive_search_html() -> None:
    _catalog, _collection_context, predictive_search, _blueprint, _rules = task_inputs()
    expected = expected_search_groups(predictive_search)
    soup = read_predictive_soup()
    actual = []
    for group in soup.select(".predictive-search__group[data-group], [data-predictive-group]"):
        actual.append({
            "key": predictive_group_key(group),
            "label": group.select_one("h2").get_text(strip=True),
            "count": len(group.select("li")),
        })
    if actual != expected:
        raise AssertionError(f"predictive groups mismatch: got={actual} expected={expected}")


def test_report_contract() -> None:
    catalog, collection_context, predictive_search, _blueprint, quality_rules = task_inputs()
    expected = expected_products(catalog, collection_context)
    expected_groups = expected_search_groups(predictive_search)
    report = read_report()

    required = {"collection_handle", "rendered_product_count", "visible_filters", "sort_options", "search_groups", "product_cards", "quality_checks"}
    missing = sorted(required - set(report.keys()))
    if missing:
        raise AssertionError(f"missing report keys: {missing}")

    if report["collection_handle"] != collection_context["collection"]["handle"]:
        raise AssertionError("collection_handle mismatch")
    if int(report["rendered_product_count"]) != len(expected):
        raise AssertionError("rendered_product_count mismatch")
    actual_groups = []
    for item in report["search_groups"]:
        key = item.get("key") or item.get("id")
        label = item.get("label") or next(group["label"] for group in expected_groups if group["key"] == key)
        actual_groups.append({"key": key, "label": label, "count": item["count"]})
    if actual_groups != expected_groups:
        raise AssertionError(f"search_groups mismatch: got={actual_groups} expected={expected_groups}")
    if sorted(item["handle"] for item in report["product_cards"]) != sorted(item["handle"] for item in expected):
        raise AssertionError("report product handles mismatch")
    actual_availability = []
    for item in report["product_cards"]:
        value = item["availability"]
        if value in {"Sold out", "Low stock", "In stock"}:
            value = {"Sold out": "out_of_stock", "Low stock": "in_stock", "In stock": "in_stock"}[value]
        actual_availability.append(value)
    if actual_availability != [item["availability"] for item in expected]:
        raise AssertionError("report availability mismatch")
    reported_check_names = [item["name"] for item in report["quality_checks"]]
    missing_checks = [name for name in quality_rules["required_report_checks"] if name not in reported_check_names]
    if missing_checks:
        raise AssertionError(f"report quality checks mismatch: missing={missing_checks} reported={reported_check_names}")
    if any(not str(item["status"]).strip() for item in report["quality_checks"]):
        raise AssertionError("all quality checks should include a non-empty status")


def test_shopify_theme_check() -> None:
    result = run_cmd(["shopify", "theme", "check"], check=False)
    if result.returncode != 0:
        raise AssertionError(f"shopify theme check failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
