#!/bin/bash

set -euo pipefail

cat <<'EOF' > /root/SupportTopicReport.scala
import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Paths}
import scala.jdk.CollectionConverters._
import scala.util.matching.Regex

object SupportTopicReport {
  final case class Ticket(
      ticketId: String,
      queue: String,
      agent: String,
      status: String,
      subject: String,
      body: String
  )

  private val WordRegex: Regex = "[A-Za-z]+".r

  private def readLines(path: String): List[String] =
    Files.readAllLines(Paths.get(path), StandardCharsets.UTF_8).asScala.toList

  def loadTickets(path: String): List[Ticket] = {
    val lines = readLines(path)
    val header = lines.head.split("\t", -1).map(_.trim).toList
    val indexByName = header.zipWithIndex.toMap

    lines.tail.filter(_.nonEmpty).map { line =>
      val cells = line.split("\t", -1).map(_.trim)
      def value(name: String): String = cells(indexByName(name))
      Ticket(
        ticketId = value("ticket_id"),
        queue = value("queue"),
        agent = value("agent"),
        status = value("status"),
        subject = value("subject"),
        body = value("body")
      )
    }
  }

  def loadStopwords(path: String): Set[String] =
    readLines(path)
      .map(_.trim.toLowerCase)
      .filter(_.nonEmpty)
      .toSet

  def extractTicketTerms(ticket: Ticket, stopwords: Set[String]): List[String] = {
    val text = s"${ticket.subject} ${ticket.body}".toLowerCase
    WordRegex
      .findAllIn(text)
      .filter(word => word.length >= 4 && !stopwords.contains(word))
      .toSet
      .toList
      .sorted
  }

  private def topTerms(termCounts: Map[String, Int], limit: Int): List[String] =
    termCounts.toList
      .sortBy { case (term, count) => (-count, term) }
      .take(limit)
      .map(_._1)

  private def joinTerms(values: Seq[String]): String =
    if (values.isEmpty) "-" else values.mkString(",")

  def buildReportLines(tickets: List[Ticket], stopwords: Set[String]): List[String] = {
    val ticketTerms = tickets.map(ticket => ticket.ticketId -> extractTicketTerms(ticket, stopwords)).toMap

    val queueRows = tickets
      .groupBy(_.queue)
      .toList
      .map { case (queue, queueTickets) =>
        val termCounts = queueTickets
          .flatMap(ticket => ticketTerms.getOrElse(ticket.ticketId, Nil))
          .groupMapReduce(identity)(_ => 1)(_ + _)
        val topics = topTerms(termCounts, 5)
        val activeCount = queueTickets.count(ticket => {
          val status = ticket.status.toLowerCase
          status == "open" || status == "pending"
        })
        val agentCount = queueTickets.map(_.agent).distinct.size
        (queue, queueTickets.size, activeCount, agentCount, topics)
      }
      .sortBy { case (queue, ticketCount, activeCount, _, _) => (-activeCount, -ticketCount, queue) }

    val queueTopTermSets = queueRows.map { case (queue, _, _, _, topics) =>
      queue -> topics.toSet
    }.toMap

    val agentRows = tickets
      .groupBy(_.agent)
      .toList
      .map { case (agent, agentTickets) =>
        val termCounts = agentTickets
          .flatMap(ticket => ticketTerms.getOrElse(ticket.ticketId, Nil))
          .groupMapReduce(identity)(_ => 1)(_ + _)
        val queues = agentTickets.map(_.queue).distinct.sorted
        val topics = topTerms(termCounts, 3)
        (agent, agentTickets.size, queues, topics)
      }
      .sortBy { case (agent, ticketCount, queues, _) => (-queues.size, -ticketCount, agent) }

    val overlapRows = queueTopTermSets.keys.toList.sorted
      .combinations(2)
      .flatMap {
        case List(queueA, queueB) =>
          val shared = (queueTopTermSets(queueA) intersect queueTopTermSets(queueB)).toList.sorted
          if (shared.nonEmpty) Some((queueA, queueB, shared)) else None
        case _ => None
      }
      .toList
      .sortBy { case (queueA, queueB, shared) => (-shared.size, queueA, queueB) }

    val queueLines = queueRows.map { case (queue, ticketCount, activeCount, agentCount, topics) =>
      s"QUEUE\t${queue}\t${ticketCount}\t${activeCount}\t${agentCount}\t${joinTerms(topics)}"
    }

    val agentLines = agentRows.map { case (agent, ticketCount, queues, topics) =>
      s"AGENT\t${agent}\t${ticketCount}\t${queues.mkString(",")}\t${joinTerms(topics)}"
    }

    val overlapLines = overlapRows.map { case (queueA, queueB, shared) =>
      s"OVERLAP\t${queueA}\t${queueB}\t${joinTerms(shared)}"
    }

    List("QUEUE SUMMARY") ::: queueLines ::: List("", "AGENT SUMMARY") ::: agentLines ::: List("", "QUEUE OVERLAPS") ::: overlapLines
  }

  def writeReport(ticketsPath: String, stopwordsPath: String, outputPath: String): Unit = {
    val tickets = loadTickets(ticketsPath)
    val stopwords = loadStopwords(stopwordsPath)
    val content = buildReportLines(tickets, stopwords).mkString("", "\n", "\n")
    Files.write(Paths.get(outputPath), content.getBytes(StandardCharsets.UTF_8))
  }

  def main(args: Array[String]): Unit = {
    if (args.length != 3) {
      Console.err.println("Usage: SupportTopicReport <tickets.tsv> <stopwords.txt> <output.txt>")
      System.exit(1)
    }
    writeReport(args(0), args(1), args(2))
  }
}
EOF
