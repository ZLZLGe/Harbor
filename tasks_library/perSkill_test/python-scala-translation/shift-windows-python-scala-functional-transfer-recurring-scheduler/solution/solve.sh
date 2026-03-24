#!/bin/bash
set -euo pipefail

cat <<'EOF' > /root/ShiftWindowPlanner.scala
import java.time.LocalDateTime

final case class TimeRange(start: LocalDateTime, end: LocalDateTime) {
  def overlaps(other: TimeRange): Boolean =
    start.isBefore(other.end) && other.start.isBefore(end)

  def merge(other: TimeRange): TimeRange =
    TimeRange(
      if (start.isBefore(other.start)) start else other.start,
      if (end.isAfter(other.end)) end else other.end
    )
}

final case class ShiftTemplate(
  workerId: String,
  window: TimeRange,
  repeatEveryDays: Option[Int] = None,
  occurrenceCount: Option[Int] = Some(1),
  until: Option[LocalDateTime] = None,
  tags: Vector[String] = Vector.empty
)

final case class BlockedWindow(
  window: TimeRange,
  workerId: Option[String] = None,
  reason: String = ""
)

final case class PlannerConfig(
  mergeGapMinutes: Option[Int] = None,
  labelPrefix: Option[String] = None,
  requiredTags: Option[Vector[String]] = None,
  maxResults: Option[Int] = None,
  defaultRepeatDays: Option[Int] = None
) {
  def normalized(defaults: PlannerConfig = PlannerConfig.defaults): PlannerConfig =
    PlannerConfig(
      mergeGapMinutes = Some(mergeGapMinutes.orElse(defaults.mergeGapMinutes).getOrElse(0)),
      labelPrefix = Some(labelPrefix.orElse(defaults.labelPrefix).getOrElse("")),
      requiredTags = Some(requiredTags.orElse(defaults.requiredTags).getOrElse(Vector.empty)),
      maxResults = maxResults.orElse(defaults.maxResults),
      defaultRepeatDays = Some(defaultRepeatDays.orElse(defaults.defaultRepeatDays).getOrElse(7))
    )
}

object PlannerConfig {
  val defaults: PlannerConfig =
    PlannerConfig(
      mergeGapMinutes = Some(0),
      labelPrefix = Some(""),
      requiredTags = Some(Vector.empty),
      maxResults = None,
      defaultRepeatDays = Some(7)
    )
}

final case class PlannedShift(
  workerId: String,
  window: TimeRange,
  label: String,
  tags: Vector[String] = Vector.empty
)

object ShiftWindowPlanner {
  def withFallbackConfig(
    config: Option[PlannerConfig] = None,
    defaults: PlannerConfig = PlannerConfig.defaults
  ): PlannerConfig =
    config.getOrElse(PlannerConfig()).normalized(defaults)

  def weekly(
    workerId: String,
    start: LocalDateTime,
    end: LocalDateTime,
    weeks: Int,
    tags: Vector[String] = Vector.empty
  ): ShiftTemplate =
    ShiftTemplate(
      workerId = workerId,
      window = TimeRange(start, end),
      repeatEveryDays = Some(7),
      occurrenceCount = Some(weeks),
      until = None,
      tags = tags
    )

  def expandRecurring(
    template: ShiftTemplate,
    config: PlannerConfig = PlannerConfig.defaults
  ): LazyList[PlannedShift] = {
    val normalized = config.normalized()
    val repeatDays = template.repeatEveryDays.orElse(normalized.defaultRepeatDays).getOrElse(7)
    val labelSuffix = template.tags.headOption match {
      case Some(tag) => tag
      case None => "shift"
    }
    val label = s"${normalized.labelPrefix.getOrElse("")}${template.workerId}:$labelSuffix"

    def loop(window: TimeRange, index: Int): LazyList[PlannedShift] = {
      val pastCount = template.occurrenceCount.exists(index >= _)
      val pastUntil = template.until.exists(window.start.isAfter)
      if (pastCount || pastUntil) {
        LazyList.empty
      } else {
        val current = PlannedShift(template.workerId, window, label, template.tags)
        val shouldContinue = template.occurrenceCount.isDefined || template.until.isDefined
        if (!shouldContinue) {
          current #:: LazyList.empty
        } else {
          val nextWindow = TimeRange(window.start.plusDays(repeatDays.toLong), window.end.plusDays(repeatDays.toLong))
          current #:: loop(nextWindow, index + 1)
        }
      }
    }

    loop(template.window, 0)
  }

  def filterConflicts(
    candidates: Iterator[PlannedShift],
    blockedWindows: Iterable[BlockedWindow]
  ): Iterator[PlannedShift] = {
    val blocked = blockedWindows.toVector
    candidates.filterNot { shift =>
      blocked.exists { block =>
        block.workerId.forall(_ == shift.workerId) && shift.window.overlaps(block.window)
      }
    }
  }

  def mergeRanges(
    candidates: Iterable[PlannedShift],
    config: PlannerConfig = PlannerConfig.defaults
  ): Vector[PlannedShift] = {
    val normalized = config.normalized()
    val gapMinutes = normalized.mergeGapMinutes.getOrElse(0).toLong
    val ordered = candidates.toVector.sortBy { shift =>
      (
        shift.workerId,
        shift.label,
        shift.window.start.toString,
        shift.window.end.toString,
        shift.tags.mkString("|")
      )
    }

    ordered.foldLeft(Vector.empty[PlannedShift]) { (acc, shift) =>
      acc.lastOption match {
        case Some(last)
            if last.workerId == shift.workerId &&
              last.label == shift.label &&
              last.tags == shift.tags &&
              !shift.window.start.isAfter(last.window.end.plusMinutes(gapMinutes)) =>
          acc.init :+ last.copy(window = last.window.merge(shift.window))
        case _ =>
          acc :+ shift
      }
    }
  }

  def plan(
    templates: Iterable[ShiftTemplate],
    blockedWindows: Iterable[BlockedWindow],
    config: Option[PlannerConfig] = None,
    defaults: PlannerConfig = PlannerConfig.defaults
  ): Vector[PlannedShift] = {
    val normalized = withFallbackConfig(config, defaults)
    val requiredTags = normalized.requiredTags.getOrElse(Vector.empty).toSet
    val expanded = templates.iterator.flatMap(template => expandRecurring(template, normalized).iterator)
    val tagged = for {
      shift <- expanded
      if requiredTags.isEmpty || shift.tags.exists(requiredTags.contains)
    } yield shift

    val merged = mergeRanges(filterConflicts(tagged, blockedWindows).toVector, normalized)
    normalized.maxResults match {
      case Some(limit) => merged.take(limit)
      case None => merged
    }
  }
}
EOF
