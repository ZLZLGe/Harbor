import hashlib
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


PROJECT_DIR = Path("/workspace/release-portal")
DOCS_DIR = PROJECT_DIR / "docs"
POM_PATH = DOCS_DIR / "pom.xml"
JAVADOC_JAR = DOCS_DIR / "target" / "release-docs-1.0.0-SNAPSHOT-javadoc.jar"
NS = {"m": "http://maven.apache.org/POM/4.0.0"}

EXPECTED_HASHES = {
    "docs/src/main/java/com/acme/release/docs/ReleaseChannelGuide.java": "6f8a38bb63ed5a1c3ac936c4f867ab4990f70eb9e97091546e38c0327f007d00",
    "docs/src/main/java/com/acme/release/docs/ReleaseChecklist.java": "993afa640955132c1dd097f895a4c398e0b3842067ab393683f5b44c21a40eb7",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get_text(node, xpath: str):
    found = node.find(xpath, NS)
    return None if found is None or found.text is None else found.text.strip()


def parse_javadoc_plugin():
    tree = ET.parse(POM_PATH)
    plugin = tree.find(
        "./m:build/m:plugins/m:plugin[m:artifactId='maven-javadoc-plugin']",
        NS,
    )
    assert plugin is not None, "maven-javadoc-plugin is missing"
    return plugin


def assert_sources_unchanged() -> None:
    for relative_path, expected_hash in EXPECTED_HASHES.items():
        file_path = PROJECT_DIR / relative_path
        assert file_path.exists(), f"missing source file: {relative_path}"
        assert sha256(file_path) == expected_hash, f"{relative_path} was modified"


def test_pom_configuration() -> None:
    plugin = parse_javadoc_plugin()

    source = get_text(plugin, "./m:configuration/m:source")
    doclint = get_text(plugin, "./m:configuration/m:doclint")
    goal = get_text(plugin, "./m:executions/m:execution/m:goals/m:goal")

    assert source in {"17", "${maven.compiler.release}"}, "javadoc source must target the current JDK level"
    assert doclint == "none", "doclint must be disabled for this release docs build"
    assert goal == "jar", "javadoc execution must attach a jar artifact"


def test_package_build_and_javadoc_jar() -> None:
    assert_sources_unchanged()

    result = subprocess.run(
        ["mvn", "-q", "-pl", "docs", "-am", "package"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"mvn -pl docs -am package failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    assert JAVADOC_JAR.exists(), "javadoc jar was not produced"

    with zipfile.ZipFile(JAVADOC_JAR) as jar:
        names = set(jar.namelist())
        guide_page = jar.read("com/acme/release/docs/ReleaseChannelGuide.html").decode("utf-8")

    assert "com/acme/release/docs/ReleaseChannelGuide.html" in names
    assert "com/acme/release/docs/ReleaseChecklist.html" in names
    assert "ReleaseChannelGuide" in guide_page
    assert "version" in guide_page
    assert "channel" in guide_page


if __name__ == "__main__":
    test_pom_configuration()
    test_package_build_and_javadoc_jar()
