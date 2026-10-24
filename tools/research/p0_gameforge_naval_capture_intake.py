"""Prospective real-game R1/R2 naval HP capture intake; NOT official mechanic proof.

Accept user-transcribed screenshot metadata ONLY. The comparator is a
conditional what-if against previous SYNTHETIC Tender=1 hypotheses; never
promote observations to verified official rules or treat the original owner
53%/65% Carrier bars as this synthetic fleet. No production engine mutation.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path

from tools.research import p0_naval_hp_bar_capture_discrimination as model
from tools.research.p0_live_round2_prefire_postfire_ledger import scenario

SCHEMA = "p0_gameforge_naval_r1_r2_capture_intake_v1"
USER_TRANSCRIPTION = "user_transcribed_unverified"
TEMPLATE = "template_no_game_observation"
ROUNDS = ("floor", "nearest_half_up", "ceil")
ROUND_UNKNOWN = "unknown"
MAPPED = "assumed_model_slot_address"
UNMAPPED = "unmapped_per_wave"
EQUIVALENCE_ASSERTED = "asserted_by_submitter_unverified"
EQUIVALENCE_UNKNOWN = "unverified"
PROVENANCE = "USER_TRANSCRIPTION_UNVERIFIED_NEVER_OFFICIAL_RULE_VALIDATION"
CONDITIONAL = "CONDITIONAL_MODEL_SCREENING_NOT_GAMEFORGE_MECHANIC_VALIDATION"

TOP_KEYS = frozenset({
    "schema", "record_kind", "evidence_id", "source_refs", "context",
    "mapping_mode", "percent_rounding", "model_fleet_equivalence",
    "r2_prefire_bars",
})
REF_KEYS = frozenset({"round1_end", "round2_prefire", "fleet_setup"})
CONTEXT_KEYS = frozenset({
    "battlefield_id", "tender_count", "attacker_forge_level", "defender_forge_level",
    "attacker_units", "defender_units", "ram_ship_attack_upgrade",
    "ram_ship_armor_upgrade", "steam_ram_attack_upgrade",
    "steam_ram_armor_upgrade", "workshop_details_captured",
    "reinforcements_between_snapshots", "r2_snapshot_is_prefire",
})
OBS_KEYS = frozenset({
    "unit_id", "wave_id", "model_damage_position", "visible_percent",
    "units_alive", "source_ref",
})
NAVAL_FIELDS = frozenset({
    "naval-mini", "naval-small", "naval-medium", "naval-large", "naval-max",
})


def template() -> dict:
    """Blank worksheet, NEVER a fabricated game measurement."""
    return {
        "schema": SCHEMA,
        "record_kind": TEMPLATE,
        "evidence_id": "",
        "source_refs": {"round1_end": "", "round2_prefire": "", "fleet_setup": ""},
        "context": {
            "battlefield_id": None, "tender_count": None,
            "attacker_forge_level": None, "defender_forge_level": None,
            "attacker_units": {}, "defender_units": {},
            "ram_ship_attack_upgrade": None, "ram_ship_armor_upgrade": None,
            "steam_ram_attack_upgrade": None, "steam_ram_armor_upgrade": None,
            "workshop_details_captured": None,
            "reinforcements_between_snapshots": "unknown",
            "r2_snapshot_is_prefire": None,
        },
        "mapping_mode": UNMAPPED,
        "percent_rounding": ROUND_UNKNOWN,
        "model_fleet_equivalence": EQUIVALENCE_UNKNOWN,
        "r2_prefire_bars": [],
    }


def _nonblank(v) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _bad_keys(value, expected: frozenset, name: str, errors: list):
    if not isinstance(value, dict):
        errors.append(f"{name} must be an object")
        return False
    unexpected = sorted(set(value) - expected)
    if unexpected:
        errors.append(f"{name} unknown or forbidden fields: {unexpected}")
    return not unexpected


def _expected_control_setup() -> dict:
    """Read true original synthetic R1 configuration; never invent a proxy."""
    setup = scenario("naval_tender", 0)
    defender = setup["defender"]
    ram = next(x for x in defender["units"] if x["unit_id"] == "ram_ship")
    steam = next(x for x in defender["units"] if x["unit_id"] == "steam_ram")
    return {
        "battlefield_id": setup["battlefield"],
        "tender_count": 1,
        "attacker_forge_level": setup["attacker"]["forge_level"],
        "defender_forge_level": defender["forge_level"],
        "attacker_units": {
            unit["unit_id"]: unit["quantity"]
            for unit in setup["attacker"]["units"]
        },
        "defender_units": {
            **{unit["unit_id"]: unit["quantity"] for unit in defender["units"]},
            "tender": 1,
        },
        "ram_ship_attack_upgrade": ram["attack_upgrade"],
        "ram_ship_armor_upgrade": ram["armor_upgrade"],
        # Absent upgrade keys in the actual control are normalized defaults 0.
        # Compare both values explicitly; a captured=true boolean is not enough.
        "steam_ram_attack_upgrade": steam.get("attack_upgrade", 0),
        "steam_ram_armor_upgrade": steam.get("armor_upgrade", 0),
    }


def _model_plan() -> tuple[dict, dict]:
    plan = model.build_report()
    if (plan["provenance"] != model.PROVENANCE
            or plan["summary"]["new_game_observations"] != 0
            or plan["summary"]["independent_holdouts"] != 0
            or plan["source"]["game_to_model_slot_mapping_verified"] is not False
            or plan["source"]["game_rounding_verified"] is not False):
        raise AssertionError("source model suddenly claims unsupported Gameforge verification")
    channels = {x["channel_id"]: x for x in plan["channels"]}
    if len(channels) != len(plan["channels"]):
        raise AssertionError("duplicate prediction channel ID")
    return plan, channels


def _valid_observations(raw: list, mode: str, channels: dict,
                        refs: dict, errors: list) -> list:
    known = {(x["unit_id"], x["wave_id"], x["damage_position"]): cid
             for cid, x in channels.items()}
    allowed_waves = {(x["unit_id"], x["wave_id"]) for x in channels.values()}
    results = []
    mapped_seen = set()
    wave_count = defaultdict(int)
    max_wave_count = defaultdict(int)
    for ch in channels.values():
        max_wave_count[ch["unit_id"], ch["wave_id"]] += 1
    for index, row in enumerate(raw):
        mark = f"r2_prefire_bars[{index}]"
        if not _bad_keys(row, OBS_KEYS, mark, errors):
            continue
        uid, wave = row.get("unit_id"), row.get("wave_id")
        percent, position = row.get("visible_percent"), row.get("model_damage_position")
        key = uid, wave
        if not _nonblank(uid) or not _nonblank(wave):
            errors.append(f"{mark} requires explicit unit_id and model Wave ID as a comparison assumption")
            continue
        if key not in allowed_waves:
            errors.append(f"{mark} does not correspond to the synthetic comparison fleet")
            continue
        if type(percent) is not int or not 0 <= percent <= 100:
            errors.append(f"{mark} displayed percent must be an integer 0..100")
            continue
        evidence_ref = row.get("source_ref")
        if not _nonblank(evidence_ref) or evidence_ref != refs.get("round2_prefire"):
            errors.append(f"{mark} must link to the recorded R2 prefire screenshot reference")
            continue
        alive = row.get("units_alive")
        if alive is not None and (type(alive) is not int or alive <= 0):
            errors.append(f"{mark} units_alive must be a positive integer or null")
            continue
        if mode == MAPPED:
            if type(position) is not int or position <= 0:
                errors.append(f"{mark} requires positive assumed model_damage_position")
                continue
            mapped = known.get((uid, wave, position))
            if mapped is None:
                errors.append(f"{mark} mapped Slot absent from synthetic model")
                continue
            if mapped in mapped_seen:
                errors.append(f"{mark} duplicate observed mapped Slot")
                continue
            expected_units = channels[mapped]["simulated_slot_population"]
            if alive is not None and alive != expected_units:
                errors.append(f"{mark} different Slot survivor population: fleet not comparable")
                continue
            mapped_seen.add(mapped)
        else:
            if position is not None:
                errors.append(f"{mark} unmapped observations must NOT invent a model Slot address")
                continue
            wave_count[key] += 1
            if wave_count[key] > max_wave_count[key]:
                errors.append(f"{mark} more recorded bars than modeled live Slots for Wave")
                continue
        results.append({
            "unit_id": uid, "wave_id": wave, "visible_percent": percent,
            "channel_id": mapped if mode == MAPPED else None,
            "units_alive": alive,
        })
    return results


def _unmapped_wave_assignment(observed: list[dict], candidate_ids: list[str],
                              channels: dict, predictions: dict | None = None,
                              rounding: str | None = None) -> bool:
    """Injectively match recorded bars to any *distinct* model Slot in Wave.

    When predictions is None, only test population compatibility. This
    prevents a forged 999-unit bar from being interpreted as a model percent
    mismatch, while keeping genuine percent-only hypothesis disagreement
    conditional rather than misclassifying it as a bad screenshot.
    """
    if predictions is not None and rounding not in ROUNDS:
        raise ValueError("missing globally shared candidate rounding mode")
    states = {0}
    for observed_bar in observed:
        next_states = set()
        for used in states:
            for index, cid in enumerate(candidate_ids):
                if used & (1 << index):
                    continue
                required_population = observed_bar["units_alive"]
                if (required_population is not None and
                        channels[cid]["simulated_slot_population"] != required_population):
                    continue
                if (predictions is not None and
                        predictions[cid][rounding] != observed_bar["visible_percent"]):
                    continue
                next_states.add(used | (1 << index))
        if not next_states:
            return False
        states = next_states
    return True


def _unmapped_groups(observations: list[dict], channels: dict) -> tuple[dict, dict]:
    observed_by_wave = defaultdict(list)
    model_by_wave = defaultdict(list)
    for row in observations:
        observed_by_wave[row["unit_id"], row["wave_id"]].append(row)
    for cid, channel in channels.items():
        model_by_wave[channel["unit_id"], channel["wave_id"]].append(cid)
    return observed_by_wave, model_by_wave


def _matches_case(plan: dict, observations: list, case_id: str,
                  modes: tuple[str, ...], mapping_mode: str, channels: dict) -> bool:
    predicted = plan["predicted_integer_percent_bars"][case_id]
    if mapping_mode == MAPPED:
        return any(all(predicted[row["channel_id"]][rounding] == row["visible_percent"]
                       for row in observations) for rounding in modes)

    observed_by_wave, model_by_wave = _unmapped_groups(observations, channels)
    # A single rounding mode is used across *all* Waves and all observed
    # Slot percentages. Partial per-Wave screenshots can map to any distinct
    # subset, but must preserve each supplied survivor population.
    return any(
        all(_unmapped_wave_assignment(rows, model_by_wave[wave], channels,
                                      predicted, rounding)
            for wave, rows in observed_by_wave.items())
        for rounding in modes
    )

def evaluate_capture(record: dict, plan: dict | None = None) -> dict:
    """Never return an official game-mechanic conclusion, even for matches."""
    errors: list[str] = []
    if not isinstance(record, dict):
        raise ValueError("intake must be a JSON object")
    if not _bad_keys(record, TOP_KEYS, "record", errors):
        return _out("INVALID", errors, [], None)
    if record.get("schema") != SCHEMA:
        errors.append("wrong intake schema")
    kind = record.get("record_kind")
    if kind not in (TEMPLATE, USER_TRANSCRIPTION):
        errors.append("record_kind must explicitly classify user transcription vs template")
    if kind == TEMPLATE:
        if record == template():
            return _out("TEMPLATE_ONLY", [], [], None)
        errors.append("template may not contain purported Gameforge observations")
    if not _nonblank(record.get("evidence_id")):
        errors.append("nonblank evidence_id required")
    refs = record.get("source_refs")
    if _bad_keys(refs, REF_KEYS, "source_refs", errors):
        for key in REF_KEYS:
            if not _nonblank(refs.get(key)):
                errors.append(f"source_refs.{key} is required")
        if all(_nonblank(refs.get(key)) for key in REF_KEYS) and len(set(refs.values())) != 3:
            errors.append("different battle stages must have distinguishable evidence references")
    else:
        refs = {}
    context = record.get("context")
    if _bad_keys(context, CONTEXT_KEYS, "context", errors):
        # The previous research had a SPECIFIC artificial battle, NOT just
        # an interchangeable naval fleet with one support vessel. Reject
        # different configurations rather than telling owners their real
        # battle falsifies the original synthetic hypotheses.
        expected = _expected_control_setup()
        for key, expected_value in expected.items():
            value = context.get(key)
            if type(value) is not type(expected_value) or value != expected_value:
                errors.append(f"context.{key} differs from synthetic source setup; no direct model screen")
        if context.get("workshop_details_captured") is not True:
            errors.append("workshop details must be documented before model screening")
        if context.get("reinforcements_between_snapshots") != "none":
            errors.append("must rule out reinforcements between R1 and R2 snapshots")
        if context.get("r2_snapshot_is_prefire") is not True:
            errors.append("R2 screenshot must be confirmed before shots")
    mode = record.get("mapping_mode")
    if mode not in (MAPPED, UNMAPPED):
        errors.append("mapping_mode must be mapped-hypothesis or unmapped Wave bars")
    rounding = record.get("percent_rounding")
    if rounding not in (*ROUNDS, ROUND_UNKNOWN):
        errors.append("percent_rounding must be unknown or an explicit candidate mode")
    if record.get("model_fleet_equivalence") != EQUIVALENCE_ASSERTED:
        errors.append("model fleet equivalence to synthetic case remains unasserted; no model screen")
    observations = record.get("r2_prefire_bars")
    if not isinstance(observations, list) or not observations:
        errors.append("at least one actual R2 prefire integer-percent bar needed")
        observations = []
    if plan is None:
        plan, channels = _model_plan()
    else:
        # All caller-supplied plans must be tied to the canonical synthetic
        # comparator; no fake observations or official rules in source.
        canonical, channels = _model_plan()
        if plan != canonical:
            raise ValueError("supplied comparator differs from current classified synthetic source")
    if mode in (MAPPED, UNMAPPED) and isinstance(record.get("r2_prefire_bars"), list):
        parsed = _valid_observations(observations, mode, channels, refs, errors)
    else:
        parsed = []
    if mode == UNMAPPED and parsed:
        groups, model_groups = _unmapped_groups(parsed, channels)
        for wave, rows in groups.items():
            if not _unmapped_wave_assignment(rows, model_groups[wave], channels):
                errors.append(
                    f"unmapped Wave {wave}: no injective model Slot assignment "
                    "compatible with supplied living-unit counts"
                )
    if errors:
        return _out("NOT_COMPARABLE", errors, parsed, None)
    modes = ROUNDS if rounding == ROUND_UNKNOWN else (rounding,)
    compatible = [
        cid for cid in plan["case_order"]
        if _matches_case(plan, parsed, cid, modes, mode, channels)
    ]
    eliminated = [cid for cid in plan["case_order"] if cid not in compatible]
    return _out("CONDITIONAL_SCREEN_ONLY", [], parsed, {
        "model_source_case": plan["source"]["case_id"],
        "rounding_candidates": list(modes),
        "mapping_assumption": mode,
        "model_hypotheses_consistent_with_supplied_bars": compatible,
        "model_hypotheses_inconsistent_if_all_model_assumptions_hold": eliminated,
        "hypothesis_count_total": len(plan["case_order"]),
        "all_inconsistent": not bool(compatible),
        "interpretation": CONDITIONAL,
    })


def _out(status: str, errors: list, observations: list, comparison: dict | None) -> dict:
    return {
        "schema": "p0_gameforge_naval_capture_intake_result_v1",
        "status": status, "source_provenance": PROVENANCE,
        "original_game_observations_independently_verified": 0,
        "independent_holdouts": 0,
        "official_game_mechanism_verified": False,
        "input_requirements_missing_or_invalid": errors,
        "parsed_r2_prefire_bar_count": len(observations),
        "conditional_model_comparison": comparison,
        "limitations": [
            "Source references are user-supplied strings, NOT verified image files or independently confirmed real Gameforge events.",
            "Even a matching manually reported synthetic fleet/upgrade setup does NOT verify actual screenshot contents, Wave mapping or game equivalence.",
            "Per-Wave mapping, percent denominator and model-to-game Slot addresses remain unverified assumptions.",
            "A model bar match is NOT evidence of actual Gameforge healing allocation, RR timing, or combat targeting.",
            "Past 53%/65% Carrier sample is unrelated to this synthetic Tender=1 scenario.",
        ],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--write-template", type=Path)
    group.add_argument("--input", type=Path)
    ap.add_argument("--output-json", type=Path)
    args = ap.parse_args()
    if args.write_template is not None:
        if args.output_json is not None:
            ap.error("--output-json may only accompany --input")
        out, destination = template(), args.write_template
    else:
        if args.output_json is None:
            ap.error("--input needs --output-json")
        out = evaluate_capture(json.loads(args.input.read_text(encoding="utf-8")))
        destination = args.output_json
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(json.dumps({
        "status": "template" if args.write_template is not None else out["status"],
        "output": str(destination),
    }, ensure_ascii=False))
    if args.input is not None and out["status"] in ("NOT_COMPARABLE", "INVALID"):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
