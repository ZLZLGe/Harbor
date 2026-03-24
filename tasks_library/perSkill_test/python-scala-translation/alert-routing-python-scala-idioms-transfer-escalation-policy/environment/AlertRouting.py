from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class DeliveryChannel(Enum):
    CHAT = "chat"
    EMAIL = "email"
    PAGER = "pager"
    PHONE = "phone"


def _normalize_token(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: list[str] = []
    for value in values:
        normalized = _normalize_token(value)
        if normalized and normalized not in seen:
            seen.append(normalized)
    return tuple(seen)


@dataclass(frozen=True)
class ScheduleWindow:
    name: str
    start_hour: int
    end_hour: int
    primary: tuple[str, ...]
    secondary: tuple[str, ...] = ()
    after_hours: bool = False

    def includes(self, hour: int) -> bool:
        normalized = hour % 24
        if self.start_hour == self.end_hour:
            return True
        if self.start_hour < self.end_hour:
            return self.start_hour <= normalized < self.end_hour
        return normalized >= self.start_hour or normalized < self.end_hour

    def targets_for(self, severity: Severity) -> tuple[str, ...]:
        if severity is Severity.CRITICAL:
            return _dedupe(self.primary + self.secondary)
        return _dedupe(self.primary)


@dataclass(frozen=True)
class EscalationPolicy:
    initial_channel: DeliveryChannel
    repeat_channel: DeliveryChannel | None = None
    repeat_after_minutes: int | None = None
    fallback_channel: DeliveryChannel | None = None
    suppress_after_hours: bool = False


@dataclass(frozen=True)
class Alert:
    service: str
    severity: Severity
    created_hour: int
    tags: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)
    summary: str = ""


@dataclass(frozen=True)
class EscalationStep:
    channel: DeliveryChannel
    targets: tuple[str, ...]
    delay_minutes: int
    note: str


@dataclass(frozen=True)
class RoutingDecision:
    service: str
    severity: Severity
    active_window: str | None
    steps: tuple[EscalationStep, ...]
    fallback_used: bool
    dedup_key: str


@dataclass
class ServicePolicy:
    service: str
    windows: list[ScheduleWindow]
    policies: dict[Severity, EscalationPolicy]
    fallback_targets: list[str] = field(default_factory=list)
    tag_overrides: dict[str, DeliveryChannel] = field(default_factory=dict)

    def find_window(self, hour: int) -> ScheduleWindow | None:
        for window in self.windows:
            if window.includes(hour):
                return window
        return None


class AlertRouter:
    def __init__(self, policies: dict[str, ServicePolicy]) -> None:
        self.policies = policies

    def resolve_service(self, service: str) -> ServicePolicy:
        return self.policies.get(service, self.policies["default"])

    def active_window(self, service: str, hour: int) -> ScheduleWindow | None:
        return self.resolve_service(service).find_window(hour)

    def route_alert(self, alert: Alert) -> RoutingDecision:
        service_policy = self.resolve_service(alert.service)
        escalation = service_policy.policies.get(alert.severity) or service_policy.policies[Severity.WARNING]
        active = service_policy.find_window(alert.created_hour)
        after_hours = active.after_hours if active is not None else True

        override_channel = None
        for tag in alert.tags:
            normalized_tag = _normalize_token(tag)
            if normalized_tag in service_policy.tag_overrides:
                override_channel = service_policy.tag_overrides[normalized_tag]
                break

        fallback_targets = _dedupe(service_policy.fallback_targets)

        if active is not None:
            base_targets = active.targets_for(alert.severity)
            repeat_targets = _dedupe(active.secondary) or fallback_targets
        else:
            base_targets = ()
            repeat_targets = fallback_targets

        using_fallback_targets = active is None or not base_targets
        initial_targets = base_targets or fallback_targets
        fallback_used = using_fallback_targets

        if escalation.suppress_after_hours and after_hours:
            channel = escalation.fallback_channel or escalation.initial_channel
            steps = (EscalationStep(channel, fallback_targets, 0, "after-hours digest"),)
            fallback_used = True
        else:
            initial_channel = override_channel or escalation.initial_channel
            if using_fallback_targets and escalation.fallback_channel is not None:
                initial_channel = escalation.fallback_channel
                fallback_used = True

            mutable_steps = [EscalationStep(initial_channel, initial_targets, 0, "tag override" if override_channel else "initial")]
            if escalation.repeat_channel is not None and escalation.repeat_after_minutes is not None and repeat_targets:
                mutable_steps.append(
                    EscalationStep(escalation.repeat_channel, repeat_targets, escalation.repeat_after_minutes, "escalation")
                )
                if repeat_targets == fallback_targets:
                    fallback_used = True
            steps = tuple(mutable_steps)

        normalized_tags = sorted({_normalize_token(tag) for tag in alert.tags if _normalize_token(tag)})
        dedup_key = f"{service_policy.service}:{alert.severity.value}:{','.join(normalized_tags)}"

        return RoutingDecision(
            service=service_policy.service,
            severity=alert.severity,
            active_window=active.name if active is not None else None,
            steps=steps,
            fallback_used=fallback_used,
            dedup_key=dedup_key,
        )

    def route_batch(self, alerts: Iterable[Alert]) -> list[RoutingDecision]:
        return [self.route_alert(alert) for alert in alerts]


def summarize_by_channel(decisions: Iterable[RoutingDecision]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for decision in decisions:
        for step in decision.steps:
            counts[step.channel.value] = counts.get(step.channel.value, 0) + 1
    return dict(sorted(counts.items()))


def escalation_targets(decision: RoutingDecision) -> tuple[str, ...]:
    combined: list[str] = []
    for step in decision.steps:
        for target in step.targets:
            normalized = _normalize_token(target)
            if normalized and normalized not in combined:
                combined.append(normalized)
    return tuple(combined)


def default_policies() -> dict[str, ServicePolicy]:
    shared_policies = {
        Severity.INFO: EscalationPolicy(
            initial_channel=DeliveryChannel.CHAT,
            fallback_channel=DeliveryChannel.EMAIL,
            suppress_after_hours=True,
        ),
        Severity.WARNING: EscalationPolicy(
            initial_channel=DeliveryChannel.CHAT,
            repeat_channel=DeliveryChannel.EMAIL,
            repeat_after_minutes=20,
            fallback_channel=DeliveryChannel.PHONE,
        ),
        Severity.CRITICAL: EscalationPolicy(
            initial_channel=DeliveryChannel.PAGER,
            repeat_channel=DeliveryChannel.PHONE,
            repeat_after_minutes=5,
            fallback_channel=DeliveryChannel.PHONE,
        ),
    }

    return {
        "payments": ServicePolicy(
            service="payments",
            windows=[
                ScheduleWindow(
                    name="business",
                    start_hour=8,
                    end_hour=18,
                    primary=("maya", "nico"),
                    secondary=("payments-manager",),
                ),
                ScheduleWindow(
                    name="overnight",
                    start_hour=18,
                    end_hour=8,
                    primary=("night-pay",),
                    secondary=("incident-commander",),
                    after_hours=True,
                ),
            ],
            policies=dict(shared_policies),
            fallback_targets=["payments-dispatch"],
            tag_overrides={"vip": DeliveryChannel.PAGER, "audit": DeliveryChannel.EMAIL},
        ),
        "platform": ServicePolicy(
            service="platform",
            windows=[
                ScheduleWindow(
                    name="day",
                    start_hour=9,
                    end_hour=17,
                    primary=("infra-east", "infra-west"),
                    secondary=("infra-manager",),
                ),
                ScheduleWindow(
                    name="overnight",
                    start_hour=17,
                    end_hour=9,
                    primary=("platform-night",),
                    secondary=("duty-director",),
                    after_hours=True,
                ),
            ],
            policies=dict(shared_policies),
            fallback_targets=["global-noc"],
            tag_overrides={"maintenance": DeliveryChannel.EMAIL},
        ),
        "default": ServicePolicy(
            service="default",
            windows=[],
            policies=dict(shared_policies),
            fallback_targets=["global-noc"],
            tag_overrides={},
        ),
    }


DEFAULT_POLICIES = default_policies()
DEFAULT_ROUTER = AlertRouter(DEFAULT_POLICIES)


def route_alert(alert: Alert, policies: dict[str, ServicePolicy] | None = None) -> RoutingDecision:
    return AlertRouter(policies or DEFAULT_POLICIES).route_alert(alert)


def route_batch(alerts: Iterable[Alert], policies: dict[str, ServicePolicy] | None = None) -> list[RoutingDecision]:
    return AlertRouter(policies or DEFAULT_POLICIES).route_batch(alerts)
