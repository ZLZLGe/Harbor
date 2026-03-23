import json
from pathlib import Path

WORKSPACE = Path("/workspace")
OUTPUT = Path("/root/transfer1_query_fix.json")
EXPECTED = {
    "service": "warehouse-transfer",
    "updated_query": "select t from TransferOrder t where t.dock.code = :dockCode and t.closed = false order by t.priority desc",
    "touched_files": [
        "src/main/java/com/example/warehouse/model/TransferOrder.java",
        "src/main/java/com/example/warehouse/repository/TransferOrderRepository.java",
    ],
}
ENTITY_JAVA = WORKSPACE / "src/main/java/com/example/warehouse/model/TransferOrder.java"
REPOSITORY_JAVA = WORKSPACE / "src/main/java/com/example/warehouse/repository/TransferOrderRepository.java"
POM_XML = WORKSPACE / "pom.xml"


def main() -> None:
    assert OUTPUT.exists(), f"missing output file: {OUTPUT}"
    assert json.loads(OUTPUT.read_text()) == EXPECTED
    entity = ENTITY_JAVA.read_text()
    assert "jakarta.persistence" in entity
    assert "javax.persistence" not in entity
    repository = REPOSITORY_JAVA.read_text()
    assert "where dock.code" not in repository
    assert "where t.dock.code = :dockCode" in repository
    pom = POM_XML.read_text()
    assert "<version>3.2.6</version>" in pom
    assert "<java.version>21</java.version>" in pom
    print("transfer1 verifier checks passed")


if __name__ == "__main__":
    main()
