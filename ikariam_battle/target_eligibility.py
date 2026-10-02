from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .damage import DamageTrace, RoundingPolicy, calculate_damage
from .profiles import ForgeProfile, WorkshopProfile
from .units import UnitDefinition, Weapon
from .wall import wall_stats


TARGET_PENETRATION_RULE_ID = "TARGET-PENETRATION-001"
WALL_ARTILLERY_PRIORITY_RULE_ID = "WALL-ARTILLERY-PRIORITY-001"


@dataclass(frozen=True)
class TargetEligibility:
    eligible: bool
    effective_attack: str
    effective_defense: int
    reason: str


def unit_target_eligibility(
    attacker: UnitDefinition,
    target: UnitDefinition,
    attack_upgrade: int,
    armor_upgrade: int,
    attacker_forge: int,
    defender_forge: int,
    workshop: WorkshopProfile,
    forge: ForgeProfile,
    *,
    weapon: Weapon,
) -> tuple[TargetEligibility, DamageTrace]:
    """Evaluate whether a weapon can penetrate a unit target.

    Observed combat semantics: a target whose effective DEF is greater than or
    equal to the attacker's effective ATK is not attacked. This is a target
    eligibility rule, not a zero-damage shot: no attack should be spent on that
    target, and target selection may continue to the next eligible candidate.
    """
    trace = calculate_damage(
        attacker,
        target,
        attack_upgrade,
        armor_upgrade,
        attacker_forge,
        defender_forge,
        workshop,
        forge,
        RoundingPolicy.FLOOR,
        weapon=weapon,
    )
    effective_attack = Decimal(trace.post_forge_damage)
    effective_defense = (
        trace.target_base_armor
        + trace.target_workshop_armor_bonus
        + trace.target_forge_armor_bonus
    )
    eligible = effective_attack > Decimal(effective_defense)
    return (
        TargetEligibility(
            eligible=eligible,
            effective_attack=str(effective_attack),
            effective_defense=effective_defense,
            reason="penetrates" if eligible else "effective_attack_not_above_defense",
        ),
        trace,
    )


def wall_target_eligibility(
    attacker: UnitDefinition,
    attack_upgrade: int,
    attacker_forge: int,
    wall_level: int,
    workshop: WorkshopProfile,
    forge: ForgeProfile,
    *,
    weapon: Weapon,
) -> TargetEligibility:
    """Evaluate the same penetration rule against one Town Wall section.

    This helper does not make wall combat executable. It is the arithmetic
    eligibility layer needed by the separately guarded wall-targeting model.
    """
    if weapon.damage is None:
        raise ValueError("weapon damage is required for wall eligibility")
    base = weapon.damage + workshop.bonus(attacker.domain, attack_upgrade)
    effective_attack = Decimal(base) * forge.effect(attacker_forge).damage_multiplier
    effective_defense = int(wall_stats(wall_level)["armor"] or 0)
    eligible = effective_attack > Decimal(effective_defense)
    return TargetEligibility(
        eligible=eligible,
        effective_attack=str(effective_attack),
        effective_defense=effective_defense,
        reason="penetrates" if eligible else "effective_attack_not_above_defense",
    )
