"""Read-only empirical naval Ram-vs-Deckwrecker analysis on controlled inputs.

WARNING: These small pure-Ram model runs are *not* identical to a historical
battle unless every missing wave, reinforcement and other formation is verified.
Do not calibrate combat rules from their difference alone.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ikariam_battle import simulate

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / "tests/fixtures/reverse_engineering/naval_ram_deckwrecker_20261013.json"


def net_damage_math(armor_upgrade: int) -> dict:
    """Current public profile arithmetic; not a claim about actual target selection."""
    hp = 3080
    barbarian_hit = 1500 - (180 + 10 * armor_upgrade + 20)
    player_hit = int((1500 + 20 * 10) * 115 / 100) - 240
    return {
        "player_armor_upgrade": armor_upgrade,
        "player_hp": hp,
        "barbarian_net_hit": barbarian_hit,
        "hits_to_kill_player": (hp + barbarian_hit - 1) // barbarian_hit,
        "player_hp_pct_after_one_independent_hit": 100 * (hp - barbarian_hit) / hp,
        "player_net_hit_attack_20": player_hit,
        "barbarian_hp_pct_if_three_die_and_all_six_hits_conserved": (
            100 * (3 * hp - (6 * player_hit - 3 * hp)) / (3 * hp)
        ),
    }


def model_one_controlled_round(armor_upgrade: int, attack_upgrade: int = 20) -> dict:
    """Barbarian attacker vs player defender, six 6-ship Flank slots each."""
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
            if s.get("unit_id") == unit and s.get("line") == "flank"
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
        "attacker_barbarian_deaths": round1["casualties"]["attacker"].get(
            "barbarian_deckwrecker", 0
        ),
        "defender_player_deaths": round1["casualties"]["defender"].get("ram_ship", 0),
        "round1_flank_slots": slots,
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
        print(
            f"DEF {level}: observed player deaths={observed}, "
            f"controlled model player deaths={model.get('defender_player_deaths')}, "
            f"barbarian deaths={model.get('attacker_barbarian_deaths')}, "
            f"hit={math['barbarian_net_hit']}, "
            f"single-hit remaining%={math['player_hp_pct_after_one_independent_hit']:.3f}, "
            f"model status={model['status']}"
        )
        for side, sl in model.get("round1_flank_slots", {}).items():
            print(f"  {side} physical-slot casualties/remaining damage: " + str([
                (x["physical_position"], x["casualties"], x["units"], x["damage"])
                for x in sl
            ]))
    print(f"JSON probe: {args.output}")


if __name__ == "__main__":
    main()
