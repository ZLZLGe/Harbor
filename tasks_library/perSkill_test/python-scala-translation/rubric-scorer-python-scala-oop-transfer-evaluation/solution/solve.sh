#!/bin/bash
set -euo pipefail

cat <<'EOF' > /root/RubricScorer.scala
package rubric

import scala.math.BigDecimal.RoundingMode
import scala.util.matching.Regex

object RubricMath {
  def roundScore(value: Double): Double =
    BigDecimal.decimal(value).setScale(4, RoundingMode.HALF_UP).toDouble

  def formatScore(value: Double): String =
    f"${roundScore(value)}%.4f"

  def clamp(value: Double, minimum: Double, maximum: Double): Double =
    math.max(minimum, math.min(value, maximum))

  def normalizeText(value: String): String =
    value.trim.toLowerCase.split("\\s+").filter(_.nonEmpty).mkString(" ")

  def readString(value: Any): String = value match {
    case text: String => text.trim
    case other        => other.toString.trim
  }

  def readDouble(value: Any): Double = value match {
    case number: Double     => number
    case number: Float      => number.toDouble
    case number: Int        => number.toDouble
    case number: Long       => number.toDouble
    case number: Short      => number.toDouble
    case number: BigDecimal => number.toDouble
    case text: String       => text.trim.toDouble
    case other              => other.toString.trim.toDouble
  }

  def readStringSeq(value: Any): Vector[String] = value match {
    case values: Iterable[_] =>
      values.iterator.map(item => normalizeText(readString(item))).filter(_.nonEmpty).toVector
    case text: String if text.trim.nonEmpty =>
      Vector(normalizeText(text))
    case _ =>
      Vector.empty
  }

  def readStringMap(value: Any): Map[String, String] = value match {
    case values: collection.Map[_, _] =>
      values.iterator.map { case (key, item) =>
        readString(key) -> readString(item)
      }.toMap
    case _ =>
      Map.empty
  }
}

import RubricMath._

final case class RubricQuestion(
    questionId: String,
    prompt: String,
    maxPoints: Double,
    weight: Double = 1.0,
    keywords: Vector[String] = Vector.empty,
    metadata: Map[String, String] = Map.empty
) {
  def maxWeighted: Double =
    roundScore(maxPoints * weight)
}

object RubricQuestion {
  def fromPayload(payload: Map[String, Any]): RubricQuestion =
    RubricQuestion(
      questionId = readString(payload("question_id")),
      prompt = readString(payload("prompt")),
      maxPoints = roundScore(readDouble(payload("max_points"))),
      weight = roundScore(payload.get("weight").map(readDouble).getOrElse(1.0d)),
      keywords = payload.get("keywords").map(readStringSeq).getOrElse(Vector.empty),
      metadata = payload.get("metadata").map(readStringMap).getOrElse(Map.empty)
    )
}

final case class ScoreResult(
    questionId: String,
    scorerKind: String,
    rawScore: Double,
    maxPoints: Double,
    weightedScore: Double,
    feedback: String,
    metadata: Map[String, String] = Map.empty
) {
  def ratio: Double =
    if (maxPoints == 0.0d) 0.0d else roundScore(rawScore / maxPoints)

  def withMetadata(entries: (String, String)*): ScoreResult =
    copy(metadata = metadata ++ entries.toMap)

  def render: String =
    s"$questionId|$scorerKind|${formatScore(rawScore)}|${formatScore(weightedScore)}|${formatScore(ratio)}|$feedback"
}

object ScoreResult {
  def fromEvaluation(
      question: RubricQuestion,
      scorerKind: String,
      rawScore: Double,
      feedback: String,
      metadata: Map[String, String] = Map.empty
  ): ScoreResult = {
    val bounded = roundScore(clamp(rawScore, 0.0d, question.maxPoints))
    ScoreResult(
      questionId = question.questionId,
      scorerKind = scorerKind,
      rawScore = bounded,
      maxPoints = question.maxPoints,
      weightedScore = roundScore(bounded * question.weight),
      feedback = feedback.trim,
      metadata = metadata
    )
  }
}

final case class SubmissionReport(
    studentId: String,
    results: Vector[ScoreResult],
    metadata: Map[String, String] = Map.empty
) {
  def totalWeightedScore: Double =
    roundScore(results.map(_.weightedScore).sum)

  def totalMaxWeighted: Double =
    roundScore(results.map(result => result.maxPoints * result.metadata.get("weight").map(_.toDouble).getOrElse(1.0d)).sum)

  def averageRatio(): Double = {
    val denominator = results.map(result => result.maxPoints * result.metadata.get("weight").map(_.toDouble).getOrElse(1.0d)).sum
    if (denominator == 0.0d) 0.0d else roundScore(totalWeightedScore / denominator)
  }

  def render: String = {
    val details = results.map(result => s"${result.questionId}:${formatScore(result.weightedScore)}").mkString(",")
    s"$studentId|${formatScore(totalWeightedScore)}|${formatScore(averageRatio())}|$details"
  }
}

object SubmissionReport {
  def fromResults(
      studentId: String,
      results: Iterable[ScoreResult],
      metadata: Map[String, String] = Map.empty
  ): SubmissionReport =
    SubmissionReport(studentId.trim, results.toVector, metadata)
}

abstract class AbstractScorer(val kind: String) {
  def scoreRaw(question: RubricQuestion, response: String): (Double, String)

  def buildResult(question: RubricQuestion, response: String, metadata: (String, String)*): ScoreResult = {
    val evaluation = scoreRaw(question, response)
    val baseMetadata = Map(
      "prompt" -> question.prompt,
      "response_chars" -> response.trim.length.toString
    ) ++ question.metadata ++ metadata.toMap
    ScoreResult.fromEvaluation(question, kind, evaluation._1, evaluation._2, baseMetadata)
  }

  def score(question: RubricQuestion, response: String): ScoreResult =
    buildResult(question, response)
}

final class TextRubricScorer(minLength: Int = 0, bonusPoints: Double = 0.0d)
    extends AbstractScorer("text") {
  override def scoreRaw(question: RubricQuestion, response: String): (Double, String) = {
    val normalized = normalizeText(response)
    if (normalized.isEmpty) {
      0.0d -> "blank response"
    } else if (question.keywords.isEmpty) {
      val rawScore = if (normalized.length >= minLength) question.maxPoints else 0.0d
      val feedback = if (rawScore > 0.0d) "free response accepted" else "response too short"
      roundScore(rawScore) -> feedback
    } else {
      val matched = question.keywords.filter(keyword => normalized.contains(keyword))
      val ratio = matched.size.toDouble / question.keywords.size.toDouble
      val bonus = if (ratio == 1.0d && normalized.length >= minLength) bonusPoints else 0.0d
      val rawScore = roundScore(clamp(question.maxPoints * ratio + bonus, 0.0d, question.maxPoints))
      val suffix = if (normalized.length < minLength) "; below length target" else ""
      rawScore -> s"matched ${matched.size}/${question.keywords.size} keywords$suffix"
    }
  }
}

final class NumericRubricScorer(target: Double, tolerance: Double, partialCredit: Double = 0.5d)
    extends AbstractScorer("numeric") {
  private val numberPattern: Regex = "-?\\d+(?:\\.\\d+)?".r

  private def extractNumber(response: String): Option[Double] =
    numberPattern.findFirstIn(response).map(_.toDouble)

  override def scoreRaw(question: RubricQuestion, response: String): (Double, String) =
    extractNumber(response) match {
      case None =>
        0.0d -> "no numeric answer"
      case Some(value) =>
        val delta = math.abs(value - target)
        if (delta <= tolerance) {
          roundScore(question.maxPoints) -> "exact numeric match"
        } else if (delta <= tolerance * 2.0d) {
          roundScore(question.maxPoints * partialCredit) -> "close numeric match"
        } else {
          0.0d -> s"outside tolerance by ${formatScore(delta)}"
        }
    }
}

final class WeightedRubricScorer(components: Vector[(String, AbstractScorer, Double)])
    extends AbstractScorer("weighted") {
  require(components.nonEmpty, "WeightedRubricScorer requires at least one component")

  private def evaluateComponents(question: RubricQuestion, response: String): Vector[(String, Double, String, Double)] =
    components.map { case (label, scorer, weight) =>
      val evaluation = scorer.scoreRaw(question, response)
      (label, roundScore(evaluation._1), evaluation._2, weight)
    }

  override def scoreRaw(question: RubricQuestion, response: String): (Double, String) = {
    val rows = evaluateComponents(question, response)
    val totalWeight = rows.map(_._4).sum
    val weightedRatio = rows.map { case (_, rawScore, _, weight) =>
      val componentRatio = if (question.maxPoints == 0.0d) 0.0d else rawScore / question.maxPoints
      componentRatio * weight
    }.sum / totalWeight
    val feedback = rows.map { case (label, _, itemFeedback, _) =>
      s"$label=$itemFeedback"
    }.mkString("; ")
    roundScore(question.maxPoints * weightedRatio) -> feedback
  }

  override def buildResult(question: RubricQuestion, response: String, metadata: (String, String)*): ScoreResult = {
    val rows = evaluateComponents(question, response)
    val totalWeight = rows.map(_._4).sum
    val weightedRatio = rows.map { case (_, rawScore, _, weight) =>
      val componentRatio = if (question.maxPoints == 0.0d) 0.0d else rawScore / question.maxPoints
      componentRatio * weight
    }.sum / totalWeight
    val rawScore = roundScore(question.maxPoints * weightedRatio)
    val feedback = rows.map { case (label, _, itemFeedback, _) =>
      s"$label=$itemFeedback"
    }.mkString("; ")
    val summary = rows.map { case (label, rawValue, _, weight) =>
      s"$label:${formatScore(rawValue)}@${f"$weight%.2f"}"
    }.mkString(",")
    super
      .buildResult(
        question,
        response,
        (metadata.toMap ++ Map(
          "component_summary" -> summary,
          "component_count" -> rows.size.toString
        )).toSeq: _*
      )
      .copy(rawScore = rawScore, weightedScore = roundScore(rawScore * question.weight), feedback = feedback)
      .withMetadata("weighted_feedback" -> feedback)
  }
}

final class BatchRubricScorer private (
    questions: Vector[RubricQuestion],
    scorers: Map[String, AbstractScorer],
    cohortName: String
) {
  def scoreSubmission(studentId: String, responses: Map[String, String]): SubmissionReport = {
    val results = questions.map { question =>
      val scorer = scorers(question.questionId)
      val response = responses.getOrElse(question.questionId, "")
      scorer.buildResult(
        question,
        response,
        "student" -> studentId.trim,
        "cohort" -> cohortName,
        "weight" -> formatScore(question.weight)
      )
    }

    SubmissionReport.fromResults(
      studentId,
      results,
      Map("cohort" -> cohortName, "question_count" -> questions.size.toString)
    )
  }

  def scoreAll(submissions: Iterable[(String, Map[String, String])]): Vector[SubmissionReport] =
    submissions.iterator.map { case (studentId, answers) =>
      scoreSubmission(studentId, answers)
    }.toVector

  def averageRatio(reports: Iterable[SubmissionReport]): Double = {
    val values = reports.iterator.toVector
    if (values.isEmpty) 0.0d else roundScore(values.map(_.averageRatio()).sum / values.size.toDouble)
  }
}

object BatchRubricScorer {
  def apply(
      questions: Seq[RubricQuestion],
      scorers: Map[String, AbstractScorer],
      cohortName: String = "default"
  ): BatchRubricScorer =
    new BatchRubricScorer(questions.toVector, scorers, if (cohortName.trim.nonEmpty) cohortName.trim else "default")
}
EOF
