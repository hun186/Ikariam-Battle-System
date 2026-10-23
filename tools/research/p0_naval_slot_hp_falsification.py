"""Read-only historical counterpart slot-HP falsification report (not a holdout)."""
from __future__ import annotations
import argparse
import csv
from copy import deepcopy
import json
from pathlib import Path

from tools.research.naval_air_counterpart_probe import (
    FIXTURE, damage_and_round_observables, run_current_full_engine_control,
)

IN_SAMPLE = "previously_analyzed_in_sample"
UNVERIFIED = "ui_bar_semantics_and_physical_slot_mapping_unverified"
COUNTERFACTUAL = "conditional_full_damage_retention_not_verified_game_rule"


def _count(v, label):
    if type(v) is not int or v < 0:
        raise ValueError(f"{label} must be a nonnegative integer")
    return v


def _bars(v, label):
    if v is not None and (not isinstance(v, list) or len(v) != 2 or any(
        type(x) is not int or not 0 <= x <= 100 for x in v
    )):
        raise ValueError(f"{label} must be exactly two integer percentages")
    return v


def historical_cases(fixture):
    src = fixture.get("source", {})
    if (fixture.get("evidence_class") != "USER_CONVERSATION_REPORTED_REAL_GAME_OUTCOMES"
            or src.get("original_battle_reports_attached") is not False
            or src.get("raw_game_individual_shot_trace_available") is not False):
        raise ValueError("historical provenance changed: re-audit original source")
    original = fixture["observed"]
    if len(original) != 4 or len({x["case"] for x in original}) != 4:
        raise ValueError("historical original case set changed")
    cases = [(x, {
        "source": x["source"], "round": x.get("health_bars_observed_after_round"),
        "evidence_class": fixture["evidence_class"], "mapping_confirmed": False,
    }) for x in original]
    extra = fixture.get("additional_observations", [])
    if len(extra) != 1 or extra[0].get("case") != "barbarian_fast_vs_player_carrier_def3_no_forge":
        raise ValueError("expected one source-separated DEF3 observation")
    x = extra[0]
    if not (x.get("attacker_and_target_counts_verified_for_this_case") is True
            and x.get("round_number_verified") is True
            and x.get("known_per_slot_deaths") is False
            and x.get("aircraft_unit_id_mapping_verified") is False
            and x.get("confirmed_attacker_slot_counts") == [15, 15]
            and x.get("confirmed_target_slot_counts") == [3, 3]
            and x.get("confirmed_attacker_count") == 30
            and x.get("confirmed_target_count") == 6):
        raise ValueError("DEF3 source/formation confirmation changed")
    base = deepcopy(next(c for c in original if c["case"] == "barbarian_fast_vs_player_carrier_def7"))
    base.update({
        "case": x["case"],
        "player_defense_upgrade": _count(x["observed_player_defense_upgrade"], "defense"),
        "player_forge_level": _count(x["observed_player_forge_level"], "Forge"),
        "reported_player_total_deaths": _count(x["observed_total_player_carrier_deaths"], "deaths"),
        "source": x["source"],
    })
    base.pop("bar_percentages", None)
    if base["player_defense_upgrade"] != 3 or base["player_forge_level"] != 0:
        raise ValueError("DEF3 source parameter mismatch")
    cases.append((base, {
        "source": x["source"], "round": x["observed_round_number"],
        "evidence_class": x["evidence_class"],
        "mapping_confirmed": x["aircraft_unit_id_mapping_verified"],
    }))
    if len({c["case"] for c, _ in cases}) != 5:
        raise ValueError("duplicate historical case")
    return cases


def compare_case(case, provenance):
    if case.get("evaluation_split") not in (None, IN_SAMPLE) or case.get("independent_holdout") not in (None, False):
        raise ValueError("historically analyzed case cannot claim independent holdout")
    if case.get("source") not in ("USER_CHAT", "USER_CHAT_2026_10_13_NEW_OBSERVATION"):
        raise ValueError("source must be owner conversation, never engine synthesis")
    if (case["attacker_count"], case["target_count"], case["attacker_positions"],
            case["target_positions"], case["attacker_units_per_position"],
            case["target_units_per_position"]) != (30, 6, 2, 2, 15, 3):
        raise ValueError("controlled 30-v-6 two-slot scenario changed")

    if "reported_player_total_deaths" in case:
        observed_total = _count(case["reported_player_total_deaths"], "original deaths")
        original_slot_deaths = None
    else:
        n = _count(case["reported_barbarian_deaths_per_position"], "original per-slot deaths")
        observed_total, original_slot_deaths = 2 * n, [n, n]
    original_bars = _bars(case.get(
        "reported_occupied_slot_bars_percent",
        case.get("reported_survivor_slot_bars_percent")), "original HP bars")
    engine = run_current_full_engine_control(case)
    math = damage_and_round_observables(case)
    if engine["rounds_completed"] != 1 or engine["invented_first_line_filler_not_observed"] is not True:
        raise ValueError("controlled one-round engine scenario changed")
    slots = sorted(engine["target_slots"], key=lambda x: x["damage_position"])
    if len(slots) != 2 or len({x["damage_position"] for x in slots}) != 2:
        raise ValueError("model target slot coverage changed")
    hp = _count(math["target_unit_hp"], "target unit HP")
    if hp == 0:
        raise ValueError("zero unit HP")
    model_bars = []
    for slot in slots:
        if slot["unit_id"] != case["target"] or slot["line"] != "balloon":
            raise ValueError("unexpected target formation")
        remaining = _count(slot["units"], "remaining count")
        deaths = _count(slot["casualties"], "model deaths")
        damage = _count(slot["damage"], "model retained damage")
        if remaining + deaths != 3 or damage > remaining * hp:
            raise ValueError("invalid model per-slot headcount or retained HP")
        model_bars.append(100 * (remaining * hp - damage) // (remaining * hp) if remaining else None)
    if sum(s["casualties"] for s in slots) != engine["model_target_units_lost"]:
        raise ValueError("model slot casualties do not reconcile to reported total")
    events = [
        e for e in engine["synthetic_round1_model_events"]
        if e.get("type") == "damage"
        and (e.get("details") or {}).get("source_unit_id") == case["attacker"]
        and (e.get("details") or {}).get("target_unit_id") == case["target"]
    ]
    if not events or {e["details"].get("target_damage_position") for e in events} != {
        s["damage_position"] for s in slots
    }:
        raise ValueError("model damage-event target slots incomplete")
    if sum(_count(e["details"].get("firing_units"), "firing units") for e in events) != 30:
        raise ValueError("model target firing-unit ledger incomplete")
    # We lack original physical address mapping: sorted BAR PAIRS are
    # diagnostic only, not verified per-physical-slot game parity.
    paired = sorted(model_bars) if None not in model_bars and original_bars is not None else None
    residuals = [m - o for m, o in zip(paired, sorted(original_bars))] if paired is not None else None
    alternative = None
    if original_slot_deaths is not None:
        hypothetical = math["hypothetical_all_damage_retained_bars_truncated"]
        alternative = {
            "status": COUNTERFACTUAL,
            "not_engine_output": True,
            "bars_sorted": sorted(hypothetical),
            "residual_percent_points_sorted": (
                [v - o for v, o in zip(sorted(hypothetical), sorted(original_bars))]
                if original_bars is not None else None
            ),
        }
    return {
        "case_id": case["case"], "evaluation_split": IN_SAMPLE,
        "independent_holdout": False,
        "observed": {
            "source": provenance["source"], "evidence_class": provenance["evidence_class"],
            "reported_round": provenance["round"], "total_deaths": observed_total,
            "per_slot_deaths": original_slot_deaths,
            "hp_bars_unmapped_percent": original_bars,
            "game_unit_mapping_confirmed": provenance["mapping_confirmed"],
            "physical_slot_mapping": "unknown",
        },
        "model": {
            "source": "SYNTHETIC_CURRENT_ENGINE", "round": 1,
            "invented_first_line_fillers": True,
            "target_unit_hp": hp, "total_deaths": engine["model_target_units_lost"],
            "per_slot": [{**s, "modeled_hp_bar_percent": pct, "ammo": "unknown"}
                         for s, pct in zip(slots, model_bars)],
            "target_damage_events": events,
            "full_round1_event_trace": engine["synthetic_round1_model_events"],
            "assumption_ledger": engine["model_applied_assumptions"],
        },
        "diagnostics": {
            "total_residual_model_minus_game": engine["model_target_units_lost"] - observed_total,
            "aggregate": (
                "controlled_in_sample_match_not_validation"
                if engine["model_target_units_lost"] == observed_total else "controlled_mismatch_noncausal"
            ),
            "hp_bar_semantics": UNVERIFIED,
            "observed_hp_bars_sorted": sorted(original_bars) if original_bars is not None else None,
            "model_hp_bars_sorted": paired,
            "hp_bar_residual_percent_points_sorted": residuals,
            "slot_deaths_residual": (
                [s["casualties"] - v for s, v in zip(slots, original_slot_deaths)]
                if original_slot_deaths is not None else None
            ),
            "full_retention_arithmetic_counterfactual": alternative,
            "game_slot_hp_parity_verified": False,
            "official_game_mechanism_verified": False,
        },
    }


def build_report():
    evidence = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cases = [compare_case(x, provenance) for x, provenance in historical_cases(evidence)]
    return {
        "schema_version": 1, "classification": "RESEARCH_ONLY_NO_ENGINE_CHANGE",
        "report_id": "P0-NAVAL-SLOT-HP-FALSIFICATION-20261023",
        "original_fixture": "tests/fixtures/reverse_engineering/naval_air_counterparts_20261013.json",
        "summary": {
            "historically_analyzed_cases": len(cases),
            "independent_holdout_cases": 0,
            "controlled_aggregate_matches": sum(c["diagnostics"]["total_residual_model_minus_game"] == 0 for c in cases),
            "controlled_aggregate_mismatches": sum(c["diagnostics"]["total_residual_model_minus_game"] != 0 for c in cases),
            "cases_with_source_hp_bars": sum(c["observed"]["hp_bars_unmapped_percent"] is not None for c in cases),
        },
        "cases": cases,
        "warning": "All five cases are IN-SAMPLE. Simulator events, controlled formations and conditional bar arithmetic are not original Gameforge shot telemetry or independent validation.",
    }


def csv_rows(report):
    def encoded(x):
        return json.dumps(x, ensure_ascii=False, separators=(",", ":"))
    return [{
        "case_id": c["case_id"], "evaluation_split": c["evaluation_split"],
        "original_total": c["observed"]["total_deaths"],
        "model_total": c["model"]["total_deaths"],
        "aggregate": c["diagnostics"]["aggregate"],
        "original_slot_deaths": encoded(c["observed"]["per_slot_deaths"]),
        "model_slot_deaths": encoded([s["casualties"] for s in c["model"]["per_slot"]]),
        "original_bars": encoded(c["observed"]["hp_bars_unmapped_percent"]),
        "model_bars": encoded([s["modeled_hp_bar_percent"] for s in c["model"]["per_slot"]]),
        "unmapped_sorted_hp_residuals": encoded(c["diagnostics"]["hp_bar_residual_percent_points_sorted"]),
        "counterfactual": encoded(c["diagnostics"]["full_retention_arithmetic_counterfactual"]),
        "independent_holdout": c["independent_holdout"],
    } for c in report["cases"]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()
    report = build_report()
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    rows = csv_rows(report)
    with args.output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(report["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
