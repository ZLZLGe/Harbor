from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class TimeRange:
    start: datetime
    end: datetime

    def overlaps(self, other: "TimeRange") -> bool:
        return self.start < other.end and other.start < self.end

    def merge(self, other: "TimeRange") -> "TimeRange":
        return TimeRange(min(self.start, other.start), max(self.end, other.end))


@dataclass(frozen=True)
class ShiftTemplate:
    worker_id: str
    window: TimeRange
    repeat_every_days: int | None = None
    occurrence_count: int | None = 1
    until: datetime | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class BlockedWindow:
    window: TimeRange
    worker_id: str | None = None
    reason: str = ""


@dataclass(frozen=True)
class PlannerConfig:
    merge_gap_minutes: int | None = None
    label_prefix: str | None = None
    required_tags: tuple[str, ...] | None = None
    max_results: int | None = None
    default_repeat_days: int | None = None

    def normalized(self, defaults: "PlannerConfig | None" = None) -> "PlannerConfig":
        base = defaults or PlannerConfig(
            merge_gap_minutes=0,
            label_prefix="",
            required_tags=(),
            max_results=None,
            default_repeat_days=7,
        )
        return PlannerConfig(
            merge_gap_minutes=self.merge_gap_minutes if self.merge_gap_minutes is not None else base.merge_gap_minutes,
            label_prefix=self.label_prefix if self.label_prefix is not None else base.label_prefix,
            required_tags=self.required_tags if self.required_tags is not None else base.required_tags,
            max_results=self.max_results if self.max_results is not None else base.max_results,
            default_repeat_days=self.default_repeat_days if self.default_repeat_days is not None else base.default_repeat_days,
        )


@dataclass(frozen=True)
class PlannedShift:
    worker_id: str
    window: TimeRange
    label: str
    tags: tuple[str, ...] = ()


class ShiftWindowPlanner:
    @staticmethod
    def with_fallback_config(
        config: PlannerConfig | None = None,
        defaults: PlannerConfig | None = None,
    ) -> PlannerConfig:
        return (config or PlannerConfig()).normalized(defaults)

    @staticmethod
    def weekly(
        worker_id: str,
        start: datetime,
        end: datetime,
        weeks: int,
        tags: Iterable[str] = (),
    ) -> ShiftTemplate:
        return ShiftTemplate(
            worker_id=worker_id,
            window=TimeRange(start, end),
            repeat_every_days=7,
            occurrence_count=weeks,
            until=None,
            tags=tuple(tags),
        )

    @staticmethod
    def expand_recurring(
        template: ShiftTemplate,
        config: PlannerConfig | None = None,
    ) -> Iterator[PlannedShift]:
        normalized = ShiftWindowPlanner.with_fallback_config(config)
        repeat_days = template.repeat_every_days or normalized.default_repeat_days or 7
        label_suffix = template.tags[0] if template.tags else "shift"
        label = f"{normalized.label_prefix or ''}{template.worker_id}:{label_suffix}"

        def walk(window: TimeRange, index: int) -> Iterator[PlannedShift]:
            if template.occurrence_count is not None and index >= template.occurrence_count:
                return
            if template.until is not None and window.start > template.until:
                return

            yield PlannedShift(
                worker_id=template.worker_id,
                window=window,
                label=label,
                tags=template.tags,
            )

            if template.occurrence_count is None and template.until is None:
                return

            delta = timedelta(days=repeat_days)
            next_window = TimeRange(window.start + delta, window.end + delta)
            yield from walk(next_window, index + 1)

        return walk(template.window, 0)

    @staticmethod
    def filter_conflicts(
        candidates: Iterable[PlannedShift],
        blocked_windows: Iterable[BlockedWindow],
    ) -> Iterator[PlannedShift]:
        blocked = tuple(blocked_windows)
        for shift in candidates:
            if any(
                shift.window.overlaps(block.window)
                and (block.worker_id is None or block.worker_id == shift.worker_id)
                for block in blocked
            ):
                continue
            yield shift

    @staticmethod
    def merge_ranges(
        candidates: Iterable[PlannedShift],
        config: PlannerConfig | None = None,
    ) -> list[PlannedShift]:
        normalized = ShiftWindowPlanner.with_fallback_config(config)
        gap_minutes = normalized.merge_gap_minutes or 0
        ordered = sorted(
            candidates,
            key=lambda shift: (
                shift.worker_id,
                shift.label,
                shift.window.start,
                shift.window.end,
                shift.tags,
            ),
        )
        merged: list[PlannedShift] = []
        for shift in ordered:
            if not merged:
                merged.append(shift)
                continue

            last = merged[-1]
            gap = (shift.window.start - last.window.end).total_seconds() / 60
            if (
                last.worker_id == shift.worker_id
                and last.label == shift.label
                and last.tags == shift.tags
                and gap <= gap_minutes
            ):
                merged[-1] = PlannedShift(
                    worker_id=last.worker_id,
                    window=last.window.merge(shift.window),
                    label=last.label,
                    tags=last.tags,
                )
            else:
                merged.append(shift)
        return merged

    @staticmethod
    def plan(
        templates: Iterable[ShiftTemplate],
        blocked_windows: Iterable[BlockedWindow],
        config: PlannerConfig | None = None,
        defaults: PlannerConfig | None = None,
    ) -> list[PlannedShift]:
        normalized = ShiftWindowPlanner.with_fallback_config(config, defaults)
        required_tags = set(normalized.required_tags or ())

        expanded = (
            shift
            for template in templates
            for shift in ShiftWindowPlanner.expand_recurring(template, normalized)
        )
        tagged = (
            shift
            for shift in expanded
            if not required_tags or any(tag in required_tags for tag in shift.tags)
        )
        conflict_free = ShiftWindowPlanner.filter_conflicts(tagged, blocked_windows)
        merged = ShiftWindowPlanner.merge_ranges(conflict_free, normalized)

        if normalized.max_results is not None:
            return merged[: normalized.max_results]
        return merged
