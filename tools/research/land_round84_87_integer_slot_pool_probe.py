"""Research-only falsifiable integer slot-pool candidate for Land R84-R87.

Matches the owner's proposed 7 effective gun hits to the central Axe under a
HYPOTHETICAL AM source-row reroute. Baseline project AM still addresses center
14 times; this program does NOT claim that Gameforge redirects 7 addresses, or
that the game's actual Kill Type uses pooled integer floor/rem arithmetic.

Wall 1-kill is applied AFTER gun damage and pool equalization in this
candidate. It removes a minimally wounded integer unit (floor of the slot's
remaining wound total divided by living post-gun units). Source wall ordering
and slot/individual damage distribution are NOT observed facts.

Only read-only inverse research: never import or modify production engine
behavior beyond reading the project profile and baseline AM function.
"""
from __future__ import annotations

import json

from tools.research.land_round80_89_am_focus_probe import (
    FIXTURE, model_am_addressed_shots_by_physical_slot,
)
from tools.research.land_round80_89_two_class_am_probe import weapon_profiles


def compute_candidate(
    *, first_round_end_wounds: int = 25, effective_center_gun_hits: int = 7,
    wall_direct_kills_per_round: int = 1,
) -> dict:
    """Integer full-HP capacity / retained-wound pool, no per-round tuning."""
    evidence = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert evidence["player_forge"]["level_verified"]
    forge_level = evidence["player_forge"]["level"]
    profiles = weapon_profiles(attacker_forge=forge_level)
    axe = profiles["barbarian_targets"]["barbarian_axe_swinger"]
    hp, gun_damage = axe["target_hp"], axe["shot_damage"]
    obs = {item["round"]: item for item in evidence["observations"]}
    start = obs[83]
    n = start["central_position_4_axe_bearer_remaining_units"]
    w = first_round_end_wounds
    if n != 21 or hp != 1120 or gun_damage != 710:
        raise ValueError("Unexpected research fixture/profile; re-evaluate source")
    if not 0 <= w <= n * hp or effective_center_gun_hits < 0:
        raise ValueError("Invalid starting wounds or assumed gun shots")
    baseline = model_am_addressed_shots_by_physical_slot(
        list(range(1,8)), [12] * 7,
    )
    if baseline != {1:7, 2:14, 3:14, 4:14, 5:14, 6:14, 7:7}:
        raise ValueError("Baseline project AM addressing changed")
    displayed_83 = 100*(n*hp-w)//(n*hp)
    rows = []
    for rnd in (84,85,86,87):
        previous_n, previous_w = n, w
        gun_incoming = effective_center_gun_hits * gun_damage
        pool = w + gun_incoming
        gun_kills = min(n, pool // hp)
        after_gun = n - gun_kills
        excess_after_gun = pool - gun_kills * hp
        if after_gun and excess_after_gun >= after_gun * hp:
            raise ValueError("Survivor damage pool exceeds capacity")
        # HYPOTHESIS: the wall kills one of the least-wounded post-gun
        # survivors from a near-equal integer wound redistribution.
        if wall_direct_kills_per_round > after_gun:
            raise ValueError("More direct wall kills than survivors")
        removed_old_wounds = 0
        if wall_direct_kills_per_round:
            quotient, remainder = divmod(excess_after_gun, after_gun)
            # Minimum possible wound for each of the wall victims in this
            # near-equal distribution (floor share, with integer remainder).
            removed_old_wounds = quotient * wall_direct_kills_per_round
            if wall_direct_kills_per_round > after_gun - remainder:
                removed_old_wounds += (
                    wall_direct_kills_per_round - (after_gun - remainder)
                )
        n = after_gun - wall_direct_kills_per_round
        w = excess_after_gun - removed_old_wounds if n else 0
        if not 0 <= w <= n*(hp-1):
            raise ValueError("Impossible living wound state")
        bar = (100*(n*hp-w)//(n*hp)) if n else 0
        source = obs[rnd]
        observed_n = source["central_position_4_axe_bearer_remaining_units"]
        observed_kills = source["central_position_4_axe_bearer_deaths"]
        observed_bar = source[
            "attacker_main_line_front_survivor_hp_percent_left_to_right"
        ][3]
        rows.append({
            "round":rnd,
            "before_axe_units":previous_n,
            "previous_living_slot_wounds":previous_w,
            "full_gun_hits_UNVERIFIED":effective_center_gun_hits,
            "gun_damage_per_hit_F5":gun_damage,
            "gun_damage_sum":gun_incoming,
            "gun_pool_before_killing":pool,
            "gun_kills_floor_HP":gun_kills,
            "gun_pool_residual_after_kills":excess_after_gun,
            "alive_after_guns_before_wall":after_gun,
            "independent_direct_wall_kills_ASSUMED":wall_direct_kills_per_round,
            "old_wounds_removed_with_wall_victim":removed_old_wounds,
            "end_living_slot_wounds":w,
            "modeled_end_axe_units":n,
            "modeled_end_bar_floor_pct":bar,
            "source_casualties":observed_kills,
            "source_end_units":observed_n,
            "source_bar_percent":observed_bar,
            "matches_source":(
                observed_kills == gun_kills + wall_direct_kills_per_round
                and observed_n == n and observed_bar == bar
            ),
        })
    return {
        "kind":"RESEARCH_ONLY_INTEGER_SLOT_POOL_EXISTENCE_WITNESS",
        "owner_confirmed_player_forge_level":forge_level,
        "axe_hp":hp,
        "effective_gun_damage_to_axe":gun_damage,
        "baseline_project_AM_center_addresses":baseline[4],
        "baseline_AM_all_physical":list(baseline.values()),
        "candidate_center_full_effective_hits":effective_center_gun_hits,
        "seven_gun_hits_are_redirected_or_otherwise_reduced_UNVERIFIED":True,
        "wall_source_targeting_and_last_phase_UNVERIFIED":True,
        "source_end_R83_units":21,
        "source_R83_bar_percent":start[
            "attacker_main_line_front_survivor_hp_percent_left_to_right"
        ][3],
        "candidate_R83_living_slot_wounds":first_round_end_wounds,
        "candidate_R83_bar_percent":displayed_83,
        "one_integer_rule_used_for_all_rounds":True,
        "game_implementation_verified":False,
        "rounds":rows,
        "reproduces_R84_R87_count_and_HP":(
            displayed_83 == 99 and all(row["matches_source"] for row in rows)
        ),
        "interpretation_limits":[
            "The actual source AM allocates FOURTEEN ADDRESSES to central Axe at all seven slots occupied",
            "Half-source-group rerouting is a separate unproven hypothesis; 7 effective full gun hits NOT established",
            "Floor(mean living HP) screenshot semantics and near-equal integer slot-level wound redistribution UNVERIFIED",
            "Wall attacks after gun pool and one effective direct wall kill assigned to center UNVERIFIED",
            "Residual gun overkill/damage when no Axes survive may be lost or redirected; source leftmost +7 still unexplained",
            "The R83 assumed wound parameter is a mathematical witness, not recovered per-individual history",
            "A mode change at center slot <25 from 29 before R83 to 21 before R84 is only a candidate threshold; no selector established",
        ],
    }


def sensitivity_report() -> dict:
    """Exhaustively scan EVERY integer R83 wound compatible with 21 Axe/99%."""
    profile = weapon_profiles(attacker_forge=5)
    hp = profile["barbarian_targets"]["barbarian_axe_swinger"]["target_hp"]
    matching = []
    valid_prior = []
    for wounds in range(0, 21*hp+1):
        if 100 * (21*hp - wounds) // (21*hp) != 99:
            continue
        valid_prior.append(wounds)
        scenario = compute_candidate(first_round_end_wounds=wounds)
        if scenario["reproduces_R84_R87_count_and_HP"]:
            matching.append(wounds)
    return {
        "source_R83_21_axes_99pct_wound_candidates":len(valid_prior),
        "survivor_wounds_compatible_with_R83_99pct": [
            min(valid_prior), max(valid_prior),
        ],
        "witness_wounds_matching_ALL_R84_R87":matching,
        "witness_interval_if_contiguous":[min(matching),max(matching)],
        "example":compute_candidate(),
        "warning":"Matching many starting integer states supports numerical feasibility only. Different wall chronology, RR/IR, shot effectiveness or AM routing can break this witness.",
    }


if __name__=="__main__":
    print(json.dumps(sensitivity_report(),ensure_ascii=False,indent=2))
