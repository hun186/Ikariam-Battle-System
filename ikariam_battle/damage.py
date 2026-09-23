from __future__ import annotations

from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from enum import Enum

from .units import UnitDefinition


class RoundingPolicy(str, Enum):
    FLOOR = "floor"
    NEAREST = "nearest"


def integer_damage(attacker: UnitDefinition, target: UnitDefinition, attack_upgrade: int = 0,
                   defense_upgrade: int = 0, attacker_hephaistos: bool = False,
                   defender_hephaistos: bool = False, rounding: RoundingPolicy = RoundingPolicy.FLOOR) -> int:
    attack = Decimal(attacker.base_attack + attack_upgrade * attacker.attack_upgrade_per_level)
    if attacker_hephaistos:
        attack *= Decimal("1.2")
    armor = Decimal(target.base_armor + defense_upgrade * target.armor_upgrade_per_level + (2 if defender_hephaistos else 0))
    value = max(Decimal(0), attack - armor)
    mode = ROUND_FLOOR if rounding is RoundingPolicy.FLOOR else ROUND_HALF_UP
    return int(value.quantize(Decimal("1"), rounding=mode))
