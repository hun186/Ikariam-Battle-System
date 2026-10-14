"""Land R80-89 conditional WALL + MUSKETEER source decomposition.

The owner confirmed each effective high-level wall shot kills ONE Barbarian.
The game has NOT confirmed seven actual attacks, their target addresses,
or exactly 84 successful musket hits. These controls are NOT production rules.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.research.land_round80_89_am_focus_probe import (
    FIXTURE, model_am_addressed_shots_by_physical_slot,
)


def hypothetical_wall_kills_by_slot(
    active_slots: list[int], sections: int = 7,
) -> dict[int, int]:
    """ILLUSTRATIVE (not official) placement: once each, excess to first slot.

    This is *one* possible allocation of seven successful lethal wall shots
    across 7/6/4 live enemy target slots. It is not the game's damage priority.
    """
    if len(active_slots) == 0 or sections < len(active_slots):
        raise ValueError("Need >=one hypothetical wall shot per target")
    if len(set(active_slots)) != len(active_slots):
        raise ValueError("Duplicate active target slots")
    a = dict.fromkeys(sorted(active_slots), 1)
    a[min(a)] += sections - len(active_slots)
    return a


def build_report() -> dict:
    src = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if not src.get("wall_attack_followup", {}).get(
        "user_confirmed_each_effective_wall_hit_kills_one_barbarian"
    ):
        raise ValueError("Unconfirmed wall lethality assumption")
    result = []
    for game in src["observations"]:
        active = [
            i+1 for i, killed in enumerate(
                game["attacker_barbarian_main_line_deaths_left_to_right"]
            ) if killed is not None
        ]
        current_AM = model_am_addressed_shots_by_physical_slot(active, [12]*7)
        source_deaths = {
            pos: game["attacker_barbarian_main_line_deaths_left_to_right"][pos-1]
            for pos in active
        }
        # Round 80 has NO corresponding 7-wall configuration and different
        # actual source layout. We never claim 84 musket hits at round 80.
        if game["round"] == 80:
            result.append({
                "round": 80, "source_deaths": source_deaths,
                "observed_total_deaths": sum(source_deaths.values()),
                "wall_shot_kill_model": None,
                "gun_kills_conditional": None,
                "cannot_compare_to_7_walled_84_gun_budget": True,
                "source": "USER_CONFIRMED_ROUND_DEATHS_ONLY",
            })
            continue

        wall = hypothetical_wall_kills_by_slot(active)
        # Competing UNSUPPORTED test: treat wall attacks as if they shared
        # the existing LAND AM row-major source/target ordering.
        wall_am = model_am_addressed_shots_by_physical_slot(active, [1]*7)
        gun = {p:source_deaths[p]-wall[p] for p in active}
        residual = {p:gun[p]-current_AM[p] for p in active}
        gun_am_wall = {p:source_deaths[p]-wall_am[p] for p in active}
        residual_am_wall = {p:gun_am_wall[p]-current_AM[p] for p in active}
        result.append({
            "round": game["round"],
            "source": "USER_CONFIRMED_ROUND_DEATHS_PLUS_CONDITIONAL_WALL_HYPOTHESIS",
            "active_barbarian_front_slots": active,
            "user_confirmed_deaths_per_slot": source_deaths,
            "observed_total_deaths": sum(source_deaths.values()),
            "hypothetical_musket_AM_addresses": current_AM,
            "hypothetical_wall_source_sections": 7,
            "hypothetical_wall_one_shot_one_kill": True,
            "hypothetical_wall_slot_kills_NOT_OBSERVED": wall,
            "alternate_wall_same_AM_target_policy_NOT_OFFICIAL": wall_am,
            "alternate_wall_AM_derived_gun_kills": gun_am_wall,
            "alternate_wall_AM_derived_gun_kills_minus_musket_AM": residual_am_wall,
            "wall_total_kills_IF_ALL_SEVEN_FIRE": sum(wall.values()),
            "derived_musket_kills_after_subtracting_wall_NOT_OBSERVED": gun,
            "derived_musket_kill_total": sum(gun.values()),
            "derived_musket_kill_total_minus_84_modeled_shots": sum(gun.values())-84,
            "derived_musket_kills_minus_frozen_AM_address_NOT_REAL_HITS": residual,
            "all_slot_derived_musket_kills_within_frozen_AM_addresses": all(
                gun[p] <= current_AM[p] for p in active
            ),
            "total_deaths_equals_84_plus_7": sum(source_deaths.values()) == 91,
            "hypothetical_wall_policy": (
                "ONE kill per occupied target plus (7-active_slot_count) extra "
                "kills assigned to LEFTMOST occupied slot ONLY for an algebraic "
                "control, NOT official Gameforge wall target priority"
            ),
            "evidence_limits": (
                "Wall single-hit lethal effect is user stated. Seven effective "
                "wall attacks, targeting and 84 fully successful musket shots "
                "are NOT measured. A musket AM address is not a lethal hit; "
                "positive slot residual requires reassignment/other sources/"
                "wrong policy. Current engine wall offensive Accuracy unresolved."
            ),
        })
    return {
        "schema_version": 1,
        "evidence_class": "RESEARCH_ONLY_WALL_AND_GUN_TWO_SOURCE_HYPOTHETICAL_DECOMPOSITION",
        "owner_verified_source": src["source"],
        "owner_wall_followup": src["wall_attack_followup"],
        "rounds": result,
        "source_count_assumptions_not_game_shot_log": {
            "musket_source_counts_per_column": [12]*7,
            "musket_model_shots_total": 84,
            "wall_sections_visible_in_walled_rounds": 7,
            "wall_model_single_successful_kill_per_section": True,
            "wall_target_distribution_is_UNOBSERVED": True,
            "open_field_round_80_is_not_reconstructed": True,
        },
        "central_treatment_findings": {
            "rounds_81_83": "AM center14, wall hypothesis1, user center deaths8 => modeled gun kills7; remaining seven addresses need not cause a death",
            "rounds_84_87": "outer left slot user15 versus hypothetical 7 AM+1 wall => +7 extra kills; fixed AM and one-per-slot wall cannot explain without additional redistribution/sources",
            "rounds_88_89": "both have 91 source deaths; the post-hoc leftmost-extra wall distribution gives EXACT 84 modeled musket one-kill-per-shot allocation; this is NOT proof of wall target priority, while a competing row-major wall AM produces nonzero per-slot residuals",
        },
        "official_wall_target_selection_algorithm_verified": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    data = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n",encoding="utf-8")
    for r in data["rounds"]:
        if r["round"] == 80:
            print("round=80: no comparable seven-wall source model")
            continue
        print(f"round={r['round']} deaths={r['observed_total_deaths']} "
              f"conditional_wall={r['wall_total_kills_IF_ALL_SEVEN_FIRE']} "
              f"conditional_musket_kills={r['derived_musket_kill_total']} "
              f"AM_residuals={list(r['derived_musket_kills_minus_frozen_AM_address_NOT_REAL_HITS'].values())}")
    print("CAUTION: wall source count/position is NOT real Gameforge shot telemetry")


if __name__ == "__main__":
    main()
