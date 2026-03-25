#!/bin/bash

set -euo pipefail

mkdir -p /app/artifacts

python3 - <<'PY'
import json
from pathlib import Path

import yaml


INPUT_ROOT = Path("/app/refactor_audit_inputs")
OUTPUT_PATH = Path("/app/artifacts/refactor-memory-audit.yaml")


def load_json(name: str):
    with (INPUT_ROOT / name).open(encoding="utf-8") as f:
        return json.load(f)


def load_text(name: str) -> str:
    return (INPUT_ROOT / name).read_text(encoding="utf-8")


def locate_lines(name: str, needles):
    lines = load_text(name).splitlines()
    matches = []
    for needle in needles:
        for idx, line in enumerate(lines, start=1):
            if needle in line:
                matches.append((f"L{idx}", line.strip()))
                break
    return matches


bank = load_json("legacy_memory_bank.json")
module_index = load_json("module_index.json")

snapshot_hits = locate_lines(
    "refactor_snapshot.md",
    [
        "Library.Tactic.Induction` moved",
        "closed-form lemma first",
        "induction'",
        "mod_cases n % 2",
        "repository-relative evidence",
    ],
)
failure_hits = locate_lines(
    "build_failures.log",
    [
        "Library.Tactic.Induction",
        "simple_induction",
        "pow_pos",
        "mod_cases n % 2",
        "repeatedly unfolding the recurrence",
    ],
)
guide_hits = locate_lines(
    "migration_guide.md",
    [
        "simple_induction",
        "pow_pos",
        "top-level recurrence unfolding",
        "mod_cases n % 2",
        "repository-relative path plus line hint or theorem name",
    ],
)


def evidence(*items):
    return [{"file": file_name, "locator": locator, "reason": reason} for file_name, locator, reason in items]


records = []
for record in bank["records"]:
    rid = record["record_id"]
    old_conf = record["confidence"]

    if rid == "mem-pp-closed-tail":
        records.append(
            {
                "record_id": rid,
                "record_type": record["record_type"],
                "status": "needs_review",
                "old_confidence": old_conf,
                "new_confidence": 0.67,
                "decision": (
                    "核心策略仍然成立，因为闭式尾项仍是当前序列上界证明的推荐入口；"
                    "但旧记录依赖已删除的 `Library.Tactic.Induction` 路径和 `simple_induction`，所以需要改写后再继续信任。"
                ),
                "suggested_update": (
                    "把导入改成 `Math2001/Tactic/StrongInduction.lean`，将 `simple_induction` 更新为 `induction'`，"
                    "并优先引用 `geometric_tail_closed_form` 而不是重复手写旧闭式推导。"
                ),
                "evidence": evidence(
                    ("legacy_memory_bank.json", "records[mem-pp-closed-tail]", "旧记录明确依赖 `simple_induction` 和旧模块路径。"),
                    ("refactor_snapshot.md", snapshot_hits[0][0], "重构说明确认归纳 helper 已迁移。"),
                    ("refactor_snapshot.md", snapshot_hits[2][0], "当前工作流明确改用 `induction'`。"),
                    ("build_failures.log", failure_hits[1][0], "构建日志显示 `simple_induction` 已失效。"),
                    ("migration_guide.md", guide_hits[0][0], "迁移指南给出了新的替代写法。"),
                ),
            }
        )
    elif rid == "mem-fa-unfold-top":
        records.append(
            {
                "record_id": rid,
                "record_type": record["record_type"],
                "status": "valid",
                "old_confidence": old_conf,
                "new_confidence": 0.9,
                "decision": "这条失败经验没有被重构推翻；新快照仍然建议先拿到闭式，再处理不等式，构建日志也继续暴露顶层展开导致目标不收敛的问题。",
                "suggested_update": "保留这条失败记忆，只需把示例位置更新到当前快照中的几何尾项文件或新的构建日志片段。",
                "evidence": evidence(
                    ("legacy_memory_bank.json", "records[mem-fa-unfold-top]", "旧记录描述的是结构性死路，而不是某个短期 API。"),
                    ("refactor_snapshot.md", snapshot_hits[1][0], "当前证明流程仍要求先到闭式。"),
                    ("build_failures.log", failure_hits[4][0], "新日志继续记录顶层展开无助于简化目标。"),
                    ("migration_guide.md", guide_hits[2][0], "迁移指南明确说这条警告仍应保留。"),
                ),
            }
        )
    elif rid == "mem-pc-traceable-citation":
        records.append(
            {
                "record_id": rid,
                "record_type": record["record_type"],
                "status": "valid",
                "old_confidence": old_conf,
                "new_confidence": 0.9,
                "decision": "证据引用规范在这次重构里没有变化，仍然是维护和复查历史记录的基础约束。",
                "suggested_update": "保留这条约定，并把示例文件名更新成当前索引中的 `docs/reviewing.md` 或新的 theorem 名称。",
                "evidence": evidence(
                    ("legacy_memory_bank.json", "records[mem-pc-traceable-citation]", "旧记录描述的是项目级审计约定。"),
                    ("refactor_snapshot.md", snapshot_hits[4][0], "重构快照明确说审阅卫生规则保持不变。"),
                    ("migration_guide.md", guide_hits[4][0], "迁移指南再次确认证据格式仍然强制执行。"),
                    ("module_index.json", "tracked_files[3]", "当前索引里仍保留 review 文档入口。"),
                ),
            }
        )
    elif rid == "mem-td-pow-pos":
        records.append(
            {
                "record_id": rid,
                "record_type": record["record_type"],
                "status": "deprecated",
                "old_confidence": old_conf,
                "new_confidence": 0.18,
                "decision": "这条依赖记录直接绑定了已经移除的常量名 `pow_pos`，在当前快照中不能继续作为可靠依赖保留。",
                "suggested_update": "废弃旧条目，改写成显式引用 `pow_pos_of_pos` 的新依赖记录，并补上当前模块路径和 theorem 名。",
                "evidence": evidence(
                    ("legacy_memory_bank.json", "records[mem-td-pow-pos]", "旧记录把 `pow_pos` 当成关键依赖。"),
                    ("build_failures.log", failure_hits[2][0], "构建日志显示 `pow_pos` 已经无法解析。"),
                    ("migration_guide.md", guide_hits[1][0], "迁移指南给出直接替代项 `pow_pos_of_pos`。"),
                    ("module_index.json", "available_theorems[1]", "当前索引里存在的是 `pow_pos_of_pos`。"),
                ),
            }
        )
    elif rid == "mem-pp-modcases-parity":
        records.append(
            {
                "record_id": rid,
                "record_type": record["record_type"],
                "status": "deprecated",
                "old_confidence": old_conf,
                "new_confidence": 0.21,
                "decision": "这条套路依赖的 `mod_cases n % 2` 已退出维护流程；重构后的奇偶性证明转向整数同余引理，因此原 recipe 不再应被推荐。",
                "suggested_update": "把这条记忆改写为先做整数 coercion，再围绕 `Int.ModEq.pow`、`Int.ModEq.add` 或 `Int.ModEq.mul` 组织分支证明。",
                "evidence": evidence(
                    ("legacy_memory_bank.json", "records[mem-pp-modcases-parity]", "旧记录明确把 `mod_cases n % 2` 作为默认入口。"),
                    ("refactor_snapshot.md", snapshot_hits[3][0], "重构快照明确说该捷径不再维护。"),
                    ("build_failures.log", failure_hits[3][0], "当前构建日志显示旧 tactic recipe 已失效。"),
                    ("migration_guide.md", guide_hits[3][0], "迁移指南要求改用 `Int.ModEq` 路线。"),
                    ("module_index.json", "available_theorems[2..4]", "当前可用索引提供的是 `Int.ModEq` 系列引理。"),
                ),
            }
        )
    else:
        raise RuntimeError(f"Unexpected record id: {rid}")


status_counts = {
    "valid": sum(1 for item in records if item["status"] == "valid"),
    "needs_review": sum(1 for item in records if item["status"] == "needs_review"),
    "deprecated": sum(1 for item in records if item["status"] == "deprecated"),
}

refresh_queue = [
    {
        "record_id": "mem-td-pow-pos",
        "priority": 1,
        "next_step": "先把已失效的 theorem dependency 改写为 `pow_pos_of_pos`，否则后续引用会继续直接报错。",
    },
    {
        "record_id": "mem-pp-modcases-parity",
        "priority": 2,
        "next_step": "重写奇偶性套路说明，改成整数同余路线，并补上 `Int.ModEq` 系列证据。",
    },
    {
        "record_id": "mem-pp-closed-tail",
        "priority": 3,
        "next_step": "在保留核心闭式思路的前提下，把旧归纳 recipe 迁移到 `induction'` 与 `geometric_tail_closed_form`。",
    },
]

output = {
    "audit_id": "refactor-audit-2026-03-lean-sequence-memories",
    "audited_inputs": [
        "/app/refactor_audit_inputs/legacy_memory_bank.json",
        "/app/refactor_audit_inputs/refactor_snapshot.md",
        "/app/refactor_audit_inputs/build_failures.log",
        "/app/refactor_audit_inputs/module_index.json",
        "/app/refactor_audit_inputs/migration_guide.md",
    ],
    "summary": {
        "total_records": len(records),
        "valid_count": status_counts["valid"],
        "needs_review_count": status_counts["needs_review"],
        "deprecated_count": status_counts["deprecated"],
        "audit_focus": "区分仍可靠的项目记忆、需要降级后修订的记录，以及已经被重构直接淘汰的旧 recipe。",
    },
    "records": records,
    "refresh_queue": refresh_queue,
}

OUTPUT_PATH.write_text(yaml.safe_dump(output, sort_keys=False, allow_unicode=True), encoding="utf-8")
PY
