from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


REPO_ROOT = Path("/workspace/platform-bom")
POM_PATH = REPO_ROOT / "pom.xml"
NS = {"m": "http://maven.apache.org/POM/4.0.0"}
MANAGED_COORDS = {
    ("junit", "junit"),
    ("org.slf4j", "slf4j-api"),
    ("ch.qos.logback", "logback-classic"),
}
JACKSON_COORDS = {
    ("com.fasterxml.jackson.core", "jackson-databind"),
    ("com.fasterxml.jackson.core", "jackson-annotations"),
}


def parse_xml(path: Path) -> ET.Element:
    return ET.parse(path).getroot()


def dependency_map(root: ET.Element, query: str) -> dict[tuple[str, str], ET.Element]:
    dependencies = {}
    for dep in root.findall(query, NS):
        group_id = dep.findtext("m:groupId", default="", namespaces=NS)
        artifact_id = dep.findtext("m:artifactId", default="", namespaces=NS)
        dependencies[(group_id, artifact_id)] = dep
    return dependencies


def test_root_bom_uses_dependency_management():
    root = parse_xml(POM_PATH)
    managed = dependency_map(root, "./m:dependencyManagement/m:dependencies/m:dependency")

    jackson_bom = managed.get(("com.fasterxml.jackson", "jackson-bom"))
    if jackson_bom is not None:
        assert jackson_bom.findtext("m:type", default="", namespaces=NS) == "pom"
        assert jackson_bom.findtext("m:scope", default="", namespaces=NS) == "import"
        assert jackson_bom.findtext("m:version", default="", namespaces=NS).strip()
    else:
        missing = []
        for coords in JACKSON_COORDS:
            dep = managed.get(coords)
            if dep is None or not dep.findtext("m:version", default="", namespaces=NS).strip():
                missing.append(f"{coords[0]}:{coords[1]}")
        assert not missing, (
            "root POM should manage Jackson versions in dependencyManagement, "
            "either by importing com.fasterxml.jackson:jackson-bom or by explicitly "
            f"managing the downstream Jackson artifacts. Missing: {missing}"
        )

    for coords in MANAGED_COORDS:
        dep = managed.get(coords)
        assert dep is not None, f"{coords[0]}:{coords[1]} should be managed in the root POM"
        assert dep.findtext("m:version", default="", namespaces=NS).strip()


def test_root_pom_no_longer_declares_shared_libraries_as_regular_dependencies():
    root = parse_xml(POM_PATH)
    regular = dependency_map(root, "./m:dependencies/m:dependency")

    forbidden = set(MANAGED_COORDS)
    forbidden.add(("com.fasterxml.jackson", "jackson-bom"))
    forbidden.update(JACKSON_COORDS)
    overlap = sorted(forbidden.intersection(regular))
    assert not overlap, f"root POM should not keep shared libraries as regular dependencies: {overlap}"


def test_downstream_modules_keep_versionless_dependencies():
    module_specs = {
        "event-service": {
            ("com.fasterxml.jackson.core", "jackson-databind"),
            ("org.slf4j", "slf4j-api"),
            ("ch.qos.logback", "logback-classic"),
            ("junit", "junit"),
        },
        "ops-cli": {
            ("com.fasterxml.jackson.core", "jackson-databind"),
            ("com.fasterxml.jackson.core", "jackson-annotations"),
            ("org.slf4j", "slf4j-api"),
            ("ch.qos.logback", "logback-classic"),
            ("junit", "junit"),
        },
    }

    for module, expected in module_specs.items():
        pom = parse_xml(REPO_ROOT / module / "pom.xml")
        deps = dependency_map(pom, "./m:dependencies/m:dependency")
        for coords in expected:
            dep = deps.get(coords)
            assert dep is not None, f"{module} should depend on {coords[0]}:{coords[1]}"
            assert dep.find("m:version", NS) is None, (
                f"{module} should keep {coords[0]}:{coords[1]} without an explicit version"
            )


def test_downstream_modules_still_use_inherit_or_import_paths():
    event_service = parse_xml(REPO_ROOT / "event-service" / "pom.xml")
    parent = event_service.find("m:parent", NS)
    assert parent is not None, "event-service should inherit from the root POM"
    assert parent.findtext("m:artifactId", default="", namespaces=NS) == "platform-bom"

    ops_cli = parse_xml(REPO_ROOT / "ops-cli" / "pom.xml")
    imports = dependency_map(ops_cli, "./m:dependencyManagement/m:dependencies/m:dependency")
    imported_bom = imports.get(("com.acme.platform", "platform-bom"))
    assert imported_bom is not None, "ops-cli should keep importing the root BOM"
    assert imported_bom.findtext("m:type", default="", namespaces=NS) == "pom"
    assert imported_bom.findtext("m:scope", default="", namespaces=NS) == "import"


def test_reactor_tests_pass():
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
    assert result.returncode == 0, "mvn test should succeed for the platform-bom reactor"
