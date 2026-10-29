"""Synthetic-only model candidate diagnostic fixtures; no Gameforge evidence."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from tools.research import p0_report_case_manual_visual_review as manual
from tools.research import p0_report_case_model_candidate_diagnostic as diagnostic

NODE = shutil.which("node")
# Deliberately incomplete headers, not decodable or original Gameforge images.
IMAGES = [b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + bytes([n]) * 24
          for n in (1, 2, 3, 4)]


@pytest.fixture
def case_bundle(tmp_path):
    if not NODE:
        pytest.skip("Node required for canonical browser case validation")
    model = Path(diagnostic.__file__).resolve().parents[2] / "battle-cases-model.js"
    source = r"""
const M=require(process.argv[1]);
const c=M.create('Synthetic only','naval-small');
c.rounds[0].number=50;
const r51=M.newRound(51),r52=M.newRound(52),r80=M.newRound(80);
r52.phase='round_prefire';r80.phase='round_end';
const a=M.newSlot('first',1);
Object.assign(a,{unit:'ram_ship',wave:'W1',count:6,hp:93});
r51.attacker.slots.push(a);
const b=M.newSlot('first',1);
Object.assign(b,{unit:'ram_ship',wave:'W1',count:5,hp:91});
r52.attacker.slots.push(b);
c.rounds.push(r80,r52,r51); // intentionally unordered
c.rounds[0].source='PRIVATE /a/secret/filename.png';
process.stdout.write(JSON.stringify(c));
"""
    value = subprocess.run([NODE, "-e", source, str(model)], check=True,
                           capture_output=True, timeout=10).stdout
    case = json.loads(value)
    root = tmp_path / "images"
    root.mkdir()
    for n, contents in enumerate(IMAGES):
        (root / f"capture-{n}.png").write_bytes(contents)
    order = {v["number"]: v for v in case["rounds"]}
    manifest = {
        "schema": "p0_report_case_local_image_manifest_v1",
        "record_kind": "user_supplied_unverified_files",
        "case_id": case["id"],
        "captures": [
            {
                "capture_id": order[num]["id"],
                "capture_round": num,
                "capture_phase": order[num]["phase"],
                "relative_path": f"capture-{i}.png",
                "expected_sha256": None,
            }
            for i, num in enumerate((50, 51, 52, 80))
        ],
    }
    review = manual.review_worksheet(value, manifest, root)
    assert len(review["review_items"]) == 3
    for row in review["review_items"]:
        row["review_status"] = "REVIEWER_REPORTS_IMAGES_READABLE"
    # Ensure approved reporter statuses are not confused with authentications.
    audited = manual.assess_review(value, manifest, root, review)
    assert audited["independently_verified_game_observations"] == 0
    review_bytes = json.dumps(review, sort_keys=True).encode("utf-8")
    return value, case, manifest, root, review_bytes


def proposal(case_bundle):
    raw, _, manifest, root, review_bytes = case_bundle
    worksheet = diagnostic.create_model_worksheet(raw, manifest, root, review_bytes)
    worksheet["model_run_label"] = "user-copied-synthetic-projection"
    for row, count, hp in zip(worksheet["comparison_rows"],
                              (7, 4, 0), (94, 90, 0)):
        row["predicted_target_unit"] = "ram_ship"
        row["predicted_target_wave"] = "W1"
        row["predicted_target_count"] = count
        row["predicted_target_hp_percent"] = hp
    return worksheet


def test_model_proposal_compares_only_readable_adjacent_same_phase_snapshots(case_bundle):
    raw, case, manifest, root, review = case_bundle
    sheet = proposal(case_bundle)
    draft = diagnostic.create_model_worksheet(raw, manifest, root, review)
    assert draft["record_kind"] == "draft_user_model_candidate_not_empirical_evidence"
    assert draft["model_source_class"] == diagnostic.USER_MODEL_SOURCE
    assert draft["model_run_label"] is None
    assert draft["case_id"] == case["id"]
    assert draft["review_worksheet_bytes_sha256"] == sha256(review).hexdigest()
    assert all(x["predicted_target_count"] is None for x in draft["comparison_rows"])
    assert [(x["earlier_round"], x["target_round"], x["review_reason"])
            for x in draft["comparison_rows"]] == [
                (50, 51, "ONE_SIDED"), (51, 52, "PHASE_MISMATCH"),
                (52, 80, "ONE_SIDED")]
    assert "PRIVATE /a/secret" not in json.dumps(draft)
    result = diagnostic.assess_model_candidate(raw, manifest, root, review, sheet)
    items = result["candidate_rows"]
    assert result["candidate_rows_with_numeric_diagnostic"] == 1
    assert items[0]["diagnostic_status"] == (
        "USER_ENTERED_MODEL_TARGET_SNAPSHOT_DIFFERENT_UNVERIFIED"
    )
    assert items[0]["target_typed_count"] == 6
    assert items[0]["target_typed_hp_percent"] == 93
    assert items[0]["model_minus_user_typed_count"] == 1
    assert items[0]["model_minus_user_typed_hp_percentage_points"] == 1
    assert items[1]["diagnostic_status"] == "NOT_ASSESSABLE_DIFFERENT_CAPTURE_PHASE"
    assert items[2]["diagnostic_status"] == "NOT_ASSESSABLE_UNOBSERVED_INTERMEDIATE_GAME_ROUNDS"
    assert all(row["gameforge_observation_authenticated"] is False for row in items)
    assert result["model_prediction_engine_attested"] is False
    assert result["original_game_screenshots_authenticated"] is False
    assert result["independently_verified_game_observations"] == 0
    assert result["independent_holdouts"] == 0
    assert result["combat_causality_inferred"] is False
    assert result["model_calibration_verified"] is False
    assert "PRIVATE /a/secret" not in json.dumps(result)
    assert str(root) not in json.dumps(result)
    sheet["comparison_rows"][0]["predicted_target_count"] = 6
    sheet["comparison_rows"][0]["predicted_target_hp_percent"] = 93
    same = diagnostic.assess_model_candidate(raw, manifest, root, review, sheet)
    assert same["candidate_rows"][0]["diagnostic_status"] == (
        "USER_ENTERED_MODEL_TARGET_SNAPSHOT_EQUAL_UNVERIFIED"
    )


def test_zero_count_vs_missing_and_labels_always_fail_closed(case_bundle):
    raw, _, manifest, root, review = case_bundle
    base = proposal(case_bundle)
    for key, value, code in (
        ("predicted_target_unit", "other_ship", "NOT_ASSESSABLE_MODEL_AND_TYPED_TARGET_LABELS_DIFFER"),
        ("predicted_target_wave", "W2", "NOT_ASSESSABLE_MODEL_AND_TYPED_TARGET_LABELS_DIFFER"),
        ("predicted_target_count", None, "NOT_ASSESSABLE_MODEL_CANDIDATE_INCOMPLETE"),
        ("predicted_target_hp_percent", None, "NOT_ASSESSABLE_MODEL_CANDIDATE_INCOMPLETE"),
    ):
        sheet = deepcopy(base)
        sheet["comparison_rows"][0][key] = value
        report = diagnostic.assess_model_candidate(raw, manifest, root, review, sheet)
        assert report["candidate_rows"][0]["diagnostic_status"] == code
        assert report["candidate_rows"][0]["model_minus_user_typed_count"] is None
    sheet = deepcopy(base)
    sheet["comparison_rows"][0]["predicted_target_count"] = 0
    sheet["comparison_rows"][0]["predicted_target_hp_percent"] = 0
    report = diagnostic.assess_model_candidate(raw, manifest, root, review, sheet)
    assert report["candidate_rows"][0]["model_minus_user_typed_count"] == -6
    assert report["candidate_rows"][0]["model_minus_user_typed_hp_percentage_points"] == -93


@pytest.mark.parametrize("mutation", [
    "bad_record_kind", "forged_authentication", "wrong_case_id",
    "wrong_case_hash", "wrong_review_hash", "wrong_capture_id", "wrong_slot",
    "wrong_review", "wrong_observed_count", "missing_row", "extra_row",
    "float_prediction", "bool_prediction", "negative_count", "hp_above_100",
    "bad_unit_type", "missing_model_label",
])
def test_model_candidate_rejects_forged_or_invalid_values(case_bundle, mutation):
    raw, _, manifest, root, review = case_bundle
    sheet = proposal(case_bundle)
    item = sheet["comparison_rows"][0]
    if mutation == "bad_record_kind":
        sheet["record_kind"] = "OFFICIAL_GAMEFORGE_PROVEN"
    elif mutation == "forged_authentication":
        sheet["official_gameforge_verified"] = True
    elif mutation == "wrong_case_id":
        sheet["case_id"] = "other"
    elif mutation == "wrong_case_hash":
        sheet["case_backup_bytes_sha256"] = "0" * 64
    elif mutation == "wrong_review_hash":
        sheet["review_worksheet_bytes_sha256"] = "0" * 64
    elif mutation == "wrong_capture_id":
        item["target_capture_id"] = "other"
    elif mutation == "wrong_slot":
        item["physical_position"] = 77
    elif mutation == "wrong_review":
        item["reviewer_reported_status"] = "NOT_REVIEWED"
    elif mutation == "wrong_observed_count":
        item["target_typed_count"] = 999
    elif mutation == "missing_row":
        sheet["comparison_rows"].pop()
    elif mutation == "extra_row":
        sheet["comparison_rows"].append(deepcopy(item))
    elif mutation == "float_prediction":
        item["predicted_target_count"] = 1.0
    elif mutation == "bool_prediction":
        item["predicted_target_hp_percent"] = True
    elif mutation == "negative_count":
        item["predicted_target_count"] = -1
    elif mutation == "hp_above_100":
        item["predicted_target_hp_percent"] = 101
    elif mutation == "bad_unit_type":
        item["predicted_target_unit"] = 12
    elif mutation == "missing_model_label":
        sheet["model_run_label"] = None
    with pytest.raises(ValueError):
        diagnostic.assess_model_candidate(raw, manifest, root, review, sheet)


def test_unreviewed_and_tampered_images_cannot_be_model_evidence(case_bundle):
    raw, case, manifest, root, review = case_bundle
    sheet = proposal(case_bundle)
    modified_review = json.loads(review)
    modified_review["review_items"][0]["review_status"] = "NOT_REVIEWED"
    raw_review = json.dumps(modified_review, sort_keys=True).encode("utf-8")
    with pytest.raises(ValueError):
        diagnostic.assess_model_candidate(raw, manifest, root, raw_review, sheet)
    draft = diagnostic.create_model_worksheet(raw, manifest, root, raw_review)
    draft["model_run_label"] = "synthetic"
    for k in diagnostic.MODEL_FIELDS:
        draft["comparison_rows"][0][k] = sheet["comparison_rows"][0][k]
    assessed = diagnostic.assess_model_candidate(raw, manifest, root, raw_review, draft)
    assert assessed["candidate_rows"][0]["diagnostic_status"] == (
        "NOT_ASSESSABLE_NO_READABLE_USER_REVIEW_OR_REVIEW_CONFLICT"
    )
    original = (root / "capture-1.png").read_bytes()
    (root / "capture-1.png").write_bytes(original + b"later altered")
    with pytest.raises(ValueError):
        diagnostic.assess_model_candidate(raw, manifest, root, review, sheet)
    (root / "capture-1.png").write_bytes(original)
    changed_case = deepcopy(case)
    changed_case["notes"] = "altered transcription"
    with pytest.raises(ValueError):
        diagnostic.assess_model_candidate(json.dumps(changed_case).encode(),
                                          manifest, root, review, sheet)


def test_cli_model_proposal_and_diagnostic_exclusive_output(case_bundle, tmp_path):
    raw, _, manifest, root, review = case_bundle
    original_case = tmp_path / "original-case.json"
    manifest_file = tmp_path / "manifest.json"
    review_file = tmp_path / "review.json"
    draft_file = tmp_path / "draft-prediction.json"
    report_file = tmp_path / "candidate-report.json"
    original_case.write_bytes(raw)
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    review_file.write_bytes(review)
    common = [sys.executable, "-m",
              "tools.research.p0_report_case_model_candidate_diagnostic",
              "--case", str(original_case), "--manifest", str(manifest_file),
              "--evidence-root", str(root),
              "--review-worksheet", str(review_file)]
    gen = common + ["--write-model-worksheet", str(draft_file)]
    result = subprocess.run(gen, capture_output=True, text=True, timeout=35)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "DRAFT_MODEL_CANDIDATE_NOT_ENGINE_ATTESTED"
    raw_draft = draft_file.read_bytes()
    assert json.loads(raw_draft)["comparison_rows"][0]["predicted_target_count"] is None
    assert subprocess.run(gen, capture_output=True, timeout=35).returncode == 2
    assert draft_file.read_bytes() == raw_draft
    assert subprocess.run(common + [
        "--write-model-worksheet", str(original_case)
    ], capture_output=True, timeout=35).returncode == 2
    assert original_case.read_bytes() == raw
    model = proposal(case_bundle)
    draft_file.write_text(json.dumps(model), encoding="utf-8")
    analyze = common + ["--model-worksheet", str(draft_file),
                        "--output-json", str(report_file)]
    good = subprocess.run(analyze, capture_output=True, text=True, timeout=35)
    assert good.returncode == 0, good.stderr
    assert json.loads(report_file.read_text())["candidate_rows_with_numeric_diagnostic"] == 1
    assert subprocess.run(analyze, capture_output=True, timeout=35).returncode == 2
    invalid = deepcopy(model)
    invalid["official_gameforge_verified"] = True
    draft_file.write_text(json.dumps(invalid), encoding="utf-8")
    failed_path = tmp_path / "never-created.json"
    rejected = subprocess.run(common + [
        "--model-worksheet", str(draft_file), "--output-json", str(failed_path)
    ], capture_output=True, timeout=35)
    assert rejected.returncode == 2
    assert not failed_path.exists()
    assert report_file.is_file()
