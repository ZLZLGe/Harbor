from pathlib import Path
import re
import subprocess

WORKSPACE = Path("/workspace")


def read_text(relative_path: str) -> str:
    return (WORKSPACE / relative_path).read_text()


def test_required_files_use_jakarta_namespaces():
    expected_packages = {
        "src/main/java/com/example/catalog/api/CatalogApplication.java": "jakarta.ws.rs",
        "src/main/java/com/example/catalog/api/CatalogResource.java": "jakarta.annotation",
        "src/main/java/com/example/catalog/model/CatalogItem.java": "jakarta.xml.bind",
        "src/main/java/com/example/catalog/model/CatalogSnapshot.java": "jakarta.xml.bind",
        "src/main/java/com/example/catalog/model/CatalogPreviewRequest.java": "jakarta.xml.bind",
        "src/main/java/com/example/catalog/model/CatalogPreview.java": "jakarta.xml.bind",
        "src/test/java/com/example/catalog/api/CatalogResourceTest.java": "jakarta.ws.rs",
        "src/test/java/com/example/catalog/api/CatalogXmlCodecTest.java": "jakarta.xml.bind",
    }

    for relative_path, package_name in expected_packages.items():
        content = read_text(relative_path)
        assert package_name in content, f"{relative_path} should import {package_name}"


def test_no_legacy_javax_namespaces_remain():
    legacy_pattern = re.compile(r"\bjavax\.(ws\.rs|xml\.bind|annotation)\b")
    for java_file in WORKSPACE.rglob("*.java"):
        assert legacy_pattern.search(java_file.read_text()) is None, f"legacy namespace remains in {java_file}"


def test_catalog_contract_strings_remain_present():
    resource_content = read_text("src/main/java/com/example/catalog/api/CatalogResource.java")
    snapshot_content = read_text("src/main/java/com/example/catalog/model/CatalogSnapshot.java")
    preview_content = read_text("src/main/java/com/example/catalog/model/CatalogPreview.java")

    assert '"seasonal-catalog"' in resource_content
    assert '"ops-bot"' in resource_content
    assert '"UNASSIGNED"' in resource_content
    assert '"READY"' in resource_content
    assert '"catalog-preview"' in resource_content
    assert 'name = "catalogSnapshot"' in snapshot_content
    assert 'name = "catalogPreview"' in preview_content


def test_maven_tests_pass():
    result = subprocess.run(
        ["mvn", "test", "-q"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr
