"""Which model-predicted naval HP bars would separate current research hypotheses?

Research-only prospective capture plan from the existing synthetic Tender=1
PR #85 mathematical counterfactuals, NOT a new battle, measurement or
Gameforge display formula. Includes uncertainty in rounding and source-to-slot
mapping. NEVER folds in the unrelated historical 53/65% carrier-bar report.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from itertools import combinations
from pathlib import Path
import csv
import json

from ikariam_battle.units import UnitRegistry
from tools.research import p0_tender_healing_rr_order_uncertainty as previous
from tools.research.p0_naval_hp_bar_inverse_bounds import (
    ROUNDING_MODES, display_percent,
)

PROVENANCE = "PROSPECTIVE_SYNTHETIC_NAVAL_BAR_DISCRIMINATION_NOT_GAME_OBSERVATION"
UNKNOWN_ROUNDING = "unknown_same_rounding_mode_across_visible_slots"
NO_SLOT_MAPPING = "unmapped_per_wave_visible_slot_multiset"
SLOT_MAPPING = "addressed_model_slot_positions_unverified_game_mapping"


def _nonnegative(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} is not a nonnegative integer")
    return value


def _channel_id(uid: str, wave_id: str, position: int) -> str:
    if not uid or not wave_id or type(position) is not int or position <= 0:
        raise ValueError("invalid observed Slot identity")
    # JSON-encoded tuple is unambiguous even if wave labels have delimiters.
    return json.dumps([uid, wave_id, position], separators=(",", ":"))


def extract_predictions(report: dict) -> tuple[list[str], dict[str, dict], dict[str, dict]]:
    """Validate report provenance and all common population/HP denominators."""
    if (report.get("classification") != previous.PROVENANCE
            or report.get("summary", {}).get("novel_game_observations") != 0
            or report.get("summary", {}).get("independent_holdouts") != 0
            or report.get("summary", {}).get("game_mechanic_verified") is not False
            or report.get("source", {}).get("unknown_original_game_rule")
            != previous.prior.PENDING):
        raise AssertionError("source is not the classified unverified PR #85 model")
    cases = report["cases"]
    expected_count = 1 + len(previous.PRIORITIES) * len(previous.ORDERS)
    if len(cases) != expected_count:
        raise AssertionError("model case set changed")
    registry = UnitRegistry.load(include_barbarians=True)
    frames = {}
    common = None
    for case in cases:
        case_id = case["case_id"]
        if (not isinstance(case_id, str) or not case_id
                or case_id in frames
                or case.get("game_mechanic_verified") is not False
                or case.get("actual_changed_R2_combat_executed") is not False):
            raise AssertionError("duplicate identity or forged case verification")
        frame = {}
        populations = {}
        seen_waves = set()
        for wave in case["wave_hp"]:
            wkey = (wave["unit_id"], wave["wave_id"])
            if wkey in seen_waves:
                raise AssertionError("duplicate Wave projected")
            seen_waves.add(wkey)
            hp = registry.get(wkey[0]).hit_points
            if type(hp) is not int or hp <= 0:
                raise AssertionError("unknown positive unit HP denominator")
            original = _nonnegative(wave["original_wounds_r1"], "original wound")
            remaining = _nonnegative(wave["hypothetical_remaining_wounds"], "remaining wound")
            healed = _nonnegative(wave["hypothetical_healed_hp"], "heal")
            if original != remaining + healed:
                raise AssertionError("Wave healed HP not conserved")
            reserve_wounds = _nonnegative(wave["reserve_wounds"], "reserve wound")
            reserve = _nonnegative(wave["reserve"], "reserve units")
            if reserve_wounds >= max(1, reserve * hp):
                raise AssertionError("Reserve surviving HP invalid")
            if reserve == 0 and reserve_wounds:
                raise AssertionError("empty Reserve has wounded units")
            summed = reserve_wounds
            living = reserve
            for slot in wave["slots"]:
                units = _nonnegative(slot["units"], "slot units")
                position = slot["damage_position"]
                if type(position) is not int or position <= 0:
                    raise AssertionError("invalid physical slot address")
                cid = _channel_id(wkey[0], wkey[1], position)
                if cid in frame:
                    raise AssertionError("duplicate physical Slot in projected Wave")
                if (not isinstance(slot["slot_id"], str)
                        or not slot["slot_id"]):
                    raise AssertionError("missing Slot evidence label")
                wounds = _nonnegative(slot["remaining_wounds"], "slot wound")
                if units and wounds >= units * hp:
                    raise AssertionError("nonliving hypothetical wounded Slot")
                if not units and wounds:
                    raise AssertionError("wounds in zero-population physical Slot")
                summed += wounds
                living += units
                # A zero-person slot has no survivor HP bar to measure. Keep
                # its stable geometry in the audit but NOT capture plan.
                if units:
                    full_hp = units * hp
                    frame[cid] = {
                        "unit_id": wkey[0], "wave_id": wkey[1],
                        "damage_position": position, "slot_id": slot["slot_id"],
                        "units": units, "full_hp": full_hp,
                        "wounds": wounds,
                        "rounding_predictions": {
                            mode: display_percent(full_hp - wounds, full_hp, mode)
                            for mode in ROUNDING_MODES
                        },
                    }
                    populations[cid] = (slot["slot_id"], units, full_hp)
            if summed != remaining or living != wave["alive"]:
                raise AssertionError("case Wave HP or surviving population drift")
        if not frame:
            raise AssertionError("no visible model Slot HP to discriminate")
        if common is None:
            common = populations
        elif populations != common:
            raise AssertionError("hypotheses have incompatible physical Slot topology")
        frames[case_id] = frame
    ids = sorted(common)
    return ids, frames, {
        cid: {
            "channel_id": cid, "unit_id": frames[cases[0]["case_id"]][cid]["unit_id"],
            "wave_id": frames[cases[0]["case_id"]][cid]["wave_id"],
            "damage_position": frames[cases[0]["case_id"]][cid]["damage_position"],
            "slot_id": frames[cases[0]["case_id"]][cid]["slot_id"],
            "simulated_slot_population": frames[cases[0]["case_id"]][cid]["units"],
            "model_hp_denominator": frames[cases[0]["case_id"]][cid]["full_hp"],
            "game_slot_address_verified": False,
        } for cid in ids
    }


def _signature(frame: dict, chosen: list[str], rounding: str) -> tuple:
    if rounding not in ROUNDING_MODES:
        raise ValueError("not a known rounding rule")
    return tuple(frame[cid]["rounding_predictions"][rounding] for cid in chosen)


def _possible_signatures(frame: dict, chosen: list[str], rounding: str) -> set[tuple]:
    if rounding == UNKNOWN_ROUNDING:
        return {_signature(frame, chosen, m) for m in ROUNDING_MODES}
    return {_signature(frame, chosen, rounding)}


def distinguished_pairs(case_ids: list[str], frames: dict,
                        chosen: list[str], rounding: str,
                        *, unmapped: bool = False) -> set[tuple[str, str]]:
    """Pair is separable only if allowed integer bar patterns never overlap."""
    if rounding not in ROUNDING_MODES and rounding != UNKNOWN_ROUNDING:
        raise ValueError("unknown game display assumption")
    if len(chosen) != len(set(chosen)):
        raise ValueError("duplicate channels in an observation request")
    for cid in chosen:
        if any(cid not in frames[case_id] for case_id in case_ids):
            raise ValueError("requested unknown model Slot")
    if unmapped:
        # Missing physical slot mapping: only the per-Wave unordered multiset
        # of visible bars remains. This applies to the entire selected
        # collection (never smuggle game target-address identity back in).
        wave_groups = defaultdict(list)
        for cid in chosen:
            first = frames[case_ids[0]][cid]
            wave_groups[(first["unit_id"], first["wave_id"])].append(cid)
        def possibilities(case_id):
            f = frames[case_id]
            return {
                tuple((
                    key, tuple(sorted(f[cid]["rounding_predictions"][mode]
                                      for cid in wave_groups[key]))
                ) for key in sorted(wave_groups))
                for mode in ((rounding,) if rounding != UNKNOWN_ROUNDING
                             else ROUNDING_MODES)
            }
    else:
        def possibilities(case_id):
            return _possible_signatures(frames[case_id], chosen, rounding)
    signature_by_case = {case_id: possibilities(case_id) for case_id in case_ids}
    return {
        (a, b) for a, b in combinations(case_ids, 2)
        if signature_by_case[a].isdisjoint(signature_by_case[b])
    }


def capture_plan(case_ids: list[str], frames: dict,
                 channels: list[str], rounding: str) -> dict:
    """Deterministic greedy plan, explicitly NOT a proven minimum set."""
    full_pairs = distinguished_pairs(case_ids, frames, channels, rounding)
    unresolved = set(full_pairs)
    candidates = list(channels)
    chosen = []
    steps = []
    while unresolved and candidates:
        scored = []
        for cid in candidates:
            now = distinguished_pairs(case_ids, frames, chosen + [cid], rounding)
            gain = len(now & unresolved)
            scored.append((gain, cid))
        # A joint multi-Slot pattern can eliminate ambiguity even when no
        # single new Slot gains separation. Keep adding until full available
        # discriminability is reached rather than falsely stopping at 0 gain.
        gain, cid = sorted(scored, key=lambda x: (-x[0], x[1]))[0]
        chosen.append(cid)
        candidates.remove(cid)
        achieved = distinguished_pairs(case_ids, frames, chosen, rounding)
        unresolved -= achieved
        steps.append({
            "capture_channel_id": cid,
            "newly_distinguishable_pairs": gain,
            "cumulative_distinguishable_pairs": len(achieved),
            "target_distinguishable_pairs_with_all_slots": len(full_pairs),
        })
    if unresolved:
        raise AssertionError("greedy capture plan failed to reach full-Slot coverage")
    return {
        "heuristic": "sequential_greedy_not_minimal_set_cover",
        "recommended_order": chosen,
        "steps": steps,
        "full_slot_distinguishable_pairs": len(full_pairs),
        "fully_ambiguous_pairs": len(case_ids) * (len(case_ids) - 1) // 2 - len(full_pairs),
    }


def build_report(source_report: dict | None = None) -> dict:
    original = previous.build_report() if source_report is None else source_report
    channels, frames, channel_details = extract_predictions(original)
    ids = list(frames)
    cases = []
    for rounding in (*ROUNDING_MODES, UNKNOWN_ROUNDING):
        pairwise = distinguished_pairs(ids, frames, channels, rounding)
        without_addresses = distinguished_pairs(
            ids, frames, channels, rounding, unmapped=True
        )
        if not without_addresses.issubset(pairwise):
            raise AssertionError("missing physical address information increased identifiability")
        cases.append({
            "assumed_game_bar_rounding": rounding,
            "status": "conditional_unverified_display_semantics",
            "addressed_all_slot_distinguishable_pairs": len(pairwise),
            "without_game_slot_mapping_distinguishable_pairs": len(without_addresses),
            "address_mapping_only_distinguishable_pairs": len(pairwise - without_addresses),
            "ambiguous_pairs_even_with_all_slot_bars": [
                [a, b] for a, b in combinations(ids, 2)
                if (a, b) not in pairwise
            ],
            "pairs_lost_without_slot_mapping": [
                [a, b] for a, b in sorted(pairwise - without_addresses)
            ],
            "capture_plan": capture_plan(ids, frames, channels, rounding),
        })
    # Keep model predictions to make the capture guidance falsifiable and
    # reproducible, not merely opaque scores. No Gameforge rounding assumed.
    return {
        "schema": "p0_naval_hypothesis_hp_bar_identifiability_v1",
        "provenance": PROVENANCE,
        "source": {
            "model": "p0_tender_healing_RR_localization_counterfactual_v1",
            "case_id": original["source"]["case_id"],
            "source_game_observations": 0,
            "source_independent_holdouts": 0,
            "game_rounding_verified": False,
            "game_to_model_slot_mapping_verified": False,
            "true_healing_recipient_or_rr_order_verified": False,
        },
        "summary": {
            "source_model_comparisons": len(ids),
            "physical_simulated_slot_channels": len(channels),
            "candidate_rounding_interpretations": len(cases),
            "new_game_observations": 0,
            "independent_holdouts": 0,
            "game_mechanic_verified": False,
        },
        "channels": [channel_details[x] for x in channels],
        "case_order": ids,
        "predicted_integer_percent_bars": {
            case_id: {
                cid: frames[case_id][cid]["rounding_predictions"]
                for cid in channels
            } for case_id in ids
        },
        "rounding_analyses": cases,
        "requirements_for_real_holdout": [
            "Obtain fresh, independent actual Gameforge Round1-end and Round2 pre-volley screenshots of one known Tender fight.",
            "Record exact unit type, living counts, numbered physical Slot positions, upgrades, Forge and support count.",
            "Identify whether observed percentages use floor, nearest or ceil, and if the game bar denominator is actually per-survivor Slot HP.",
            "Do NOT infer any official mechanic if observed Slot ownership, denominator, healing amount or rounding is unknown.",
            "Only model physical Slots appear in this prospective screenshot plan; Reserve wound HP may be unavailable in game UI.",
            "Previously owner-reported 53%/65% Carrier bars were a different unmapped in-sample case and are not evaluated against this Tender scenario.",
        ],
    }


def csv_rows(data: dict) -> list[dict]:
    rows = []
    for analysis in data["rounding_analyses"]:
        for step in analysis["capture_plan"]["steps"]:
            cid = step["capture_channel_id"]
            ch = next(x for x in data["channels"] if x["channel_id"] == cid)
            rows.append({
                "source_case_id": data["source"]["case_id"],
                "rounding_assumption": analysis["assumed_game_bar_rounding"],
                "capture_order": 0,  # assigned sequentially from ordered steps below
                "channel_id": cid, "unit_id": ch["unit_id"], "wave_id": ch["wave_id"],
                "damage_position": ch["damage_position"],
                "slot_id": ch["slot_id"],
                "simulated_slot_population": ch["simulated_slot_population"],
                "new_pairs_distinguished": step["newly_distinguishable_pairs"],
                "cumulative_pairs_distinguished": step["cumulative_distinguishable_pairs"],
                "full_slot_pairs_distinguished": analysis["addressed_all_slot_distinguishable_pairs"],
                "game_rounding_verified": False,
                "game_slot_mapping_verified": False,
                "new_game_observations": 0,
                "independent_holdouts": 0,
                "provenance": PROVENANCE,
            })
        # The sequential number is an observation order, NOT a label order.
        current = [x for x in rows if x["rounding_assumption"] == analysis["assumed_game_bar_rounding"]]
        for number, row in enumerate(current, start=1):
            row["capture_order"] = number
    if len({(r["rounding_assumption"], r["channel_id"]) for r in rows}) != len(rows):
        raise AssertionError("capture guidance contains repeated measurement")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()
    data = build_report()
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    rows = csv_rows(data)
    with args.output_csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(data["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
