import hashlib
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_DIR = Path("/workspace/project")
POM_PATH = PROJECT_DIR / "pom.xml"
NS = {"m": "http://maven.apache.org/POM/4.0.0"}

EXPECTED_HASHES = {
    "src/main/java/com/acme/catalog/DescriptorCli.java": "3812c25a679dac704417a4431f361aa07a6e3ac89482b6bdabdcb6c37c886d98",
    "src/main/java/com/acme/catalog/DescriptorSpec.java": "81e13ff330f339a8cecafefde5d4996faa847b3f855084dc4c200f1326ceff6e",
    "src/main/java/com/acme/catalog/OrderSchema.java": "a5a6ad888ecd55b7bebe6e993a85c776114d4d075389540f2dbb308328e61f34",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def assert_source_files_unchanged() -> None:
    for relative_path, expected_hash in EXPECTED_HASHES.items():
        file_path = PROJECT_DIR / relative_path
        assert file_path.exists(), f"missing source file: {relative_path}"
        actual_hash = sha256(file_path)
        assert actual_hash == expected_hash, f"{relative_path} was modified"


def parse_plugin_configuration():
    tree = ET.parse(POM_PATH)
    plugin = tree.find(
        "./m:build/m:plugins/m:plugin[m:artifactId='maven-compiler-plugin']",
        NS,
    )
    assert plugin is not None, "maven-compiler-plugin is missing"
    return plugin


def get_text(node, xpath: str):
    found = node.find(xpath, NS)
    return None if found is None or found.text is None else found.text.strip()


def test_pom_configuration() -> None:
    plugin = parse_plugin_configuration()

    processor_artifact = get_text(
        plugin,
        "./m:configuration/m:annotationProcessorPaths/m:path/m:artifactId",
    )
    assert processor_artifact == "descriptor-processor", "annotation processor path must use descriptor-processor"

    compiler_args = [
        arg.text.strip()
        for arg in plugin.findall("./m:configuration/m:compilerArgs/m:arg", NS)
        if arg.text
    ]

    assert "-proc:only" not in compiler_args, "normal compilation must not keep -proc:only"
    assert "-Adescriptor.package=com.acme.catalog.generated" in compiler_args, "missing descriptor.package compiler arg"
    assert "-Adescriptor.className=OrderFieldsDescriptor" in compiler_args, "missing descriptor.className compiler arg"


def test_build_and_runtime_output() -> None:
    assert_source_files_unchanged()

    build = subprocess.run(
        ["mvn", "-q", "-DskipTests", "package"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    if build.returncode != 0:
        raise AssertionError(f"mvn package failed\nSTDOUT:\n{build.stdout}\nSTDERR:\n{build.stderr}")

    generated_source = PROJECT_DIR / "target/generated-sources/annotations/com/acme/catalog/generated/OrderFieldsDescriptor.java"
    assert generated_source.exists(), "expected generated source was not created"

    run = subprocess.run(
        ["java", "-cp", "target/classes", "com.acme.catalog.DescriptorCli"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    if run.returncode != 0:
        raise AssertionError(f"DescriptorCli failed\nSTDOUT:\n{run.stdout}\nSTDERR:\n{run.stderr}")

    assert run.stdout.strip() == "id,status,total", "unexpected CLI output"


if __name__ == "__main__":
    test_pom_configuration()
    test_build_and_runtime_output()
