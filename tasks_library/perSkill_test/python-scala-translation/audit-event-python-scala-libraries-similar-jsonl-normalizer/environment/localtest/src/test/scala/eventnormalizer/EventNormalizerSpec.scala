package eventnormalizer

import io.circe.parser.parse
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import java.nio.file.{Files, Path, Paths}
import scala.jdk.CollectionConverters._

class EventNormalizerSpec extends AnyFlatSpec with Matchers {

  private val expectedSummary = EventSummary(
    total = 5,
    bySeverity = Map("low" -> 2, "medium" -> 1, "high" -> 2),
    byActor = Map(
      "backup-daemon" -> 1,
      "bot-sync" -> 1,
      "ops@example.com" -> 2,
      "sec@example.com" -> 1
    ),
    labelCounts = Map(
      "auth" -> 1,
      "cold" -> 1,
      "config" -> 1,
      "iam" -> 2,
      "p1" -> 1,
      "platform" -> 1,
      "prod" -> 2,
      "retention" -> 1
    ),
    windowStart = "2024-11-05T08:15:30Z",
    windowEnd = "2024-11-06T00:00:00Z"
  )

  "EventNormalizer" should "normalize supported timestamp formats to UTC" in {
    val normalizer = new EventNormalizer()

    normalizer.normalizeTimestamp("2024-11-05T08:15:30Z") shouldBe "2024-11-05T08:15:30Z"
    normalizer.normalizeTimestamp("2024-11-05 08:16:10") shouldBe "2024-11-05T08:16:10Z"
    normalizer.normalizeTimestamp("2024/11/05 16:20:00 +0800") shouldBe "2024-11-05T08:20:00Z"
    normalizer.normalizeTimestamp("2024-11-06") shouldBe "2024-11-06T00:00:00Z"
  }

  it should "extract lowercase unique labels in first-seen order" in {
    val normalizer = new EventNormalizer()

    normalizer.extractLabels("console#Prod #IAM", "rotate #iam #P1") shouldBe List("prod", "iam", "p1")
  }

  it should "parse a JSONL line into a normalized audit event" in {
    val normalizer = new EventNormalizer()
    val line =
      """{"id":"evt-003","occurred_at":"2024/11/05 16:20:00 +0800","principal":"sec@example.com","type":"revoke-key","object":"service/api#Auth","note":"Emergency rotation #P1 #Auth"}"""

    val event = normalizer.parseLine(line)

    event.eventId shouldBe "evt-003"
    event.timestamp shouldBe "2024-11-05T08:20:00Z"
    event.actor shouldBe "sec@example.com"
    event.action shouldBe "REVOKE_KEY"
    event.resource shouldBe "service/api#Auth"
    event.severity shouldBe "high"
    event.labels shouldBe List("auth", "p1")
    event.metadata shouldBe Map("rawTime" -> "2024/11/05 16:20:00 +0800", "source" -> "inline")
  }

  it should "normalize a file, emit JSONL, and return the expected summary" in {
    val inputResource = Paths.get(getClass.getResource("/audit-log.jsonl").toURI)
    val tempDir = Files.createTempDirectory("event-normalizer-spec")
    val inputPath = tempDir.resolve("audit-log.jsonl")
    Files.copy(inputResource, inputPath)

    val normalizer = new EventNormalizer(tempDir)
    val summary = normalizer.normalizeFile("audit-log.jsonl", "out/normalized.jsonl")

    summary shouldBe expectedSummary

    val outputPath = tempDir.resolve("out/normalized.jsonl")
    Files.exists(outputPath) shouldBe true

    val lines = Files.readAllLines(outputPath).asScala.toList.filter(_.nonEmpty)
    lines should have size 5

    val firstJson = parse(lines.head).toOption.get
    firstJson.hcursor.get[String]("eventId").toOption shouldBe Some("evt-001")
    firstJson.hcursor.get[String]("timestamp").toOption shouldBe Some("2024-11-05T08:15:30Z")
    firstJson.hcursor.get[String]("severity").toOption shouldBe Some("low")
  }

  it should "load and summarize a JSONL file without writing output" in {
    val inputResource = Paths.get(getClass.getResource("/audit-log.jsonl").toURI)
    val tempDir = Files.createTempDirectory("event-normalizer-summary")
    val inputPath = tempDir.resolve("audit-log.jsonl")
    Files.copy(inputResource, inputPath)

    val normalizer = new EventNormalizer(tempDir)

    normalizer.loadAndSummarize("audit-log.jsonl") shouldBe expectedSummary
  }
}
