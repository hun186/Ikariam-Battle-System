from __future__ import annotations

from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from enum import Enum

from .profiles import ForgeProfile, WorkshopProfile
from .units import UnitDefinition, Weapon


class RoundingPolicy(str, Enum):
    FLOOR = "EXP-ROUND-FLOOR-001"
    NEAREST = "test-nearest"


@dataclass(frozen=True)
class DamageTrace:
    weapon_id: str
    weapon_trigger: str
    base_damage: int
    workshop_attack_level: int
    workshop_damage_bonus: int
    pre_forge_damage: int
    forge_level: int
    forge_damage_multiplier: str
    post_forge_damage: str
    target_base_armor: int
    target_workshop_armor_level: int
    target_workshop_armor_bonus: int
    target_forge_armor_bonus: int
    net_damage_before_rounding: str
    rounding_policy: str
    final_damage: int

    def as_dict(self) -> dict: return asdict(self)


def calculate_damage(attacker: UnitDefinition, target: UnitDefinition, attack_level: int, armor_level: int,
                     attacker_forge: int, defender_forge: int, workshop: WorkshopProfile,
                     forge: ForgeProfile, rounding: RoundingPolicy, *, weapon: Weapon | None = None) -> DamageTrace:
    if not attacker.numerically_supported or target.base_armor is None:
        raise ValueError("damage requires verified numerical fields")
    selected = attacker.primary_weapon if weapon is None else weapon
    base = selected.damage
    assert base is not None
    workshop_damage = workshop.bonus(attacker.domain, attack_level)
    pre_forge = base + workshop_damage
    attack_effect, defense_effect = forge.effect(attacker_forge), forge.effect(defender_forge)
    post_forge = Decimal(pre_forge) * attack_effect.damage_multiplier
    workshop_armor = workshop.bonus(target.domain, armor_level)
    net = max(Decimal(0), post_forge - Decimal(target.base_armor + workshop_armor + defense_effect.armor_bonus))
    mode = ROUND_FLOOR if rounding is RoundingPolicy.FLOOR else ROUND_HALF_UP
    final = int(net.quantize(Decimal("1"), rounding=mode))
    return DamageTrace(selected.id, selected.trigger, base, attack_level, workshop_damage, pre_forge, attacker_forge,
                       str(attack_effect.damage_multiplier), str(post_forge), target.base_armor,
                       armor_level, workshop_armor, defense_effect.armor_bonus, str(net), rounding.value, final)
