from __future__ import annotations

import argparse
import json
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from top20_search.src import fetch_skill_bundle

DEFAULT_INPUT_DIR = ROOT / "subcategory_top50"
DEFAULT_END_CATEGORY = "development"
DEFAULT_OUTPUT_DIR = ROOT / "downloads_until_development"
DEFAULT_JOBS = 8
WINDOWS_FORBIDDEN_OUTPUT_CHARS = set('<>:"/\\|?*')
WINDOWS_RESERVED_OUTPUT_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


class DownloadSubcategorySkillsError(RuntimeError):
    pass


IndexedRecord = tuple[int, dict[str, Any]]


def _sanitize_segment(value: Any, label: str) -> str:
    raw_value = str(value).strip()
    if not raw_value:
        raise DownloadSubcategorySkillsError(f"{label} 不能为空")
    if "/" in raw_value or "\\" in raw_value:
        raise DownloadSubcategorySkillsError(f"{label} 不能包含路径分隔符: {raw_value}")
    posix_path = PurePosixPath(raw_value)
    if posix_path.is_absolute():
        raise DownloadSubcategorySkillsError(f"{label} 不能是绝对路径: {raw_value}")
    if len(posix_path.parts) != 1 or any(part in ("", ".", "..") for part in posix_path.parts):
        raise DownloadSubcategorySkillsError(f"{label} 非法: {raw_value}")
    return posix_path.name


def list_category_dirs_until(input_dir: Path | str, end_category: str) -> list[Path]:
    base_dir = Path(input_dir)
    if not base_dir.exists():
        raise DownloadSubcategorySkillsError(f"输入目录不存在: {base_dir}")
    categories = sorted(path for path in base_dir.iterdir() if path.is_dir())
    selected: list[Path] = []
    for category_dir in categories:
        selected.append(category_dir)
        if category_dir.name == end_category:
            return selected
    raise DownloadSubcategorySkillsError(
        f"未在 {base_dir} 中找到截止目录: {end_category}"
    )


def collect_skill_records(input_dir: Path | str, end_category: str) -> tuple[list[dict[str, Any]], list[str]]:
    category_dirs = list_category_dirs_until(input_dir, end_category)
    records: list[dict[str, Any]] = []
    included_categories = [path.name for path in category_dirs]
    for category_dir in category_dirs:
        for yaml_path in sorted(category_dir.glob("*.yaml")):
            payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            if not isinstance(payload, dict):
                raise DownloadSubcategorySkillsError(f"YAML 顶层必须是映射: {yaml_path}")
            subcategory_slug = payload.get("subcategory_slug") or yaml_path.stem
            skills = payload.get("skills") or []
            if not isinstance(skills, list):
                raise DownloadSubcategorySkillsError(f"skills 字段必须是列表: {yaml_path}")
            for skill in skills:
                if not isinstance(skill, dict):
                    raise DownloadSubcategorySkillsError(f"skills 项必须是映射: {yaml_path}")
                records.append(
                    {
                        "category_slug": _sanitize_segment(category_dir.name, "category_slug"),
                        "subcategory_slug": _sanitize_segment(subcategory_slug, "subcategory_slug"),
                        "rank": int(skill.get("rank") or 0),
                        "id": _sanitize_segment(skill.get("id") or skill.get("name") or "unknown", "skill id"),
                        "name": str(skill.get("name") or ""),
                        "author": str(skill.get("author") or ""),
                        "github_url": str(skill.get("github_url") or "").strip(),
                        "source_yaml": str(yaml_path),
                    }
                )
    return records, included_categories


def _is_usable_output_skill_name(value: Any) -> bool:
    raw_name = str(value or "")
    if not raw_name:
        return False
    if raw_name != raw_name.strip():
        return False
    if raw_name[-1] in {" ", "."}:
        return False
    if any(ord(char) < 32 or char in WINDOWS_FORBIDDEN_OUTPUT_CHARS for char in raw_name):
        return False

    device_prefix = raw_name.split(".", 1)[0].upper()
    if device_prefix in WINDOWS_RESERVED_OUTPUT_NAMES:
        return False
    return True


def build_skill_output_dir(output_dir: Path | str, record: dict[str, Any]) -> Path:
    base_dir = Path(output_dir)
    rank = int(record["rank"])
    if _is_usable_output_skill_name(record.get("name")):
        skill_leaf = f"{rank:02d}__{record['name']}"
    else:
        skill_leaf = f"{rank:02d}"
    return (
        base_dir
        / _sanitize_segment(record["category_slug"], "category_slug")
        / _sanitize_segment(record["subcategory_slug"], "subcategory_slug")
        / skill_leaf
    )


def _prepare_output_dir(output_dir: Path | str) -> Path:
    target_dir = Path(output_dir)
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def _build_manifest_entry(
    record: dict[str, Any],
    *,
    status: str,
    url_kind: str,
    cache_hit: bool,
    output_dir: Path | None,
    error: str = "",
) -> dict[str, Any]:
    return {
        "category_slug": record["category_slug"],
        "subcategory_slug": record["subcategory_slug"],
        "rank": int(record["rank"]),
        "id": record["id"],
        "name": record["name"],
        "author": record["author"],
        "github_url": record["github_url"],
        "source_yaml": record["source_yaml"],
        "url_kind": url_kind,
        "status": status,
        "cache_hit": cache_hit,
        "output_dir": str(output_dir) if output_dir is not None else "",
        "error": error,
    }


def _infer_url_kind(github_url: str) -> str:
    parsed = urlparse(github_url)
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.netloc == "github.com" and len(parts) >= 5 and parts[2] == "tree":
        return "tree"
    if parsed.netloc == "github.com" and len(parts) == 2:
        return "repo_root"
    return "tree"


def _positive_int(raw_value: str) -> int:
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"必须是正整数: {raw_value}") from exc
    if value < 1:
        raise argparse.ArgumentTypeError(f"必须是正整数: {raw_value}")
    return value


def _classify_group_result(github_url: str, error_text: str, url_kind: str | None = None) -> tuple[str, str]:
    resolved_url_kind = url_kind or _infer_url_kind(github_url)
    status = "skipped" if "missing SKILL.md/skill.md" in error_text else "failed"
    return status, resolved_url_kind


def _build_group_failure(
    indexed_records: list[IndexedRecord],
    *,
    github_url: str,
    error_text: str,
    url_kind: str | None = None,
) -> dict[str, Any]:
    status, resolved_url_kind = _classify_group_result(github_url, error_text, url_kind)
    log_prefix = "skip" if status == "skipped" else "fail"
    return {
        "entries": [
            {
                "index": index,
                "entry": _build_manifest_entry(
                    record,
                    status=status,
                    url_kind=resolved_url_kind,
                    cache_hit=position > 0,
                    output_dir=None,
                    error=error_text,
                ),
            }
            for position, (index, record) in enumerate(indexed_records)
        ],
        "log_lines": [
            f"{log_prefix} {record['id']}: {error_text}"
            for _position, (_index, record) in enumerate(indexed_records)
        ],
    }


def _process_github_url_group(
    *,
    github_url: str,
    indexed_records: list[IndexedRecord],
    output_root: Path,
    parse_url_fn: Callable[..., fetch_skill_bundle.ParsedGitHubDirectory],
    fetch_tree_files_fn: Callable[[fetch_skill_bundle.GitHubTreeRef], list[dict[str, Any]]],
    fetch_repo_root_files_fn: Callable[..., list[dict[str, Any]]],
    write_files_fn: Callable[[list[dict[str, Any]], Path | str], list[Path]],
) -> dict[str, Any]:
    try:
        parsed = parse_url_fn(github_url)
        if parsed.url_kind == "tree":
            files = fetch_tree_files_fn(parsed.ref)
        elif parsed.url_kind == "repo_root":
            files = fetch_repo_root_files_fn(parsed.ref)
        else:
            raise DownloadSubcategorySkillsError(f"未知 url_kind: {parsed.url_kind}")
    except (DownloadSubcategorySkillsError, fetch_skill_bundle.FetchSkillBundleError, ValueError) as exc:
        return _build_group_failure(
            indexed_records,
            github_url=github_url,
            error_text=str(exc),
        )

    written_dirs: list[Path] = []
    entries: list[dict[str, Any]] = []
    log_lines: list[str] = []
    try:
        for position, (index, record) in enumerate(indexed_records):
            target_dir = build_skill_output_dir(output_root, record)
            write_files_fn(files, target_dir)
            written_dirs.append(target_dir)
            action = "reuse" if position > 0 else "download"
            log_lines.append(f"{action} {record['id']}: {github_url} -> {target_dir}")
            entries.append(
                {
                    "index": index,
                    "entry": _build_manifest_entry(
                        record,
                        status="downloaded",
                        url_kind=parsed.url_kind,
                        cache_hit=position > 0,
                        output_dir=target_dir,
                        error="",
                    ),
                }
            )
    except Exception as exc:
        for path in written_dirs:
            shutil.rmtree(path, ignore_errors=True)
        return _build_group_failure(
            indexed_records,
            github_url=github_url,
            error_text=str(exc),
            url_kind=parsed.url_kind,
        )
    return {
        "entries": entries,
        "log_lines": log_lines,
    }


def run_download_flow(
    *,
    input_dir: Path | str = DEFAULT_INPUT_DIR,
    end_category: str = DEFAULT_END_CATEGORY,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    jobs: int = DEFAULT_JOBS,
    parse_url_fn: Callable[..., fetch_skill_bundle.ParsedGitHubDirectory] = fetch_skill_bundle.parse_github_directory_url,
    fetch_tree_files_fn: Callable[[fetch_skill_bundle.GitHubTreeRef], list[dict[str, Any]]] = fetch_skill_bundle.fetch_github_tree_directory_files,
    fetch_repo_root_files_fn: Callable[..., list[dict[str, Any]]] = fetch_skill_bundle.fetch_repo_root_directory_files,
    write_files_fn: Callable[[list[dict[str, Any]], Path | str], list[Path]] = fetch_skill_bundle.write_downloaded_skill_files,
    log_fn: Callable[[str], None] = print,
) -> dict[str, Any]:
    if jobs < 1:
        raise DownloadSubcategorySkillsError(f"jobs 必须 >= 1，收到: {jobs}")

    records, included_categories = collect_skill_records(input_dir, end_category)
    output_root = _prepare_output_dir(output_dir)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    entry_slots: list[dict[str, Any] | None] = [None] * len(records)
    grouped_records: dict[str, list[IndexedRecord]] = {}
    stats = {
        "total_records": len(records),
        "unique_github_urls": 0,
        "downloaded": 0,
        "skipped": 0,
        "failed": 0,
        "cache_hits": 0,
    }

    for index, record in enumerate(records):
        github_url = record["github_url"]
        if not github_url:
            entry_slots[index] = _build_manifest_entry(
                record,
                status="skipped",
                url_kind="missing",
                cache_hit=False,
                output_dir=None,
                error="github_url 为空",
            )
            log_fn(f"skip {record['id']}: missing github_url")
            continue
        grouped_records.setdefault(github_url, []).append((index, record))

    stats["unique_github_urls"] = len(grouped_records)
    stats["cache_hits"] = sum(len(indexed_records) - 1 for indexed_records in grouped_records.values())

    if grouped_records:
        max_workers = min(jobs, len(grouped_records))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _process_github_url_group,
                    github_url=github_url,
                    indexed_records=indexed_records,
                    output_root=output_root,
                    parse_url_fn=parse_url_fn,
                    fetch_tree_files_fn=fetch_tree_files_fn,
                    fetch_repo_root_files_fn=fetch_repo_root_files_fn,
                    write_files_fn=write_files_fn,
                ): github_url
                for github_url, indexed_records in grouped_records.items()
            }
            for future in as_completed(futures):
                result = future.result()
                for line in result["log_lines"]:
                    log_fn(line)
                for item in result["entries"]:
                    entry_slots[item["index"]] = item["entry"]

    entries: list[dict[str, Any]] = []
    for entry in entry_slots:
        if entry is None:
            raise DownloadSubcategorySkillsError("内部错误：存在未生成 manifest 的记录")
        entries.append(entry)
        if entry["status"] == "downloaded":
            stats["downloaded"] += 1
        elif entry["status"] == "skipped":
            stats["skipped"] += 1
        else:
            stats["failed"] += 1

    manifest = {
        "generated_at": generated_at,
        "scope": {
            "input_dir": str(Path(input_dir).resolve()),
            "end_category": end_category,
            "included_categories": included_categories,
        },
        "stats": stats,
        "entries": entries,
    }
    manifest_path = output_root / "download_manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    log_fn(
        json.dumps(
            {
                "output_dir": str(output_root.resolve()),
                "manifest_path": str(manifest_path.resolve()),
                "stats": stats,
            },
            ensure_ascii=False,
        )
    )
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download skills from subcategory_top50 snapshots.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Path to subcategory_top50 directory.",
    )
    parser.add_argument(
        "--end-category",
        type=str,
        default=DEFAULT_END_CATEGORY,
        help="Inclusive end category when category directories are sorted by name.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where downloaded skills will be written.",
    )
    parser.add_argument(
        "--jobs",
        type=_positive_int,
        default=DEFAULT_JOBS,
        help="Maximum number of unique GitHub URLs to process in parallel.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run_download_flow(
        input_dir=args.input_dir,
        end_category=args.end_category,
        output_dir=args.output_dir,
        jobs=args.jobs,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
