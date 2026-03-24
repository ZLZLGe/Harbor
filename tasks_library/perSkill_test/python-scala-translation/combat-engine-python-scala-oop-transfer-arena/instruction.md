# Transfer: 回合制战斗引擎翻译

`/root/CombatArena.py` 是一个 Python 回合制战斗引擎。请把它翻译为 Scala 2.13，并将结果保存到 `/root/CombatArena.scala`。

要求：

- Scala 文件必须使用 `package arena`。
- 需要保留并实现这些核心类型：`Equipment`、`EquipmentFactory`、`CombatLogEntry`、`BattleResult`、`StatusEffect`、`BurnEffect`、`ShieldEffect`、`FocusEffect`、`Skill`、`SlashSkill`、`FireballSkill`、`GuardSkill`、`HealSkill`、`RallySkill`、`Combatant`、`Hero`、`Monster`、`BattleEngine`。
- 需要保留并实现这些核心接口或方法：`create`、`equip`、`learnSkill`、`currentHp`、`mana`、`alive`、`attackPower`、`defensePower`、`hasStatus`、`addStatus`、`chooseSkill`、`takeTurn`、`run`、`render`、`summary`。
- 语义应与 Python 版本一致：角色与技能的类层次、状态效果的继承与刷新行为、装备工厂、只读属性、战斗日志记录和回合推进逻辑都要保持一致。
- 只依赖 Scala 2.13 标准库，不要引入第三方库。
- 代码应符合 Scala 风格，不要做逐行机械翻译。
