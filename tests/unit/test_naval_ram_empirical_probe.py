"""Keep user-supplied naval casualties distinct from conditional micro-models."""
import json

from ikariam_battle.battlefield import NAVAL_BATTLEFIELDS
from ikariam_battle.damage import RoundingPolicy, calculate_damage
from ikariam_battle.profiles import ForgeProfile, WorkshopProfile
from ikariam_battle.units import UnitRegistry
from tools.research.naval_ram_empirical_probe import (
    CASE, build_report, microprobe_six_hits, net_damage_math,
)


def test_workbook_defense_series_and_chat_observations_are_distinct():
    case = json.loads(CASE.read_text(encoding="utf-8"))
    observed = case["observed"]
    series = observed["player_deaths_total_by_defense_upgrade"]
    assert set(series) == {str(i) for i in range(3, 19)}
    assert all(series[str(level)] == 6 for level in range(3, 15))
    assert all(series[str(level)] == 0 for level in range(15, 19))
    assert "19" not in series
    assert case["source"]["actual_series_range"] == "F4:F19"
    assert observed["direct_conversation_case"]["player_defense_upgrade"] == 19
    assert observed["direct_conversation_case"]["player_total_deaths"] == 0
    assert observed["direct_conversation_case"]["player_remaining_hp_bar_percent"] == 63
    assert observed["direct_conversation_case"]["barbarian_deaths_per_flank_position"] == 3
    assert observed["direct_conversation_case"]["barbarian_remaining_hp_bar_percent"] == 88
    assert observed["direct_conversation_case"]["source"].startswith("USER_CONVERSATION")
    slot_claims = observed["direct_chat_position_claims"]
    assert slot_claims["defense_upgrades_3_to_14_each_slot_deaths"] == 1
    assert slot_claims["defense_15_each_slot_deaths"] == 0
    assert not slot_claims["independently_telemetry_verified"]
    assert "not in Excel" in observed["direct_conversation_case"]["note"]


def test_three_hits_to_kill_is_constant_at_observed_defense_jump():
    a, b = net_damage_math(14), net_damage_math(15)
    assert (a["barbarian_net_hit"], b["barbarian_net_hit"]) == (1160, 1150)
    assert (a["hits_to_kill_player"], b["hits_to_kill_player"]) == (3, 3)
    assert a["source_profile_incoming"]["final_damage"] == a["barbarian_net_hit"]
    assert b["source_profile_incoming"]["target_workshop_armor_level"] == 15


def test_damage_is_derived_from_same_profile_and_production_calculator():
    registry = UnitRegistry.load(include_barbarians=True)
    ws, forge = WorkshopProfile.load(), ForgeProfile.load()
    player, enemy = registry.get("ram_ship"), registry.get("barbarian_deckwrecker")
    inc = calculate_damage(enemy, player, 0, 19, 0, 5, ws, forge, RoundingPolicy.FLOOR)
    out = calculate_damage(player, enemy, 20, 0, 5, 0, ws, forge, RoundingPolicy.FLOOR)
    snapshot = net_damage_math(19)
    assert snapshot["barbarian_net_hit"] == inc.final_damage == 1110
    assert snapshot["player_net_hit_attack_20"] == out.final_damage == 1715
    assert snapshot["player_hp"] == player.hit_points == 3080
    assert snapshot["barbarian_hp"] == enemy.hit_points == 3080
    assert snapshot["barbarian_accuracy"] == enemy.primary_weapon.accuracy
    assert snapshot["player_accuracy"] == player.primary_weapon.accuracy
    assert 63 < snapshot["player_hp_pct_after_one_independent_hit"] < 64
    assert 88 < snapshot["barbarian_hp_pct_if_three_die_and_all_six_hits_conserved"] < 89
    # The predicted visual bars are CONDITIONAL on assumed hit count and UI format.


def test_six_hit_microprobe_reads_profiles_and_discards_overkill():
    data = [
        microprobe_six_hits("barbarian_deckwrecker", "ram_ship", armor_upgrade=level, target_forge=5)
        for level in (14, 15, 19)
    ]
    assert [r["deaths"] for r in data] == [2, 2, 2]
    assert [r["surviving_units"] for r in data] == [4, 4, 4]
    assert [r["overkill_discarded"] for r in data] == [800, 740, 500]
    assert all(r["survivor_average_hp_pct"] == 100 for r in data)
    for model, level in zip(data, (14, 15, 19)):
        assert model["net_damage_per_hit"] == net_damage_math(level)["barbarian_net_hit"]
        assert model["damage_source"]["target_workshop_armor_level"] == level
        assert model["accuracy"] == net_damage_math(level)["barbarian_accuracy"]


def test_player_attack20_microprobe_mismatch_in_bar_display_is_not_a_game_claim():
    r = microprobe_six_hits(
        "ram_ship", "barbarian_deckwrecker", attack_upgrade=20, attacker_forge=5
    )
    assert r["deaths"] == 3
    assert r["surviving_units"] == 3
    assert r["overkill_discarded"] == 1050
    assert r["persistent_damage"] == 0
    assert r["survivor_average_hp_pct"] == 100
    assert r["net_damage_per_hit"] == net_damage_math(19)["player_net_hit_attack_20"]
    hp = r["unit_hp"]
    conditional_pct = 100 * (3 * hp - r["overkill_discarded"]) / (3 * hp)
    assert 88 < conditional_pct < 89


def test_current_max_help_geometry_and_controlled_formation_provenance():
    case = json.loads(CASE.read_text(encoding="utf-8"))
    assert case["controlled_scenario_assumptions"]["not_observed_exact_original_battle_configuration"]
    assert case["source"]["worksheet"] == "野撞打開爐衝撞"
    assert NAVAL_BATTLEFIELDS["naval-max"].lines["flank"].slot_space == 20
    assert NAVAL_BATTLEFIELDS["naval-max"].lines["second"].slot_space == 25
    report = build_report()
    assert len(report["current_model"]) == 3
    assert all(
        {slot["line"] for slot in model["initial_layout_by_side"]["defender"]} == {"first"}
        for model in report["current_model"]
    )
    # Actual user-described six flank positions were NOT reproduced by this
    # pure-Ram-only first-line fallback controlled model.
    # A separate synthetic 35 Steam Rams + 42 Barbarian Wedge Paddlers
    # fills both First formations while keeping 36 native Flank ships per side.
    # These front ships were NEVER identified as present in the real battle.
    matched = report["controlled_front_filled_model_not_real_battle"]
    assert len(matched) == 3
    for model in matched:
        assert model["synthetic_front_filled"]
        for side in ("attacker", "defender"):
            layout = model["initial_layout_by_side"][side]
            flank = [s for s in layout if s["line"] == "flank"]
            assert len(flank) == 6
            assert sorted(x["physical_position"] for x in flank) == [1, 2, 3, 4, 5, 6]
            assert [x["units"] for x in flank] == [6] * 6
        assert model["attacker_barbarian_deaths"] == 18
    # The scoped Experimental F(Accuracy,N) six-Ram pool now tracks the
    # owner's 14→15 death cliff, *not* an independently held-out case.
    assert [m["defender_player_deaths"] for m in matched] == [6, 0, 0]
    assert case["controlled_scenario_assumptions"][
        "synthetic_geometry_valid_front_fillers"
    ]["do_not_calibrate_casualties_as_real_battle"]
