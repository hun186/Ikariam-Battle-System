from __future__ import annotations

from .units import UnitDefinition, Weapon


class UnsupportedWeaponSelection(ValueError):
    """The active weapon depends on a mechanic the engine does not know."""


def select_active_weapon(unit: UnitDefinition, runtime_line: str) -> Weapon:
    """Select a weapon without inferring secondary-weapon trigger behavior.

    Native-line combat retains the established primary-weapon behavior. A
    non-native Light Infantry unit in the first line is also deterministic
    when its registry profile contains exactly one weapon. Official naval Help
    additionally makes the exhausted Long-Range -> Front transition known; in
    that runtime line the registry's second (hull/close-combat) weapon is used.
    Other fallback cases remain unsupported until evidence-backed.
    """
    if runtime_line == unit.native_line:
        return unit.primary_weapon
    if unit.semantic_class == "light_infantry" and runtime_line == "first" and len(unit.weapons) == 1:
        return unit.weapons[0]
    if (
        unit.domain == "naval"
        and unit.semantic_class == "long_range"
        and runtime_line == "first"
        and len(unit.weapons) == 2
    ):
        # Official Naval Battlefield Help says Long-Range Battleships with no
        # munition can replace the Front Line. Their non-primary hull weapon is
        # therefore the only executable weapon in that runtime formation.
        return unit.weapons[1]
    raise UnsupportedWeaponSelection(
        f"active weapon is unknown for {unit.id} in non-native runtime line {runtime_line}"
    )
