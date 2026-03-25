#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


ENTRY_PAGES = [
    "/home",
    "/landing/spring",
    "/pricing",
    "/blog/rollups",
    "/promo/bundle",
    "/docs/getting-started",
]

PAGES = [
    "/home",
    "/pricing",
    "/features/search",
    "/features/analytics",
    "/docs/getting-started",
    "/docs/api",
    "/blog/rollups",
    "/blog/performance",
    "/support/contact",
    "/checkout",
    "/account/billing",
]

MID_SESSION_EVENTS = ["view", "click", "scroll", "add_to_cart", "submit_form"]

DEVICES = ["desktop", "mobile", "tablet"]
REFERRERS = ["search", "email", "direct", "partner", "social"]


def _session_length(rng: random.Random) -> int:
    roll = rng.random()
    if roll < 0.08:
        return 1
    if roll < 0.35:
        return rng.randint(2, 5)
    if roll < 0.82:
        return rng.randint(6, 11)
    return rng.randint(12, 18)


def write_clickstream(path: str | Path, num_sessions: int, seed: int) -> None:
    rng = random.Random(seed)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    base_time = 1735689600

    with path.open("w", encoding="utf-8") as handle:
        for session_number in range(num_sessions):
            session_id = f"S{session_number:07d}"
            user_id = f"U{1000 + rng.randint(0, 8999)}"
            event_count = _session_length(rng)
            first_page = rng.choice(ENTRY_PAGES)
            converted = event_count > 1 and rng.random() < 0.22
            purchase_index = rng.randint(1, event_count - 1) if converted else -1

            event_time = base_time + session_number * 113 + rng.randint(0, 19)
            for event_index in range(event_count):
                if event_index == 0:
                    page = first_page
                    event_type = "view"
                elif event_index == purchase_index:
                    page = "/checkout/confirmation"
                    event_type = "purchase"
                else:
                    page = rng.choice(PAGES)
                    event_type = rng.choice(MID_SESSION_EVENTS)
                if event_index > 0:
                    event_time += rng.randint(5, 95)

                record = {
                    "session_id": session_id,
                    "user_id": user_id,
                    "event_time": event_time,
                    "page": page,
                    "event_type": event_type,
                    "device": rng.choice(DEVICES),
                    "referrer": rng.choice(REFERRERS),
                }
                handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic clickstream fixtures.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--num-sessions", type=int, required=True)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    write_clickstream(args.output, args.num_sessions, args.seed)


if __name__ == "__main__":
    main()
