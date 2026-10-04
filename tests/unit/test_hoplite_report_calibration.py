import json
from importlib.resources import files

from ikariam_battle.attacking_matrix import from_slot_counts
from ikariam_battle.damage import RoundingPolicy, calculate_damage
from ikariam_battle.profiles import ForgeProfile, WorkshopProfile
from ikariam_battle.units import UnitRegistry


PHYSICAL_FIRST = (6, 4, 2, 1, 3, 5, 7)


def _evidence():
    return json.loads(
        files("ikariam_battle.data.calibration")
        .joinpath("hoplite-mortar-carabineer-user-observation-2026-06-25.json")
        .read_text(encoding="utf-8")
    )


def test_2026_06_25_mortar_phase_has_exact_one_shot_am_baseline():
    evidence = _evidence()
    trace = from_slot_counts([6, 6, 6, 6, 6], list(range(1, 8)))
    assert list(trace.row_populations) == [5, 5, 5, 5, 5, 5]
    assert trace.hits_by_damage_position == {1:5,2:5,3:5,4:5,5:5,6:5,7:0}
    assert trace.physical_vector(PHYSICAL_FIRST) == [5,5,5,5,5,5,0]
    assert evidence["exact_phase_baseline"]["hits_physical_left_to_right"] == [5,5,5,5,5,5,0]

    registry = UnitRegistry.load()
    workshop = WorkshopProfile.load()
    forge = ForgeProfile.load()
    mortar = registry.get("mortar")
    hoplite = registry.get("hoplite")
    vs_defender = calculate_damage(
        mortar, hoplite, 0, 18, 5, 5, workshop, forge, RoundingPolicy.FLOOR
    )
    vs_attacker = calculate_damage(
        mortar, hoplite, 0, 21, 5, 5, workshop, forge, RoundingPolicy.FLOOR
    )
    assert vs_defender.final_damage >= hoplite.hit_points
    assert vs_attacker.final_damage >= hoplite.hit_points


def test_2026_06_25_full_carabineer_am_and_working_hit_damage_are_locked():
    evidence = _evidence()
    trace = from_slot_counts([12] * 7, list(range(1, 8)))
    assert trace.physical_vector(PHYSICAL_FIRST) == [7,14,14,14,14,14,7]

    registry = UnitRegistry.load()
    workshop = WorkshopProfile.load()
    forge = ForgeProfile.load()
    carabineer = registry.get("sulphur_carabineer")
    hoplite = registry.get("hoplite")
    attacker = calculate_damage(
        carabineer, hoplite, 16, 18, 5, 5, workshop, forge, RoundingPolicy.FLOOR
    )
    defender = calculate_damage(
        carabineer, hoplite, 10, 21, 5, 5, workshop, forge, RoundingPolicy.FLOOR
    )
    assert attacker.final_damage == 629
    assert defender.final_damage == 579
    assert evidence["following_carabineer_am"]["forge5_working_hit_damage"] == {
        "attacker_carabineer16_to_defender_hoplite18": 629,
        "defender_carabineer10_to_attacker_hoplite21": 579,
    }
