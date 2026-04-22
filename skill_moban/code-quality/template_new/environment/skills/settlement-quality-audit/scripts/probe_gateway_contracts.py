from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


TEXT_SUFFIXES = {
    ".py",
    ".ts",
    ".js",
    ".java",
    ".kt",
    ".go",
    ".rb",
    ".php",
    ".yaml",
    ".yml",
    ".json",
    ".proto",
    ".http",
    ".md",
}
SKIP_PARTS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
}
ROUTE_PATTERNS = [
    re.compile(r"@(get|post|put|patch|delete)\(\s*[\"']([^\"']+)", re.I),
    re.compile(r"\b(?:router|app|bp|blueprint|server|fastify)\.(get|post|put|patch|delete)\(\s*[\"']([^\"']+)", re.I),
    re.compile(r"^(GET|POST|PUT|PATCH|DELETE)\s+(\S+)", re.M),
]
ENUM_HINT = re.compile(r"\b(?:state|status|enum)\b", re.I)
TOKEN_HINT = re.compile(r"[A-Z][A-Z0-9_]{2,}|[a-z][a-z0-9_]{2,}")


def default_environment_root() -> Path:
    workspace_root = Path("/app/workspace")
    gateway_root = Path("/services/settlement-gateway")
    if workspace_root.exists() or gateway_root.exists():
        return Path("/")
    return Path(__file__).resolve().parents[3]


def scan_roots(root: Path, gateway_root: Path | None = None) -> list[Path]:
    preferred = [
        Path("/app/workspace"),
        gateway_root,
        Path("/services/settlement-gateway"),
        root / "workspace",
        root / "settlement-gateway",
    ]
    existing = [path for path in preferred if path is not None and path.exists()]
    return existing or [root]


def iter_files(root: Path, gateway_root: Path | None = None) -> Iterable[Path]:
    for scan_root in scan_roots(root, gateway_root):
        for path in scan_root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in SKIP_PARTS for part in path.parts):
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            try:
                if path.stat().st_size > 1024 * 1024:
                    continue
            except OSError:
                continue
            yield path


def normalize_path(raw: str) -> str:
    normalized = raw.strip().strip(",);")
    normalized = re.sub(r"https?://[^/]+", "", normalized)
    normalized = re.sub(r":[A-Za-z_][A-Za-z0-9_]*", "{param}", normalized)
    normalized = re.sub(r"\{[^}]+\}", "{param}", normalized)
    normalized = re.sub(r"<[^>]+>", "{param}", normalized)
    normalized = re.sub(r"/+", "/", normalized)
    return normalized or "/"


def extract_routes_from_text(text: str) -> set[tuple[str, str]]:
    routes: set[tuple[str, str]] = set()
    for pattern in ROUTE_PATTERNS:
        for method, path in pattern.findall(text):
            routes.add((method.upper(), normalize_path(path)))

    current_openapi_path: str | None = None
    for line in text.splitlines():
        path_match = re.match(r"^\s{0,8}(/[^:\s]+):\s*$", line)
        if path_match:
            current_openapi_path = normalize_path(path_match.group(1))
            continue
        method_match = re.match(r"^\s{2,}(get|post|put|patch|delete):\s*$", line, re.I)
        if current_openapi_path and method_match:
            routes.add((method_match.group(1).upper(), current_openapi_path))
    return routes


def extract_state_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for line in text.splitlines():
        if not ENUM_HINT.search(line):
            continue
        for token in TOKEN_HINT.findall(line):
            lowered = token.lower()
            if lowered in {"state", "status", "enum", "string", "type", "values", "value"}:
                continue
            tokens.add(token)
    return tokens


def collect(root: Path, gateway_root: Path | None = None) -> tuple[dict[str, set[tuple[str, str]]], dict[str, set[str]], dict[str, list[str]]]:
    route_map = {"gateway": set(), "workspace": set()}
    token_map = {"gateway": set(), "workspace": set()}
    sources: dict[str, list[str]] = defaultdict(list)

    for path in iter_files(root, gateway_root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        side = "gateway" if "settlement-gateway" in path.parts else "workspace"
        routes = extract_routes_from_text(text)
        tokens = extract_state_tokens(text)
        if routes or tokens:
            sources[side].append(str(path.relative_to(root)))
        route_map[side].update(routes)
        token_map[side].update(tokens)
    return route_map, token_map, sources


def print_report(root: Path, gateway_root: Path | None, show_matches: bool) -> None:
    route_map, token_map, sources = collect(root, gateway_root)
    gateway_only = sorted(route_map["gateway"] - route_map["workspace"])
    workspace_only = sorted(route_map["workspace"] - route_map["gateway"])
    shared = sorted(route_map["gateway"] & route_map["workspace"])
    gateway_tokens_only = sorted(token_map["gateway"] - token_map["workspace"])
    workspace_tokens_only = sorted(token_map["workspace"] - token_map["gateway"])

    print(f"environment_root: {root}")
    print(f"gateway_route_count: {len(route_map['gateway'])}")
    print(f"workspace_route_count: {len(route_map['workspace'])}")
    print()

    print("[gateway_sources]")
    for source in sources["gateway"][:12]:
        print(f"- {source}")
    if len(sources["gateway"]) > 12:
        print(f"- ... {len(sources['gateway']) - 12} more files")
    if not sources["gateway"]:
        print("- none")
    print()

    print("[workspace_sources]")
    for source in sources["workspace"][:12]:
        print(f"- {source}")
    if len(sources["workspace"]) > 12:
        print(f"- ... {len(sources['workspace']) - 12} more files")
    if not sources["workspace"]:
        print("- none")
    print()

    print("[routes_only_in_gateway]")
    if gateway_only:
        for method, path in gateway_only[:20]:
            print(f"- {method} {path}")
    else:
        print("- none")
    print()

    print("[routes_only_in_workspace]")
    if workspace_only:
        for method, path in workspace_only[:20]:
            print(f"- {method} {path}")
    else:
        print("- none")
    print()

    print("[state_tokens_only_in_gateway]")
    print("- " + ", ".join(gateway_tokens_only[:20]) if gateway_tokens_only else "- none")
    print()

    print("[state_tokens_only_in_workspace]")
    print("- " + ", ".join(workspace_tokens_only[:20]) if workspace_tokens_only else "- none")
    print()

    if show_matches:
        print("[shared_routes]")
        if shared:
            for method, path in shared[:20]:
                print(f"- {method} {path}")
        else:
            print("- none")
        print()

    verdicts = []
    if gateway_only:
        verdicts.append("gateway advertises routes the workspace does not obviously implement")
    if workspace_only:
        verdicts.append("workspace exposes routes not visible in gateway-facing contract files")
    if gateway_tokens_only or workspace_tokens_only:
        verdicts.append("state vocabulary drift detected")
    if not verdicts:
        verdicts.append("no obvious contract drift found from static route and enum extraction")
    print("verdict:", "; ".join(verdicts))


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare settlement gateway contract files against workspace implementation hints.")
    parser.add_argument("--root", type=Path, default=default_environment_root(), help="Environment root to scan.")
    parser.add_argument("--gateway-root", type=Path, default=None, help="Optional explicit gateway root to scan alongside the workspace.")
    parser.add_argument("--show-matches", action="store_true", help="Print shared routes as well.")
    args = parser.parse_args()

    print_report(args.root, args.gateway_root, args.show_matches)


if __name__ == "__main__":
    main()
