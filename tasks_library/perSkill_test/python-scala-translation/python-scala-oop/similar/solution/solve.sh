#!/bin/bash
set -euo pipefail

cat > /app/workspace/similar.scala <<'SCALA'
sealed trait TokenType {
  def value: String
}

object TokenType {
  case object STRING extends TokenType { val value: String = "string" }
  case object NUMERIC extends TokenType { val value: String = "numeric" }
}

final case class Token(
  value: String,
  tokenType: TokenType,
  metadata: Map[String, String] = Map.empty
) {
  def withMetadata(entries: (String, String)*): Token =
    copy(metadata = metadata ++ entries.toMap)
}

abstract class BaseTokenizer[A] {
  def tokenize(value: A): Token

  def tokenizeBatch(values: Seq[A]): Seq[Token] =
    values.map(tokenize)
}

final class StringTokenizer extends BaseTokenizer[String] {
  override def tokenize(value: String): Token =
    Token(value, TokenType.STRING)
}

final class NumericTokenizer extends BaseTokenizer[Double] {
  override def tokenize(value: Double): Token =
    Token(value.toString, TokenType.NUMERIC)
}

object TokenizerBuilder {
  def toToken(value: Any): Token = value match {
    case s: String => new StringTokenizer().tokenize(s)
    case n: Int => new NumericTokenizer().tokenize(n.toDouble)
    case n: Double => new NumericTokenizer().tokenize(n)
    case other => new StringTokenizer().tokenize(other.toString)
  }
}
SCALA
