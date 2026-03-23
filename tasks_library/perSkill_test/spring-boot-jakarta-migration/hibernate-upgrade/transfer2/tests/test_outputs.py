from pathlib import Path

WORKSPACE = Path("/workspace")
OUTPUT = Path("/root/transfer2_criteria_migration.txt")
EXPECTED = """service=incident-review
replaced_api=org.hibernate.Criteria
new_api=jakarta.persistence.criteria.CriteriaBuilder
query_method=findOpenCasesByTeam
"""
ENTITY_JAVA = WORKSPACE / "src/main/java/com/example/incidents/model/IncidentCase.java"
REPOSITORY_JAVA = WORKSPACE / "src/main/java/com/example/incidents/repository/IncidentCaseSearchRepositoryImpl.java"
POM_XML = WORKSPACE / "pom.xml"


def main() -> None:
    assert OUTPUT.exists(), f"missing output file: {OUTPUT}"
    assert OUTPUT.read_text() == EXPECTED
    entity = ENTITY_JAVA.read_text()
    assert "jakarta.persistence" in entity
    assert "javax.persistence" not in entity
    repository = REPOSITORY_JAVA.read_text()
    assert "CriteriaBuilder" in repository
    assert "org.hibernate.Criteria" not in repository
    assert "Restrictions" not in repository
    assert "createCriteria" not in repository
    pom = POM_XML.read_text()
    assert "<version>3.2.6</version>" in pom
    assert "<java.version>21</java.version>" in pom
    print("transfer2 verifier checks passed")


if __name__ == "__main__":
    main()
