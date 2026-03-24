#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REQUIRED_PATTERNS: list[tuple[str, str]] = [
    ("package", r"package\s+arena"),
    ("Equipment", r"case\s+class\s+Equipment"),
    ("EquipmentFactory", r"object\s+EquipmentFactory"),
    ("CombatLogEntry", r"case\s+class\s+CombatLogEntry"),
    ("BattleResult", r"case\s+class\s+BattleResult"),
    ("StatusEffect", r"abstract\s+class\s+StatusEffect"),
    ("BurnEffect", r"class\s+BurnEffect"),
    ("ShieldEffect", r"class\s+ShieldEffect"),
    ("FocusEffect", r"class\s+FocusEffect"),
    ("Skill", r"abstract\s+class\s+Skill"),
    ("SlashSkill", r"class\s+SlashSkill"),
    ("FireballSkill", r"class\s+FireballSkill"),
    ("GuardSkill", r"class\s+GuardSkill"),
    ("HealSkill", r"class\s+HealSkill"),
    ("RallySkill", r"class\s+RallySkill"),
    ("Combatant", r"abstract\s+class\s+Combatant"),
    ("Hero", r"class\s+Hero"),
    ("Monster", r"class\s+Monster"),
    ("BattleEngine", r"class\s+BattleEngine"),
    ("currentHp", r"def\s+currentHp"),
    ("attackPower", r"def\s+attackPower"),
    ("defensePower", r"def\s+defensePower"),
    ("chooseSkill", r"def\s+chooseSkill"),
    ("run", r"def\s+run"),
]

ANTI_PATTERNS: list[tuple[str, str]] = [
    (r"\bnull\b", "不要使用 null"),
    (r"\.asInstanceOf\[", "不要使用 asInstanceOf"),
]

SCALA_RUNNER = """import arena._

object TestRunner {
  private def line(key: String, value: String): Unit = println(s"$key=$value")

  private def serializeStatuses(statuses: Seq[StatusEffect]): String =
    if (statuses.isEmpty) "none" else statuses.map(effect => s"${effect.name}:${effect.duration}").mkString("|")

  def main(args: Array[String]): Unit = {
    val sword = EquipmentFactory.create("Iron Sword")
    val charm = EquipmentFactory.create("focus_charm")

    val trainingHero = new Hero("Scout", 20, 4, 2, 8)
    trainingHero.equip(sword)
    trainingHero.equip(charm)
    trainingHero.addStatus(new FocusEffect(2, 3, 2))
    line("training_attack", trainingHero.attackPower.toString)
    line("training_mana", trainingHero.mana.toString)
    trainingHero.addStatus(new ShieldEffect(1, 4))
    line("training_defense", trainingHero.defensePower.toString)
    line("factory_tags", sword.tags.mkString(","))

    val hero = new Hero("Aria", 24, 5, 2, 10)
    hero.equip(EquipmentFactory.create("iron-sword"))
    hero.equip(EquipmentFactory.create("focus charm"))
    hero.learnSkill(new SlashSkill())
    hero.learnSkill(new FireballSkill())
    hero.learnSkill(new HealSkill())
    hero.learnSkill(new RallySkill())

    val monster = new Monster("Gronn", 30, 5, 3, 6)
    monster.equip(EquipmentFactory.create("hide_armor"))
    monster.learnSkill(new SlashSkill("Claw", flatBonus = 1))
    monster.learnSkill(new GuardSkill())

    val engine = new BattleEngine(hero, monster)
    val result = engine.run(5)

    line("winner", result.winner)
    line("rounds", result.rounds.toString)
    line("hero_hp", hero.currentHp.toString)
    line("hero_mana", hero.mana.toString)
    line("hero_attack", hero.attackPower.toString)
    line("hero_defense", hero.defensePower.toString)
    line("hero_statuses", serializeStatuses(hero.statuses))
    line("monster_hp", monster.currentHp.toString)
    line("monster_mana", monster.mana.toString)
    line("monster_attack", monster.attackPower.toString)
    line("monster_defense", monster.defensePower.toString)
    line("monster_statuses", serializeStatuses(monster.statuses))
    line("log_size", result.logs.size.toString)
    line("first_log", result.logs.head.render)
    line("last_log", result.logs.last.render)
    line("burn_log_count", result.logs.count(_.action == "burn").toString)
    line("summary", result.summary)
  }
}
"""


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def load_module(source_file: Path):
    spec = importlib.util.spec_from_file_location("combat_arena_source", source_file)
    if spec is None or spec.loader is None:
        raise SystemExit(f"无法加载 Python 参考实现: {source_file}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def serialize_statuses(statuses) -> str:
    values = [f"{status.name}:{status.duration}" for status in statuses]
    return "none" if not values else "|".join(values)


def build_expected(module) -> dict[str, str]:
    sword = module.EquipmentFactory.create("Iron Sword")
    charm = module.EquipmentFactory.create("focus_charm")

    training_hero = module.Hero("Scout", 20, 4, 2, 8)
    training_hero.equip(sword)
    training_hero.equip(charm)
    training_hero.add_status(module.FocusEffect(2, 3, 2))
    training_attack = str(training_hero.attack_power)
    training_mana = str(training_hero.mana)
    training_hero.add_status(module.ShieldEffect(1, 4))
    training_defense = str(training_hero.defense_power)

    hero = module.Hero("Aria", 24, 5, 2, 10)
    hero.equip(module.EquipmentFactory.create("iron-sword"))
    hero.equip(module.EquipmentFactory.create("focus charm"))
    hero.learn_skill(module.SlashSkill())
    hero.learn_skill(module.FireballSkill())
    hero.learn_skill(module.HealSkill())
    hero.learn_skill(module.RallySkill())

    monster = module.Monster("Gronn", 30, 5, 3, 6)
    monster.equip(module.EquipmentFactory.create("hide_armor"))
    monster.learn_skill(module.SlashSkill(name="Claw", flat_bonus=1))
    monster.learn_skill(module.GuardSkill())

    engine = module.BattleEngine(hero, monster)
    result = engine.run(max_rounds=5)

    return {
        "training_attack": training_attack,
        "training_mana": training_mana,
        "training_defense": training_defense,
        "factory_tags": ",".join(sword.tags),
        "winner": result.winner,
        "rounds": str(result.rounds),
        "hero_hp": str(hero.current_hp),
        "hero_mana": str(hero.mana),
        "hero_attack": str(hero.attack_power),
        "hero_defense": str(hero.defense_power),
        "hero_statuses": serialize_statuses(hero.statuses),
        "monster_hp": str(monster.current_hp),
        "monster_mana": str(monster.mana),
        "monster_attack": str(monster.attack_power),
        "monster_defense": str(monster.defense_power),
        "monster_statuses": serialize_statuses(monster.statuses),
        "log_size": str(len(result.logs)),
        "first_log": result.logs[0].render(),
        "last_log": result.logs[-1].render(),
        "burn_log_count": str(sum(1 for entry in result.logs if entry.action == "burn")),
        "summary": result.summary(),
    }


def parse_runner_output(stdout: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key] = value
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scala_file")
    parser.add_argument("source_file")
    args = parser.parse_args()

    scala_file = Path(args.scala_file)
    source_file = Path(args.source_file)

    if not source_file.exists():
        raise SystemExit(f"缺少输入资产: {source_file}")

    if not scala_file.exists():
        raise SystemExit(f"缺少输出文件: {scala_file}")

    source = scala_file.read_text(encoding="utf-8")

    for name, pattern in REQUIRED_PATTERNS:
        if re.search(pattern, source) is None:
            raise SystemExit(f"缺少必需实现: {name}")

    for pattern, message in ANTI_PATTERNS:
        if re.search(pattern, source):
            raise SystemExit(message)

    if shutil.which("scalac") is None:
        raise SystemExit("scalac 不可用")
    if run(["scalac", "-version"]).returncode != 0:
        raise SystemExit("scalac 不可用")

    if shutil.which("scala") is None:
        raise SystemExit("scala 不可用")
    if run(["scala", "-version"]).returncode != 0:
        raise SystemExit("scala 不可用")

    module = load_module(source_file)
    expected = build_expected(module)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        runner_file = tmp_path / "TestRunner.scala"
        runner_file.write_text(SCALA_RUNNER, encoding="utf-8")

        compile_result = run(["scalac", "-d", str(out_dir), str(scala_file), str(runner_file)])
        if compile_result.returncode != 0:
            raise SystemExit(
                "Scala 编译失败:\n"
                f"{compile_result.stdout}\n{compile_result.stderr}".strip()
            )

        test_result = run(["scala", "-cp", str(out_dir), "TestRunner"])
        if test_result.returncode != 0:
            raise SystemExit(
                "语义校验失败:\n"
                f"{test_result.stdout}\n{test_result.stderr}".strip()
            )

        actual = parse_runner_output(test_result.stdout)

    missing = sorted(set(expected) - set(actual))
    if missing:
        raise SystemExit(f"Scala 测试输出缺少字段: {', '.join(missing)}")

    mismatches = [
        f"{key}: expected={expected[key]!r} actual={actual[key]!r}"
        for key in expected
        if expected[key] != actual.get(key)
    ]
    if mismatches:
        raise SystemExit("语义不一致:\n" + "\n".join(mismatches))

    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
