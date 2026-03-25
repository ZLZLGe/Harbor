import json
import sys
from pathlib import Path


def main() -> int:
    config = json.loads(Path(sys.argv[1]).read_text())
    output = Path(sys.argv[2])
    output.write_text(
        f"# {config['title']}\n\nOwner: {config['owner']}\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
