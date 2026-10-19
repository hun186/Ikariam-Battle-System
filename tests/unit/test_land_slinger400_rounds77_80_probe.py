"""Owner's 400-Slinger Lv24 four consecutive round source, research-only.

Only tested arithmetical bounds and conservation; NO official Gameforge
damage formula, actual 350 successful primary hits, Forge selection, phase
routing or UI-bar aggregate rule asserted.
"""
from tools.research.land_slinger400_rounds77_80_probe import (
    floored_mean_hp_total_interval, report,
)
import pytest


def test_four_source_rounds_and_slot_compaction_total_are_preserved():
    d=report()
    assert d["user_slinger_workshop_attack_level"]==24
    assert d["user_slinger_total"]==400
    assert d["seven_visible_active_firing_cells"]==[50]*7
    assert d["reserve"]==50
    t=d["by_round"]
    assert [t[str(i)]["front_deaths"] for i in range(77,81)]==[61,123,40,114]
    assert [t[str(i)]["axe_end"] for i in range(77,81)]==[165,154,114,0]
    assert [t[str(i)]["knife_end"] for i in (77,78)]==[93,0]
    assert t["78"]["knife_deaths"]==112
    assert t["79"]["rear_thrower_end"]==217
    assert t["80"]["rear_thrower_end"]==188
    assert t["80"]["rear_thrower_deaths"]==29
    assert all(d["three_count_conservation_checks"].values())


def test_project_seven_50_slinger_slots_AM_addresses_change_on_target_collapse():
    d=report()
    a=d["project_AM_7x50_control_by_occupied_physical_targets"]
    assert [x["total_addresses_if_350_fully_fire"] for x in a]==[350]*3
    assert a[0]["AM_base_addresses_by_physical"]=={
        "1":49,"2":49,"3":49,"4":56,"5":49,"6":49,"7":49,
    }
    assert a[1]["AM_base_addresses_by_physical"]=={
        "2":84,"3":91,"4":91,"5":84,
    }
    assert a[2]["AM_base_addresses_by_physical"]=={
        "3":119,"4":119,"5":112,
    }


def test_HP_budget_intervals_if_and_only_if_floor_mean_bar_and_no_unobserved_HP_input():
    d=report()
    p=d["conditional_floor_surviving_total_HP_ranges"]
    assert p["R78_end_154_living_axe"]==[104431,106151]
    assert p["R79_end_114_living_axe"]==[37029,38301]
    assert p["R78_to_R79_all_axe_HP_removed_range_NO_ADDED_HP"]==[66130,69122]
    assert p["R80_end_188_living_thrower"]==[37825,38422]
    assert p["R80_thrower_HP_removed_range_IF_R79_REAR_FULL_HP"]==[31018,31615]
    assert p["R80_joint_axe_plus_thrower_HP_removed_IF_R79_REAR_FULL_HP"]==[68047,69916]
    assert d["real_hp_bar_floor_mean_rule_VERIFIED"] is False
    assert d["owner_R76_front_full_100pct_CONFIRMED"]
    assert d["R77_slinger_first_join_round_owner_confirmed"]==77
    assert d["owner_blue_primary_ammo_visible_in_R77"]
    assert d["primary_ammo_capacity_per_unit"]==5
    assert d["max_primary_shots_PER_UNIT_in_4_rounds_77_to80"]==4
    assert d["ammo_cannot_have_been_exhausted_before_R80_IF_max1_shot_per_round"]
    assert d["R76_wall_only_seven_deaths_NONUNIFORM"]==[1,2,1,1,0,1,1]
    assert d["R76_to_R77_frontline_repacking"]==[1,-2,1,1,0,1,1]


def test_owner_confirmed_forge5_damage_with_forge0_counterfactual_comparison():
    d=report()
    p={x["forge_level_for_control"]:x for x in d[
        "per_hit_forge_comparison_PRIMARY_only"
    ]}
    assert (p[0]["per_full_primary_hit_to_Axe"],
            p[0]["per_full_primary_hit_to_Knife"],
            p[0]["per_full_primary_hit_to_AxeThrower"])==(160,180,180)
    assert (p[5]["per_full_primary_hit_to_Axe"],
            p[5]["per_full_primary_hit_to_Knife"],
            p[5]["per_full_primary_hit_to_AxeThrower"])==(187,207,207)
    assert p[0]["fresh_full_Axe_hits_to_kill"]==7
    assert p[5]["fresh_full_Axe_hits_to_kill"]==6
    assert p[0]["max_350_primary_full_hit_damage_all_to_Axe"]==56000
    assert p[5]["max_350_primary_full_hit_damage_all_to_Axe"]==65450
    assert p[0]["R78_R79_possible_with_extreme_UP_TO_7_full_hp_wall_Axe_kills"] is False
    assert p[5]["R78_R79_possible_with_extreme_UP_TO_7_full_hp_wall_Axe_kills"] is True
    assert p[0]["R80_best_case_full_primary_shots_needed_if_wall_has_ZERO_attacks_front"]==405
    assert p[5]["R80_front_full_primary_shots_min_if_no_other_attack"]==199
    assert p[5]["R80_rear_full_primary_shots_min_if_no_other_attack"]==150
    assert p[5]["R80_best_case_full_primary_shots_needed_if_wall_has_ZERO_attacks_front"]==349
    assert p[5]["R80_no_wall_full_hit_feasibility_if_at_most350"]
    assert d["actual_forge_level_verified"]
    assert d["owner_confirmed_active_forge_level"]==5
    assert d["forge0_is_counterfactual_only"]
    assert p[5]["forge_profile_is_actual_user_confirmed_case"]
    assert not p[0]["forge_profile_is_actual_user_confirmed_case"]
    assert d["confirmed_real_F5_primary_per_hit"]=={"barbarian_axe_swinger":187,"barbarian_knifeman":207,"barbarian_axe_thrower":207}


def test_r77_physical_center56_and_adjacent49_am_wounds_fit_forge5_bars():
    d=report()
    v={r["forge_level_comparator"]:r
       for r in d["R77_physical4_and5_conditional_full_wound_spread_witness"]}
    assert v[5]["physical4_addresses"]==56
    assert v[5]["physical5_addresses"]==49
    assert v[5]["hypothetical_gun_wounds_phys4"]==10472
    assert v[5]["hypothetical_gun_wounds_phys5"]==9163
    assert v[5]["phys4_wall_one_kill_and_removes_near_average_prior_wounds"]==209
    assert v[5]["phys4_end_wounds"]==10263
    assert v[5]["phys4_floor_HP_bar"]==81
    assert v[5]["phys5_floor_HP_bar_without_wall_kill"]==83
    assert v[5]["phys4_and_phys5_match_owner_snapshot"]
    assert not v[0]["phys4_and_phys5_match_owner_snapshot"]
    assert v[5]["target_was_100pct_before_round_UNVERIFIED"]


def test_r80_integer_aggregate_front_then_rear_feasibility_witness_is_not_a_hit_log():
    d=report()
    w=d["R80_ONE_NO_WALL_AGGREGATE_FULL_DAMAGE_WITNESS_NOT_REAL_ATTACK_LOG"]
    assert w["owner_confirmed_forge_level_for_damage_profile"]==5
    assert w["gun_hit_count_to_current_front_Axe"]==199
    assert w["gun_hit_count_to_rear_AxeThrower_after_hypothetical_target_switch"]==151
    assert w["gun_hit_count_to_current_front_Axe"]+w[
        "gun_hit_count_to_rear_AxeThrower_after_hypothetical_target_switch"
    ]==350
    assert w["full_front_HP_consumed"]==37213
    assert w["full_rear_HP_consumed"]==31257
    assert w["modeled_rear_end_total_HP"]==38183
    assert w["front_remaining_HP_interval_makes_witness_possible"]
    assert w["rear_end_HP_interval_makes_witness_possible"]
    assert w["requires_target_class_transition_during_battle_round"]
    assert w["per_slot_HP_and_actual_source_shot_paths_not_recovered"]


def test_three_knife_groups_require_additional_damage_under_fresh_full_hp_control():
    d=report()
    p=d["R77_THREE_KNIFE_SLOTS_FULL_HP_CONDITIONAL_DAMAGE_DEFICIT"]
    assert p["number_of_identical_knife_front_slots"]==3
    assert p["HP_removed_per_knife_slot_if_fresh_and_floor_bar"]==[11639,11750]
    assert p["baseline_project_AM_primary_addresses_each"]==49
    assert p["owner_confirmed_forge5_damage_per_complete_knife_primary_hit"]==207
    assert p["max_one_wall_knife_full_HP_direct_kill"]==360
    assert p["baseline_49_full_gun_hits_plus_generous_one_wall_HP_depletion"]==10503
    assert p["minimum_additional_full_gun_equivalents_per_knife_slot"]==6
    assert p["minimum_conditional_additional_shots_ALL_three_knife_slots"]==18
    assert p["R76_all_frontline_hp_100pct_CONFIRMED"]
    assert p["no_unobserved_damage_between_R76_R77_ASSUMED"]
    assert p["actual_per_individual_hit_log_UNAVAILABLE"]
    assert p["observed_reroute_UNVERIFIED"]
    assert p["total_HP_accounting_not_specific_Kill_Type"]


def test_partial_axe_cell_could_supply_equivalent_18_shots_but_not_proven_reroute():
    d=report()
    p=d["R77_PARTIAL_AXE_PHYSICAL2_conditional_surplus_assigned_damage"]
    assert p["start_Axe_IF_full_before_R77"]==19
    assert p["survivors"]==17
    assert p["shown_HP_percent"]==81
    assert p["observed_HP_removed_interval_IF_floor_bar"]==[5668,5857]
    assert p["baseline_AM_49_complete_forge5_shots_HP"]==9163
    assert p["at_least_18_gun_tickets_not_consumed_locally_IF_full_hits_conserved_without_overkill"]==18
    assert p["no_proof_actual_18_shots_redirected"]
    assert p["no_unobserved_HP_inflow_heal_or_rebuild_into_phys2_REQUIRED"]
    assert p["no_ammo_miss_overkill_OR_other_damage_loss_REQUIRED"]
    assert p["possible_RR_reserve_replacement_HP_inflow_NOT_EXCLUDED_BY_SCREENSHOT"]


def test_help_priority_confirms_front_to_rear_fallthrough_but_not_199_151():
    from ikariam_battle.profiles import TargetingProfile

    rules=TargetingProfile.load()
    assert rules.priorities["second"]==("first","flank","second")
    contract=rules.metadata["target_transfer_contract"]
    assert contract["status"]=="KNOWN_AT_FORMATION_CLASS_LEVEL"
    assert "Later individual shots select" in contract["rule"]
    assert contract["source_type"]=="GAMEFORGE_IN_GAME_HELP"
    d=report()
    known=d["R80_formational_fallback_GAMEFORGE_HELP_KNOWN"]
    assert known["source_runtime_line"]=="second"
    assert known["priority_target_lines"]==["first","flank","second"]
    assert known["next_target_when_no_first_and_no_flank"]=="second"
    assert known["later_shots_reselect_target_class_after_higher_priority_class_eliminated"]
    assert known["individual_slot_AM_damage_distribution_UNKNOWN"]
    assert known["actual_R80_front_vs_rear_shot_counts_UNKNOWN"]
    witness=d["R80_ONE_NO_WALL_AGGREGATE_FULL_DAMAGE_WITNESS_NOT_REAL_ATTACK_LOG"]
    assert witness["target_class_fallback_priority_KNOWN_IN_GAME_HELP"]
    assert witness["precise_199_151_shot_split_IS_HYPOTHETICAL_NOT_OBSERVED"]


def test_hp_percentage_as_interval_rejects_invalid_or_missing_units():
    assert floored_mean_hp_total_interval(49,1120,81)==(44453,45001)
    assert floored_mean_hp_total_interval(0,1120,0)==(0,0)
    assert floored_mean_hp_total_interval(1,1120,100)==(1120,1120)
    with pytest.raises(ValueError):
        floored_mean_hp_total_interval(0,1120,81)
    with pytest.raises(ValueError):
        floored_mean_hp_total_interval(-1,1120,81)


def test_r76_owner_full_100_percent_and_seven_walls_cannot_assume_one_per_slot():
    d=report()
    assert d["R76_wall_only_seven_deaths_NONUNIFORM"]==[1,2,1,1,0,1,1]
    assert sum(d["R76_wall_only_seven_deaths_NONUNIFORM"])==7
    assert d["owner_R76_front_full_100pct_CONFIRMED"]
    assert d["R77_slinger_first_join_round_owner_confirmed"]==77


def test_r77_19_Axe_exactly_grounded_in_inter_round_169_repacking():
    d=report()
    assert d["R76_to_R77_frontline_repacking"]==[1,-2,1,1,0,1,1]
    assert d["R77_PARTIAL_AXE_PHYSICAL2_conditional_surplus_assigned_damage"][
        "start_Axe_IF_full_before_R77"
    ]==19
    assert d["R77_THREE_KNIFE_SLOTS_FULL_HP_CONDITIONAL_DAMAGE_DEFICIT"][
        "start_units_IF_full_at_before_R77"
    ]==50


def test_five_primary_ammo_each_supports_all_four_rounds_but_not_claim_hits():
    d=report()
    assert d["primary_ammo_capacity_per_unit"]==5
    assert d["max_primary_shots_PER_UNIT_in_4_rounds_77_to80"]==4
    assert d["ammo_cannot_have_been_exhausted_before_R80_IF_max1_shot_per_round"]
    assert d["owner_blue_primary_ammo_visible_in_R77"]
    assert d["R77_slinger_first_join_round_owner_confirmed"]==77


def test_two_slinger_shots_reselect_living_second_after_first_eliminated_same_volley():
    """Engine regression: Help priority fallback is real, not report booleans."""
    from collections import defaultdict
    from ikariam_battle.battlefield import LAND_MINI, deploy
    from ikariam_battle.engine import _build_damage_queues, _resolve_volleys, _snapshot_phase_fire
    from ikariam_battle.models import Army
    from ikariam_battle.profiles import ForgeProfile, WorkshopProfile, TargetingProfile
    from ikariam_battle.units import UnitRegistry

    registry=UnitRegistry.load()
    targeting=TargetingProfile.load()
    assert targeting.metadata["target_transfer_contract"]["status"]=="KNOWN_AT_FORMATION_CLASS_LEVEL"
    a_army=Army.from_dict({
        "forge_level":5,
        "units":[{"unit_id":"slinger","quantity":2,"attack_upgrade":24}],
    })
    d_army=Army.from_dict({
        "forge_level":0,
        "units":[{"unit_id":"spearman","quantity":1},{"unit_id":"slinger","quantity":1}],
    })
    attacker=deploy(a_army,registry,LAND_MINI)
    defender=deploy(d_army,registry,LAND_MINI)
    events=[]
    applied={}
    volleys=_snapshot_phase_fire(
        attacker,defender,registry,targeting,events,1,"attacker","second",applied
    )
    assert len(volleys)>=1
    queues=_build_damage_queues(defender,registry,events,1,"defender",applied)
    fired=_resolve_volleys(
        volleys,defender,queues,registry,WorkshopProfile.load(),
        ForgeProfile.load(),targeting,events,1,a_army,d_army,
        defaultdict(int),defaultdict(int),applied,
    )
    assert fired==2
    damaged=[event for event in events if event.type=="damage"]
    assert [event.details["target_class"] for event in damaged]==["first","second"]
    assert damaged[0].details["target_unit_id"]=="spearman"
    assert damaged[1].details["target_unit_id"]=="slinger"
