#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed the local blogwatcher database.")
    parser.add_argument("--bundle-root", default="/app/release-watch")
    parser.add_argument("--workspace-root", default="/app/workspace")
    parser.add_argument("--db-path", default="")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def blogwatcher_binary() -> str:
    binary = shutil.which("blogwatcher")
    if not binary:
        raise FileNotFoundError("blogwatcher is required in PATH")
    return binary


def append_audit_log(audit_log: Path, stage: str, args: list[str]) -> None:
    audit_log.parent.mkdir(parents=True, exist_ok=True)
    with audit_log.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "stage": stage,
                    "args": args,
                }
            )
            + "\n"
        )


def run_blogwatcher(db_path: Path, args: list[str], audit_log: Path) -> None:
    env = os.environ.copy()
    env["BLOGWATCHER_DB"] = str(db_path)
    append_audit_log(audit_log, "seed", args)
    subprocess.run(
        [blogwatcher_binary(), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )


@contextmanager
def mirror_server(data_root: Path, port: int) -> Iterator[None]:
    process = subprocess.Popen(
        [
            "python3",
            "-m",
            "http.server",
            str(port),
            "--bind",
            "127.0.0.1",
            "--directory",
            str(data_root),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(0.8)
        yield
    finally:
        process.terminate()
        process.wait(timeout=10)


def local_url(port: int, rel_path: str) -> str:
    return f"http://127.0.0.1:{port}/{rel_path.lstrip('/')}"


def main() -> int:
    args = parse_args()
    bundle_root = Path(args.bundle_root)
    workspace_root = Path(args.workspace_root)
    contract = load_json(bundle_root / "contracts" / "digest_contract.json")
    seed_state = load_json(bundle_root / contract["seed_state_file"])
    db_path = Path(args.db_path) if args.db_path else workspace_root / contract["state_db_file"]
    audit_log = workspace_root / contract["audit_log_file"]
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.unlink(missing_ok=True)

    data_root = bundle_root / "data"
    port = int(contract["local_server_port"])

    with mirror_server(data_root, port):
        for blog in seed_state["seeded_blogs"]:
            run_blogwatcher(
                db_path,
                [
                    "add",
                    blog["name"],
                    local_url(port, blog["homepage_snapshot"]),
                    "--feed-url",
                    local_url(port, blog["feed_snapshot"]),
                ],
                audit_log,
            )
        for blog in seed_state["legacy_blogs"]:
            blog_args = ["add", blog["name"], blog["url"]]
            if blog.get("feed_url"):
                blog_args.extend(["--feed-url", blog["feed_url"]])
            run_blogwatcher(db_path, blog_args, audit_log)

        for blog in seed_state["seeded_blogs"]:
            run_blogwatcher(db_path, ["scan", blog["name"]], audit_log)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("UPDATE articles SET is_read = 0")
        for blog in seed_state["seeded_blogs"]:
            conn.executemany(
                "UPDATE articles SET is_read = 1 WHERE url = ?",
                [(url,) for url in blog["mark_read_urls"]],
            )
        conn.commit()
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
