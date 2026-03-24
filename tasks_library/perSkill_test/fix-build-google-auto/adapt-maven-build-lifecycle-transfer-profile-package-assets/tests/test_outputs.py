from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile


WORKSPACE = Path("/workspace")
POM_PATH = WORKSPACE / "app" / "pom.xml"
JAR_PATH = WORKSPACE / "app" / "target" / "release-notifier-1.0.0.jar"
NS = {"m": "http://maven.apache.org/POM/4.0.0"}


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def get_profile(root: ET.Element, profile_id: str) -> ET.Element | None:
    for profile in root.findall("./m:profiles/m:profile", NS):
        if profile.findtext("m:id", default="", namespaces=NS).strip() == profile_id:
            return profile
    return None


def assert_profile_phase_fixed() -> None:
    if not POM_PATH.exists():
        fail(f"missing pom.xml at {POM_PATH}")

    root = ET.parse(POM_PATH).getroot()
    profile = get_profile(root, "production")
    if profile is None:
        fail("missing production profile in app/pom.xml")

    for plugin in profile.findall("./m:build/m:plugins/m:plugin", NS):
        artifact_id = plugin.findtext("m:artifactId", default="", namespaces=NS)
        group_id = plugin.findtext("m:groupId", default="org.apache.maven.plugins", namespaces=NS)
        if group_id != "org.apache.maven.plugins" or artifact_id != "maven-resources-plugin":
            continue

        for execution in plugin.findall("./m:executions/m:execution", NS):
            execution_id = execution.findtext("m:id", default="", namespaces=NS).strip()
            if execution_id != "stage-production-assets":
                continue

            phase = execution.findtext("m:phase", default="", namespaces=NS).strip()
            if phase != "process-resources":
                fail("stage-production-assets must be bound to process-resources")
            return

    fail("missing stage-production-assets execution in production profile")


def run_package() -> None:
    result = subprocess.run(
        ["mvn", "-q", "-B", "-f", "app/pom.xml", "-Pproduction", "package"],
        cwd=WORKSPACE,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        fail("mvn -f app/pom.xml -Pproduction package did not succeed")


def assert_jar_contains_profile_asset() -> None:
    if not JAR_PATH.exists():
        fail(f"expected jar at {JAR_PATH}")

    with zipfile.ZipFile(JAR_PATH) as jar:
        try:
            content = jar.read("release-config/release.properties").decode()
        except KeyError as exc:
            fail("release-config/release.properties was not packaged into the production jar")
            raise AssertionError from exc

    expected_markers = [
        "release.channel=production",
        "release.endpoint=https://notify.harbor.internal/prod",
        "audit.enabled=true",
    ]
    for marker in expected_markers:
        if marker not in content:
            fail(f"packaged release.properties is missing expected marker {marker!r}")


def main() -> None:
    assert_profile_phase_fixed()
    run_package()
    assert_jar_contains_profile_asset()


if __name__ == "__main__":
    main()
