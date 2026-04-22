from __future__ import annotations

import argparse

from .pipeline import build_warehouse
from .publish import build_publish_bundle, publish_bundle, write_bundle_and_receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["build", "publish"])
    args = parser.parse_args()

    build_warehouse()
    if args.command == "build":
        return

    bundle = build_publish_bundle()
    receipt = publish_bundle(bundle)
    write_bundle_and_receipt(bundle, receipt)


if __name__ == "__main__":
    main()
