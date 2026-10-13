"""User empirical naval records and controlled model arithmetic must be distinct."""
import json

from tools.research.naval_ram_empirical_probe import CASE, net_damage_math


def test_empirical_workbook_records_the_defense_14_to_15_jump():
    case = json.loads(CASE.read_text(encoding="utf-8"))
    observed = case["observed"]
    series = observed["player_deaths_total_by_defense_upgrade"]
    assert all(series[str(level)] == 6 for level in range(3, 15))
    assert all(series[str(level)] == 0 for level in range(15, 20))
    assert observed["direct_conversation_case"] == {
        "player_attack_upgrade": 20,
        "player_defense_upgrade": 19,
        "player_total_deaths": 0,
        "player_remaining_hp_bar_percent": 63,
        "barbarian_deaths_per_flank_position": 3,
        "barbarian_remaining_hp_bar_percent": 88,
        "note": (
            "Level-19 death and both health bars explicitly stated in chat, "
            "not entered in Excel sheet F20"
        ),
    }


def test_three_hits_to_kill_stays_constant_at_observed_death_jump():
    a = net_damage_math(14)
    b = net_damage_math(15)
    assert (a["barbarian_net_hit"], b["barbarian_net_hit"]) == (1160, 1150)
    assert (a["hits_to_kill_player"], b["hits_to_kill_player"]) == (3, 3)


def test_defense_19_and_attack_20_health_bar_arithmetic():
    case = net_damage_math(19)
    assert case["barbarian_net_hit"] == 1110
    assert case["player_net_hit_attack_20"] == 1715
    assert 63 < case["player_hp_pct_after_one_independent_hit"] < 64
    assert 88 < case["barbarian_hp_pct_if_three_die_and_all_six_hits_conserved"] < 89
    # The formula's apparent bar match is an unvalidated hypothesis, not a game result.


def test_observation_source_warns_controlled_simulation_is_not_same_battle():
    case = json.loads(CASE.read_text(encoding="utf-8"))
    assert case["controlled_scenario_assumptions"]["not_observed_exact_original_battle_configuration"]
    assert case["source"]["worksheet"] == "野撞打開爐衝撞"
    assert case["observed"]["player_forge_level"] == 5
    assert case["observed"]["barbarian_forge_level"] == 0
