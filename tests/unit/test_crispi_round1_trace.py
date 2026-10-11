"""Crispi trace is derived from the current model, not fixture legacy kills."""
from tools.crispi_round1_trace import run_trace


def test_crispi_model_trace_keeps_three_evidence_layers_separate():
    trace = run_trace()
    assert trace["observed"]["attacker"]["hoplite"] == 52
    assert trace["legacy_model_pre_pr63"]["attacker"]["hoplite"] == 94
    assert trace["attacker_hoplite_gap_observed_minus_model"] == (
        52 - trace["current_model"]["attacker"]["hoplite"]
    )
    assert trace["current_model"]["attacker"]["hoplite"] != 94


def test_crispi_trace_includes_attacks_and_preserves_air_kills():
    trace = run_trace()
    assert trace["current_model"]["defender"]["bombardier"] == 30
    assert trace["current_model"]["attacker"]["bombardier"] == 20
    assert trace["damage_events_by_source"]
    assert trace["event_counts"].get("damage_calculation", 0) > 0
