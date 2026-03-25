# Transfer - Feature Flag Rule Engine Translation

`/root/FeatureFlagEngine.py` contains a Python feature flag evaluator that stores rules as nested dict/list structures and returns `None` when a flag key is unknown. Translate it into idiomatic Scala 2.13 and save the result as `/root/FeatureFlagEngine.scala`.

Your Scala file must compile under Scala 2.13 and use package `featureflags`.

Preserve the same domain behavior while exposing this translated public surface:

- `sealed trait AttributeValue` with concrete cases for text, numeric, and boolean attributes
- `final case class EvaluationContext`
- `sealed trait Condition`
- `case object Always`
- `final case class AttributeEquals`
- `final case class AttributeIn`
- `final case class NumericAtLeast`
- `final case class BooleanIs`
- `final case class PercentageRollout`
- `final case class All`
- `final case class Any`
- `final case class Not`
- `final case class FlagRule`
- `final case class FlagDefinition`
- `final case class EvaluationResult`
- `class FeatureFlagEngine` with `evaluate` and `evaluateAll`
- `object FeatureFlagEngine` with `stableBucket`

Behavioral requirements:

- Rule order matters: the first matching rule wins.
- `evaluate` must return `Either[String, EvaluationResult]`; unknown flag keys should return a `Left` instead of throwing.
- `evaluateAll` must return results for every configured flag.
- Atomic attribute checks must fail closed when the field is missing or has the wrong value type.
- `All`, `Any`, and `Not` must support arbitrary nesting.
- `PercentageRollout` must preserve the Python source semantics: build the SHA-1 seed from `(flagKey, salt, bucketKey)`, read the first 8 hex digits, map them into `0.00` to `99.99`, and compare the resulting bucket to the configured percentage.
- When no rule matches, the engine must return the flag's default variant with `matchedRule = None`.

Data-modeling requirements:

- Model both attribute values and conditions as sealed ADTs.
- Use pattern matching for condition evaluation.
- Use `Option` for optional rollout salt and `matchedRule`.
- Do not use `null` to represent missing data.

The bundled tests will compile your Scala file, run Scala unit tests against its behavior, and check the public API plus the typed optional/error handling contract. `/root/flag_cases.json` is included only as a quick sanity-check asset.
