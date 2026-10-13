"""Read-only empirical naval Ram-vs-Deckwrecker analysis on controlled inputs.

WARNING: These small pure-Ram model runs are *not* identical to a historical
battle unless every missing wave, reinforcement and other formation is verified.
Do not calibrate combat rules from their difference alone.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from functools import lru_cache
from types import SimpleNamespace

from ikariam_battle import simulate
from ikariam_battle.damage import RoundingPolicy, calculate_damage
from ikariam_battle.profiles import ForgeProfile, WorkshopProfile
from ikariam_battle.units import UnitRegistry
from ikariam_battle.accuracy import select_accuracy_target
from ikariam_battle.engine import _apply_sequential_hit

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / "tests/fixtures/reverse_engineering/naval_ram_deckwrecker_20261013.json"


@lru_cache(maxsize=1)
def _profiles():
    """Load same packaged numeric unit/workshop/Forge data used by simulate."""
    return (
        UnitRegistry.load(include_barbarians=True),
        WorkshopProfile.load(),
        ForgeProfile.load(),
    )


def _damage_trace(
    attacker_unit_id: str,
    target_unit_id: str,
    *,
    attack_upgrade: int = 0,
    armor_upgrade: int = 0,
    attacker_forge: int = 0,
    target_forge: int = 0,
):
    registry, workshop, forge = _profiles()
    attacker, target = registry.get(attacker_unit_id), registry.get(target_unit_id)
    result = calculate_damage(
        attacker, target,
        attack_level=attack_upgrade,
        armor_level=armor_upgrade,
        attacker_forge=attacker_forge,
        defender_forge=target_forge,
        workshop=workshop,
        forge=forge,
        rounding=RoundingPolicy.FLOOR,
    )
    return attacker, target, result


def net_damage_math(armor_upgrade: int, attack_upgrade: int = 20) -> dict:
    """Conditional arithmetic derived from current packaged combat profiles."""
    enemy, player, incoming = _damage_trace(
        "barbarian_deckwrecker", "ram_ship",
        armor_upgrade=armor_upgrade, target_forge=5,
    )
    _, _, outgoing = _damage_trace(
        "ram_ship", "barbarian_deckwrecker",
        attack_upgrade=attack_upgrade, attacker_forge=5,
    )
    player_hp, enemy_hp = player.hit_points, enemy.hit_points
    assert player_hp is not None and enemy_hp is not None
    barbarian_hit, player_hit = incoming.final_damage, outgoing.final_damage
    if barbarian_hit <= 0:
        raise ValueError("Current profile has no penetrative Barbarian Ram damage")
    theoretical_remainder = 6 * player_hit - 3 * enemy_hp
    return {
        "player_armor_upgrade": armor_upgrade,
        "player_attack_upgrade": attack_upgrade,
        "player_hp": player_hp,
        "barbarian_hp": enemy_hp,
        "barbarian_accuracy": enemy.primary_weapon.accuracy,
        "player_accuracy": player.primary_weapon.accuracy,
        "barbarian_net_hit": barbarian_hit,
        "hits_to_kill_player": (player_hp + barbarian_hit - 1) // barbarian_hit,
        "player_hp_pct_after_one_independent_hit": (
            100 * (player_hp - barbarian_hit) / player_hp
        ),
        "player_net_hit_attack_20": player_hit,
        "barbarian_hp_pct_if_three_die_and_all_six_hits_conserved": (
            100 * (3 * enemy_hp - theoretical_remainder) / (3 * enemy_hp)
        ),
        "source_profile_incoming": incoming.as_dict(),
        "source_profile_outgoing": outgoing.as_dict(),
        "hypothesis_not_established": (
            "Six actual hits per slot and transfer of excess damage to survivors "
            "have not been verified in real-game telemetry"
        ),
    }


def microprobe_six_hits(
    attacker_unit_id: str,
    target_unit_id: str,
    *,
    attack_upgrade: int = 0,
    armor_upgrade: int = 0,
    attacker_forge: int = 0,
    target_forge: int = 0,
) -> dict:
    """Actual current experimental selector, six hits on a synthetic six-unit slot.

    HP, Accuracy and damage (including Forge/Workshop) come from production
    registries and calculate_damage. This is NOT a full battle/observed AM trace.
    """
    attacker, target, trace = _damage_trace(
        attacker_unit_id, target_unit_id,
        attack_upgrade=attack_upgrade,
        armor_upgrade=armor_upgrade,
        attacker_forge=attacker_forge,
        target_forge=target_forge,
    )
    hp, accuracy, net_damage = (
        target.hit_points,
        attacker.primary_weapon.accuracy,
        trace.final_damage,
    )
    if hp is None or accuracy is None:
        raise ValueError("Unit HP and weapon Accuracy must be verified")
    queue = [0] * 6
    slot = SimpleNamespace(units=6, damage=0)
    history = []
    deaths = 0
    overkill = 0
    for shot in range(1, 7):
        selected = select_accuracy_target(queue, hp, net_damage, accuracy)
        prior, killed, discarded = _apply_sequential_hit(
            slot, queue, hp, net_damage, selected.target_index
        )
        deaths += killed
        overkill += discarded
        history.append({
            "shot": shot,
            "target_index": selected.target_index,
            "mode": selected.mode,
            "prior_unit_damage": prior,
            "killed": killed,
            "overkill_discarded": discarded,
            "queue_remaining_damage": list(queue),
        })
    return {
        "evidence_class": "CONTROLLED_CURRENT_ENGINE_MICROPROBE",
        "attacker_unit_id": attacker.id,
        "target_unit_id": target.id,
        "damage_source": trace.as_dict(),
        "starting_units": 6,
        "hit_count": 6,
        "net_damage_per_hit": net_damage,
        "unit_hp": hp,
        "accuracy": accuracy,
        "deaths": deaths,
        "surviving_units": slot.units,
        "persistent_damage": slot.damage,
        "overkill_discarded": overkill,
        "survivor_average_hp_pct": (
            100 * (slot.units * hp - slot.damage) / (slot.units * hp)
            if slot.units else None
        ),
        "history": history,
    }


def model_one_controlled_round(armor_upgrade: int, attack_upgrade: int = 20) -> dict:
    """Controlled Ram-only battle, NOT six full user-observed Flank slots.

    Ram-only deployments can fill First by fallback, which is not equivalent
    to the user-reported real battle with six Flank slots.
    """
    scenario = {
        "policy": "experimental",
        "battlefield": "naval-max",
        "max_rounds": 1,
        "attacker": {
            "army_kind": "barbarian",
            "forge_level": 0,
            "units": [
                {"unit_id": "barbarian_deckwrecker", "quantity": 36,
                 "entry_batch_id": "barb-first", "wave_id": "barb-first::deckwrecker"}
            ],
        },
        "defender": {
            "army_kind": "player",
            "forge_level": 5,
            "units": [
                {"unit_id": "ram_ship", "quantity": 36,
                 "attack_upgrade": attack_upgrade,
                 "armor_upgrade": armor_upgrade,
                 "entry_batch_id": "player-first", "wave_id": "player-first::ram"}
            ],
        },
    }
    result = simulate(scenario)
    if not result.get("rounds") or len(result["rounds"]) < 2:
        return {
            "defense_upgrade": armor_upgrade,
            "attack_upgrade": attack_upgrade,
            "status": result.get("status"),
            "rounds_completed": result.get("rounds_completed"),
            "warning": "No Round-1 snapshot; cannot interpret casualties",
            "unsupported_events": [
                e for e in result.get("events", [])
                if e.get("type") == "unsupported_mechanic"
            ],
        }
    round1 = result["rounds"][1]
    slots = {}
    for side, unit in (("attacker", "barbarian_deckwrecker"), ("defender", "ram_ship")):
        slots[side] = [
            {k: s.get(k) for k in (
                "slot_id", "line", "unit_id", "physical_position", "damage_position",
                "units", "casualties", "damage",
            )}
            for s in round1[side]["slots"]
            if s.get("unit_id") == unit
        ]
    events = []
    for e in result.get("events", []):
        if e.get("round") == 1 and e.get("type") in (
            "damage", "damage_calculation", "attacking_matrix",
            "formation_fire_phase", "unsupported_mechanic",
        ):
            d = e.get("details") or {}
            if e.get("type") not in ("damage", "damage_calculation") or (
                d.get("source_unit_id") in ("ram_ship", "barbarian_deckwrecker")
            ):
                events.append({
                    "type": e["type"],
                    "side": e.get("side"),
                    "phase": e.get("phase"),
                    "details": d,
                })
    return {
        "defense_upgrade": armor_upgrade,
        "attack_upgrade": attack_upgrade,
        "status": result.get("status"),
        "rounds_completed": result.get("rounds_completed"),
        "initial_layout_by_side": {
            side: [
                {"line": slot.get("line"), "physical_position": slot.get("physical_position"),
                 "units": slot.get("units"), "unit_id": slot.get("unit_id")}
                for slot in result.get("initial_state", {}).get(side, {}).get("slots", [])
            ] for side in ("attacker", "defender")
        },
        "attacker_barbarian_deaths": round1["casualties"]["attacker"].get(
            "barbarian_deckwrecker", 0
        ),
        "defender_player_deaths": round1["casualties"]["defender"].get("ram_ship", 0),
        "round1_unit_slots_all_lines": slots,
        "unsupported_events": [
            e for e in result.get("events", [])
            if e.get("type") == "unsupported_mechanic"
        ],
        "round1_events": events,
    }


def build_report() -> dict:
    fixture = json.loads(CASE.read_text(encoding="utf-8"))
    variants = fixture["controlled_scenario_assumptions"][
        "player_armor_upgrade_variants"
    ]
    return {
        "schema_version": 1,
        "case_id": fixture["case_id"],
        "observed": fixture["observed"],
        "source": fixture["source"],
        "controlled_model_assumptions": fixture["controlled_scenario_assumptions"],
        "independent_arithmetic": [net_damage_math(level) for level in variants],
        "microprobe_current_accuracy_and_overkill": {
            "barbarian_to_player": [
                {"defense_upgrade": level,
                 **microprobe_six_hits("barbarian_deckwrecker", "ram_ship", armor_upgrade=level, target_forge=5)}
                for level in variants
            ],
            "player_attack20_to_barbarian": microprobe_six_hits("ram_ship", "barbarian_deckwrecker", attack_upgrade=20, attacker_forge=5),
        },
        "current_model": [
            model_one_controlled_round(level) for level in variants
        ],
        "research_warnings": [
            "Observed HP bars may represent something other than survivor-average remaining HP",
            "80 Accuracy does not imply 80% independent chance to hit; check the current EXP accuracy selector",
            "Current engine sequential hits discard overkill; test, do not assume, alternative damage redistribution",
            "Defense Lv14→15 keeps a 3-hit threshold despite observed kills falling from six to zero",
            "Controlled pure Ram matchup is not proven identical to historical complete fleet composition",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    for math, model in zip(report["independent_arithmetic"], report["current_model"]):
        level = math["player_armor_upgrade"]
        observed = report["observed"]["player_deaths_total_by_defense_upgrade"].get(str(level))
        if observed is None:
            observed = report["observed"]["direct_conversation_case"]["player_total_deaths"]
        print(
            f"DEF {level}: observed player deaths={observed}, "
            f"controlled model player deaths={model.get('defender_player_deaths')}, "
            f"barbarian deaths={model.get('attacker_barbarian_deaths')}, "
            f"hit={math['barbarian_net_hit']}, "
            f"single-hit remaining%={math['player_hp_pct_after_one_independent_hit']:.3f}, "
            f"model status={model['status']}"
        )
        for side, sl in model.get("round1_unit_slots_all_lines", {}).items():
            print(f"  {side} all-lines physical-slot casualties/remaining damage: " + str([
                (x["physical_position"], x["casualties"], x["units"], x["damage"])
                for x in sl
            ]))
    print("Exact current six-hit Accuracy/overkill microprobe:")
    for x in report["microprobe_current_accuracy_and_overkill"]["barbarian_to_player"]:
        print(f"  DEF{x['defense_upgrade']} barbarian→player: "
              f"deaths={x['deaths']}, survivorHP={x['survivor_average_hp_pct']:.3f}%, "
              f"overkill_lost={x['overkill_discarded']}")
    x = report["microprobe_current_accuracy_and_overkill"]["player_attack20_to_barbarian"]
    print(f"  player ATT20→barbarian: deaths={x['deaths']}, "
          f"survivorHP={x['survivor_average_hp_pct']:.3f}%, "
          f"overkill_lost={x['overkill_discarded']}")
    print(f"JSON probe: {args.output}")


if __name__ == "__main__":
    main()
