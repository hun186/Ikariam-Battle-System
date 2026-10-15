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
