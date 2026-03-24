from __future__ import annotations

import argparse
import sys
import tarfile
from pathlib import Path


EXPECTED_COPY_LINE = "COPY packaging/release/ /opt/harbor/release/"


def build_bundle(repo_root: Path, dockerfile: Path, output: Path) -> int:
    dockerfile_text = dockerfile.read_text()
    if EXPECTED_COPY_LINE not in dockerfile_text:
        print(
            "Dockerfile does not copy packaging/release/ into /opt/harbor/release/.",
            file=sys.stderr,
        )
        return 1

    required_files = [
        repo_root / "packaging" / "release" / "release-manifest.json",
        repo_root / "packaging" / "release" / "entrypoint.sh",
        repo_root / "src" / "app" / "main.py",
        repo_root / "src" / "app" / "version.txt",
    ]
    for path in required_files:
        if not path.exists():
            print(f"Missing required release asset: {path}", file=sys.stderr)
            return 1

    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz") as archive:
        archive.add(
            repo_root / "packaging" / "release" / "release-manifest.json",
            arcname="release/release-manifest.json",
        )
        archive.add(
            repo_root / "packaging" / "release" / "entrypoint.sh",
            arcname="release/entrypoint.sh",
        )
        archive.add(repo_root / "src" / "app" / "main.py", arcname="app/main.py")
        archive.add(
            repo_root / "src" / "app" / "version.txt",
            arcname="app/version.txt",
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--dockerfile", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    return build_bundle(args.repo_root, args.dockerfile, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
