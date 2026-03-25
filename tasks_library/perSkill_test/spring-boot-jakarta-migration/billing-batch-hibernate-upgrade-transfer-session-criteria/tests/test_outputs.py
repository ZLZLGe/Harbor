from pathlib import Path
import subprocess


WORKSPACE = Path("/workspace")
PRIMARY_OUTPUT = WORKSPACE / "src/main/java/com/example/billing/job/InvoiceArchiveJob.java"
AUDIT_ENTITY = WORKSPACE / "src/main/java/com/example/billing/model/ArchiveAudit.java"


def test_primary_output_exists():
    assert PRIMARY_OUTPUT.exists(), "主要输出文件不存在"


def test_legacy_hibernate_patterns_are_removed():
    content = PRIMARY_OUTPUT.read_text()

    forbidden_tokens = [
        "javax.persistence",
        "org.hibernate.Criteria",
        "org.hibernate.criterion",
        "createCriteria(",
        "update from Invoice",
    ]

    for token in forbidden_tokens:
        assert token not in content, f"发现未迁移的旧写法: {token}"

    assert "jakarta.persistence" in content, "需要使用 jakarta.persistence"


def test_outdated_id_generation_is_removed():
    content = AUDIT_ENTITY.read_text()
    assert "@GenericGenerator" not in content, "不应保留旧式 GenericGenerator"
    assert "strategy = \"increment\"" not in content, "不应继续使用 increment 主键策略"
    assert "GenerationType.IDENTITY" in content or "GenerationType.SEQUENCE" in content, "需要切换到当前兼容的主键生成方式"


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
