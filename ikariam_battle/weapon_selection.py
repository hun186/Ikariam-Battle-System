from __future__ import annotations

from .units import UnitDefinition, Weapon


class UnsupportedWeaponSelection(ValueError):
    """The active weapon depends on a mechanic the engine does not know."""


def select_active_weapon(unit: UnitDefinition, runtime_line: str) -> Weapon:
    """Select a weapon without inferring secondary-weapon trigger behavior.

    Native-line combat retains the established primary-weapon behavior. A
    non-native Light Infantry unit in the first line is also deterministic
    when its registry profile contains exactly one weapon. Other fallback
    cases remain unsupported until their trigger rules are evidence-backed.
    """
    if runtime_line == unit.native_line:
        return unit.primary_weapon
    if unit.semantic_class == "light_infantry" and runtime_line == "first" and len(unit.weapons) == 1:
        return unit.weapons[0]
    raise UnsupportedWeaponSelection(
        f"active weapon is unknown for {unit.id} in non-native runtime line {runtime_line}"
    )
