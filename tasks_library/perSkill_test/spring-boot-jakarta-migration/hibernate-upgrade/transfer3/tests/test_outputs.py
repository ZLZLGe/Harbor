from pathlib import Path

WORKSPACE = Path("/workspace")
OUTPUT = Path("/root/transfer3_metadata_mapping_report.md")
EXPECTED = """# Vendor Metadata Mapping Migration
- service: vendor-onboarding
- removed_annotations: @TypeDef, @Type
- replacement: @JdbcTypeCode(SqlTypes.JSON)
- touched_file: src/main/java/com/example/vendor/model/VendorProfile.java
"""
MODEL_JAVA = WORKSPACE / "src/main/java/com/example/vendor/model/VendorProfile.java"
POM_XML = WORKSPACE / "pom.xml"


def main() -> None:
    assert OUTPUT.exists(), f"missing output file: {OUTPUT}"
    assert OUTPUT.read_text().strip() == EXPECTED.strip()
    model = MODEL_JAVA.read_text()
    assert "jakarta.persistence" in model
    assert "@JdbcTypeCode(SqlTypes.JSON)" in model
    assert "@TypeDef" not in model
    assert "@Type(" not in model
    assert "javax.persistence" not in model
    pom = POM_XML.read_text()
    assert "<version>3.2.6</version>" in pom
    assert "<java.version>21</java.version>" in pom
    print("transfer3 verifier checks passed")


if __name__ == "__main__":
    main()
