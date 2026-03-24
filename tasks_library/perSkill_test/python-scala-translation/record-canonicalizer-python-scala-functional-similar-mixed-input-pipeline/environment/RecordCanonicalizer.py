"""
Record canonicalization pipeline for mixed ingest data.

The module intentionally mixes:
- higher-order text normalization
- optional metadata enrichment
- heterogeneous runtime dispatch
- lazy record batching
- streaming text segmentation
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Protocol, TypeVar, runtime_checkable

T = TypeVar("T")
NumericT = TypeVar("NumericT", int, float, Decimal)
MetadataFactory = Callable[[str, Any], dict[str, Any]]
TextNormalizer = Callable[[str], str]


@runtime_checkable
class CanonicalValue(Protocol):
    """Any object that knows how to describe itself canonically."""

    def canonical_value(self) -> str: ...


class FieldKind(Enum):
    TEXT = "text"
    NUMBER = "number"
    TEMPORAL = "temporal"
    FLAG = "flag"
    STRUCTURED = "structured"
    EMPTY = "empty"


@dataclass(frozen=True)
class CanonicalField:
    key: str
    value: str
    kind: FieldKind
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_metadata(self, **kwargs: Any) -> "CanonicalField":
        return CanonicalField(self.key, self.value, self.kind, {**self.metadata, **kwargs})


class BaseCanonicalizer(ABC, Callable[[str, T], CanonicalField]):
    @abstractmethod
    def canonicalize(self, key: str, value: T, metadata: dict[str, Any] | None = None) -> CanonicalField:
        raise NotImplementedError

    def __call__(self, key: str, value: T) -> CanonicalField:
        return self.canonicalize(key, value)

    def canonicalize_batch(
        self,
        entries: Iterable[tuple[str, T]],
        metadata: dict[str, Any] | None = None,
    ) -> Iterator[CanonicalField]:
        for key, value in entries:
            yield self.canonicalize(key, value, metadata)


def compose_normalizers(*normalizers: TextNormalizer) -> TextNormalizer:
    def apply_all(text: str) -> str:
        result = text
        for normalizer in normalizers:
            result = normalizer(result)
        return result

    return apply_all


class TextCanonicalizer(BaseCanonicalizer[str | bytes]):
    def __init__(
        self,
        *,
        key_normalizer: TextNormalizer | None = None,
        value_normalizer: TextNormalizer | None = None,
        encoding: str = "utf-8",
    ) -> None:
        self.key_normalizer = key_normalizer or (lambda text: text)
        self.value_normalizer = value_normalizer or (lambda text: text)
        self.encoding = encoding

    def canonicalize(self, key: str, value: str | bytes, metadata: dict[str, Any] | None = None) -> CanonicalField:
        normalized_key = self.key_normalizer(key)
        text = value.decode(self.encoding) if isinstance(value, bytes) else value
        normalized_value = self.value_normalizer(text)
        return CanonicalField(normalized_key, normalized_value, FieldKind.TEXT, metadata or {})


class NumericCanonicalizer(BaseCanonicalizer[NumericT]):
    def __init__(self, *, precision: int = 2, key_normalizer: TextNormalizer | None = None) -> None:
        self.precision = precision
        self.key_normalizer = key_normalizer or (lambda text: text)

    def canonicalize(self, key: str, value: NumericT, metadata: dict[str, Any] | None = None) -> CanonicalField:
        normalized_key = self.key_normalizer(key)
        if isinstance(value, int) and not isinstance(value, bool):
            rendered = str(value)
        else:
            rendered = f"{value:.{self.precision}f}"

        extra = {"original_type": type(value).__name__}
        if metadata:
            extra = {**metadata, **extra}

        return CanonicalField(normalized_key, rendered, FieldKind.NUMBER, extra)


class TemporalCanonicalizer(BaseCanonicalizer[datetime | date]):
    ISO_FORMAT = "%Y-%m-%dT%H:%M:%S"
    DATE_FORMAT = "%Y-%m-%d"

    def __init__(self, format_str: str | None = None, *, key_normalizer: TextNormalizer | None = None) -> None:
        self.format_str = format_str
        self.key_normalizer = key_normalizer or (lambda text: text)

    def canonicalize(self, key: str, value: datetime | date, metadata: dict[str, Any] | None = None) -> CanonicalField:
        normalized_key = self.key_normalizer(key)
        if self.format_str is not None:
            fmt = self.format_str
        elif isinstance(value, datetime):
            fmt = self.ISO_FORMAT
        else:
            fmt = self.DATE_FORMAT

        return CanonicalField(normalized_key, value.strftime(fmt), FieldKind.TEMPORAL, metadata or {})


def stream_text_segments(text: str) -> Iterator[tuple[int, str]]:
    index = 0
    current: list[str] = []

    for char in text:
        if char.isspace():
            if current:
                yield index, "".join(current)
                current.clear()
                index += 1
        else:
            current.append(char)

    if current:
        yield index, "".join(current)


class RecordCanonicalizer(BaseCanonicalizer[Any]):
    def __init__(
        self,
        *,
        key_normalizer: TextNormalizer | None = None,
        text_normalizer: TextNormalizer | None = None,
        precision: int = 2,
        default_metadata: dict[str, Any] | None = None,
    ) -> None:
        self.key_normalizer = key_normalizer or (lambda text: text)
        self.default_metadata = default_metadata or {}
        self._text = TextCanonicalizer(
            key_normalizer=self.key_normalizer,
            value_normalizer=text_normalizer,
        )
        self._numeric = NumericCanonicalizer(
            precision=precision,
            key_normalizer=self.key_normalizer,
        )
        self._temporal = TemporalCanonicalizer(key_normalizer=self.key_normalizer)

    def canonicalize(self, key: str, value: Any, metadata: dict[str, Any] | None = None) -> CanonicalField:
        merged = {**self.default_metadata, **(metadata or {})}

        if value is None:
            return CanonicalField(self.key_normalizer(key), "", FieldKind.EMPTY, merged)

        if isinstance(value, bool):
            return CanonicalField(self.key_normalizer(key), str(value).lower(), FieldKind.FLAG, merged)

        if isinstance(value, CanonicalValue):
            return CanonicalField(self.key_normalizer(key), value.canonical_value(), FieldKind.STRUCTURED, merged)

        if isinstance(value, (str, bytes)):
            return self._text.canonicalize(key, value, merged)

        if isinstance(value, (int, float, Decimal)):
            return self._numeric.canonicalize(key, value, merged)

        if isinstance(value, (datetime, date)):
            return self._temporal.canonicalize(key, value, merged)

        if isinstance(value, Mapping):
            return CanonicalField(
                self.key_normalizer(key),
                json.dumps(dict(value), sort_keys=True),
                FieldKind.STRUCTURED,
                {**merged, "structured": True},
            )

        if isinstance(value, Sequence):
            return CanonicalField(
                self.key_normalizer(key),
                json.dumps(list(value)),
                FieldKind.STRUCTURED,
                {**merged, "structured": True},
            )

        return CanonicalField(self.key_normalizer(key), str(value), FieldKind.TEXT, {**merged, "fallback": True})

    def canonicalize_record(
        self,
        record: Iterable[tuple[str, Any]] | Mapping[str, Any],
        metadata_factory: MetadataFactory | None = None,
    ) -> list[CanonicalField]:
        items = record.items() if isinstance(record, Mapping) else record
        result: list[CanonicalField] = []

        for key, value in items:
            generated = metadata_factory(key, value) if metadata_factory is not None else {}
            result.append(self.canonicalize(key, value, generated))

        return result

    def canonicalize_records(
        self,
        records: Iterable[Mapping[str, Any]],
        *,
        metadata_factory: MetadataFactory | None = None,
        batch_size: int = 2,
    ) -> Iterator[list[CanonicalField]]:
        bucket: list[list[CanonicalField]] = []

        for record in records:
            bucket.append(self.canonicalize_record(record, metadata_factory))
            if len(bucket) >= batch_size:
                yield [field for fields in bucket for field in fields]
                bucket = []

        if bucket:
            yield [field for fields in bucket for field in fields]


class CanonicalizerBuilder:
    def __init__(self) -> None:
        self._key_normalizer: TextNormalizer = lambda text: text
        self._text_normalizers: list[TextNormalizer] = []
        self._metadata: dict[str, Any] = {}
        self._precision = 2

    def with_key_normalizer(self, normalizer: TextNormalizer) -> "CanonicalizerBuilder":
        previous = self._key_normalizer
        self._key_normalizer = compose_normalizers(previous, normalizer)
        return self

    def with_text_normalizer(self, normalizer: TextNormalizer) -> "CanonicalizerBuilder":
        self._text_normalizers.append(normalizer)
        return self

    def with_metadata(self, **metadata: Any) -> "CanonicalizerBuilder":
        self._metadata.update(metadata)
        return self

    def with_precision(self, precision: int) -> "CanonicalizerBuilder":
        self._precision = precision
        return self

    def build(self) -> RecordCanonicalizer:
        text_normalizer = compose_normalizers(*self._text_normalizers) if self._text_normalizers else None
        return RecordCanonicalizer(
            key_normalizer=self._key_normalizer,
            text_normalizer=text_normalizer,
            precision=self._precision,
            default_metadata=self._metadata.copy(),
        )
