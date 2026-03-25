#!/bin/bash
set -euo pipefail

cat <<'EOF' > /root/DependencyPlannerApp.scala
package dependencyplanner

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Paths}
import scala.util.Try
import ujson.{Arr, Obj, Value}

final case class TaskNode(id: String, dependencies: Vector[String], priority: Int)

final case class TaskGraph(graphId: String, tasks: Vector[TaskNode])

sealed trait PlannerIssue {
  def kind: String
  def taskId: String
}

final case class DuplicateTask(taskId: String) extends PlannerIssue {
  override val kind: String = "duplicate-task"
}

final case class UnknownDependency(taskId: String, dependencyId: String) extends PlannerIssue {
  override val kind: String = "unknown-dependency"
}

final case class TopologySnapshot(executionOrder: Vector[String], remaining: Vector[String])

final case class PlanReport(
  graphId: String,
  status: String,
  executionOrder: Vector[String],
  cycles: Vector[Vector[String]],
  unresolved: Vector[String],
  errors: Vector[PlannerIssue]
) {
  def firstCycleTask: Option[String] = cycles.headOption.flatMap(_.headOption)
}

object DependencyPlanner {
  private val Planned = "planned"
  private val Cycle = "cycle"
  private val Invalid = "invalid"

  def fromJson(raw: String): Either[String, Vector[TaskGraph]] =
    Try(ujson.read(raw)).toEither.left.map(_.getMessage).flatMap(parsePayload)

  private def parsePayload(value: Value): Either[String, Vector[TaskGraph]] =
    for {
      obj <- asObject(value, "payload root must be an object")
      graphsValue <- obj.get("graphs").toRight("missing graphs")
      graphs <- parseGraphs(graphsValue)
    } yield graphs

  private def parseGraphs(value: Value): Either[String, Vector[TaskGraph]] =
    Try(value.arr.toVector).toEither.left.map(_.getMessage).flatMap { items =>
      items.foldLeft[Either[String, Vector[TaskGraph]]](Right(Vector.empty)) { (acc, item) =>
        for {
          graphs <- acc
          graph <- parseGraph(item)
        } yield graphs :+ graph
      }
    }

  private def parseGraph(value: Value): Either[String, TaskGraph] =
    for {
      obj <- asObject(value, "graph must be an object")
      graphId <- readString(obj, "graphId")
      tasksValue <- obj.get("tasks").toRight("tasks is required")
      tasks <- parseTasks(tasksValue)
    } yield TaskGraph(graphId, tasks)

  private def parseTasks(value: Value): Either[String, Vector[TaskNode]] =
    Try(value.arr.toVector).toEither.left.map(_.getMessage).flatMap { items =>
      items.foldLeft[Either[String, Vector[TaskNode]]](Right(Vector.empty)) { (acc, item) =>
        for {
          tasks <- acc
          task <- parseTask(item)
        } yield tasks :+ task
      }
    }

  private def parseTask(value: Value): Either[String, TaskNode] =
    for {
      obj <- asObject(value, "task must be an object")
      id <- readString(obj, "id")
      dependenciesValue <- obj.get("dependencies").toRight("dependencies is required")
      dependencies <- readStringArray(dependenciesValue, "dependencies")
      priority <- readInt(obj, "priority")
    } yield TaskNode(id, dependencies, priority)

  private def asObject(value: Value, errorMessage: String): Either[String, collection.Map[String, Value]] =
    Try(value.obj).toEither.left.map(_ => errorMessage)

  private def readString(obj: collection.Map[String, Value], key: String): Either[String, String] =
    obj.get(key).toRight(s"$key is required").flatMap { value =>
      Try(value.str).toEither.left.map(_ => s"$key must be a string")
    }

  private def readStringArray(value: Value, key: String): Either[String, Vector[String]] =
    Try(value.arr.toVector.map(_.str)).toEither.left.map(_ => s"$key must be an array of strings")

  private def readInt(obj: collection.Map[String, Value], key: String): Either[String, Int] =
    obj.get(key).toRight(s"$key is required").flatMap { value =>
      Try(value.num.toInt).toEither.left.map(_ => s"$key must be a number")
    }

  def stableTopologicalOrder(graph: TaskGraph): TopologySnapshot = {
    val tasksById = graph.tasks.iterator.map(task => task.id -> task).toMap
    val dependents = graph.tasks.foldLeft(Map.empty[String, Vector[String]].withDefaultValue(Vector.empty)) {
      case (acc, task) =>
        task.dependencies.foldLeft(acc) { (inner, dependencyId) =>
          inner.updated(dependencyId, inner(dependencyId) :+ task.id)
        }
    }
    val initialDegrees = graph.tasks.iterator.map(task => task.id -> task.dependencies.size).toMap
    val initialReady = initialDegrees.collect { case (taskId, degree) if degree == 0 => taskId }.toVector

    @annotation.tailrec
    def loop(
      ready: Vector[String],
      degrees: Map[String, Int],
      order: Vector[String]
    ): TopologySnapshot =
      if (ready.isEmpty) {
        TopologySnapshot(order, degrees.collect { case (taskId, degree) if degree > 0 => taskId }.toVector.sorted)
      } else {
        val nextTaskId = ready.minBy(taskId => (tasksById(taskId).priority, taskId))
        val remainingReady = ready.filterNot(_ == nextTaskId)
        val baseDegrees = degrees - nextTaskId
        val (nextDegrees, nextReady) = dependents(nextTaskId).foldLeft((baseDegrees, remainingReady)) {
          case ((degreeMap, readyIds), dependentId) =>
            degreeMap.get(dependentId) match {
              case Some(currentDegree) =>
                val updatedDegree = currentDegree - 1
                val updatedDegrees = degreeMap.updated(dependentId, updatedDegree)
                if (updatedDegree == 0) (updatedDegrees, readyIds :+ dependentId)
                else (updatedDegrees, readyIds)
              case None =>
                (degreeMap, readyIds)
            }
        }
        loop(nextReady, nextDegrees, order :+ nextTaskId)
      }

    loop(initialReady, initialDegrees, Vector.empty)
  }

  def findCycles(graph: TaskGraph, remaining: Vector[String]): Vector[Vector[String]] = {
    val remainingSet = remaining.toSet
    val adjacency = graph.tasks.iterator
      .filter(task => remainingSet(task.id))
      .map(task => task.id -> task.dependencies.filter(remainingSet))
      .toMap

    var nextIndex = 0
    var stack = List.empty[String]
    var onStack = Set.empty[String]
    var indices = Map.empty[String, Int]
    var lowLinks = Map.empty[String, Int]
    var components = Vector.empty[Vector[String]]

    def strongConnect(taskId: String): Unit = {
      indices = indices.updated(taskId, nextIndex)
      lowLinks = lowLinks.updated(taskId, nextIndex)
      nextIndex += 1
      stack = taskId :: stack
      onStack += taskId

      adjacency.getOrElse(taskId, Vector.empty).foreach { nextTaskId =>
        if (!indices.contains(nextTaskId)) {
          strongConnect(nextTaskId)
          lowLinks = lowLinks.updated(taskId, math.min(lowLinks(taskId), lowLinks(nextTaskId)))
        } else if (onStack.contains(nextTaskId)) {
          lowLinks = lowLinks.updated(taskId, math.min(lowLinks(taskId), indices(nextTaskId)))
        }
      }

      if (lowLinks(taskId) == indices(taskId)) {
        val buffer = Vector.newBuilder[String]
        var done = false
        while (!done && stack.nonEmpty) {
          val member = stack.head
          stack = stack.tail
          onStack -= member
          buffer += member
          done = member == taskId
        }

        val component = buffer.result().sorted
        val selfLoop = adjacency.getOrElse(taskId, Vector.empty).contains(taskId)
        if (component.size > 1 || selfLoop) {
          components = components :+ component
        }
      }
    }

    remaining.sorted.foreach { taskId =>
      if (!indices.contains(taskId)) {
        strongConnect(taskId)
      }
    }

    components.sortBy(_.headOption.getOrElse(""))
  }

  def plan(graph: TaskGraph): Either[Vector[PlannerIssue], PlanReport] = {
    val issues = validate(graph)
    if (issues.nonEmpty) {
      Left(issues)
    } else {
      val snapshot = stableTopologicalOrder(graph)
      val cycles = if (snapshot.remaining.nonEmpty) findCycles(graph, snapshot.remaining) else Vector.empty
      val status = if (cycles.nonEmpty) Cycle else Planned
      val unresolved = cycles.flatten.distinct.sorted
      Right(
        PlanReport(
          graphId = graph.graphId,
          status = status,
          executionOrder = snapshot.executionOrder,
          cycles = cycles,
          unresolved = unresolved,
          errors = Vector.empty
        )
      )
    }
  }

  def planAll(graphs: Vector[TaskGraph]): Vector[PlanReport] =
    graphs.map { graph =>
      plan(graph).fold(
        issues =>
          PlanReport(
            graphId = graph.graphId,
            status = Invalid,
            executionOrder = Vector.empty,
            cycles = Vector.empty,
            unresolved = issues.map(_.taskId).distinct.sorted,
            errors = issues
          ),
        identity
      )
    }

  def renderReports(reports: Vector[PlanReport]): String = {
    val rendered = Obj(
      "reports" -> Arr.from(reports.map(reportToJson))
    )
    ujson.write(rendered, indent = 2)
  }

  private def validate(graph: TaskGraph): Vector[PlannerIssue] = {
    val duplicateIssues = graph.tasks
      .groupBy(_.id)
      .collect { case (taskId, tasks) if tasks.size > 1 => DuplicateTask(taskId): PlannerIssue }
      .toVector
      .sortBy(_.taskId)

    val knownIds = graph.tasks.map(_.id).toSet
    val missingIssues = graph.tasks
      .sortBy(_.id)
      .flatMap { task =>
        task.dependencies.sorted.collect {
          case dependencyId if !knownIds.contains(dependencyId) =>
            UnknownDependency(task.id, dependencyId): PlannerIssue
        }
      }

    duplicateIssues ++ missingIssues
  }

  private def reportToJson(report: PlanReport): Value =
    Obj(
      "graphId" -> report.graphId,
      "status" -> report.status,
      "executionOrder" -> Arr.from(report.executionOrder),
      "cycles" -> Arr.from(report.cycles.map(cycle => Arr.from(cycle))),
      "unresolved" -> Arr.from(report.unresolved),
      "errors" -> Arr.from(report.errors.map(issueToJson))
    )

  private def issueToJson(issue: PlannerIssue): Value = issue match {
    case DuplicateTask(taskId) =>
      Obj(
        "kind" -> issue.kind,
        "taskId" -> taskId
      )
    case UnknownDependency(taskId, dependencyId) =>
      Obj(
        "kind" -> issue.kind,
        "taskId" -> taskId,
        "dependencyId" -> dependencyId
      )
  }
}

object DependencyPlannerApp {
  def main(args: Array[String]): Unit =
    args.toVector match {
      case Vector(inputPath, outputPath) =>
        val payload = new String(Files.readAllBytes(Paths.get(inputPath)), StandardCharsets.UTF_8)
        val graphs = DependencyPlanner.fromJson(payload) match {
          case Right(value) => value
          case Left(error) => throw new IllegalArgumentException(error)
        }
        val rendered = DependencyPlanner.renderReports(DependencyPlanner.planAll(graphs)) + "\n"
        Files.write(Paths.get(outputPath), rendered.getBytes(StandardCharsets.UTF_8))
      case _ =>
        throw new IllegalArgumentException("usage: DependencyPlannerApp <input-json> <output-json>")
    }
}
EOF
