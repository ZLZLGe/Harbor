from functools import lru_cache
from pathlib import Path
import subprocess
import zipfile


PROJECT_DIR = Path("/workspace/release-bulletin-service")
OUTPUT_FILE = PROJECT_DIR / "target/classes/release/build-info.properties"
JAR_FILE = PROJECT_DIR / "target/release-bulletin-service-2.7.4.jar"
EXPECTED_VALUES = {
    "app.name": "release-bulletin-service",
    "app.version": "2.7.4",
    "deployment.environment": "release",
    "release.channel": "stable",
    "release.badge": "release-2.7.4",
}


def parse_properties(content: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


@lru_cache(maxsize=1)
def run_release_package():
    result = subprocess.run(
        ["mvn", "-Prelease", "package"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
    return result


def test_release_package_succeeds():
    result = run_release_package()
    assert result.returncode == 0, "expected `mvn -Prelease package` to succeed"


def test_filtered_build_info_written_to_target_classes():
    result = run_release_package()
    assert result.returncode == 0, "build must succeed before checking release metadata"
    assert OUTPUT_FILE.exists(), f"missing output file: {OUTPUT_FILE}"

    content = OUTPUT_FILE.read_text()
    values = parse_properties(content)

    for key, expected in EXPECTED_VALUES.items():
        assert values.get(key) == expected, f"expected {key}={expected!r}, got {values.get(key)!r}"

    assert "${" not in content, "unresolved placeholders remain in build-info.properties"


def test_packaged_jar_contains_same_release_metadata():
    result = run_release_package()
    assert result.returncode == 0, "build must succeed before checking packaged jar"
    assert JAR_FILE.exists(), f"missing jar file: {JAR_FILE}"

    disk_content = OUTPUT_FILE.read_text().strip()
    with zipfile.ZipFile(JAR_FILE) as jar_file:
        jar_content = jar_file.read("release/build-info.properties").decode().strip()

    assert jar_content == disk_content, "jar should contain the same filtered release metadata file"
