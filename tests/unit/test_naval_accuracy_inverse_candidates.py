"""Falsifiable, source-grounded naval individual-target research (not engine rules)."""
from math import ceil

from tools.research.naval_accuracy_inverse_candidates import (
    _air_cases,
    effective_focus_share_surrogate,
    predicted,
    report,
    select_target,
    simulate_slot,
)


def test_candidate_selector_is_integer_shots_not_magic_fraction_or_hit_miss():
    assert select_target([0, 0, 0], hp=2800, hit=250, threshold=74) == 2
    # Once the damaged ship has 250 damage, it has 91.07% HP and spreads.
    assert select_target([0, 0, 250], hp=2800, hit=250, threshold=74) == 1
    # After 3 hits of 250, HP=73.21%, so next one focuses.
    assert select_target([0, 0, 750], hp=2800, hit=250, threshold=74) == 2
    assert select_target([0, 0, 750], hp=2800, hit=250, threshold=None) == 1


def test_air_cases_come_only_from_source_fixtures_and_production_profiles():
    cases = _air_cases()
    assert len(cases) == 7
    assert sorted(c["weapon_accuracy"] for c in cases) == [90, 90, 90, 95, 95, 95, 95]
    assert {c["effective_hit"] for c in cases} == {180, 240, 250, 271, 310, 314, 326}
    assert sorted(c["observed_total_deaths"] for c in cases) == [0, 0, 1, 1, 2, 2, 2]
    assert all(c["source"] == "USER_CHAT" for c in cases)
    assert all(c["hp"] == 2800 and c["initial_units_per_target_slot"] == 3
               for c in cases)
    assert all(c["modeled_successful_hits_per_slot"] == [16, 14] for c in cases)


def test_cross_air_fixed_74_works_as_in_sample_hypothesis_not_game_rule():
    r = report()
    matches = r["candidate_74_percent_focus_threshold"]
    assert len(matches) == 7
    assert all(x["matches_reported_total"] for x in matches)
    by_name = {x["case_id"]: x for x in matches}
    assert [by_name[s]["candidate_deaths"] for s in (
        "barbarian_fast_vs_player_carrier_def7",
        "barbarian_fast_vs_player_carrier_def8",
        "barbarian_fast_vs_player_carrier_def14",
        "barbarian_fast_vs_player_carrier_def3_no_forge",
        "pvp_fast_att12_carrier_def8",
        "pvp_fast_att20_carrier_def16",
        "pvp_fast_att17_carrier_def18",
    )] == [1, 0, 0, 2, 2, 2, 1]
    assert [by_name[s]["model_slot_results"][0]["deaths"] for s in (
        "barbarian_fast_vs_player_carrier_def7",
        "barbarian_fast_vs_player_carrier_def8",
        "pvp_fast_att17_carrier_def18",
    )] == [1, 0, 1]
    assert r["conditional_inputs"][
        "testing_threshold_against_all_7_air_casualty_cases_is_IN_SAMPLE_FIT"
    ] is True
    assert r["evidence_class"] == "RESEARCH_ONLY_CANDIDATE_NOT_GAME_RULE"
    assert r["fitting_threshold_count_in_grid"] > 1


def test_fitting_thresholds_are_a_range_not_identification_of_exact_74():
    fitted = report()["fitting_percentage_point_interval_grid_0_01"]
    assert fitted is not None
    assert 73.20 < fitted[0] < 73.30
    assert 74.20 < fitted[1] < 74.30
    assert fitted[0] < 74 < fitted[1]
    # Source weapon accuracies remain 90 and 95, not equal to fitted threshold.
    assert all(x["threshold"] != 74 for x in report()[
        "current_accuracy_percentage_used_as_focus_threshold"
    ])


def test_current_accuracy_as_focus_threshold_is_not_a_seven_case_solution():
    current = report()["current_accuracy_percentage_used_as_focus_threshold"]
    assert sum(x["matches_reported_total"] for x in current) < 7
    by_name = {x["case_id"]: x for x in current}
    assert by_name["pvp_fast_att17_carrier_def18"]["candidate_deaths"] == 2
    assert by_name["pvp_fast_att17_carrier_def18"]["observed_total_deaths"] == 1
    assert by_name["barbarian_fast_vs_player_carrier_def7"]["candidate_deaths"] == 2
    assert by_name["barbarian_fast_vs_player_carrier_def7"]["observed_total_deaths"] == 1


def test_same_threshold_fails_ram_defense14_to15_with_six_hypothetical_hits():
    cases = report()["out_of_family_ram_six_hit_holdouts"]
    assert [(x["conditional_net_hit"], x["observed_player_deaths_per_reported_slot"],
             x["synthetic_six_hit_model_deaths"]) for x in cases] == [
        (1160, 1, 2),
        (1150, 0, 2),
        (1110, 0, 2),
    ]
    assert all(not x["matches_observed"] for x in cases)
    # Same integer hits-to-kill, so a damage-independent shot allocation is
    # incapable of causing the observed DEF14->DEF15 step.
    assert ceil(3080 / 1160) == ceil(3080 / 1150) == 3
    assert ceil(2800 / 250) == ceil(2800 / 240) == 12


def test_candidate_matches_defense14_65_70_bars_conditional_on_16_14_shots():
    case = next(x for x in report()["candidate_74_percent_focus_threshold"]
                if x["case_id"] == "barbarian_fast_vs_player_carrier_def14")
    assert [x["deaths"] for x in case["model_slot_results"]] == [0, 0]
    assert [int(x["surviving_hp_percent_no_carry"]) for x in case["model_slot_results"]] == [65, 70]
    assert case["observed_bars"] == [65, 70]


def test_reverse_53_65_bars_require_another_damage_budget_hypothesis():
    r = report()["reverse_player_fast_to_barbarian_carrier_bars"]
    assert r["net_hit"] == 337
    assert r["observed_deaths_per_slot"] == 1
    assert r["observed_hp_bars"] == [53, 65]
    assert r["model_deaths_per_slot"] == [1, 1]
    assert r["lost_overkill_by_slot"] == [233, 233]
    assert r["model_bars_discard_overkill"] == [57, 69]
    assert r["counterfactual_bars_if_discarded_overkill_reallocated"] == [53, 65]


def test_spread_only_and_focus_only_do_not_jointly_match_all_air_cases():
    cases = _air_cases()
    assert any(not predicted(c, None)["matches_reported_total"] for c in cases)
    assert any(not predicted(c, 100)["matches_reported_total"] for c in cases)
    # Distinct real plausible policies can yield same aggregates: 74 is not a
    # unique identification of Gameforge implementation.
    probe = simulate_slot(2800, 3, 16, 271, 74)
    assert probe["deaths"] == 1
    assert probe["overkill_discarded"] >= 0


def test_leave_one_case_out_exposes_which_battles_actually_identify_threshold():
    """No LOO test may be mistaken for new independent game observations."""
    result = report()
    loo = result["leave_one_reported_case_out"]
    assert len(loo) == 7
    assert result["leave_one_out_is_NOT_fully_independent_validation"]
    rows = {r["held_out_case"]: r for r in loo}
    defense7 = rows["barbarian_fast_vs_player_carrier_def7"]
    assert defense7["training_threshold_grid_range"] == [70.97, 74.28]
    assert defense7["held_out_candidate_deaths_possible"] == [0, 1]
    assert defense7["candidate_threshold_counts_by_held_out_prediction"] == {
        "0": 225, "1": 107
    }
    assert not defense7["all_training_fits_predict_correct_held_out"]
    defense8 = rows["barbarian_fast_vs_player_carrier_def8"]
    assert defense8["training_threshold_grid_range"] == [73.22, 80.64]
    assert defense8["held_out_candidate_deaths_possible"] == [0, 1]
    assert defense8["candidate_threshold_counts_by_held_out_prediction"] == {
        "0": 107, "1": 636
    }
    assert not defense8["all_training_fits_predict_correct_held_out"]
    for case in loo:
        assert case["evidence_class"] == (
            "RESEARCH_ONLY_LEAVE_ONE_CASE_OUT_NOT_INDEPENDENT_FIELD_TRIAL"
        )
        assert len(case["training_cases"]) == 6
        assert "NOT likelihoods" in case["important_caveat"]
    assert all(r["all_training_fits_predict_correct_held_out"]
               for r in loo if r["held_out_case"] not in (
                   "barbarian_fast_vs_player_carrier_def7",
                   "barbarian_fast_vs_player_carrier_def8",
               ))


def test_focus_interval_is_straddled_by_three_hit_hp_250_versus_240():
    """Parameter window is chiefly the observed Barbarian DEF7/8 cliff."""
    hp = 2800
    after_three_250 = 100 * (hp - 3 * 250) / hp
    after_three_240 = 100 * (hp - 3 * 240) / hp
    assert round(after_three_250, 4) == 73.2143
    assert round(after_three_240, 4) == 74.2857
    bounds = report()["fitting_percentage_point_interval_grid_0_01"]
    assert bounds == [73.22, 74.28]
    assert after_three_250 < bounds[0] < 74 < bounds[1] < after_three_240


def test_new_unseen_first_round_pvp_17_18_slot_health_predictions_are_explicitly_model_only():
    """Proposed falsification uses VISIBLE future bars, not hidden hit traces."""
    r = report()
    forecasts = {
        x["case_id"]: x for x in r[
            "unobserved_round1_slot_bar_predictions_research_only"
        ]
    }
    p = forecasts["pvp_fast_att17_carrier_def18"]
    assert p["predicted_slot_deaths_not_verified_by_game"] == [1, 0]
    assert p["predicted_floor_survivor_slot_bars_not_observed"] == [75, 54]
    assert p["predicted_surviving_individual_HP_not_game_shot_trace"] == [
        [2258, 1987], [2258, 2258, 90]
    ]
    assert "Source did not provide actual" in p["research_warning"]
    # The only carrier case with actual two-slot bars has its own
    # observed_bars source field and must NOT appear in unseen predictions.
    assert "barbarian_fast_vs_player_carrier_def14" not in forecasts
    assert len(forecasts) == 6


def test_old_A_N_focus_share_surrogate_crosses_all_known_first_kill_boundaries():
    """Cross-family numerical fit DOES NOT establish individual-hit targeting."""
    f95 = effective_focus_share_surrogate(95, 3)
    f90 = effective_focus_share_surrogate(90, 3)
    f80 = effective_focus_share_surrogate(80, 6)
    assert abs(f95 - 13 / 18) < 1e-12
    assert abs(f90 - 2 / 3) < 1e-12
    assert abs(f80 - 4 / 9) < 1e-12
    assert 2800 / (16*250) <= f95 < 2800 / (16*240)
    assert 3080 / (6*1160) <= f80 < 3080 / (6*1150)
    trials = report()["speculative_aggregate_F_surrogate_NOT_same_as_T"]
    assert trials["all_air_binary_totals_match"]
    assert trials["all_ram_binary_first_kills_match"]
    assert trials["speculative_intercept_60_not_verified"] is True
    assert trials["cannot_apply_fractional_budget_to_undivided_integer_shots"]
    assert len(trials["air_first_hull_binary_trials"]) == 7
    assert [(x["player_defense_level"],
             x["model_binary_first_kill_NOT_total_ship_losses"])
            for x in trials["ram_first_hull_binary_trials"]] == [
        (14,1),(15,0),(19,0)
    ]
    pvp = [
        x["model_binary_first_kills_per_slot_NOT_full_casualty_sim"]
        for x in trials["air_first_hull_binary_trials"]
        if x["case_id"].startswith("pvp_")
    ]
    assert pvp == [[1,1],[1,1],[1,0]]


def test_json_report_retains_all_fixture_provenance_not_just_user_chat_label():
    provenance = report()["fixture_provenance_including_unverified_source_limitations"]
    assert provenance["barbarian_and_reverse_air"]["source"][
        "original_battle_reports_attached"
    ] is False
    assert provenance["barbarian_and_reverse_air"]["candidate_unit_mapping_provisional"][
        "status"
    ].startswith("provisional")
    assert provenance["player_versus_player_air"]["source"][
        "original_battle_reports_attached"
    ] is False
    assert provenance["player_versus_player_air"]["model_controls"][
        "slots_derived_from_official_help_not_explicitly_reconfirmed_for_these_three_battles"
    ] is True
    assert provenance["player_versus_player_air"]["source"][
        "round_confirmation_source"
    ].startswith("USER_FOLLOWUP_CHAT")
    assert provenance["ram_and_deckwrecker"]["source"]
    assert provenance["ram_and_deckwrecker"]["controlled_scenario_assumptions"]
    assert len(provenance["barbarian_and_reverse_air"]["separate_extra_observations"]) == 1


def test_ram_F_surrogate_derives_all_inputs_from_fixture_and_profiles(monkeypatch):
    """Old P2: accuracy, slot size, observations cannot silently stay literals."""
    from copy import deepcopy
    from tools.research import naval_accuracy_inverse_candidates as inverse
    base=inverse._read(inverse.RAM_FIXTURE)
    normal=inverse.aggregate_focus_surrogate_trials(inverse._air_cases(),base)
    assert [(x["source_weapon_accuracy"],
             x["assumed_target_ships_per_slot"],
             x["synthetic_successful_hits_per_slot_not_game_trace"],
             x["user_reported_per_slot_deaths"])
            for x in normal["ram_first_hull_binary_trials"]] == [
        (80,6,6,1),(80,6,6,0),(80,6,6,0)
    ]

    changed=deepcopy(base)
    changed["observed"]["user_stated_ships_per_flank_position"]=7
    changed["observed"]["direct_chat_position_claims"][
        "defense_upgrades_3_to_14_each_slot_deaths"
    ]=0
    changed_out=inverse.aggregate_focus_surrogate_trials(inverse._air_cases(),changed)
    assert all(x["assumed_target_ships_per_slot"]==7
               for x in changed_out["ram_first_hull_binary_trials"])
    assert changed_out["ram_first_hull_binary_trials"][0][
        "user_reported_per_slot_deaths"
    ]==0
    assert changed_out["ram_first_hull_binary_trials"][0][
        "conditional_first_hull_concentrated_fraction"
    ] != normal["ram_first_hull_binary_trials"][0][
        "conditional_first_hull_concentrated_fraction"
    ]
    # Separate control: source-death mutation alone breaks the baseline fit;
    # mutating n=7 ALSO changes the model threshold, so those are independent.
    altered_outcomes=deepcopy(base)
    altered_outcomes["observed"]["direct_chat_position_claims"][
        "defense_upgrades_3_to_14_each_slot_deaths"
    ]=0
    observed_out=inverse.aggregate_focus_surrogate_trials(
        inverse._air_cases(),altered_outcomes
    )
    assert not observed_out["ram_first_hull_binary_trials"][0][
        "binary_first_kill_equals_source"
    ]

    original=inverse.net_damage_math
    def changed_profile(level):
        v=dict(original(level))
        v["barbarian_accuracy"]=90
        return v
    monkeypatch.setattr(inverse,"net_damage_math",changed_profile)
    changed_accuracy=inverse.aggregate_focus_surrogate_trials(inverse._air_cases(),base)
    assert all(x["source_weapon_accuracy"]==90
               for x in changed_accuracy["ram_first_hull_binary_trials"])
