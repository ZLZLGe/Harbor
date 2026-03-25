#!/bin/bash
set -euo pipefail

cd /workspace/grpc-gateway

python3 - <<'PY'
import xml.etree.ElementTree as ET
from pathlib import Path

POM_PATH = Path("pom.xml")
NS_URI = "http://maven.apache.org/POM/4.0.0"
NS = {"m": NS_URI}
TAG = f"{{{NS_URI}}}"

ET.register_namespace("", NS_URI)


def qname(tag: str) -> str:
    return f"{TAG}{tag}"


def child(parent: ET.Element, tag: str) -> ET.Element | None:
    return parent.find(qname(tag))


def child_text(parent: ET.Element, tag: str) -> str:
    node = child(parent, tag)
    return (node.text or "").strip() if node is not None and node.text else ""


def ensure_child(parent: ET.Element, tag: str) -> ET.Element:
    node = child(parent, tag)
    if node is None:
        node = ET.SubElement(parent, qname(tag))
    return node


def find_dependency(parent: ET.Element, group_id: str, artifact_id: str) -> ET.Element | None:
    for dep in parent.findall(qname("dependency")):
        if child_text(dep, "groupId") == group_id and child_text(dep, "artifactId") == artifact_id:
            return dep
    return None


def ensure_dependency(parent: ET.Element, group_id: str, artifact_id: str) -> ET.Element:
    dep = find_dependency(parent, group_id, artifact_id)
    if dep is None:
        dep = ET.SubElement(parent, qname("dependency"))
        ET.SubElement(dep, qname("groupId")).text = group_id
        ET.SubElement(dep, qname("artifactId")).text = artifact_id
    return dep


tree = ET.parse(POM_PATH)
root = tree.getroot()

properties = ensure_child(root, "properties")
for name, value in {
    "grpc.version": "1.68.1",
    "protobuf.version": "4.29.0",
}.items():
    prop = child(properties, name)
    if prop is None:
        prop = ET.SubElement(properties, qname(name))
    prop.text = value

dependency_management = child(root, "dependencyManagement")
dependencies = child(root, "dependencies")
if dependency_management is None:
    dependency_management = ET.Element(qname("dependencyManagement"))
    managed_dependencies = ET.SubElement(dependency_management, qname("dependencies"))
    if dependencies is not None:
        insert_at = list(root).index(dependencies)
        root.insert(insert_at, dependency_management)
    else:
        root.append(dependency_management)
else:
    managed_dependencies = ensure_child(dependency_management, "dependencies")

for group_id, artifact_id, version_ref in [
    ("io.grpc", "grpc-bom", "${grpc.version}"),
    ("com.google.protobuf", "protobuf-bom", "${protobuf.version}"),
]:
    dep = ensure_dependency(managed_dependencies, group_id, artifact_id)
    ensure_child(dep, "version").text = version_ref
    ensure_child(dep, "type").text = "pom"
    ensure_child(dep, "scope").text = "import"

runtime_dependencies = ensure_child(root, "dependencies")
for group_id, artifact_id in [
    ("io.grpc", "grpc-netty-shaded"),
    ("io.grpc", "grpc-protobuf"),
    ("io.grpc", "grpc-stub"),
    ("com.google.protobuf", "protobuf-java"),
    ("com.google.protobuf", "protobuf-java-util"),
]:
    dep = ensure_dependency(runtime_dependencies, group_id, artifact_id)
    version = child(dep, "version")
    if version is not None:
        dep.remove(version)

proto_dep = ensure_dependency(
    runtime_dependencies,
    "com.google.api.grpc",
    "proto-google-common-protos",
)
exclusions = ensure_child(proto_dep, "exclusions")
for group_id, artifact_id in [
    ("com.google.protobuf", "protobuf-java"),
    ("com.google.protobuf", "protobuf-java-util"),
]:
    exclusion = None
    for candidate in exclusions.findall(qname("exclusion")):
        if child_text(candidate, "groupId") == group_id and child_text(candidate, "artifactId") == artifact_id:
            exclusion = candidate
            break
    if exclusion is None:
        exclusion = ET.SubElement(exclusions, qname("exclusion"))
        ET.SubElement(exclusion, qname("groupId")).text = group_id
        ET.SubElement(exclusion, qname("artifactId")).text = artifact_id

ET.indent(tree, space="    ")
tree.write(POM_PATH, encoding="utf-8", xml_declaration=False)
PY
