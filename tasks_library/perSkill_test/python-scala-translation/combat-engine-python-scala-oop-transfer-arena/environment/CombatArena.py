from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Equipment:
    name: str
    attack_bonus: int = 0
    defense_bonus: int = 0
    mana_bonus: int = 0
    tags: tuple[str, ...] = ()


class EquipmentFactory:
    _CATALOG: dict[str, Equipment] = {
        "iron-sword": Equipment("Iron Sword", attack_bonus=2, tags=("weapon", "starter")),
        "hide-armor": Equipment("Hide Armor", defense_bonus=1, tags=("armor", "beast")),
        "focus-charm": Equipment("Focus Charm", mana_bonus=2, tags=("focus", "starter")),
    }

    @classmethod
    def create(cls, code: str) -> Equipment:
        normalized = code.strip().lower().replace("_", "-").replace(" ", "-")
        if normalized not in cls._CATALOG:
            raise ValueError(f"Unknown equipment: {code}")
        return cls._CATALOG[normalized]


@dataclass(frozen=True)
class CombatLogEntry:
    round_number: int
    actor: str
    action: str
    detail: str

    def render(self) -> str:
        return f"{self.round_number}:{self.actor}:{self.action}:{self.detail}"


@dataclass(frozen=True)
class BattleResult:
    winner: str
    rounds: int
    logs: tuple[CombatLogEntry, ...]

    def summary(self) -> str:
        return f"winner={self.winner};rounds={self.rounds};logs={len(self.logs)}"


class StatusEffect(ABC):
    def __init__(self, name: str, duration: int) -> None:
        self.name = name
        self.duration = duration

    @property
    def active(self) -> bool:
        return self.duration > 0

    def attack_bonus(self) -> int:
        return 0

    def defense_bonus(self) -> int:
        return 0

    def mana_regen(self) -> int:
        return 0

    def on_turn_start(self, target: "Combatant", engine: "BattleEngine") -> None:
        return None

    def advance(self) -> None:
        self.duration -= 1

    @abstractmethod
    def clone(self) -> "StatusEffect":
        raise NotImplementedError


class BurnEffect(StatusEffect):
    def __init__(self, duration: int = 2, damage_per_turn: int = 2) -> None:
        super().__init__("burn", duration)
        self.damage_per_turn = damage_per_turn

    def on_turn_start(self, target: "Combatant", engine: "BattleEngine") -> None:
        dealt = target.receive_damage(self.damage_per_turn, ignore_defense=True)
        engine.record(target.name, "burn", f"damage={dealt}")

    def clone(self) -> "BurnEffect":
        return BurnEffect(self.duration, self.damage_per_turn)


class ShieldEffect(StatusEffect):
    def __init__(self, duration: int = 2, defense_boost: int = 3) -> None:
        super().__init__("shield", duration)
        self.defense_boost = defense_boost

    def defense_bonus(self) -> int:
        return self.defense_boost

    def clone(self) -> "ShieldEffect":
        return ShieldEffect(self.duration, self.defense_boost)


class FocusEffect(StatusEffect):
    def __init__(self, duration: int = 2, attack_boost: int = 2, mana_regen_bonus: int = 1) -> None:
        super().__init__("focus", duration)
        self.attack_boost = attack_boost
        self.mana_regen_bonus = mana_regen_bonus

    def attack_bonus(self) -> int:
        return self.attack_boost

    def mana_regen(self) -> int:
        return self.mana_regen_bonus

    def clone(self) -> "FocusEffect":
        return FocusEffect(self.duration, self.attack_boost, self.mana_regen_bonus)


class Skill(ABC):
    def __init__(self, name: str, mana_cost: int = 0) -> None:
        self.name = name
        self.mana_cost = mana_cost

    def can_use(self, user: "Combatant", target: "Combatant") -> bool:
        return user.alive and user.mana >= self.mana_cost

    @abstractmethod
    def use(self, user: "Combatant", target: "Combatant", engine: "BattleEngine") -> None:
        raise NotImplementedError


class SlashSkill(Skill):
    def __init__(self, name: str = "Slash", flat_bonus: int = 3) -> None:
        super().__init__(name, mana_cost=0)
        self.flat_bonus = flat_bonus

    def use(self, user: "Combatant", target: "Combatant", engine: "BattleEngine") -> None:
        dealt = target.receive_damage(user.attack_power + self.flat_bonus)
        engine.record(user.name, self.name, f"damage={dealt};target={target.name}")


class FireballSkill(Skill):
    def __init__(
        self,
        name: str = "Fireball",
        base_damage: int = 6,
        burn_duration: int = 2,
        burn_damage: int = 2,
    ) -> None:
        super().__init__(name, mana_cost=4)
        self.base_damage = base_damage
        self.burn_duration = burn_duration
        self.burn_damage = burn_damage

    def use(self, user: "Combatant", target: "Combatant", engine: "BattleEngine") -> None:
        user.spend_mana(self.mana_cost)
        dealt = target.receive_damage(self.base_damage + user.attack_power // 2)
        target.add_status(BurnEffect(self.burn_duration, self.burn_damage))
        engine.record(
            user.name,
            self.name,
            f"damage={dealt};burn={self.burn_damage}/{self.burn_duration};target={target.name}",
        )


class GuardSkill(Skill):
    def __init__(self, name: str = "Guard", defense_boost: int = 3, duration: int = 2) -> None:
        super().__init__(name, mana_cost=2)
        self.defense_boost = defense_boost
        self.duration = duration

    def use(self, user: "Combatant", target: "Combatant", engine: "BattleEngine") -> None:
        user.spend_mana(self.mana_cost)
        user.add_status(ShieldEffect(self.duration, self.defense_boost))
        engine.record(user.name, self.name, f"shield={self.defense_boost};turns={self.duration}")


class HealSkill(Skill):
    def __init__(self, name: str = "Heal", amount: int = 6) -> None:
        super().__init__(name, mana_cost=3)
        self.amount = amount

    def can_use(self, user: "Combatant", target: "Combatant") -> bool:
        return super().can_use(user, target) and user.current_hp < user.max_hp

    def use(self, user: "Combatant", target: "Combatant", engine: "BattleEngine") -> None:
        user.spend_mana(self.mana_cost)
        healed = user.heal(self.amount + user.attack_power // 3)
        engine.record(user.name, self.name, f"healed={healed}")


class RallySkill(Skill):
    def __init__(self, name: str = "Rally", attack_boost: int = 2, mana_regen_bonus: int = 1, duration: int = 2) -> None:
        super().__init__(name, mana_cost=2)
        self.attack_boost = attack_boost
        self.mana_regen_bonus = mana_regen_bonus
        self.duration = duration

    def use(self, user: "Combatant", target: "Combatant", engine: "BattleEngine") -> None:
        user.spend_mana(self.mana_cost)
        user.add_status(FocusEffect(self.duration, self.attack_boost, self.mana_regen_bonus))
        engine.record(
            user.name,
            self.name,
            f"focus={self.attack_boost};regen={self.mana_regen_bonus};turns={self.duration}",
        )


class Combatant(ABC):
    def __init__(self, name: str, max_hp: int, base_attack: int, base_defense: int, max_mana: int = 0) -> None:
        self.name = name
        self._max_hp = max_hp
        self._base_attack = base_attack
        self._base_defense = base_defense
        self._base_max_mana = max_mana
        self._current_hp = max_hp
        self._mana = max_mana
        self._equipment: list[Equipment] = []
        self._skills: list[Skill] = []
        self._statuses: list[StatusEffect] = []

    @property
    def max_hp(self) -> int:
        return self._max_hp

    @property
    def current_hp(self) -> int:
        return self._current_hp

    @property
    def max_mana(self) -> int:
        return self._base_max_mana + sum(item.mana_bonus for item in self._equipment)

    @property
    def mana(self) -> int:
        return self._mana

    @property
    def alive(self) -> bool:
        return self._current_hp > 0

    @property
    def attack_power(self) -> int:
        return self._base_attack + sum(item.attack_bonus for item in self._equipment) + sum(
            effect.attack_bonus() for effect in self._statuses
        )

    @property
    def defense_power(self) -> int:
        return self._base_defense + sum(item.defense_bonus for item in self._equipment) + sum(
            effect.defense_bonus() for effect in self._statuses
        )

    @property
    def statuses(self) -> tuple[StatusEffect, ...]:
        return tuple(self._statuses)

    def equip(self, item: Equipment) -> None:
        self._equipment.append(item)
        self._mana = self.max_mana

    def learn_skill(self, skill: Skill) -> None:
        self._skills.append(skill)

    def has_status(self, name: str) -> bool:
        normalized = name.strip().lower()
        return any(effect.name == normalized and effect.active for effect in self._statuses)

    def add_status(self, effect: StatusEffect) -> None:
        for index, current in enumerate(self._statuses):
            if current.name == effect.name:
                self._statuses[index] = effect.clone()
                return
        self._statuses.append(effect.clone())

    def receive_damage(self, amount: int, ignore_defense: bool = False) -> int:
        mitigated = amount if ignore_defense else amount - self.defense_power
        dealt = max(1, mitigated)
        self._current_hp = max(0, self._current_hp - dealt)
        return dealt

    def heal(self, amount: int) -> int:
        healed = min(amount, self.max_hp - self._current_hp)
        self._current_hp += healed
        return healed

    def spend_mana(self, amount: int) -> bool:
        if self._mana < amount:
            return False
        self._mana -= amount
        return True

    def restore_mana(self, amount: int) -> int:
        before = self._mana
        self._mana = min(self.max_mana, self._mana + amount)
        return self._mana - before

    def start_turn(self, engine: "BattleEngine") -> None:
        regen = 1 + sum(effect.mana_regen() for effect in self._statuses)
        self.restore_mana(regen)
        for effect in list(self._statuses):
            effect.on_turn_start(self, engine)

    def end_turn(self, engine: "BattleEngine") -> None:
        remaining: list[StatusEffect] = []
        for effect in self._statuses:
            effect.advance()
            if effect.active:
                remaining.append(effect)
            else:
                engine.record(self.name, "status-expired", effect.name)
        self._statuses = remaining

    def take_turn(self, opponent: "Combatant", engine: "BattleEngine") -> None:
        if not self.alive:
            return
        self.start_turn(engine)
        if not self.alive:
            return

        skill = self.choose_skill(opponent)
        if skill is None:
            engine.record(self.name, "wait", "no-usable-skill")
        else:
            skill.use(self, opponent, engine)

        self.end_turn(engine)

    def first_usable(self) -> Skill | None:
        for skill in self._skills:
            if skill.can_use(self, self):
                return skill
        return None

    @abstractmethod
    def choose_skill(self, opponent: "Combatant") -> Skill | None:
        raise NotImplementedError


class Hero(Combatant):
    def choose_skill(self, opponent: "Combatant") -> Skill | None:
        for skill in self._skills:
            if isinstance(skill, RallySkill) and not self.has_status("focus") and skill.can_use(self, opponent):
                return skill

        for skill in self._skills:
            if isinstance(skill, HealSkill) and self.current_hp <= self.max_hp // 2 and skill.can_use(self, opponent):
                return skill

        for skill in self._skills:
            if isinstance(skill, FireballSkill) and not opponent.has_status("burn") and skill.can_use(self, opponent):
                return skill

        for skill in self._skills:
            if isinstance(skill, SlashSkill) and skill.can_use(self, opponent):
                return skill

        return self.first_usable()


class Monster(Combatant):
    def choose_skill(self, opponent: "Combatant") -> Skill | None:
        for skill in self._skills:
            if isinstance(skill, GuardSkill) and self.current_hp <= (self.max_hp * 2) // 3 and not self.has_status("shield") and skill.can_use(self, opponent):
                return skill

        for skill in self._skills:
            if isinstance(skill, SlashSkill) and skill.can_use(self, opponent):
                return skill

        return self.first_usable()


class BattleEngine:
    def __init__(self, hero: Combatant, monster: Combatant) -> None:
        self.hero = hero
        self.monster = monster
        self.current_round = 0
        self._logs: list[CombatLogEntry] = []

    @property
    def logs(self) -> tuple[CombatLogEntry, ...]:
        return tuple(self._logs)

    def record(self, actor: str, action: str, detail: str) -> None:
        self._logs.append(CombatLogEntry(self.current_round, actor, action, detail))

    def run(self, max_rounds: int = 5) -> BattleResult:
        for round_number in range(1, max_rounds + 1):
            self.current_round = round_number
            if self.hero.alive:
                self.hero.take_turn(self.monster, self)
            if self.monster.alive:
                self.monster.take_turn(self.hero, self)
            if not self.hero.alive or not self.monster.alive:
                break

        if self.hero.alive and not self.monster.alive:
            winner = self.hero.name
        elif self.monster.alive and not self.hero.alive:
            winner = self.monster.name
        else:
            winner = "draw"

        return BattleResult(winner, self.current_round, self.logs)
