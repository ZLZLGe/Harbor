from pathlib import Path
import subprocess


WORKSPACE = Path("/workspace")
PRIMARY_OUTPUT = WORKSPACE / "src/main/java/com/example/inventory/repository/StockItemRepository.java"


def test_primary_output_exists():
    assert PRIMARY_OUTPUT.exists(), "主要输出文件不存在"


def test_repository_no_longer_uses_legacy_hibernate_5_apis():
    content = PRIMARY_OUTPUT.read_text()

    forbidden_tokens = [
        "javax.persistence",
        "org.hibernate.Criteria",
        "org.hibernate.criterion",
        "createCriteria(",
        "update from StockItem",
    ]

    for token in forbidden_tokens:
        assert token not in content, f"发现未迁移的旧写法: {token}"

    assert "jakarta.persistence" in content, "需要切换到 jakarta.persistence 命名空间"


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
