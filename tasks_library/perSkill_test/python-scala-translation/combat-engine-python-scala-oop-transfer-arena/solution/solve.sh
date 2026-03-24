#!/bin/bash
set -euo pipefail

cat <<'EOF' > /root/CombatArena.scala
package arena

import scala.collection.mutable.ArrayBuffer

case class Equipment(
  name: String,
  attackBonus: Int = 0,
  defenseBonus: Int = 0,
  manaBonus: Int = 0,
  tags: Vector[String] = Vector.empty
)

object EquipmentFactory {
  private val catalog: Map[String, Equipment] = Map(
    "iron-sword" -> Equipment("Iron Sword", attackBonus = 2, tags = Vector("weapon", "starter")),
    "hide-armor" -> Equipment("Hide Armor", defenseBonus = 1, tags = Vector("armor", "beast")),
    "focus-charm" -> Equipment("Focus Charm", manaBonus = 2, tags = Vector("focus", "starter"))
  )

  private def normalize(code: String): String =
    code.trim.toLowerCase.replace("_", "-").replace(" ", "-")

  def create(code: String): Equipment =
    catalog.getOrElse(normalize(code), throw new IllegalArgumentException(s"Unknown equipment: $code"))
}

case class CombatLogEntry(roundNumber: Int, actor: String, action: String, detail: String) {
  def render: String = s"$roundNumber:$actor:$action:$detail"
}

case class BattleResult(winner: String, rounds: Int, logs: Vector[CombatLogEntry]) {
  def summary: String = s"winner=$winner;rounds=$rounds;logs=${logs.size}"
}

abstract class StatusEffect(val name: String, private var remainingTurns: Int) {
  def duration: Int = remainingTurns
  def active: Boolean = remainingTurns > 0
  def attackBonus: Int = 0
  def defenseBonus: Int = 0
  def manaRegen: Int = 0
  def onTurnStart(target: Combatant, engine: BattleEngine): Unit = ()
  def advance(): Unit = {
    remainingTurns -= 1
  }
  def copyEffect(): StatusEffect
}

class BurnEffect(initialDuration: Int = 2, val damagePerTurn: Int = 2)
    extends StatusEffect("burn", initialDuration) {
  override def onTurnStart(target: Combatant, engine: BattleEngine): Unit = {
    val dealt = target.receiveDamage(damagePerTurn, ignoreDefense = true)
    engine.record(target.name, "burn", s"damage=$dealt")
  }

  override def copyEffect(): StatusEffect = new BurnEffect(duration, damagePerTurn)
}

class ShieldEffect(initialDuration: Int = 2, val defenseBoost: Int = 3)
    extends StatusEffect("shield", initialDuration) {
  override def defenseBonus: Int = defenseBoost
  override def copyEffect(): StatusEffect = new ShieldEffect(duration, defenseBoost)
}

class FocusEffect(initialDuration: Int = 2, val attackBoost: Int = 2, val manaRegenBonus: Int = 1)
    extends StatusEffect("focus", initialDuration) {
  override def attackBonus: Int = attackBoost
  override def manaRegen: Int = manaRegenBonus
  override def copyEffect(): StatusEffect = new FocusEffect(duration, attackBoost, manaRegenBonus)
}

abstract class Skill(val name: String, val manaCost: Int = 0) {
  def canUse(user: Combatant, target: Combatant): Boolean =
    user.alive && user.mana >= manaCost

  def use(user: Combatant, target: Combatant, engine: BattleEngine): Unit
}

class SlashSkill(skillName: String = "Slash", val flatBonus: Int = 3) extends Skill(skillName, manaCost = 0) {
  override def use(user: Combatant, target: Combatant, engine: BattleEngine): Unit = {
    val dealt = target.receiveDamage(user.attackPower + flatBonus)
    engine.record(user.name, name, s"damage=$dealt;target=${target.name}")
  }
}

class FireballSkill(
  skillName: String = "Fireball",
  val baseDamage: Int = 6,
  val burnDuration: Int = 2,
  val burnDamage: Int = 2
) extends Skill(skillName, manaCost = 4) {
  override def use(user: Combatant, target: Combatant, engine: BattleEngine): Unit = {
    user.spendMana(manaCost)
    val dealt = target.receiveDamage(baseDamage + user.attackPower / 2)
    target.addStatus(new BurnEffect(burnDuration, burnDamage))
    engine.record(user.name, name, s"damage=$dealt;burn=$burnDamage/$burnDuration;target=${target.name}")
  }
}

class GuardSkill(skillName: String = "Guard", val defenseBoost: Int = 3, val turns: Int = 2)
    extends Skill(skillName, manaCost = 2) {
  override def use(user: Combatant, target: Combatant, engine: BattleEngine): Unit = {
    user.spendMana(manaCost)
    user.addStatus(new ShieldEffect(turns, defenseBoost))
    engine.record(user.name, name, s"shield=$defenseBoost;turns=$turns")
  }
}

class HealSkill(skillName: String = "Heal", val amount: Int = 6) extends Skill(skillName, manaCost = 3) {
  override def canUse(user: Combatant, target: Combatant): Boolean =
    super.canUse(user, target) && user.currentHp < user.maxHp

  override def use(user: Combatant, target: Combatant, engine: BattleEngine): Unit = {
    user.spendMana(manaCost)
    val healed = user.heal(amount + user.attackPower / 3)
    engine.record(user.name, name, s"healed=$healed")
  }
}

class RallySkill(
  skillName: String = "Rally",
  val attackBoost: Int = 2,
  val manaRegenBonus: Int = 1,
  val turns: Int = 2
) extends Skill(skillName, manaCost = 2) {
  override def use(user: Combatant, target: Combatant, engine: BattleEngine): Unit = {
    user.spendMana(manaCost)
    user.addStatus(new FocusEffect(turns, attackBoost, manaRegenBonus))
    engine.record(user.name, name, s"focus=$attackBoost;regen=$manaRegenBonus;turns=$turns")
  }
}

abstract class Combatant(
  val name: String,
  val maxHp: Int,
  val baseAttack: Int,
  val baseDefense: Int,
  private val baseMaxMana: Int = 0
) {
  private var currentHpValue: Int = maxHp
  private var manaValue: Int = baseMaxMana
  protected val equipmentSlots: ArrayBuffer[Equipment] = ArrayBuffer.empty
  protected val learnedSkills: ArrayBuffer[Skill] = ArrayBuffer.empty
  protected val activeStatuses: ArrayBuffer[StatusEffect] = ArrayBuffer.empty

  def currentHp: Int = currentHpValue
  def maxMana: Int = baseMaxMana + equipmentSlots.map(_.manaBonus).sum
  def mana: Int = manaValue
  def alive: Boolean = currentHpValue > 0

  def attackPower: Int =
    baseAttack + equipmentSlots.map(_.attackBonus).sum + activeStatuses.map(_.attackBonus).sum

  def defensePower: Int =
    baseDefense + equipmentSlots.map(_.defenseBonus).sum + activeStatuses.map(_.defenseBonus).sum

  def statuses: Vector[StatusEffect] = activeStatuses.toVector

  def equip(item: Equipment): Unit = {
    equipmentSlots += item
    manaValue = maxMana
  }

  def learnSkill(skill: Skill): Unit = {
    learnedSkills += skill
  }

  def hasStatus(effectName: String): Boolean = {
    val normalized = effectName.trim.toLowerCase
    activeStatuses.exists(effect => effect.name == normalized && effect.active)
  }

  def addStatus(effect: StatusEffect): Unit = {
    val replacement = effect.copyEffect()
    val index = activeStatuses.indexWhere(_.name == replacement.name)
    if (index >= 0) {
      activeStatuses.update(index, replacement)
    } else {
      activeStatuses += replacement
    }
  }

  def receiveDamage(amount: Int, ignoreDefense: Boolean = false): Int = {
    val mitigated = if (ignoreDefense) amount else amount - defensePower
    val dealt = math.max(1, mitigated)
    currentHpValue = math.max(0, currentHpValue - dealt)
    dealt
  }

  def heal(amount: Int): Int = {
    val healed = math.min(amount, maxHp - currentHpValue)
    currentHpValue += healed
    healed
  }

  def spendMana(amount: Int): Boolean = {
    if (manaValue < amount) {
      false
    } else {
      manaValue -= amount
      true
    }
  }

  def restoreMana(amount: Int): Int = {
    val before = manaValue
    manaValue = math.min(maxMana, manaValue + amount)
    manaValue - before
  }

  def startTurn(engine: BattleEngine): Unit = {
    val regen = 1 + activeStatuses.map(_.manaRegen).sum
    restoreMana(regen)
    activeStatuses.foreach(_.onTurnStart(this, engine))
  }

  def endTurn(engine: BattleEngine): Unit = {
    val remaining = ArrayBuffer.empty[StatusEffect]
    activeStatuses.foreach { effect =>
      effect.advance()
      if (effect.active) {
        remaining += effect
      } else {
        engine.record(name, "status-expired", effect.name)
      }
    }
    activeStatuses.clear()
    activeStatuses ++= remaining
  }

  def takeTurn(opponent: Combatant, engine: BattleEngine): Unit = {
    if (!alive) {
      return
    }

    startTurn(engine)
    if (!alive) {
      return
    }

    chooseSkill(opponent) match {
      case Some(skill) => skill.use(this, opponent, engine)
      case None        => engine.record(name, "wait", "no-usable-skill")
    }

    endTurn(engine)
  }

  def firstUsable: Option[Skill] =
    learnedSkills.find(skill => skill.canUse(this, this))

  def chooseSkill(opponent: Combatant): Option[Skill]
}

class Hero(name: String, maxHp: Int, baseAttack: Int, baseDefense: Int, maxMana: Int = 0)
    extends Combatant(name, maxHp, baseAttack, baseDefense, maxMana) {
  override def chooseSkill(opponent: Combatant): Option[Skill] = {
    learnedSkills.collectFirst {
      case skill: RallySkill if !hasStatus("focus") && skill.canUse(this, opponent) => skill
    }.orElse {
      learnedSkills.collectFirst {
        case skill: HealSkill if currentHp <= maxHp / 2 && skill.canUse(this, opponent) => skill
      }
    }.orElse {
      learnedSkills.collectFirst {
        case skill: FireballSkill if !opponent.hasStatus("burn") && skill.canUse(this, opponent) => skill
      }
    }.orElse {
      learnedSkills.collectFirst {
        case skill: SlashSkill if skill.canUse(this, opponent) => skill
      }
    }.orElse(firstUsable)
  }
}

class Monster(name: String, maxHp: Int, baseAttack: Int, baseDefense: Int, maxMana: Int = 0)
    extends Combatant(name, maxHp, baseAttack, baseDefense, maxMana) {
  override def chooseSkill(opponent: Combatant): Option[Skill] = {
    learnedSkills.collectFirst {
      case skill: GuardSkill
          if currentHp <= (maxHp * 2) / 3 && !hasStatus("shield") && skill.canUse(this, opponent) =>
        skill
    }.orElse {
      learnedSkills.collectFirst {
        case skill: SlashSkill if skill.canUse(this, opponent) => skill
      }
    }.orElse(firstUsable)
  }
}

class BattleEngine(val hero: Combatant, val monster: Combatant) {
  private val recordedLogs: ArrayBuffer[CombatLogEntry] = ArrayBuffer.empty
  private var roundValue: Int = 0

  def currentRound: Int = roundValue
  def logs: Vector[CombatLogEntry] = recordedLogs.toVector

  def record(actor: String, action: String, detail: String): Unit = {
    recordedLogs += CombatLogEntry(currentRound, actor, action, detail)
  }

  def run(maxRounds: Int = 5): BattleResult = {
    for (round <- 1 to maxRounds if hero.alive && monster.alive) {
      roundValue = round
      if (hero.alive) {
        hero.takeTurn(monster, this)
      }
      if (monster.alive) {
        monster.takeTurn(hero, this)
      }
    }

    val winner =
      if (hero.alive && !monster.alive) {
        hero.name
      } else if (monster.alive && !hero.alive) {
        monster.name
      } else {
        "draw"
      }

    BattleResult(winner, roundValue, logs)
  }
}
EOF
