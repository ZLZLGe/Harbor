#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

from bs4 import BeautifulSoup


TASK_ROOT = Path(os.environ.get("TASK_ROOT", "/app"))
WORKSPACE_ROOT = TASK_ROOT / "workspace"
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", str(TASK_ROOT / "output")))
DECK_HTML_PATH = OUTPUT_ROOT / "deck" / "index.html"
QUOTE_PATH = WORKSPACE_ROOT / "data" / "customer_quotes.json"


def load_soup() -> BeautifulSoup:
    return BeautifulSoup(DECK_HTML_PATH.read_text(encoding="utf-8"), "html.parser")


def load_quotes() -> dict[str, dict[str, str]]:
    payload = json.loads(QUOTE_PATH.read_text(encoding="utf-8"))
    return {quote["quote_id"]: quote for quote in payload}


def ensure_quote_card(card: BeautifulSoup, quote: dict[str, str]) -> None:
    card["data-quote-id"] = quote["quote_id"]
    body = card.find("p")
    if body is None:
        body = card.new_tag("p")
        card.append(body)
    body.string = quote["quote_text"]

    byline = card.find("strong")
    if byline is None:
        byline = card.new_tag("strong")
        card.append(byline)
    byline.string = f'{quote["speaker_name"]}, {quote["speaker_role"]}'


def main() -> None:
    if not DECK_HTML_PATH.exists():
        raise SystemExit(f"missing deck html: {DECK_HTML_PATH}")

    quotes = load_quotes()
    soup = load_soup()

    journey_slide = soup.select_one('[data-slide-role="journey-diagram"]')
    if journey_slide is not None:
        journey_card = journey_slide.select_one(".quote-card")
        if journey_card is not None:
            ensure_quote_card(journey_card, quotes["q5"])

    risks_slide = soup.select_one('[data-slide-role="risks-next-steps"]')
    if risks_slide is not None:
        risk_cards = risks_slide.select(".risk-card p")
        if len(risk_cards) >= 1:
            risk_cards[0].string = (
                "External agency review still sits outside the strongest product workflow "
                "and should not be overclaimed in launch messaging."
            )
        if len(risk_cards) >= 2:
            risk_cards[1].string = (
                "The story is grounded in structured launch review and executive readiness "
                "visibility. It is not a replacement for every project management workflow."
            )
        quote_panel = risks_slide.select_one('.panel[data-quote-id], .quote-card[data-quote-id]')
        if quote_panel is not None:
            ensure_quote_card(quote_panel, quotes["q4"])

    DECK_HTML_PATH.write_text(str(soup), encoding="utf-8")
    print(f"Updated story fidelity markers in {DECK_HTML_PATH}")


if __name__ == "__main__":
    main()
