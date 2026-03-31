"""Helpers to normalize and collect skillsmp search candidates."""

from __future__ import annotations

from typing import Any, Iterable
from urllib.parse import quote_plus

DEFAULT_LIMIT = 50
DEFAULT_TIMEOUT_SECONDS = 15

OFFICIAL_SEARCH_PATTERN = (
    "https://skillsmp.com/api/v1/skills/search?q={query}&limit={limit}&page={page}&sortBy=stars"
)
SEARCH_URL_PATTERNS = (
    OFFICIAL_SEARCH_PATTERN,
    "https://skillsmp.com/api/skills/search?query={query}&limit={limit}&page={page}",
    "https://skillsmp.com/api/skills?search={query}&limit={limit}",
)


BUCKET_QUERY_PARAM = "q"


def _build_patterns_from_bucket(bucket: dict[str, Any]) -> list[str]:
    custom = bucket.get("search_url_patterns")
    if isinstance(custom, list):
        patterns = [str(pattern) for pattern in custom if isinstance(pattern, str)]
        if patterns:
            return patterns
    base = bucket.get("search_base_url") or bucket.get("base_url") or "https://skillsmp.com"
    path = bucket.get("search_path") or "/api/v1/skills/search"
    param = bucket.get("query_param") or BUCKET_QUERY_PARAM
    base = base.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    first_pattern = (
        f"{base}{path}?{param}={{query}}&limit={{limit}}&page={{page}}&sortBy=stars"
    )
    return [first_pattern, *SEARCH_URL_PATTERNS[1:]]


class SearchSkillsMPError(RuntimeError):
    """Raised when the skillsmp search helpers cannot return candidates."""


def normalize_search_skill(raw: dict[str, Any], query: str | None = None) -> dict[str, Any]:
    """Return a normalized candidate shape from raw skillsmp search data."""

    def _coerce(value: Any, default: str = "") -> str:
        if value is None:
            return default
        return str(value)

    def _int(value: Any) -> int:
        try:
            return int(value)
        except Exception:  # pragma: no cover - defensive best effort
            return 0

    candidate_id = raw.get("id") or raw.get("skill_id") or raw.get("slug") or ""
    normalized = {
        "id": _coerce(candidate_id),
        "name": _coerce(raw.get("name")),
        "author": _coerce(raw.get("author")),
        "description": _coerce(raw.get("description")),
        "github_url": _coerce(raw.get("github_url") or raw.get("githubUrl")),
        "skillsmp_url": _coerce(raw.get("url") or raw.get("skillsmp_url") or raw.get("skillUrl")),
        "stars": _int(raw.get("stars") or raw.get("star_count")),
        "forks": _int(raw.get("forks") or raw.get("fork_count")),
        "queries": [query] if query else [],
    }
    return normalized


def dedupe_candidates(candidates: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate by skill id and sort with stable tie breaking."""

    merged: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        cid = candidate.get("id")
        if not cid:
            continue
        existing = merged.setdefault(cid, {**candidate, "queries": list(candidate.get("queries", []))})
        if existing is not candidate:
            # merge queries while preserving insertion order
            for query in candidate.get("queries", []):
                if query and query not in existing["queries"]:
                    existing["queries"].append(query)
            existing["stars"] = max(existing.get("stars", 0), candidate.get("stars", 0))
            existing["forks"] = max(existing.get("forks", 0), candidate.get("forks", 0))
    sorted_candidates = sorted(
        merged.values(),
        key=lambda item: (
            -int(item.get("stars", 0)),
            -int(item.get("forks", 0)),
            (item.get("name") or "").lower(),
            item.get("id") or "",
        ),
    )
    return sorted_candidates


def _extract_raw_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    nested_data = payload.get("data")
    if isinstance(nested_data, dict):
        raw_candidates = nested_data.get("skills") or nested_data.get("results") or []
    else:
        raw_candidates = payload.get("results") or payload.get("skills") or payload.get("data") or []
    if not isinstance(raw_candidates, list):
        return []
    return raw_candidates


def search_one_query(
    scraper: Any,
    query: str,
    limit: int = DEFAULT_LIMIT,
    page: int = 1,
    auth_token: str | None = None,
    url_patterns: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Run skillsmp search for a single query string."""

    attempted_errors: list[tuple[str, Exception]] = []
    encoded = quote_plus(query)
    patterns = list(url_patterns) if url_patterns else list(SEARCH_URL_PATTERNS)
    for pattern in patterns:
        url = pattern.format(query=encoded, limit=limit, page=page)
        try:
            request_kwargs: dict[str, Any] = {"timeout": DEFAULT_TIMEOUT_SECONDS}
            if auth_token:
                request_kwargs["headers"] = {"Authorization": f"Bearer {auth_token}"}
            response = scraper.get(url, **request_kwargs)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # pragma: no cover - upstream errors need manual troubleshooting
            attempted_errors.append((url, exc))
            continue
        raw_candidates = _extract_raw_candidates(payload)
        normalized = [normalize_search_skill(raw, query=query) for raw in raw_candidates]
        return normalized[:limit]
    message = "; ".join(f"{url} => {exc}" for url, exc in attempted_errors)
    raise SearchSkillsMPError(
        f"Failed to fetch skillsmp search results for '{query}'. Tried {len(SEARCH_URL_PATTERNS)} patterns."
        + (f" Details: {message}" if message else "")
    )


def _matches_exclude(candidate: dict[str, Any], exclude_terms: list[str]) -> bool:
    if not exclude_terms:
        return False
    haystack = " ".join(
        str(candidate.get(field, "")) for field in ("name", "description", "author")
    ).lower()
    return any(term.lower() in haystack for term in exclude_terms if term)


def search_bucket_candidates(scraper: Any, bucket: dict[str, Any]) -> list[dict[str, Any]]:
    """Discover candidates for the provided bucket config."""

    candidate_limit = bucket.get("candidate_limit") or DEFAULT_LIMIT
    target_limit = bucket.get("target_limit") or candidate_limit
    auth_token = bucket.get("auth_token") or bucket.get("api_key")
    page = bucket.get("page") or 1
    exclude_terms = [term for term in bucket.get("exclude_terms") or [] if isinstance(term, str)]
    url_patterns = _build_patterns_from_bucket(bucket)
    queries: list[str] = []
    for key in ("seed_queries", "expand_queries"):
        raw_queries = bucket.get(key)
        if not isinstance(raw_queries, list):
            continue
        for item in raw_queries:
            if isinstance(item, str) and item not in queries:
                queries.append(item)

    results: list[dict[str, Any]] = []
    for query in queries:
        page_candidates = search_one_query(
            scraper,
            query,
            limit=candidate_limit,
            page=page,
            auth_token=auth_token,
            url_patterns=url_patterns,
        )
        filtered = [candidate for candidate in page_candidates if not _matches_exclude(candidate, exclude_terms)]
        results.extend(filtered)
    deduped = dedupe_candidates(results)
    return deduped[:target_limit]
