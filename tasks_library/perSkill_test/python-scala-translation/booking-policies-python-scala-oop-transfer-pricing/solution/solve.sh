#!/bin/bash
set -euo pipefail

cat <<'EOF' > /root/BookingPolicies.scala
package booking

import scala.collection.mutable
import scala.math.floor

object PricingSupport {
  def normalizeCode(raw: String): String =
    raw.trim.toLowerCase.replace("_", "-").replace(" ", "-")

  def roundMoney(value: Double): Int =
    floor(value + 0.5d).toInt

  def readString(value: Any): String = value match {
    case text: String => text.trim
    case other => other.toString.trim
  }

  def readInt(value: Any): Int = value match {
    case number: Int => number
    case number: Long => number.toInt
    case number: Short => number.toInt
    case number: Double => number.toInt
    case number: Float => number.toInt
    case text: String => text.trim.toInt
    case other => other.toString.trim.toInt
  }

  def readBoolean(value: Any): Boolean = value match {
    case flag: Boolean => flag
    case text: String => text.trim.toLowerCase match {
        case "true" | "1" | "yes" => true
        case _ => false
      }
    case number: Int => number != 0
    case number: Long => number != 0L
    case _ => false
  }

  def readStringVector(value: Any): Vector[String] = value match {
    case values: Iterable[_] => values.iterator.map(item => normalizeCode(readString(item))).toVector
    case text: String if text.trim.nonEmpty => Vector(normalizeCode(text))
    case _ => Vector.empty
  }
}

import PricingSupport._

final case class RoomType(
    code: String,
    nightlyRate: Int,
    cleaningFee: Int,
    cityFee: Int,
    maxGuests: Int,
    amenities: Vector[String] = Vector.empty
)

object RoomType {
  private val catalog: Map[String, RoomType] = Map(
    "studio" -> RoomType("studio", 120, 30, 6, 2, Vector("espresso", "desk")),
    "loft" -> RoomType("loft", 180, 45, 7, 3, Vector("balcony", "kitchen")),
    "suite" -> RoomType("suite", 260, 55, 9, 4, Vector("lounge", "tub")),
    "villa" -> RoomType("villa", 420, 90, 12, 6, Vector("garden", "pool"))
  )

  def fromCode(code: String): RoomType =
    catalog(normalizeCode(code))
}

final case class BookingOrder(
    bookingId: String,
    guestName: String,
    roomType: RoomType,
    nights: Int,
    guests: Int,
    season: String = "regular",
    extras: Vector[String] = Vector.empty,
    vip: Boolean = false,
    corporateAccount: String = ""
) {
  def baseSubtotal: Int =
    roomType.nightlyRate * nights

  def mandatoryFees: Int =
    roomType.cleaningFee + roomType.cityFee * guests * nights

  def extrasTotal: Int =
    extras.iterator.map(BookingOrder.extraPrices).sum

  def hasExtra(extra: String): Boolean =
    extras.contains(normalizeCode(extra))
}

object BookingOrder {
  val extraPrices: Map[String, Int] = Map(
    "breakfast" -> 18,
    "parking" -> 14,
    "late-checkout" -> 25,
    "shuttle" -> 36
  )

  def fromPayload(payload: Map[String, Any]): BookingOrder = {
    val extras = payload.get("extras").map(readStringVector).getOrElse(Vector.empty)
    BookingOrder(
      bookingId = readString(payload("booking_id")),
      guestName = readString(payload("guest_name")),
      roomType = RoomType.fromCode(readString(payload("room_type"))),
      nights = readInt(payload("nights")),
      guests = readInt(payload("guests")),
      season = normalizeCode(payload.get("season").map(readString).getOrElse("regular")),
      extras = extras,
      vip = payload.get("vip").exists(readBoolean),
      corporateAccount = payload.get("corporate_account").map(readString).getOrElse("")
    )
  }
}

final case class ChargeSummary(
    bookingId: String,
    policyCode: String,
    roomCode: String,
    baseSubtotal: Int,
    mandatoryFees: Int,
    extrasTotal: Int,
    discountAmount: Int,
    serviceCharge: Int,
    totalDue: Int,
    rewardPoints: Int,
    notes: Vector[String] = Vector.empty
) {
  def grandFees: Int =
    mandatoryFees + extrasTotal + serviceCharge

  def renderLine: String =
    s"$bookingId|$policyCode|$totalDue|$rewardPoints|${notes.mkString(",")}"
}

abstract class DiscountPolicy {
  def code: String

  protected def serviceRate: Double = 0.08d

  def mandatoryFees(order: BookingOrder): Int =
    order.mandatoryFees

  def extrasTotal(order: BookingOrder): Int =
    order.extrasTotal

  def discountAmount(order: BookingOrder): Int

  def rewardPoints(order: BookingOrder, totalDue: Int): Int =
    totalDue / 10

  def notes(order: BookingOrder): Vector[String] =
    Vector(code, order.roomType.code)

  def quote(order: BookingOrder): ChargeSummary = {
    val fees = mandatoryFees(order)
    val extras = extrasTotal(order)
    val discount = discountAmount(order)
    val service = roundMoney(math.max(order.baseSubtotal - discount, 0) * serviceRate)
    val total = order.baseSubtotal + fees + extras - discount + service
    ChargeSummary(
      bookingId = order.bookingId,
      policyCode = code,
      roomCode = order.roomType.code,
      baseSubtotal = order.baseSubtotal,
      mandatoryFees = fees,
      extrasTotal = extras,
      discountAmount = discount,
      serviceCharge = service,
      totalDue = total,
      rewardPoints = rewardPoints(order, total),
      notes = notes(order)
    )
  }
}

final class StandardPolicy extends DiscountPolicy {
  override val code: String = "standard"

  override def discountAmount(order: BookingOrder): Int = 0

  override def notes(order: BookingOrder): Vector[String] =
    Vector("rack-rate", order.roomType.code)
}

final class MemberPolicy extends DiscountPolicy {
  override val code: String = "member"

  override protected val serviceRate: Double = 0.05d

  override def discountAmount(order: BookingOrder): Int = {
    val rate = if (order.vip) 0.14d else 0.10d
    val baseDiscount = roundMoney(order.baseSubtotal * rate)
    if (order.vip && order.season == "shoulder") baseDiscount + 15 else baseDiscount
  }

  override def rewardPoints(order: BookingOrder, totalDue: Int): Int =
    totalDue / 8 + (if (order.vip) 25 else 0)

  override def notes(order: BookingOrder): Vector[String] =
    if (order.vip) Vector("member-rate", "vip-benefit") else Vector("member-rate")
}

final class CorporatePolicy extends DiscountPolicy {
  override val code: String = "corporate"

  override protected val serviceRate: Double = 0.03d

  override def discountAmount(order: BookingOrder): Int =
    roundMoney(order.baseSubtotal * 0.18d)

  override def mandatoryFees(order: BookingOrder): Int = {
    val cityComponent = roundMoney(order.roomType.cityFee * order.guests * order.nights * 0.5d)
    order.roomType.cleaningFee + cityComponent
  }

  override def rewardPoints(order: BookingOrder, totalDue: Int): Int = 0

  override def notes(order: BookingOrder): Vector[String] =
    Vector("corporate-rate", if (order.corporateAccount.nonEmpty) order.corporateAccount else "house-account")
}

final class LongStayPolicy extends DiscountPolicy {
  override val code: String = "long-stay"

  override protected val serviceRate: Double = 0.04d

  override def discountAmount(order: BookingOrder): Int = {
    val rate =
      if (order.nights >= 7) 0.15d
      else if (order.nights >= 4) 0.07d
      else 0.0d
    roundMoney(order.baseSubtotal * rate)
  }

  override def mandatoryFees(order: BookingOrder): Int =
    if (order.nights >= 7) order.roomType.cityFee * order.guests * order.nights else order.mandatoryFees

  override def rewardPoints(order: BookingOrder, totalDue: Int): Int =
    totalDue / 12 + (if (order.nights >= 7) 15 else 0)

  override def notes(order: BookingOrder): Vector[String] =
    Vector("extended-stay", s"nights=${order.nights}")
}

final class FamilyPolicy extends DiscountPolicy {
  override val code: String = "family"

  override protected val serviceRate: Double = 0.05d

  override def discountAmount(order: BookingOrder): Int = {
    val rate = if (order.guests >= 3) 0.12d else 0.05d
    roundMoney(order.baseSubtotal * rate)
  }

  override def mandatoryFees(order: BookingOrder): Int = {
    val waivedCityFee = if (order.guests >= 3) order.roomType.cityFee * order.nights else 0
    order.mandatoryFees - waivedCityFee
  }

  override def extrasTotal(order: BookingOrder): Int = {
    val breakfastCredit =
      if (order.guests >= 3 && order.hasExtra("breakfast")) BookingOrder.extraPrices("breakfast") else 0
    order.extrasTotal - breakfastCredit
  }

  override def rewardPoints(order: BookingOrder, totalDue: Int): Int =
    totalDue / 11 + (if (order.guests >= 4) 10 else 0)

  override def notes(order: BookingOrder): Vector[String] =
    Vector("family-credit", s"guests=${order.guests}")
}

object PolicyRegistry {
  private val registry: mutable.LinkedHashMap[String, () => DiscountPolicy] =
    mutable.LinkedHashMap.empty

  def register(policyFactory: () => DiscountPolicy): Unit = {
    val policy = policyFactory()
    registry.update(policy.code, policyFactory)
  }

  def buildDefaults(): Unit =
    if (registry.isEmpty) {
      register(() => new StandardPolicy)
      register(() => new MemberPolicy)
      register(() => new CorporatePolicy)
      register(() => new LongStayPolicy)
      register(() => new FamilyPolicy)
    }

  def create(code: String): DiscountPolicy = {
    buildDefaults()
    registry(normalizeCode(code))()
  }

  def supportedCodes: Vector[String] = {
    buildDefaults()
    registry.keys.toVector.sorted
  }

  def quoteAll(order: BookingOrder, codes: Iterable[String]): Vector[ChargeSummary] = {
    buildDefaults()
    codes.iterator.map(code => create(code).quote(order)).toVector
  }
}

final case class PricingLedger(quotes: Vector[ChargeSummary]) {
  def totalDue: Int =
    quotes.iterator.map(_.totalDue).sum

  def totalDiscount: Int =
    quotes.iterator.map(_.discountAmount).sum

  def renderReport: String = {
    val totals = mutable.LinkedHashMap.empty[String, Int]
    quotes.foreach { quote =>
      val next = totals.getOrElse(quote.policyCode, 0) + quote.totalDue
      totals.update(quote.policyCode, next)
    }
    totals.keys.toVector.sorted.map(code => s"$code:${totals(code)}").mkString("|")
  }
}

object PricingLedger {
  def fromPayloads(payloads: Iterable[Map[String, Any]], policyCodes: Iterable[String]): PricingLedger = {
    val quotes = payloads.iterator.flatMap { payload =>
      val order = BookingOrder.fromPayload(payload)
      PolicyRegistry.quoteAll(order, policyCodes)
    }.toVector
    PricingLedger(quotes)
  }
}
EOF
