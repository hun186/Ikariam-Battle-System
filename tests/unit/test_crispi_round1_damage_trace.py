"""The event trace distinguishes actual screenshot values from model events."""
import re
from tools.research.crispi_round1_damage_trace import build_report


def test_crispi_round1_trace_preserves_evidence_provenance():
    report = build_report(source_commit_sha="a" * 40)
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


def test_uncommitted_development_can_build_report_without_revision(monkeypatch):
    from tools.research import crispi_round1_damage_trace as trace

    def should_not_resolve():
        raise AssertionError("build_report must not inspect Git status")

    monkeypatch.setattr(trace, "resolve_revision", should_not_resolve)
    report = trace.build_report()
    assert report["source_commit_sha"] is None
    assert report["current_model"]["attacker_hoplite_casualties"] == 44


def test_unified_trace_keeps_wall_firing_separate_from_breach_outcomes():
    current = build_report()["current_model"]
    assert current["event_counts"]["wall_damage"] == 30
    assert len(current["wall_damage_events"]) == 30
    assert len(current["raw_damage_events_by_source"]["attacker/mortar/wall_damage"]) == 30
    assert all(
        shot["side"] == "attacker"
        and shot["details"]["source_unit_id"] == "mortar"
        for shot in current["wall_damage_events"]
    )
    assert len(current["wall_breach_outcomes"]) == 5
    assert {
        outcome["details"]["physical_position"]
        for outcome in current["wall_breach_outcomes"]
    } == {2, 3, 4, 5, 6}
    assert not any(
        "wall_section_breached" in key
        for key in current["raw_damage_events_by_source"]
    )


def test_unified_trace_retains_round_slot_casualties_and_source_matrix():
    report = build_report()
    current = report["current_model"]
    assert current["slot_losses"]["attacker"]
    assert current["slot_losses"]["defender"]
    assert all(
        slot["casualties"] > 0 and slot["physical_position"] is not None
        for slot in current["slot_losses"]["attacker"]
    )
    assert current["source_events_sum_equals_snapshot"]
    assert current["attacker_hoplite_casualties"] == 44
    assert report["observed"]["attacker_hoplite_casualties"] == 52
    assert current["delta_observed_minus_model"] == 8
    assert len(current["raw_damage_events_by_source"]["defender/mortar/damage"]) > 0


def test_generated_trace_output_is_ignored_but_evidence_fixture_is_not():
    """Local artifact reruns may overwrite JSON without hiding source changes."""
    import subprocess
    from tools.research import crispi_round1_damage_trace as trace

    def ignored(path):
        return subprocess.run(
            ["git", "check-ignore", "--quiet", "--no-index", path],
            cwd=trace.ROOT, check=False,
        ).returncode == 0

    assert ignored("research-output/crispi_r1_current_trace.json")
    assert not ignored("tests/fixtures/reverse_engineering/crispi_round1.json")
    assert not ignored("tools/research/crispi_round1_damage_trace.py")
