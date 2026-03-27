#!/bin/bash
set -euo pipefail

cat > /app/workspace/transfer1.scala <<'SCALA'
abstract class Job(val name: String) {
  def run: String
}

final case class CsvJob(override val name: String, path: String) extends Job(name) {
  override def run: String = s"csv:$name:$path"
}

final case class ApiJob(override val name: String, endpoint: String) extends Job(name) {
  override def run: String = s"api:$name:$endpoint"
}

object JobFactory {
  def fromKind(kind: String, name: String, arg: String): Job = kind match {
    case "csv" => CsvJob(name, arg)
    case _ => ApiJob(name, arg)
  }
}

object JobRunner {
  def runBatch(jobs: Seq[Job]): Seq[String] =
    jobs.map(_.run)
}
SCALA
