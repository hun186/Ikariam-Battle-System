"""Do NOT elevate the experimental accuracy/redirect models to game facts."""
from tools.research.land_cross_weapon_accuracy_am_reallocation_probe import (
    report,
)


def test_two_weapon_accuracy_and_fresh_axe_hits_to_kill_are_different():
    v=report()
    c=v["comparison"]
    assert v["case_provenance"]["same_battle"] is False
    assert (c["gun_primary_accuracy"],c["slinger_primary_accuracy"])==(70,20)
    assert (c["gun_Axe_damage"],c["slinger_Axe_damage"])==(710,187)
    assert (c["gun_full_Axe_hits_to_kill"],c["slinger_full_Axe_hits_to_kill"])==(2,6)
    assert (c["gun_Knife_damage"],c["slinger_Knife_damage"])==(730,207)
    assert (c["gun_full_Knife_hits_to_kill"],c["slinger_full_Knife_hits_to_kill"])==(1,2)
    assert c["experimental_focus_steps_before_remainingHP_below_accuracy"]["gun_vs_Axe"]==1
    assert c["experimental_focus_steps_before_remainingHP_below_accuracy"]["slinger_vs_Axe"]==5


def test_R77_source_HP_ranges_and_shot_address_competition():
    v=report()
    assert v["R77_standard_350_AM_physical"]==[49,49,49,56,49,49,49]
    rows=v["R77_slot_HP_bounds_fresh_full_floor_bar_ONLY"]
    assert [x["before_full_COUNT_assumed"] for x in rows]==[50,19,50,50,50,50,50]
    assert [x["deaths"] for x in rows]==[19,2,1,1,0,19,19]
    assert [x["HP_loss_min_IF_R77_full"] for x in rows]==[
        11639,5668,10999,10999,8961,11639,11639
    ]
    assert [x["HP_loss_max_IF_R77_full"] for x in rows]==[
        11750,5857,11547,11547,9520,11750,11750
    ]
    assert [x["HP_only_optimistic_no_overkill_min_full_gun_hits"] for x in rows]==[
        55,25,53,53,48,55,55
    ]
    assert [x["strict_individual_D_overkill_lost_min_full_gun_hits"] for x in rows]==[
        60,25,53,53,48,60,60
    ]
    assert [x["HP_only_min_minus_baseline"] for x in rows]==[6,-24,4,-3,-1,6,6]
    # Knife deficits total +18, but physics requires simultaneous Axe
    # slot adjustments and casualty-mode assumptions.
    assert sum(x["HP_only_min_minus_baseline"] for x in rows)==-6


def test_reassignment_alone_CANNOT_fit_strict_D_in_350_tickets():
    v=report()
    assert v["R77_conservative_HP_only_min_full_primary_with_one_wall_each"]==344
    assert v["R77_strict_D_min_full_primary_with_one_wall_each"]==359
    cap=v["R77_allocation_optimum_with_at_most_seven_wall_one_shots"]
    assert cap["conserved_HP_no_overkill"]["minimum_total_primary_shots"]==338
    assert cap["strict_individual_D_with_discarded_overkill"]["minimum_total_primary_shots"]==353
    assert cap["strict_individual_D_with_discarded_overkill"]["wall_shots_used"]<=7
    assert 338<=350<353


def test_350_full_damaging_tickets_can_fit_HP_intervals_not_kill_counts():
    v=report()
    w=v["R77_one_INTEGER_HP_budget_witness_350_tickets"]
    assert [x["full_shots_ASSUMED"] for x in w]==[55,27,54,56,48,55,55]
    assert [x["difference_from_baseline_AM"] for x in w]==[6,-22,5,0,-1,6,6]
    assert sum(x["full_shots_ASSUMED"] for x in w)==350
    assert all(x["budget_feasible_WITH_ONE_DIRECT_WALL_KILL"] for x in w)
    assert all(x["individual_KILL_COUNT_not_reconstructed"] for x in w)


def test_experimental_accuracy_only_DIFferences_do_not_fit_R77_knives():
    v=report()
    sims=v["EXPERIMENTAL_accuracy_single_slot_simulations"]
    assert sims["carabineer_14_against_21_fresh_Axe"]["gun_deaths"]==7
    assert sims["slinger_49_into_50_fresh_Knife"]["gun_deaths"]==0
    assert sims["slinger_55_into_50_fresh_Knife"]["gun_deaths"]==5
    assert sims["slinger_49_into_19_fresh_Axe"]["gun_deaths"]==0
    assert sims["slinger_56_into_50_fresh_Axe"]["gun_deaths"]==0
    assert v["R77_Knife_19_deaths_vs_exp_accuracy_55hits_model_only5"]
    assert v["one_shot_or_diversion_explanations_unverified"]
    assert any("19-Axe slot" in x for x in v["interpretive_limits"])



def test_R76_owner_full_health_seven_wall_deaths_precedes_fresh_slinger_volley():
    r=report()["R76_owner_verified_baseline"]
    assert r["front_HP_full_100pct_owner_verified"]
    assert r["no_slinger_before_R77_owner_verified"]
    assert r["R77_slingers_first_arrival_round"]==77
    assert r["R77_visible_primary_blue_ammo_sufficient_for_first_350_attempts_owner_verified"]
    assert r["R76_round_deaths_LTR"]==[1,2,1,1,0,1,1]
    assert r["R76_round_deaths_total"]==7
    assert r["wall_one_death_PER_SLOT_is_NOT_supported"]
    assert r["wall_actual_seven_attack_hit_log_not_observed"]


def test_R76_R77_inter_round_169_Axe_repacking_was_not_projectile_reroute():
    r=report()["R76_to_R77_slot_population_repacking"]
    assert r["R76_end_front_physical"]==[49,21,49,49,50,49,49]
    assert r["R77_before_shots_physical"]==[50,19,50,50,50,50,50]
    assert r["inter_round_delta_LTR"]==[1,-2,1,1,0,1,1]
    assert r["axe_total_before_and_after"]==[169,169]
    assert r["Knife_total_front_plus_reserve_before_and_after"]==[169,169]
    assert r["partial_Axe_slot2_21_to19_and_phys3_4_each_plus1"]
    assert r["is_inter_round_UNIT_repacking_not_same_round_AM_shot_reroute"]


def test_two_small_axe_slots_42_to43_pct_nominal_damage_pressure_not_universal_trigger():
    r=report()["dimensionless_incoming_nominal_HP_pressure_CANDIDATE_NOT_RULE"]
    gun=14*710/(21*1120)
    slinger=49*187/(19*1120)
    assert r["gun_R84_center_Axe_14x710_div_21x1120"]==gun
    assert r["slinger_R77_partial_Axe_49x187_div_19x1120"]==slinger
    assert abs(gun-slinger)<0.01
    assert r["slinger_R77_full_Knife49x207_div50x360_counterexample"]==49*207/(50*360)
    assert r["universal_pressure_threshold_is_FALSIFIED_by_full_Knife"]
    assert r["understrength_occupancy_gate_or_other_rule_UNVERIFIED"]
    assert r["actual_round_damage_post_AM_may_differ"]


def test_R76_two_wall_kills_in_one_slot_changes_R77_18_hit_equivalence():
    d=report()
    sens=d["R77_Knife_AND_partial_Axe_wall_assignment_sensitivity"]
    assert d["R76_wall7_nonuniform_distribution_makes_R77_wall_redistribution_unknown"]
    a=sens["Knife_by_wall_0_1_2"]
    assert [v["Knife_min_extra_equivalents_over_base49"] for v in a]==[8,6,4]
    assert [v["three_Knife_min_extra_over_base"] for v in a]==[24,18,12]
    assert [v["using_three_slots_wall_cost"] for v in a]==[0,3,6]
    b=sens["partial_Axe_by_wall_0_1_2"]
    assert [v["min_unspent_nominal_AM_hit_equivalents_under_assumptions"]
            for v in b]==[18,24,30]
    assert [v["max_locally_consumable_primary_hits_IF_no_damage_loss"]
            for v in b]==[31,25,19]
    assert sens["wall_damage_assumes_each_direct_death_REMOVES_full_target_HP_NOT_PREWOUNDED"]
    assert sens["R77_true_wall_targets_UNOBSERVED"]
