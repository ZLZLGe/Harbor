#!/bin/bash
set -euo pipefail

cd /workspace/platform-bom

python3 <<'PY'
from pathlib import Path
import xml.etree.ElementTree as ET

NS = {"m": "http://maven.apache.org/POM/4.0.0"}
ET.register_namespace("", NS["m"])

pom_path = Path("/workspace/platform-bom/pom.xml")
tree = ET.parse(pom_path)
root = tree.getroot()

managed_entries = [
    ("com.fasterxml.jackson", "jackson-bom", "${jackson.version}", "pom", "import"),
    ("junit", "junit", "${junit.version}", None, None),
    ("org.slf4j", "slf4j-api", "${slf4j.version}", None, None),
    ("ch.qos.logback", "logback-classic", "${logback.version}", None, None),
]
managed_coords = {(group_id, artifact_id) for group_id, artifact_id, *_ in managed_entries}


def child(parent, tag):
    node = parent.find(f"m:{tag}", NS)
    if node is None:
        node = ET.SubElement(parent, f"{{{NS['m']}}}{tag}")
    return node


dependencies = root.find("m:dependencies", NS)
if dependencies is not None:
    kept = []
    for dep in list(dependencies):
        coords = (
            dep.findtext("m:groupId", default="", namespaces=NS),
            dep.findtext("m:artifactId", default="", namespaces=NS),
        )
        if coords not in managed_coords:
            kept.append(dep)
    dependencies[:] = kept
    if not kept:
        root.remove(dependencies)

dependency_management = child(root, "dependencyManagement")
managed_dependencies = child(dependency_management, "dependencies")
managed_dependencies[:] = []

for group_id, artifact_id, version, dep_type, scope in managed_entries:
    dep = ET.SubElement(managed_dependencies, f"{{{NS['m']}}}dependency")
    ET.SubElement(dep, f"{{{NS['m']}}}groupId").text = group_id
    ET.SubElement(dep, f"{{{NS['m']}}}artifactId").text = artifact_id
    ET.SubElement(dep, f"{{{NS['m']}}}version").text = version
    if dep_type is not None:
        ET.SubElement(dep, f"{{{NS['m']}}}type").text = dep_type
    if scope is not None:
        ET.SubElement(dep, f"{{{NS['m']}}}scope").text = scope

if hasattr(ET, "indent"):
    ET.indent(tree, space="  ")

tree.write(pom_path, encoding="utf-8", xml_declaration=True)
PY

mvn --batch-mode test
