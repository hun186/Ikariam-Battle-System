"""The event trace distinguishes actual screenshot values from model events."""
import re
from tools.research.crispi_round1_damage_trace import build_report


def test_crispi_round1_trace_preserves_evidence_provenance():
    report = build_report()
    assert report["schema_version"] == 1
    assert re.fullmatch(r"[0-9a-f]{40}", report["source_commit_sha"])
    assert report["observed"]["attacker_hoplite_casualties"] == 52
    assert report["legacy_model"]["attacker_hoplite_casualties"] == 94
    current = report["current_model"]
    assert current["delta_observed_minus_model"] == 52 - current["attacker_hoplite_casualties"]
    assert current["rounds_completed"] >= 1


def test_crispi_round1_trace_breaks_down_defender_sources_without_guessing():
    current = build_report()["current_model"]
    assert current["source_events_sum_equals_snapshot"]
    assert not current["defender_first_damage_events"]
    assert {piece["physical_position"] for piece in current["breached_wall_positions"]} == {2, 3, 4, 5, 6}
    assert current["attacker_bombardier_casualties"] == 20
    assert current["defender_bombardier_casualties"] == 30
    assert "sulphur_carabineer" in current["defender_sources_to_attacker_hoplite"]
    assert "mortar" in current["defender_sources_to_attacker_hoplite"]
