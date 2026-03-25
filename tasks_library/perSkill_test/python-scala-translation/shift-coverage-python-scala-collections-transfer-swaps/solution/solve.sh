#!/bin/bash

set -euo pipefail

cat <<'EOF' > /root/ShiftCoveragePlanner.scala
import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Paths}
import scala.io.Source

object ShiftCoveragePlanner {
  final case class ShiftNeed(date: String, slot: String, role: String, requiredStaff: Int)
  final case class EmployeeSkill(
      employeeId: String,
      roles: Vector[String],
      preferredSlots: Vector[String],
      unavailableDates: Vector[String]
  )
  final case class LeavePreference(
      employeeId: String,
      date: String,
      avoidSlots: Vector[String],
      priority: Int,
      note: String
  )
  final case class CoverageGap(
      date: String,
      slot: String,
      role: String,
      requiredStaff: Int,
      assignedEmployees: Vector[String],
      missingCount: Int
  )
  final case class EmployeeConflict(employeeId: String, date: String, slot: String, roles: Vector[String])
  final case class SwapSuggestion(
      date: String,
      slot: String,
      role: String,
      fromEmployee: String,
      toEmployee: String,
      score: Int,
      reasons: Vector[String]
  )
  final case class PlanningResult(
      gaps: Vector[CoverageGap],
      conflicts: Vector[EmployeeConflict],
      suggestions: Vector[SwapSuggestion]
  )

  private def splitCsvLine(line: String): Vector[String] = {
    val builder = Vector.newBuilder[String]
    val current = new StringBuilder
    var inQuotes = false
    var index = 0
    while (index < line.length) {
      val ch = line.charAt(index)
      if (ch == '"') {
        if (inQuotes && index + 1 < line.length && line.charAt(index + 1) == '"') {
          current.append('"')
          index += 1
        } else {
          inQuotes = !inQuotes
        }
      } else if (ch == ',' && !inQuotes) {
        builder += current.toString
        current.clear()
      } else {
        current.append(ch)
      }
      index += 1
    }
    builder += current.toString
    builder.result().map(_.trim)
  }

  private def readRows(path: String): Vector[Map[String, String]] = {
    val source = Source.fromFile(path, "UTF-8")
    try {
      val lines = source.getLines().toVector.filterNot(_.trim.isEmpty)
      if (lines.isEmpty) {
        Vector.empty
      } else {
        val header = splitCsvLine(lines.head)
        lines.tail.map { line =>
          val values = splitCsvLine(line)
          header.zipAll(values, "", "").map { case (key, value) => key.trim -> value.trim }.toMap
        }
      }
    } finally {
      source.close()
    }
  }

  private def splitPipe(value: String, lower: Boolean = false): Vector[String] =
    value
      .split("\\|", -1)
      .iterator
      .map(_.trim)
      .filter(_.nonEmpty)
      .map(part => if (lower) part.toLowerCase else part)
      .toVector

  private def leavePriority(
      leavePreferences: Vector[LeavePreference],
      employeeId: String,
      date: String,
      slot: String
  ): Int =
    leavePreferences
      .filter(pref =>
        pref.employeeId == employeeId &&
          pref.date == date &&
          (pref.avoidSlots.contains("all") || pref.avoidSlots.contains(slot))
      )
      .map(_.priority)
      .foldLeft(0)(math.max)

  private def prefersSlot(skill: EmployeeSkill, slot: String): Boolean =
    skill.preferredSlots.contains(slot)

  private def canCover(skill: EmployeeSkill, role: String, date: String): Boolean =
    skill.roles.contains(role) && !skill.unavailableDates.contains(date)

  private def joinValues(values: Vector[String]): String =
    if (values.isEmpty) "-" else values.mkString(",")

  def loadShiftNeeds(path: String): Vector[ShiftNeed] =
    readRows(path)
      .map { row =>
        ShiftNeed(
          date = row.getOrElse("date", "").trim,
          slot = row.getOrElse("slot", "").trim.toLowerCase,
          role = row.getOrElse("role", "").trim.toLowerCase,
          requiredStaff = row.getOrElse("required_staff", "0").trim.toInt
        )
      }
      .sortBy(need => (need.date, need.slot, need.role))

  def loadEmployeeSkills(path: String): Vector[EmployeeSkill] =
    readRows(path)
      .map { row =>
        EmployeeSkill(
          employeeId = row.getOrElse("employee_id", "").trim,
          roles = splitPipe(row.getOrElse("roles", ""), lower = true),
          preferredSlots = splitPipe(row.getOrElse("preferred_slots", ""), lower = true),
          unavailableDates = splitPipe(row.getOrElse("unavailable_dates", ""))
        )
      }
      .sortBy(_.employeeId)

  def loadLeavePreferences(path: String): Vector[LeavePreference] =
    readRows(path)
      .map { row =>
        LeavePreference(
          employeeId = row.getOrElse("employee_id", "").trim,
          date = row.getOrElse("date", "").trim,
          avoidSlots = splitPipe(row.getOrElse("avoid_slots", ""), lower = true),
          priority = row.getOrElse("priority", "0").trim.toInt,
          note = row.getOrElse("note", "").trim
        )
      }
      .sortBy(pref => (pref.date, pref.employeeId, pref.priority, pref.note))

  def planCoverage(
      shiftNeeds: Vector[ShiftNeed],
      employeeSkills: Vector[EmployeeSkill],
      leavePreferences: Vector[LeavePreference]
  ): PlanningResult = {
    val sortedNeeds = shiftNeeds.sortBy(need => (need.date, need.slot, need.role))

    val assignments = sortedNeeds.map { need =>
      val rankedCandidates = employeeSkills
        .filter(skill => canCover(skill, need.role, need.date))
        .sortBy { skill =>
          val leaveFlag = if (leavePriority(leavePreferences, skill.employeeId, need.date, need.slot) > 0) 1 else 0
          val preferredFlag = if (prefersSlot(skill, need.slot)) 0 else 1
          (leaveFlag, preferredFlag, skill.roles.size, skill.employeeId)
        }

      (need.date, need.slot, need.role) -> rankedCandidates.take(need.requiredStaff).map(_.employeeId)
    }.toMap

    val gaps = sortedNeeds.flatMap { need =>
      val assigned = assignments.getOrElse((need.date, need.slot, need.role), Vector.empty)
      val missing = need.requiredStaff - assigned.size
      if (missing > 0) {
        Some(
          CoverageGap(
            date = need.date,
            slot = need.slot,
            role = need.role,
            requiredStaff = need.requiredStaff,
            assignedEmployees = assigned,
            missingCount = missing
          )
        )
      } else {
        None
      }
    }

    val groupedAssignments = assignments.toVector
      .flatMap { case ((date, slot, role), employees) =>
        employees.map(employeeId => ((date, slot, employeeId), role))
      }
      .groupBy(_._1)

    val conflicts = groupedAssignments.toVector
      .flatMap { case ((date, slot, employeeId), rows) =>
        val roles = rows.map(_._2).distinct.sorted
        if (roles.size > 1) {
          Some(EmployeeConflict(employeeId = employeeId, date = date, slot = slot, roles = roles))
        } else {
          None
        }
      }
      .sortBy(conflict => (conflict.date, conflict.slot, conflict.employeeId))

    val conflictKeys = conflicts.map(conflict => (conflict.date, conflict.slot, conflict.employeeId)).toSet

    val assignedInSlot = assignments.toVector
      .flatMap { case ((date, slot, _), employees) =>
        employees.map(employeeId => ((date, slot), employeeId))
      }
      .groupBy(_._1)
      .view
      .mapValues(_.map(_._2).toSet)
      .toMap

    val suggestionMap = sortedNeeds
      .flatMap { need =>
        val assigned = assignments.getOrElse((need.date, need.slot, need.role), Vector.empty)
        val occupiedEmployees = assignedInSlot.getOrElse((need.date, need.slot), Set.empty[String])

        assigned.flatMap { fromEmployee =>
          val priority = leavePriority(leavePreferences, fromEmployee, need.date, need.slot)
          val hasConflict = conflictKeys.contains((need.date, need.slot, fromEmployee))
          if (priority == 0 && !hasConflict) {
            None
          } else {
            val replacement = employeeSkills
              .filter(skill =>
                skill.employeeId != fromEmployee &&
                  canCover(skill, need.role, need.date) &&
                  !occupiedEmployees.contains(skill.employeeId) &&
                  leavePriority(leavePreferences, skill.employeeId, need.date, need.slot) == 0
              )
              .sortBy(skill => (if (prefersSlot(skill, need.slot)) 0 else 1, skill.roles.size, skill.employeeId))
              .headOption

            replacement.map { candidate =>
              val reasons = Vector(
                if (hasConflict) Some("conflict") else None,
                if (priority > 0) Some("leave") else None,
                if (prefersSlot(candidate, need.slot)) Some("preferred-slot") else None
              ).flatten

              val suggestion = SwapSuggestion(
                date = need.date,
                slot = need.slot,
                role = need.role,
                fromEmployee = fromEmployee,
                toEmployee = candidate.employeeId,
                score = priority + (if (hasConflict) 3 else 0) + (if (prefersSlot(candidate, need.slot)) 1 else 0),
                reasons = reasons
              )

              (suggestion.date, suggestion.slot, suggestion.role, suggestion.fromEmployee, suggestion.toEmployee) -> suggestion
            }
          }
        }
      }
      .toMap

    val suggestions = suggestionMap.values.toVector.sortBy { suggestion =>
      (-suggestion.score, suggestion.date, suggestion.slot, suggestion.role, suggestion.fromEmployee, suggestion.toEmployee)
    }

    PlanningResult(gaps = gaps, conflicts = conflicts, suggestions = suggestions)
  }

  def renderPlan(result: PlanningResult): Vector[String] = {
    val gapLines =
      if (result.gaps.isEmpty) {
        Vector("GAP|-")
      } else {
        result.gaps.map { gap =>
          s"GAP|${gap.date}|${gap.slot}|${gap.role}|${gap.requiredStaff}|${joinValues(gap.assignedEmployees)}|${gap.missingCount}"
        }
      }

    val conflictLines =
      if (result.conflicts.isEmpty) {
        Vector("CONFLICT|-")
      } else {
        result.conflicts.map { conflict =>
          s"CONFLICT|${conflict.employeeId}|${conflict.date}|${conflict.slot}|${joinValues(conflict.roles)}"
        }
      }

    val suggestionLines =
      if (result.suggestions.isEmpty) {
        Vector("SWAP|-")
      } else {
        result.suggestions.map { suggestion =>
          s"SWAP|${suggestion.date}|${suggestion.slot}|${suggestion.role}|${suggestion.fromEmployee}|${suggestion.toEmployee}|${suggestion.score}|${joinValues(suggestion.reasons)}"
        }
      }

    Vector(
      "SUMMARY",
      s"SUMMARY|${result.gaps.size}|${result.conflicts.size}|${result.suggestions.size}",
      "",
      "GAPS"
    ) ++ gapLines ++ Vector("", "CONFLICTS") ++ conflictLines ++ Vector("", "SUGGESTIONS") ++ suggestionLines
  }

  def writePlan(result: PlanningResult, outputPath: String): Unit = {
    val content = renderPlan(result).mkString("", "\n", "\n")
    Files.write(Paths.get(outputPath), content.getBytes(StandardCharsets.UTF_8))
  }

  def main(args: Array[String]): Unit = {
    if (args.length != 4) {
      System.err.println(
        "Usage: ShiftCoveragePlanner <shift_requirements.csv> <employee_skills.csv> <leave_preferences.csv> <output_path>"
      )
      System.exit(1)
    }

    val shiftNeeds = loadShiftNeeds(args(0))
    val employeeSkills = loadEmployeeSkills(args(1))
    val leavePreferences = loadLeavePreferences(args(2))
    val result = planCoverage(shiftNeeds, employeeSkills, leavePreferences)
    writePlan(result, args(3))
  }
}
EOF
