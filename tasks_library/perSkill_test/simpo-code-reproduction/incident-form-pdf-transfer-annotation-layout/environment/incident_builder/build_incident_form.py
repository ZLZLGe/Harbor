import shutil
import sys
from pathlib import Path


ASSET_PATH = Path(__file__).with_name("terminal_incident_form.pdf")


def main(output_path: str):
    shutil.copyfile(ASSET_PATH, output_path)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: build_incident_form.py <output.pdf>")
    main(sys.argv[1])
