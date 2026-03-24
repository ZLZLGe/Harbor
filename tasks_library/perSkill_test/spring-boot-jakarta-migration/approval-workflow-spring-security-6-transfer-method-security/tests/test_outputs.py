import os
import subprocess

WORKSPACE_DIR = "/workspace"
METHOD_SECURITY_CONFIG = os.path.join(
    WORKSPACE_DIR,
    "src/main/java/com/example/approval/security/MethodSecurityConfig.java",
)


def read_method_security_config():
    with open(METHOD_SECURITY_CONFIG, encoding="utf-8") as file:
        return file.read()


class TestMethodSecurityMigrationShape:
    def test_removed_legacy_apis(self):
        content = read_method_security_config()
        assert "WebSecurityConfigurerAdapter" not in content
        assert "EnableGlobalMethodSecurity" not in content
        assert "authorizeRequests" not in content
        assert "antMatchers" not in content

    def test_component_based_method_security_is_present(self):
        content = read_method_security_config()
        assert "EnableMethodSecurity" in content
        assert "SecurityFilterChain" in content
        assert "authorizeHttpRequests" in content
        assert "requestMatchers" in content
        assert "httpBasic" in content

    def test_authentication_wiring_and_public_health_rule_remain(self):
        content = read_method_security_config()
        assert "PasswordEncoder" in content
        assert "UserDetailsService" in content
        assert (
            "AuthenticationProvider" in content
            or "AuthenticationConfiguration" in content
            or "DaoAuthenticationProvider" in content
        )
        assert "/actuator/health" in content
        assert "SessionCreationPolicy.STATELESS" in content


class TestProjectBehavior:
    def test_maven_tests_pass(self):
        result = subprocess.run(
            [
                "bash",
                "-lc",
                "source /root/.sdkman/bin/sdkman-init.sh && sdk use java 21.0.2-tem >/dev/null && mvn test -q",
            ],
            cwd=WORKSPACE_DIR,
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, result.stdout + "\n" + result.stderr
