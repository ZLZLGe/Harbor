#!/bin/bash
set -euo pipefail

cat <<'EOF' > /root/CartPricing.scala
import scala.math.BigDecimal.RoundingMode

final case class CartLine(
  sku: String,
  quantity: Int,
  unitPrice: BigDecimal,
  categories: Vector[String] = Vector.empty
) {
  def lineTotal: BigDecimal =
    CartPricing.toMoney(unitPrice * BigDecimal(quantity))
}

final case class CustomerContext(
  customerId: Option[String] = None,
  tier: Option[String] = None,
  region: Option[String] = None,
  tags: Vector[String] = Vector.empty
)

final case class Coupon(
  code: String,
  percentOff: BigDecimal,
  minimumSubtotal: BigDecimal = BigDecimal(0),
  allowedCategories: Option[Set[String]] = None,
  requiredTier: Option[String] = None,
  active: Boolean = true
)

final case class PricingBreakdown(
  subtotal: BigDecimal,
  discounts: BigDecimal = BigDecimal(0),
  appliedRules: Vector[String] = Vector.empty,
  warnings: Vector[String] = Vector.empty
) {
  def total: BigDecimal = {
    val remaining = subtotal - discounts
    if (remaining < BigDecimal(0)) BigDecimal(0).setScale(2, RoundingMode.HALF_UP)
    else CartPricing.toMoney(remaining)
  }

  def applyDiscount(label: String, amount: BigDecimal): PricingBreakdown = {
    val normalized = CartPricing.toMoney(amount)
    if (normalized <= BigDecimal(0)) this
    else copy(
      discounts = CartPricing.toMoney(discounts + normalized),
      appliedRules = appliedRules :+ label
    )
  }

  def withWarning(message: String): PricingBreakdown =
    copy(warnings = warnings :+ message)
}

trait PricingStep {
  def apply(
    breakdown: PricingBreakdown,
    lines: Seq[CartLine],
    customer: Option[CustomerContext]
  ): PricingBreakdown
}

object CartPricing {
  def toMoney(value: BigDecimal): BigDecimal =
    value.setScale(2, RoundingMode.HALF_UP)

  def normalizeCouponCode(code: Option[String]): Option[String] =
    code.map(_.trim).filter(_.nonEmpty).map(_.toUpperCase)

  def computeSubtotal(lines: Seq[CartLine]): BigDecimal =
    toMoney(lines.foldLeft(BigDecimal(0))((acc, line) => acc + line.lineTotal))

  def makeBulkDiscount(
    minQuantity: Int,
    percentOff: BigDecimal,
    category: Option[String] = None,
    label: Option[String] = None
  ): PricingStep = {
    val normalizedCategory = category.map(_.trim).filter(_.nonEmpty).map(_.toLowerCase)
    val ruleLabel = label.getOrElse(s"bulk:$minQuantity")

    new PricingStep {
      override def apply(
        breakdown: PricingBreakdown,
        lines: Seq[CartLine],
        customer: Option[CustomerContext]
      ): PricingBreakdown = {
        val eligibleTotal = lines.foldLeft(BigDecimal(0)) { (acc, line) =>
          val matchesQuantity = line.quantity >= minQuantity
          val matchesCategory = normalizedCategory.forall { target =>
            normalizedCategories(line.categories).contains(target)
          }
          if (matchesQuantity && matchesCategory) acc + line.lineTotal else acc
        }

        breakdown.applyDiscount(ruleLabel, toMoney(eligibleTotal * percentOff / BigDecimal(100)))
      }
    }
  }

  def makeTierDiscount(
    requiredTier: String,
    percentOff: BigDecimal,
    label: Option[String] = None
  ): PricingStep = {
    val normalizedTier = requiredTier.trim.toLowerCase
    val ruleLabel = label.getOrElse(s"tier:$normalizedTier")

    new PricingStep {
      override def apply(
        breakdown: PricingBreakdown,
        lines: Seq[CartLine],
        customer: Option[CustomerContext]
      ): PricingBreakdown = {
        val customerTier = customer.flatMap(_.tier).map(_.trim.toLowerCase)
        if (customerTier.contains(normalizedTier)) {
          breakdown.applyDiscount(ruleLabel, toMoney(breakdown.subtotal * percentOff / BigDecimal(100)))
        } else {
          breakdown
        }
      }
    }
  }

  def validateCoupon(
    coupon: Coupon,
    lines: Seq[CartLine],
    subtotal: BigDecimal,
    customer: Option[CustomerContext] = None
  ): Either[String, Coupon] = {
    if (!coupon.active) Left("coupon inactive")
    else if (subtotal < toMoney(coupon.minimumSubtotal)) Left("subtotal below minimum")
    else if (coupon.requiredTier.exists { tier =>
      customer.flatMap(_.tier).map(_.trim.toLowerCase) != Some(tier.trim.toLowerCase)
    }) Left("coupon tier mismatch")
    else if (coupon.allowedCategories.exists { allowed =>
      val seen = lines.iterator.flatMap(line => normalizedCategories(line.categories)).toSet
      seen.intersect(normalizedCategories(allowed.toVector)).isEmpty
    }) Left("coupon category mismatch")
    else Right(coupon)
  }

  def couponStep(
    couponLookup: String => Option[Coupon],
    rawCode: Option[String]
  ): PricingStep =
    new PricingStep {
      override def apply(
        breakdown: PricingBreakdown,
        lines: Seq[CartLine],
        customer: Option[CustomerContext]
      ): PricingBreakdown =
        normalizeCouponCode(rawCode) match {
          case None =>
            breakdown.withWarning("coupon skipped: empty code")
          case Some(code) =>
            couponLookup(code) match {
              case None =>
                breakdown.withWarning(s"coupon skipped: $code not found")
              case Some(coupon) =>
                validateCoupon(coupon, lines, breakdown.subtotal, customer) match {
                  case Left(reason) =>
                    breakdown.withWarning(s"coupon skipped: $reason")
                  case Right(validCoupon) =>
                    val eligibleSubtotal = validCoupon.allowedCategories match {
                      case Some(allowed) =>
                        val normalizedAllowed = normalizedCategories(allowed.toVector)
                        lines.foldLeft(BigDecimal(0)) { (acc, line) =>
                          if (normalizedCategories(line.categories).intersect(normalizedAllowed).nonEmpty) {
                            acc + line.lineTotal
                          } else {
                            acc
                          }
                        }
                      case None =>
                        breakdown.subtotal
                    }

                    breakdown.applyDiscount(
                      s"coupon:$code",
                      toMoney(eligibleSubtotal * validCoupon.percentOff / BigDecimal(100))
                    )
                }
            }
        }
    }

  def composeSteps(steps: PricingStep*): PricingStep =
    new PricingStep {
      override def apply(
        breakdown: PricingBreakdown,
        lines: Seq[CartLine],
        customer: Option[CustomerContext]
      ): PricingBreakdown =
        steps.foldLeft(breakdown) { (current, step) =>
          step(current, lines, customer)
        }
    }

  private def normalizedCategories(categories: Seq[String]): Set[String] =
    categories.iterator.map(_.trim).filter(_.nonEmpty).map(_.toLowerCase).toSet
}

final class CartPricingEngine(steps: PricingStep*) {
  private val composed = CartPricing.composeSteps(steps: _*)

  def price(
    lines: Seq[CartLine],
    customer: Option[CustomerContext] = None
  ): PricingBreakdown = {
    val subtotal = CartPricing.computeSubtotal(lines)
    composed(PricingBreakdown(subtotal = subtotal), lines, customer)
  }
}
EOF
