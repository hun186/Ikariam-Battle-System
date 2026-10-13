"""Reproducible, evidence-separated Crispi Round 1 event attribution trace.

This report reads the frozen user-observed fixture and runs the *current*
simulator on that scenario. A simulator event is NOT an in-game shot log.
No experimental wall/firearm formulas or loss numbers are changed here.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import os
import re
import subprocess
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from ikariam_battle import simulate  # noqa: E402

CASE_PATH = ROOT / "tests/fixtures/reverse_engineering/crispi_round1.json"


def resolve_revision() -> str:
    """Require immutable 40-character commit SHA in exported evidence."""
    revision = os.environ.get("GITHUB_SHA")
    if not revision:
        # A local HEAD is reproducible only when the entire checkout is clean.
        # Include untracked files: they can shadow imports or alter the fixture.
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=ROOT, text=True,
        )
        if dirty.strip():
            raise RuntimeError(
                "Cannot attribute a local trace to HEAD with a dirty worktree; "
                "commit or remove local changes first"
            )
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Trace requires an exact full 40-character Git commit SHA")
    return revision



def compare_hoplite_physical_positions(case: dict, round1: dict, damage_events: list[dict]) -> dict:
    """Compare independently observed physical slots with current simulator slots.

    The engine's AM addresses *damage positions*. Never assume those numbers
    equal left-to-right *physical positions*: map them through the actual
    Round-1 attacker First-line slot snapshot before joining event sources.
    """
    observed = case["observed"]["slot_losses"]["attacker"]["hoplite"]
    snapshot = [
        slot for slot in round1["attacker"]["slots"]
        if slot.get("line") == "first" and slot.get("unit_id") == "hoplite"
    ]
    by_physical = {}
    by_damage = {}
    for slot in snapshot:
        physical = slot.get("physical_position")
        damage = slot.get("damage_position")
        if not isinstance(physical, int) or not isinstance(damage, int):
            raise ValueError("Crispi Hoplite slots require explicit physical and damage positions")
        if physical in by_physical or damage in by_damage:
            raise ValueError("Ambiguous Hoplite physical-to-damage-position mapping")
        by_physical[physical] = slot
        by_damage[damage] = physical

    expected_positions = set(range(1, len(observed) + 1))
    if set(by_physical) != expected_positions:
        raise ValueError("Crispi physical Hoplite positions must cover the observed seven slots")

    event_sources = defaultdict(lambda: defaultdict(lambda: {
        "casualties": 0, "shots": 0, "net_damage": 0,
    }))
    unmapped_events = []
    for event in damage_events:
        damage_position = event.get("target_damage_position")
        if damage_position not in by_damage:
            unmapped_events.append({
                "target_damage_position": damage_position,
                "source_unit_id": event.get("source_unit_id"),
                "casualties": event.get("casualties"),
            })
            continue
        physical = by_damage[damage_position]
        source = event_sources[physical][event["source_unit_id"]]
        for field in ("casualties", "shots", "net_damage"):
            source[field] += int(event.get(field) or 0)

    rows = []
    for physical in sorted(expected_positions):
        slot = by_physical[physical]
        modeled = int(slot.get("casualties") or 0)
        sources = dict(sorted(event_sources[physical].items()))
        rows.append({
            "physical_position": physical,
            "model_damage_position": slot["damage_position"],
            "observed_hoplite_losses": observed[physical - 1],
            "modeled_hoplite_losses": modeled,
            "gap_observed_minus_modeled": observed[physical - 1] - modeled,
            "modeled_remaining_units": slot.get("units"),
            "modeled_slot_damage": slot.get("damage"),
            "modeled_defender_sources": sources,
            "source_losses_equal_slot": sum(x["casualties"] for x in sources.values()) == modeled,
        })

    observed_total = sum(observed)
    modeled_total = sum(row["modeled_hoplite_losses"] for row in rows)
    return {
        "position_basis": "physical left-to-right 1..7, mapped via current Round-1 slot snapshot",
        "event_basis": "simulator damage events only; observed game source attribution unavailable",
        "positions": rows,
        "observed_total": observed_total,
        "modeled_total": modeled_total,
        "gap_observed_minus_modeled": observed_total - modeled_total,
        "source_losses_equal_each_slot": all(row["source_losses_equal_slot"] for row in rows),
        "unmapped_simulator_events": unmapped_events,
    }



def evaluate_surviving_wall_one_kill_hypothesis(case: dict, matrix: dict) -> dict:
    """Conditional wall/firearm attribution, not observed game shot telemetry.

    Assume destroyed sections cannot shoot after artillery, surviving walls
    fire once at the directly facing physical First slot and kill one there,
    and current modeled Mortar kills match real Mortar kills. Do not modify
    engine casualties using this analytical counterfactual.
    """
    wall_alive = case["observed"]["wall_alive_physical"]
    rows = matrix["positions"]
    if len(wall_alive) != len(rows):
        raise ValueError("Observed wall mask must match physical First positions")
    inferred = []
    for index, (alive, row) in enumerate(zip(wall_alive, rows), 1):
        if row["physical_position"] != index or alive not in (0, 1):
            raise ValueError("Wall hypothesis requires ordered physical slots and 0/1 mask")
        mortar = row["modeled_defender_sources"].get("mortar", {}).get("casualties", 0)
        carabineer = row["modeled_defender_sources"].get(
            "sulphur_carabineer", {}
        ).get("casualties", 0)
        firearm_needed = row["observed_hoplite_losses"] - mortar - alive
        inferred.append({
            "physical_position": index,
            "observed_hoplite_losses": row["observed_hoplite_losses"],
            "wall_survives_observed": bool(alive),
            "hypothesized_wall_kills": alive,
            "assumed_mortar_kills": mortar,
            "inferred_carabineer_kills": firearm_needed,
            "modeled_carabineer_kills": carabineer,
            "inferred_minus_modeled_carabineer_kills": firearm_needed - carabineer,
        })
    return {
        "status": "UNVERIFIED_CONDITIONAL_DECOMPOSITION",
        "hypothesis_id": "HYP-WALL-SURVIVING-FACING-ONE-KILL-001",
        "assumptions": [
            "Breached wall sections cannot fire in the later First firing phase",
            "Each surviving wall section targets its directly facing physical First slot",
            "Each surviving wall section fires successfully and kills one attacker Hoplite",
            "Actual Mortar kills per physical slot match current simulator Mortar events",
            "No further sources change the counted First-line deaths",
        ],
        "rows": inferred,
        "wall_kills_total": sum(r["hypothesized_wall_kills"] for r in inferred),
        "assumed_mortar_kills_total": sum(r["assumed_mortar_kills"] for r in inferred),
        "inferred_carabineer_kills_total": sum(r["inferred_carabineer_kills"] for r in inferred),
        "all_inferred_carabineer_counts_nonnegative": all(
            r["inferred_carabineer_kills"] >= 0 for r in inferred
        ),
    }


def build_report(source_commit_sha: str | None = None) -> dict:
    case = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    scenario = json.loads(json.dumps(case["scenario"]))
    scenario["max_rounds"] = 1
    result = simulate(scenario)
    if len(result["rounds"]) < 2:
        raise RuntimeError("Crispi case ended before Round 1; inspect UNKNOWN events")

    round1 = result["rounds"][1]
    model_losses = round1["casualties"]["attacker"].get("hoplite", 0)
    observed_losses = case["observed"]["casualties"]["attacker"]["hoplite"]
    sources = defaultdict(lambda: {
        "casualties": 0, "shots": 0, "net_damage": 0,
        "target_positions": defaultdict(lambda: {"casualties": 0, "shots": 0, "net_damage": 0}),
    })
    damage_events = []
    damage_calculations = []
    relevant_assumptions = set()
    breaches = []
    other_unsupported = []
    # Raw simulator events are evidence, not actual game shot telemetry.
    raw_events_by_source = defaultdict(list)
    wall_shot_events = []
    wall_breach_outcomes = []

    for event in result["events"]:
        if event.get("round") != 1:
            continue
        kind = event["type"]
        d = event.get("details") or {}
        if kind in {"damage", "damage_calculation", "wall_damage"}:
            key = "/".join((
                str(event.get("side") or "unspecified"),
                str(d.get("source_unit_id") or "unspecified"),
                kind,
            ))
            raw_events_by_source[key].append({
                "phase": event.get("phase"),
                "details": d,
            })
        if kind == "wall_damage":
            wall_shot_events.append({
                "side": event.get("side"),
                "phase": event.get("phase"),
                "details": d,
            })
        if kind == "damage" and event.get("side") == "defender" and d.get("target_unit_id") == "hoplite":
            unit_id = d.get("source_unit_id", "unidentified")
            counts = {
                "casualties": int(d.get("casualties", 0)),
                "shots": int(d.get("firing_units", 0)),
                "net_damage": int(d.get("damage", 0)),
            }
            pos = str(d.get("target_damage_position", "unknown"))
            for key, number in counts.items():
                sources[unit_id][key] += number
                sources[unit_id]["target_positions"][pos][key] += number
            damage_events.append({
                "source_unit_id": unit_id,
                "target_damage_position": d.get("target_damage_position"),
                "target_line": d.get("target_line"),
                "target_slot": d.get("target_slot"),
                "firing_phase": d.get("firing_phase"),
                "casualties": counts["casualties"],
                "shots": counts["shots"],
                "net_damage": counts["net_damage"],
                "prior_damage": d.get("prior_damage"),
                "persistent_damage": d.get("persistent_damage"),
                "overkill_discarded": d.get("overkill_discarded"),
                "accuracy_model": d.get("accuracy_model"),
                "source_column_hits": d.get("source_column_hits"),
            })
        elif kind == "damage_calculation" and event.get("side") == "defender" and d.get("target_unit_id") == "hoplite":
            damage_calculations.append({
                "source_unit_id": d.get("source_unit_id"),
                "firing_phase": d.get("firing_phase"),
                "final_damage_per_hit": d.get("final_damage"),
                "forge_level": d.get("forge_level"),
                "weapon_id": d.get("weapon_id"),
            })
        elif kind == "assumption_applied":
            if d.get("id"):
                relevant_assumptions.add(d["id"])
        elif kind == "wall_section_breached":
            wall_breach_outcomes.append({
                "side": event.get("side"),
                "phase": event.get("phase"),
                "details": d,
            })
            breaches.append({
                "physical_position": d.get("physical_position"),
                "damage_position": d.get("damage_position"),
            })
        elif kind == "unsupported_mechanic":
            other_unsupported.append({"phase": event.get("phase"), "details": d})

    grouped = {
        name: {
            key: dict(sorted(value.items())) if key == "target_positions" else value
            for key, value in data.items()
        } for name, data in sorted(sources.items())
    }
    attribution_sum = sum(entry["casualties"] for entry in grouped.values())
    legacy = case["legacy_model"]["casualties"]["attacker"]["hoplite"]
    position_comparison = compare_hoplite_physical_positions(case, round1, damage_events)
    wall_fire_hypothesis = evaluate_surviving_wall_one_kill_hypothesis(
        case, position_comparison,
    )

    return {
        "schema_version": 1,
        "source_commit_sha": source_commit_sha,
        "case_id": case["case_id"],
        "evidence_boundary": {
            "observed": "User-supplied game screenshot; casualties are not per-source game telemetry",
            "legacy_model": "Pre-PR63 simulator export; not current model output",
            "current_model": "Simulator-generated events for source_commit_sha on this checked-out commit",
        },
        "observed": {
            "attacker_hoplite_casualties": observed_losses,
            "attacker_hoplite_slot_losses_physical": case["observed"]["slot_losses"]["attacker"]["hoplite"],
            "wall_alive_physical": case["observed"]["wall_alive_physical"],
            "source_attribution_hypothesis": case["observed"]["source_attribution_hypothesis"],
        },
        "legacy_model": {"attacker_hoplite_casualties": legacy},
        "physical_hoplite_comparison": position_comparison,
        "conditional_wall_fire_hypothesis": wall_fire_hypothesis,
        "current_model": {
            "status": result.get("status"),
            "rounds_completed": result.get("rounds_completed"),
            "attacker_hoplite_casualties": model_losses,
            "delta_observed_minus_model": observed_losses - model_losses,
            "defender_hoplite_casualties": round1["casualties"]["defender"].get("hoplite", 0),
            "defender_bombardier_casualties": round1["casualties"]["defender"].get("bombardier", 0),
            "attacker_bombardier_casualties": round1["casualties"]["attacker"].get("bombardier", 0),
            "defender_first_damage_events": [
                {"source_unit_id": e["details"].get("source_unit_id"),
                 "casualties": e["details"].get("casualties")}
                for e in result["events"]
                if e.get("round") == 1 and e.get("side") == "defender"
                and e["type"] == "damage" and e["details"].get("firing_phase") == "first"
            ],
            "defender_sources_to_attacker_hoplite": grouped,
            "reported_source_casualties_sum": attribution_sum,
            "source_events_sum_equals_snapshot": attribution_sum == model_losses,
            "defender_damage_calculations": damage_calculations,
            "breached_wall_positions": breaches,
            "assumptions_applied_in_round1": sorted(relevant_assumptions),
            "unsupported_events": other_unsupported,
            "damage_events": damage_events,
            "raw_damage_events_by_source": dict(sorted(raw_events_by_source.items())),
            "wall_damage_events": wall_shot_events,
            "wall_breach_outcomes": wall_breach_outcomes,
            "slot_losses": {
                side: [
                    {key: slot.get(key) for key in (
                        "line", "physical_position", "damage_position",
                        "unit_id", "units", "casualties", "damage",
                    )}
                    for slot in round1[side]["slots"]
                    if slot.get("casualties", 0)
                ]
                for side in ("attacker", "defender")
            },
            "event_counts": {
                kind: sum(
                    e.get("round") == 1 and e.get("type") == kind
                    for e in result["events"]
                )
                for kind in sorted({
                    e.get("type") for e in result["events"]
                    if e.get("round") == 1
                })
            },
        },
        "unproven": [
            "Which attacker Hoplites the game Town Wall actually kills",
            "The game's exact per-hit Carabineer Accuracy, targeting and redistribution",
            "Whether SR/IR are triggered between the relevant in-game formations",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Write JSON artifact here")
    args = parser.parse_args()
    # Only an exported artifact claims immutable Git revision provenance.
    report = build_report(source_commit_sha=resolve_revision())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    model = report["current_model"]
    print(f"Crispi R1 observed Hoplite casualties: {report['observed']['attacker_hoplite_casualties']}")
    print(f"Legacy pre-PR63 model: {report['legacy_model']['attacker_hoplite_casualties']}")
    print(f"Current model: {model['attacker_hoplite_casualties']}; observed minus model: {model['delta_observed_minus_model']}")
    print("Defender sources to attacker Hoplite:")
    for unit, source in model["defender_sources_to_attacker_hoplite"].items():
        print(f"  {unit}: casualties={source['casualties']}, shots={source['shots']}, net_damage={source['net_damage']}")
        positions = ", ".join(
            f"{position}: {values['casualties']} killed / {values['shots']} hits"
            for position, values in sorted(
                source["target_positions"].items(), key=lambda pair: int(pair[0])
            )
        )
        print(f"    target damage positions: {positions}")
    print(f"Event source sum equals snapshot: {model['source_events_sum_equals_snapshot']}")
    print("Observed/model Hoplite by physical position (left to right):")
    for row in report["physical_hoplite_comparison"]["positions"]:
        print(
            f"  physical {row['physical_position']} / damage {row['model_damage_position']}: "
            f"observed={row['observed_hoplite_losses']}, modeled={row['modeled_hoplite_losses']}, "
            f"gap={row['gap_observed_minus_modeled']}, "
            f"simulated_sources={row['modeled_defender_sources']}"
        )
    print(f"Wall breach physical positions: {[x['physical_position'] for x in model['breached_wall_positions']]}")
    print(f"JSON trace: {args.output}")


if __name__ == "__main__":
    main()
