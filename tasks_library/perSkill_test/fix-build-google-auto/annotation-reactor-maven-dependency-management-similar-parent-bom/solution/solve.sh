#!/bin/bash
set -euo pipefail

cd /workspace/annotation-parent

python3 <<'PY'
from pathlib import Path
import xml.etree.ElementTree as ET

NS = {"m": "http://maven.apache.org/POM/4.0.0"}
ET.register_namespace("", NS["m"])

repo = Path("/workspace/annotation-parent")
parent_path = repo / "pom.xml"
managed = [
    ("com.google.guava", "guava", "${guava.version}"),
    ("com.google.auto", "auto-common", "${auto.common.version}"),
    ("com.google.auto.service", "auto-service", "${auto.service.version}"),
    ("com.google.auto.service", "auto-service-annotations", "${auto.service.version}"),
]
targets = {(group_id, artifact_id) for group_id, artifact_id, _ in managed}


def child(parent, tag):
    node = parent.find(f"m:{tag}", NS)
    if node is None:
        node = ET.SubElement(parent, f"{{{NS['m']}}}{tag}")
    return node


parent_tree = ET.parse(parent_path)
parent_root = parent_tree.getroot()

dep_mgmt = child(parent_root, "dependencyManagement")
deps = child(dep_mgmt, "dependencies")
deps[:] = []

for group_id, artifact_id, version in managed:
    dep = ET.SubElement(deps, f"{{{NS['m']}}}dependency")
    ET.SubElement(dep, f"{{{NS['m']}}}groupId").text = group_id
    ET.SubElement(dep, f"{{{NS['m']}}}artifactId").text = artifact_id
    ET.SubElement(dep, f"{{{NS['m']}}}version").text = version

parent_tree.write(parent_path, encoding="utf-8", xml_declaration=False)

for pom_path in repo.glob("*/pom.xml"):
    tree = ET.parse(pom_path)
    root = tree.getroot()
    changed = False
    for dep in root.findall(".//m:dependencies/m:dependency", NS):
        group_id = dep.findtext("m:groupId", default="", namespaces=NS)
        artifact_id = dep.findtext("m:artifactId", default="", namespaces=NS)
        if (group_id, artifact_id) in targets:
            version = dep.find("m:version", NS)
            if version is not None:
                dep.remove(version)
                changed = True
    if changed:
        tree.write(pom_path, encoding="utf-8", xml_declaration=False)
PY

mvn --batch-mode test
