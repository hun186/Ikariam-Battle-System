import pytest

from ikariam_battle.units import UnitRegistry
from ikariam_battle.weapon_selection import UnsupportedWeaponSelection, select_active_weapon


def test_single_weapon_light_fallback_selects_only_weapon():
    swordsman = UnitRegistry.load().get("swordsman")
    assert select_active_weapon(swordsman, "first") is swordsman.primary_weapon


def test_native_multi_weapon_combat_keeps_primary_weapon():
    archer = UnitRegistry.load().get("archer")
    assert select_active_weapon(archer, "second") is archer.primary_weapon


def test_exhausted_land_long_range_first_uses_secondary_close_weapon():
    archer = UnitRegistry.load().get("archer")
    selected = select_active_weapon(archer, "first")
    assert selected is archer.weapons[1]
    assert selected.id == "secondary"


def test_unrelated_non_native_multi_weapon_selection_remains_unsupported():
    mortar = UnitRegistry.load().get("mortar")
    with pytest.raises(UnsupportedWeaponSelection):
        select_active_weapon(mortar, "first")
