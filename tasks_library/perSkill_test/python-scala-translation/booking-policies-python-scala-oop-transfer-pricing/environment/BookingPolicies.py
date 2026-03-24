from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from math import floor
from typing import ClassVar, Iterable


def normalize_code(raw: str) -> str:
    return raw.strip().lower().replace("_", "-").replace(" ", "-")


def round_money(value: float) -> int:
    return int(floor(value + 0.5))


@dataclass(frozen=True)
class RoomType:
    code: str
    nightly_rate: int
    cleaning_fee: int
    city_fee: int
    max_guests: int
    amenities: tuple[str, ...] = ()

    CATALOG: ClassVar[dict[str, tuple[int, int, int, int, tuple[str, ...]]]] = {
        "studio": (120, 30, 6, 2, ("espresso", "desk")),
        "loft": (180, 45, 7, 3, ("balcony", "kitchen")),
        "suite": (260, 55, 9, 4, ("lounge", "tub")),
        "villa": (420, 90, 12, 6, ("garden", "pool")),
    }

    @classmethod
    def from_code(cls, code: str) -> "RoomType":
        normalized = normalize_code(code)
        nightly_rate, cleaning_fee, city_fee, max_guests, amenities = cls.CATALOG[normalized]
        return cls(
            code=normalized,
            nightly_rate=nightly_rate,
            cleaning_fee=cleaning_fee,
            city_fee=city_fee,
            max_guests=max_guests,
            amenities=amenities,
        )


@dataclass(frozen=True)
class BookingOrder:
    booking_id: str
    guest_name: str
    room_type: RoomType
    nights: int
    guests: int
    season: str = "regular"
    extras: tuple[str, ...] = ()
    vip: bool = False
    corporate_account: str = ""

    EXTRA_PRICES: ClassVar[dict[str, int]] = {
        "breakfast": 18,
        "parking": 14,
        "late-checkout": 25,
        "shuttle": 36,
    }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "BookingOrder":
        extras = tuple(normalize_code(str(extra)) for extra in payload.get("extras", ()))
        return cls(
            booking_id=str(payload["booking_id"]).strip(),
            guest_name=str(payload["guest_name"]).strip(),
            room_type=RoomType.from_code(str(payload["room_type"])),
            nights=int(payload["nights"]),
            guests=int(payload["guests"]),
            season=normalize_code(str(payload.get("season", "regular"))),
            extras=extras,
            vip=bool(payload.get("vip", False)),
            corporate_account=str(payload.get("corporate_account", "")).strip(),
        )

    @property
    def base_subtotal(self) -> int:
        return self.room_type.nightly_rate * self.nights

    @property
    def mandatory_fees(self) -> int:
        return self.room_type.cleaning_fee + self.room_type.city_fee * self.guests * self.nights

    @property
    def extras_total(self) -> int:
        return sum(self.EXTRA_PRICES[extra] for extra in self.extras)

    def has_extra(self, extra: str) -> bool:
        return normalize_code(extra) in self.extras


@dataclass(frozen=True)
class ChargeSummary:
    booking_id: str
    policy_code: str
    room_code: str
    base_subtotal: int
    mandatory_fees: int
    extras_total: int
    discount_amount: int
    service_charge: int
    total_due: int
    reward_points: int
    notes: tuple[str, ...] = ()

    @property
    def grand_fees(self) -> int:
        return self.mandatory_fees + self.extras_total + self.service_charge

    def render_line(self) -> str:
        notes = ",".join(self.notes)
        return f"{self.booking_id}|{self.policy_code}|{self.total_due}|{self.reward_points}|{notes}"


class DiscountPolicy(ABC):
    code: ClassVar[str] = "standard"
    service_rate: ClassVar[float] = 0.08

    def mandatory_fees(self, order: BookingOrder) -> int:
        return order.mandatory_fees

    def extras_total(self, order: BookingOrder) -> int:
        return order.extras_total

    @abstractmethod
    def discount_amount(self, order: BookingOrder) -> int:
        raise NotImplementedError

    def reward_points(self, order: BookingOrder, total_due: int) -> int:
        return total_due // 10

    def notes(self, order: BookingOrder) -> tuple[str, ...]:
        return (self.code, order.room_type.code)

    def quote(self, order: BookingOrder) -> ChargeSummary:
        fees = self.mandatory_fees(order)
        extras = self.extras_total(order)
        discount = self.discount_amount(order)
        service = round_money(max(order.base_subtotal - discount, 0) * self.service_rate)
        total_due = order.base_subtotal + fees + extras - discount + service
        return ChargeSummary(
            booking_id=order.booking_id,
            policy_code=self.code,
            room_code=order.room_type.code,
            base_subtotal=order.base_subtotal,
            mandatory_fees=fees,
            extras_total=extras,
            discount_amount=discount,
            service_charge=service,
            total_due=total_due,
            reward_points=self.reward_points(order, total_due),
            notes=self.notes(order),
        )


class StandardPolicy(DiscountPolicy):
    code = "standard"

    def discount_amount(self, order: BookingOrder) -> int:
        return 0

    def notes(self, order: BookingOrder) -> tuple[str, ...]:
        return ("rack-rate", order.room_type.code)


class MemberPolicy(DiscountPolicy):
    code = "member"
    service_rate = 0.05

    def discount_amount(self, order: BookingOrder) -> int:
        rate = 0.14 if order.vip else 0.10
        discount = round_money(order.base_subtotal * rate)
        if order.vip and order.season == "shoulder":
            discount += 15
        return discount

    def reward_points(self, order: BookingOrder, total_due: int) -> int:
        return total_due // 8 + (25 if order.vip else 0)

    def notes(self, order: BookingOrder) -> tuple[str, ...]:
        base = ["member-rate"]
        if order.vip:
            base.append("vip-benefit")
        return tuple(base)


class CorporatePolicy(DiscountPolicy):
    code = "corporate"
    service_rate = 0.03

    def discount_amount(self, order: BookingOrder) -> int:
        return round_money(order.base_subtotal * 0.18)

    def mandatory_fees(self, order: BookingOrder) -> int:
        city_component = round_money(order.room_type.city_fee * order.guests * order.nights * 0.5)
        return order.room_type.cleaning_fee + city_component

    def reward_points(self, order: BookingOrder, total_due: int) -> int:
        return 0

    def notes(self, order: BookingOrder) -> tuple[str, ...]:
        label = order.corporate_account or "house-account"
        return ("corporate-rate", label)


class LongStayPolicy(DiscountPolicy):
    code = "long-stay"
    service_rate = 0.04

    def discount_amount(self, order: BookingOrder) -> int:
        if order.nights >= 7:
            rate = 0.15
        elif order.nights >= 4:
            rate = 0.07
        else:
            rate = 0.0
        return round_money(order.base_subtotal * rate)

    def mandatory_fees(self, order: BookingOrder) -> int:
        if order.nights >= 7:
            return order.room_type.city_fee * order.guests * order.nights
        return order.mandatory_fees

    def reward_points(self, order: BookingOrder, total_due: int) -> int:
        return total_due // 12 + (15 if order.nights >= 7 else 0)

    def notes(self, order: BookingOrder) -> tuple[str, ...]:
        return ("extended-stay", f"nights={order.nights}")


class FamilyPolicy(DiscountPolicy):
    code = "family"
    service_rate = 0.05

    def discount_amount(self, order: BookingOrder) -> int:
        rate = 0.12 if order.guests >= 3 else 0.05
        return round_money(order.base_subtotal * rate)

    def mandatory_fees(self, order: BookingOrder) -> int:
        total = order.mandatory_fees
        if order.guests >= 3:
            total -= order.room_type.city_fee * order.nights
        return total

    def extras_total(self, order: BookingOrder) -> int:
        total = order.extras_total
        if order.guests >= 3 and order.has_extra("breakfast"):
            total -= BookingOrder.EXTRA_PRICES["breakfast"]
        return total

    def reward_points(self, order: BookingOrder, total_due: int) -> int:
        return total_due // 11 + (10 if order.guests >= 4 else 0)

    def notes(self, order: BookingOrder) -> tuple[str, ...]:
        return ("family-credit", f"guests={order.guests}")


class PolicyRegistry:
    _registry: ClassVar[dict[str, type[DiscountPolicy]]] = {}

    @classmethod
    def register(cls, policy_cls: type[DiscountPolicy]) -> None:
        cls._registry[policy_cls.code] = policy_cls

    @classmethod
    def build_defaults(cls) -> None:
        if cls._registry:
            return
        for policy_cls in (
            StandardPolicy,
            MemberPolicy,
            CorporatePolicy,
            LongStayPolicy,
            FamilyPolicy,
        ):
            cls.register(policy_cls)

    @classmethod
    def create(cls, code: str) -> DiscountPolicy:
        cls.build_defaults()
        return cls._registry[normalize_code(code)]()

    @classmethod
    def supported_codes(cls) -> tuple[str, ...]:
        cls.build_defaults()
        return tuple(sorted(cls._registry))

    @classmethod
    def quote_all(cls, order: BookingOrder, codes: Iterable[str]) -> tuple[ChargeSummary, ...]:
        cls.build_defaults()
        return tuple(cls.create(code).quote(order) for code in codes)


@dataclass(frozen=True)
class PricingLedger:
    quotes: tuple[ChargeSummary, ...]

    @classmethod
    def from_payloads(
        cls, payloads: Iterable[dict[str, object]], policy_codes: Iterable[str]
    ) -> "PricingLedger":
        compiled: list[ChargeSummary] = []
        for payload in payloads:
            order = BookingOrder.from_payload(payload)
            compiled.extend(PolicyRegistry.quote_all(order, policy_codes))
        return cls(tuple(compiled))

    def total_due(self) -> int:
        return sum(quote.total_due for quote in self.quotes)

    def total_discount(self) -> int:
        return sum(quote.discount_amount for quote in self.quotes)

    def render_report(self) -> str:
        totals: dict[str, int] = {}
        for quote in self.quotes:
            totals[quote.policy_code] = totals.get(quote.policy_code, 0) + quote.total_due
        return "|".join(f"{code}:{totals[code]}" for code in sorted(totals))


PolicyRegistry.build_defaults()
