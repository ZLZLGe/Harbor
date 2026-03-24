from pathlib import Path


def read_version() -> str:
    return Path(__file__).with_name("version.txt").read_text().strip()


if __name__ == "__main__":
    print(f"harbor release {read_version()}")
