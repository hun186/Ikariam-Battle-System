"""Falsifiable mathematical witness only, NOT a Gameforge engine rule."""
import pytest

from tools.research.land_round84_87_integer_slot_pool_probe import (
    compute_candidate, sensitivity_report,
)


def test_four_rounds_same_integer_rule_matches_deaths_and_bar_without_healing():
    data=compute_candidate()
    assert data["owner_confirmed_player_forge_level"]==5
    assert data["axe_hp"]==1120
    assert data["effective_gun_damage_to_axe"]==710
    assert data["baseline_project_AM_center_addresses"]==14
    assert data["baseline_AM_all_physical"]==[7,14,14,14,14,14,7]
    assert data["candidate_center_full_effective_hits"]==7
    assert data["seven_gun_hits_are_redirected_or_otherwise_reduced_UNVERIFIED"]
    assert not data["game_implementation_verified"]
    assert data["source_R83_bar_percent"]==99
    assert data["candidate_R83_living_slot_wounds"]==25
    assert data["candidate_R83_bar_percent"]==99
    rows=data["rounds"]
    assert [x["round"] for x in rows]==[84,85,86,87]
    assert [x["gun_kills_floor_HP"] for x in rows]==[4,4,5,4]
    assert [x["independent_direct_wall_kills_ASSUMED"] for x in rows]==[1]*4
    assert [x["gun_pool_residual_after_kills"] for x in rows]==[515,975,264,710]
    assert [x["old_wounds_removed_with_wall_victim"] for x in rows]==[30,81,44,710]
    assert [x["end_living_slot_wounds"] for x in rows]==[485,894,220,0]
    assert [x["modeled_end_axe_units"] for x in rows]==[16,11,5,0]
    assert [x["modeled_end_bar_floor_pct"] for x in rows]==[97,92,96,0]
    assert [x["source_casualties"] for x in rows]==[5,5,6,5]
    assert all(x["matches_source"] for x in rows)
    assert data["reproduces_R84_R87_count_and_HP"]


def test_all_compatible_integer_R83_wounds_and_witness_range():
    sensitivity=sensitivity_report()
    assert sensitivity["survivor_wounds_compatible_with_R83_99pct"]==[1,235]
    assert sensitivity["source_R83_21_axes_99pct_wound_candidates"]==235
    assert sensitivity["witness_interval_if_contiguous"]==[1,29]
    assert sensitivity["witness_wounds_matching_ALL_R84_R87"]==list(range(1,30))
    assert not compute_candidate(first_round_end_wounds=30)["reproduces_R84_R87_count_and_HP"]


def test_stand_alone_am_14_full_gun_hits_is_not_the_7_hit_witness():
    # Unchanged baseline AM addresses must not silently become 7 gun hits.
    d=compute_candidate()
    assert d["baseline_project_AM_center_addresses"]==14
    assert d["candidate_center_full_effective_hits"]==7
    # Under the same initial old wounds, if all 14 baseline addresses
    # deliver 710 FULL damage, R84 would already have 8 gun deaths,
    # and hypothetical one wall death, not source-observed 5.
    assert (25+14*710)//1120==8
    assert 21-8-1==12
    assert 12 != d["rounds"][0]["source_end_units"]


def test_requires_valid_integral_starting_hp_state_and_wall_one_kill():
    with pytest.raises(ValueError):
        compute_candidate(first_round_end_wounds=-1)
    with pytest.raises(ValueError):
        compute_candidate(first_round_end_wounds=21*1120+1)
    with pytest.raises(ValueError):
        compute_candidate(effective_center_gun_hits=-1)
