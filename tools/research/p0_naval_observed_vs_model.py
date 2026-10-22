"""Source-tagged P0 naval aggregate calibration matrix.

This is a RESEARCH REPORT, not a fitting, official Accuracy implementation,
or proof that invented First-line fillers were in an actual user's fleet.

For each already-in-sample casualty aggregate we compare a controlled
one-round engine outcome to the original source. Physical-slot HP and death
parity is deliberately NOT_ASSESSABLE when the actual battle report/slot
telemetry or UI bar semantics is missing.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from tools.research.naval_pvp_fast_carrier_probe import (
    FIXTURE as PVP_FIXTURE,
    control_case,
)
from tools.research.naval_ram_empirical_probe import (
    CASE as RAM_FIXTURE,
    model_one_controlled_round,
)

SOURCE_AGGREGATE = "SOURCE_REPORTED_AGGREGATE"
MODEL_SYNTHETIC = "SYNTHETIC_CONTROLLED_CURRENT_ENGINE"
MATCH_IN_SAMPLE = "aggregate_match_in_sample_only"
MISMATCH_CONTROLLED = "aggregate_mismatch_controlled_model"
NOT_ASSESSABLE = "not_assessable"
NO_INDEPENDENT_HOLDOUT = "not_assessable_no_independent_holdout"
SLOT_UNAVAILABLE = "not_assessable_original_slot_telemetry_unavailable"
BAR_UNAVAILABLE = "not_assessable_hp_bar_semantics_unverified"
ROUND_UNKNOWN = "not_assessable_original_round_not_confirmed"

NEXT_EVIDENCE = (
    "Original opposing full fleets, exact entry batches and source weapon upgrades",
    "Round-scoped original screenshots with numbered physical-slot deaths",
    "Original surviving slot HP bars and game version with UI rounding provenance",
    "Independent previously unseen battle with comparable Forge and upgrades",
)


def assess_aggregate(observed: int | None, predicted: int | None) -> str:
    """Never turn an unknown target or a matching fitted case into validation."""
    if observed is None or predicted is None:
        return NOT_ASSESSABLE
    if type(observed) is not int or type(predicted) is not int:
        raise ValueError("aggregate casualty counts must be integers or None")
    if observed < 0 or predicted < 0:
        raise ValueError("aggregate casualty counts must be nonnegative")
    return MATCH_IN_SAMPLE if observed == predicted else MISMATCH_CONTROLLED


def _record(
    *,
    case_id: str,
    source_class: str,
    observed_total: int,
    model_total: int | None,
    observed_round: int | None,
    model_round: int | None,
    simulated_slots: list[dict[str, Any]],
    observed_slot_provenance: str,
    observed_hp_bars: dict[str, int] | None = None,
) -> dict[str, Any]:
    # An actual slot address or bar must not silently come from model output:
    # the source for all six cases lacks independently checkable slot telemetry.
    return {
        "case_id": case_id,
        "observed": {
            "evidence_class": source_class,
            "casualties_total": observed_total,
            "reported_round": observed_round,
            "physical_slot_source_status": observed_slot_provenance,
            "reported_hp_bars_percent": observed_hp_bars,
        },
        "model": {
            "evidence_class": MODEL_SYNTHETIC,
            "casualties_total": model_total,
            "rounds_completed": model_round,
            "physical_slots_model_only": simulated_slots,
            "invented_first_line_fillers": True,
            "production_combat_algorithm_changed": False,
        },
        "assessment": {
            "aggregate": assess_aggregate(observed_total, model_total),
            "round": (
                ROUND_UNKNOWN if observed_round is None
                else (
                    "model_reached_reported_round"
                    if model_round == observed_round
                    else NOT_ASSESSABLE
                )
            ),
            "per_slot_deaths": SLOT_UNAVAILABLE,
            "hp_bar": BAR_UNAVAILABLE,
            "independent_holdout": NO_INDEPENDENT_HOLDOUT,
            "official_mechanic_validation": NOT_ASSESSABLE,
            "exact_original_fleet_reconstruction": False,
        },
        "next_required_evidence": list(NEXT_EVIDENCE),
    }


def build_report() -> dict[str, Any]:
    pvp = json.loads(PVP_FIXTURE.read_text(encoding="utf-8"))
    ram = json.loads(RAM_FIXTURE.read_text(encoding="utf-8"))
    cases = []

    # These three observed PvP cases were owner-confirmed as ROUND ONE and
    # BOTH players Forge5. The 35 Steam Ram fillers are model-only.
    for item in pvp["observed"]:
        if not (item["both_forge5_confirmed_by_user"]
                and item["round_one_confirmed_by_user"]
                and item["attacker_forge_level"] == 5
                and item["defender_forge_level"] == 5):
            raise ValueError("PvP Forge/round provenance changed: stop instead of guessing")
        prediction = control_case(
            item,
            attacker_forge=item["attacker_forge_level"],
            defender_forge=item["defender_forge_level"],
        )
        slots = sorted(
            prediction["model_carrier_slots"],
            key=lambda x: x["damage_position"],
        )
        cases.append(_record(
            case_id=item["case"],
            source_class=pvp["evidence_class"],
            observed_total=item["reported_carrier_total_deaths"],
            model_total=prediction["model_total_carrier_deaths"],
            observed_round=item["observed_round_number"],
            model_round=prediction["model_rounds_completed"],
            simulated_slots=slots,
            observed_slot_provenance="unreported_for_this_game_case",
        ))

    observed = ram["observed"]
    series = observed["player_deaths_total_by_defense_upgrade"]
    if not (ram["source"]["actual_series_range"] == "F4:F19"
            and observed["player_forge_level"] == 5
            and observed["barbarian_forge_level"] == 0):
        raise ValueError("Ram workbook provenance or forge scope changed")
    chat = observed["direct_conversation_case"]
    if chat["player_defense_upgrade"] != 19 or chat["player_attack_upgrade"] != 20:
        raise ValueError("Ram chat DEF19/ATT20 observation changed")

    for defense in (14, 15, 19):
        predicted = model_one_controlled_round(
            defense, attack_upgrade=20, fill_front=True,
        )
        if defense == 19:
            source_class = chat["source"]
            death_total = chat["player_total_deaths"]
            bars = {
                "player_remaining": chat["player_remaining_hp_bar_percent"],
                "barbarian_remaining": chat["barbarian_remaining_hp_bar_percent"],
            }
            slot_provenance = "user_chat_not_independently_slot_telemetry_verified"
        else:
            source_class = "USER_WORKBOOK_F4_F19_AGGREGATE_ONLY"
            death_total = series[str(defense)]
            bars = None
            slot_provenance = (
                "separate_user_chat_per_slot_claim_no_original_screenshot"
            )
        slots = sorted(
            predicted["round1_unit_slots_all_lines"]["defender"],
            key=lambda x: (x["line"], x["damage_position"]),
        )
        cases.append(_record(
            case_id=f"ram_defense_{defense}_attack_20_forge5",
            source_class=source_class,
            observed_total=death_total,
            model_total=predicted.get("defender_player_deaths"),
            observed_round=None,  # Workbook did not certify Round 1.
            model_round=predicted.get("rounds_completed"),
            simulated_slots=slots,
            observed_slot_provenance=slot_provenance,
            observed_hp_bars=bars,
        ))

    summary = {
        "total_cases": len(cases),
        "aggregate_in_sample_matches": sum(
            c["assessment"]["aggregate"] == MATCH_IN_SAMPLE for c in cases
        ),
        "aggregate_controlled_mismatches": sum(
            c["assessment"]["aggregate"] == MISMATCH_CONTROLLED for c in cases
        ),
        "independently_held_out_cases": 0,
        "per_slot_game_telemetry_assessable_cases": 0,
        "game_hp_bar_parity_assessable_cases": 0,
    }
    return {
        "schema_version": 1,
        "report_id": "P0-NAVAL-OBSERVED-MODEL-EVIDENCE-GAP-20261023",
        "classification": "RESEARCH_ONLY_NO_PRODUCTION_ALGORITHM_CHANGE",
        "fixture_sources": [
            "tests/fixtures/reverse_engineering/naval_pvp_fast_boat_carrier_20261013.json",
            "tests/fixtures/reverse_engineering/naval_ram_deckwrecker_20261013.json",
        ],
        "summary": summary,
        "cases": cases,
        "warning": (
            "The matched aggregates are IN-SAMPLE, under invented frontline "
            "controls, and do not validate actual Gameforge shot allocation, "
            "Accuracy, per-slot kills, UI HP percentages or later rounds."
        ),
    }


def csv_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [{
        "case_id": c["case_id"],
        "source_class": c["observed"]["evidence_class"],
        "observed_total": c["observed"]["casualties_total"],
        "model_total": c["model"]["casualties_total"],
        "aggregate_status": c["assessment"]["aggregate"],
        "round_status": c["assessment"]["round"],
        "physical_slot_status": c["assessment"]["per_slot_deaths"],
        "hp_bar_status": c["assessment"]["hp_bar"],
        "holdout_status": c["assessment"]["independent_holdout"],
        "invented_first_line_fillers": c["model"]["invented_first_line_fillers"],
    } for c in report["cases"]]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", required=True, type=Path)
    ap.add_argument("--output-csv", required=True, type=Path)
    options = ap.parse_args()
    report = build_report()
    options.output_json.parent.mkdir(parents=True, exist_ok=True)
    options.output_csv.parent.mkdir(parents=True, exist_ok=True)
    options.output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    rows = csv_rows(report)
    with options.output_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
    print(f"Reports: {options.output_json}; {options.output_csv}")


if __name__ == "__main__":
    main()
