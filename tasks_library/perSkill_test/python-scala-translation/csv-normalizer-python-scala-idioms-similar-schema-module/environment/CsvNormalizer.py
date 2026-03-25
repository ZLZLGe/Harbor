"""Schema-driven CSV row normalization helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
from typing import Any, Optional, Union

NormalizedScalar = Union[str, int, Decimal, bool, tuple[str, ...]]
NormalizedCell = Optional[NormalizedScalar]
Parser = Callable[[str], NormalizedScalar]


class ColumnKind(Enum):
    TEXT = "text"
    INTEGER = "integer"
    DECIMAL = "decimal"
    FLAG = "flag"
    TAGS = "tags"


@dataclass(frozen=True)
class ColumnSpec:
    output_name: str
    source_name: str
    kind: ColumnKind
    required: bool = True
    aliases: tuple[str, ...] = ()
    default_raw: Optional[str] = None
    parser: Optional[Parser] = None

    def candidates(self) -> tuple[str, ...]:
        return (self.source_name, *self.aliases)


@dataclass(frozen=True)
class NormalizationIssue:
    column: str
    message: str
    raw_value: Optional[str] = None


@dataclass(frozen=True)
class NormalizedRow:
    values: dict[str, NormalizedCell]
    issues: tuple[NormalizationIssue, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_metadata(self, **extra: Any) -> "NormalizedRow":
        return NormalizedRow(self.values, self.issues, {**self.metadata, **extra})


def parse_integer(raw: str) -> int:
    return int(raw.strip())


def parse_decimal(raw: str) -> Decimal:
    value = Decimal(raw.strip())
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parse_flag(raw: str) -> bool:
    normalized = raw.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"unsupported flag value: {raw!r}")


def parse_tags(raw: str) -> tuple[str, ...]:
    return tuple(part.strip().lower() for part in raw.split("|") if part.strip())


DEFAULT_PARSERS: dict[ColumnKind, Parser] = {
    ColumnKind.TEXT: lambda value: value.strip(),
    ColumnKind.INTEGER: parse_integer,
    ColumnKind.DECIMAL: parse_decimal,
    ColumnKind.FLAG: parse_flag,
    ColumnKind.TAGS: parse_tags,
}


def catalog_schema() -> list[ColumnSpec]:
    return [
        ColumnSpec("sku", "sku", ColumnKind.TEXT),
        ColumnSpec("warehouse", "warehouse", ColumnKind.TEXT, aliases=("site",)),
        ColumnSpec("quantity", "qty", ColumnKind.INTEGER),
        ColumnSpec("unitPrice", "unit_price", ColumnKind.DECIMAL, required=False),
        ColumnSpec("active", "active", ColumnKind.FLAG, required=False, default_raw="yes"),
        ColumnSpec("tags", "labels", ColumnKind.TAGS, required=False),
    ]


class CsvNormalizer:
    def __init__(self, schema: Iterable[ColumnSpec], source_label: str) -> None:
        self.schema = list(schema)
        self.source_label = source_label

    def headers(self) -> list[str]:
        return [spec.output_name for spec in self.schema]

    def normalize_row(self, raw_row: Mapping[str, str], row_number: int) -> NormalizedRow:
        values: dict[str, NormalizedCell] = {}
        issues: list[NormalizationIssue] = []
        matched_inputs: list[str] = []

        for spec in self.schema:
            matched_key, raw_value = self._pick_value(spec, raw_row)
            if matched_key is not None:
                matched_inputs.append(matched_key)

            cleaned_value = raw_value.strip() if raw_value is not None else None
            resolved_value = cleaned_value or spec.default_raw

            if resolved_value is None and spec.required:
                values[spec.output_name] = None
                issues.append(
                    NormalizationIssue(
                        column=spec.output_name,
                        message="missing required value",
                        raw_value=raw_value,
                    )
                )
                continue

            if resolved_value is None:
                values[spec.output_name] = None
                continue

            parser = spec.parser or DEFAULT_PARSERS[spec.kind]
            try:
                values[spec.output_name] = parser(resolved_value)
            except (InvalidOperation, ValueError) as exc:
                values[spec.output_name] = None
                issues.append(
                    NormalizationIssue(
                        column=spec.output_name,
                        message=str(exc),
                        raw_value=resolved_value,
                    )
                )

        return NormalizedRow(values, tuple(issues)).with_metadata(
            source=self.source_label,
            rowNumber=row_number,
            matchedInputs=",".join(matched_inputs),
            issueCount=len(issues),
        )

    def normalize_rows(
        self,
        rows: Iterable[Mapping[str, str]],
        start_row: int = 1,
    ) -> Iterator[NormalizedRow]:
        for offset, row in enumerate(rows, start=start_row):
            yield self.normalize_row(row, offset)

    @staticmethod
    def _pick_value(
        spec: ColumnSpec,
        raw_row: Mapping[str, str],
    ) -> tuple[Optional[str], Optional[str]]:
        for candidate in spec.candidates():
            if candidate in raw_row:
                return candidate, raw_row[candidate]
        return None, None
