"""Real engine execution with synthetic local files, never an actual game battle."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from ikariam_battle import simulate
from tools.research import p0_report_case_real_engine_trace as adapter
from tools.research import p0_report_case_manual_visual_review as manual

NODE = shutil.which("node")
FAKE_IMAGES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + bytes(32),
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + bytes([1]) * 32,
)


@pytest.fixture(scope="module")
def engine_input():
    scenario = {
        "battlefield": "land-mini",
        "policy": "experimental",
        "max_rounds": 2,
        "attacker": {
            "army_kind": "player", "forge_level": 0,
            "units": [{"unit_id": "hoplite", "quantity": 120}],
        },
        "defender": {
            "army_kind": "player", "forge_level": 0,
            "units": [{"unit_id": "hoplite", "quantity": 120}],
        },
    }
    return json.dumps(scenario).encode("utf-8")


def test_engine_trace_uses_actual_current_production_simulator(engine_input):
    scenario = json.loads(engine_input)
    actual = simulate(scenario)
    projected = adapter.engine_trace(engine_input)
    assert projected["engine_execution_recorded"] is True
    assert projected["source_class"] == adapter.SOURCE
    assert projected["scenario_sha256"] == sha256(engine_input).hexdigest()
    assert projected["engine_output_sha256"] == sha256(adapter._bytes_json(actual)).hexdigest()
    assert projected["engine_applied_assumptions"] == actual["assumptions"]
    assert projected["engine_rounds_completed"] == actual["rounds_completed"]
    assert projected["engine_policy"] == actual["policy"]
    assert projected["engine_status"] == actual["status"]
    flat = [
        (r["round"], side, s["wave_id"], s["unit_id"],
         s["line"], s["physical_position"], s["units"])
        for r in actual["rounds"] for side in ("attacker", "defender")
        for s in r[side]["slots"]
    ]
    assert flat
    assert [
        (v["engine_round"], v["side"], v["wave_id"], v["unit_id"],
         v["line"], v["physical_position"], v["units"])
        for v in projected["engine_slots"]
    ] == flat
    assert all(v["engine_phase"] == (
        "initial" if v["engine_round"] == 0 else "round_end_model_snapshot"
    ) for v in projected["engine_slots"])
    assert projected["scenario_reconstructed_from_original_game"] is False
    assert projected["original_game_screenshots_authenticated"] is False
    assert projected["model_calibration_verified"] is False
    assert projected["independently_verified_game_observations"] == 0


@pytest.fixture
def local_synthetic_case(tmp_path, engine_input):
    if not NODE:
        pytest.skip("Node required for canonical browser v1 case")
    trace = adapter.engine_trace(engine_input)
    slots = [s for s in trace["engine_slots"] if s["engine_round"] == 2
             and s["side"] == "attacker" and s["unit_id"] == "hoplite"]
    assert slots, "synthetic fixture must run two engine rounds"
    model = slots[0]
    case_model = Path(adapter.__file__).resolve().parents[2] / "battle-cases-model.js"
    js = r"""
const M=require(process.argv[1]);
const meta=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
const c=M.create('Artificial model control','land-mini');
const r1=c.rounds[0];r1.number=1;
const r2=M.newRound(2);c.rounds.push(r2);
const early=M.newSlot(meta.line,meta.position);
Object.assign(early,{unit:meta.unit,wave:meta.wave,count:null,hp:null});
r1.attacker.slots=[early];
const late=M.newSlot(meta.line,meta.position);
Object.assign(late,{unit:meta.unit,wave:meta.wave,count:meta.units,hp:95});
r2.attacker.slots=[late];
r1.source='PRIVATE /not-to-be-exported.png';
process.stdout.write(JSON.stringify(c));
"""
    meta = {"line": model["line"], "position": model["physical_position"],
            "unit": model["unit_id"], "wave": model["wave_id"], "units": model["units"]}
    case_bytes = subprocess.run(
        [NODE, "-e", js, str(case_model)],
        input=json.dumps(meta).encode(), capture_output=True,
        check=True, timeout=10
    ).stdout
    case = json.loads(case_bytes)
    root = tmp_path / "fake-images"
    root.mkdir()
    for n, blob in enumerate(FAKE_IMAGES):
        (root / f"synthetic-{n}.png").write_bytes(blob)
    manifest = {
        "schema": "p0_report_case_local_image_manifest_v1",
        "record_kind": "user_supplied_unverified_files",
        "case_id": case["id"],
        "captures": [
            {"capture_id": case["rounds"][n]["id"],
             "relative_path": f"synthetic-{n}.png",
             "expected_sha256": None}
            for n in (0, 1)
        ],
    }
    review = manual.review_worksheet(case_bytes, manifest, root)
    assert len(review["review_items"]) == 1
    assert review["review_items"][0]["review_reason"] == "INCOMPLETE"
    review["review_items"][0]["review_status"] = "REVIEWER_REPORTS_IMAGES_READABLE"
    review_bytes = json.dumps(review).encode()
    assert manual.assess_review(case_bytes, manifest, root, review)["pending_review_items"] == 1
    mapping = {
        "schema": adapter.MAP_SCHEMA,
        "case_id": case["id"],
        "case_sha256": sha256(case_bytes).hexdigest(),
        "scenario_sha256": trace["scenario_sha256"],
        "bindings": [{
            "review_item_index": 0,
            "target_capture_id": case["rounds"][1]["id"],
            "engine_round": 2,
            "side": model["side"],
            "line": model["line"],
            "physical_position": model["physical_position"],
            "engine_wave_id": model["wave_id"],
        }],
    }
    return trace, case_bytes, manifest, root, review_bytes, mapping, model


def test_explicit_capture_to_engine_slot_mapping_only_gives_hypothesis_diagnostics(local_synthetic_case):
    trace, case_bytes, manifest, root, review, mapping, slot = local_synthetic_case
    result = adapter.compare_to_captures(trace, case_bytes, manifest, root, review, mapping)
    assert len(result["bindings"]) == 1
    one = result["bindings"][0]
    assert one["engine_slot_found"] is True
    assert one["engine_round"] == 2
    assert one["engine_units"] == slot["units"]
    assert one["engine_hp_metric_percent"] == slot["hit_points_percent"]
    assert one["engine_unit_id"] == "hoplite"
    assert one["engine_hp_metric_not_game_ui_bar"] is True
    assert one["hp_percentage_point_difference"] is None
    if any(e["round"] is None or e["round"] <= 2
           for e in trace["engine_unsupported_events"]):
        assert one["diagnostic_status"] == "NOT_ASSESSABLE_ENGINE_UNSUPPORTED_MECHANIC_BOUNDARY"
        assert one["count_difference"] is None
    else:
        assert one["diagnostic_status"] == "ENGINE_MINUS_USER_TYPED_COUNT_UNVERIFIED"
        assert one["count_difference"] == 0
    assert result["physical_slot_and_wave_mapping_user_asserted"] is True
    assert result["original_game_screenshots_authenticated"] is False
    assert result["independently_verified_game_observations"] == 0
    assert result["independent_holdouts"] == 0
    assert result["model_calibration_verified"] is False
    assert "PRIVATE /not-to-be-exported.png" not in json.dumps(result)
    assert str(root) not in json.dumps(result)


@pytest.mark.parametrize("changed", [
    "wrong_round", "wrong_capture", "wrong_position", "wrong_line",
    "wrong_wave", "wrong_case_hash", "wrong_scenario_hash", "wrong_battlefield",
    "duplicate_binding", "forged_proof_field", "negative_index", "index_bool",
])
def test_wrong_or_forged_wave_and_physical_address_rejected(local_synthetic_case,changed):
    trace, case_bytes, manifest, root, review, mapping, slot = local_synthetic_case
    bad = deepcopy(mapping)
    if changed == "wrong_round":bad["bindings"][0]["engine_round"] = 1
    elif changed == "wrong_capture":bad["bindings"][0]["target_capture_id"] = "other"
    elif changed == "wrong_position":bad["bindings"][0]["physical_position"] += 1
    elif changed == "wrong_line":bad["bindings"][0]["line"] = "flank"
    elif changed == "wrong_wave":bad["bindings"][0]["engine_wave_id"] = "nonexistent"
    elif changed == "wrong_case_hash":bad["case_sha256"] = "0"*64
    elif changed == "wrong_scenario_hash":bad["scenario_sha256"] = "0"*64
    elif changed == "wrong_battlefield":trace = {**trace,"scenario_battlefield":"naval-mini"}
    elif changed == "duplicate_binding":bad["bindings"].append(deepcopy(bad["bindings"][0]))
    elif changed == "forged_proof_field":bad["official_verified"]=True
    elif changed == "negative_index":bad["bindings"][0]["review_item_index"]=-1
    elif changed == "index_bool":bad["bindings"][0]["review_item_index"]=True
    if changed == "wrong_wave":
        # An explicitly asserted but absent Wave must never fabricate a hit.
        output = adapter.compare_to_captures(trace, case_bytes, manifest, root, review, bad)
        assert output["bindings"][0]["engine_slot_found"] is False
        assert output["bindings"][0]["count_difference"] is None
    else:
        with pytest.raises(ValueError):
            adapter.compare_to_captures(trace, case_bytes, manifest, root, review, bad)


def test_local_engine_trace_cli_is_real_and_never_clobbers_input(engine_input,tmp_path):
    scenario_path=tmp_path/"real-scenario.json"
    output_path=tmp_path/"real-execution.json"
    scenario_path.write_bytes(engine_input)
    command=[sys.executable,"-m","tools.research.p0_report_case_real_engine_trace",
             "--scenario",str(scenario_path),"--output-json",str(output_path)]
    run=subprocess.run(command,capture_output=True,text=True,timeout=35)
    assert run.returncode==0,run.stderr
    assert json.loads(run.stdout)["status"]=="ACTUAL_ENGINE_RUN_HYPOTHETICAL_NOT_GAME_VERIFIED"
    result=json.loads(output_path.read_bytes())
    assert result["capture_alignment"] is None
    assert result["engine_execution"]["scenario_sha256"]==sha256(engine_input).hexdigest()
    assert result["engine_execution"]["engine_execution_recorded"] is True
    before_scenario=scenario_path.read_bytes()
    before_output=output_path.read_bytes()
    assert subprocess.run(command,capture_output=True,timeout=35).returncode==2
    assert subprocess.run(command[:-1]+[str(scenario_path)],capture_output=True,timeout=35).returncode==2
    assert scenario_path.read_bytes()==before_scenario
    assert output_path.read_bytes()==before_output


def test_no_case_evidence_does_not_magically_produce_capture_alignment(engine_input):
    trace=adapter.engine_trace(engine_input)
    assert trace["engine_slots"]
    assert trace["scenario_reconstructed_from_original_game"] is False
    assert trace["independently_verified_game_observations"] == 0
    assert trace["independent_holdouts"] == 0



def test_actual_engine_unsupported_boundary_never_labeled_round_end():
    scenario = {
        "battlefield": "land-mini", "policy": "experimental", "max_rounds": 2,
        "attacker": {"units": [
            {"unit_id": "hoplite", "quantity": 30,
             "wave_id": "initial", "entry_batch_id": "a0", "arrival_round": 0},
            {"unit_id": "hoplite", "quantity": 90,
             "wave_id": "arriving", "entry_batch_id": "a2", "arrival_round": 2},
        ]},
        "defender": {"units": [{"unit_id": "hoplite", "quantity": 120}]},
    }
    actual = simulate(scenario)
    unsupported = [
        e for e in actual["events"]
        if e["type"] == "unsupported_mechanic"
        and e["round"] == 2
    ]
    assert unsupported, "synthetic scenario must hit actual engine unsupported boundary"
    trace = adapter.engine_trace(json.dumps(scenario).encode())
    assert any(e["round"] == 2 for e in trace["engine_unsupported_events"])
    interrupted = [x for x in trace["engine_slots"] if x["engine_round"] == 2]
    assert interrupted, "engine should expose preserved boundary snapshot"
    assert all(x["engine_phase"] == "unsupported_boundary_not_round_end"
               for x in interrupted)
    assert not any(x["engine_phase"] == "round_end_model_snapshot"
                   for x in interrupted)
    assert all(x["engine_phase"] == "initial"
               for x in trace["engine_slots"] if x["engine_round"] == 0)


@pytest.mark.parametrize("missing_label", ["unit", "wave"])
def test_earlier_unknown_unit_or_wave_never_qualifies_as_continuous_identity(
    local_synthetic_case, missing_label
):
    trace, case_bytes, manifest, root, review, mapping, model = local_synthetic_case
    changed = json.loads(case_bytes)
    first = next(r for r in changed["rounds"] if r["number"] == 1)
    first["attacker"]["slots"][0][missing_label] = ""
    new_bytes = json.dumps(changed).encode()
    latest_review = manual.review_worksheet(new_bytes, manifest, root)
    assert latest_review["review_items"][0]["review_reason"] == "INCOMPLETE"
    latest_review["review_items"][0]["review_status"] = (
        "REVIEWER_REPORTS_IMAGES_READABLE"
    )
    new_review = json.dumps(latest_review).encode()
    new_map = deepcopy(mapping)
    new_map["case_sha256"] = sha256(new_bytes).hexdigest()
    result = adapter.compare_to_captures(
        trace, new_bytes, manifest, root, new_review, new_map
    )
    row = result["bindings"][0]
    assert row["engine_slot_found"] is True
    assert row["diagnostic_status"] == (
        "NOT_ASSESSABLE_EARLIER_UNIT_OR_WAVE_MISSING_OR_CHANGED"
    )
    assert row["count_difference"] is None
    assert row["hp_percentage_point_difference"] is None
    assert result["original_game_screenshots_authenticated"] is False



def test_real_open_field_override_rejects_same_number_different_geometry(
    local_synthetic_case
):
    _, case_bytes, manifest, root, review_bytes, mapping, _ = local_synthetic_case
    scenario = {
        "battlefield": "land-mini",
        "town_hall_level": 1,
        "policy": "experimental", "max_rounds": 2,
        "attacker": {"units": [{"unit_id": "hoplite", "quantity": 600}]},
        "defender": {"units": [{"unit_id": "hoplite", "quantity": 600}]},
    }
    actual = simulate(scenario)
    assert actual["garrison_status"]["effective_battlefield"] == "land-max"
    trace = adapter.engine_trace(json.dumps(scenario).encode("utf-8"))
    assert trace["scenario_battlefield"] == "land-mini"
    assert trace["engine_effective_battlefield"] == "land-max"
    altered_map = deepcopy(mapping)
    altered_map["scenario_sha256"] = trace["scenario_sha256"]
    with pytest.raises(ValueError, match="effective engine deployment battlefield"):
        adapter.compare_to_captures(
            trace, case_bytes, manifest, root, review_bytes, altered_map,
        )
    assert trace["scenario_reconstructed_from_original_game"] is False


def test_no_open_field_override_preserves_requested_and_effective_geometry(engine_input):
    result = adapter.engine_trace(engine_input)
    assert result["scenario_battlefield"] == "land-mini"
    assert result["engine_effective_battlefield"] == "land-mini"


# Follow-up to PR #120: a *real* simulator trace projected over a declared
# partial observation with the existing image/review/slot-map safety gates.
from tools.research import p0_report_case_focused_engine_diagnostic as focused


def _focused_inputs(local_synthetic_case):
    trace, case_bytes, manifest, root, review_bytes, mapping, model = local_synthetic_case
    case = json.loads(case_bytes)
    # Only declared partial observations are eligible. This is a synthetic
    # case created from the real engine, NOT an original Gameforge report.
    case["research"] = {
        "kind": "partial_observation",
        "objective": "Only first-line physical position casualty research",
        "observed_scope": "Single side and line; other positions unknown",
        "known_conditions": "Synthetic fixture for test only",
        "hypothetical_inputs": "Simulated hoplite forces",
        "unknown_fields": "Unobserved game mechanics and source identity",
        "confirmed_absences": "",
    }
    new_bytes = json.dumps(case, ensure_ascii=False).encode()
    new_review = manual.review_worksheet(new_bytes, manifest, root)
    assert len(new_review["review_items"]) == 1
    new_review["review_items"][0]["review_status"] = "REVIEWER_REPORTS_IMAGES_READABLE"
    new_review_bytes = json.dumps(new_review).encode()
    new_map = deepcopy(mapping)
    new_map["case_sha256"] = sha256(new_bytes).hexdigest()
    return new_bytes, manifest, root, new_review_bytes, new_map, model


def test_focused_actual_engine_reuses_source_review_wave_and_round_gates(engine_input, local_synthetic_case):
    case_bytes, manifest, root, review_bytes, slot_map, slot = _focused_inputs(local_synthetic_case)
    target_capture = json.loads(case_bytes)["rounds"][1]["id"]
    report = focused.focused_diagnostic(
        engine_input, case_bytes, manifest, root, review_bytes, slot_map,
        capture_id=target_capture, side="attacker", line=slot["line"],
    )
    assert report["schema"] == focused.SCHEMA
    assert report["source_class"] == adapter.SOURCE
    assert report["scenario_sha256"] == sha256(engine_input).hexdigest()
    assert report["engine_output_sha256"] == adapter.engine_trace(engine_input)["engine_output_sha256"]
    assert report["typed_positions"] == 1
    assert report["explicit_bindings_in_focus"] == 1
    assert report["descriptive_count_comparisons"] == 1
    item = report["rows"][0]
    assert item["count_comparison_status"] == "ENGINE_MINUS_USER_TYPED_COUNT_UNVERIFIED"
    assert item["typed_count"] == slot["units"]
    assert item["engine_count_context_only"] == slot["units"]
    assert item["engine_minus_typed_count"] == 0  # Real known zero, not missing.
    assert item["engine_internal_hp_context_only"] == slot["hit_points_percent"]
    assert item["engine_minus_game_hp_points"] is None
    assert report["hp_bar_comparison_performed"] is False
    assert report["global_calibration_allowed"] is False
    assert report["game_source_authenticated"] is False
    assert report["scenario_reconstructed_from_game"] is False
    assert report["independent_holdouts"] == 0
    assert report["source_notes_or_image_paths_exported"] is False
    serialized = json.dumps(report)
    assert "not-to-be-exported" not in serialized
    assert "fake-images" not in serialized
    assert str(root) not in serialized


def test_focused_actual_engine_never_auto_maps_unbound_wave(engine_input, local_synthetic_case):
    case_bytes, manifest, root, review_bytes, slot_map, slot = _focused_inputs(local_synthetic_case)
    target_capture = json.loads(case_bytes)["rounds"][1]["id"]
    slot_map["bindings"] = []
    result = focused.focused_diagnostic(
        engine_input, case_bytes, manifest, root, review_bytes, slot_map,
        capture_id=target_capture, side="attacker", line=slot["line"],
    )
    assert result["typed_positions"] == 1
    assert result["explicit_bindings_in_focus"] == 0
    assert result["descriptive_count_comparisons"] == 0
    row = result["rows"][0]
    assert row["count_comparison_status"] == "NOT_ASSESSABLE_NO_EXPLICIT_REVIEW_SLOT_BINDING"
    assert row["engine_minus_typed_count"] is None
    assert row["engine_count_context_only"] is None


def test_focused_actual_engine_rejects_unscoped_and_stale_source(engine_input, local_synthetic_case):
    case_bytes, manifest, root, review_bytes, slot_map, slot = _focused_inputs(local_synthetic_case)
    c = json.loads(case_bytes)
    target = c["rounds"][1]["id"]
    def attempt(data, *, capture_id=target, side="attacker", line=slot["line"], map_data=slot_map):
        return focused.focused_diagnostic(
            engine_input, data, manifest, root, review_bytes, map_data,
            capture_id=capture_id, side=side, line=line,
        )
    for kind in ("full_report", "research_summary"):
        wrong = deepcopy(c)
        wrong["research"]["kind"] = kind
        with pytest.raises(ValueError, match="partial_observation"):
            attempt(json.dumps(wrong).encode())
    legacy = deepcopy(c)
    del legacy["research"]
    with pytest.raises(ValueError, match="partial_observation"):
        attempt(json.dumps(legacy).encode())
    with pytest.raises(ValueError, match="ID not unique or not found"):
        attempt(case_bytes, capture_id="missing-round")
    with pytest.raises(ValueError, match="canonical formation address"):
        attempt(case_bytes, side="third-side")
    with pytest.raises(ValueError, match="no typed numeric"):
        attempt(case_bytes, side="defender", line="flank")
    prefire = deepcopy(c)
    prefire["rounds"][1]["phase"] = "round_prefire"
    with pytest.raises(ValueError, match="prefire"):
        attempt(json.dumps(prefire).encode())
    stale = deepcopy(c)
    stale["notes"] = "changed-case-bytes-invalidates-map"
    # Strict manual review case-byte anchor rejects this BEFORE map checking.
    with pytest.raises(ValueError, match="review worksheet.*stale"):
        attempt(json.dumps(stale).encode())
    bad_map = deepcopy(slot_map)
    bad_map["case_sha256"] = "0"*64
    with pytest.raises(ValueError, match="source hashes do not match"):
        attempt(case_bytes, map_data=bad_map)
    # In-place change to the private screenshot files is rejected by the
    # existing fresh image-byte validation, not ignored by focused projection.
    (root / "synthetic-0.png").write_bytes(b"tampered")
    with pytest.raises(ValueError):
        attempt(case_bytes)


def test_focused_actual_engine_cli_output_exclusive(engine_input, local_synthetic_case, tmp_path):
    case_bytes, manifest, root, review_bytes, slot_map, slot = _focused_inputs(local_synthetic_case)
    target = json.loads(case_bytes)["rounds"][1]["id"]
    for filename, payload in (
        ("scenario.json", engine_input),
        ("case.json", case_bytes),
        ("manifest.json", json.dumps(manifest).encode()),
        ("review.json", review_bytes),
        ("slot-map.json", json.dumps(slot_map).encode()),
    ):
        (tmp_path / filename).write_bytes(payload)
    out = tmp_path / "focused-only.json"
    cmd = [
        sys.executable, "-m",
        "tools.research.p0_report_case_focused_engine_diagnostic",
        "--scenario", str(tmp_path / "scenario.json"),
        "--case", str(tmp_path / "case.json"),
        "--manifest", str(tmp_path / "manifest.json"),
        "--evidence-root", str(root),
        "--review-worksheet", str(tmp_path / "review.json"),
        "--slot-map", str(tmp_path / "slot-map.json"),
        "--capture-id", target,
        "--side", "attacker",
        "--line", slot["line"],
        "--output-json", str(out),
    ]
    first = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
    assert first.returncode == 0, first.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["descriptive_count_comparisons"] == 1
    assert "verified_game_mechanics" in first.stdout
    second = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
    assert second.returncode == 2
    assert "refusing to overwrite" in second.stderr
    assert data == json.loads(out.read_text(encoding="utf-8"))
