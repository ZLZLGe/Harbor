import csv
import os


def test_outputs() -> None:
    workspace_root = os.environ.get("WORKSPACE_ROOT", "/app/workspace")
    output_path = os.path.join(workspace_root, "output", "azure_identity_posture.csv")
    assert os.path.exists(output_path), f"缺少输出文件: {output_path}"

    with open(output_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        headers = reader.fieldnames

    expected_headers = ["app", "identity_grade", "keyvault_readiness", "rotation_needed", "notes"]
    assert headers == expected_headers, f"输出列不匹配: {headers}"

    expected_rows = [
        {
            "app": "audit-cli",
            "identity_grade": "C",
            "keyvault_readiness": "missing",
            "rotation_needed": "yes",
            "notes": "explicit_credential;kv_missing;content_safety_off",
        },
        {
            "app": "content-guard",
            "identity_grade": "A",
            "keyvault_readiness": "ready",
            "rotation_needed": "no",
            "notes": "managed_identity;kv_ready;content_safety_on",
        },
        {
            "app": "finance-api",
            "identity_grade": "A",
            "keyvault_readiness": "ready",
            "rotation_needed": "no",
            "notes": "managed_identity;kv_ready;content_safety_off",
        },
        {
            "app": "java-worker",
            "identity_grade": "B",
            "keyvault_readiness": "ready",
            "rotation_needed": "no",
            "notes": "managed_identity;kv_ready;content_safety_on",
        },
        {
            "app": "rust-daemon",
            "identity_grade": "C",
            "keyvault_readiness": "ready",
            "rotation_needed": "no",
            "notes": "explicit_credential;kv_ready;content_safety_off",
        },
        {
            "app": "ts-portal",
            "identity_grade": "A",
            "keyvault_readiness": "missing",
            "rotation_needed": "yes",
            "notes": "managed_identity;kv_missing;content_safety_on",
        },
    ]

    assert rows == expected_rows, f"输出内容不匹配.\nactual={rows}\nexpected={expected_rows}"

    apps = [row["app"] for row in rows]
    assert apps == sorted(apps), f"输出未按 app 升序排序: {apps}"

    for row in rows:
        for key, value in row.items():
            assert value not in {"", "null", "None", "nan", "NaN"}, f"{key} 存在非法值: {value}"
            assert value == value.strip(), f"{key} 含首尾空白: {value!r}"


if __name__ == "__main__":
    test_outputs()
