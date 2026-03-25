from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_HALF_UP


Money = Decimal
PricingStep = Callable[["PricingBreakdown", Sequence["CartLine"], "CustomerContext | None"], "PricingBreakdown"]
CouponLookup = Callable[[str], "Coupon | None"]
CENT = Decimal("0.01")


def to_money(value: Decimal | str | int | float) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class CartLine:
    sku: str
    quantity: int
    unit_price: Decimal
    categories: tuple[str, ...] = ()

    def line_total(self) -> Decimal:
        return to_money(self.unit_price * self.quantity)


@dataclass(frozen=True)
class CustomerContext:
    customer_id: str | None = None
    tier: str | None = None
    region: str | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class Coupon:
    code: str
    percent_off: Decimal
    minimum_subtotal: Decimal = Decimal("0")
    allowed_categories: frozenset[str] | None = None
    required_tier: str | None = None
    active: bool = True


@dataclass(frozen=True)
class PricingBreakdown:
    subtotal: Decimal
    discounts: Decimal = Decimal("0")
    applied_rules: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def total(self) -> Decimal:
        return to_money(max(Decimal("0"), self.subtotal - self.discounts))

    def apply_discount(self, label: str, amount: Decimal) -> "PricingBreakdown":
        normalized = to_money(amount)
        if normalized <= 0:
            return self
        return replace(
            self,
            discounts=to_money(self.discounts + normalized),
            applied_rules=self.applied_rules + (label,),
        )

    def with_warning(self, message: str) -> "PricingBreakdown":
        return replace(self, warnings=self.warnings + (message,))


def normalize_coupon_code(code: str | None) -> str | None:
    if code is None:
        return None
    cleaned = code.strip().upper()
    return cleaned or None


def compute_subtotal(lines: Sequence[CartLine]) -> Decimal:
    return to_money(sum((line.line_total() for line in lines), Decimal("0")))


def _normalized_categories(categories: Sequence[str]) -> set[str]:
    return {category.strip().lower() for category in categories if category.strip()}


def make_bulk_discount(
    min_quantity: int,
    percent_off: Decimal,
    category: str | None = None,
    label: str | None = None,
) -> PricingStep:
    target_category = category.strip().lower() if category and category.strip() else None
    rule_label = label or f"bulk:{min_quantity}"
    percent = Decimal(str(percent_off))

    def apply_rule(
        breakdown: PricingBreakdown,
        lines: Sequence[CartLine],
        customer: CustomerContext | None,
    ) -> PricingBreakdown:
        del customer
        eligible_total = Decimal("0")
        for line in lines:
            if line.quantity < min_quantity:
                continue
            if target_category is not None and target_category not in _normalized_categories(line.categories):
                continue
            eligible_total += line.line_total()
        amount = to_money(eligible_total * percent / Decimal("100"))
        return breakdown.apply_discount(rule_label, amount)

    return apply_rule


def make_tier_discount(required_tier: str, percent_off: Decimal, label: str | None = None) -> PricingStep:
    normalized_tier = required_tier.strip().lower()
    percent = Decimal(str(percent_off))
    rule_label = label or f"tier:{normalized_tier}"

    def apply_rule(
        breakdown: PricingBreakdown,
        lines: Sequence[CartLine],
        customer: CustomerContext | None,
    ) -> PricingBreakdown:
        del lines
        customer_tier = (customer.tier if customer else None) or ""
        if customer_tier.strip().lower() != normalized_tier:
            return breakdown
        amount = to_money(breakdown.subtotal * percent / Decimal("100"))
        return breakdown.apply_discount(rule_label, amount)

    return apply_rule


def validate_coupon(
    coupon: Coupon,
    lines: Sequence[CartLine],
    subtotal: Decimal,
    customer: CustomerContext | None = None,
) -> str | None:
    if not coupon.active:
        return "coupon inactive"
    if subtotal < to_money(coupon.minimum_subtotal):
        return "subtotal below minimum"
    if coupon.required_tier:
        customer_tier = (customer.tier if customer else None) or ""
        if customer_tier.strip().lower() != coupon.required_tier.strip().lower():
            return "coupon tier mismatch"
    if coupon.allowed_categories:
        seen = set()
        for line in lines:
            seen.update(_normalized_categories(line.categories))
        allowed = _normalized_categories(tuple(coupon.allowed_categories))
        if seen.isdisjoint(allowed):
            return "coupon category mismatch"
    return None


def coupon_step(coupon_lookup: CouponLookup, raw_code: str | None) -> PricingStep:
    def apply_rule(
        breakdown: PricingBreakdown,
        lines: Sequence[CartLine],
        customer: CustomerContext | None,
    ) -> PricingBreakdown:
        normalized_code = normalize_coupon_code(raw_code)
        if normalized_code is None:
            return breakdown.with_warning("coupon skipped: empty code")

        coupon = coupon_lookup(normalized_code)
        if coupon is None:
            return breakdown.with_warning(f"coupon skipped: {normalized_code} not found")

        reason = validate_coupon(coupon, lines, breakdown.subtotal, customer)
        if reason is not None:
            return breakdown.with_warning(f"coupon skipped: {reason}")

        if coupon.allowed_categories:
            allowed = _normalized_categories(tuple(coupon.allowed_categories))
            eligible_subtotal = Decimal("0")
            for line in lines:
                if _normalized_categories(line.categories) & allowed:
                    eligible_subtotal += line.line_total()
        else:
            eligible_subtotal = breakdown.subtotal

        amount = to_money(eligible_subtotal * Decimal(str(coupon.percent_off)) / Decimal("100"))
        return breakdown.apply_discount(f"coupon:{normalized_code}", amount)

    return apply_rule


def compose_steps(*steps: PricingStep) -> PricingStep:
    def apply_rule(
        breakdown: PricingBreakdown,
        lines: Sequence[CartLine],
        customer: CustomerContext | None,
    ) -> PricingBreakdown:
        current = breakdown
        for step in steps:
            current = step(current, lines, customer)
        return current

    return apply_rule


class CartPricingEngine:
    def __init__(self, *steps: PricingStep) -> None:
        self._step = compose_steps(*steps)

    def price(
        self,
        lines: Sequence[CartLine],
        customer: CustomerContext | None = None,
    ) -> PricingBreakdown:
        subtotal = compute_subtotal(lines)
        initial = PricingBreakdown(subtotal=subtotal)
        return self._step(initial, lines, customer)
