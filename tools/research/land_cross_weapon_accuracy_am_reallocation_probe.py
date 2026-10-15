"""Research-only falsifiers for the owner's 70%-Accuracy Carabineer vs 20% Slinger case.

Compare two distinct battle/source windows, NOT the same battle:
- 400 Slinger Workshop ATT24 Forge5: R77 full frontline, 350 active sources
- 84 Carabineer Workshop ATT11 Forge5: same fight's R81-87 window

All conditional damage bounds below require:
* Owner VERIFIED R76 displayed HP100% for all frontline and R77 is the FIRST Slinger deployment; no evidence of interim wounds, but no per-individual shot log.
* Screenshot bar is floor(100 * SUM(living_hp)/(living_count*max_unit_hp)).
* Primary weapon FULL damage and no other damage source except up to 7
  independent direct one-unit wall kills. Shot addresses are not real hits.
* Blue ammo bars and R77 fresh 400 Slingers establish first-volley primary ammo availability for 350 deployed units, not a real per-hit, effective-damage, or exact Gameforge AM target ledger.

This does not assert that Gameforge uses the current experimental Accuracy
threshold, overkill recovery, D/I/P/IR selection or any inferred target transfers.
"""
from __future__ import annotations

import json
from itertools import product
from math import ceil
from pathlib import Path

from ikariam_battle.accuracy import (
    EXPERIMENTAL_ACCURACY_MODEL_ID,
    select_accuracy_target,
)
from ikariam_battle.units import UnitRegistry
from tools.research.land_round80_89_am_focus_probe import (
    model_am_addressed_shots_by_physical_slot,
)
from tools.research.land_slinger400_rounds77_80_probe import (
    FIXTURE as SLINGER_FIXTURE,
    floored_mean_hp_total_interval,
)
from tools.research.land_round80_89_two_class_am_probe import weapon_profiles


def _simulate_experimental_individual_focus(
    *, individuals: int, hits: int, hp: int, hit_damage: int, accuracy: int
) -> dict:
    """FULL real hits to an addressed slot, no wall, same unknown target history."""
    wounded=[0]*individuals
    decisions={}
    deaths=0
    for _ in range(hits):
        d=select_accuracy_target(wounded,hp,hit_damage,accuracy)
        decisions[d.mode]=decisions.get(d.mode,0)+1
        idx=d.target_index
        amount=wounded[idx]+hit_damage
        if amount>=hp:
            deaths+=1
            wounded.pop(idx)
        else:
            wounded[idx]=amount
        if not wounded:
            break
    return {
        "target_initial_full_individuals":individuals,
        "source_full_hits":hits,
        "gun_deaths":deaths,
        "gun_survivors":len(wounded),
        "remaining_gun_wounds":sum(wounded),
        "by_selection":decisions,
        "EXPERIMENTAL_NOT_OFFICIAL":EXPERIMENTAL_ACCURACY_MODEL_ID,
    }


def _hp_loss_interval(*, before: int, dead: int, hp: int, bar: int) -> list[int]:
    alive=before-dead
    low_hp,high_hp=floored_mean_hp_total_interval(alive,hp,bar)
    return [before*hp-high_hp,before*hp-low_hp]


def _minimum_full_shots(
    *, hp_loss_min: int, hp: int, per_hit: int, dead: int, wall_kills: int,
    discard_kill_overkill: bool,
) -> int:
    if not 0 <= wall_kills <= dead:
        raise ValueError("Wall death count inconsistent with observed casualty bound")
    gun_kills=dead-wall_kills
    hits_to_kill=ceil(hp/per_hit)
    # STRICT individually concentrated D-kill: one full-health individual
    # must absorb ceil(hp/damage) attacks; remainder overkill is discarded.
    overkill_per_gun_kill=(hits_to_kill*per_hit-hp) if discard_kill_overkill else 0
    productive_gun_hp_required=hp_loss_min-wall_kills*hp+gun_kills*overkill_per_gun_kill
    return max(0,gun_kills*hits_to_kill,
               ceil(productive_gun_hp_required/per_hit))


def _min_budget_with_wall_assignments(
    rows:list[dict], *, strict_D:bool, total_wall_shots:int
) -> dict:
    best=None
    # Enumerate at most 7 distinct wall one-shot kills and at most each
    # slot's observed deaths, deliberately generous to the wall.
    for allocation in product(*(range(min(k["deaths"],total_wall_shots)+1)
                                for k in rows)):
        if sum(allocation)>total_wall_shots:
            continue
        need=[
            _minimum_full_shots(
                hp_loss_min=x["HP_loss_min_IF_R77_full"],
                hp=x["target_hp"],
                per_hit=x["full_primary_damage"],
                dead=x["deaths"],
                wall_kills=w,
                discard_kill_overkill=strict_D,
            )
            for x,w in zip(rows,allocation)
        ]
        value=sum(need)
        if best is None or value < best["minimum_total_primary_shots"]:
            best={
                "minimum_total_primary_shots":value,
                "witness_wall_kills_LTR":list(allocation),
                "per_slot_full_shots_lower_bound_LTR":need,
                "wall_shots_used":sum(allocation),
            }
    assert best is not None
    return best


def report()->dict:
    fixture=json.loads(SLINGER_FIXTURE.read_text(encoding="utf-8"))
    assert fixture["source"]["user_confirmed_forge_level_in_this_400_slinger_battle"]==5
    units=UnitRegistry.load(include_barbarians=True)
    sl=units.get("slinger")
    gn=units.get("sulphur_carabineer")
    assert (sl.primary_weapon.accuracy,gn.primary_weapon.accuracy)==(20,70)
    s_axe=units.get("barbarian_axe_swinger")
    s_knife=units.get("barbarian_knifeman")
    assert (s_axe.hit_points,s_knife.hit_points)==(1120,360)
    assert (sl.primary_weapon.ammunition,gn.primary_weapon.ammunition)==(5,3)
    gun=weapon_profiles(attacker_forge=5)["barbarian_targets"]
    assert (
        gun["barbarian_axe_swinger"]["shot_damage"],
        gun["barbarian_knifeman"]["shot_damage"]
    )==(710,730)
    previous=next(x for x in fixture["rounds"] if x["round"]==76)
    assert fixture["source"]["pre_R77_HP_100pct_verified_by_owner"]
    assert fixture["source"]["all_400_slingers_first_enter_round"]==77
    assert fixture["source"]["R77_350_deployed_primary_shots_ammo_available_owner_confirmed"]
    assert previous["owner_confirms_all_7_front_slot_HP_at_100pct"]
    assert previous["defender_slingers_deployed"]==0
    assert [x["round_deaths"] for x in previous["barbarian_first_by_physical_slot"]]==[
        1,2,1,1,0,1,1
    ]
    assert sum(x["round_deaths"] for x in previous["barbarian_first_by_physical_slot"])==7
    source=next(x for x in fixture["rounds"] if x["round"]==77)
    slinger_am=model_am_addressed_shots_by_physical_slot(
        list(range(1,8)),[50]*7
    )
    assert list(slinger_am.values())==[49,49,49,56,49,49,49]
    prev_end=[x["survivors"] for x in previous["barbarian_first_by_physical_slot"]]
    start_now=[x["survivors"]+x["round_deaths"] for x in source["barbarian_first_by_physical_slot"]]
    repack=[now-prev for now,prev in zip(start_now,prev_end)]
    assert prev_end==[49,21,49,49,50,49,49]
    assert start_now==[50,19,50,50,50,50,50]
    assert repack==[1,-2,1,1,0,1,1]
    assert (sum(prev_end[i] for i in (1,2,3,4)),
            sum(start_now[i] for i in (1,2,3,4)))==(169,169)
    assert sum(prev_end[i] for i in (0,5,6))+22==sum(
        start_now[i] for i in (0,5,6)
    )+19==169
    # Compare percentage of HP capacity addressed with per-hit gun damage,
    # not a claim of actual full applied damage or "accuracy = miss %".
    # Understrength Axe: Gun center 21 at original R84:14×710 / (21×1120)
    # vs Slinger R77 Axe19:49×187/(19×1120).
    # Both ~42%-43%, although sample size2 does NOT prove threshold.
    gun_pressure=14*710/(21*1120)
    slinger_pressure=49*187/(19*1120)
    assert 0.42<gun_pressure<0.43
    assert 0.43<slinger_pressure<0.44
    assert abs(gun_pressure-slinger_pressure)<0.01
    # Refute a UNIVERSAL damage-pressure trigger: all THREE healthy Knife
    # outer cells are FULL 50 and have HIGHER baseline pressure (~56%).
    knife_pressure=49*207/(50*360)
    assert knife_pressure>0.56
    entries=[]
    for pos in source["barbarian_first_by_physical_slot"]:
        i=pos["physical_slot"]
        unit=units.get(pos["unit"])
        hp=unit.hit_points
        shot=187 if pos["unit"]=="barbarian_axe_swinger" else 207
        before=pos["survivors"]+pos["round_deaths"]
        loss_lo,loss_hi=_hp_loss_interval(
            before=before,dead=pos["round_deaths"],hp=hp,bar=pos["hp_percent"])
        wall=1 if pos["round_deaths"] else 0
        conservative=_minimum_full_shots(
            hp_loss_min=loss_lo,hp=hp,per_hit=shot,
            dead=pos["round_deaths"],wall_kills=wall,
            discard_kill_overkill=False,
        )
        strict=_minimum_full_shots(
            hp_loss_min=loss_lo,hp=hp,per_hit=shot,
            dead=pos["round_deaths"],wall_kills=wall,
            discard_kill_overkill=True,
        )
        current_am=slinger_am[i]
        entries.append({
            "physical_slot":i,
            "unit":pos["unit"],
            "before_full_COUNT_assumed":before,
            "deaths":pos["round_deaths"],
            "end_living":pos["survivors"],
            "end_HP_bar_owner_reported":pos["hp_percent"],
            "target_hp":hp,
            "weapon_accuracy":sl.primary_weapon.accuracy,
            "full_primary_damage":shot,
            "fresh_full_hits_to_kill":ceil(hp/shot),
            "overkill_discarded_per_pair_or_sextuple":ceil(hp/shot)*shot-hp,
            "HP_loss_min_IF_R77_full":loss_lo,
            "HP_loss_max_IF_R77_full":loss_hi,
            "baseline_AM_addresses":current_am,
            "generous_one_wall_kill_max":wall,
            "HP_only_optimistic_no_overkill_min_full_gun_hits":conservative,
            "strict_individual_D_overkill_lost_min_full_gun_hits":strict,
            "HP_only_min_minus_baseline":conservative-current_am,
            "D_min_minus_baseline":strict-current_am,
        })
    c1=_min_budget_with_wall_assignments(entries,strict_D=False,total_wall_shots=7)
    c2=_min_budget_with_wall_assignments(entries,strict_D=True,total_wall_shots=7)
    one_per=[
        1 if row["deaths"] else 0 for row in entries
    ]
    one_conserved=[
        _minimum_full_shots(
            hp_loss_min=row["HP_loss_min_IF_R77_full"],
            hp=row["target_hp"],per_hit=row["full_primary_damage"],
            dead=row["deaths"],wall_kills=w,discard_kill_overkill=False
        ) for row,w in zip(entries,one_per)
    ]
    one_strict=[
        _minimum_full_shots(
            hp_loss_min=row["HP_loss_min_IF_R77_full"],
            hp=row["target_hp"],per_hit=row["full_primary_damage"],
            dead=row["deaths"],wall_kills=w,discard_kill_overkill=True
        ) for row,w in zip(entries,one_per)
    ]
    # All physically occupied 7 front slots: wall cannot kill in the slot
    # showing ZERO source deaths; wall shots therefore may be ineffective.
    assert (one_conserved,one_strict)==(
        [55,25,53,53,48,55,55],[60,25,53,53,48,60,60]
    )
    assert (sum(one_conserved),sum(one_strict))==(344,359)
    assert (c1["minimum_total_primary_shots"],c2["minimum_total_primary_shots"])==(338,353)

    # A full-350 full-damage *integer HP budget* witness under one
    # hypothetical wall death in each slot with >=1 observed death.
    # This does NOT predict observed knife kill counts under D or I.
    algebraic_tickets=[55,27,54,56,48,55,55]
    assert sum(algebraic_tickets)==350
    hp_witness=[]
    for row,shots,w in zip(entries,algebraic_tickets,one_per):
        min_wall=row["HP_loss_min_IF_R77_full"]-shots*row["full_primary_damage"]
        max_wall=row["HP_loss_max_IF_R77_full"]-shots*row["full_primary_damage"]
        feasible=max(0,min_wall)<=min(row["target_hp"]*w,max_wall)
        hp_witness.append({
            "physical_slot":row["physical_slot"],
            "full_shots_ASSUMED":shots,
            "difference_from_baseline_AM":shots-row["baseline_AM_addresses"],
            "wall_total_healthy_HP_equiv_needed_interval":[min_wall,max_wall],
            "budget_feasible_WITH_ONE_DIRECT_WALL_KILL":feasible,
            "individual_KILL_COUNT_not_reconstructed":True,
        })
    assert all(v["budget_feasible_WITH_ONE_DIRECT_WALL_KILL"] for v in hp_witness)

    threshold_models={
        "carabineer_14_against_21_fresh_Axe":
            _simulate_experimental_individual_focus(
                individuals=21,hits=14,hp=1120,hit_damage=710,accuracy=70),
        "slinger_49_into_50_fresh_Knife":
            _simulate_experimental_individual_focus(
                individuals=50,hits=49,hp=360,hit_damage=207,accuracy=20),
        "slinger_55_into_50_fresh_Knife":
            _simulate_experimental_individual_focus(
                individuals=50,hits=55,hp=360,hit_damage=207,accuracy=20),
        "slinger_49_into_19_fresh_Axe":
            _simulate_experimental_individual_focus(
                individuals=19,hits=49,hp=1120,hit_damage=187,accuracy=20),
        "slinger_56_into_50_fresh_Axe":
            _simulate_experimental_individual_focus(
                individuals=50,hits=56,hp=1120,hit_damage=187,accuracy=20),
    }
    assert [v["gun_deaths"] for v in threshold_models.values()]==[7,0,5,0,0]
    return {
        "schema":1,
        "case_provenance":{
            "slinger_case_id":fixture["case_id"],
            "musket_battle_id":"land-barbarian-same-owner-battle-r1-r89-20261014",
            "same_battle":False,
            "slinger_F5_owner_confirmed":True,
            "slinger_workshop_ATK24_owner_confirmed":True,
            "musket_F5_workshop_ATK11_owner_confirmed":True,
        },
        "comparison":{
            "gun_primary_accuracy":gn.primary_weapon.accuracy,
            "slinger_primary_accuracy":sl.primary_weapon.accuracy,
            "gun_Axe_damage":710,
            "slinger_Axe_damage":187,
            "gun_full_Axe_hits_to_kill":2,
            "slinger_full_Axe_hits_to_kill":6,
            "gun_Knife_damage":730,
            "slinger_Knife_damage":207,
            "gun_full_Knife_hits_to_kill":1,
            "slinger_full_Knife_hits_to_kill":2,
            "experimental_focus_steps_before_remainingHP_below_accuracy":{
                "gun_vs_Axe":1,
                "slinger_vs_Axe":5,
                "slinger_vs_Knife":"never before second hit kills, since one hit leaves 42.5pct >Accuracy20",
            },
        },
        "R76_owner_verified_baseline":{
            "source_image":"image(20261015-062727).png",
            "front_HP_full_100pct_owner_verified":True,
            "no_slinger_before_R77_owner_verified":True,
            "R77_slingers_first_arrival_round":77,
            "R77_visible_primary_blue_ammo_sufficient_for_first_350_attempts_owner_verified":True,
            "R76_seven_wall_segments":[1]*7,
            "R76_round_deaths_LTR":[1,2,1,1,0,1,1],
            "R76_round_deaths_total":7,
            "wall_one_death_PER_SLOT_is_NOT_supported":True,
            "wall_actual_seven_attack_hit_log_not_observed":True,
        },
        "R76_to_R77_slot_population_repacking":{
            "R76_end_front_physical":prev_end,
            "R77_before_shots_physical":start_now,
            "inter_round_delta_LTR":repack,
            "axe_total_before_and_after":[169,169],
            "Knife_total_front_plus_reserve_before_and_after":[169,169],
            "partial_Axe_slot2_21_to19_and_phys3_4_each_plus1":True,
            "is_inter_round_UNIT_repacking_not_same_round_AM_shot_reroute":True,
        },
        "dimensionless_incoming_nominal_HP_pressure_CANDIDATE_NOT_RULE":{
            "gun_R84_center_Axe_14x710_div_21x1120":gun_pressure,
            "slinger_R77_partial_Axe_49x187_div_19x1120":slinger_pressure,
            "absolute_difference":abs(gun_pressure-slinger_pressure),
            "slinger_R77_full_Knife49x207_div50x360_counterexample":knife_pressure,
            "universal_pressure_threshold_is_FALSIFIED_by_full_Knife":True,
            "understrength_occupancy_gate_or_other_rule_UNVERIFIED":True,
            "actual_round_damage_post_AM_may_differ":True,
        },
        "R77_slot_HP_bounds_fresh_full_floor_bar_ONLY":entries,
        "R77_standard_350_AM_physical":list(slinger_am.values()),
        "R77_conservative_HP_only_min_full_primary_with_one_wall_each":sum(one_conserved),
        "R77_strict_D_min_full_primary_with_one_wall_each":sum(one_strict),
        "R77_allocation_optimum_with_at_most_seven_wall_one_shots":{
            "conserved_HP_no_overkill":c1,
            "strict_individual_D_with_discarded_overkill":c2,
        },
        "R77_one_INTEGER_HP_budget_witness_350_tickets":hp_witness,
        "R77_one_witness_all_HP_intervals_fit":all(v[
            "budget_feasible_WITH_ONE_DIRECT_WALL_KILL"
        ] for v in hp_witness),
        "EXPERIMENTAL_accuracy_selector_not_gameforge":EXPERIMENTAL_ACCURACY_MODEL_ID,
        "EXPERIMENTAL_accuracy_single_slot_simulations":threshold_models,
        "R77_Knife_19_deaths_vs_exp_accuracy_55hits_model_only5":
            threshold_models["slinger_55_into_50_fresh_Knife"]["gun_deaths"]==5,
        "one_shot_or_diversion_explanations_unverified":True,
        "interpretive_limits":[
            "Combined 18-ticket knife deficit matched partial Axe surplus applies only to HP-only accounting with one wall per living casualty slot, NOT to D kills; global D lower bound353 exceeds the350 address budget even with seven ideal wall 1-kills",
            "Raw HP-only witness 350 addresses fits HP intervals but does NOT reproduce casualty count from any actual per-individual allocator, so do not call it a full Gameforge simulation",
            "Slinger weapon Accuracy20 and Gun70 are known user/project weapon stats but EXACT Gameforge focusing/targeting semantics UNKNOWN",
            "Owner CONFIRMED all R76 frontline HP bars were 100% and Slingers first arrive R77: fresh pre-volley HP is now strongly sourced, barring unlogged inter-round damage. Actual per-individual target HP never instrumented",
            "Accuracy is not automatically hit/miss probability or damage scalar; current EXP accuracy function only selects a target WITHIN an addressed slot",
            "A 19-Axe slot has capacity 19×6=114 primary slinger hits to kill all full Axe, more than49 original attacks; an already-empty-slot overflow cannot explain the candidate transfer",
            "Slingers newly arrived R77 and player sees BLUE primary ammo: enough to attempt 350 first-volley primary shots; which were full damaging hits and how they target slots remain unverified",
            "R76 seven frontline deaths exactly match seven visible walls and distribution [1,2,1,1,0,1,1]; one wall kill per different slot is NOT observed even on wall-only R76. R77 wall shot targets remain unobserved",
        ],
    }


if __name__=="__main__":
    print(json.dumps(report(),ensure_ascii=False,indent=2))
