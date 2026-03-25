from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from enum import Enum


class EventKind(Enum):
    LOGIN = "login"
    DATA_ACCESS = "data_access"
    CONFIG_CHANGE = "config_change"
    OTHER = "other"


def merge_metadata(*sources: Mapping[str, str] | None) -> dict[str, str]:
    merged: dict[str, str] = {}
    for source in sources:
        if source:
            merged.update(source)
    return merged


def make_field_normalizer(
    aliases: Mapping[str, str] | None = None,
    default_value: str | None = None,
    transform: Callable[[str], str] | None = None,
) -> Callable[[str | None], str | None]:
    alias_map = {key.strip().lower(): value.strip().lower() for key, value in (aliases or {}).items()}
    final_transform = transform or (lambda value: value)

    def normalize(value: str | None) -> str | None:
        if value is None:
            return default_value

        stripped = value.strip()
        if not stripped:
            return default_value

        canonical = alias_map.get(stripped.lower(), stripped.lower())
        return final_transform(canonical)

    return normalize


@dataclass(frozen=True)
class AuditEvent:
    actor: str | None
    action: str
    resource: str | None = None
    tags: tuple[str, ...] = ()
    metadata: dict[str, str] | None = None

    def with_metadata(self, **kwargs: str) -> "AuditEvent":
        return AuditEvent(
            actor=self.actor,
            action=self.action,
            resource=self.resource,
            tags=self.tags,
            metadata=merge_metadata(self.metadata, kwargs),
        )


@dataclass(frozen=True)
class NormalizedEvent:
    actor: str
    action: str
    resource: str
    kind: EventKind
    tags: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)

    def with_metadata(self, **kwargs: str) -> "NormalizedEvent":
        return NormalizedEvent(
            actor=self.actor,
            action=self.action,
            resource=self.resource,
            kind=self.kind,
            tags=self.tags,
            metadata=merge_metadata(self.metadata, kwargs),
        )


class BaseNormalizer(ABC):
    @abstractmethod
    def normalize(self, event: AuditEvent) -> NormalizedEvent:
        raise NotImplementedError

    def normalize_batch(self, events: Iterable[AuditEvent]) -> Iterator[NormalizedEvent]:
        for event in events:
            yield self.normalize(event)


class AuditEventNormalizer(BaseNormalizer):
    def __init__(
        self,
        actor_aliases: Mapping[str, str] | None = None,
        resource_aliases: Mapping[str, str] | None = None,
        base_metadata: Mapping[str, str] | None = None,
    ) -> None:
        self._actor_aliases = dict(actor_aliases or {})
        self._resource_aliases = dict(resource_aliases or {})
        self._actor_normalizer = make_field_normalizer(self._actor_aliases, default_value="system")
        self._resource_normalizer = make_field_normalizer(self._resource_aliases, default_value="unknown-resource")
        self._action_normalizer = make_field_normalizer(transform=lambda value: value.replace(" ", "_"))
        self._base_metadata = merge_metadata(base_metadata)

    def infer_kind(self, action: str) -> EventKind:
        normalized = self._action_normalizer(action) or "unknown-action"
        if normalized in {"login", "sign_in"}:
            return EventKind.LOGIN
        if normalized.startswith("read_") or normalized.startswith("export_") or normalized in {"download", "view"}:
            return EventKind.DATA_ACCESS
        if normalized.startswith("config_") or normalized.startswith("rotate_") or normalized.endswith("_policy"):
            return EventKind.CONFIG_CHANGE
        return EventKind.OTHER

    def normalize(self, event: AuditEvent) -> NormalizedEvent:
        actor = self._actor_normalizer(event.actor) or "system"
        resource = self._resource_normalizer(event.resource) or "unknown-resource"
        action = self._action_normalizer(event.action) or "unknown-action"
        tags = tuple(sorted({tag.strip().lower() for tag in event.tags if tag.strip()}))
        metadata = merge_metadata(self._base_metadata, event.metadata)
        return NormalizedEvent(
            actor=actor,
            action=action,
            resource=resource,
            kind=self.infer_kind(action),
            tags=tags,
            metadata=metadata,
        )

    def with_metadata(self, **kwargs: str) -> "AuditEventNormalizer":
        return AuditEventNormalizer(
            actor_aliases=self._actor_aliases,
            resource_aliases=self._resource_aliases,
            base_metadata=merge_metadata(self._base_metadata, kwargs),
        )


def normalize_events(
    events: Iterable[AuditEvent],
    normalizer: AuditEventNormalizer | None = None,
) -> Iterator[NormalizedEvent]:
    selected = normalizer or AuditEventNormalizer()
    yield from selected.normalize_batch(events)
