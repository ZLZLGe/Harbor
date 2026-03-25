import subprocess
from pathlib import Path


WORKSPACE = Path("/workspace")


def read_text(relative_path: str) -> str:
    return (WORKSPACE / relative_path).read_text()


def test_boot_and_java_versions_are_upgraded():
    pom = read_text("pom.xml")
    assert "<version>3.2." in pom, "pom.xml must use Spring Boot 3.2.x"
    assert "<java.version>21</java.version>" in pom, "pom.xml must target Java 21"


def test_old_jjwt_and_jaxb_dependencies_are_removed():
    pom = read_text("pom.xml")
    assert "<artifactId>jjwt</artifactId>" not in pom, "legacy jjwt 0.9 dependency must be removed"
    assert "javax.xml.bind" not in pom, "legacy JAXB dependency must be removed"
    assert "<artifactId>jjwt-api</artifactId>" in pom, "modern jjwt modular dependency is required"


def test_main_sources_no_longer_use_javax_namespace():
    for java_file in (WORKSPACE / "src/main/java").rglob("*.java"):
        content = java_file.read_text()
        assert "javax.persistence" not in content, f"found javax.persistence in {java_file}"
        assert "javax.validation" not in content, f"found javax.validation in {java_file}"
        assert "javax.servlet" not in content, f"found javax.servlet in {java_file}"


def test_security_config_uses_security_filter_chain():
    content = read_text("src/main/java/com/acme/claims/config/SecurityConfig.java")
    assert "SecurityFilterChain" in content, "SecurityConfig must define SecurityFilterChain"
    assert "requestMatchers" in content, "SecurityConfig must use requestMatchers"
    assert "EnableMethodSecurity" in content, "SecurityConfig must enable method security"
    assert "WebSecurityConfigurerAdapter" not in content, "legacy security adapter should be removed"
    assert "antMatchers" not in content, "legacy antMatchers should be removed"
    assert "EnableGlobalMethodSecurity" not in content, "legacy method security annotation should be removed"


def test_risk_gateway_uses_modern_http_client():
    content = read_text("src/main/java/com/acme/claims/service/RiskGateway.java")
    assert "RestTemplate" not in content, "legacy RestTemplate should be removed from risk gateway"
    assert any(client in content for client in ("RestClient", "WebClient")), (
        "risk gateway must use a Spring Boot 3.2-compatible HTTP client such as RestClient or WebClient"
    )


def test_maven_clean_compile_succeeds():
    result = subprocess.run(
        ["mvn", "clean", "compile", "-q"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr


def test_maven_test_succeeds():
    result = subprocess.run(
        ["mvn", "test", "-q"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
