from __future__ import annotations

import json
import os
from pathlib import Path
import time
import tomllib
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import requests

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com"
DEFAULT_CODEX_CONFIG_PATH = Path.home() / ".codex" / "config.toml"
DEFAULT_CODEX_AUTH_PATH = Path.home() / ".codex" / "auth.json"
OPENAI_REVIEW_USER_AGENT = "Harbor-top20-search/1.0"
OPENAI_REVIEW_MAX_RETRIES = 2
OPENAI_REVIEW_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class OpenAIReviewError(RuntimeError):
    """Raised when OpenAI review request cannot be completed."""


def resolve_openai_api_key(auth_path: Path | str = DEFAULT_CODEX_AUTH_PATH) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if api_key:
        return api_key

    codex_auth_path = Path(auth_path)
    if codex_auth_path.exists():
        try:
            payload = json.loads(codex_auth_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise OpenAIReviewError(f"Failed to read Codex auth config for OpenAI API key: {exc}") from exc
        if isinstance(payload, dict):
            api_key = str(payload.get("OPENAI_API_KEY") or "").strip()
            if api_key:
                return api_key

    raise OpenAIReviewError("OPENAI_API_KEY is required for bucket review")


def _build_responses_url(base_url: str) -> str:
    parsed = urlsplit(base_url.strip().rstrip("/"))
    path = parsed.path.rstrip("/")
    if path.endswith("/v1"):
        response_path = f"{path}/responses"
    else:
        response_path = f"{path}/v1/responses"
    return urlunsplit((parsed.scheme, parsed.netloc, response_path, "", ""))


def resolve_openai_base_url(config_path: Path | str = DEFAULT_CODEX_CONFIG_PATH) -> str:
    env_base_url = os.environ.get("OPENAI_BASE_URL", "").strip()
    if env_base_url:
        return env_base_url

    codex_config_path = Path(config_path)
    if codex_config_path.exists():
        try:
            payload = tomllib.loads(codex_config_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise OpenAIReviewError(f"Failed to read Codex config for OpenAI base URL: {exc}") from exc

        if isinstance(payload, dict):
            provider_name = str(payload.get("model_provider") or "").strip()
            providers = payload.get("model_providers")
            if provider_name and isinstance(providers, dict):
                provider = providers.get(provider_name)
                if isinstance(provider, dict):
                    base_url = str(provider.get("base_url") or "").strip()
                    if base_url:
                        return base_url

    return DEFAULT_OPENAI_BASE_URL


def _extract_structured_output_text(payload: dict[str, Any]) -> str:
    output = payload.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    return text
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    raise KeyError("structured output text not found")


def request_structured_review(*, model: str, system_prompt: str, user_prompt: str) -> dict[str, Any]:
    api_key = resolve_openai_api_key()
    request_url = _build_responses_url(resolve_openai_base_url())
    request_payload: dict[str, Any] = {
        "model": model,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "bucket_review_decision",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "selected",
                        "decision",
                        "summary",
                        "matched_keep_rules",
                        "matched_drop_rules",
                        "confidence",
                    ],
                    "properties": {
                        "selected": {"type": "boolean"},
                        "decision": {"type": "string", "enum": ["keep", "drop"]},
                        "summary": {"type": "string"},
                        "matched_keep_rules": {"type": "array", "items": {"type": "string"}},
                        "matched_drop_rules": {"type": "array", "items": {"type": "string"}},
                        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                    },
                },
            }
        },
    }

    response: requests.Response | Any | None = None
    for attempt in range(OPENAI_REVIEW_MAX_RETRIES + 1):
        try:
            response = requests.post(
                request_url,
                json=request_payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": OPENAI_REVIEW_USER_AGENT,
                },
                timeout=60,
            )
            response.raise_for_status()
            break
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code in OPENAI_REVIEW_RETRYABLE_STATUS_CODES and attempt < OPENAI_REVIEW_MAX_RETRIES:
                time.sleep(min(2 ** attempt, 5))
                continue
            body = ""
            if exc.response is not None:
                body = (exc.response.text or "").strip()
            if body:
                raise OpenAIReviewError(f"OpenAI request failed: {exc}. Response body: {body[:400]}") from exc
            raise OpenAIReviewError(f"OpenAI request failed: {exc}") from exc
        except requests.RequestException as exc:
            raise OpenAIReviewError(f"OpenAI request failed: {exc}") from exc
    else:  # pragma: no cover - defensive; loop exits via break or exception
        raise OpenAIReviewError("OpenAI request failed after retries")

    try:
        payload = response.json()
        output_text = _extract_structured_output_text(payload)
        parsed = json.loads(output_text)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise OpenAIReviewError("Invalid OpenAI response payload for structured review") from exc

    parsed["raw_response_id"] = str(payload.get("id", ""))
    return parsed
