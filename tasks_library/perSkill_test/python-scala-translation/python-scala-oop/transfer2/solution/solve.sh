#!/bin/bash
set -euo pipefail

cat > /app/workspace/transfer2.scala <<'SCALA'
abstract class PaymentMethod(val amount: BigDecimal) {
  def charge: String
}

trait Refundable {
  def refund: String = "refund-issued"
}

trait Auditable {
  def auditTag: String = "audit-ok"
}

final case class CardPayment(override val amount: BigDecimal)
    extends PaymentMethod(amount)
    with Refundable
    with Auditable {
  override def charge: String = f"card:${amount}%.2f"
}

final case class WirePayment(override val amount: BigDecimal)
    extends PaymentMethod(amount)
    with Auditable {
  override def charge: String = f"wire:${amount}%.2f"
}

object PaymentFactory {
  def create(kind: String, amount: BigDecimal): PaymentMethod = kind match {
    case "card" => CardPayment(amount)
    case _ => WirePayment(amount)
  }
}
SCALA
