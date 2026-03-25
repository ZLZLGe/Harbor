from pathlib import Path
import subprocess


WORKSPACE = Path("/workspace")
PRIMARY_OUTPUT = WORKSPACE / "src/main/java/com/example/reporting/service/ShipmentSummaryService.java"


def test_primary_output_exists():
    assert PRIMARY_OUTPUT.exists(), "主要输出文件不存在"


def test_maven_test_passes():
    result = subprocess.run(
        ["mvn", "test", "-q"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=240,
    )

    assert result.returncode == 0, (
        "mvn test 失败\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
