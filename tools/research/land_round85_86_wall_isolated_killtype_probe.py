"""Research-only R85->R86 gun kill-type discriminant with wall D-kills isolated.

This is NOT a Gameforge executable algorithm, production damage rule, or
official Kill Type selector. Wall kill counts/targets, gun shot count and
displayed HP semantics are conditional assumptions. The owner's Forge5
is confirmed. See the matching regression tests and LAND calibration note.
"""
from __future__ import annotations

import json
from math import ceil

from tools.research.land_round80_89_am_focus_probe import (
    FIXTURE, model_am_addressed_shots_by_physical_slot,
)
from tools.research.land_round80_89_hp_state_probe import (
    floor_survivor_hp_bar_damage_interval,
)
from tools.research.land_round80_89_two_class_am_probe import weapon_profiles


def minimum_prior_wounds_for_individual_direct_kills(
    *, gun_hits: int, gun_kills: int, unit_hp: int, full_hit_damage: int
) -> dict:
    """Restricted individual D-kill focus: two whole hits or one on a prior-injured victim.

    Each hit damages only one individual, no P/IR/RR, no overkill reuse;
    each victim taking only one hit must already lack >= HP-hit_damage.
    This is NOT a universal property of Gameforge kill calculations.
    """
    if not all(isinstance(n, int) and n >= 0 for n in (gun_hits, gun_kills)):
        raise ValueError("hits/kills must be nonnegative integers")
    if not 0 < full_hit_damage < unit_hp <= 2 * full_hit_damage:
        raise ValueError("restricted formula requires exactly 2 hits for fresh kill")
    minimum_one_hit_ready = max(0, 2 * gun_kills - gun_hits)
    return {
        "minimum_preinjured_one_hit_victims": minimum_one_hit_ready,
        "minimum_preexisting_aggregate_wounds": (
            minimum_one_hit_ready * (unit_hp - full_hit_damage)
        ),
        "exclusively_single_target_full_hits": True,
        "no_redistribution_or_other_damage": True,
    }


def separated_wall_and_pooled_guns(
    *, starting_units: int, unit_hp: int, starting_wounds: int,
    direct_wall_kills: int, wounds_removed_with_wall_victims: int,
    gun_hits: int, gun_full_hit_damage: int,
) -> dict:
    """Hypothetical lossless pooled slot: wall removes killed unit AND its old wounds.

    The wall has NO added numeric damage in the gun pool. Then gun shots
    contribute their full damage and the pool converts HP to casualties,
    keeping all nonlethal remainder. This differs from strict paper I-kill
    (which was described for divisible attack totals) and from individual
    D-kill. Neither timing nor conserved overkill is official Gameforge behavior.
    """
    params=(starting_units,unit_hp,starting_wounds,direct_wall_kills,
            wounds_removed_with_wall_victims,gun_hits,gun_full_hit_damage)
    if not all(isinstance(n,int) for n in params):
        raise ValueError("integral inputs required")
    if not (starting_units>0 and unit_hp>0 and 0<=direct_wall_kills<=starting_units
            and 0<=starting_wounds<=starting_units*(unit_hp-1)
            and 0<=wounds_removed_with_wall_victims<=min(
                starting_wounds,direct_wall_kills*(unit_hp-1)
            ) and gun_hits>=0 and gun_full_hit_damage>0):
        raise ValueError("invalid slot/wound configuration")
    after_wall=starting_units-direct_wall_kills
    wounds_after_wall=starting_wounds-wounds_removed_with_wall_victims
    if wounds_after_wall>after_wall*(unit_hp-1):
        raise ValueError("wounds cannot be held by surviving wall targets")
    total_pool=wounds_after_wall+gun_hits*gun_full_hit_damage
    gun_kills=min(after_wall,total_pool//unit_hp)
    survivors=after_wall-gun_kills
    raw_remnant=total_pool-gun_kills*unit_hp
    remnant=raw_remnant if survivors else None
    if survivors and remnant>survivors*(unit_hp-1):
        raise ValueError("survivor pool exceeds living capacity under model")
    display_bar=(
        (100*(survivors*unit_hp-remnant))//(survivors*unit_hp)
        if survivors else None
    )
    return {
        "model":"HYPOTHETICAL_WALL_DIRECT_ONE_KILL_PLUS_CONSERVED_GUN_SLOT_POOL",
        "wall_kills":direct_wall_kills,
        "wall_wound_damage_added_to_gun_pool":0,
        "previous_wounds_removed_with_wall_victims":wounds_removed_with_wall_victims,
        "gun_hits":gun_hits,
        "gun_hit_damage":gun_full_hit_damage,
        "gun_kills":gun_kills,
        "all_casualties":direct_wall_kills+gun_kills,
        "survivors":survivors,
        "survivor_wounds":remnant,
        "floor_survivor_mean_bar":display_bar,
        "gun_overkill_retention_assumed":True,
        "official_game_mechanism_verified":False,
    }


def report() -> dict:
    src=json.loads(FIXTURE.read_text(encoding="utf-8"))
    obs={x["round"]:x for x in src["observations"]}
    previous,current=obs[85],obs[86]
    assert src["player_forge"]["level_verified"] and src["player_forge"]["level"]==5
    hp=weapon_profiles(attacker_forge=5)["barbarian_targets"]["barbarian_axe_swinger"]["target_hp"]
    forge5=weapon_profiles(attacker_forge=5)
    atk=forge5["barbarian_targets"]["barbarian_axe_swinger"]["shot_damage"]
    n=previous["central_position_4_axe_bearer_remaining_units"]
    killed=current["central_position_4_axe_bearer_deaths"]
    survivors=current["central_position_4_axe_bearer_remaining_units"]
    before_bar=previous["attacker_main_line_front_survivor_hp_percent_left_to_right"][3]
    after_bar=current["attacker_main_line_front_survivor_hp_percent_left_to_right"][3]
    assert (n,killed,survivors,before_bar,after_bar)==(11,6,5,92,96)
    before_range=floor_survivor_hp_bar_damage_interval(n,hp,before_bar)
    after_range=floor_survivor_hp_bar_damage_interval(survivors,hp,after_bar)
    # CURRENT ENGINE AM baseline with 7 source cells x 12 shots and all seven
    # target slots occupied is 14 ADDRESSES to the center, never 7.
    baseline_am = model_am_addressed_shots_by_physical_slot(
        list(range(1, 8)), [12] * 7
    )
    assert baseline_am == {1: 7, 2: 14, 3: 14, 4: 14, 5: 14, 6: 14, 7: 7}
    # DISTINCT, UNPROVEN hypothetical source-row diversion: move one group
    # of seven addresses from central Axe (physical4) to leftmost Knife (1).
    diverted_am = dict(baseline_am)
    diverted_am[4] -= 7
    diverted_am[1] += 7
    assert diverted_am == {1: 14, 2: 14, 3: 14, 4: 7, 5: 14, 6: 14, 7: 7}
    # Only with that diversion AND full effective exclusive hits is the
    # previous seven-center-shot pool witness even applicable. AM addresses
    # are not automatically successful damaging hits or casualties.
    # We independently vary assumed effective wall attacks to this slot.
    controls=[]
    for wall_kills in range(4):
        gun_kills=killed-wall_kills
        bound=minimum_prior_wounds_for_individual_direct_kills(
            gun_hits=7,gun_kills=gun_kills,unit_hp=hp,full_hit_damage=atk
        )
        controls.append({
            "hypothetical_wall_kills":wall_kills,
            "gun_kills_required":gun_kills,
            "conditional_seven_center_full_gun_hits":7,
            **bound,
            "compatible_with_R85_floor_mean_wound_budget_IF_unchanged_population":(
                bound["minimum_preexisting_aggregate_wounds"]<=before_range[1]
            ),
        })
    witness=separated_wall_and_pooled_guns(
        starting_units=11, unit_hp=hp, starting_wounds=900,
        direct_wall_kills=1, wounds_removed_with_wall_victims=70,
        gun_hits=7,gun_full_hit_damage=atk,
    )
    assert (witness["all_casualties"],witness["survivors"],
            witness["survivor_wounds"],witness["floor_survivor_mean_bar"]) == (6,5,200,96)
    baseline_fourteen_full_hit_control = separated_wall_and_pooled_guns(
        starting_units=11, unit_hp=hp, starting_wounds=900,
        direct_wall_kills=1, wounds_removed_with_wall_victims=70,
        gun_hits=baseline_am[4], gun_full_hit_damage=atk,
    )
    assert (
        baseline_fourteen_full_hit_control["all_casualties"],
        baseline_fourteen_full_hit_control["survivors"],
        baseline_fourteen_full_hit_control["survivor_wounds"],
        baseline_fourteen_full_hit_control["floor_survivor_mean_bar"],
    ) == (10, 1, 690, 38)
    # This rejects ONLY the hypothetical combination: baseline 14 addresses
    # ALL succeed as full 710-point hits, same lossless pool and chosen old
    # wounds/wall target. It does NOT disprove 14 AM addresses in the real game.
    # Fixed identical hypothetical 900/70 prior-wound state; sensitivity
    # only tests whether a new hit magnitude crosses an aggregate HP threshold.
    sensitivity=[]
    for lv in range(6):
        prof=weapon_profiles(attacker_forge=lv)
        dmg=prof["barbarian_targets"]["barbarian_axe_swinger"]["shot_damage"]
        out=separated_wall_and_pooled_guns(
            starting_units=11,unit_hp=hp,starting_wounds=900,
            direct_wall_kills=1,wounds_removed_with_wall_victims=70,
            gun_hits=7,gun_full_hit_damage=dmg,
        )
        sensitivity.append({
            "forge_level_comparator":lv,
            "damage_to_axe":dmg,
            "gun_kills_in_same_hypothetical_pool":out["gun_kills"],
            "remaining_survivors":out["survivors"],
            "result_bar_if_five_survive":out["floor_survivor_mean_bar"] if out["survivors"]==5 else None,
            "historically_real_forge":lv==5,
        })
    return {
        "schema_version":1,
        "scope":"LAND R85->R86 center Axe only; ordinary Knife leftmost cross-slot behavior separate",
        "owner_confirmed": {
            "forge":5,"R85_center_axes":n,"R85_bar":before_bar,
            "R86_center_axe_deaths":killed,"R86_center_axes":survivors,
            "R86_bar":after_bar,
        },
        "current_packaged_effective_gun_damage_to_axe":atk,
        "CURRENT_ENGINE_AM_7x12_all_seven_targets_baseline":{
            "physical_slot_1_to_7_addresses":{
                str(i):baseline_am[i] for i in range(1,8)
            },
            "center_physical_4_address_count":baseline_am[4],
            "these_addresses_are_real_full_successful_hits_VERIFIED":False,
        },
        "HYPOTHETICAL_seven_address_diversion_center_to_leftmost":{
            "physical_slot_1_to_7_addresses":{
                str(i):diverted_am[i] for i in range(1,8)
            },
            "center_physical_4_address_count":diverted_am[4],
            "leftmost_physical_1_added_addresses":7,
            "actual_Gameforge_diversion_VERIFIED":False,
        },
        "floor_survivor_mean_bar_UNVERIFIED":True,
        "hypothetical_R85_total_survivor_wounds_range":list(before_range),
        "hypothetical_R86_total_survivor_wounds_range":list(after_range),
        "individual_D_kill_with_seven_hits_wall_kill_controls":controls,
        "restricted_D_kill_one_wall_seven_guns_INCOMPATIBLE_with_92pct_IF_no_wound_inflow":True,
        "baseline_14_addresses_AS_IF_14_full_hits_lossless_pool_CONTROL":{
            "conditional_previous_total_wounds":900,
            "conditional_wall_victim_old_wounds":70,
            "result":baseline_fourteen_full_hit_control,
            "matches_observed_R86_deaths6_remaining5_bar96":False,
            "warning":"Disproves only the 14 FULL EFFECTIVE HITS + lossless gun pool + chosen wall/old wounds model, not 14 AM address count",
        },
        "pool_model_one_wall_seven_guns_WITNESS":{
            "assumed_R85_wounds":900,
            "assumed_preexisting_wounds_on_wall_victim":70,
            "retained_prior_wounds_after_wall_kill":830,
            "gun_added_damage":7*atk,
            "five_gun_kills_consume_HP":5*hp,
            **witness,
        },
        "comparison_by_forge_level_IN_SAME_HYPOTHETICAL_POOL":sensitivity,
        "aggregate_hit_damage_threshold_for_five_gun_kills":ceil(
            (5*hp-(900-70))/7
        ),
        "candidate_switch_features_not_proven_conditions":[
            "target HP and armor; effective attack per full hit",
            "shots_to_kill_fresh=ceil(HP/attack); prior injury thresholds",
            "attack group/AM row length; divisibility of group damage by HP",
            "potential wasted overkill versus conserved pool",
            "slot occupancy, source phase, eligible targets and cross-slot spill",
            "weapon Accuracy: possible gating/redistribution selector but mechanism UNKNOWN",
            "available ammunition and observed attack count vs AM addresses",
        ],
        "paper_caveats":{
            "1_kill":"paper one-shot one-target death, appropriate simplified wall model; distinct from multi-attack D-kill",
            "D_kill":"several attacks concentrated on an individual until lethal; no survivor overkill per paper",
            "I_kill":"paper described aggregation only for EXACT divisibility; our 5800 pool /1120 is NOT proof of I-kill",
            "P_kill":"retention of excess damage is a possible alternative but not synonymous with a confirmed full slot pool",
            "IR_kill":"within addressed slot, damage may be redistributed between attacks",
            "cross_slot":"paper section13 discusses excess damage exceeding weak slot capacity and other slots; exact algorithm open",
            "wall_kill":"candidate one-shot 1-kill per EFFECTIVE wall hit as user-supported; owner called it D-kill informally, paper distinguishes from multi-hit D-kill; number of central wall hits not observed",
            "version":"2020 community paper pre-v13; 2025 followup says AM/redistribution ideas persist but old unit values changed",
        },
        "AM_distinction":"Project baseline is 14 CENTER AM ADDRESSES. The seven-effective-hit witness requires unverified seven-address rerouting, or a separate reduction in effective damaging hits.",
        "unknowns":[
            "No verified wall central-slot target count or attack chronology",
            "No verified floor-average HP-bar rule or unchanged identity/wound transfer",
            "No individual shot log, gun rounds/ammunition certainty or official Kill Type dispatcher",
            "Both numerical models are falsifiable counterfactuals, not recovered game code",
            "Leftmost 7 additional Knife deaths are a separate AM / cross-slot puzzle",
        ],
    }


if __name__=="__main__":
    print(json.dumps(report(),ensure_ascii=False,indent=2))
