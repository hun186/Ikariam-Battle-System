from ikariam_battle.battlefield import SMALL_LAND, deploy
from ikariam_battle.models import Army
from ikariam_battle.units import UnitRegistry


def army(rows):
    return Army.from_dict({'units': rows, 'workshop': {'attack_level': 12, 'armor_level': 12}, 'forge_level': 0})


def test_physical_layout_is_distinct_from_damage_and_deployment_priority():
    line = SMALL_LAND.lines['first']
    assert line.physical_order == (2, 1, 3)
    assert line.damage_priority == (1, 2, 3)
    assert line.physical_position(1) == 2


def test_first_deployment_is_center_damage_position_one():
    wave = deploy(army([{'unit_id':'hoplite','quantity':1}]), UnitRegistry.load(), SMALL_LAND)[0]
    assert wave.slots[0].damage_position == 1
    assert wave.slots[0].physical_position == 2


def test_duplicate_same_wave_rows_normalize_before_deployment():
    one = army([{'unit_id':'hoplite','quantity':60,'wave_id':'w'}])
    split = army([{'unit_id':'hoplite','quantity':30,'wave_id':'w'}, {'unit_id':'hoplite','quantity':30,'wave_id':'w'}])
    assert one == split
    assert [(s.damage_position,s.units) for s in deploy(one,UnitRegistry.load(),SMALL_LAND)[0].slots] == [(1,30),(2,30)]
