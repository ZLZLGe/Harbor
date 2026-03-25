package featureflags

import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers

class FeatureFlagEngineSpec extends AnyFunSuite with Matchers {
  private def text(value: String): AttributeValue = TextValue(value)
  private def number(value: Double): AttributeValue = NumberValue(BigDecimal.decimal(value))
  private def bool(value: Boolean): AttributeValue = BooleanValue(value)

  private def context(bucketKey: String, entries: (String, AttributeValue)*): EvaluationContext =
    EvaluationContext(entries.toMap, bucketKey)

  private val searchRanking = FlagDefinition(
    key = "search-ranking",
    rules = Vector(
      FlagRule(
        name = "vip-pilot",
        when = All(
          Vector(
            AttributeIn("plan", Set("pro", "enterprise")),
            Any(
              Vector(
                AttributeEquals("region", "us-east"),
                AttributeEquals("region", "eu-west")
              )
            ),
            Not(BooleanIs("suspended", expected = true)),
            PercentageRollout(BigDecimal("30.0"), Some("beta"))
          )
        ),
        variant = "ranking-v2"
      ),
      FlagRule(
        name = "adult-ca",
        when = All(
          Vector(
            AttributeEquals("country", "CA"),
            NumericAtLeast("age", BigDecimal("18"))
          )
        ),
        variant = "ranking-ca"
      )
    ),
    defaultVariant = "ranking-v1"
  )

  private val checkoutFlow = FlagDefinition(
    key = "checkout-flow",
    rules = Vector(
      FlagRule(
        name = "vip-fastlane",
        when = All(
          Vector(
            BooleanIs("vip", expected = true),
            NumericAtLeast("orders", BigDecimal("5"))
          )
        ),
        variant = "fast-lane"
      ),
      FlagRule(
        name = "steady-rollout",
        when = All(
          Vector(
            AttributeEquals("country", "US"),
            PercentageRollout(BigDecimal("10.0"), Some("steady"))
          )
        ),
        variant = "checkout-v2"
      )
    ),
    defaultVariant = "classic"
  )

  private val engine = new FeatureFlagEngine(Vector(searchRanking, checkoutFlow))

  test("first matching nested rule wins when percentage rollout passes") {
    val subject = context(
      bucketKey = "alice",
      "plan" -> text("pro"),
      "region" -> text("us-east"),
      "country" -> text("US"),
      "age" -> number(29),
      "suspended" -> bool(false)
    )

    engine.evaluate("search-ranking", subject) shouldBe
      Right(EvaluationResult("search-ranking", "ranking-v2", Some("vip-pilot")))
  }

  test("default fallback is used when no rule matches") {
    val subject = context(
      bucketKey = "bob",
      "plan" -> text("pro"),
      "region" -> text("us-east"),
      "country" -> text("US"),
      "age" -> number(29),
      "suspended" -> bool(false)
    )

    engine.evaluate("search-ranking", subject) shouldBe
      Right(EvaluationResult("search-ranking", "ranking-v1", None))
  }

  test("later rules can match after an earlier rule fails") {
    val subject = context(
      bucketKey = "acct-9",
      "plan" -> text("free"),
      "region" -> text("ca-central"),
      "country" -> text("CA"),
      "age" -> number(44),
      "suspended" -> bool(false)
    )

    engine.evaluate("search-ranking", subject) shouldBe
      Right(EvaluationResult("search-ranking", "ranking-ca", Some("adult-ca")))
  }

  test("evaluateAll returns every configured flag result and stable buckets are deterministic") {
    val subject = context(
      bucketKey = "acct-100",
      "country" -> text("US"),
      "vip" -> bool(false),
      "orders" -> number(1)
    )

    val results = engine.evaluateAll(subject)
    results("search-ranking") shouldBe EvaluationResult("search-ranking", "ranking-v1", None)
    results("checkout-flow") shouldBe EvaluationResult("checkout-flow", "checkout-v2", Some("steady-rollout"))

    FeatureFlagEngine.stableBucket("checkout-flow", "steady", "acct-100") shouldBe BigDecimal("1.57")
    FeatureFlagEngine.stableBucket("checkout-flow", "steady", "acct-101") shouldBe BigDecimal("95.69")
  }

  test("type mismatches fail closed and unknown flags return Left") {
    val subject = context(
      bucketKey = "acct-101",
      "country" -> text("US"),
      "orders" -> text("five")
    )

    engine.evaluate("checkout-flow", subject) shouldBe
      Right(EvaluationResult("checkout-flow", "classic", None))

    engine.evaluate("missing-flag", subject) match {
      case Left(message) =>
        message should include("missing-flag")
      case Right(result) =>
        fail(s"expected Left for missing flag, got $result")
    }
  }
}
