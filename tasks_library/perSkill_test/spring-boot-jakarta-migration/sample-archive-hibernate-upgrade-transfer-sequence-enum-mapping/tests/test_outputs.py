import os
import subprocess

WORKSPACE_DIR = "/workspace"
ENTITY_FILE = os.path.join(
    WORKSPACE_DIR,
    "src/main/java/com/acme/archive/model/SampleRecord.java",
)
TEST_PROPERTIES = os.path.join(
    WORKSPACE_DIR,
    "src/test/resources/application.properties",
)


def run(command):
    return subprocess.run(
        command,
        cwd=WORKSPACE_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )


class TestEntityMigration:
    def test_entity_file_exists(self):
        assert os.path.exists(ENTITY_FILE), "SampleRecord.java not found"

    def test_sequence_generator_uses_standard_jpa_annotations(self):
        with open(ENTITY_FILE, encoding="utf-8") as handle:
            content = handle.read()

        assert "@SequenceGenerator" in content
        assert "allocationSize = 1" in content
        assert "@GenericGenerator" not in content
        assert "increment_size" not in content

    def test_enum_and_time_fields_use_hibernate6_friendly_mapping(self):
        with open(ENTITY_FILE, encoding="utf-8") as handle:
            content = handle.read()

        assert content.count("@Enumerated(EnumType.STRING)") >= 2
        assert "@Type(type =" not in content
        assert "OffsetDateTime archivedAt" in content
        assert "OffsetDateTime replayedAt" in content


class TestDialectMigration:
    def test_outdated_dialect_removed_from_test_properties(self):
        assert os.path.exists(TEST_PROPERTIES), "application.properties not found"

        with open(TEST_PROPERTIES, encoding="utf-8") as handle:
            content = handle.read()

        assert "PostgreSQL95Dialect" not in content


class TestBuildAndBehavior:
    def test_compile(self):
        result = run(["mvn", "-q", "-DskipTests", "compile"])
        assert result.returncode == 0, result.stdout + "\n" + result.stderr

    def test_repository_behavior(self):
        result = run(["mvn", "-q", "-Dtest=SampleRecordRepositoryTest", "test"])
        assert result.returncode == 0, result.stdout + "\n" + result.stderr
