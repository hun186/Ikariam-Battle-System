"""Invert the historical naval HP bars into *conditional* integer wound ranges.

Original chat HP bars are real-game reports, but the physical-slot mapping and
UI percent display semantics are UNKNOWN. All damage, hit counts and overkill
budgets here come from the current SYNTHETIC engine, not Gameforge shot traces.
No production combat or official Gameforge rule is changed or claimed.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import json
from itertools import permutations
from pathlib import Path

from tools.research import p0_naval_slot_hp_falsification as historical

ROUNDING_MODES = ("floor", "nearest_half_up", "ceil")
BAR_CLASS = "USER_CHAT_REPORTED_UNMAPPED_PERCENT_IN_SAMPLE"
MODEL_CLASS = "SYNTHETIC_ENGINE_R1_GROUPED_DAMAGE_AND_DISCARDED_OVERKILL"
STATUS_UNKNOWN = "not_assessable_no_original_bars"
CONDITIONAL = "conditional_overkill_budget_feasibility_not_game_mechanic_validation"
FIXTURE = "tests/fixtures/reverse_engineering/naval_air_counterparts_20261013.json"


def _integer(value: int, description: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{description} must be an integer")
    return value


def _ceildiv(x: int, denominator: int) -> int:
    return -(-x // denominator)


def percent_window(percent: int, full_hp: int, mode: str) -> tuple[int, int]:
    """All *integer retained wound HP* values displaying a given percent.

    This is independent of any guessed game shot distribution. Uses exact
    rational integer bounds rather than error-prone floating point inversion.
    """
    p = _integer(percent, "visible percentage")
    cap = _integer(full_hp, "living Slot HP capacity")
    if not 0 <= p <= 100 or cap <= 0 or mode not in ROUNDING_MODES:
        raise ValueError("percentage, living capacity or rounding mode invalid")
    if mode == "floor":
        survivors_min = _ceildiv(p * cap, 100)
        survivors_max = _ceildiv((p + 1) * cap, 100) - 1
    elif mode == "nearest_half_up":
        survivors_min = _ceildiv((2 * p - 1) * cap, 200)
        survivors_max = _ceildiv((2 * p + 1) * cap, 200) - 1
    else:
        survivors_min = ((p - 1) * cap) // 100 + 1
        survivors_max = (p * cap) // 100
    survivors_min = max(0, survivors_min)
    survivors_max = min(cap, survivors_max)
    if survivors_min > survivors_max:
        raise ValueError("reported integer bar impossible at current HP resolution")
    return cap - survivors_max, cap - survivors_min


def display_percent(living_hp: int, full_hp: int, mode: str) -> int:
    living = _integer(living_hp, "living HP")
    cap = _integer(full_hp, "full living HP")
    if cap <= 0 or not 0 <= living <= cap or mode not in ROUNDING_MODES:
        raise ValueError("invalid displayed HP denominator or living HP")
    if mode == "floor":
        return 100 * living // cap
    if mode == "nearest_half_up":
        return (200 * living + cap) // (2 * cap)
    return _ceildiv(100 * living, cap)


def _model_slots(case: dict) -> list[dict]:
    """Read only this actual controlled model's addressed events and HP."""
    model, observed = case["model"], case["observed"]
    if case["evaluation_split"] != historical.IN_SAMPLE or case["independent_holdout"]:
        raise ValueError("historically fitted sample may not claim holdout")
    if observed["physical_slot_mapping"] != "unknown":
        raise ValueError("original source physical Slot mapping changed")
    if case["diagnostics"]["hp_bar_semantics"] != historical.UNVERIFIED:
        raise ValueError("source UI bar semantics no longer marked unknown")
    if not model["invented_first_line_fillers"]:
        raise ValueError("controlled model provenance changed")
    slots = sorted(model["per_slot"], key=lambda x: x["damage_position"])
    if len(slots) != 2 or len({x["damage_position"] for x in slots}) != 2:
        raise ValueError("expected exactly two distinct model Carrier Slots")
    events_by_pos = defaultdict(list)
    for event in model["target_damage_events"]:
        if event["type"] != "damage" or event["round"] != 1:
            raise ValueError("unrelated event in model target damage record")
        d = event["details"]
        if d["target_unit_id"] != slots[0]["unit_id"] or d["target_side"] != "defender":
            raise ValueError("unexpected target in controlled model damage record")
        events_by_pos[d["target_damage_position"]].append(event)
    if set(events_by_pos) != {s["damage_position"] for s in slots}:
        raise ValueError("model hit events fail to cover both target Slots")

    result = []
    for slot in slots:
        alive, dead = slot["units"], slot["casualties"]
        wounds, hp = slot["damage"], model["target_unit_hp"]
        if any(type(x) is not int or x < 0 for x in (alive, dead, wounds, hp)):
            raise ValueError("model Slot counts and HP must be nonnegative integers")
        if hp == 0 or alive == 0 or alive + dead != 3 or wounds >= alive * hp:
            raise ValueError("model target survivor HP/count invariants changed")
        addressed = events_by_pos[slot["damage_position"]]
        # Even different source contexts may share a physical target Slot;
        # grouped events are not individual Gameforge hits.
        gross, thrown, events_dead = 0, 0, 0
        ids = set()
        for event in addressed:
            d = event["details"]
            if d["target_wave"] != "wave-1" or d["target_slot"] is None:
                raise ValueError("grouped target identity is incomplete")
            for key in ("damage", "overkill_discarded", "casualties"):
                if type(d[key]) is not int or d[key] < 0:
                    raise ValueError("grouped synthetic hit value not nonnegative integer")
            gross += d["damage"]
            thrown += d["overkill_discarded"]
            events_dead += d["casualties"]
            ids.update(d.get("assumption_ids", []))
        if events_dead != dead or gross != dead * hp + wounds + thrown:
            raise ValueError("synthetic grouped hit budget does not reconcile with Slot HP")
        if not ids:
            raise ValueError("model event assumption provenance missing")
        cap = alive * hp
        if display_percent(cap - wounds, cap, "floor") != slot["modeled_hp_bar_percent"]:
            raise ValueError("current engine model bar differs from slot injury")
        result.append({
            "damage_position": slot["damage_position"],
            "physical_position_model_only": slot["physical_position"],
            "unit_id": slot["unit_id"], "living_units": alive,
            "dead_units_model": dead, "unit_hp": hp,
            "survivor_hp_capacity": cap,
            "survivor_wounds_model": wounds, "nominal_incoming_damage_model": gross,
            "discarded_overkill_model": thrown, "event_casualties_model": events_dead,
            "assumption_ids_model": sorted(ids),
            "reported_engine_floor_bar": slot["modeled_hp_bar_percent"],
            "grouped_model_events": addressed,
        })
    return result


def analyze_case(case: dict) -> dict:
    model_slots = _model_slots(case)
    observed = case["observed"]
    bars = observed["hp_bars_unmapped_percent"]
    base = {
        "case_id": case["case_id"],
        "evaluation_split": historical.IN_SAMPLE,
        "observed_source": observed["source"],
        "observed_evidence_class": observed["evidence_class"],
        "observed_round": observed["reported_round"],
        "observed_total_deaths": observed["total_deaths"],
        "observed_slot_deaths": observed["per_slot_deaths"],
        "original_physical_slot_mapping": "unknown",
        "ui_hp_bar_rule_verified": False,
        "model_evidence_class": MODEL_CLASS,
        "invented_first_line_fillers": True,
        "independent_game_holdout": False,
        "official_game_mechanic_verified": False,
        "model_slots": model_slots,
        "observed_bars_unmapped": bars,
    }
    if bars is None:
        return {
            **base, "status": STATUS_UNKNOWN, "conditional_mappings": [],
            "missing_original_observations": [
                "round-scoped source HP bar screenshot",
                "matching numbered physical Slot address",
                "UI percentage rounding and denominator definition",
            ],
        }
    if (len(bars) != 2 or len(set(bars)) != 2 or
            any(type(x) is not int or x < 0 or x > 100 for x in bars)):
        raise ValueError("original two HP bars invalid/duplicated: recheck fixture")
    options = []
    for mode in ROUNDING_MODES:
        for assignment in sorted(set(permutations(bars))):
            by_slot = []
            for slot, bar in zip(model_slots, assignment):
                low, high = percent_window(bar, slot["survivor_hp_capacity"], mode)
                extra_low = low - slot["survivor_wounds_model"]
                extra_high = high - slot["survivor_wounds_model"]
                budget = slot["discarded_overkill_model"]
                retained_min = max(extra_low, 0)
                retained_max = min(extra_high, budget)
                possible = retained_min <= retained_max
                by_slot.append({
                    "model_damage_position": slot["damage_position"],
                    "assigned_original_percent_unverified_mapping": bar,
                    "inverted_wounds_min": low, "inverted_wounds_max": high,
                    "additional_wounds_required_min": extra_low,
                    "additional_wounds_required_max": extra_high,
                    "synthetic_discarded_overkill_budget": budget,
                    "overkill_recovery_feasible": possible,
                    "feasible_recovered_overkill_min": retained_min if possible else None,
                    "feasible_recovered_overkill_max": retained_max if possible else None,
                    "no_recovery_display_bar": display_percent(
                        slot["survivor_hp_capacity"] - slot["survivor_wounds_model"],
                        slot["survivor_hp_capacity"], mode),
                    "full_recovery_display_bar": display_percent(
                        slot["survivor_hp_capacity"] - slot["survivor_wounds_model"] - budget,
                        slot["survivor_hp_capacity"], mode),
                    "scenario": CONDITIONAL,
                })
            options.append({
                "ui_rounding_hypothesis": mode,
                "original_bar_mapping_status": "unmapped_permutation_hypothesis",
                "all_slots_overkill_budget_feasible": all(
                    x["overkill_recovery_feasible"] for x in by_slot
                ),
                "slots": by_slot,
            })
    return {
        **base, "status": CONDITIONAL, "conditional_mappings": options,
        "missing_original_observations": [
            "actual physical Slot to UI bar correspondence",
            "official UI display rounding/denominator specification",
            "complete actual fleet and individual firing/overkill outcome",
        ],
    }


def build_report() -> dict:
    baseline = historical.build_report()
    if baseline["summary"]["historically_analyzed_cases"] != 5 or baseline["summary"]["independent_holdout_cases"] != 0:
        raise ValueError("historical sample scope changed: re-audit before report")
    cases = [analyze_case(case) for case in baseline["cases"]]
    return {
        "schema": "p0_naval_hp_bar_inverse_integer_bounds_v1",
        "source_fixture": FIXTURE,
        "classification": "HISTORICAL_IN_SAMPLE_CONDITIONAL_INVERSE_NOT_OFFICIAL_GAME_PROOF",
        "summary": {
            "historical_cases": len(cases),
            "cases_with_reported_original_bars": sum(
                c["status"] == CONDITIONAL for c in cases
            ),
            "new_game_observations": 0,
            "independent_holdouts": 0,
            "official_game_mechanic_verified": False,
            "feasible_mapping_counts_by_rounding": {
                mode: sum(
                    item["all_slots_overkill_budget_feasible"]
                    for case in cases
                    for item in case["conditional_mappings"]
                    if item["ui_rounding_hypothesis"] == mode
                ) for mode in ROUNDING_MODES
            },
        },
        "cases": cases,
        "conclusion_limit": (
            "Percent inversion proves only conditional integer feasibility "
            "under current SYNTHETIC engine damage/overkill and assumed "
            "survivor-only HP denominator, not Gameforge mechanics or UI rules."
        ),
    }


def csv_rows(report: dict) -> list[dict]:
    data = []
    for case in report["cases"]:
        for option in case["conditional_mappings"]:
            for slot in option["slots"]:
                data.append({
                    "case_id": case["case_id"],
                    "source": case["observed_source"],
                    "round_observed": case["observed_round"],
                    "original_bars_unmapped_json": json.dumps(case["observed_bars_unmapped"]),
                    "rounding_hypothesis": option["ui_rounding_hypothesis"],
                    "mapping_status": option["original_bar_mapping_status"],
                    "whole_mapping_feasible": option["all_slots_overkill_budget_feasible"],
                    "game_mechanic_verified": False,
                    "independent_holdout": False,
                    **slot,
                })
    if not data:
        raise ValueError("no reported source bars: no valid inverse comparisons")
    return data


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-json", required=True, type=Path)
    p.add_argument("--output-csv", required=True, type=Path)
    a = p.parse_args()
    report = build_report()
    a.output_json.parent.mkdir(parents=True, exist_ok=True)
    a.output_csv.parent.mkdir(parents=True, exist_ok=True)
    a.output_json.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    rows = csv_rows(report)
    with a.output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(report["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
