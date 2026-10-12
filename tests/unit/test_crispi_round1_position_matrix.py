"""Crispi physical-slot gap matrix: observed game values are NOT model events."""
from tools.research.crispi_round1_damage_trace import (
    build_report,
    compare_hoplite_physical_positions,
)


def test_crispi_position_matrix_preserves_observed_and_current_model_separately():
    report = build_report()
    matrix = report["physical_hoplite_comparison"]
    rows = matrix["positions"]

    assert [r["physical_position"] for r in rows] == list(range(1, 8))
    assert [r["observed_hoplite_losses"] for r in rows] == [1, 11, 11, 11, 11, 6, 1]
    assert matrix["observed_total"] == 52
    assert matrix["modeled_total"] == report["current_model"]["attacker_hoplite_casualties"] == 44
    assert matrix["gap_observed_minus_modeled"] == 8
    assert sum(r["gap_observed_minus_modeled"] for r in rows) == 8
    assert not matrix["unmapped_simulator_events"]
    assert matrix["source_losses_equal_each_slot"]
    assert all(r["source_losses_equal_slot"] for r in rows)
    assert sum(
        r["modeled_defender_sources"].get("mortar", {}).get("casualties", 0)
        for r in rows
    ) == 20
    assert sum(
        r["modeled_defender_sources"].get("sulphur_carabineer", {}).get("casualties", 0)
        for r in rows
    ) == 24
    assert all(
        set(r["modeled_defender_sources"]) <= {"mortar", "sulphur_carabineer"}
        for r in rows
    )


def test_physical_positions_are_not_confused_with_am_damage_positions():
    from tools.research.crispi_round1_damage_trace import CASE_PATH
    import json

    case = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    rows = [
        {
            "line": "first", "unit_id": "hoplite",
            "physical_position": i, "damage_position": 8 - i,
            "casualties": 1 if i == 1 else 0,
            "units": 49, "damage": 0,
        }
        for i in range(1, 8)
    ]
    events = [{
        "target_damage_position": 7,
        "source_unit_id": "mortar",
        "casualties": 1, "shots": 1, "net_damage": 1120,
    }]
    matrix = compare_hoplite_physical_positions(
        case, {"attacker": {"slots": rows}}, events,
    )
    assert matrix["positions"][0]["model_damage_position"] == 7
    assert matrix["positions"][0]["modeled_defender_sources"]["mortar"]["casualties"] == 1
    assert matrix["positions"][-1]["model_damage_position"] == 1
    assert matrix["source_losses_equal_each_slot"]
    assert not matrix["unmapped_simulator_events"]


def test_an_unmapped_damage_event_is_reported_not_silently_redistributed():
    from tools.research.crispi_round1_damage_trace import CASE_PATH
    import json

    case = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    rows = [
        {
            "line": "first", "unit_id": "hoplite",
            "physical_position": i, "damage_position": i, "casualties": 0,
        }
        for i in range(1, 8)
    ]
    matrix = compare_hoplite_physical_positions(
        case, {"attacker": {"slots": rows}},
        [{"target_damage_position": 99, "source_unit_id": "mortar", "casualties": 1}],
    )
    assert len(matrix["unmapped_simulator_events"]) == 1
    assert matrix["unmapped_simulator_events"][0]["target_damage_position"] == 99
    assert matrix["modeled_total"] == 0


def test_crispi_current_position_baseline_tracks_signed_gap_not_just_total():
    """Intentional CURRENT-MODEL baseline, not a claim about real-game shots.

    A future evidence-supported calibration can update this assertion together
    with its independent references and the strict empirical xfail.
    """
    comparison = build_report()["physical_hoplite_comparison"]
    rows = comparison["positions"]
    assert [r["model_damage_position"] for r in rows] == [6, 4, 2, 1, 3, 5, 7]
    assert [r["modeled_hoplite_losses"] for r in rows] == [2, 9, 9, 9, 9, 4, 2]
    assert [r["gap_observed_minus_modeled"] for r in rows] == [-1, 2, 2, 2, 2, 2, -1]

    mortars = [
        r["modeled_defender_sources"].get("mortar", {}).get("casualties", 0)
        for r in rows
    ]
    carabineers = [
        r["modeled_defender_sources"].get("sulphur_carabineer", {}).get("casualties", 0)
        for r in rows
    ]
    carabineer_shots = [
        r["modeled_defender_sources"].get("sulphur_carabineer", {}).get("shots", 0)
        for r in rows
    ]
    assert mortars == [0, 5, 5, 5, 5, 0, 0]
    assert carabineers == [2, 4, 4, 4, 4, 4, 2]
    assert carabineer_shots == [7, 14, 14, 14, 14, 14, 7]
    assert sum(carabineer_shots) == 84
