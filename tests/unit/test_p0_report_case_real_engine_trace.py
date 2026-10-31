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


# PR #122: adjacent-round descriptive changes are NOT casualty/mechanic proof.
from tools.research import p0_report_case_multi_round_engine_diagnostic as multi


def _synthetic_pair(a_count=9, b_count=7, *, a_wave="w1", b_wave="w1",
                    b_engine_wave="model-w1", first_round=80, second_round=81):
    base = {
        "schema": focused.SCHEMA,
        "source_class": adapter.SOURCE,
        "case_sha256": "a" * 64,
        "scenario_sha256": "b" * 64,
        "engine_source_sha256": "c" * 64,
        "engine_output_sha256": "d" * 64,
        "review_worksheet_sha256": "e" * 64,
        "case_id": "synthetic",
        "side": "attacker", "line": "flank",
        "engine_policy": "experimental",
    }
    def row(count, engine_count, wave, engine_wave):
        return {
            "physical_position": 1,
            "typed_unit_label": "swordsman",
            "typed_wave_label": wave,
            "typed_count": count,
            "typed_deaths": None,
            "typed_hp_percent": None,
            "engine_unit_id": "swordsman",
            "engine_wave_id_user_asserted": engine_wave,
            "engine_count_context_only": engine_count,
            "engine_minus_typed_count": engine_count-count,
            "count_comparison_status": multi.ELIGIBLE,
        }
    a = {**base, "capture_round": first_round, "capture_id": "early",
         "rows": [row(a_count, 8, a_wave, "model-w1")]}
    b = {**base, "capture_round": second_round, "capture_id": "later",
         "rows": [row(b_count, 6, b_wave, b_engine_wave)]}
    return a, b


def test_multi_round_adjacent_count_changes_are_descriptive_only():
    a,b = _synthetic_pair()
    pair = multi._pair(a,b)
    assert pair["round_number_gap"] == 1
    assert pair["descriptive_change_comparisons"] == 1
    row=pair["rows"][0]
    assert row["comparison_status"] == "DESCRIPTIVE_COUNT_CHANGES_ONLY_NOT_CAUSAL"
    assert row["typed_count_change"] == -2
    assert row["engine_count_change"] == -2
    assert row["engine_minus_typed_change"] == 0
    assert row["hp_or_casualty_mechanism_inferred"] is False


def test_multi_round_whitespace_only_wave_and_unit_labels_are_unknown_not_deltas():
    # Codex P2 #4426839047: the old boolean check accepted " " as a Wave
    # label, even if the engine and manual source both supplied that value.
    # Preserve the original strings; never strip-and-compare as an identity.
    for blank in (" ", " \t ", "\n", "\u3000"):
        for field in ("typed_wave_label", "typed_unit_label"):
            a,b=_synthetic_pair()
            a["rows"][0][field]=blank
            b["rows"][0][field]=blank
            p=multi._pair(a,b)
            assert p["descriptive_change_comparisons"]==0
            assert p["rows"][0]["comparison_status"]=="NOT_ASSESSABLE_INCOMPLETE_TYPED_WAVE_IDENTITY"
            assert p["rows"][0]["typed_count_change"] is None
            assert p["rows"][0]["engine_count_change"] is None
            assert p["rows"][0]["engine_minus_typed_change"] is None
        for field in ("engine_wave_id_user_asserted", "engine_unit_id"):
            a,b=_synthetic_pair()
            a["rows"][0][field]=blank
            b["rows"][0][field]=blank
            p=multi._pair(a,b)
            assert p["descriptive_change_comparisons"]==0
            assert p["rows"][0]["comparison_status"]=="NOT_ASSESSABLE_INCOMPLETE_ENGINE_WAVE_IDENTITY"
            assert p["rows"][0]["typed_count_change"] is None
            assert p["rows"][0]["engine_count_change"] is None
            assert p["rows"][0]["engine_minus_typed_change"] is None


def test_multi_round_wave_identity_requires_exact_raw_equality_after_nonblank_gate():
    a,b=_synthetic_pair()
    # Nonblank surrounding whitespace is not automatically normalized:
    # the distinct raw source Wave labels cannot be equated.
    a["rows"][0]["typed_wave_label"]="w1"
    b["rows"][0]["typed_wave_label"]=" w1 "
    p=multi._pair(a,b)
    assert p["rows"][0]["comparison_status"]=="NOT_ASSESSABLE_DIFFERENT_WAVE_OR_UNIT_IDENTITY"
    assert p["rows"][0]["typed_count_change"] is None
    # Two identical nonempty labels are allowed, despite surrounding spaces.
    a["rows"][0]["typed_wave_label"]=" w1 "
    p=multi._pair(a,b)
    assert p["descriptive_change_comparisons"]==1
    # The engine mapping identity is also compared verbatim, never trimmed.
    b["rows"][0]["engine_wave_id_user_asserted"]=" model-w1 "
    p=multi._pair(a,b)
    assert p["rows"][0]["comparison_status"]=="NOT_ASSESSABLE_DIFFERENT_WAVE_OR_UNIT_IDENTITY"


def test_multi_round_unknown_zero_unpaired_and_gapped_never_invent_changes():
    a,b = _synthetic_pair(a_count=0,b_count=0)
    p=multi._pair(a,b)["rows"][0]
    assert p["typed_count_change"] == 0
    assert p["engine_count_change"] == -2
    assert p["engine_minus_typed_change"] == -2
    assert a["rows"][0]["typed_count"] == 0
    for candidate in (
        {"capture_round":83},
        {"rows":[{**b["rows"][0],"physical_position":2}]},
        {"rows":[{**b["rows"][0],"count_comparison_status":
                  "NOT_ASSESSABLE_NO_EXPLICIT_REVIEW_SLOT_BINDING",
                  "engine_minus_typed_count":None}]},
        {"rows":[{**b["rows"][0],"typed_count":None,
                  "engine_minus_typed_count":None,
                  "count_comparison_status":"NOT_ASSESSABLE_UNKNOWN_TYPED_COUNT"}]},
        {"rows":[{**b["rows"][0],"typed_wave_label":""}]},
        {"rows":[{**b["rows"][0],"typed_wave_label":"w2"}]},
        {"rows":[{**b["rows"][0],"engine_wave_id_user_asserted":"model-w2"}]},
        {"rows":[{**b["rows"][0],"engine_unit_id":"hoplite"}]},
    ):
        mod={**b,**candidate}
        result=multi._pair(a,mod)
        assert result["descriptive_change_comparisons"]==0,mod
        assert all(r["typed_count_change"] is None
                   and r["engine_count_change"] is None
                   and r["engine_minus_typed_change"] is None
                   for r in result["rows"])
    with pytest.raises(ValueError,match="strictly increasing"):
        multi._pair(b,a)
    with pytest.raises(ValueError,match="provenance"):
        multi._pair(a,{**b,"scenario_sha256":"0"*64})
    with pytest.raises(ValueError,match="duplicated physical"):
        multi._pair(a,{**b,"rows":[b["rows"][0],b["rows"][0]]})



def test_evidence_summary_preserves_numeric_equal_and_both_signed_differences():
    # These are three different synthetic descriptions of existing model and
    # transcribed changes; not observed Gameforge source or model validation.
    cases = [
        (_synthetic_pair(a_count=9,b_count=7), multi.NUMERIC_SAME),
        (_synthetic_pair(a_count=9,b_count=6), multi.NUMERIC_ABOVE),
        (_synthetic_pair(a_count=9,b_count=8), multi.NUMERIC_BELOW),
    ]
    pairs = [multi._pair(a,b) for (a,b),_ in cases]
    summary = multi.summarize_evidence(pairs)
    assert summary["schema"] == multi.SUMMARY_SCHEMA
    assert summary["capture_pairs_count"] == 3
    assert summary["typed_position_pair_rows"] == 3
    assert summary["descriptive_numeric_change_rows"] == 3
    assert summary["unassessable_rows"] == 0
    assert summary["numeric_change_equal_rows"] == 1
    assert summary["numeric_engine_change_above_typed_rows"] == 1
    assert summary["numeric_engine_change_below_typed_rows"] == 1
    assert [p["rows"][0]["evidence_category"] for p in pairs] == [
        expected for _, expected in cases
    ]
    assert all(x["descriptive_numeric_change_rows"]==1 for x in summary["pair_summaries"])
    assert summary["denominator_is_typed_slot_pair_rows_not_complete_battle"] is True
    assert summary["cross_pair_rows_are_not_independent_holdouts"] is True
    assert summary["descriptive_zero_residual_is_not_model_verification"] is True
    assert summary["battle_causality_or_calibration_verified"] is False


def test_evidence_summary_accounts_for_missing_round_identity_and_position():
    a,b = _synthetic_pair(a_count=0,b_count=0)
    scenarios = [
        ({**b, "capture_round":83}, "NOT_ASSESSABLE_MISSING_INTERVENING_CAPTURE_ROUNDS"),
        ({**b, "rows":[{**b["rows"][0],"physical_position":2}]},
         "NOT_ASSESSABLE_TYPED_POSITION_MISSING_IN_ONE_CAPTURE"),
        ({**b, "rows":[{**b["rows"][0],
                       "count_comparison_status":"NOT_ASSESSABLE_NO_EXPLICIT_REVIEW_SLOT_BINDING",
                       "engine_minus_typed_count":None}]},
         "NOT_ASSESSABLE_SOURCE_OR_ENGINE_MAPPING_GATE"),
        ({**b, "rows":[{**b["rows"][0],"typed_wave_label":" \t "}]},
         "NOT_ASSESSABLE_INCOMPLETE_TYPED_WAVE_IDENTITY"),
        ({**b, "rows":[{**b["rows"][0],"engine_wave_id_user_asserted":"\u3000"}]},
         "NOT_ASSESSABLE_INCOMPLETE_ENGINE_WAVE_IDENTITY"),
        ({**b, "rows":[{**b["rows"][0],"typed_wave_label":"another-wave"}]},
         "NOT_ASSESSABLE_DIFFERENT_WAVE_OR_UNIT_IDENTITY"),
    ]
    pairs=[multi._pair(a,s) for s,_ in scenarios]
    result=multi.summarize_evidence(pairs)
    assert result["capture_pairs_count"]==len(pairs)
    # The missing-position case contributes two typed original positions,
    # both unassessable; we must never collapse them into one phantom slot.
    assert result["typed_position_pair_rows"]==len(pairs)+1
    assert result["descriptive_numeric_change_rows"]==0
    assert result["unassessable_rows"]==len(pairs)+1
    for pair,(_,reason) in zip(pairs,scenarios):
        assert all(r["evidence_category"]==reason for r in pair["rows"])
        assert all(r["typed_count_change"] is None for r in pair["rows"])
        assert all(r["engine_count_change"] is None for r in pair["rows"])
    assert result["category_counts"]["NOT_ASSESSABLE_TYPED_POSITION_MISSING_IN_ONE_CAPTURE"]==2
    assert all(p["unassessable_rows"]==p["typed_position_pairs"] for p in result["pair_summaries"])
    assert result["battle_causality_or_calibration_verified"] is False


def test_evidence_summary_rejects_malformed_eligibility_and_failed_reconciliation():
    a,b=_synthetic_pair()
    good=multi._pair(a,b)
    def corrupt(**changes):
        row={**good["rows"][0],**changes}
        return [{**good, "rows":[row]}]
    for row_changes,pattern in [
        ({"engine_minus_typed_change":None}, "three exact integer"),
        ({"engine_minus_typed_change":True}, "three exact integer"),
        ({"engine_minus_typed_change":10}, "does not reconcile"),
        ({"comparison_status":"UNRECOGNIZED"}, "unknown comparison status"),
        ({"comparison_status":"NOT_ASSESSABLE_SOURCE_OR_ENGINE_MAPPING_GATE"},
         "null numeric changes"),
    ]:
        with pytest.raises(ValueError,match=pattern):
            multi.summarize_evidence(corrupt(**row_changes))
    with pytest.raises(ValueError,match="count does not reconcile"):
        multi.summarize_evidence([{**good,"descriptive_change_comparisons":2}])


def _multi_real_case(local_synthetic_case):
    raw, manifest, root, _, mapping, model = _focused_inputs(local_synthetic_case)
    c=json.loads(raw)
    # R1 is partially typed with an explicit zero death count; numeric first
    # capture now qualifies for focus but has no user-entered binding row.
    c["rounds"][0]["attacker"]["slots"][0]["deaths"]=0
    updated=json.dumps(c,ensure_ascii=False).encode()
    review=manual.review_worksheet(updated,manifest,root)
    assert len(review["review_items"])==1
    review["review_items"][0]["review_status"]="REVIEWER_REPORTS_IMAGES_READABLE"
    mapping["case_sha256"]=sha256(updated).hexdigest()
    return updated,manifest,root,json.dumps(review).encode(),mapping,model,c


def test_multi_round_real_simulator_with_source_gates_and_unknown_wave(engine_input,local_synthetic_case):
    raw,manifest,root,review,mapping,model,c=_multi_real_case(local_synthetic_case)
    ids=[r["id"] for r in c["rounds"]]
    result=multi.multi_round_diagnostic(
        engine_input,raw,manifest,root,review,mapping,
        capture_ids=ids,side="attacker",line=model["line"],
    )
    assert result["schema"]==multi.SCHEMA
    assert result["source_class"]==adapter.SOURCE
    assert result["capture_ids"]==ids
    assert result["actual_current_engine_executed"] is True
    assert result["number_of_engine_executions"]==2
    assert result["strictly_adjacent_pairs"]==1
    assert result["descriptive_change_comparisons"]==0
    summary=result["comparison_evidence_summary"]
    assert summary["schema"]==multi.SUMMARY_SCHEMA
    assert summary["descriptive_numeric_change_rows"]==0
    assert summary["unassessable_rows"]==1
    assert summary["category_counts"]=={"NOT_ASSESSABLE_SOURCE_OR_ENGINE_MAPPING_GATE":1}
    assert summary["battle_causality_or_calibration_verified"] is False
    pair=result["round_pairs"][0]
    assert pair["rows"][0]["comparison_status"]=="NOT_ASSESSABLE_SOURCE_OR_ENGINE_MAPPING_GATE"
    assert pair["rows"][0]["typed_count_change"] is None
    assert result["capture_projections"][0]["rows"][0]["typed_deaths"] == 0
    assert result["capture_projections"][0]["rows"][0]["typed_count"] is None
    assert result["global_calibration_allowed"] is False
    assert result["hp_bar_comparison_performed"] is False
    assert result["casualty_damage_healing_or_reserve_mechanism_inferred"] is False
    assert result["independent_holdouts"] == 0
    serialized=json.dumps(result)
    assert "not-to-be-exported" not in serialized
    assert str(root) not in serialized
    with pytest.raises(ValueError,match="2-10"):
        multi.multi_round_diagnostic(engine_input,raw,manifest,root,review,mapping,
            capture_ids=ids[:1],side="attacker",line=model["line"])
    with pytest.raises(ValueError,match="2-10"):
        multi.multi_round_diagnostic(engine_input,raw,manifest,root,review,mapping,
            capture_ids=ids*6,side="attacker",line=model["line"])
    with pytest.raises(ValueError,match="unique"):
        multi.multi_round_diagnostic(engine_input,raw,manifest,root,review,mapping,
            capture_ids=ids[:1]*2,side="attacker",line=model["line"])
    with pytest.raises(ValueError,match="increasing"):
        multi.multi_round_diagnostic(engine_input,raw,manifest,root,review,mapping,
            capture_ids=ids[::-1],side="attacker",line=model["line"])
    with pytest.raises(ValueError,match="not found"):
        multi.multi_round_diagnostic(engine_input,raw,manifest,root,review,mapping,
            capture_ids=[ids[0],"nonexistent"],side="attacker",line=model["line"])
    (root/"synthetic-0.png").write_bytes(b"tampered")
    with pytest.raises(ValueError):
        multi.multi_round_diagnostic(engine_input,raw,manifest,root,review,mapping,
            capture_ids=ids,side="attacker",line=model["line"])


def test_multi_round_cli_synthetic_actual_engine_and_exclusive_write(
    engine_input,local_synthetic_case,tmp_path,
):
    raw,manifest,root,review,mapping,model,c=_multi_real_case(local_synthetic_case)
    payloads={
        "scenario.json":engine_input,
        "case.json":raw,
        "manifest.json":json.dumps(manifest).encode(),
        "review.json":review,
        "map.json":json.dumps(mapping).encode(),
    }
    for path,data in payloads.items():
        (tmp_path/path).write_bytes(data)
    output=tmp_path/"multi.json"
    cmd=[sys.executable,"-m",
         "tools.research.p0_report_case_multi_round_engine_diagnostic",
         "--scenario",str(tmp_path/"scenario.json"),
         "--case",str(tmp_path/"case.json"),
         "--manifest",str(tmp_path/"manifest.json"),
         "--evidence-root",str(root),
         "--review-worksheet",str(tmp_path/"review.json"),
         "--slot-map",str(tmp_path/"map.json"),
         "--side","attacker","--line",model["line"]]
    for capture in c["rounds"]:
        cmd+=["--capture-id",capture["id"]]
    cmd+=["--output-json",str(output)]
    completed=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
    assert completed.returncode==0,completed.stderr
    saved=json.loads(output.read_text())
    assert saved["global_calibration_allowed"] is False
    assert saved["comparison_evidence_summary"]["unassessable_rows"]==1
    assert saved["comparison_evidence_summary"]["descriptive_numeric_change_rows"]==0
    assert "game_mechanics_verified" in completed.stdout
    second=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
    assert second.returncode==2
    assert "refusing to overwrite" in second.stderr
