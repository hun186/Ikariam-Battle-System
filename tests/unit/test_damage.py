from ikariam_battle.damage import RoundingPolicy, integer_damage
from ikariam_battle.units import UnitRegistry


def test_documented_damage_without_hephaistos():
    # PDF pp. 15-16: (29 + 3) - (1 + 3) = 28.
    units = UnitRegistry.load()
    assert integer_damage(units.get("sulphur_carabineer"), units.get("hoplite"), 3, 3) == 28


def test_documented_hephaistos_floor_example():
    # PDF p. 16: ((29 + 3) * 1.2) - (1 + 3 + 2) = 32.4 -> 32.
    units = UnitRegistry.load()
    assert integer_damage(units.get("sulphur_carabineer"), units.get("hoplite"), 3, 3, True, True,
                          RoundingPolicy.FLOOR) == 32


def test_rounding_is_explicit_not_builtin_round():
    units = UnitRegistry.load()
    floor = integer_damage(units.get("sulphur_carabineer"), units.get("hoplite"), 3, 3, True, True,
                           RoundingPolicy.FLOOR)
    nearest = integer_damage(units.get("sulphur_carabineer"), units.get("hoplite"), 3, 3, True, True,
                             RoundingPolicy.NEAREST)
    assert (floor, nearest) == (32, 32)
