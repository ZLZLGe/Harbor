from __future__ import annotations

from hashlib import sha1
from typing import Any


Condition = dict[str, Any]
RuleSpec = dict[str, Any]
FlagSpec = dict[str, Any]


def stable_bucket(flag_key: str, salt: str | None, bucket_key: str) -> float:
    seed = f"{flag_key}:{salt or ''}:{bucket_key}".encode("utf-8")
    digest = sha1(seed).hexdigest()
    bucket = int(digest[:8], 16) % 10000
    return bucket / 100.0


class FeatureFlagEngine:
    def __init__(self, flags: list[FlagSpec]):
        self._flags = {flag["key"]: flag for flag in flags}

    def evaluate(self, flag_key: str, subject: dict[str, Any]) -> dict[str, Any] | None:
        flag = self._flags.get(flag_key)
        if flag is None:
            return None

        bucket_key = str(subject.get("bucketKey") or subject.get("id") or "anonymous")
        for rule in flag.get("rules", []):
            if self._matches(flag_key, bucket_key, subject, rule["when"]):
                return {
                    "flagKey": flag_key,
                    "variant": rule["variant"],
                    "matchedRule": rule.get("name"),
                }

        return {
            "flagKey": flag_key,
            "variant": flag.get("default", "off"),
            "matchedRule": None,
        }

    def evaluate_all(self, subject: dict[str, Any]) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}
        for flag_key in self._flags:
            results[flag_key] = self.evaluate(flag_key, subject)
        return results

    def _matches(
        self,
        flag_key: str,
        bucket_key: str,
        subject: dict[str, Any],
        condition: Condition,
    ) -> bool:
        op = condition["op"]
        if op == "always":
            return True
        if op == "eq":
            return subject.get(condition["field"]) == condition["value"]
        if op == "in":
            return subject.get(condition["field"]) in condition["values"]
        if op == "gte":
            actual = subject.get(condition["field"])
            return isinstance(actual, (int, float)) and actual >= condition["value"]
        if op == "bool":
            return subject.get(condition["field"]) is condition["value"]
        if op == "rollout":
            return stable_bucket(flag_key, condition.get("salt"), bucket_key) < float(condition["percentage"])
        if op == "all":
            return all(self._matches(flag_key, bucket_key, subject, part) for part in condition["conditions"])
        if op == "any":
            return any(self._matches(flag_key, bucket_key, subject, part) for part in condition["conditions"])
        if op == "not":
            return not self._matches(flag_key, bucket_key, subject, condition["condition"])
        raise ValueError(f"unknown operation: {op}")


SAMPLE_FLAGS: list[FlagSpec] = [
    {
        "key": "search-ranking",
        "default": "ranking-v1",
        "rules": [
            {
                "name": "vip-pilot",
                "variant": "ranking-v2",
                "when": {
                    "op": "all",
                    "conditions": [
                        {"op": "in", "field": "plan", "values": ["pro", "enterprise"]},
                        {
                            "op": "any",
                            "conditions": [
                                {"op": "eq", "field": "region", "value": "us-east"},
                                {"op": "eq", "field": "region", "value": "eu-west"},
                            ],
                        },
                        {"op": "not", "condition": {"op": "bool", "field": "suspended", "value": True}},
                        {"op": "rollout", "percentage": 30.0, "salt": "beta"},
                    ],
                },
            }
        ],
    }
]
