from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

T = TypeVar("T")
MetricT = TypeVar("MetricT", int, float, Decimal)

META_KEYS = {"channel", "tags", "observed_at"}
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"


@runtime_checkable
class MessageLike(Protocol):
    def canonical_text(self) -> str: ...


class MessageProcessor(Protocol):
    def process(self, message: "CanonicalMessage") -> "CanonicalMessage": ...


class MessageKind(Enum):
    TEXT = "text"
    EVENT = "event"
    METRIC = "metric"
    EMPTY = "empty"


def normalize_whitespace(value: str) -> str:
    return " ".join(value.strip().split())


def normalize_token(value: str) -> str:
    return normalize_whitespace(value).lower()


def normalize_channel(value: Any) -> str | None:
    if value is None:
        return None

    normalized = normalize_token(str(value))
    return normalized or None


def normalize_tags(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        items = value
    else:
        items = [value]

    tags = {normalize_token(str(item)) for item in items if normalize_token(str(item))}
    return tuple(sorted(tags))


def normalize_observed_at(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.strftime(TIMESTAMP_FORMAT)

    normalized = normalize_whitespace(str(value))
    return normalized or None


def format_metric(value: int | float | Decimal, precision: int) -> str:
    if isinstance(value, int):
        return str(value)

    if not isinstance(value, Decimal):
        value = Decimal(str(value))

    quantum = Decimal(1).scaleb(-precision)
    rounded = value.quantize(quantum, rounding=ROUND_HALF_UP)
    rendered = format(rounded.normalize(), "f")
    return rendered.rstrip("0").rstrip(".") or "0"


def render_value(value: Any, precision: int) -> str | None:
    if value is None:
        return None

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, (int, float, Decimal)):
        return format_metric(value, precision)

    if isinstance(value, datetime):
        return value.strftime(TIMESTAMP_FORMAT)

    if isinstance(value, Mapping):
        fields: list[tuple[str, str]] = []
        for key, item in sorted(value.items(), key=lambda pair: normalize_token(str(pair[0]))):
            rendered = render_value(item, precision)
            if rendered is not None:
                fields.append((normalize_token(str(key)), rendered))
        return "{" + ",".join(f"{key}:{rendered}" for key, rendered in fields) + "}"

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        items = [render_value(item, precision) for item in value]
        return "[" + ",".join(item for item in items if item is not None) + "]"

    if isinstance(value, MessageLike):
        return normalize_whitespace(value.canonical_text())

    normalized = normalize_whitespace(str(value))
    return normalized or None


@dataclass(frozen=True)
class CanonicalMessage:
    body: str
    kind: MessageKind
    channel: str | None = None
    tags: tuple[str, ...] = ()
    attributes: dict[str, str] = field(default_factory=dict)
    observed_at: str | None = None

    def with_attributes(self, **kwargs: str) -> "CanonicalMessage":
        merged = {**self.attributes, **kwargs}
        return CanonicalMessage(
            body=self.body,
            kind=self.kind,
            channel=self.channel,
            tags=self.tags,
            attributes=merged,
            observed_at=self.observed_at,
        )

    def with_tags(self, *extra: str) -> "CanonicalMessage":
        merged = tuple(sorted({*self.tags, *(normalize_token(tag) for tag in extra if normalize_token(tag))}))
        return CanonicalMessage(
            body=self.body,
            kind=self.kind,
            channel=self.channel,
            tags=merged,
            attributes=self.attributes,
            observed_at=self.observed_at,
        )


class BaseCanonicalizer(ABC, Generic[T]):
    @abstractmethod
    def canonicalize(self, value: T) -> CanonicalMessage:
        raise NotImplementedError

    def canonicalize_batch(self, values: Iterable[T]) -> list[CanonicalMessage]:
        return [self.canonicalize(value) for value in values]


class TextCanonicalizer(BaseCanonicalizer[str | bytes | MessageLike]):
    def __init__(self, lowercase: bool = True) -> None:
        self.lowercase = lowercase

    def canonicalize(self, value: str | bytes | MessageLike) -> CanonicalMessage:
        if isinstance(value, bytes):
            raw = value.decode("utf-8")
        elif isinstance(value, MessageLike):
            raw = value.canonical_text()
        else:
            raw = value

        normalized = normalize_whitespace(raw)
        body = normalized.lower() if self.lowercase else normalized
        kind = MessageKind.TEXT if body else MessageKind.EMPTY
        return CanonicalMessage(body=body, kind=kind)


class MetricCanonicalizer(BaseCanonicalizer[MetricT]):
    def __init__(self, precision: int = 2) -> None:
        self.precision = precision

    def canonicalize(self, value: MetricT) -> CanonicalMessage:
        body = format_metric(value, self.precision)
        return CanonicalMessage(
            body=body,
            kind=MessageKind.METRIC,
            channel="metrics",
            attributes={"source_type": type(value).__name__},
        )


class StructuredCanonicalizer(BaseCanonicalizer[Mapping[str, Any]]):
    def __init__(self, precision: int = 2) -> None:
        self.precision = precision

    def canonicalize(self, value: Mapping[str, Any]) -> CanonicalMessage:
        fields: list[tuple[str, str]] = []

        for key, item in sorted(value.items(), key=lambda pair: normalize_token(str(pair[0]))):
            if key in META_KEYS:
                continue

            rendered = render_value(item, self.precision)
            if rendered is not None:
                fields.append((normalize_token(str(key)), rendered))

        body = "{" + ",".join(f"{key}:{rendered}" for key, rendered in fields) + "}" if fields else ""
        kind = MessageKind.EVENT if fields else MessageKind.EMPTY

        return CanonicalMessage(
            body=body,
            kind=kind,
            channel=normalize_channel(value.get("channel")),
            tags=normalize_tags(value.get("tags")),
            attributes={"field_count": str(len(fields))},
            observed_at=normalize_observed_at(value.get("observed_at")),
        )


class MessagePipeline:
    def __init__(self, processors: Sequence[MessageProcessor] | None = None) -> None:
        self.processors = list(processors or [])
        self._text = TextCanonicalizer()
        self._metric = MetricCanonicalizer()
        self._structured = StructuredCanonicalizer()

    def canonicalize_message(self, value: Any) -> CanonicalMessage:
        if value is None:
            message = CanonicalMessage(body="", kind=MessageKind.EMPTY)
        elif isinstance(value, CanonicalMessage):
            message = value
        elif isinstance(value, (str, bytes, MessageLike)):
            message = self._text.canonicalize(value)
        elif isinstance(value, Mapping):
            message = self._structured.canonicalize(value)
        elif isinstance(value, (int, float, Decimal)):
            message = self._metric.canonicalize(value)
        else:
            message = self._text.canonicalize(str(value))

        for processor in self.processors:
            message = processor.process(message)

        return message

    def run(self, values: Iterable[Any]) -> list[CanonicalMessage]:
        return [self.canonicalize_message(value) for value in values]


def canonicalize_message(value: Any, processors: Sequence[MessageProcessor] | None = None) -> CanonicalMessage:
    return MessagePipeline(processors).canonicalize_message(value)


def canonicalize_batch(values: Iterable[Any], processors: Sequence[MessageProcessor] | None = None) -> list[CanonicalMessage]:
    return MessagePipeline(processors).run(values)


def summarize_by_kind(messages: Iterable[CanonicalMessage]) -> dict[str, int]:
    summary: dict[str, int] = {}

    for message in messages:
        summary[message.kind.value] = summary.get(message.kind.value, 0) + 1

    return summary
