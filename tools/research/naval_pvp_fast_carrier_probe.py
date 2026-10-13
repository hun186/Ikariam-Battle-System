"""Player-versus-player fast boat versus carrier held-out battle controls.

All empirical counts are sourced from user chat. The full battle contains
invented first-line fillers solely to allow a one-round engine control.
Nothing in this file implements or changes official Accuracy mechanics.
"""
from __future__ import annotations

import argparse
import json
from math import ceil
from pathlib import Path

from ikariam_battle import simulate
from ikariam_battle.engine import _shot_rows
from tools.research.naval_ram_empirical_probe import _damage_trace

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/reverse_engineering/naval_pvp_fast_boat_carrier_20261013.json"


def control_case(case: dict, *, attacker_forge: int, defender_forge: int) -> dict:
    attacker, defender, damage = _damage_trace(
        case["attacker_unit_id"], case["defender_unit_id"],
        attack_upgrade=case["attacker_attack_upgrade"],
        armor_upgrade=case["defender_armor_upgrade"],
        attacker_forge=attacker_forge,
        target_forge=defender_forge,
    )
    hp = defender.hit_points
    assert hp is not None
    source_count = case["attacker_count"]
    source_per_slot = source_count // 2
    rows = _shot_rows([source_per_slot, source_per_slot])
    hit_counts = [sum((row - 1) % 2 == i for row in rows) for i in range(2)]
    assert hit_counts == [16, 14]
    scenario = {
        "policy": "experimental",
        "battlefield": "naval-max",
        "max_rounds": 1,
        "attacker": {
            "army_kind": "player",
            "forge_level": attacker_forge,
            "units": [
                {"unit_id": "steam_ram", "quantity": 35},
                {"unit_id": attacker.id, "quantity": source_count,
                 "attack_upgrade": case["attacker_attack_upgrade"]},
            ],
        },
        "defender": {
            "army_kind": "player",
            "forge_level": defender_forge,
            "units": [
                {"unit_id": "steam_ram", "quantity": 35},
                {"unit_id": defender.id, "quantity": case["defender_count"],
                 "armor_upgrade": case["defender_armor_upgrade"]},
            ],
        },
    }
    result = simulate(scenario)
    rounds = result.get("rounds") or []
    round1 = rounds[1] if len(rounds) > 1 else None
    slots = [
        {k: s.get(k) for k in ("unit_id", "line", "physical_position", "damage_position", "units", "casualties", "damage")}
        for s in ((round1 or {}).get("defender", {}).get("slots") or [])
        if s.get("unit_id") == defender.id
    ]
    matrix_events = [
        e for e in result.get("events", [])
        if e.get("round") == 1
        and e.get("type") == "attacking_matrix"
        and e.get("side") == "attacker"
        and (e.get("details") or {}).get("unit_id") == attacker.id
    ]
    target_damage_events = [
        e for e in result.get("events", [])
        if e.get("round") == 1
        and e.get("type") == "damage"
        and (e.get("details") or {}).get("source_unit_id") == attacker.id
        and (e.get("details") or {}).get("target_unit_id") == defender.id
    ]
    if "attacker_forge_level" in case and "defender_forge_level" in case:
        is_observed_forge_scope = (
            attacker_forge == case["attacker_forge_level"]
            and defender_forge == case["defender_forge_level"]
        )
    else:
        raise ValueError("PvP observed case must record both user-confirmed Forge levels")
    return {
        "case": case["case"],
        "evidence_class": "CONTROLLED_SYNTHETIC_CURRENT_ENGINE_NOT_HISTORICAL",
        "forge_scope_evidence_class": (
            "USER_CONFIRMED_GAME_FORGE_SCOPE_WITH_SYNTHETIC_ENGINE"
            if is_observed_forge_scope else
            "COUNTERFACTUAL_FORGE_SENSITIVITY_NOT_USER_OBSERVED"
        ),
        "matches_user_confirmed_forge_scope": is_observed_forge_scope,
        "original_observation": case,
        "forge_config": {"attacker": attacker_forge, "defender": defender_forge},
        "damage_trace_from_production": damage.as_dict(),
        "net_hit": damage.final_damage,
        "accuracy": attacker.primary_weapon.accuracy,
        "target_ship_hp": hp,
        "minimum_hits_to_kill_fresh_ship": ceil(hp / damage.final_damage),
        "model_am_hit_slots": hit_counts,
        "gross_damage_per_slot": [n*damage.final_damage for n in hit_counts],
        "reported_total_deaths": case["reported_carrier_total_deaths"],
        "model_rounds_completed": result.get("rounds_completed"),
        "model_total_carrier_deaths": (
            round1["casualties"]["defender"].get(defender.id, 0)
            if round1 else None
        ),
        "model_carrier_slots": slots,
        "model_am_events": matrix_events,
        "model_source_damage_events": target_damage_events,
        "model_applied_assumptions": result.get("assumptions", []),
        "synthetic_frontline_warning": "Invented 35 player Steam Rams per side, not evidence of real historical fleet",
        "round_warning": "Comparison uses first round as a model control; user has not yet confirmed source records refer to end of first round",
        "forge_scope_warning": "Both player sides Forge5 is user-confirmed; attacker-only variant is explicitly counterfactual",
    }


def report() -> dict:
    source = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return {
        "case_id": source["case_id"],
        "evidence_class": source["evidence_class"],
        "raw_observations": source["observed"],
        "model_controls": source["model_controls"],
        "comparisons": [
            control_case(c, attacker_forge=forge["attacker_forge"],
                         defender_forge=forge["defender_forge"])
            for c in source["observed"]
            for forge in source["model_controls"]["conditional_forge_configs"]
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for x in output["comparisons"]:
        print(f"{x['case']}: forge={x['forge_config']}, damage={x['net_hit']}, "
              f"hit_to_kill={x['minimum_hits_to_kill_fresh_ship']}, "
              f"observed={x['reported_total_deaths']}, model={x['model_total_carrier_deaths']}, "
              f"model_per_slot={[s['casualties'] for s in x['model_carrier_slots']]}, "
              f"AM_hits={x['model_am_hit_slots']}, round={x['model_rounds_completed']}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
