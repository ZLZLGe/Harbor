## Task Description

`/app/workspace/tokenizer_subset.py` contains a Python object-oriented tokenizer snippet.

Create `/app/workspace/similar.scala` that translates the design to idiomatic Scala 2.13.

Requirements:

1. Preserve these core elements as Scala definitions:
- `TokenType`
- `Token`
- `BaseTokenizer`
- `StringTokenizer`
- `NumericTokenizer`
- `TokenizerBuilder`
2. Preserve operation names in Scala style-compatible form, while keeping recognizable intent for:
- `tokenize`
- `tokenizeBatch`
- `toToken`
- `withMetadata`
3. Use Scala OOP best practices:
- sealed trait or equivalent for token type family
- case class for immutable token data
- abstract base for tokenizer contract
- inheritance/override for concrete tokenizer implementations
- companion object usage where appropriate
4. The output must be valid Scala source text with clear structure and readability.
5. Do not write extra files.
