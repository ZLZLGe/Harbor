from pathlib import Path

OUTPUT = Path("/root/donation_layout_shift_audit.md")

EXPECTED = """# Donation Layout Shift Audit

CLS Score: 0.312
Rating: poor

## Primary Causes
1. The hero image does not reserve its final height, so the opening copy shifts when the asset arrives.
2. The matching-gift banner mounts after first paint without a placeholder and pushes the donation form downward.
3. The receipt preview reflows when the custom font swaps in, which changes card height late in the session.

## Recommended Fix Order
1. Add intrinsic dimensions or an aspect-ratio box for the hero image.
2. Reserve banner space with a persistent container and a minimum height before the campaign copy loads.
3. Preload the receipt font or switch to a less disruptive font-display strategy.

Conclusion: Do not ship the page until CLS drops below the 0.25 blocker threshold.
"""


def main() -> None:
    assert OUTPUT.exists(), f"missing output file: {OUTPUT}"
    actual = OUTPUT.read_text()
    assert actual == EXPECTED, actual


if __name__ == "__main__":
    main()
