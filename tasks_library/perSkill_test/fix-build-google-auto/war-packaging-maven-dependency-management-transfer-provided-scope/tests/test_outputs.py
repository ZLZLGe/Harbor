from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
import zipfile


REPO_ROOT = Path("/workspace/web-portal")
POM_PATH = REPO_ROOT / "pom.xml"
WAR_PATH = REPO_ROOT / "target" / "web-portal.war"
NS = {"m": "http://maven.apache.org/POM/4.0.0"}


def parse_pom() -> ET.Element:
    return ET.parse(POM_PATH).getroot()


def find_dependency(root: ET.Element, group_id: str, artifact_id: str) -> ET.Element:
    for dependency in root.findall("./m:dependencies/m:dependency", NS):
        current_group = dependency.findtext("m:groupId", default="", namespaces=NS)
        current_artifact = dependency.findtext("m:artifactId", default="", namespaces=NS)
        if (current_group, current_artifact) == (group_id, artifact_id):
            return dependency
    raise AssertionError(f"missing dependency {group_id}:{artifact_id}")


def test_servlet_api_uses_provided_scope():
    root = parse_pom()
    dependency = find_dependency(root, "jakarta.servlet", "jakarta.servlet-api")
    scope = dependency.findtext("m:scope", default="", namespaces=NS)
    assert scope == "provided", "jakarta.servlet-api should use provided scope"


def test_portal_bootstrap_excludes_jetty_dependencies():
    root = parse_pom()
    dependency = find_dependency(root, "com.acme.portal", "portal-bootstrap")
    exclusions = {
        (
            exclusion.findtext("m:groupId", default="", namespaces=NS),
            exclusion.findtext("m:artifactId", default="", namespaces=NS),
        )
        for exclusion in dependency.findall("./m:exclusions/m:exclusion", NS)
    }
    assert ("org.eclipse.jetty", "jetty-server") in exclusions
    assert ("org.eclipse.jetty", "jetty-servlet") in exclusions


def test_package_builds_clean_war():
    result = subprocess.run(
        ["mvn", "--batch-mode", "package"],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=240,
    )
    if result.returncode != 0:
        print(result.stdout)
    assert result.returncode == 0, "mvn package should succeed"
    assert WAR_PATH.exists(), f"missing {WAR_PATH}"

    with zipfile.ZipFile(WAR_PATH) as archive:
        names = archive.namelist()

    assert "WEB-INF/classes/com/acme/webportal/web/GreetingServlet.class" in names
    assert any(name.startswith("WEB-INF/lib/portal-bootstrap-1.0.0") for name in names)

    forbidden = []
    for name in names:
        if not name.startswith("WEB-INF/lib/"):
            continue
        file_name = name.rsplit("/", 1)[-1]
        if file_name.startswith("jakarta.servlet-api-") or file_name.startswith("jetty-"):
            forbidden.append(file_name)

    assert not forbidden, f"WAR should not contain servlet or Jetty container jars: {forbidden}"
