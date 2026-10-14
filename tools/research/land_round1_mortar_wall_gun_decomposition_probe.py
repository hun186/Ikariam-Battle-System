"""R1 Barbarian all-Axe battle: explicitly separate Mortar, Wall, and Gun casualties.

This is a reproducible ONE-ROUND conditional analytical fit, NOT a recovered
Gameforge attack-by-attack log, wall order or formal Kill-Type dispatcher.
The owner proposed 5 mortar groups of 6 shots, each one-shot-killing an Axe,
plus seven wall sections causing one direct casualty each; attacking-matrix
target priority distributes mortar shots across PHYSICAL slots 1..6.
Guns: 7-address edges use lossless pooled-damage model; 14-address inner
positions use pairwise two-gun-hit D-kill with discarded overkill. ALL
source full-success/kill-type/HP-bar rules remain unverified assumptions.
"""
from __future__ import annotations

import json
from pathlib import Path

from ikariam_battle.units import UnitRegistry
from tools.research.land_round80_89_am_focus_probe import (
    model_am_addressed_shots_by_physical_slot,
)
from tools.research.land_round80_89_two_class_am_probe import weapon_profiles


FIXTURE = Path(__file__).resolve().parents[2] / (
    "tests/fixtures/reverse_engineering/"
    "land_barbarian_round1_full_axes_20261014.json"
)


def report() -> dict:
    source = json.loads(FIXTURE.read_text(encoding="utf-8"))
    confirmed = source["owner_confirmed"]
    screen = source["transcribed_screenshot"]
    assert confirmed["player_forge_level"] == 5
    assert confirmed["musketeer_attack_workshop_level"] == 11
    assert screen["defender_player_visible_artillery_slots"] == [6]*5
    assert screen["defender_player_visible_musket_slots"] == [12]*7
    assert screen["defender_player_visible_wall_sections"] == [1]*7

    units = UnitRegistry.load(include_barbarians=True)
    mortar = units.get("mortar")
    gun_profile = weapon_profiles(attacker_forge=5)
    target = gun_profile["barbarian_targets"]["barbarian_axe_swinger"]
    axe_hp = target["target_hp"]
    gun_damage = target["shot_damage"]
    assert (axe_hp, gun_damage) == (1120, 710)
    # Ammo, target eligibility and effective Accuracy remain unobserved.
    # Paper/engine AM rows distribute 30 source mortar attacks across
    # first six damage-position targets, physically 1..6 in land-max.
    active_slots = list(range(1, 8))
    mortar_addresses = model_am_addressed_shots_by_physical_slot(
        active_slots, screen["defender_player_visible_artillery_slots"]
    )
    gun_addresses = model_am_addressed_shots_by_physical_slot(
        active_slots, screen["defender_player_visible_musket_slots"]
    )
    assert list(mortar_addresses.values()) == [5,5,5,5,5,5,0]
    assert list(gun_addresses.values()) == [7,14,14,14,14,14,7]
    assert mortar.primary_weapon.damage > axe_hp  # primary BASE damage
    rows=[]
    for physical in active_slots:
        idx=physical-1
        initial=screen["axe_front_before"][idx]
        dead=screen["axe_deaths_this_round"][idx]
        live=screen["axe_front_end"][idx]
        bar=confirmed["displayed_axe_front_survivor_HP_percent_physical_left_to_right"][idx]
        mortar_one_shot_kills=mortar_addresses[physical]
        wall_one_shot_kills=1
        shots=gun_addresses[physical]
        if shots==14:
            gun_kill_type="HYPOTHETICAL_PAIRWISE_D_KILL"
            gun_kills=shots//2
            surviving_wounds=0
            wasted_overkill=gun_kills*(2*gun_damage-axe_hp)
        elif shots==7:
            gun_kill_type="HYPOTHETICAL_AGGREGATE_DAMAGE_WITH_REMAINDER"
            full_gun_damage=shots*gun_damage
            gun_kills, surviving_wounds=divmod(full_gun_damage,axe_hp)
            wasted_overkill=0
        else:
            raise ValueError("Unexpected gun address count; re-evaluate")
        pred_deaths=mortar_one_shot_kills+wall_one_shot_kills+gun_kills
        pred_alive=initial-pred_deaths
        if pred_alive<=0:
            raise ValueError("No survivors: current HP bar hypothesis undefined")
        pred_bar=100*(pred_alive*axe_hp-surviving_wounds)//(pred_alive*axe_hp)
        rows.append({
            "physical_slot":physical,
            "mortar_AM_addresses_CONDITIONAL":mortar_addresses[physical],
            "wall_1kill_per_slot_CONDITIONAL":wall_one_shot_kills,
            "gun_AM_addresses_CONDITIONAL":shots,
            "gun_kill_type_HYPOTHESIS":gun_kill_type,
            "gun_kills_if_every_address_fires_full":gun_kills,
            "gun_overkill_discarded_in_D_control":wasted_overkill,
            "gun_surviving_slot_wounds":surviving_wounds,
            "predicted_deaths":pred_deaths,
            "observed_deaths":dead,
            "predicted_survivors":pred_alive,
            "observed_survivors":live,
            "predicted_HP_pct_IF_floor_survivor_mean":pred_bar,
            "observed_HP_pct":bar,
            "matches_all_source_dimensions":(
                pred_deaths==dead and pred_alive==live and pred_bar==bar
            ),
        })
    return {
        "schema_version":1,
        "scope":"Independent new first-round all-Axe battle; not prior R80-R89",
        "evidence_class":"CONDITIONAL_MORTAR_ONE_SHOT_WALL_ONE_SHOT_GUN_MIXED_KILL_TYPE_FIT",
        "owner_confirmed_forge":5,
        "source_artillery_screenshot_counts":screen["defender_player_visible_artillery_slots"],
        "mortar_registry_primary_base_damage":mortar.primary_weapon.damage,
        "mortar_primary_accuracy":mortar.primary_weapon.accuracy,
        "mortar_source_ammo_pool_per_unit":mortar.primary_weapon.ammunition,
        "source_gun_damage_to_axe_F5":gun_damage,
        "source_axe_hp":axe_hp,
        "source_AM_address_counts_by_physical":{
            "mortar":[mortar_addresses[i] for i in active_slots],
            "gun":[gun_addresses[i] for i in active_slots],
        },
        "assumptions_NOT_OBSERVED":{
            "every_mortar_source_attack_is_effective_and_kills_one_Axe":True,
            "all_mortar_attacks_target_first_Axe_line_using_the_current_AM":True,
            "wall_each_active_physical_slot_exactly_one_lethal_hit":True,
            "gun_primary_hits_all_land_with_full_calculated_damage":True,
            "fourteen_gun_addresses_use_pairwise_D_Kill_and_waste_overkill":True,
            "seven_gun_addresses_use_pooled_damage_and_retain_mod_HP":True,
            "pooled_490_wounds_remain_on_survivors_not_spent_by_mortar_wall":True,
            "floor_of_total_surviving_HP_bar_semantics":True,
            "other_visible_battle_units_add_no_deaths_to_this_Axe_front_in_round1":True,
        },
        "rows":rows,
        "all_seven_slots_match":all(x["matches_all_source_dimensions"] for x in rows),
        "source_total_axe_deaths":sum(screen["axe_deaths_this_round"]),
        "predicted_total_axe_deaths":sum(x["predicted_deaths"] for x in rows),
        "key_numerical_observation":"same 490 wounds in both edge slots: /40 surviving Axe =98 percent while /45 =99 percent under floor UI; mortar kills five additional on left",
        "limitations":[
            "Shot rows/address counts are known from current simulator model, not observed real game logs",
            "Wall source attack count and physical-facing targeting, source ordering, and mortar Accuracy uncertain",
            "Middle clean 100 percent bars and 13 deaths are compatible with two-hit paired focus after mortar/wall losses, not proof of specific Gameforge Kill Type",
            "Seven-shot edge can mathematically kill four by pooled overkill with 490 remainder, but direct sequential two-hit-only gun fire would kill only three and leave one wounded",
            "The current ammunition/secondary weapon/source sequence and other units remain unaudited",
            "Display floor semantics and persistence of the two 490 wound pools remain unverified",
        ],
    }


if __name__=="__main__":
    print(json.dumps(report(),ensure_ascii=False,indent=2))
