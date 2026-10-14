"""Source-distinct LAND R81–89 two-target-class / wall Attack Matrix research.

This is a CONDITIONAL mathematical decomposition, NOT recovered game shots.
The owner's source confirms per-round casualties, unit type effects, HP bars,
and wall one-hit lethality; full exact unit fire/ammo and wall target selection
remain unobserved. Leave the production engine unchanged.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ikariam_battle.damage import RoundingPolicy, calculate_damage
from ikariam_battle.profiles import ForgeProfile, WorkshopProfile
from ikariam_battle.units import UnitRegistry
from tools.research.land_round80_89_am_focus_probe import (
    FIXTURE, model_am_addressed_shots_by_physical_slot,
)

ROOT = Path(__file__).resolve().parents[2]
FIRST_LINE = [1, 2, 3, 4, 5, 6, 7]


def weapon_profiles(*, attacker_forge: int = 0) -> dict:
    """Read authoritative packaged unit HP, armor, ammo and land upgrades."""
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    registry = UnitRegistry.load(include_barbarians=True)
    gun = registry.get("sulphur_carabineer")
    axe = registry.get("barbarian_axe_swinger")
    knife = registry.get("barbarian_knifeman")
    workshop, forge = WorkshopProfile.load(), ForgeProfile.load()
    attack_level = data["player_musketeer_upgrade"]["attack"]
    damage = {}
    for target in (axe, knife):
        trace = calculate_damage(
            gun, target, attack_level=attack_level, armor_level=0,
            attacker_forge=attacker_forge, defender_forge=0,
            workshop=workshop, forge=forge, rounding=RoundingPolicy.FLOOR,
        )
        assert target.hit_points is not None
        damage[target.id] = {
            "target_hp": target.hit_points,
            "target_armor": target.base_armor,
            "shot_damage": trace.final_damage,
            "shots_to_kill_full": (
                target.hit_points + trace.final_damage - 1
            ) // trace.final_damage,
            "damage_trace": trace.as_dict(),
        }
    return {
        "weapon": gun.id,
        "source_primary_ammunition_pool_per_unit_battle": gun.primary_weapon.ammunition,
        "gun_units_per_model_source_cell": 12,
        "weapon_primary_acc": gun.primary_weapon.accuracy,
        "land_workshop_attack_increase_per_level": workshop.land_increment,
        "attacker_forge_level_is_UNVERIFIED": attacker_forge,
        "barbarian_targets": damage,
        "model_only_weapon_ids_not_identified_from_per_hit_game_logs": True,
    }


def _round_result(game: dict, profiles: dict) -> dict:
    round_no = game["round"]
    if round_no < 81:
        return {
            "round": round_no,
            "source_deaths": game["attacker_barbarian_main_line_total_round_deaths"],
            "excluded_from_wall_controls": True,
            "why": "Different open-field scene, original wall attacks not pictured",
        }
    losses = game["attacker_barbarian_main_line_deaths_left_to_right"]
    active = [i+1 for i, x in enumerate(losses) if x is not None]
    gun_am = model_am_addressed_shots_by_physical_slot(active, [12] * 7)
    # MODEL HYPOTHESIS: wall hits the opposing same physical slot, one lethal
    # hit each; if the target slot is empty, all such shots redirect to
    # lowest occupied PHYSICAL position, not to next AM damage position.
    wall = {i: 1 for i in active}
    wall[min(active)] += 7 - len(active)
    ordinary = {i: losses[i-1] for i in active if i != 4 or round_no >= 88}
    axe_kills = losses[3] if 4 in active and round_no < 88 else 0
    # With the wall assumption every occupied knife position already gets
    # one wall kill. A further ordinary death requires one gun hit.
    gun_ordinary_required = sum(ordinary[i] - wall[i] for i in ordinary)
    total_gun_shots = sum(gun_am.values())
    center_gun_shots_left = total_gun_shots - gun_ordinary_required
    axe_wall_kills = wall.get(4, 0) if axe_kills else 0
    axe_gun_kills = axe_kills - axe_wall_kills
    model_knife_gun_by_slot = {i: ordinary[i]-wall[i] for i in ordinary}
    gun_differences = {
        i: model_knife_gun_by_slot[i] - gun_am[i] for i in ordinary
    }
    # FORGE0 / SEVEN EXCLUSIVE FULL HITS COUNTERFACTUAL ONLY.
    # If each full gun hit does less than target HP but two such hits kill,
    # minimum one-hit-ready wound-bearing axe men needed to kill k targets
    # in fewer than 2k shots is 2k-shots (best-case no wasted hits).
    min_prior_wounded = max(0, 2*axe_gun_kills-center_gun_shots_left)
    axe_damage = profiles["barbarian_targets"]["barbarian_axe_swinger"]
    min_prior_damage_per_wounded = (
        axe_damage["target_hp"]-axe_damage["shot_damage"]
    )
    min_prior_existing_damage = min_prior_wounded * min_prior_damage_per_wounded
    return {
        "round": round_no,
        "observed_deaths": game["attacker_barbarian_main_line_total_round_deaths"],
        "observed_deaths_by_occupied_slot": {str(i): losses[i-1] for i in active},
        "modeled_84_musket_AM_by_slot": {str(i): gun_am[i] for i in active},
        "hypothetical_seven_direct_wall_kills_by_slot": {str(i): wall[i] for i in active},
        "ordinary_knife_gun_shots_implied_if_one_shot_kill_each": gun_ordinary_required,
        "gun_ordinary_minus_unmodified_AM": {
            str(i): v for i,v in gun_differences.items()
        },
        "available_total_gun_shots_IN_MODEL": total_gun_shots,
        "gun_shots_left_for_center_axe_AFTER_knife_kills": center_gun_shots_left,
        "center_axe_user_reported_deaths": axe_kills,
        "axe_conditional_wall_kills": axe_wall_kills,
        "axe_gun_kills_required": axe_gun_kills,
        "minimum_near_lethal_wounded_axes_at_round_start": min_prior_wounded,
        "minimum_initial_carryover_axe_damage_to_support_one_row_shift": min_prior_existing_damage,
        "wound_lower_bound_is_forge0_exclusive_hit_counterfactual_ONLY": True,
        "individual_axe_hit_concentration_is_UNVERIFIED": True,
        "conditional_exact_one_AM_row_shift_center_to_leftmost": (
            round_no in (84,85,86,87)
            and gun_differences.get(1)==7
            and all(v==0 for i,v in gun_differences.items() if i!=1)
            and gun_am.get(4,0)-center_gun_shots_left==7
        ),
        "observation_not_proof": (
            "The 7-hit reassignment is an arithmetic explanation contingent "
            "on all 84 original gun hits + seven separate one-kill wall attacks "
            "at assumed wall slots, and knife hits all one-shot. The actual "
            "wall addressing and individual Axe wounds have not been observed."
        ),
    }


def report() -> dict:
    source = json.loads(FIXTURE.read_text(encoding="utf-8"))
    p = weapon_profiles()
    rows = [_round_result(o,p) for o in source["observations"]]
    axe_hp = p["barbarian_targets"]["barbarian_axe_swinger"]["target_hp"]
    preceding = {x["round"]: x for x in source["observations"]}
    for row in rows:
        r=row["round"]
        if r < 84 or r > 87:
            continue
        prev = preceding[r-1]
        survivors=prev["central_position_4_axe_bearer_remaining_units"]
        bar=prev["attacker_main_line_front_survivor_hp_percent_left_to_right"][3]
        minimum_damage=row["minimum_initial_carryover_axe_damage_to_support_one_row_shift"]
        max_avg_hp_percent_if_minimum_wound = (
            100*(1-minimum_damage/(survivors*axe_hp))
            if survivors else None
        )
        row["previous_round_observed_center_hp_bar_percent"]=bar
        row["previous_round_center_survivors_from_screenshot"]=survivors
        row["max_possible_previous_center_average_hp_if_minimum_wounds_percent"] = max_avg_hp_percent_if_minimum_wound
        row["counterfactual_HP_bar_conflict_IF_no_HP_state_transition"] = (
            max_avg_hp_percent_if_minimum_wound is not None
            and max_avg_hp_percent_if_minimum_wound < bar
        )
        row["same_survivor_population_and_interround_HP_continuity_VERIFIED"] = False
        row["floor_survivor_average_bar_semantics_VERIFIED"] = False
        row["forge0_exclusive_hit_model_represents_actual_battle"] = False
        row["incompatible_IF_bar_floors_average_of_survivor_HP"] = False
    sensitivity = {
        str(level): weapon_profiles(attacker_forge=level)
        for level in sorted(ForgeProfile.load().levels)
        if level > 0
    }
    return {
        "schema_version":2,
        "evidence_class":"RESEARCH_ONLY_CONDITIONAL_TWO_TARGET_CLASS_ONE_KILL_WALL_DECOMPOSITION",
        "unit_identity_provenance": source["unit_identity_provenance"],
        "forge_active_level_unknown": True,
        "sensitivity_cases_only_not_actual_forge": sensitivity,
        "pdf_source_limitations": {
            "provenance": "AT Barbarossa and Xanto 2020 community pre-v13 reverse engineering, not authoritative modern formula",
            "RR": "inter-round same-wave survivors damage may redistribute across slots and reserve",
            "SR": "within addressed target slot between firing lines, not universal",
            "IR": "within addressed target slot between shots, not universal",
            "one_shot_cross_slot_damage": "NOT_PROVEN_BY_THE_PAPER",
        },
        "source":source["source"],
        "user_confirmed_wall":source.get("wall_attack_followup"),
        "actual_game_forge_record":source.get("player_forge"),
        "user_distributed_damage_correction":source.get("single_shot_distribution_correction"),
        "forge0_damage_report_is_counterfactual_only":True,
        "seven_exclusive_center_hits_is_not_confirmed":True,
        "prewounded_axe_count_is_conditional_not_observed":True,
        "unit_damage_from_current_profiles":p,
        "conditional_assumptions":[
            "The 7x12 lower formation is precisely the unit type sulphur_carabineer",
            "All 84 source musketeers still have ammunition and execute one successful primary gun hit this round",
            "All seven wall sections each execute exactly one successful attack that kills exactly one barbarian",
            "Wall targeting is one opposing physical slot each and all missing-target shots go to leftmost occupied PHYSICAL position",
            "All knife hits that count as casualties are gun one-shot kills (the 635>360 profile comparison)",
            "In the Forge0 control 14 hits kill seven fresh Axe only IF the 14 are paired on seven individual axes; 14 distinct recipients can yield zero kills. Individual concentration is UNVERIFIED.",
            "Real Forge is active but level not observed: Forge0 615 Axe/635 knife is counterfactual only, and alternative active levels are sensitivity tests",
            "Seven-center-gun and previous-wound deductions require full exclusive same-cell gun hits, fixed wall assignment, no SR/IR/RR, unchanged HP state and no additional sources",
            "No other source classes, no hidden extra gun shots, wall effects or final damage transfer",
            "Displayed center HP bar is unknown denominator/rounding; average-live-HP calculations are conditional",
        ],
        "rounds":rows,
        "falsification_guide":[
            "R81-83 deaths have ONE feasible allocation with paired 14 hits on seven fresh axes plus conditional wall hits; 14 addresses DO NOT guarantee seven axe deaths",
            "R84-87 7 extra knife deaths at physical slot 1 correspond to one 7-shot AM row; source of deviation is UNVERIFIED",
            "R86 at-least-3 prewounded axes and 505 damage each apply ONLY to Forge0 seven-exclusive-center-hit, fixed-wall no-spread control; previous HP clash additionally needs identical populations, no RR/healing/rebuild/interround transfer and verified bar floor/timing. Not a real-battle lower bound",
            "R88 6 occupied: 14 gun shots each, and proposed wall 2 to physical leftmost and 1 each other gives 16/15/15/15/15/15",
            "R89 4 occupied: 21 gun shots each, and proposed wall 4 to physical leftmost and 1 each other gives 25/22/22/22",
            "Primary musket ammunition from packaged profile is 3 shots per unit; sustaining identical 84 primary shots for nine consecutive rounds would require a changing source/ammo state, unobserved fresh waves or other weapon identification; the full sequence is NOT replicated",
        ]
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    arg=ap.parse_args()
    data=report()
    arg.output.parent.mkdir(parents=True,exist_ok=True)
    arg.output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    p=data["unit_damage_from_current_profiles"]["barbarian_targets"]
    print("Gun under Forge0: knife damage",p["barbarian_knifeman"]["shot_damage"],"axe damage",p["barbarian_axe_swinger"]["shot_damage"])
    for r in data["rounds"]:
        if r.get("excluded_from_wall_controls"):
            continue
        print("R",r["round"],"guns for knives",r["ordinary_knife_gun_shots_implied_if_one_shot_kill_each"],"for axe",r["gun_shots_left_for_center_axe_AFTER_knife_kills"],"near-lethal prior wounds >=",r["minimum_near_lethal_wounded_axes_at_round_start"],"one-row diversion?",r["conditional_exact_one_AM_row_shift_center_to_leftmost"])
    print("Model controls not official Gameforge wall fire or Accuracy!")
if __name__=="__main__":
    main()
