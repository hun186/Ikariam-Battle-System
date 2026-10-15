"""Research-only falsifiers for the owner's 70%-Accuracy Carabineer vs 20% Slinger case.

Compare two distinct battle/source windows, NOT the same battle:
- 400 Slinger Workshop ATT24 Forge5: R77 full frontline, 350 active sources
- 84 Carabineer Workshop ATT11 Forge5: same fight's R81-87 window

All conditional damage bounds below require:
* Every victim BEFORE R77 had FULL HP, as OWNER EXPECTED (not independently logged).
* Screenshot bar is floor(100 * SUM(living_hp)/(living_count*max_unit_hp)).
* Primary weapon FULL damage and no other damage source except up to 7
  independent direct one-unit wall kills. Shot addresses are not real hits.
* Cross-slot conservation budget is 350 source tickets, not verified ammo.

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
    source=next(x for x in fixture["rounds"] if x["round"]==77)
    slinger_am=model_am_addressed_shots_by_physical_slot(
        list(range(1,8)),[50]*7
    )
    assert list(slinger_am.values())==[49,49,49,56,49,49,49]
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
            "User's R77 initial fresh HP is an expected value, not a measured log; invalidates bounds if false",
            "Accuracy is not automatically hit/miss probability or damage scalar; current EXP accuracy function only selects a target WITHIN an addressed slot",
            "A 19-Axe slot has capacity 19×6=114 primary slinger hits to kill all full Axe, more than49 original attacks; an already-empty-slot overflow cannot explain the candidate transfer",
            "Source primary ammo5 and live slot shot count at R77 unverified; source gunning may be secondary",
            "Wall 7 hits physically targeted/one hit each is a generous assumption, not observed",
        ],
    }


if __name__=="__main__":
    print(json.dumps(report(),ensure_ascii=False,indent=2))
