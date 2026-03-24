import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

WORKSPACE_DIR = Path("/workspace/customer-profiles")
POM_PATH = WORKSPACE_DIR / "pom.xml"
NS = {"m": "http://maven.apache.org/POM/4.0.0"}


def read_pom_text() -> str:
    return POM_PATH.read_text()


def parse_pom() -> ET.Element:
    return ET.parse(POM_PATH).getroot()


def dependency_map():
    root = parse_pom()
    dependencies = {}
    for dep in root.findall("./m:dependencies/m:dependency", NS):
        group_id = dep.findtext("m:groupId", default="", namespaces=NS)
        artifact_id = dep.findtext("m:artifactId", default="", namespaces=NS)
        version = dep.findtext("m:version", default="", namespaces=NS)
        scope = dep.findtext("m:scope", default="", namespaces=NS)
        dependencies[(group_id, artifact_id)] = {"version": version, "scope": scope}
    return dependencies


class TestPomMigration:
    def test_parent_is_spring_boot_32(self):
        root = parse_pom()
        version = root.findtext("./m:parent/m:version", default="", namespaces=NS)
        assert re.fullmatch(r"3\.2(\.\d+)?", version), f"Unexpected Spring Boot version: {version}"

    def test_java_version_is_21(self):
        root = parse_pom()
        java_version = root.findtext("./m:properties/m:java.version", default="", namespaces=NS)
        assert java_version == "21", f"Expected java.version 21, got {java_version}"

    def test_old_jjwt_removed(self):
        deps = dependency_map()
        assert ("io.jsonwebtoken", "jjwt") not in deps, "Old single jjwt dependency should be removed"

    def test_modular_jjwt_present(self):
        deps = dependency_map()
        assert deps[("io.jsonwebtoken", "jjwt-api")]["version"].startswith("0.12")
        assert deps[("io.jsonwebtoken", "jjwt-impl")]["version"].startswith("0.12")
        assert deps[("io.jsonwebtoken", "jjwt-jackson")]["version"].startswith("0.12")
        assert deps[("io.jsonwebtoken", "jjwt-impl")]["scope"] == "runtime"
        assert deps[("io.jsonwebtoken", "jjwt-jackson")]["scope"] == "runtime"

    def test_legacy_jaxb_removed(self):
        deps = dependency_map()
        assert ("javax.xml.bind", "jaxb-api") not in deps
        assert "javax.xml.bind" not in read_pom_text()


class TestBuildVerification:
    def test_maven_compile(self):
        result = subprocess.run(
            [
                "bash",
                "-lc",
                "source /root/.sdkman/bin/sdkman-init.sh && sdk use java 21.0.2-tem >/dev/null && mvn -f /workspace/customer-profiles/pom.xml clean compile -q",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, f"Compile failed: {result.stdout}\n{result.stderr}"

    def test_maven_test(self):
        result = subprocess.run(
            [
                "bash",
                "-lc",
                "source /root/.sdkman/bin/sdkman-init.sh && sdk use java 21.0.2-tem >/dev/null && mvn -f /workspace/customer-profiles/pom.xml test -q",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, f"Tests failed: {result.stdout}\n{result.stderr}"
