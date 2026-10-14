"""400 Slinger Attack Workshop24: four observed R77..R80 Barbarian snapshots.

Read-only inverse constraints. Does NOT identify actual slinger ammo, Forge,
real Gameforge hit path, wall targets or HP-bar semantics. In particular R77
'100% before battle hit' and R79 rear 100% are owner hypotheses/screenshots,
NOT observed exact pre-phase per-individual HP values.
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
            "slinger_forge_control_NOT_CONFIRMED":forge_level,
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
            "source_real_ammo_and_Forge_unknown":True,
        })
    return {
        "schema_version":1,
        "kind":"FOUR_ROUND_400_SLINGER_SAME_BATTLE_COUNT_AND_HP_CONSTRAINTS",
        "case_id":j["case_id"],
        "battle_id":j["battle_identity"]["battle_id"],
        "user_slinger_workshop_attack_level":24,
        "user_slinger_total":400,
        "seven_visible_active_firing_cells":[50]*7,
        "reserve":50,
        "actual_forge_active_level_UNKNOWN":True,
        "target_HP":{"axe":hA,"knife":hK,"rear_axe_thrower":hR},
        "real_hp_bar_floor_mean_rule_VERIFIED":False,
        "owner_R77_front_start_full_100pct_NOT_CONFIRMED":True,
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
        "per_hit_forge_comparison_PRIMARY_only":budget,
        "central_caveat":"R80 29 rear AxeThrower deaths and 65/61/61/65/61 HP while front Axe114 all die is consistent with shifting attack damage to rear after/beside frontline collapse; source-of-rear-hit timing and direct AM cross-line fallthrough UNVERIFIED.",
        "hypotheses_to_compare":[
            "Integer conserved Slot wounds and RR interround damage vs individual D-kill with wounds retained",
            "AM regroup target slot count 7→4→3, distinct from incoming 350 attacks and screenshots showing 50+50+14 after regroup",
            "Target-class change Axe HP1120/armor20 → Axe Thrower HP320/armor0 when frontline clears R80",
            "Can same complete shot pool transfer attacks from front to rear inside one firing phase? Current engine frozen-target vs Gameforge UNKNOWN",
            "Test Forge5 primary 187/207 vs Forge0 160/180; owner did not confirm Forge for this separate Slinger battle",
            "Primary ammunition 5 and arrival/replenishment before R77 unknown: cannot assume every 50 displayed Slinger shoots full primary",
            "Accuracy20 percent must not be blindly implemented as independent 20pct random hits; kill/wound allocator still unknown",
            "R77 100pct preattack only owner's likely expectation; R79 rear full HP screenshot visual but not precise 100pct certification",
        ]
    }


if __name__=="__main__":
    print(json.dumps(report(),ensure_ascii=False,indent=2))
