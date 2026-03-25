import base64
import gzip
import sys
from pathlib import Path


ENCODED_PATH = Path(__file__).with_name("claim_payload.b64")


def main(output_path: str):
    encoded = ENCODED_PATH.read_text(encoding="ascii").strip()
    decoded = gzip.decompress(base64.b64decode(encoded))
    Path(output_path).write_bytes(decoded)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: write_response_payload.py <output.json>")
    main(sys.argv[1])
