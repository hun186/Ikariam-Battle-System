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
    assert one["count_difference"] is None
    assert one["hp_percentage_point_difference"] is None
    assert one["diagnostic_status"].startswith("NOT_ASSESSABLE_")
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
