#!/bin/bash
set -euo pipefail

PROJECT_DIR=/workspace/reactor-release-console

python3 <<'PY'
from pathlib import Path
import xml.etree.ElementTree as ET

PROJECT_DIR = Path("/workspace/reactor-release-console")
POM_NS = "http://maven.apache.org/POM/4.0.0"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

ET.register_namespace("", POM_NS)
ET.register_namespace("xsi", XSI_NS)


def qname(tag: str) -> str:
    return f"{{{POM_NS}}}{tag}"


def load_xml(path: Path):
    tree = ET.parse(path)
    return tree, tree.getroot()


def find_required(parent: ET.Element, path: str) -> ET.Element:
    node = parent.find(path)
    if node is None:
        raise RuntimeError(f"missing required XML path: {path}")
    return node


def ensure_child(parent: ET.Element, tag: str) -> ET.Element:
    child = parent.find(qname(tag))
    if child is None:
        child = ET.SubElement(parent, qname(tag))
    return child


def clear_children(parent: ET.Element) -> None:
    for child in list(parent):
        parent.remove(child)


root_pom = PROJECT_DIR / "pom.xml"
tree, root = load_xml(root_pom)

modules = find_required(root, qname("modules"))
clear_children(modules)
for module_name in ("shared-lib", "service-layer", "cli-app"):
    module = ET.SubElement(modules, qname("module"))
    module.text = module_name

dependencies = find_required(
    root,
    f"{qname('dependencyManagement')}/{qname('dependencies')}",
)
clear_children(dependencies)
for artifact_id in ("shared-lib", "service-layer", "cli-app"):
    dependency = ET.SubElement(dependencies, qname("dependency"))
    ensure_child(dependency, "groupId").text = "com.acme.reactor"
    ensure_child(dependency, "artifactId").text = artifact_id
    ensure_child(dependency, "version").text = "${project.version}"

ET.indent(tree, space="    ")
tree.write(root_pom, encoding="utf-8", xml_declaration=False)

cli_pom = PROJECT_DIR / "cli-app" / "pom.xml"
tree, root = load_xml(cli_pom)
phase = find_required(
    root,
    f"{qname('build')}/{qname('plugins')}/{qname('plugin')}/{qname('executions')}/{qname('execution')}/{qname('phase')}",
)
phase.text = "package"

ET.indent(tree, space="    ")
tree.write(cli_pom, encoding="utf-8", xml_declaration=False)
PY

cd "$PROJECT_DIR"
mvn verify
