import json
import subprocess
from pathlib import Path

WORKSPACE = Path("/workspace")
OUTPUT = Path("/root/similar_namespace_report.json")
EXPECTED = {
    "service": "user-roster",
    "migrated_files": [
        "src/main/java/com/example/roster/controller/UserRosterController.java",
        "src/main/java/com/example/roster/dto/UserSignupRequest.java",
        "src/main/java/com/example/roster/filter/CorrelationIdFilter.java",
        "src/main/java/com/example/roster/model/RosterUser.java",
    ],
    "packages_fixed": [
        "javax.persistence",
        "javax.servlet",
        "javax.validation",
    ],
    "remaining_javax_imports": 0,
}


def main() -> None:
    assert OUTPUT.exists(), f"missing output file: {OUTPUT}"
    assert json.loads(OUTPUT.read_text()) == EXPECTED
    for java_file in (WORKSPACE / "src").rglob("*.java"):
        assert "import javax." not in java_file.read_text(), java_file
    roster_user = (WORKSPACE / "src/main/java/com/example/roster/model/RosterUser.java").read_text()
    assert "jakarta.persistence" in roster_user
    assert "jakarta.validation" in roster_user
    filter_java = (WORKSPACE / "src/main/java/com/example/roster/filter/CorrelationIdFilter.java").read_text()
    assert "jakarta.servlet" in filter_java
    result = subprocess.run(["bash", "/workspace/verify.sh"], cwd=WORKSPACE, capture_output=True, text=True, timeout=600)
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    print("similar verifier checks passed")


if __name__ == "__main__":
    main()
