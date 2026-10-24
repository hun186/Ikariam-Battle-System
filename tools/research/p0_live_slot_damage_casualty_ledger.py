"""Audit actual R1/R2 per-slot deaths/HP against grouped engine hit events.

This research-only module compares live simulator outputs for wholly SYNTHETIC
armies. Engine events can aggregate shots; they are NOT per-projectile records
and cannot verify Gameforge Accuracy, targeting or individual-hit behavior.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path

from ikariam_battle.units import UnitRegistry
from tools.research.p0_live_round2_prefire_postfire_ledger import (
    DOMAINS, SUPPORT_COUNTS, live_audit,
)

PROVENANCE = "SYNTHETIC_ENGINE_GROUPED_DAMAGE_EVENTS_AND_SLOT_HP_NOT_GAME_OBSERVATION"
EXACT = "current_engine_sequential_damage_balance"
EXPERIMENTAL_EXEMPT = "experimental_focus_or_overkill_model_requires_separate_calibration"
BASELINE_RESOLUTION = "sequential_d_kill_baseline"


def _key_from_slot(slot: dict) -> tuple[str, str, str]:
    return slot["unit_id"], slot["wave_id"], slot["slot_id"]


def _key_from_hit(hit: dict) -> tuple[str, str, str]:
    detail = hit["details"]
    return (detail["target_unit_id"], detail["target_wave"],
            detail["target_slot"])


def reconcile_round(side: str, round_number: int, before: dict, after: dict,
                    damage_events: list[dict], registry: UnitRegistry) -> list[dict]:
    if side not in ("attacker", "defender") or round_number not in (1, 2):
        raise ValueError("only actual R1 and R2 attacker/defender sides are supported")
    old = {_key_from_slot(s): s for s in before["slots"]}
    new = {_key_from_slot(s): s for s in after["slots"]}
    if len(old) != len(before["slots"]) or len(new) != len(after["slots"]):
        raise AssertionError("duplicate concrete wave/slot snapshot identity")
    hits = defaultdict(list)
    for event in damage_events:
        if event["type"] != "damage" or event["round"] != round_number:
            continue
        d = event["details"]
        if d.get("target_side") != side:
            continue
        key = _key_from_hit(event)
        if key not in old:
            raise AssertionError(f"event targets missing pre-volley slot {key}")
        if event["side"] == side:
            raise AssertionError(f"invalid side: source and target both {side}")
        hits[key].append(event)
    if not set(new) <= set(old):
        raise AssertionError(f"{side}/R{round_number}: new slot appeared during firing")
    result = []
    for key, pre in sorted(old.items()):
        post = new.get(key)
        if post is None:
            raise AssertionError(f"{side}/R{round_number}: old slot omitted at round end {key}")
        hp = registry.get(key[0]).hit_points
        if hp is None or hp <= 0:
            raise AssertionError(f"unknown slot unit HP for {key}")
        start_units, end_units = pre["units"], post["units"]
        start_wounds, end_wounds = pre["damage"], post["damage"]
        if end_units > start_units or start_units < 0 or end_units < 0:
            raise AssertionError(f"illegal in-volley resurrection {key}")
        if any(type(v) is not int or v < 0
               for v in (start_wounds, end_wounds)):
            raise AssertionError(f"invalid per-slot injury {key}")
        deaths = start_units - end_units
        recorded_deaths = post["casualties"]
        if deaths != recorded_deaths:
            raise AssertionError(
                f"slot casualties disagree with pre/end live units {key}: "
                f"{deaths} != {recorded_deaths}"
            )

        entries = hits[key]
        events_killed = sum(int(e["details"]["casualties"]) for e in entries)
        incoming = sum(int(e["details"]["damage"]) for e in entries)
        discarded = sum(int(e["details"]["overkill_discarded"]) for e in entries)
        if (any(type(e["details"].get(field)) is not int
                or e["details"][field] < 0
                for e in entries
                for field in ("damage", "casualties", "overkill_discarded"))
                or events_killed != deaths):
            raise AssertionError(f"per-slot grouped-event deaths disagree with snapshot {key}")
        if any(
            e["details"].get("target_damage_position") != pre["damage_position"]
            for e in entries
        ):
            raise AssertionError(f"event targets wrong damage-position address {key}")
        # The default sequential individual-hit implementation conserves
        # incoming HP *after* deducting lethal overkill. Bounded naval pooled
        # and Swordsman M-/I-Kill overrides can explicitly retain/reallocate
        # overkill; do not falsely certify their damage ledger as canonical.
        hp_residual = start_wounds + incoming - (
            deaths * hp + end_wounds + discarded
        )
        resolutions = sorted({str(e.get("details", {}).get("resolution"))
                              for e in entries})
        overrides = [x for x in resolutions if x != BASELINE_RESOLUTION]
        if hp_residual and not overrides:
            raise AssertionError(
                f"sequential HP balance mismatch {key}: residual {hp_residual}, "
                f"start {start_wounds}, hits {incoming}, dead {deaths}, "
                f"end {end_wounds}, overkill {discarded}"
            )
        if not entries and (deaths or start_wounds != end_wounds):
            raise AssertionError(f"slot changed HP/deaths without a damage event {key}")
        result.append({
            "side": side, "round": round_number,
            "unit_id": key[0], "wave_id": key[1], "slot_id": key[2],
            "damage_position": pre["damage_position"],
            "units_before": start_units, "units_after": end_units,
            "dead": deaths, "snapshot_casualties": recorded_deaths,
            "event_casualties": events_killed, "hp_per_unit": hp,
            "wounds_before": start_wounds, "wounds_after": end_wounds,
            "incoming_hp": incoming, "overkill_discarded": discarded,
            "hp_balance_residual": hp_residual,
            "grouped_event_count": len(entries),
            "resolutions": resolutions,
            "balance_status": (
                EXACT if not hp_residual else EXPERIMENTAL_EXEMPT
            ),
            "independent_game_holdout": False,
        })
    if len(result) != len(old):
        raise AssertionError("missing concrete Slot in audited ledger")
    # Reconcile per-unit deaths from both independent sources: the round-level
    # combat count and the post-combat individual slot-casualties.
    total_by_unit = defaultdict(int)
    for row in result:
        total_by_unit[row["unit_id"]] += row["dead"]
    declared = {
        k: v for k, v in after.get("_round_casualties", {}).items() if v
    }
    if declared and {
        k: v for k, v in total_by_unit.items() if v
    } != declared:
        raise AssertionError("per-slot deaths disagree with round unit totals")
    return result


def slot_case(domain: str, supporters: int) -> dict:
    core = live_audit(domain, supporters)
    registry = UnitRegistry.load(include_barbarians=True)
    rows = []
    for side in ("attacker", "defender"):
        w = core["witness"][side]
        for number in (1, 2):
            pre = w[f"round{number}_prefire"]
            post = w[f"round{number}_end"]
            # Pass the published per-unit round casualty ledger as an
            # independent third source, not inferred from events/slot counts.
            post = {**post, "_round_casualties": core["round_casualties"][str(number)][side]}
            rows.extend(reconcile_round(
                side, number, pre, post, core["round_damage_events"], registry
            ))
    if not any(row["dead"] > 0 and row["round"] == 2 for row in rows):
        raise AssertionError("no genuine R2 slot casualties to reconcile")
    if not any(row["incoming_hp"] and row["wounds_after"] > 0
               for row in rows):
        raise AssertionError("no wounded R1/R2 survivor slot to reconcile")
    return {
        "case_id": core["case_id"], "provenance": PROVENANCE,
        "domain": domain, "supporters": supporters,
        "actual_R1_R2_simulator_firing": True,
        "real_game_observations": 0, "independent_game_holdouts": 0,
        "rounds": 2,
        "rows": rows,
        "counts": {
            "concrete_slot_rounds": len(rows),
            "grouped_damage_events": sum(row["grouped_event_count"] for row in rows),
            "audited_slot_deaths": sum(row["dead"] for row in rows),
            "model_specific_hp_residuals": sum(
                row["balance_status"] == EXPERIMENTAL_EXEMPT for row in rows
            ),
        },
        "interpretation": (
            "Default sequential model HP conservation only. Pooled and "
            "other bounded experimental overrides are explicitly classified "
            "and cannot identify official Gameforge targeting, P or IR."
        ),
    }


def report() -> dict:
    cases = [
        slot_case(domain, supporters)
        for domain in DOMAINS for supporters in SUPPORT_COUNTS
    ]
    return {
        "schema": "p0_actual_two_round_per_slot_grouped_damage_ledger_v1",
        "provenance": PROVENANCE,
        "summary": {
            "synthetic_cases": len(cases),
            "game_observations": 0,
            "independent_holdouts": 0,
            "slot_rounds": sum(x["counts"]["concrete_slot_rounds"] for x in cases),
            "slot_deaths": sum(x["counts"]["audited_slot_deaths"] for x in cases),
            "noncanonical_hp_balances": sum(
                x["counts"]["model_specific_hp_residuals"] for x in cases
            ),
        },
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()
    data = report()
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    rows = [row for case in data["cases"] for row in case["rows"]]
    with args.output_csv.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(data["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
