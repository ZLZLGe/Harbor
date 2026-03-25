from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


SCALA_FILE = Path("/root/CartPricing.scala")

HARNESS = """
object CartPricingHarness {
  private def money(value: BigDecimal): String =
    value.setScale(2, BigDecimal.RoundingMode.HALF_UP).toString()

  private def emit(key: String, value: String): Unit =
    println(s"$key=$value")

  def main(args: Array[String]): Unit = {
    val lines = Vector(
      CartLine("apple-crate", 3, BigDecimal("12.50"), Vector(" grocery ", "produce")),
      CartLine("battery-pack", 3, BigDecimal("5.00"), Vector("electronics")),
      CartLine("tea-box", 2, BigDecimal("4.25"), Vector("grocery", " pantry "))
    )

    val goldCustomer = Some(CustomerContext(
      customerId = Some("cust-7"),
      tier = Some(" Gold "),
      region = None,
      tags = Vector("vip")
    ))
    val guestCustomer = Some(CustomerContext(tier = Some("guest")))

    emit("code.blank", CartPricing.normalizeCouponCode(Some("   ")).getOrElse("NONE"))
    emit("code.trimmed", CartPricing.normalizeCouponCode(Some(" grocery10 ")).getOrElse("NONE"))
    emit("line.total", money(lines.head.lineTotal))
    emit("subtotal", money(CartPricing.computeSubtotal(lines)))

    val activeCoupon = Coupon(
      code = "GROCERY10",
      percentOff = BigDecimal("10"),
      minimumSubtotal = BigDecimal("50.00"),
      allowedCategories = Some(Set("grocery")),
      requiredTier = None,
      active = true
    )
    val highMinimumCoupon = activeCoupon.copy(code = "BIG70", minimumSubtotal = BigDecimal("70.00"))
    val tierCoupon = activeCoupon.copy(code = "SILVER5", requiredTier = Some("silver"))
    val apparelCoupon = activeCoupon.copy(code = "APPAREL5", allowedCategories = Some(Set("apparel")))
    val inactiveCoupon = activeCoupon.copy(code = "OFFLINE", active = false)

    emit(
      "validate.ok",
      CartPricing.validateCoupon(activeCoupon, lines, CartPricing.computeSubtotal(lines), goldCustomer)
        .map(_.code)
        .getOrElse("ERR")
    )
    emit(
      "validate.minimum",
      CartPricing.validateCoupon(highMinimumCoupon, lines, CartPricing.computeSubtotal(lines), goldCustomer)
        .left
        .getOrElse("OK")
    )
    emit(
      "validate.tier",
      CartPricing.validateCoupon(tierCoupon, lines, CartPricing.computeSubtotal(lines), goldCustomer)
        .left
        .getOrElse("OK")
    )
    emit(
      "validate.category",
      CartPricing.validateCoupon(apparelCoupon, lines, CartPricing.computeSubtotal(lines), goldCustomer)
        .left
        .getOrElse("OK")
    )
    emit(
      "validate.inactive",
      CartPricing.validateCoupon(inactiveCoupon, lines, CartPricing.computeSubtotal(lines), goldCustomer)
        .left
        .getOrElse("OK")
    )

    val bulkRule = CartPricing.makeBulkDiscount(
      minQuantity = 2,
      percentOff = BigDecimal("10"),
      category = Some("grocery"),
      label = Some("bulk:grocery")
    )
    val tierRule = CartPricing.makeTierDiscount(
      requiredTier = "gold",
      percentOff = BigDecimal("5")
    )
    val couponLookup: String => Option[Coupon] = code =>
      Map(
        "GROCERY10" -> activeCoupon,
        "BIG70" -> highMinimumCoupon,
        "SILVER5" -> tierCoupon
      ).get(code)

    val composed = CartPricing.composeSteps(
      bulkRule,
      tierRule,
      CartPricing.couponStep(couponLookup, Some(" grocery10 "))
    )
    val engine = new CartPricingEngine(
      bulkRule,
      tierRule,
      CartPricing.couponStep(couponLookup, Some(" grocery10 "))
    )
    val priced = engine.price(lines, goldCustomer)
    emit("price.discounts", money(priced.discounts))
    emit("price.total", money(priced.total))
    emit("price.rules", priced.appliedRules.mkString(","))
    emit("price.warnings", if (priced.warnings.isEmpty) "NONE" else priced.warnings.mkString(","))

    val ordered = composed(PricingBreakdown(subtotal = CartPricing.computeSubtotal(lines)), lines, goldCustomer)
    emit("compose.rules", ordered.appliedRules.mkString(","))

    val blankCoupon = new CartPricingEngine(CartPricing.couponStep(couponLookup, Some("   ")))
      .price(lines, goldCustomer)
    emit("blank.warning", blankCoupon.warnings.mkString(","))

    val unknownCoupon = new CartPricingEngine(CartPricing.couponStep(couponLookup, Some("missing")))
      .price(lines, goldCustomer)
    emit("unknown.warning", unknownCoupon.warnings.mkString(","))

    val tierMismatchCoupon = new CartPricingEngine(CartPricing.couponStep(couponLookup, Some("silver5")))
      .price(lines, guestCustomer)
    emit("tier.warning", tierMismatchCoupon.warnings.mkString(","))

    val noTierDiscount = new CartPricingEngine(tierRule).price(lines, None)
    emit("guest.rules", if (noTierDiscount.appliedRules.isEmpty) "NONE" else noTierDiscount.appliedRules.mkString(","))

    val clamped = PricingBreakdown(subtotal = BigDecimal("10.00"))
      .applyDiscount("promo", BigDecimal("20.00"))
    emit("clamped.total", money(clamped.total))

    val ignored = PricingBreakdown(subtotal = BigDecimal("10.00"))
      .applyDiscount("zero", BigDecimal("0.00"))
    emit("ignored.rules", if (ignored.appliedRules.isEmpty) "NONE" else ignored.appliedRules.mkString(","))
  }
}
"""


def ensure_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise AssertionError(f"missing required tool: {name}")


def parse_output(raw: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in raw.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def run_harness() -> dict[str, str]:
    if not SCALA_FILE.exists():
        raise AssertionError("/root/CartPricing.scala not found")

    ensure_tool("scalac")
    ensure_tool("scala")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        classes = tmp / "classes"
        classes.mkdir()
        harness_path = tmp / "CartPricingHarness.scala"
        harness_path.write_text(HARNESS, encoding="utf-8")

        compile_cmd = [
            "scalac",
            "-d",
            str(classes),
            str(SCALA_FILE),
            str(harness_path),
        ]
        compile_proc = subprocess.run(compile_cmd, capture_output=True, text=True, check=False)
        if compile_proc.returncode != 0:
            raise AssertionError(f"scalac failed:\\n{compile_proc.stdout}\\n{compile_proc.stderr}")

        run_cmd = [
            "scala",
            "-cp",
            str(classes),
            "CartPricingHarness",
        ]
        run_proc = subprocess.run(run_cmd, capture_output=True, text=True, check=False)
        if run_proc.returncode != 0:
            raise AssertionError(f"scala run failed:\\n{run_proc.stdout}\\n{run_proc.stderr}")

        return parse_output(run_proc.stdout)


def test_source_contracts() -> None:
    assert SCALA_FILE.exists(), "/root/CartPricing.scala not found"
    source = SCALA_FILE.read_text(encoding="utf-8")
    assert "package " not in source
    assert "null" not in source


def test_runtime_behavior() -> None:
    results = run_harness()

    assert results["code.blank"] == "NONE"
    assert results["code.trimmed"] == "GROCERY10"
    assert results["line.total"] == "37.50"
    assert results["subtotal"] == "61.00"

    assert results["validate.ok"] == "GROCERY10"
    assert results["validate.minimum"] == "subtotal below minimum"
    assert results["validate.tier"] == "coupon tier mismatch"
    assert results["validate.category"] == "coupon category mismatch"
    assert results["validate.inactive"] == "coupon inactive"

    assert results["price.discounts"] == "12.25"
    assert results["price.total"] == "48.75"
    assert results["price.rules"] == "bulk:grocery,tier:gold,coupon:GROCERY10"
    assert results["price.warnings"] == "NONE"
    assert results["compose.rules"] == "bulk:grocery,tier:gold,coupon:GROCERY10"

    assert results["blank.warning"] == "coupon skipped: empty code"
    assert results["unknown.warning"] == "coupon skipped: MISSING not found"
    assert results["tier.warning"] == "coupon skipped: coupon tier mismatch"
    assert results["guest.rules"] == "NONE"

    assert results["clamped.total"] == "0.00"
    assert results["ignored.rules"] == "NONE"
