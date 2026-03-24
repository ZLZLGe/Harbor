import os
import subprocess

WORKSPACE_DIR = "/workspace"
ENTITY_FILE = os.path.join(
    WORKSPACE_DIR,
    "src/main/java/com/acme/logistics/model/ShipmentEvent.java",
)


def run(command):
    return subprocess.run(
        command,
        cwd=WORKSPACE_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )


class TestJsonMappingMigration:
    def test_entity_file_exists(self):
        assert os.path.exists(ENTITY_FILE), "ShipmentEvent.java not found"

    def test_legacy_json_type_declarations_removed(self):
        with open(ENTITY_FILE, encoding="utf-8") as handle:
            content = handle.read()

        assert "@TypeDef" not in content
        assert "@Type(type = \"jsonb\")" not in content
        assert "JsonBinaryType" not in content
        assert "columnDefinition = \"jsonb\"" not in content

    def test_hibernate6_json_mapping_is_present(self):
        with open(ENTITY_FILE, encoding="utf-8") as handle:
            content = handle.read()

        assert "@JdbcTypeCode(SqlTypes.JSON)" in content
        assert "import org.hibernate.annotations.JdbcTypeCode;" in content
        assert "import org.hibernate.type.SqlTypes;" in content


class TestBuildAndBehavior:
    def test_compile(self):
        result = run(["mvn", "-q", "-DskipTests", "compile"])
        assert result.returncode == 0, result.stdout + "\n" + result.stderr

    def test_repository_json_mapping_behavior(self):
        result = run(["mvn", "-q", "-Dtest=ShipmentEventRepositoryTest", "test"])
        assert result.returncode == 0, result.stdout + "\n" + result.stderr
