from pathlib import Path
import subprocess


WORKSPACE = Path("/workspace")
SECURITY_FILE = WORKSPACE / "src/main/java/com/example/approval/security/MethodSecurityConfiguration.java"


def test_security_configuration_uses_supported_apis():
    content = SECURITY_FILE.read_text()

    assert "EnableMethodSecurity" in content
    assert "SecurityFilterChain" in content
    assert "requestMatchers" in content

    assert "EnableGlobalMethodSecurity" not in content
    assert "WebSecurityConfigurerAdapter" not in content
    assert "antMatchers" not in content


def test_workspace_maven_tests_pass():
    result = subprocess.run(
        ["mvn", "-q", "test"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=300,
    )

    assert result.returncode == 0, result.stdout + "\n" + result.stderr
