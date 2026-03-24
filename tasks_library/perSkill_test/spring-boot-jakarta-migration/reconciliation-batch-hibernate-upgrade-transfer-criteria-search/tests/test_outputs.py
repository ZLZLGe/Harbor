import os
import subprocess

WORKSPACE_DIR = "/workspace"
REPOSITORY_FILE = os.path.join(
    WORKSPACE_DIR,
    "src/main/java/com/acme/reconcile/persistence/ReconciliationSearchRepository.java",
)


def run(command):
    return subprocess.run(
        command,
        cwd=WORKSPACE_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )


class TestRepositoryMigration:
    def test_repository_file_exists(self):
        assert os.path.exists(REPOSITORY_FILE), "ReconciliationSearchRepository.java not found"

    def test_legacy_hibernate_criteria_api_removed(self):
        with open(REPOSITORY_FILE, encoding="utf-8") as handle:
            content = handle.read()

        assert "org.hibernate.Criteria" not in content
        assert "Restrictions." not in content
        assert "createCriteria(" not in content

    def test_jpa_criteria_api_is_used(self):
        with open(REPOSITORY_FILE, encoding="utf-8") as handle:
            content = handle.read()

        assert "CriteriaBuilder" in content
        assert "CriteriaQuery" in content
        assert "Subquery" in content


class TestBuildAndBehavior:
    def test_compile(self):
        result = run(["mvn", "-q", "-DskipTests", "compile"])
        assert result.returncode == 0, result.stdout + "\n" + result.stderr

    def test_repository_tests(self):
        result = run(["mvn", "-q", "test"])
        assert result.returncode == 0, result.stdout + "\n" + result.stderr
