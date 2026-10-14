"""Owner-confirmed single land battle, two noncontiguous evidence windows.

A common battle_id proves provenance linkage only. Missing R2-R79 are NOT
fabricated, and no particular R1 individual wound is asserted to survive to
R80-R83 without intervening Gameforge hit/wave/HP state evidence.
"""
import json
from pathlib import Path

from tools.research.land_round1_full_axes_probe import report as early_report
from tools.research.land_round1_mortar_wall_gun_decomposition_probe import report as r1_source_report
from tools.research.land_two_stage_attack_hypothesis_probe import two_stage_report

_ROOT = Path(__file__).resolve().parents[2] / "tests/fixtures/reverse_engineering"


def test_early_and_late_windows_one_owner_confirmed_battle():
    early = json.loads((_ROOT/"land_barbarian_round1_full_axes_20261014.json").read_text(encoding="utf-8"))
    late = json.loads((_ROOT/"land_barbarian_rounds80_89_20261014.json").read_text(encoding="utf-8"))
    key = "land-barbarian-same-owner-battle-r1-r89-20261014"
    assert early["battle_identity"]["battle_id"] == late["battle_identity"]["battle_id"] == key
    assert early["battle_identity"]["owner_explicitly_confirmed_round1_and_round80_89_are_same_battle"]
    assert late["battle_identity"]["owner_explicitly_confirmed_round1_and_round80_89_are_same_battle"]
    assert early["battle_identity"]["complete_battle_rounds2_79_provided"] is False
    assert late["battle_identity"]["complete_battle_rounds2_79_provided"] is False
    assert early["battle_identity"]["battle_data_coverage"]["unavailable_intervening_rounds"] == [2, 79]
    assert late["battle_identity"]["battle_data_coverage"]["late_round_window"] == list(range(80, 90))
    assert [x["round"] for x in late["observations"]] == list(range(80, 90))
    assert early["transcribed_screenshot"]["round"] == 1


def test_probes_preserve_same_battle_identity_but_do_not_invent_hp_carryover():
    e=early_report()
    d=r1_source_report()
    late=two_stage_report()
    assert e["battle_identity"]["battle_id"] == d["battle_identity"]["battle_id"] == late["battle_identity"]["battle_id"]
    assert "SAME battle" in e["chronology"]
    assert "SAME BATTLE" in d["scope"]
    assert late["R1_source_and_R80_R89_are_one_continuous_battle"]
    assert late["rounds_2_to_79_unobserved"]
    assert late["r81_r83_hp_bar_not_reconstructed"]
    assert "R1 center was100%" in late["remaining_unknowns"][-1]


def test_round80_HP99_is_an_observation_not_a_recovered_round1_hp_history():
    late=json.loads((_ROOT/"land_barbarian_rounds80_89_20261014.json").read_text(encoding="utf-8"))
    early=json.loads((_ROOT/"land_barbarian_round1_full_axes_20261014.json").read_text(encoding="utf-8"))
    assert early["owner_confirmed"]["displayed_axe_front_survivor_HP_percent_physical_left_to_right"] == [98,100,100,100,100,100,99]
    assert late["observations"][0]["attacker_main_line_front_survivor_hp_percent_left_to_right"][3] == 99
    assert late["observations"][1]["attacker_main_line_front_survivor_hp_percent_left_to_right"][3] == 99
    assert late["source"]["unobserved_intervening_rounds_range"] == [2, 79]
