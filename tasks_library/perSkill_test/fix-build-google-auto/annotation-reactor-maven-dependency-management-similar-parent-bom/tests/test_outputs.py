from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


REPO_ROOT = Path("/workspace/annotation-parent")
PARENT_POM = REPO_ROOT / "pom.xml"
NS = {"m": "http://maven.apache.org/POM/4.0.0"}
REQUIRED_MANAGED = {
    ("com.google.guava", "guava"),
    ("com.google.auto", "auto-common"),
    ("com.google.auto.service", "auto-service"),
    ("com.google.auto.service", "auto-service-annotations"),
}


def parse_xml(path: Path) -> ET.Element:
    return ET.parse(path).getroot()


def dependency_map(root: ET.Element, query: str) -> dict[tuple[str, str], ET.Element]:
    result = {}
    for dep in root.findall(query, NS):
        group_id = dep.findtext("m:groupId", default="", namespaces=NS)
        artifact_id = dep.findtext("m:artifactId", default="", namespaces=NS)
        result[(group_id, artifact_id)] = dep
    return result


def test_parent_pom_exists():
    assert PARENT_POM.exists(), f"missing {PARENT_POM}"


def test_parent_dependency_management_centralizes_target_versions():
    root = parse_xml(PARENT_POM)
    managed = dependency_map(root, "./m:dependencyManagement/m:dependencies/m:dependency")

    for coords in REQUIRED_MANAGED:
        assert coords in managed, f"{coords[0]}:{coords[1]} is not managed in the parent POM"
        version = managed[coords].findtext("m:version", default="", namespaces=NS)
        assert version.strip(), f"{coords[0]}:{coords[1]} should declare a managed version in the parent POM"


def test_child_modules_do_not_repeat_managed_versions():
    modules = ["processor-api", "processor-core", "processor-tests"]

    for module in modules:
        pom_path = REPO_ROOT / module / "pom.xml"
        root = parse_xml(pom_path)
        deps = dependency_map(root, "./m:dependencies/m:dependency")
        for coords in REQUIRED_MANAGED:
            dep = deps.get(coords)
            if dep is None:
                continue
            assert dep.find("m:version", NS) is None, (
                f"{module}/pom.xml should inherit the version for {coords[0]}:{coords[1]} from the parent POM"
            )


def test_reactor_build_and_unit_tests_pass():
    result = subprocess.run(
        ["mvn", "--batch-mode", "test"],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=240,
    )
    if result.returncode != 0:
        print(result.stdout)
    assert result.returncode == 0, "mvn test did not pass"
