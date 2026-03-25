#!/bin/bash
set -e

cd /root

cat <<'EOF' > FeatureFlagEngine.scala
package featureflags

import java.nio.charset.StandardCharsets
import java.security.MessageDigest

sealed trait AttributeValue
final case class TextValue(value: String) extends AttributeValue
final case class NumberValue(value: BigDecimal) extends AttributeValue
final case class BooleanValue(value: Boolean) extends AttributeValue

final case class EvaluationContext(
  attributes: Map[String, AttributeValue],
  bucketKey: String
)

sealed trait Condition
case object Always extends Condition
final case class AttributeEquals(field: String, expected: String) extends Condition
final case class AttributeIn(field: String, expected: Set[String]) extends Condition
final case class NumericAtLeast(field: String, threshold: BigDecimal) extends Condition
final case class BooleanIs(field: String, expected: Boolean) extends Condition
final case class PercentageRollout(percentage: BigDecimal, salt: Option[String] = None) extends Condition
final case class All(conditions: Vector[Condition]) extends Condition
final case class Any(conditions: Vector[Condition]) extends Condition
final case class Not(condition: Condition) extends Condition

final case class FlagRule(name: String, when: Condition, variant: String)
final case class FlagDefinition(key: String, rules: Vector[FlagRule], defaultVariant: String)
final case class EvaluationResult(flagKey: String, variant: String, matchedRule: Option[String])

class FeatureFlagEngine(flags: Vector[FlagDefinition]) {
  private val flagsByKey: Map[String, FlagDefinition] = flags.iterator.map(flag => flag.key -> flag).toMap

  def evaluate(flagKey: String, context: EvaluationContext): Either[String, EvaluationResult] =
    flagsByKey
      .get(flagKey)
      .toRight(s"Unknown flag: $flagKey")
      .map(flag => evaluateKnownFlag(flag, context))

  def evaluateAll(context: EvaluationContext): Map[String, EvaluationResult] =
    flags.iterator.map(flag => flag.key -> evaluateKnownFlag(flag, context)).toMap

  private def evaluateKnownFlag(flag: FlagDefinition, context: EvaluationContext): EvaluationResult =
    flag.rules.collectFirst {
      case rule if matches(flag.key, rule.when, context) =>
        EvaluationResult(flag.key, rule.variant, Some(rule.name))
    }.getOrElse(EvaluationResult(flag.key, flag.defaultVariant, None))

  private def matches(flagKey: String, condition: Condition, context: EvaluationContext): Boolean =
    condition match {
      case Always =>
        true
      case AttributeEquals(field, expected) =>
        textValue(field, context).contains(expected)
      case AttributeIn(field, expected) =>
        textValue(field, context).exists(expected.contains)
      case NumericAtLeast(field, threshold) =>
        numericValue(field, context).exists(_ >= threshold)
      case BooleanIs(field, expected) =>
        booleanValue(field, context).contains(expected)
      case PercentageRollout(percentage, salt) =>
        FeatureFlagEngine.stableBucket(flagKey, salt.getOrElse(""), context.bucketKey) < percentage
      case All(conditions) =>
        conditions.forall(matches(flagKey, _, context))
      case Any(conditions) =>
        conditions.exists(matches(flagKey, _, context))
      case Not(inner) =>
        !matches(flagKey, inner, context)
    }

  private def textValue(field: String, context: EvaluationContext): Option[String] =
    context.attributes.get(field).collect { case TextValue(value) => value }

  private def numericValue(field: String, context: EvaluationContext): Option[BigDecimal] =
    context.attributes.get(field).collect { case NumberValue(value) => value }

  private def booleanValue(field: String, context: EvaluationContext): Option[Boolean] =
    context.attributes.get(field).collect { case BooleanValue(value) => value }
}

object FeatureFlagEngine {
  def stableBucket(flagKey: String, salt: String, bucketKey: String): BigDecimal = {
    val seed = s"$flagKey:$salt:$bucketKey"
    val digest = MessageDigest.getInstance("SHA-1").digest(seed.getBytes(StandardCharsets.UTF_8))
    val prefix = digest.take(4).foldLeft(BigInt(0)) { (acc, byte) =>
      (acc << 8) + BigInt(byte & 0xff)
    }

    BigDecimal(prefix % 10000) / BigDecimal(100)
  }
}
EOF
