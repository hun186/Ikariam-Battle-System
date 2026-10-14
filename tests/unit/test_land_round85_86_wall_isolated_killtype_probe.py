"""Research-only R85->86 wall-separated slot-pool vs individual-kill bounds.

No test asserts a recovered Gameforge dispatch algorithm or wall targets.
"""
import pytest

from tools.research.land_round85_86_wall_isolated_killtype_probe import (
    minimum_prior_wounds_for_individual_direct_kills,
    report,
    separated_wall_and_pooled_guns,
)


def test_source_and_confirmed_forge5_are_preserved():
    data=report()
    assert data["owner_confirmed"] == {
        "forge":5,"R85_center_axes":11,"R85_bar":92,
        "R86_center_axe_deaths":6,"R86_center_axes":5,"R86_bar":96,
    }
    assert data["current_packaged_effective_gun_damage_to_axe"] == 710
    assert data["hypothetical_R85_total_survivor_wounds_range"] == [863,985]
    assert data["hypothetical_R86_total_survivor_wounds_range"] == [169,224]


def test_restricted_seven_single_target_hits_one_wall_cannot_kill_six_from_92pct():
    data=report()
    rows={r["hypothetical_wall_kills"]:r for r in data[
        "individual_D_kill_with_seven_hits_wall_kill_controls"
    ]}
    assert [rows[i]["gun_kills_required"] for i in range(4)] == [6,5,4,3]
    assert [rows[i]["minimum_preinjured_one_hit_victims"] for i in range(4)] == [5,3,1,0]
    assert [rows[i]["minimum_preexisting_aggregate_wounds"] for i in range(4)] == [2050,1230,410,0]
    assert [rows[i]["compatible_with_R85_floor_mean_wound_budget_IF_unchanged_population"] for i in range(4)] == [False,False,True,True]
    assert data["restricted_D_kill_one_wall_seven_guns_INCOMPATIBLE_with_92pct_IF_no_wound_inflow"]


def test_isolated_wall_not_added_as_damage_pool_and_pool_witness_matches_source():
    result=separated_wall_and_pooled_guns(
        starting_units=11,unit_hp=1120,starting_wounds=900,
        direct_wall_kills=1,wounds_removed_with_wall_victims=70,
        gun_hits=7,gun_full_hit_damage=710,
    )
    assert result["wall_wound_damage_added_to_gun_pool"] == 0
    assert result["previous_wounds_removed_with_wall_victims"] == 70
    assert result["gun_kills"] == 5
    assert result["all_casualties"] == 6
    assert result["survivors"] == 5
    assert result["survivor_wounds"] == 200
    assert result["floor_survivor_mean_bar"] == 96
    assert not result["official_game_mechanism_verified"]


def test_damage_pool_is_NOT_deemed_PDF_indirect_kill_or_proven_cross_slot():
    result=report()
    assert "NOT proof of I-kill" in result["paper_caveats"]["I_kill"]
    assert "one-shot one-target" in result["paper_caveats"]["1_kill"]
    assert "several attacks" in result["paper_caveats"]["D_kill"]
    assert "exact algorithm open" in result["paper_caveats"]["cross_slot"]
    assert result["floor_survivor_mean_bar_UNVERIFIED"]
    assert any("Accuracy" in line for line in result[
        "candidate_switch_features_not_proven_conditions"
    ])
    assert "Leftmost 7 additional Knife deaths are a separate AM / cross-slot puzzle" in result["unknowns"]


def test_forge_level_sensitivity_demonstrates_possible_new_hit_threshold():
    d=report()
    lv={r["forge_level_comparator"]:r for r in d[
        "comparison_by_forge_level_IN_SAME_HYPOTHETICAL_POOL"
    ]}
    assert d["aggregate_hit_damage_threshold_for_five_gun_kills"] == 682
    assert [lv[i]["damage_to_axe"] for i in range(6)] == [615,662,662,678,694,710]
    assert [lv[i]["gun_kills_in_same_hypothetical_pool"] for i in range(6)] == [4,4,4,4,5,5]
    assert lv[5]["historically_real_forge"] and all(
        not lv[i]["historically_real_forge"] for i in range(5)
    )
    assert lv[5]["result_bar_if_five_survive"] == 96


def test_input_guards_on_impossible_pool_and_one_hit_bounds():
    with pytest.raises(ValueError):
        separated_wall_and_pooled_guns(
            starting_units=11,unit_hp=1120,starting_wounds=900,
            direct_wall_kills=0,wounds_removed_with_wall_victims=70,
            gun_hits=7,gun_full_hit_damage=710,
        )
    with pytest.raises(ValueError):
        minimum_prior_wounds_for_individual_direct_kills(
            gun_hits=7,gun_kills=5,unit_hp=1120,full_hit_damage=1120
        )
