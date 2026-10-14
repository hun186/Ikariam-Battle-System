"""First-round FULL-Axe source from SAME battle as R80-R89: D vs pooled controls.

No source attribution is recovered. Conditional assumption of ONE wall 1-kill
per physical target slot and 84 full Forge5 gun attacks; screenshot also has
artillery and other side sources not covered by these controls.
No actual combat engine changes permitted.
"""
from __future__ import annotations

import json
from pathlib import Path

from tools.research.land_round80_89_am_focus_probe import (
    model_am_addressed_shots_by_physical_slot,
)
from tools.research.land_round80_89_two_class_am_probe import weapon_profiles


FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "tests/fixtures/reverse_engineering/land_barbarian_round1_full_axes_20261014.json"
)


def report() -> dict:
    f=json.loads(FIXTURE.read_text(encoding="utf-8"))
    picture=f["transcribed_screenshot"]
    assert f["owner_confirmed"]["player_forge_level"] == 5
    assert f["owner_confirmed"]["musketeer_attack_workshop_level"] == 11
    guns=weapon_profiles(attacker_forge=5)
    axe=guns["barbarian_targets"]["barbarian_axe_swinger"]
    hp,damage=axe["target_hp"],axe["shot_damage"]
    assert (hp,damage)==(1120,710)
    shots=model_am_addressed_shots_by_physical_slot(list(range(1,8)),[12]*7)
    assert list(shots.values())==[7,14,14,14,14,14,7]
    rows=[]
    for index,am_count in shots.items():
        original=picture["axe_front_before"][index-1]
        killed=picture["axe_deaths_this_round"][index-1]
        live=picture["axe_front_end"][index-1]
        displayed=f["owner_confirmed"]["displayed_axe_front_survivor_HP_percent_physical_left_to_right"][index-1]
        assert original-killed==live
        # D control uses two GUN hits per fresh Axe; one effective wall hit
        # kills one more, with an unpaired gun shot wounding a survivor.
        direct_gun_kills=am_count // axe["shots_to_kill_full"]
        direct_wounds=(am_count%axe["shots_to_kill_full"])*damage
        direct_total_kills=direct_gun_kills+1
        direct_live=original-direct_total_kills
        direct_bar=100*(direct_live*hp-direct_wounds)//(direct_live*hp)
        # Conserved gun-damage slot pool: floor(total gun damage/full HP)
        # kills; keep remainder and wall 1-kills a least-wounded victim
        # after near-equal integer wounds were redistributed.
        pool_gun_kills=am_count*damage//hp
        pool_residual=am_count*damage%hp
        pool_aftergun=original-pool_gun_kills
        wall_old_wounds=pool_residual//pool_aftergun
        pool_live=pool_aftergun-1
        pool_residual_after_wall=pool_residual-wall_old_wounds
        pool_bar=100*(pool_live*hp-pool_residual_after_wall)//(pool_live*hp)
        rows.append({
            "physical_slot":index,
            "observed_deaths":killed,"observed_end_units":live,
            "observed_display_HP_pct":displayed,
            "CURRENT_ENGINE_AM_model_address_count":am_count,
            "wall_one_direct_kill_per_slot_UNVERIFIED":True,
            "D_pairwise_gun_deaths":direct_gun_kills,
            "D_with_one_wall_deaths":direct_total_kills,
            "D_deaths_shortfall_against_source":killed-direct_total_kills,
            "D_with_one_wall_end_HP_pct_IF_floormean":direct_bar,
            "pool_gun_deaths":pool_gun_kills,
            "pool_with_one_wall_deaths":pool_gun_kills+1,
            "pool_deaths_shortfall_against_source":killed-(pool_gun_kills+1),
            "pool_with_one_wall_end_HP_pct_IF_floormean":pool_bar,
            "pool_end_wounds_after_wall":pool_residual_after_wall,
            "pool_matches_both_count_and_HP":(
                killed==pool_gun_kills+1 and displayed==pool_bar
            ),
            "D_matches_both_count_and_HP":(
                killed==direct_total_kills and displayed==direct_bar
            ),
        })
    return {
        "kind":"SAME_BATTLE_ROUND1_SOURCE_VS_TWO_RESTRICTED_CONTROLS",
        "battle_identity":f["battle_identity"],
        "fixture":f["case_id"],
        "chronology":"R1 and R80-R89 are SAME battle, R2-R79 not supplied",
        "owner_confirmed_forge":5,
        "damage_into_axe_in_current_profile":damage,
        "axe_full_hp_in_current_profile":hp,
        "AM_addresses_left_to_right":list(shots.values()),
        "observed_deaths":picture["axe_deaths_this_round"],
        "observed_end_HP_percent":f["owner_confirmed"]["displayed_axe_front_survivor_HP_percent_physical_left_to_right"],
        "observed_total_Axe_deaths":sum(picture["axe_deaths_this_round"]),
        "conditional_wall_deaths_if_one_per_occupied_slot":7,
        "unmodeled_artillery_and_side_sources_in_screenshot":True,
        "rows":rows,
        "total_gap_vs_pairwise_D_plus_seven_walls":sum(x["D_deaths_shortfall_against_source"] for x in rows),
        "total_gap_vs_conserved_pool_plus_seven_walls":sum(x["pool_deaths_shortfall_against_source"] for x in rows),
        "specific_insight":"seven-address rightmost pool + one wall matches five deaths and 99pct; leftmost + all five central slots exceed one-wall + unmodified-gun controls",
        "hypotheses_to_test_not_conclusions":[
            "Even 14 gun addresses permit pairwise direct fire (2 hits/Axe) with no survivor wounds but only 7 gun deaths, not observed 12 center gun deaths per slot",
            "Seven gun addresses are indivisible by fresh hits-to-kill 2, hence extra wounded survivor or alternative pooled/IR/P behavior plausible irrespective of target slot population",
            "First round starts all Axe slots with 50, so edge HP<100 does NOT require a below-half-slot threshold",
            "Other displayed source classes, overkill redistribution, wall multi-hit targets, actual damage profile and Gameforge AM may differ",
            "The community PDF Section 5.1 explicitly contrasts D-kill for 14 shooters with I-kill for seven under DIFFERENT old numerical divisibility; don't import that I-kill rule as proven for 710/1120",
        ],
    }


if __name__=="__main__":
    print(json.dumps(report(),ensure_ascii=False,indent=2))
