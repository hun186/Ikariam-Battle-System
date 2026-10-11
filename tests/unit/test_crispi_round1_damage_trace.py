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


def test_local_trace_revision_rejects_dirty_checkout(monkeypatch):
    import pytest
    from tools.research import crispi_round1_damage_trace as trace

    monkeypatch.delenv("GITHUB_SHA", raising=False)
    calls = []

    def fake_check_output(command, **kwargs):
        calls.append(command)
        if command[1] == "status":
            return "?? potentially_shadowing_module.py\n"
        raise AssertionError("Dirty checkout must not claim a commit revision")

    monkeypatch.setattr(trace.subprocess, "check_output", fake_check_output)
    with pytest.raises(RuntimeError, match="dirty worktree"):
        trace.resolve_revision()
    assert len(calls) == 1
    assert calls[0] == ["git", "status", "--porcelain", "--untracked-files=all"]


def test_local_clean_trace_revision_reads_git_head(monkeypatch):
    from tools.research import crispi_round1_damage_trace as trace

    monkeypatch.delenv("GITHUB_SHA", raising=False)
    revision = "a" * 40
    commands = []

    def fake_check_output(command, **kwargs):
        commands.append(command)
        return "" if command[1] == "status" else revision + "\n"

    monkeypatch.setattr(trace.subprocess, "check_output", fake_check_output)
    assert trace.resolve_revision() == revision
    assert [cmd[1] for cmd in commands] == ["status", "rev-parse"]
