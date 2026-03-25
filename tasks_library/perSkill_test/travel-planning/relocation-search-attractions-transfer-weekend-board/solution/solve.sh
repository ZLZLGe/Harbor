#!/bin/bash

set -euo pipefail

mkdir -p /app/output

python - <<'PY'
import html
import json
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, "/app/skills/search-attractions/scripts")
from search_attractions import Attractions


def pick_unique_cards(frame, count):
    cards = []
    seen = set()
    for _, row in frame.iterrows():
        name = str(row["Name"])
        if name in seen:
            continue
        cards.append(
            {
                "name": name,
                "address": str(row["Address"]),
                "website": str(row["Website"]),
            }
        )
        seen.add(name)
        if len(cards) == count:
            return cards
    raise ValueError(f"Not enough unique attractions for requested count: {count}")


app_root = Path("/app")
candidates = tomllib.loads((app_root / "data" / "relocation_candidates.toml").read_text())
rules = json.loads((app_root / "data" / "weekend_board_rules.json").read_text())

group_order = rules["group_order"]
cards_per_group = rules["cards_per_group"]
link_text = rules["link_text"]
cards_needed = sum(cards_per_group[group] for group in group_order)

attractions = Attractions(path=app_root / "data" / "attractions" / "attractions.csv")

parts = [
    "<!DOCTYPE html>",
    '<html lang="en">',
    "<head>",
    '  <meta charset="utf-8" />',
    "  <title>{}</title>".format(html.escape(candidates["page_title"])),
    "  <style>",
    "    body { font-family: Arial, sans-serif; margin: 32px; color: #1f2933; background: #f6f3ee; }",
    "    h1 { margin-bottom: 8px; }",
    "    #board-intro { max-width: 960px; margin-bottom: 24px; }",
    "    #relocation-weekend-board { display: grid; gap: 20px; }",
    "    .city-board { background: #ffffff; border: 1px solid #d6d0c4; border-radius: 12px; padding: 20px; }",
    "    .city-groups { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }",
    "    .group-column { background: #faf8f2; border-radius: 10px; padding: 14px; }",
    "    .group-column h3 { margin-top: 0; text-transform: capitalize; }",
    "    .attraction-card { background: #ffffff; border: 1px solid #e3ded2; border-radius: 8px; padding: 12px; margin-bottom: 12px; }",
    "    .attraction-card:last-child { margin-bottom: 0; }",
    "    .attraction-name { font-weight: 700; margin: 0 0 6px; }",
    "    .attraction-address { margin: 0 0 8px; }",
    "  </style>",
    "</head>",
    "<body>",
    "  <h1>{}</h1>".format(html.escape(candidates["page_title"])),
    '  <p id="board-intro">{}</p>'.format(html.escape(candidates["intro_note"])),
    '  <main id="relocation-weekend-board">',
]

for city_entry in candidates["cities"]:
    city = city_entry["city"]
    result = attractions.run(city)
    if isinstance(result, str):
        raise ValueError(f"No attraction data found for {city}: {result}")

    cards = pick_unique_cards(result, cards_needed)
    cursor = 0

    parts.append(
        '    <section class="city-board" data-city="{}">'.format(html.escape(city, quote=True))
    )
    parts.append("      <h2>{}</h2>".format(html.escape(city_entry["label"])))
    parts.append(
        '      <p class="weekend-angle">{}</p>'.format(html.escape(city_entry["weekend_angle"]))
    )
    parts.append('      <div class="city-groups">')

    for group in group_order:
        count = cards_per_group[group]
        group_cards = cards[cursor : cursor + count]
        cursor += count

        parts.append(
            '        <div class="group-column" data-group="{}">'.format(html.escape(group, quote=True))
        )
        parts.append("          <h3>{}</h3>".format(html.escape(group)))

        for card in group_cards:
            parts.append('          <article class="attraction-card">')
            parts.append(
                '            <p class="attraction-name">{}</p>'.format(html.escape(card["name"]))
            )
            parts.append(
                '            <p class="attraction-address">{}</p>'.format(html.escape(card["address"]))
            )
            parts.append(
                '            <a href="{}">{}</a>'.format(
                    html.escape(card["website"], quote=True),
                    html.escape(link_text),
                )
            )
            parts.append("          </article>")

        parts.append("        </div>")

    parts.append("      </div>")
    parts.append("    </section>")

parts.extend(["  </main>", "</body>", "</html>"])

(app_root / "output" / "relocation_weekend_board.html").write_text("\n".join(parts) + "\n")
PY
