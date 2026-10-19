"""Preserve observed per-round kills independently of synthetic AM shot addresses."""
from tools.research.land_round80_89_am_focus_probe import (
    build_report, model_am_addressed_shots_by_physical_slot,
)


def test_current_engine_land_max_AM_row_addressing_is_independent_control():
    all_slots = model_am_addressed_shots_by_physical_slot(
        [1,2,3,4,5,6,7],[12]*7
    )
    assert [all_slots[i] for i in range(1,8)] == [7,14,14,14,14,14,7]
    six = model_am_addressed_shots_by_physical_slot(
        [1,2,3,4,5,6],[12]*7
    )
    four = model_am_addressed_shots_by_physical_slot(
        [2,3,4,5],[12]*7
    )
    assert [six[i] for i in range(1,7)] == [14]*6
    assert [four[i] for i in range(2,6)] == [21]*4
    assert sum(all_slots.values()) == sum(six.values()) == sum(four.values()) == 84


def test_r81_to83_exactly_identical_death_pattern_not_proven_shot_targets():
    data = build_report()
    r = {x["round"]:x for x in data["game_round_comparisons"]}
    for rnd in (81,82,83):
        observed = r[rnd]["user_verified_visible_deaths_by_physical_position"]
        residual = r[rnd][
            "observed_deaths_minus_modeled_AM_addressed_shots_NOT_EXTRA_ATTACK_COUNT"
        ]
        assert list(observed.values()) == [8,15,15,8,15,15,8]
        assert list(residual.values()) == [1,1,1,-6,1,1,1]
        assert sum(residual.values()) == 0
        assert r[rnd]["modeled_total_shots"] == 84


def test_surviving_targets_shrink_but_loss_total_stays_at_91():
    rows = {x["round"]:x for x in build_report()["game_round_comparisons"]}
    r88, r89=rows[88],rows[89]
    assert r88["modeled_target_first_line_occupied_physical_positions"] == [1,2,3,4,5,6]
    assert r89["modeled_target_first_line_occupied_physical_positions"] == [2,3,4,5]
    assert list(r88["modeled_AM_addressed_shots_by_physical_position"].values()) == [14]*6
    assert list(r89["modeled_AM_addressed_shots_by_physical_position"].values()) == [21]*4
    assert list(r88["user_verified_visible_deaths_by_physical_position"].values()) == [16,15,15,15,15,15]
    assert list(r89["user_verified_visible_deaths_by_physical_position"].values()) == [25,22,22,22]
    assert list(r88["observed_deaths_minus_modeled_AM_addressed_shots_NOT_EXTRA_ATTACK_COUNT"].values()) == [2,1,1,1,1,1]
    assert list(r89["observed_deaths_minus_modeled_AM_addressed_shots_NOT_EXTRA_ATTACK_COUNT"].values()) == [4,1,1,1]
    assert r88["user_verified_total_deaths"] == r89["user_verified_total_deaths"] == 91
    assert r88["observed_total_deaths_minus_84_shots_NOT_PROOF_OF_OTHER_WEAPON"] == 7
    assert r89["observed_total_deaths_minus_84_shots_NOT_PROOF_OF_OTHER_WEAPON"] == 7


def test_no_unobserved_mechanism_promoted_into_a_verified_rule():
    report = build_report()
    controls = report["controls"]
    assert controls["source_ammunition_sufficiency_unverified"] is True
    assert controls["other_sources_and_wall_attack_unverified"] is True
    assert controls["comparison_is_hit_addresses_vs_casualties_not_equivalent"]
    assert report["source"]["user_confirmed_at_followup"] is True
    assert report["source"]["screenshot_binary_present_in_repository"] is False
    assert all(item["status"] != "verified"
               for item in report["candidate_explanations_not_established"])
    assert all("Do not interpret differences as proven" in x["source_provenance_warning"]
               for x in report["game_round_comparisons"])
