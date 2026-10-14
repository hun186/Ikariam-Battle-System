"""Owner's TWO INDEPENDENT LAND HYPOTHESES: AM rerouting and gun kill mode.

Research-only alternative model. Stage A: for central Axe slot occupancy
BELOW an illustrative 25 of 50, move one 7-shot source AM row from
physical4 Axe to physical1 Knifeman. Stage B: decide damage accounting
by the POST-ROUTE group size / fresh-target hits-to-kill divisibility,
NOT directly by central population. E.g. 14 attacks / 2 => individually
paired D-kill seven fresh Axe; 7 attacks / 2 has a remainder =>
hypothetical pooled-with-remainder HP accounting. Stage A trigger,
Stage B rule, ammo, wall hit locations/order and bar rounding UNVERIFIED.

R81-R83 death vectors fit conditional 14-gun-paired plus wall; preexisting
Axe wounds and 99% bars in those rounds are NOT reconstructed by that
casualty-only fit. R84-R87 uses previously tested integer Slot wound pool
witness W83=25, a math example not verified battle injuries. First-round
all-Axe side 7-versus-center14 contrast motivates Stage B independently
of occupancy falling below 25.
"""
from __future__ import annotations

import json

from tools.research.land_round80_89_am_focus_probe import (
    FIXTURE, model_am_addressed_shots_by_physical_slot,
)
from tools.research.land_round80_89_two_class_am_probe import weapon_profiles
from tools.research.land_round84_87_integer_slot_pool_probe import compute_candidate


def two_stage_report(*, illustrative_reroute_threshold: int = 25) -> dict:
    """Return conditioned predictions and per-stage uncertainty explicitly."""
    source=json.loads(FIXTURE.read_text(encoding="utf-8"))
    axe=weapon_profiles(attacker_forge=source["player_forge"]["level"])[
        "barbarian_targets"
    ]["barbarian_axe_swinger"]
    knife=weapon_profiles(attacker_forge=source["player_forge"]["level"])[
        "barbarian_targets"
    ]["barbarian_knifeman"]
    assert source["player_forge"]["level"]==5
    assert (axe["target_hp"],axe["shot_damage"])==(1120,710)
    assert knife["shot_damage"]>=knife["target_hp"]
    if not 1<=illustrative_reroute_threshold<=50:
        raise ValueError("candidate threshold must be a positive slot occupancy within50")
    games={item["round"]:item for item in source["observations"]}
    default_am=model_am_addressed_shots_by_physical_slot(
        list(range(1,8)),[12]*7,
    )
    if [default_am[i] for i in range(1,8)] !=[7,14,14,14,14,14,7]:
        raise ValueError("new project AM differs, review model")
    pooled={r["round"]:r for r in compute_candidate()["rounds"]}
    rows=[]
    for rnd in range(81,88):
        previous=games[rnd-1]
        current=games[rnd]
        central_before=previous["central_position_4_axe_bearer_remaining_units"]
        stage_a_reroute=central_before<illustrative_reroute_threshold
        gun=dict(default_am)
        if stage_a_reroute:
            gun[4]-=7
            gun[1]+=7
        central_shots=gun[4]
        axe_two_shot=axe["shots_to_kill_full"]==2
        stage_b_group_divisible=(central_shots % axe["shots_to_kill_full"]==0)
        if stage_b_group_divisible:
            assert axe_two_shot and central_shots==14
            axe_gun_kills=central_shots//2
            axe_gun_model="CONDITIONAL_PAIRWISE_D_KILL"
            modeled_remaining_axe_wounds=None
            modeled_center_hp_bar=None
        else:
            assert axe_two_shot and central_shots==7
            if rnd not in pooled:
                raise ValueError("candidate rerouting implies out-of-scope pooled round")
            axle=pooled[rnd]
            axe_gun_kills=axle["gun_kills_floor_HP"]
            axe_gun_model="CONDITIONAL_INTEGER_SLOT_WOUND_POOL"
            modeled_remaining_axe_wounds=axle["end_living_slot_wounds"]
            modeled_center_hp_bar=axle["modeled_end_bar_floor_pct"]
        # Wall independently contributes one effective 1-kill to each Axe
        # or Knifeman facing slot, AFTER this gun phase, as owner hypothesizes.
        predicted=[
            (axe_gun_kills+1) if i==4 else gun[i]+1
            for i in range(1,8)
        ]
        observed=current["attacker_barbarian_main_line_deaths_left_to_right"]
        rows.append({
            "round":rnd,
            "starting_center_axes":central_before,
            "stage_A_reroute_if_center_below_illustrative_threshold":stage_a_reroute,
            "post_route_gun_AM_physical":[gun[i] for i in range(1,8)],
            "stage_B_central_gun_address_count":central_shots,
            "stage_B_shots_divisible_by_fresh_Axe_hits_to_kill":stage_b_group_divisible,
            "stage_B_central_gun_accounting_HYPOTHESIS":axe_gun_model,
            "modeled_center_gun_Axe_kills":axe_gun_kills,
            "modeled_center_one_wall_kill":1,
            "modeled_remaining_center_Axe_wounds":modeled_remaining_axe_wounds,
            "modeled_center_HP_bar_when_pooled":modeled_center_hp_bar,
            "predicted_all_frontline_casualties":predicted,
            "source_all_frontline_casualties":observed,
            "matches_all_frontline_casualties":predicted==observed,
            "source_center_HP_bar":current[
                "attacker_main_line_front_survivor_hp_percent_left_to_right"
            ][3],
            "HP_witness_matched_IF_rerouted_pooled":(
                modeled_center_hp_bar==current[
                    "attacker_main_line_front_survivor_hp_percent_left_to_right"
                ][3]
                if stage_a_reroute else None
            ),
        })
    return {
        "kind":"RESEARCH_ONLY_OWNER_TWO_STAGE_ADDRESS_AND_DAMAGE_HYPOTHESIS",
        "stage_A":"reroute seven attacks to physical1 ONLY IF central Axe slot start population < hypothetical threshold",
        "stage_A_illustrative_threshold":illustrative_reroute_threshold,
        "stage_A_threshold_experiment_not_established":True,
        "stage_B":"depending on post-route AM hit-count divisibility by fresh individual hits-to-kill, choose PAIRWISE D or retained slot-pool model",
        "stage_B_selector_is_unverified":True,
        "baseline_am_physical":[default_am[i] for i in range(1,8)],
        "post_route_shots_may_not_be_full_real_hits":True,
        "wall_phase_last_as_owner_stated":True,
        "r81_r83_hp_bar_not_reconstructed":True,
        "r84_r87_R83_old_wound_seed_is_conditional":25,
        "rounds":rows,
        "seven_round_deaths_all_match_under_both_stages":all(
            x["matches_all_frontline_casualties"] for x in rows
        ),
        "r84_r87_pooled_center_hp_all_match":all(
            x["HP_witness_matched_IF_rerouted_pooled"]
            for x in rows if x["round"]>=84
        ),
        "remaining_unknowns":[
            "No verified reroute transition: central 29 before R83 vs21 before R84 only bounds candidate threshold",
            "R1 with all Axe targets starting50 already demonstrates 7-shot edge behavior, even with no Stage A reroute",
            "Divisibility of delivered attack count by hits-to-kill may correlate with final loss and wound remainder without any explicit Kill Type dispatcher",
            "No full per-hit Gameforge logs, ammunition history or verified Accuracy selection",
            "The shots sent to physical1 Knifeman are a candidate AM transfer, not a demonstrated cross-slot surplus-damage spill",
            "Wall target slots, one effective hit per section and wall-phase injury removal remain unverified",
            "Floor-of-living-survivor-average UI bars and near-equal redistribution remain unverified",
            "R81-R83 central 99% HP bars may reflect preexisting injuries from earlier rounds not modeled here",
        ],
    }


if __name__=="__main__":
    print(json.dumps(two_stage_report(),ensure_ascii=False,indent=2))
