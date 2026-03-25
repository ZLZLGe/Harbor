from functools import lru_cache
from pathlib import Path
import subprocess
import zipfile


PROJECT_DIR = Path("/workspace/reactor-release-console")
BUILD_LOG = PROJECT_DIR / "target/verifier-mvn-verify.log"
CLI_JAR = PROJECT_DIR / "cli-app/target/cli-app-1.0-SNAPSHOT.jar"
EXPECTED_STDOUT = "PLAN: nightly-ops|prepare-assets>warm-services>announce-window"
EXPECTED_CLASSES = {
    "com/acme/reactor/shared/ReleaseCatalog.class",
    "com/acme/reactor/service/RolloutPlanner.class",
    "com/acme/reactor/cli/ReleaseCli.class",
}


@lru_cache(maxsize=1)
def run_verify():
    BUILD_LOG.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["mvn", "verify"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    BUILD_LOG.write_text(result.stdout + "\n--- STDERR ---\n" + result.stderr)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
    return result


def test_mvn_verify_succeeds():
    result = run_verify()
    assert result.returncode == 0, "expected `mvn verify` to succeed"


def test_reactor_summary_reports_modules_in_dependency_order():
    result = run_verify()
    assert result.returncode == 0, "build must succeed before checking reactor summary"

    stdout = result.stdout
    shared_index = stdout.find("shared-lib")
    service_index = stdout.find("service-layer")
    cli_index = stdout.find("cli-app")

    assert shared_index != -1, "reactor output should mention shared-lib"
    assert service_index != -1, "reactor output should mention service-layer"
    assert cli_index != -1, "reactor output should mention cli-app"
    assert shared_index < service_index < cli_index, "reactor summary should list modules in dependency order"


def test_cli_jar_exists_and_is_executable():
    result = run_verify()
    assert result.returncode == 0, "build must succeed before checking CLI jar"
    assert CLI_JAR.exists(), f"missing output jar: {CLI_JAR}"

    run_result = subprocess.run(
        ["java", "-jar", str(CLI_JAR)],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    if run_result.returncode != 0:
        print(run_result.stdout)
        print(run_result.stderr)

    assert run_result.returncode == 0, "CLI jar should be directly executable"
    assert run_result.stdout.strip() == EXPECTED_STDOUT


def test_cli_jar_contains_all_module_classes():
    result = run_verify()
    assert result.returncode == 0, "build must succeed before checking jar contents"
    assert CLI_JAR.exists(), f"missing output jar: {CLI_JAR}"

    with zipfile.ZipFile(CLI_JAR) as jar_file:
        names = set(jar_file.namelist())

    for expected_name in EXPECTED_CLASSES:
        assert expected_name in names, f"expected shaded class missing from jar: {expected_name}"
