#!/bin/bash
set -euo pipefail

cd /workspace/web-portal

python3 <<'PY'
from pathlib import Path
import xml.etree.ElementTree as ET

NS = {"m": "http://maven.apache.org/POM/4.0.0"}
ET.register_namespace("", NS["m"])

pom_path = Path("/workspace/web-portal/pom.xml")
tree = ET.parse(pom_path)
root = tree.getroot()


def find_dependency(group_id: str, artifact_id: str):
    for dependency in root.findall("./m:dependencies/m:dependency", NS):
        current_group = dependency.findtext("m:groupId", default="", namespaces=NS)
        current_artifact = dependency.findtext("m:artifactId", default="", namespaces=NS)
        if (current_group, current_artifact) == (group_id, artifact_id):
            return dependency
    raise RuntimeError(f"dependency not found: {group_id}:{artifact_id}")


def child(parent, tag: str):
    node = parent.find(f"m:{tag}", NS)
    if node is None:
        node = ET.SubElement(parent, f"{{{NS['m']}}}{tag}")
    return node


servlet_api = find_dependency("jakarta.servlet", "jakarta.servlet-api")
scope = child(servlet_api, "scope")
scope.text = "provided"

portal_bootstrap = find_dependency("com.acme.portal", "portal-bootstrap")
exclusions = child(portal_bootstrap, "exclusions")
exclusions[:] = []

for group_id, artifact_id in [
    ("org.eclipse.jetty", "jetty-server"),
    ("org.eclipse.jetty", "jetty-servlet"),
]:
    exclusion = ET.SubElement(exclusions, f"{{{NS['m']}}}exclusion")
    ET.SubElement(exclusion, f"{{{NS['m']}}}groupId").text = group_id
    ET.SubElement(exclusion, f"{{{NS['m']}}}artifactId").text = artifact_id

if hasattr(ET, "indent"):
    ET.indent(tree, space="  ")

tree.write(pom_path, encoding="utf-8", xml_declaration=True)
PY

mvn --batch-mode package
