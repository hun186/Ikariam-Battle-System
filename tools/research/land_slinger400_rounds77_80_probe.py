"""400 Slinger Attack Workshop24: R76 full-health baseline + R77..R80.

Read-only inverse constraints. Owner CONFIRMED active Forge Lv5, R76
frontline HP all 100%, and 400 freshly introduced Slingers at R77, with
visible R77 BLUE primary-ammo bars. Native weapon capacity=5 primary shots,
so one shot per round R77-80 does NOT exhaust it. Real per-hit source
targets, accuracy/individual HP algorithm and percent-bar formula UNKNOWN.
R79 rear 100% remains visually inferred, NOT owner-verified.
"""
from __future__ import annotations

import json
from math import ceil
from pathlib import Path

from ikariam_battle.damage import RoundingPolicy, calculate_damage
from ikariam_battle.profiles import ForgeProfile, WorkshopProfile
from ikariam_battle.units import UnitRegistry
from tools.research.land_round80_89_am_focus_probe import (
    model_am_addressed_shots_by_physical_slot,
)

FIXTURE = Path(__file__).resolve().parents[2]/(
    "tests/fixtures/reverse_engineering/land_barbarian_slinger400_rounds77_80_20261015.json"
)


def floored_mean_hp_total_interval(n: int, hp: int, shown_percent: int) -> tuple[int,int]:
    """Total HP interval if percent=floor(100*live HP/live max HP). HYPOTHETICAL."""
    if not isinstance(n,int) or not isinstance(hp,int) or not isinstance(shown_percent,int):
        raise TypeError("Integral HP/units/bar required")
    if n<0 or hp<=0 or not 0<=shown_percent<=100:
        raise ValueError("Bad HP state")
    if n==0:
        if shown_percent:
            raise ValueError("No live unit cannot display positive percent")
        return (0,0)
    maximum=n*hp
    lower=(shown_percent*maximum+99)//100
    upper=min(maximum,((shown_percent+1)*maximum+99)//100-1)
    return lower,upper


def _total_hp_interval(row: list[dict], hp: int)->tuple[int,int]:
    bounds=[floored_mean_hp_total_interval(s["survivors"],hp,s["hp_percent"]) for s in row]
    return sum(x for x,_ in bounds),sum(y for _,y in bounds)


def _profile_by_target(forge_level: int)->dict:
    u=UnitRegistry.load(include_barbarians=True)
    sl=u.get("slinger")
    workshop,forge=WorkshopProfile.load(),ForgeProfile.load()
    return {
        name:calculate_damage(
            sl,u.get(name),attack_level=24,armor_level=0,
            attacker_forge=forge_level,defender_forge=0,
            workshop=workshop,forge=forge,rounding=RoundingPolicy.FLOOR,
        ).final_damage for name in (
            "barbarian_axe_swinger","barbarian_knifeman","barbarian_axe_thrower"
        )
    }


def report()->dict:
    j=json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert j["source"]["user_confirmed_forge_level_in_this_400_slinger_battle"] == 5
    assert j["source"]["user_confirmed_forge_active_in_this_400_slinger_battle"]
    assert j["source"]["pre_R77_HP_100pct_verified_by_owner"]
    assert j["source"]["all_400_slingers_first_enter_round"] == 77
    assert j["source"]["R77_350_deployed_primary_shots_ammo_available_owner_confirmed"]
    r76=next(r for r in j["rounds"] if r["round"]==76)
    r77=next(r for r in j["rounds"] if r["round"]==77)
    prior=[x["survivors"] for x in r76["barbarian_first_by_physical_slot"]]
    start=[x["survivors"]+x["round_deaths"]
           for x in r77["barbarian_first_by_physical_slot"]]
    assert prior==[49,21,49,49,50,49,49]
    assert start==[50,19,50,50,50,50,50]
    assert [b-a for a,b in zip(prior,start)]==[1,-2,1,1,0,1,1]
    assert sum(prior[i] for i in (1,2,3,4))==sum(start[i] for i in (1,2,3,4))==169
    assert sum(prior[i] for i in (0,5,6))+22==sum(start[i] for i in (0,5,6))+19==169
    assert [x["hp_percent"] for x in r76["barbarian_first_by_physical_slot"]]==[100]*7
    assert sum(x["round_deaths"] for x in r76["barbarian_first_by_physical_slot"])==7
    rows={r["round"]:r for r in j["rounds"]}
    registry=UnitRegistry.load(include_barbarians=True)
    hA=registry.get("barbarian_axe_swinger").hit_points
    hK=registry.get("barbarian_knifeman").hit_points
    hR=registry.get("barbarian_axe_thrower").hit_points
    assert (hA,hK,hR)==(1120,360,320)
    profiles={str(lv):_profile_by_target(lv) for lv in (0,5)}
    assert profiles["0"]=={
        "barbarian_axe_swinger":160,
        "barbarian_knifeman":180,
        "barbarian_axe_thrower":180,
    }
    assert profiles["5"]=={
        "barbarian_axe_swinger":187,
        "barbarian_knifeman":207,
        "barbarian_axe_thrower":207,
    }
    first=lambda rnd,unit: [
        x for x in rows[rnd]["barbarian_first_by_physical_slot"]
        if x["unit"]==unit
    ]
    totals={}
    for rnd in (77,78,79,80):
        f=rows[rnd]["barbarian_first_by_physical_slot"]
        totals[str(rnd)]={
            "front_deaths":sum(x["round_deaths"] for x in f),
            "axe_end":sum(x["survivors"] for x in first(rnd,"barbarian_axe_swinger")),
            "axe_deaths":sum(x["round_deaths"] for x in first(rnd,"barbarian_axe_swinger")),
            "knife_end":sum(x["survivors"] for x in first(rnd,"barbarian_knifeman")),
            "knife_deaths":sum(x["round_deaths"] for x in first(rnd,"barbarian_knifeman")),
            "rear_thrower_end":sum(rows[rnd]["rear_axe_thrower_group_counts"]),
            "rear_thrower_deaths":sum(rows[rnd]["rear_axe_thrower_round_deaths"]),
        }
    assert (totals["77"]["axe_end"], totals["78"]["axe_end"],
            totals["79"]["axe_end"],totals["80"]["axe_end"]) == (165,154,114,0)
    assert (totals["77"]["knife_end"],totals["78"]["knife_deaths"])==(93,112)
    assert (totals["78"]["axe_deaths"],totals["79"]["axe_deaths"],
            totals["80"]["axe_deaths"])==(11,40,114)
    assert (totals["79"]["rear_thrower_end"], totals["80"]["rear_thrower_end"],
            totals["80"]["rear_thrower_deaths"])==(217,188,29)
    assert totals["77"]["knife_end"]+rows[77]["barbarian_knifeman_reserve_after_round"]==totals["78"]["knife_deaths"]
    assert totals["78"]["axe_end"]-totals["79"]["axe_deaths"]==totals["79"]["axe_end"]
    assert totals["79"]["axe_end"]==totals["80"]["axe_deaths"]

    def row_bounds(rnd:int,unit:str,hp:int)->tuple[int,int]:
        return _total_hp_interval(first(rnd,unit),hp)

    axe_r78=row_bounds(78,"barbarian_axe_swinger",hA)
    axe_r79=row_bounds(79,"barbarian_axe_swinger",hA)
    # If identical same-wave Axe HP budget is tracked between snapshots
    # without external HP injections/deductions, net HP lost between round
    # end scenes includes both dead-HP and survivor wound increases.
    min_removed=axe_r78[0]-axe_r79[1]
    max_removed=axe_r78[1]-axe_r79[0]
    assert (min_removed,max_removed)==(66130,69122)

    # R79 rear looks fully green on image but user did not verify that
    # the TRUE rear HP was all 100% at start R80; conditional only.
    rear_live=rows[80]["rear_axe_thrower_group_counts"]
    rear_bars=rows[80]["rear_axe_thrower_HP_percent"]
    rear_final_bounds=_total_hp_interval([
        {"survivors":n,"hp_percent":pct}
        for n,pct in zip(rear_live,rear_bars)
    ],hR)
    rear_pre_hp_if_fresh=sum(rows[79]["rear_axe_thrower_group_counts"])*hR
    rear_net_removed_min=rear_pre_hp_if_fresh-rear_final_bounds[1]
    rear_net_removed_max=rear_pre_hp_if_fresh-rear_final_bounds[0]
    assert (rear_net_removed_min,rear_net_removed_max)==(31018,31615)
    # R79 remaining front HP must all disappear at R80; after a putatively
    # fresh rear loss this is a MINIMUM combined HP disappearance, NOT
    # definitely all from slingers (wall may one-kill some targets).
    r80_net_lost_min=axe_r79[0]+rear_net_removed_min
    r80_net_lost_max=axe_r79[1]+rear_net_removed_max
    assert (r80_net_lost_min,r80_net_lost_max)==(68047,69916)

    amp=[]
    for active in ((1,2,3,4,5,6,7),(2,3,4,5),(3,4,5)):
        histogram=model_am_addressed_shots_by_physical_slot(list(active),[50]*7)
        amp.append({
            "active_physical_targets":list(active),
            "AM_base_addresses_by_physical":{str(i):n for i,n in histogram.items()},
            "total_addresses_if_350_fully_fire":sum(histogram.values()),
            "not_confirmed_historical_game_firing_pattern":True,
        })
    assert [list(x["AM_base_addresses_by_physical"].values()) for x in amp]==[
        [49,49,49,56,49,49,49],[84,91,91,84],[119,119,112]
    ]
    # R77 FIRST two damage control examples with all Axe target HP initially
    # full; this does NOT assert that all walls were active/hit this round.
    # Axe physical5 50(-0) bar83: 49 AM addresses with Forge5 187 each.
    # Axe physical4 49(-1) bar81: 56 addresses spread near-uniformly over
    # 50 Axe, followed by ONE hypothetical wall one-kill that carries its old
    # average 209 gun-wound points away.
    r77_axe_center=rows[77]["barbarian_first_by_physical_slot"][3]
    r77_axe_right=rows[77]["barbarian_first_by_physical_slot"][4]
    assert (r77_axe_center["survivors"],r77_axe_center["round_deaths"],
            r77_axe_center["hp_percent"])==(49,1,81)
    assert (r77_axe_right["survivors"],r77_axe_right["round_deaths"],
            r77_axe_right["hp_percent"])==(50,0,83)
    r77_candidate=[]
    for forge_level in (0,5):
        dm=profiles[str(forge_level)]["barbarian_axe_swinger"]
        center_gun_wounds=amp[0]["AM_base_addresses_by_physical"]["4"]*dm
        right_gun_wounds=amp[0]["AM_base_addresses_by_physical"]["5"]*dm
        center_wall_victim_old_wounds=center_gun_wounds//50
        center_end=center_gun_wounds-center_wall_victim_old_wounds
        center_bar=100*(49*hA-center_end)//(49*hA)
        right_bar=100*(50*hA-right_gun_wounds)//(50*hA)
        r77_candidate.append({
            "forge_level_comparator":forge_level,
            "physical4_addresses":56,
            "physical5_addresses":49,
            "hypothetical_gun_wounds_phys4":center_gun_wounds,
            "hypothetical_gun_wounds_phys5":right_gun_wounds,
            "phys4_wall_one_kill_and_removes_near_average_prior_wounds":center_wall_victim_old_wounds,
            "phys4_end_wounds":center_end,
            "phys4_floor_HP_bar":center_bar,
            "phys5_floor_HP_bar_without_wall_kill":right_bar,
            "phys4_and_phys5_match_owner_snapshot":center_bar==81 and right_bar==83,
            "target_was_100pct_before_round_UNVERIFIED":True,
            "no_gun_deaths_near_equal_damage_per_individual_UNVERIFIED":True,
        })
    assert [q["phys4_and_phys5_match_owner_snapshot"] for q in r77_candidate]==[False,True]

    # Source R77 knife physical1/6/7: 50 full HP360 before attacks is an
    # owner now VERIFIED R76 all frontline at 100%; actual HP per soldier
    # is not separately instrumented. No Slingers before R77.
    # Conditional on that AND floor-of-survivor-average bar, each 31/56%
    # Knife group implies 11639..11750 total HP lost (dead+living wounds).
    # Even 49 fully damaging Forge5 slinger shots and a generous final
    # wall 1-kill at up to a FULL 360 HP cannot account for that loss.
    # Each knife slot would need at least 55 gun equivalents, six above
    # the baseline AM49, absent other damaging sources. This is NOT
    # proof of re-addressing; old injuries, overkill, additional attacks,
    # differing UI, or weapon logs could invalidate that interpretation.
    knife_before_count=50
    knife_after_count=31
    knife_end_hp_range=floored_mean_hp_total_interval(
        knife_after_count,hK,56
    )
    knife_hp_removed_range=(
        knife_before_count*hK-knife_end_hp_range[1],
        knife_before_count*hK-knife_end_hp_range[0],
    )
    knife_gun_damage=profiles["5"]["barbarian_knifeman"]
    baseline_knife_gun_addresses=amp[0]["AM_base_addresses_by_physical"]["1"]
    max_one_wall_knife_hp=hK
    max_baseline_knife_HP_consumption=(
        baseline_knife_gun_addresses*knife_gun_damage+max_one_wall_knife_hp
    )
    min_full_shots_needed_after_one_wall=ceil(
        (knife_hp_removed_range[0]-max_one_wall_knife_hp)/knife_gun_damage
    )
    assert knife_hp_removed_range==(11639,11750)
    assert baseline_knife_gun_addresses==49
    assert max_baseline_knife_HP_consumption==10503
    assert min_full_shots_needed_after_one_wall==55
    assert [x["round_deaths"] for x in first(77,"barbarian_knifeman")]==[19,19,19]
    assert all(x["hp_percent"]==56 for x in first(77,"barbarian_knifeman"))
    # Conditional high-impact wounded Axe slot physical2: R77 starts
    # 19 and ends17 (-2) with 81% HP. As with knife, compare FULL
    # status before the attack, assumed floor-of-living bar after.
    phys2=rows[77]["barbarian_first_by_physical_slot"][1]
    assert (phys2["physical_slot"],phys2["survivors"],
            phys2["round_deaths"],phys2["hp_percent"])==(2,17,2,81)
    hp17=floored_mean_hp_total_interval(17,hA,81)
    phys2_removed_range=(19*hA-hp17[1],19*hA-hp17[0])
    baseline_phys2_damage=amp[0]["AM_base_addresses_by_physical"]["2"]*profiles["5"]["barbarian_axe_swinger"]
    assert (phys2_removed_range,baseline_phys2_damage)==((5668,5857),9163)
    # The difference equals ~18 shot equivalents, but ONLY IF all
    # damage addressed to this cell is conserved, no healing, and the
    # excess is redirected rather than missed/overkilled. Do not
    # reify it as exact 18 actual transferred shots.
    phys2_gun_shot_overhead_lower_bound_if_all_hits_conserved=(
        49-(phys2_removed_range[1]//profiles["5"]["barbarian_axe_swinger"])
    )
    assert phys2_gun_shot_overhead_lower_bound_if_all_hits_conserved==18

    # With the same hypothetical all-350-primary shot population, see what
    # Forge0 vs Forge5 budgets can/cannot cover under the restrictive R78-79
    # pure Axe-front-only + max seven independent wall one-shot caps.
    budget=[]
    for forge_level in (0,5):
        axe=profiles[str(forge_level)]["barbarian_axe_swinger"]
        rear=profiles[str(forge_level)]["barbarian_axe_thrower"]
        knife=profiles[str(forge_level)]["barbarian_knifeman"]
        max_wall_full_axe_cap=7*hA  # wall target/number UNVERIFIED
        # If no wall/other direct source and both lines started as supplied,
        # number of optimal perfect full hits required in R80.
        needed_axe=ceil(axe_r79[0]/axe)
        needed_rear=ceil(rear_net_removed_min/rear)
        budget.append({
            "forge_level_for_control":forge_level,
            "forge_profile_is_actual_user_confirmed_case":forge_level==5,
            "per_full_primary_hit_to_Axe":axe,
            "per_full_primary_hit_to_Knife":knife,
            "per_full_primary_hit_to_AxeThrower":rear,
            "fresh_full_Axe_hits_to_kill":ceil(hA/axe),
            "primary_finite_ammo_per_unit":registry.get("slinger").primary_weapon.ammunition,
            "max_350_primary_full_hit_damage_all_to_Axe":350*axe,
            "R78_to_R79_min_hp_removed":min_removed,
            "R78_R79_possible_if_350_all_Axe_primary_hits_AND_no_other_attack":350*axe>=min_removed,
            "R78_R79_possible_with_extreme_UP_TO_7_full_hp_wall_Axe_kills":
                350*axe+max_wall_full_axe_cap>=min_removed,
            "R80_min_HP_removed_front_plus_conditional_fresh_rear":r80_net_lost_min,
            "R80_best_case_full_primary_shots_needed_if_wall_has_ZERO_attacks_front":
                needed_axe+needed_rear,
            "R80_front_full_primary_shots_min_if_no_other_attack":needed_axe,
            "R80_rear_full_primary_shots_min_if_no_other_attack":needed_rear,
            "R80_no_wall_full_hit_feasibility_if_at_most350":needed_axe+needed_rear<=350,
            "source_primary_ammo_fresh_at_R77_owner_verified":True,
            "available_primary_shot_R77_through_R80_if_max1_per_round":True,
            "individual_effective_hits_and_GM_accuracy_UNKNOWN":True,
            "forge_owner_verified_F5":True,
        })
    # One explicit AGGREGATE integer-HP feasibility witness; no wall damage,
    # no gun miss, and switches source damage when target class changes.
    # This is mathematically possible within screenshot HP intervals but not
    # an observed source-shot timeline or a real AM retargeting algorithm.
    forge5_control=profiles["5"]
    witness_front_shots=199
    witness_rear_shots=350-witness_front_shots
    witness_front_hp=witness_front_shots*forge5_control["barbarian_axe_swinger"]
    witness_rear_removed=witness_rear_shots*forge5_control["barbarian_axe_thrower"]
    witness_rear_end=sum(rows[79]["rear_axe_thrower_group_counts"])*hR-witness_rear_removed
    assert (witness_front_shots,witness_rear_shots,witness_front_hp,
            witness_rear_removed,witness_rear_end)==(199,151,37213,31257,38183)
    assert axe_r79[0]<=witness_front_hp<=axe_r79[1]
    assert rear_final_bounds[0]<=witness_rear_end<=rear_final_bounds[1]

    return {
        "schema_version":1,
        "kind":"FOUR_ROUND_400_SLINGER_SAME_BATTLE_COUNT_AND_HP_CONSTRAINTS",
        "case_id":j["case_id"],
        "battle_id":j["battle_identity"]["battle_id"],
        "user_slinger_workshop_attack_level":24,
        "user_slinger_total":400,
        "seven_visible_active_firing_cells":[50]*7,
        "reserve":50,
        "owner_confirmed_active_forge_level":5,
        "owner_confirmed_forge_evidence":"Explicit user follow-up: 有開5級熔爐。",
        "actual_forge_level_verified":True,
        "forge0_is_counterfactual_only":True,
        "target_HP":{"axe":hA,"knife":hK,"rear_axe_thrower":hR},
        "real_hp_bar_floor_mean_rule_VERIFIED":False,
        "owner_R76_front_full_100pct_CONFIRMED":True,
        "R77_slinger_first_join_round_owner_confirmed":77,
        "owner_blue_primary_ammo_visible_in_R77":True,
        "max_primary_shots_PER_UNIT_in_4_rounds_77_to80":4,
        "primary_ammo_capacity_per_unit":5,
        "ammo_cannot_have_been_exhausted_before_R80_IF_max1_shot_per_round":True,
        "R76_wall_only_seven_deaths_NONUNIFORM":[1,2,1,1,0,1,1],
        "R76_to_R77_frontline_repacking":[1,-2,1,1,0,1,1],
        "rear_R79_before_R80_full_100pct_NOT_CONFIRMED":True,
        "by_round":totals,
        "three_count_conservation_checks":{
            "R77_knife93_living_plus_reserve19_to_R78_knife112_deaths":93+19==112,
            "R78_axe154_minus_R79_deaths40_equals_R79_axe114":154-40==114,
            "R79_remaining_114_axes_dies_R80_in_50_50_14_slots":114==50+50+14,
            "R79_rear_217_throwers_loses29_and_has188_at_R80":217-29==188,
        },
        "conditional_floor_surviving_total_HP_ranges":{
            "R78_end_154_living_axe":list(axe_r78),
            "R79_end_114_living_axe":list(axe_r79),
            "R80_end_188_living_thrower":list(rear_final_bounds),
            "R78_to_R79_all_axe_HP_removed_range_NO_ADDED_HP":[min_removed,max_removed],
            "R80_axe_HP_removed_exact_if_all_114_die_range":list(axe_r79),
            "R80_thrower_HP_removed_range_IF_R79_REAR_FULL_HP":
                [rear_net_removed_min,rear_net_removed_max],
            "R80_joint_axe_plus_thrower_HP_removed_IF_R79_REAR_FULL_HP":
                [r80_net_lost_min,r80_net_lost_max],
        },
        "project_AM_7x50_control_by_occupied_physical_targets":amp,
        "R77_physical4_and5_conditional_full_wound_spread_witness":r77_candidate,
        "R77_THREE_KNIFE_SLOTS_FULL_HP_CONDITIONAL_DAMAGE_DEFICIT":{
            "number_of_identical_knife_front_slots":3,
            "start_units_IF_full_at_before_R77":50,
            "end_units_each":31,
            "owner_bar_percent_each":56,
            "end_remaining_HP_interval":list(knife_end_hp_range),
            "HP_removed_per_knife_slot_if_fresh_and_floor_bar":list(knife_hp_removed_range),
            "baseline_project_AM_primary_addresses_each":baseline_knife_gun_addresses,
            "owner_confirmed_forge5_damage_per_complete_knife_primary_hit":knife_gun_damage,
            "max_one_wall_knife_full_HP_direct_kill":max_one_wall_knife_hp,
            "baseline_49_full_gun_hits_plus_generous_one_wall_HP_depletion":max_baseline_knife_HP_consumption,
            "minimum_additional_full_gun_equivalents_per_knife_slot":min_full_shots_needed_after_one_wall-baseline_knife_gun_addresses,
            "minimum_conditional_additional_shots_ALL_three_knife_slots":
                3*(min_full_shots_needed_after_one_wall-baseline_knife_gun_addresses),
            "observed_reroute_UNVERIFIED":True,
            "R76_all_frontline_hp_100pct_CONFIRMED":True,
            "no_unobserved_damage_between_R76_R77_ASSUMED":True,
            "actual_per_individual_hit_log_UNAVAILABLE":True,
            "wall_one_full_knife_HP_kill_UNVERIFIED":True,
            "total_HP_accounting_not_specific_Kill_Type":True,
        },
        "R77_PARTIAL_AXE_PHYSICAL2_conditional_surplus_assigned_damage":{
            "start_Axe_IF_full_before_R77":19,
            "survivors":17,
            "shown_HP_percent":81,
            "observed_HP_removed_interval_IF_floor_bar":list(phys2_removed_range),
            "baseline_AM_49_complete_forge5_shots_HP":baseline_phys2_damage,
            "at_least_18_gun_tickets_not_consumed_locally_IF_full_hits_conserved_without_overkill":
                phys2_gun_shot_overhead_lower_bound_if_all_hits_conserved,
            "no_proof_actual_18_shots_redirected":True,
            "no_unobserved_HP_inflow_heal_or_rebuild_into_phys2_REQUIRED":True,
            "no_ammo_miss_overkill_OR_other_damage_loss_REQUIRED":True,
            "possible_RR_reserve_replacement_HP_inflow_NOT_EXCLUDED_BY_SCREENSHOT":True,
        },
        "per_hit_forge_comparison_PRIMARY_only":budget,
        "confirmed_real_F5_primary_per_hit":profiles["5"],
        "R80_formational_fallback_GAMEFORGE_HELP_KNOWN":{
            "source_runtime_line":"second",
            "priority_target_lines":["first","flank","second"],
            "next_target_when_no_first_and_no_flank":"second",
            "later_shots_reselect_target_class_after_higher_priority_class_eliminated":True,
            "source":"ikariam_battle/data/rules/legacy-community-land-targeting.json metadata.target_transfer_contract; Gameforge Art of Warfare in-game help",
            "individual_slot_AM_damage_distribution_UNKNOWN":True,
            "actual_R80_front_vs_rear_shot_counts_UNKNOWN":True,
        },
        "R80_ONE_NO_WALL_AGGREGATE_FULL_DAMAGE_WITNESS_NOT_REAL_ATTACK_LOG":{
            "owner_confirmed_forge_level_for_damage_profile":5,
            "wall_effective_damage_contribution_assumed":0,
            "gun_hit_count_to_current_front_Axe":witness_front_shots,
            "gun_hit_count_to_rear_AxeThrower_after_hypothetical_target_switch":witness_rear_shots,
            "full_front_HP_consumed":witness_front_hp,
            "full_rear_HP_consumed":witness_rear_removed,
            "modeled_rear_end_total_HP":witness_rear_end,
            "front_remaining_HP_interval_makes_witness_possible":axe_r79[0]<=witness_front_hp<=axe_r79[1],
            "rear_end_HP_interval_makes_witness_possible":rear_final_bounds[0]<=witness_rear_end<=rear_final_bounds[1],
            "requires_target_class_transition_during_battle_round":True,
            "target_class_fallback_priority_KNOWN_IN_GAME_HELP":True,
            "precise_199_151_shot_split_IS_HYPOTHETICAL_NOT_OBSERVED":True,
            "per_slot_HP_and_actual_source_shot_paths_not_recovered":True,
        },
        "central_caveat":"Known Help targeting Second→First then Flank then Second. R77 newly deployed Slinger primary ammo 5 shots per unit and 4 observed attacking rounds implies sufficient first-primary ammo R77–80 if at most one shot per unit each round. The R80 exact 199/151 shots, effectiveness, within-slot damage redistribution, wall assignments, and UI wound rule remain UNKNOWN.",
        "hypotheses_to_compare":[
            "Integer conserved Slot wounds and RR interround damage vs individual D-kill with wounds retained",
            "AM regroup target slot count 7→4→3, distinct from incoming 350 attacks and screenshots showing 50+50+14 after regroup",
            "Target-class change Axe HP1120/armor20 → Axe Thrower HP320/armor0 when frontline clears R80",
            "In-game Help / current engine ALREADY establish that later Second-line shots select another target class once First and Flank are absent. Only exact 199/151 allocation and per-slot damage within R80 remain unknown",
            "Owner HAS confirmed active Forge5 for this Slinger case; Forge0 is an alternative counterfactual only",
            "Owner CONFIRMED 400 Slingers first joined R77 with blue primary ammo; 5 shots per unit supports one primary shot in each R77–R80, but not an independently captured successful hit/damage count",
            "Accuracy20 percent must not be blindly implemented as independent 20pct random hits; kill/wound allocator still unknown",
            "Owner CONFIRMED R76 all frontline HP100% and no slingers before R77; R77 starts full absent inter-round hidden damage. R79 rear full HP remains visually inferred",
        ]
    }


if __name__=="__main__":
    print(json.dumps(report(),ensure_ascii=False,indent=2))
