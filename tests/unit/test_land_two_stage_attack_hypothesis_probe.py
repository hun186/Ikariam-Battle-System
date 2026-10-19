"""R81-87 conditional two-stage hypothesis only, no real Gameforge selector."""
import pytest

from tools.research.land_two_stage_attack_hypothesis_probe import two_stage_report


def test_owner_two_stage_independent_routing_and_damage_accounting():
    d=two_stage_report()
    rows=d["rounds"]
    assert d["stage_A_illustrative_threshold"]==25
    assert d["stage_A_threshold_experiment_not_established"]
    assert d["accepted_thresholds_restricted_to_switch_at_R84_for_fixed_W83_seed"]==[22,29]
    assert d["R1_mortar_then_musket_then_wall_order_owner_statement"]
    assert d["R81_to_R87_wall_phase_last_is_HYPOTHETICAL"]
    assert d["owner_has_not_independently_verified_late_round_wall_phase_last"]
    assert d["stage_B_selector_is_unverified"]
    assert d["baseline_am_physical"]==[7,14,14,14,14,14,7]
    assert [x["round"] for x in rows]==list(range(81,88))
    assert [x["starting_center_axes"] for x in rows]==[45,37,29,21,16,11,5]
    assert [x["stage_A_reroute_if_center_below_illustrative_threshold"] for x in rows]==[False]*3+[True]*4
    assert [x["stage_B_central_gun_address_count"] for x in rows]==[14]*3+[7]*4
    assert [x["stage_B_shots_divisible_by_fresh_Axe_hits_to_kill"] for x in rows]==[True]*3+[False]*4
    assert all(x["post_route_gun_AM_physical"]==[7,14,14,14,14,14,7] for x in rows[:3])
    assert all(x["post_route_gun_AM_physical"]==[14,14,14,7,14,14,7] for x in rows[3:])


def test_all_seven_rounds_death_vectors_fit_but_early_bars_not_reconstructed():
    d=two_stage_report()
    rows=d["rounds"]
    early=[8,15,15,8,15,15,8]
    late=[
        [15,15,15,5,15,15,8],
        [15,15,15,5,15,15,8],
        [15,15,15,6,15,15,8],
        [15,15,15,5,15,15,8],
    ]
    assert [x["predicted_all_frontline_casualties"] for x in rows]==[early]*3+late
    assert all(x["matches_all_frontline_casualties"] for x in rows)
    assert d["seven_round_deaths_all_match_under_both_stages"]
    assert [x["modeled_center_gun_Axe_kills"] for x in rows]==[7,7,7,4,4,5,4]
    assert [x["modeled_center_HP_bar_when_pooled"] for x in rows[:3]]==[None]*3
    assert [x["modeled_center_HP_bar_when_pooled"] for x in rows[3:]]==[97,92,96,0]
    assert d["r81_r83_hp_bar_not_reconstructed"]
    assert d["r84_r87_pooled_center_hp_all_match"]


def test_occupancy_threshold_25_is_nonunique_and_would_need_external_discriminator():
    # With observed start counts R83=29 and R84=21, ANY integer t in
    # 22..29 makes the same transition for condition center_count<t.
    for t in range(22,30):
        d=two_stage_report(illustrative_reroute_threshold=t)
        assert d["seven_round_deaths_all_match_under_both_stages"]
        assert d["r84_r87_pooled_center_hp_all_match"]
    with pytest.raises(ValueError, match="fixed R84-R87 wound witness"):
        two_stage_report(illustrative_reroute_threshold=20)
    with pytest.raises(ValueError):
        two_stage_report(illustrative_reroute_threshold=0)
    with pytest.raises(ValueError):
        two_stage_report(illustrative_reroute_threshold=51)
