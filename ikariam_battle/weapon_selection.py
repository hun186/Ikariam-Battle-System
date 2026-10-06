from __future__ import annotations

from .units import UnitDefinition, Weapon


class UnsupportedWeaponSelection(ValueError):
    """The active weapon depends on a mechanic the engine does not know."""


def select_active_weapon(unit: UnitDefinition, runtime_line: str) -> Weapon:
    """Select a weapon without inferring secondary-weapon trigger behavior.

    Native-line combat retains the established primary-weapon behavior. A
    non-native Light Infantry unit in the first line is also deterministic
    when its registry profile contains exactly one weapon. Exhausted Long-Range
    units promoted from Second to First use their registry secondary/close
    weapon; this is evidence-backed for land by the battle-system paper and for
    naval by official Help. Reactive secondary-weapon counterattacks while a
    unit remains in its native line are still separate and unsupported.
    """
    if runtime_line == unit.native_line:
        return unit.primary_weapon
    if unit.semantic_class == "light_infantry" and runtime_line == "first" and len(unit.weapons) == 1:
        return unit.weapons[0]
    if (
        unit.semantic_class == "long_range"
        and unit.native_line == "second"
        and runtime_line == "first"
        and len(unit.weapons) == 2
    ):
        # Exhausted Long-Range units promoted into First use their close/hull
        # weapon. Promotion itself is gated by round-start formation logic and
        # primary-ammo exhaustion; this selector only resolves the weapon after
        # the runtime line is already First.
        return unit.weapons[1]
    raise UnsupportedWeaponSelection(
        f"active weapon is unknown for {unit.id} in non-native runtime line {runtime_line}"
    )
