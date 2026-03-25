import json
import os
import tomllib
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup


APP_ROOT = Path(os.environ.get("APP_ROOT", "/app"))

OUTPUT_PATH = APP_ROOT / "output" / "relocation_weekend_board.html"
CANDIDATES_PATH = APP_ROOT / "data" / "relocation_candidates.toml"
RULES_PATH = APP_ROOT / "data" / "weekend_board_rules.json"
ATTRACTIONS_PATH = APP_ROOT / "data" / "attractions" / "attractions.csv"


def load_candidates():
    return tomllib.loads(CANDIDATES_PATH.read_text())


def load_rules():
    return json.loads(RULES_PATH.read_text())


def load_soup():
    return BeautifulSoup(OUTPUT_PATH.read_text(), "html.parser")


def build_lookup():
    frame = pd.read_csv(ATTRACTIONS_PATH)
    frame = frame[["City", "Name", "Address", "Website"]].dropna().drop_duplicates()
    lookup = {}
    for _, row in frame.iterrows():
        city = str(row["City"]).strip()
        triple = (
            str(row["Name"]),
            str(row["Address"]),
            str(row["Website"]),
        )
        lookup.setdefault(city, set()).add(triple)
    return lookup


def get_city_sections(soup):
    main = soup.select_one("main#relocation-weekend-board")
    assert main is not None, "Missing main#relocation-weekend-board"
    return main.find_all("section", class_="city-board", recursive=False)


def test_output_exists():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"


def test_page_title_and_intro_match_inputs():
    soup = load_soup()
    candidates = load_candidates()

    assert soup.title is not None, "Missing <title>"
    assert soup.title.get_text(strip=True) == candidates["page_title"]

    heading = soup.find("h1")
    assert heading is not None, "Missing top-level <h1>"
    assert heading.get_text(strip=True) == candidates["page_title"]

    intro = soup.select_one("p#board-intro")
    assert intro is not None, "Missing p#board-intro"
    assert intro.get_text(" ", strip=True) == candidates["intro_note"]


def test_city_sections_follow_input_order():
    soup = load_soup()
    candidates = load_candidates()
    sections = get_city_sections(soup)

    expected_cities = [city["city"] for city in candidates["cities"]]
    assert [section.get("data-city") for section in sections] == expected_cities

    for section, city in zip(sections, candidates["cities"]):
        heading = section.find("h2")
        assert heading is not None, f"Missing city heading for {city['city']}"
        assert heading.get_text(strip=True) == city["label"]

        angle = section.find("p", class_="weekend-angle")
        assert angle is not None, f"Missing weekend angle for {city['city']}"
        assert angle.get_text(" ", strip=True) == city["weekend_angle"]


def test_group_order_and_card_counts_match_rules():
    soup = load_soup()
    rules = load_rules()
    sections = get_city_sections(soup)

    expected_order = rules["group_order"]
    expected_counts = rules["cards_per_group"]

    for section in sections:
        groups = section.find_all("div", class_="group-column")
        assert [group.get("data-group") for group in groups] == expected_order

        for group in groups:
            group_name = group.get("data-group")
            cards = group.find_all("article", class_="attraction-card")
            assert len(cards) == expected_counts[group_name]


def test_cards_match_city_dataset_and_have_required_fields():
    soup = load_soup()
    rules = load_rules()
    candidates = load_candidates()
    lookup = build_lookup()
    sections = get_city_sections(soup)

    for section, city in zip(sections, candidates["cities"]):
        city_name = city["city"]
        assert city_name in lookup, f"City not found in attraction data: {city_name}"

        seen_names = set()
        card_count = 0

        for group in section.find_all("div", class_="group-column"):
            for card in group.find_all("article", class_="attraction-card"):
                name_node = card.find(class_="attraction-name")
                address_node = card.find(class_="attraction-address")
                link_node = card.find("a")

                assert name_node is not None, f"Missing attraction name in {city_name}"
                assert address_node is not None, f"Missing attraction address in {city_name}"
                assert link_node is not None, f"Missing attraction link in {city_name}"

                name = name_node.get_text(" ", strip=True)
                address = address_node.get_text(" ", strip=True)
                website = link_node.get("href", "").strip()

                assert name, f"Blank attraction name in {city_name}"
                assert address, f"Blank attraction address in {city_name}"
                assert website, f"Blank attraction website in {city_name}"
                assert link_node.get_text(" ", strip=True) == rules["link_text"]

                triple = (name, address, website)
                assert triple in lookup[city_name], f"Attraction does not match dataset for {city_name}: {triple}"
                assert name not in seen_names, f"Duplicate attraction within {city_name}: {name}"
                seen_names.add(name)
                card_count += 1

        assert card_count == sum(rules["cards_per_group"].values())
