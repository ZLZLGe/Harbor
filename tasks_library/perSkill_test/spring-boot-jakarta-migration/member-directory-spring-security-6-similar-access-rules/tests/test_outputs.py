import os
import subprocess

WORKSPACE_DIR = "/workspace"
SECURITY_CONFIG = os.path.join(
    WORKSPACE_DIR,
    "src/main/java/com/example/memberdirectory/config/SecurityConfig.java",
)


def read_security_config():
    with open(SECURITY_CONFIG, encoding="utf-8") as file:
        return file.read()


class TestSecurityConfigMigration:
    def test_removed_legacy_adapter_api(self):
        content = read_security_config()
        assert "WebSecurityConfigurerAdapter" not in content
        assert "EnableGlobalMethodSecurity" not in content
        assert "antMatchers" not in content
        assert "authorizeRequests" not in content
        assert "javax.servlet" not in content

    def test_component_based_security_beans_present(self):
        content = read_security_config()
        assert "EnableMethodSecurity" in content
        assert "SecurityFilterChain" in content
        assert "requestMatchers" in content
        assert "AuthenticationConfiguration" in content
        assert "getAuthenticationManager()" in content

    def test_public_endpoints_are_explicitly_listed(self):
        content = read_security_config()
        assert "/api/members/register" in content
        assert "/api/session/login" in content
        assert "/actuator/health" in content
        assert ".permitAll()" in content


class TestProjectBehavior:
    def test_maven_tests_pass(self):
        result = subprocess.run(
            ["bash", "-lc", "source /root/.sdkman/bin/sdkman-init.sh && sdk use java 21.0.2-tem >/dev/null && mvn test -q"],
            cwd=WORKSPACE_DIR,
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, result.stdout + "\n" + result.stderr
