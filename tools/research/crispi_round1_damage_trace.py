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

    for event in result["events"]:
        if event.get("round") != 1:
            continue
        kind = event["type"]
        d = event.get("details", {})
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
    print(f"Wall breach physical positions: {[x['physical_position'] for x in model['breached_wall_positions']]}")
    print(f"JSON trace: {args.output}")


if __name__ == "__main__":
    main()
