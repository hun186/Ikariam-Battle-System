"""Independent observable-outcome inversion for fast boats vs carriers.

Read-only research. Does not guess inaccessible per-ship game hit logs or
change any runtime rules. All computations use current packaged stats.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ikariam_battle import simulate
from ikariam_battle.engine import _shot_rows
from tools.research.naval_ram_empirical_probe import _damage_trace

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/reverse_engineering/naval_air_counterparts_20261013.json"


def damage_and_round_observables(case: dict) -> dict:
    is_barbarian_attacker = case["attacker"].startswith("barbarian_")
    player_defense = case["player_defense_upgrade"] if is_barbarian_attacker else 0
    player_attack = case["player_attack_upgrade"] if not is_barbarian_attacker else 0
    attacker, target, trace = _damage_trace(
        case["attacker"], case["target"],
        attack_upgrade=player_attack,
        armor_upgrade=player_defense,
        attacker_forge=(0 if is_barbarian_attacker else case["player_forge_level"]),
        target_forge=(case["player_forge_level"] if is_barbarian_attacker else 0),
    )
    hp = target.hit_points
    assert hp is not None
    # This AM calculation follows the actual production row-number addressing:
    # each of the two source columns has 15 units; each row has two shots,
    # both addressed to the same of two target damage-position columns.
    firing_counts = [case["attacker_units_per_position"]] * case["attacker_positions"]
    row_numbers = _shot_rows(firing_counts)
    addressed_counts = [sum((row - 1) % case["target_positions"] == idx for row in row_numbers)
                        for idx in range(case["target_positions"])]
    assert sum(addressed_counts) == case["attacker_count"]
    no_deaths = [100 * (case["target_units_per_position"] * hp - count * trace.final_damage)
                 / (case["target_units_per_position"] * hp) for count in addressed_counts]
    sunk_per_slot = case.get("reported_barbarian_deaths_per_position", 0)
    remaining_per_slot = case["target_units_per_position"] - sunk_per_slot
    retained_after_deaths = [
        100 * (remaining_per_slot * hp - (count * trace.final_damage - sunk_per_slot * hp))
        / (remaining_per_slot * hp)
        for count in addressed_counts
    ] if remaining_per_slot > 0 else []
    return {
        "case_id": case["case"],
        "evidence_class": "MODEL_CONDITIONAL_NOT_REAL_SHOT_TELEMETRY",
        "target_unit_hp": hp,
        "attacker_accuracy": attacker.primary_weapon.accuracy,
        "net_damage": trace.final_damage,
        "damage_source": trace.as_dict(),
        "model_two_source_columns": firing_counts,
        "model_target_am_hit_counts": addressed_counts,
        "hypothetical_no_loss_survivor_bars": no_deaths,
        "hypothetical_no_loss_bars_truncated": [int(v) for v in no_deaths],
        "hypothetical_all_damage_retained_survivor_bars": retained_after_deaths,
        "hypothetical_all_damage_retained_bars_truncated": [int(v) for v in retained_after_deaths],
        "observed": {
            k: case[k] for k in (
                "reported_player_total_deaths", "reported_occupied_slot_bars_percent",
                "reported_barbarian_deaths_per_position", "reported_survivor_slot_bars_percent",
            ) if k in case
        },
    }


def run_current_full_engine_control(case: dict) -> dict:
    """Exactly two unit types; NOT a reconstruction of unreported First lines."""
    is_barbarian_attacker = case["attacker"].startswith("barbarian_")
    sides = {
        "attacker": {
            "army_kind": "barbarian" if is_barbarian_attacker else "player",
            "forge_level": 0 if is_barbarian_attacker else case["player_forge_level"],
            "units": [{
                "unit_id": case["attacker"], "quantity": case["attacker_count"],
                "attack_upgrade": 0 if is_barbarian_attacker else case["player_attack_upgrade"],
            }],
        },
        "defender": {
            "army_kind": "player" if is_barbarian_attacker else "barbarian",
            "forge_level": case["player_forge_level"] if is_barbarian_attacker else 0,
            "units": [{
                "unit_id": case["target"], "quantity": case["target_count"],
                "armor_upgrade": case["player_defense_upgrade"] if is_barbarian_attacker else 0,
            }],
        },
    }
    # Synthetic First-line fillers make the real one-round engine execute
    # anti-balloon->balloon fire phases. They were NOT observed in these battles.
    sides["attacker"]["units"].insert(0, {
        "unit_id": "barbarian_wedge_paddler" if is_barbarian_attacker else "steam_ram",
        "quantity": 42 if is_barbarian_attacker else 35,
        "attack_upgrade": 0,
        "armor_upgrade": 0,
    })
    sides["defender"]["units"].insert(0, {
        "unit_id": "steam_ram" if is_barbarian_attacker else "barbarian_wedge_paddler",
        "quantity": 35 if is_barbarian_attacker else 42,
        "attack_upgrade": 0,
        "armor_upgrade": 0,
    })
    result = simulate({
        "policy": "experimental", "battlefield": "naval-max", "max_rounds": 1,
        **sides,
    })
    round1 = (result.get("rounds") or [None, None])[1] if len(result.get("rounds") or []) >= 2 else None
    matrix = [
        {"side": e.get("side"), "phase": e.get("phase"), "details": e.get("details")}
        for e in result.get("events", [])
        if e.get("type") == "attacking_matrix" and e.get("round") == 1
    ]
    return {
        "evidence_class": "CONTROLLED_SYNTHETIC_CURRENT_ENGINE_NOT_HISTORICAL",
        "status": result.get("status"),
        "rounds_completed": result.get("rounds_completed"),
        "invented_first_line_filler_not_observed": True,
        "source_count": case["attacker_count"],
        "target_count": case["target_count"],
        "attacker_unit": case["attacker"],
        "target_unit": case["target"],
        "model_attacker_units_lost": round1["casualties"]["attacker"].get(case["attacker"], 0)
            if round1 is not None else None,
        "model_target_units_lost": round1["casualties"]["defender"].get(case["target"], 0)
            if round1 is not None else None,
        "target_slots": [
            {key: slot.get(key) for key in (
                "unit_id", "line", "physical_position", "damage_position", "units",
                "casualties", "damage",
            )}
            for slot in (round1["defender"]["slots"] if round1 is not None else [])
            if slot.get("unit_id") == case["target"]
        ],
        "attacking_matrix_events": matrix,
        # Preserve the COMPLETE model round-1 event trace, rather than only
        # AM summaries. Damage, Accuracy decisions, overkill and assumptions
        # are needed to audit why current MODEL HP differs from real-game bars.
        # These are SYNTHETIC simulator events, never real per-ship hit logs.
        "synthetic_round1_model_events": [
            event for event in result.get("events", [])
            if event.get("round") == 1
        ],
        "model_applied_assumptions": result.get("assumptions", []),
        "unsupported_events": [
            x for x in result.get("events", [])
            if x.get("type") == "unsupported_mechanic"
        ],
    }


def report() -> dict:
    evidence = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return {
        "schema_version": 1,
        "case_id": evidence["case_id"],
        "source": evidence["source"],
        "candidate_unit_mapping": evidence["candidate_unit_mapping"],
        "conditions": evidence["model_assumptions"],
        "cases": [
            {
                "case": original,
                "conditional_arithmetic": damage_and_round_observables(original),
                "current_engine_control": run_current_full_engine_control(original),
            }
            for original in evidence["observed"]
        ],
        "warnings": [
            "Game battle report hides individual ship target-hit sequence; engine logs are synthetic model logs only.",
            "16/14 AM split assumes both 15-ship speedboat slots each fire once at two valid carrier target slots.",
            "Percent matches presuppose floor rounding, a survivor-only bar denominator, and all successful hit damage retained in the selected slot.",
            "Real battle may include other formations and earlier/later phases, so results are feasibility evidence not mechanistic identification.",
            "A fixed target-selection rule needs to explain grade7 -> grade8 casualty threshold without hardcoded casualty lookups.",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    outcome = report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(outcome, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for r in outcome["cases"]:
        x, y = r["conditional_arithmetic"], r["current_engine_control"]
        print(f"{x['case_id']}: net={x['net_damage']}, hit_split={x['model_target_am_hit_counts']}, "
              f"no_loss_bars={x['hypothetical_no_loss_bars_truncated']}, "
              f"retain_loss_bars={x['hypothetical_all_damage_retained_bars_truncated']}, "
              f"engine_target_loss={y['model_target_units_lost']}, "
              f"engine_status={y['status']}, engine_target_slots={y['target_slots']}")
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
