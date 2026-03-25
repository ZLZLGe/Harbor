package csvnormalizer

import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers

class CsvNormalizerSpec extends AnyFunSuite with Matchers {
  test("catalogSchema exposes expected output columns and alias wiring") {
    val schema = CsvNormalizer.catalogSchema()

    schema.map(_.outputName) shouldBe Vector(
      "sku",
      "warehouse",
      "quantity",
      "unitPrice",
      "active",
      "tags"
    )
    schema.find(_.outputName == "warehouse").get.aliases should contain("site")
  }

  test("normalizeRow parses typed values and appends metadata") {
    val normalizer = new CsvNormalizer(CsvNormalizer.catalogSchema(), "partner-feed")
    val row = Map(
      "sku" -> "A-100",
      "site" -> " north ",
      "qty" -> "12",
      "unit_price" -> "1.995",
      "active" -> "YES",
      "labels" -> "Fresh | Promo "
    )

    val normalized = normalizer.normalizeRow(row, rowNumber = 7)

    normalized.values("sku") shouldBe Some(TextValue("A-100"))
    normalized.values("warehouse") shouldBe Some(TextValue("north"))
    normalized.values("quantity") shouldBe Some(IntegerValue(12))
    normalized.values("unitPrice") shouldBe Some(DecimalValue(BigDecimal("2.00")))
    normalized.values("active") shouldBe Some(FlagValue(true))
    normalized.values("tags") shouldBe Some(TagsValue(Vector("fresh", "promo")))
    normalized.issues shouldBe empty
    normalized.metadata("source") shouldBe "partner-feed"
    normalized.metadata("rowNumber") shouldBe "7"
    normalized.metadata("matchedInputs") shouldBe "sku,site,qty,unit_price,active,labels"
    normalized.metadata("issueCount") shouldBe "0"
  }

  test("optional fields stay optional and defaults still apply") {
    val normalizer = new CsvNormalizer(CsvNormalizer.catalogSchema(), "nightly")
    val row = Map(
      "sku" -> "B-220",
      "warehouse" -> "reserve",
      "qty" -> "3",
      "active" -> " "
    )

    val normalized = normalizer.normalizeRow(row, rowNumber = 2)

    normalized.values("unitPrice") shouldBe None
    normalized.values("tags") shouldBe None
    normalized.values("active") shouldBe Some(FlagValue(true))
    normalized.issues shouldBe empty
  }

  test("invalid rows collect issues without stopping later rows") {
    val normalizer = new CsvNormalizer(CsvNormalizer.catalogSchema(), "partner-feed")
    val rows = List(
      Map("sku" -> "X-1", "warehouse" -> "west", "qty" -> "oops"),
      Map("sku" -> "X-2", "warehouse" -> "west", "qty" -> "5", "active" -> "no")
    )

    val normalized = normalizer.normalizeRows(rows, startRow = 10).toList

    normalized.head.values("quantity") shouldBe None
    normalized.head.issues.map(_.column) should contain("quantity")
    normalized.head.metadata("rowNumber") shouldBe "10"

    normalized(1).values("quantity") shouldBe Some(IntegerValue(5))
    normalized(1).values("active") shouldBe Some(FlagValue(false))
    normalized(1).metadata("rowNumber") shouldBe "11"
  }

  test("withMetadata appends keys without dropping the previous map") {
    val row = NormalizedRow(
      values = Map("sku" -> Some(TextValue("A-100"))),
      metadata = Map("source" -> "seed")
    ).withMetadata("job" -> "nightly", "source" -> "override")

    row.metadata shouldBe Map(
      "source" -> "override",
      "job" -> "nightly"
    )
  }

  test("normalizeRows keeps iteration lazy over the input iterable") {
    val normalizer = new CsvNormalizer(CsvNormalizer.catalogSchema(), "partner-feed")
    var pulled = 0
    val rows = new Iterable[Map[String, String]] {
      override def iterator: Iterator[Map[String, String]] = new Iterator[Map[String, String]] {
        private val producers = Vector[() => Map[String, String]](
          () => Map("sku" -> "L-1", "warehouse" -> "east", "qty" -> "1"),
          () => Map("sku" -> "L-2", "warehouse" -> "east", "qty" -> "2")
        ).iterator

        override def hasNext: Boolean = producers.hasNext

        override def next(): Map[String, String] = {
          val row = producers.next()()
          pulled += 1
          row
        }
      }
    }

    val iterator = normalizer.normalizeRows(rows)

    pulled shouldBe 0
    iterator.next().values("quantity") shouldBe Some(IntegerValue(1))
    pulled shouldBe 1
  }
}
