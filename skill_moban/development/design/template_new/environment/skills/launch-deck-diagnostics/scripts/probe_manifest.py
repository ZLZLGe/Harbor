#!/usr/bin/env python3
from __future__ import annotations

import json

from common import get_manifest


def main() -> None:
    payload = get_manifest()
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
