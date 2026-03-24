#!/bin/bash
set -e

cat <<'EOF' > /root/SurveyBranching.scala
import scala.annotation.tailrec
import scala.util.Try

final case class PredicateResult(
  matched: Option[Boolean],
  missingAnswers: Vector[String] = Vector.empty,
  detail: String = ""
)

final case class ExplanationStep(
  nodeId: String,
  branchLabel: String,
  matched: Option[Boolean],
  detail: String,
  missingAnswers: Vector[String] = Vector.empty
)

final case class DecisionResult(
  segment: Option[String],
  rationale: Option[String],
  missingAnswers: Vector[String],
  path: Vector[ExplanationStep]
) {
  def isResolved: Boolean =
    segment.nonEmpty && missingAnswers.isEmpty

  def explanationPath: Vector[String] = {
    val renderedPath = path.map { step =>
      val status = step.matched match {
        case Some(true) => "matched"
        case Some(false) => "skipped"
        case None if step.missingAnswers.nonEmpty => s"pending:${step.missingAnswers.mkString(",")}"
        case None => "pending"
      }
      s"${step.nodeId}.${step.branchLabel}:$status"
    }

    segment match {
      case Some(value) => renderedPath :+ s"segment:$value"
      case None if missingAnswers.nonEmpty => renderedPath :+ s"pending:${missingAnswers.mkString(",")}"
      case None => renderedPath :+ "unresolved"
    }
  }
}

sealed trait SurveyNode

final case class OutcomeNode(
  segment: String,
  rationale: String
) extends SurveyNode

final case class BranchCase(
  label: String,
  predicate: SurveyBranching.Predicate,
  nextNode: SurveyNode
)

final case class BranchNode(
  nodeId: String,
  cases: Vector[BranchCase],
  defaultNext: Option[SurveyNode] = None,
  defaultLabel: String = "default"
) extends SurveyNode

object SurveyBranching {
  type Answers = Map[String, Any]
  type Predicate = Answers => PredicateResult

  private def stableDedupe(values: Iterable[String]): Vector[String] =
    values.foldLeft((Vector.empty[String], Set.empty[String])) {
      case ((acc, seen), value) if seen.contains(value) =>
        (acc, seen)
      case ((acc, seen), value) =>
        (acc :+ value, seen + value)
    }._1

  private def missing(question: String, detail: String): PredicateResult =
    PredicateResult(None, Vector(question), detail)

  private def asDecimal(value: Any): Option[BigDecimal] = value match {
    case decimal: BigDecimal => Some(decimal)
    case intValue: Int => Some(BigDecimal(intValue))
    case longValue: Long => Some(BigDecimal(longValue))
    case doubleValue: Double => Some(BigDecimal.decimal(doubleValue))
    case floatValue: Float => Some(BigDecimal.decimal(floatValue.toDouble))
    case stringValue: String => Try(BigDecimal(stringValue.trim)).toOption
    case _ => None
  }

  def answerEquals(question: String, expected: Any): Predicate = answers =>
    answers.get(question) match {
      case None => missing(question, s"$question missing")
      case Some(null) => missing(question, s"$question missing")
      case Some(actual) =>
        PredicateResult(Some(actual == expected), Vector.empty, s"$question == $expected")
    }

  def answerIn(question: String, choices: Set[String]): Predicate = answers =>
    answers.get(question) match {
      case None => missing(question, s"$question missing")
      case Some(null) => missing(question, s"$question missing")
      case Some(actual: String) =>
        PredicateResult(
          Some(choices.contains(actual)),
          Vector.empty,
          s"$question in ${choices.toVector.sorted.mkString("[", ",", "]")}"
        )
      case Some(_) =>
        PredicateResult(Some(false), Vector.empty, s"$question incompatible")
    }

  def numericAtLeast(question: String, threshold: BigDecimal): Predicate = answers =>
    answers.get(question) match {
      case None => missing(question, s"$question missing")
      case Some(null) => missing(question, s"$question missing")
      case Some(actual) =>
        asDecimal(actual) match {
          case Some(number) =>
            PredicateResult(Some(number >= threshold), Vector.empty, s"$question >= $threshold")
          case None =>
            PredicateResult(Some(false), Vector.empty, s"$question invalid-number")
        }
    }

  def allOf(predicates: Predicate*): Predicate = answers => {
    val checks = predicates.toVector.map(_(answers))
    if (checks.exists(_.matched.contains(false))) {
      PredicateResult(Some(false), Vector.empty, "allOf")
    } else {
      val missingAnswers = stableDedupe(
        checks.iterator.filter(_.matched.isEmpty).flatMap(_.missingAnswers).toVector
      )
      if (missingAnswers.nonEmpty) PredicateResult(None, missingAnswers, "allOf")
      else PredicateResult(Some(true), Vector.empty, "allOf")
    }
  }

  def anyOf(predicates: Predicate*): Predicate = answers => {
    val checks = predicates.toVector.map(_(answers))
    if (checks.exists(_.matched.contains(true))) {
      PredicateResult(Some(true), Vector.empty, "anyOf")
    } else {
      val missingAnswers = stableDedupe(
        checks.iterator.filter(_.matched.isEmpty).flatMap(_.missingAnswers).toVector
      )
      if (missingAnswers.nonEmpty) PredicateResult(None, missingAnswers, "anyOf")
      else PredicateResult(Some(false), Vector.empty, "anyOf")
    }
  }

  def evaluate(node: SurveyNode, answers: Answers): DecisionResult =
    loop(node, answers, Vector.empty)

  private def loop(node: SurveyNode, answers: Answers, path: Vector[ExplanationStep]): DecisionResult =
    node match {
      case OutcomeNode(segment, rationale) =>
        DecisionResult(Some(segment), Some(rationale), Vector.empty, path)
      case BranchNode(nodeId, cases, defaultNext, defaultLabel) =>
        inspectCases(cases.toList, answers, nodeId, Vector.empty, Vector.empty) match {
          case Right((attempted, nextNode)) =>
            loop(nextNode, answers, path ++ attempted)
          case Left((attempted, pendingMissing)) if pendingMissing.nonEmpty =>
            DecisionResult(None, None, pendingMissing, path ++ attempted)
          case Left((attempted, _)) =>
            defaultNext match {
              case Some(nextNode) =>
                val defaultStep = ExplanationStep(nodeId, defaultLabel, Some(true), "default", Vector.empty)
                loop(nextNode, answers, path ++ attempted :+ defaultStep)
              case None =>
                DecisionResult(None, None, Vector.empty, path ++ attempted)
            }
        }
    }

  @tailrec
  private def inspectCases(
    remaining: List[BranchCase],
    answers: Answers,
    nodeId: String,
    attempted: Vector[ExplanationStep],
    pending: Vector[String]
  ): Either[(Vector[ExplanationStep], Vector[String]), (Vector[ExplanationStep], SurveyNode)] =
    remaining match {
      case Nil =>
        Left((attempted, pending))
      case branchCase :: tail =>
        val check = branchCase.predicate(answers)
        val step = ExplanationStep(
          nodeId = nodeId,
          branchLabel = branchCase.label,
          matched = check.matched,
          detail = check.detail,
          missingAnswers = check.missingAnswers
        )
        val nextAttempted = attempted :+ step
        check.matched match {
          case Some(true) =>
            Right((nextAttempted, branchCase.nextNode))
          case Some(false) =>
            inspectCases(tail, answers, nodeId, nextAttempted, pending)
          case None =>
            inspectCases(
              tail,
              answers,
              nodeId,
              nextAttempted,
              stableDedupe(pending ++ check.missingAnswers)
            )
        }
    }

  def reachableSegments(node: SurveyNode): Vector[String] = node match {
    case OutcomeNode(segment, _) =>
      Vector(segment)
    case BranchNode(_, cases, defaultNext, _) =>
      stableDedupe(
        cases.flatMap(branchCase => reachableSegments(branchCase.nextNode)) ++
          defaultNext.toVector.flatMap(reachableSegments)
      )
  }

  def renderExplanation(result: DecisionResult): String =
    result.explanationPath.mkString(" -> ")
}
EOF
