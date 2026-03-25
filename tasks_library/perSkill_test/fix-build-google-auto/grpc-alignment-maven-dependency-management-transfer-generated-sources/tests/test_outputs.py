from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


REPO_ROOT = Path("/workspace/grpc-gateway")
POM_PATH = REPO_ROOT / "pom.xml"
NS = {"m": "http://maven.apache.org/POM/4.0.0"}
EXPECTED_COORDS = {
    "groupId": "com.acme.gateway",
    "artifactId": "grpc-gateway",
    "version": "1.0.0-SNAPSHOT",
}

GRPC_COORDS = {
    ("io.grpc", "grpc-netty-shaded"),
    ("io.grpc", "grpc-protobuf"),
    ("io.grpc", "grpc-stub"),
}
PROTOBUF_COORDS = {
    ("com.google.protobuf", "protobuf-java"),
    ("com.google.protobuf", "protobuf-java-util"),
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


def test_pom_exists():
    assert POM_PATH.exists(), f"missing {POM_PATH}"


def test_project_coordinates_remain_unchanged():
    root = parse_xml(POM_PATH)

    for tag, expected in EXPECTED_COORDS.items():
        actual = root.findtext(f"m:{tag}", default="", namespaces=NS).strip()
        assert actual == expected, f"project {tag} should remain {expected}, got {actual!r}"


def test_dependency_management_centralizes_grpc_and_protobuf_versions():
    root = parse_xml(POM_PATH)
    managed = dependency_map(root, "./m:dependencyManagement/m:dependencies/m:dependency")

    grpc_bom = managed.get(("io.grpc", "grpc-bom"))
    assert grpc_bom is not None or GRPC_COORDS.issubset(managed), (
        "gRPC versions should be managed centrally via grpc-bom or explicit dependencyManagement entries"
    )
    if grpc_bom is not None:
        assert grpc_bom.findtext("m:type", default="", namespaces=NS) == "pom"
        assert grpc_bom.findtext("m:scope", default="", namespaces=NS) == "import"
        assert grpc_bom.findtext("m:version", default="", namespaces=NS).strip()

    protobuf_bom = managed.get(("com.google.protobuf", "protobuf-bom"))
    assert protobuf_bom is not None or PROTOBUF_COORDS.issubset(managed), (
        "protobuf versions should be managed centrally via protobuf-bom or explicit dependencyManagement entries"
    )
    if protobuf_bom is not None:
        assert protobuf_bom.findtext("m:type", default="", namespaces=NS) == "pom"
        assert protobuf_bom.findtext("m:scope", default="", namespaces=NS) == "import"
        assert protobuf_bom.findtext("m:version", default="", namespaces=NS).strip()

    for coords in managed:
        if coords in GRPC_COORDS or coords in PROTOBUF_COORDS:
            version = managed[coords].findtext("m:version", default="", namespaces=NS)
            assert version.strip(), f"{coords[0]}:{coords[1]} needs a managed version"


def test_runtime_dependencies_drop_explicit_versions():
    root = parse_xml(POM_PATH)
    declared = dependency_map(root, "./m:dependencies/m:dependency")

    for coords in GRPC_COORDS | PROTOBUF_COORDS:
        dep = declared.get(coords)
        assert dep is not None, f"missing dependency {coords[0]}:{coords[1]}"
        assert dep.find("m:version", NS) is None, (
            f"{coords[0]}:{coords[1]} should inherit its version from centralized management"
        )


def test_proto_common_protos_excludes_conflicting_protobuf_runtime():
    root = parse_xml(POM_PATH)
    declared = dependency_map(root, "./m:dependencies/m:dependency")

    dep = declared.get(("com.google.api.grpc", "proto-google-common-protos"))
    assert dep is not None, "proto-google-common-protos must remain as a dependency"

    exclusions = {
        (
            exclusion.findtext("m:groupId", default="", namespaces=NS),
            exclusion.findtext("m:artifactId", default="", namespaces=NS),
        )
        for exclusion in dep.findall("./m:exclusions/m:exclusion", NS)
    }
    assert ("com.google.protobuf", "protobuf-java") in exclusions
    assert ("com.google.protobuf", "protobuf-java-util") in exclusions


def test_smoke_tests_pass():
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
    assert result.returncode == 0, "mvn test should succeed for grpc-gateway"
