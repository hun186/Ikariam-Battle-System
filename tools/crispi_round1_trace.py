"""Reproduce Crispi round-one model traces without changing battle mechanics.

Run: python -m tools.crispi_round1_trace
Only the fixture's `scenario` is simulated. `observed` and `legacy_model`
remain distinct data sources; neither is used to force computed losses.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from ikariam_battle import simulate


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "reverse_engineering" / "crispi_round1.json"


def collect_trace(case: dict, result: dict) -> dict:
    """Return per-event, per-source and per-target evidence; no inferred shots."""
    events = [
        event for event in result["events"] if event.get("round") == 1
    ]
    firing_types = {"damage", "damage_calculation", "wall_damage"}
    shots = [event for event in events if event.get("type") in firing_types]
    by_source = defaultdict(list)
    for event in shots:
        detail = event.get("details") or {}
        key = (
            str(event.get("side") or "unspecified"),
            str(detail.get("source_unit_id") or "unspecified"),
            str(event.get("type") or "unspecified"),
        )
        by_source[key].append({
            "phase": event.get("phase"),
            "details": detail,
        })
    current = result["rounds"][1]["casualties"]
    observed = case["observed"]["casualties"]
    old = case["legacy_model"]["casualties"]
    return {
        "case_id": case["case_id"],
        "round": 1,
        "status": result["status"],
        "completed_rounds": result["rounds_completed"],
        "observed": observed,
        "current_model": current,
        "legacy_model_pre_pr63": old,
        "attacker_hoplite_gap_observed_minus_model": (
            observed["attacker"]["hoplite"] -
            current["attacker"].get("hoplite", 0)
        ),
        "slot_losses": {
            side: [
                {k: slot.get(k) for k in (
                    "line", "physical_position", "damage_position",
                    "unit_id", "units", "casualties", "damage",
                )}
                for slot in result["rounds"][1][side]["slots"]
                if slot.get("casualties", 0)
            ]
            for side in ("attacker", "defender")
        },
        "event_counts": {
            event_type: sum(e.get("type") == event_type for e in events)
            for event_type in sorted({e.get("type") for e in events})
        },
        "wall_breach_outcomes": [
            event for event in events if event.get("type") == "wall_section_breached"
        ],
        "damage_events_by_source": {
            "/".join(key): rows for key, rows in sorted(by_source.items())
        },
        "unsupported_mechanics": [
            e for e in events if e.get("type") == "unsupported_mechanic"
        ],
    }


def run_trace(fixture_path: Path = FIXTURE) -> dict:
    case = json.loads(fixture_path.read_text(encoding="utf-8"))
    scenario = dict(case["scenario"])
    scenario["max_rounds"] = 1
    result = simulate(scenario)
    return collect_trace(case, result)


def main() -> None:
    print(json.dumps(run_trace(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
