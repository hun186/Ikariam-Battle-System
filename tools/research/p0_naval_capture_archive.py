"""Archive user-transcribed naval R1/R2 evidence *without* synthetic-fleet gating.

Research-only. Accept incomplete or different-fleet records as *unverified*
source material; never authenticate source references or infer an official
Gameforge rule. Does not perform PR #87's narrow HP model comparison.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path

from tools.research.p0_gameforge_naval_capture_intake import (
    NAVAL_FIELDS, _expected_control_setup,
)

SCHEMA = "p0_naval_capture_archive_v1"
TEMPLATE = "empty_template_not_an_observation"
TRANSCRIPTION = "user_transcribed_unverified"
SOURCE_CLASS = "USER_SUBMITTED_NOT_INDEPENDENTLY_AUTHENTICATED"
PHASES = frozenset(("r1_end", "r2_prefire"))
SIDES = frozenset(("attacker", "defender"))
EXPECTED_KEYS = frozenset((
    "schema", "record_kind", "record_id", "source_refs", "battle_context",
    "observations",
))
REF_KEYS = frozenset(("r1_end", "r2_prefire", "fleet_setup"))
CONTEXT_KEYS = frozenset((
    "battlefield_id", "attacker_forge_level", "defender_forge_level",
    "attacker_units", "defender_units", "workshop_upgrades",
    "reinforcements_between", "r2_prefire_confirmed",
))
OBS_KEYS = frozenset((
    "phase", "side", "unit_id", "wave_label", "physical_slot_label",
    "visible_percent", "units_alive", "source_ref",
))
WORKSHOP_KEYS = frozenset(("attack", "armor"))


def blank_template() -> dict:
    return {
        "schema": SCHEMA,
        "record_kind": TEMPLATE,
        "record_id": "",
        "source_refs": {"r1_end": None, "r2_prefire": None, "fleet_setup": None},
        "battle_context": {
            "battlefield_id": None,
            "attacker_forge_level": None, "defender_forge_level": None,
            "attacker_units": {}, "defender_units": {},
            "workshop_upgrades": {},
            "reinforcements_between": None,
            "r2_prefire_confirmed": None,
        },
        "observations": [],
    }


def _str_or_null(value) -> bool:
    # Preserve intentionally blank fields as incomplete transcription data.
    return value is None or isinstance(value, str)


def _int_or_null(value, lo=0, hi=None) -> bool:
    return value is None or (
        type(value) is int and value >= lo and (hi is None or value <= hi)
    )


def _keys(obj, expected, label, errors):
    if not isinstance(obj, dict):
        errors.append(f"{label}: expected object")
        return False
    extra = sorted(set(obj) - expected)
    if extra:
        errors.append(f"{label}: unrecognized or forbidden keys {extra}")
    return not extra


def _unit_counts(raw, label, errors):
    if not isinstance(raw, dict):
        errors.append(f"{label}: expected unit-id -> quantity object")
        return
    for uid, amount in raw.items():
        if not isinstance(uid, str) or not uid.strip() or not _int_or_null(amount, 0):
            errors.append(f"{label}: invalid unit id or quantity")


def _workshop(raw, errors):
    if not isinstance(raw, dict):
        errors.append("battle_context.workshop_upgrades: expected object")
        return
    for uid, levels in raw.items():
        if not isinstance(uid, str) or not uid.strip():
            errors.append("workshop: invalid unit id")
            continue
        if _keys(levels, WORKSHOP_KEYS, f"workshop.{uid}", errors):
            for name in WORKSHOP_KEYS:
                if not _int_or_null(levels.get(name), 0):
                    errors.append(f"workshop.{uid}.{name}: invalid level")


def _compare_setup(ctx: dict) -> dict:
    """Informational exact-field comparison; NEVER screen HP on this alone."""
    expected = _expected_control_setup()
    def levels(uid, k):
        workshop = ctx.get("workshop_upgrades", {})
        w = workshop.get(uid) if isinstance(workshop, dict) else None
        return w.get(k) if isinstance(w, dict) else None

    actual = {
        "battlefield_id": ctx.get("battlefield_id"),
        "attacker_forge_level": ctx.get("attacker_forge_level"),
        "defender_forge_level": ctx.get("defender_forge_level"),
        "attacker_units": ctx.get("attacker_units"),
        "defender_units": ctx.get("defender_units"),
        "ram_ship_attack_upgrade": levels("ram_ship", "attack"),
        "ram_ship_armor_upgrade": levels("ram_ship", "armor"),
        "steam_ram_attack_upgrade": levels("steam_ram", "attack"),
        "steam_ram_armor_upgrade": levels("steam_ram", "armor"),
        "tender_count": (
            ctx.get("defender_units", {}).get("tender")
            if isinstance(ctx.get("defender_units"), dict) else None
        ),
    }
    mismatch = [
        name for name, value in actual.items()
        if type(value) is not type(expected[name]) or value != expected[name]
    ]
    return {
        "synthetic_source_scenario": "naval_tender_support_1_live_R1_R2",
        "exact_original_synthetic_setup_fields_match": not bool(mismatch),
        "nonmatching_or_missing_fields": mismatch,
        "comparison_performed": False,
        "game_battle_identity_verified": False,
        "next_step": (
            "PR87 strict screenshot / Wave mapping intake would still be required"
            if not mismatch else
            "Different real fleets are archived, NOT screened against Tender synthetic HP models"
        ),
    }


def _report(status: str, errors: list, missing: list, record=None,
            digest=None, comparison=None):
    return {
        "schema": "p0_naval_capture_archive_result_v1",
        "status": status,
        "source_class": SOURCE_CLASS,
        "game_screenshot_contents_verified": False,
        "independently_verified_game_observations": 0,
        "independent_holdouts": 0,
        "official_game_mechanism_verified": False,
        "conditional_hp_model_comparison_performed": False,
        "invalid_fields": errors,
        "missing_for_followup": missing,
        "user_record_sha256": digest,
        "user_record_digest_is_screenshot_hash": False,
        "user_submitted_record": record,
        "synthetic_setup_comparison": comparison,
        "notes": [
            "Archive retains only manually entered metadata; source refs are strings and NOT accessed or verified.",
            "The digest hashes the transcription JSON, NOT original Gameforge screenshots.",
            "An incomplete but well-typed game record is retained and flagged; different fleets are not model refutations.",
            "Do not mix the historical owner-reported 53%/65% Carrier case with the synthetic Tender=1 case.",
        ],
    }


def archive(record) -> dict:
    if not isinstance(record, dict):
        return _report("INVALID", ["root: expected object"], [], None)
    errors = []
    if not _keys(record, EXPECTED_KEYS, "record", errors):
        return _report("INVALID", errors, [], None)
    if record.get("schema") != SCHEMA:
        errors.append("schema: not the archival schema")
    kind = record.get("record_kind")
    if kind == TEMPLATE and record == blank_template():
        return _report("EMPTY_TEMPLATE", [], [], None)
    if kind != TRANSCRIPTION:
        errors.append("record_kind: source must be user_transcribed_unverified")
    record_id = record.get("record_id")
    if not _str_or_null(record_id):
        errors.append("record_id: invalid type or blank string")
    refs = record.get("source_refs")
    if _keys(refs, REF_KEYS, "source_refs", errors):
        for phase in REF_KEYS:
            if not _str_or_null(refs.get(phase)):
                errors.append(f"source_refs.{phase}: invalid reference")
    ctx = record.get("battle_context")
    if _keys(ctx, CONTEXT_KEYS, "battle_context", errors):
        battlefield = ctx.get("battlefield_id")
        if battlefield is not None and (
                not isinstance(battlefield, str) or battlefield not in NAVAL_FIELDS):
            errors.append("battle_context.battlefield_id: unsupported naval battlefield")
        for name in ("attacker_forge_level", "defender_forge_level"):
            if not _int_or_null(ctx.get(name), 0, 5):
                errors.append(f"battle_context.{name}: invalid Forge level")
        _unit_counts(ctx.get("attacker_units"), "attacker_units", errors)
        _unit_counts(ctx.get("defender_units"), "defender_units", errors)
        _workshop(ctx.get("workshop_upgrades"), errors)
        reinforcements = ctx.get("reinforcements_between")
        if reinforcements is not None and (
                not isinstance(reinforcements, str) or
                reinforcements not in ("none", "present", "unknown")):
            errors.append("battle_context.reinforcements_between: unsupported value")
        prefire = ctx.get("r2_prefire_confirmed")
        if prefire is not None and type(prefire) is not bool:
            errors.append("battle_context.r2_prefire_confirmed: invalid bool")
    observations = record.get("observations")
    if not isinstance(observations, list):
        errors.append("observations: expected list")
        observations = []
    identities = set()
    for i, row in enumerate(observations):
        label = f"observations[{i}]"
        if not _keys(row, OBS_KEYS, label, errors):
            continue
        phase = row.get("phase")
        side = row.get("side")
        if not isinstance(phase, str) or phase not in PHASES:
            errors.append(f"{label}.phase: unrecognized screenshot phase")
        if not isinstance(side, str) or side not in SIDES:
            errors.append(f"{label}.side: attacker or defender needed")
        if not isinstance(row.get("unit_id"), str) or not row["unit_id"].strip():
            errors.append(f"{label}.unit_id: nonblank unit identity needed")
        for field in ("wave_label", "physical_slot_label", "source_ref"):
            if not _str_or_null(row.get(field)):
                errors.append(f"{label}.{field}: expected string or null")
        if not _int_or_null(row.get("visible_percent"), 0, 100):
            errors.append(f"{label}.visible_percent: expected integer 0..100 or null")
        if not _int_or_null(row.get("units_alive"), 1):
            errors.append(f"{label}.units_alive: expected positive integer or null")
        # Identity is only unambiguous when the submitter labels a physical
        # Slot. Two snapshots may share the label across phases.
        slot = row.get("physical_slot_label")
        wave = row.get("wave_label")
        if (isinstance(phase, str) and phase in PHASES
                and isinstance(side, str) and side in SIDES
                and isinstance(row.get("unit_id"), str) and row["unit_id"].strip()
                and isinstance(slot, str) and slot.strip()
                and isinstance(wave, str) and wave.strip()):
            key = (phase, side, row["unit_id"], wave, slot)
            if key in identities:
                errors.append(f"{label}: duplicate labeled physical Slot in same phase")
            identities.add(key)
    if errors:
        return _report("INVALID", errors, [], None)

    missing = []
    if not isinstance(record_id, str) or not record_id.strip():
        missing.append("record_id")
    for key in sorted(REF_KEYS):
        if not refs.get(key):
            missing.append(f"source_refs.{key}")
    if not ctx.get("battlefield_id"):
        missing.append("battle_context.battlefield_id")
    for field in ("attacker_forge_level", "defender_forge_level"):
        if ctx.get(field) is None:
            missing.append(f"battle_context.{field}")
    if not ctx.get("attacker_units"):
        missing.append("battle_context.attacker_units")
    if not ctx.get("defender_units"):
        missing.append("battle_context.defender_units")
    if not ctx.get("workshop_upgrades"):
        missing.append("battle_context.workshop_upgrades")
    # Nonempty maps may still contain intentionally UNKNOWN nested values.
    # They are valid to archive, but they are NOT complete self-reports.
    for side in ("attacker_units", "defender_units"):
        units = ctx.get(side)
        if isinstance(units, dict):
            for uid, quantity in units.items():
                if quantity is None:
                    missing.append(f"battle_context.{side}.{uid}.quantity")
    workshops = ctx.get("workshop_upgrades")
    if isinstance(workshops, dict):
        for uid, levels in workshops.items():
            if isinstance(levels, dict):
                for field in sorted(WORKSHOP_KEYS):
                    if levels.get(field) is None:
                        missing.append(f"battle_context.workshop_upgrades.{uid}.{field}")
    if ctx.get("reinforcements_between") in (None, "unknown"):
        missing.append("battle_context.reinforcements_between")
    if ctx.get("r2_prefire_confirmed") is not True:
        missing.append("battle_context.r2_prefire_confirmed")
    if not observations:
        missing.append("observations")
    by_phase = {row["phase"] for row in observations}
    for phase in PHASES - by_phase:
        missing.append(f"observations.{phase}")
    for i, row in enumerate(observations):
        if not row.get("source_ref"):
            missing.append(f"observations[{i}].source_ref")
        elif refs.get(row["phase"]) != row["source_ref"]:
            missing.append(f"observations[{i}].source_ref_mismatch")
        if row.get("visible_percent") is None:
            missing.append(f"observations[{i}].visible_percent")
        if row.get("units_alive") is None:
            missing.append(f"observations[{i}].units_alive")
        if not row.get("wave_label"):
            missing.append(f"observations[{i}].wave_label")
        if not row.get("physical_slot_label"):
            missing.append(f"observations[{i}].physical_slot_label")
    # Strip no user-provided metadata, including missing/incomplete claims.
    # Hash deterministic canonical JSON, not unverifiable external media.
    snapshot = json.loads(json.dumps(record, ensure_ascii=False, allow_nan=False))
    canonical = json.dumps(snapshot, sort_keys=True, ensure_ascii=False,
                           allow_nan=False, separators=(",", ":"))
    digest = sha256(canonical.encode("utf-8")).hexdigest()
    compare = _compare_setup(ctx)
    status = "UNVERIFIED_ARCHIVE_READY" if not missing else "UNVERIFIED_ARCHIVE_INCOMPLETE"
    return _report(status, [], sorted(set(missing)), snapshot, digest, compare)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write-template", type=Path)
    group.add_argument("--input", type=Path)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()
    if args.write_template:
        if args.output_json:
            parser.error("--output-json applies only to --input")
        target, output = args.write_template, blank_template()
    else:
        if not args.output_json:
            parser.error("--input requires --output-json")
        target = args.output_json
        output = archive(json.loads(args.input.read_text(encoding="utf-8")))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(json.dumps({"status": "EMPTY_TEMPLATE" if args.write_template else output["status"]},
                     ensure_ascii=False))
    if args.input and output["status"] == "INVALID":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
