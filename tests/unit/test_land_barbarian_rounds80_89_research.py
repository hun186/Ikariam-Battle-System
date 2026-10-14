"""Provenance-aware land battle screenshots, rounds 80-89.

These tests check user-confirmed *visible results*, not implementation of an
unsupported Gameforge land Accuracy rule. No per-unit shot logs exist.
"""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/reverse_engineering/land_barbarian_rounds80_89_20261014.json"


def evidence():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_screenshot_series_and_verified_per_round_deaths():
    data = evidence()
    obs = data["observations"]
    assert len(obs) == 10
    assert [r["round"] for r in obs] == list(range(80, 90))
    assert data["source"]["user_confirmed_at_followup"]
    assert [r["attacker_barbarian_main_line_deaths_left_to_right"] for r in obs] == [
        [3, 3, 3, 4, 3, 3, 0],
        [8, 15, 15, 8, 15, 15, 8],
        [8, 15, 15, 8, 15, 15, 8],
        [8, 15, 15, 8, 15, 15, 8],
        [15, 15, 15, 5, 15, 15, 8],
        [15, 15, 15, 5, 15, 15, 8],
        [15, 15, 15, 6, 15, 15, 8],
        [15, 15, 15, 5, 15, 15, 8],
        [16, 15, 15, 15, 15, 15, None],
        [None, 25, 22, 22, 22, None, None],
    ]
    assert [r["attacker_barbarian_main_line_total_round_deaths"] for r in obs] == [
        19, 84, 84, 84, 88, 88, 89, 88, 91, 91
    ]
    assert sum(r["attacker_barbarian_main_line_total_round_deaths"] for r in obs) == 806
    assert all(
        r["attacker_barbarian_main_line_total_round_deaths"]
        == sum(x for x in r["attacker_barbarian_main_line_deaths_left_to_right"]
               if x is not None)
        for r in obs
    )
    assert obs[8]["attacker_barbarian_main_line_deaths_left_to_right"][-1] is None
    assert obs[9]["attacker_barbarian_main_line_deaths_left_to_right"][0] is None


def test_center_special_unit_depletes_without_an_observed_refill():
    seq = evidence()["observations"][:8]
    remaining = [r["central_position_4_axe_bearer_remaining_units"] for r in seq]
    deaths = [r["central_position_4_axe_bearer_deaths"] for r in seq]
    assert remaining == [45, 37, 29, 21, 16, 11, 5, 0]
    assert deaths == [4, 8, 8, 8, 5, 5, 6, 5]
    assert sum(deaths) == 49
    assert remaining[0] + deaths[0] == 49
    assert all(remaining[i] - remaining[i+1] == deaths[i+1]
               for i in range(len(remaining)-1))
    assert all(r["central_position_4_axe_bearer_remaining_units"] is None
               for r in evidence()["observations"][8:])


def test_reserve_decrements_correlate_with_other_melee_deaths_but_are_not_game_telemetry():
    obs = evidence()["observations"]
    reserves = [r["ordinary_melee_reserve_count"] for r in obs]
    assert reserves == [310, 535, 459, 383, 307, 224, 141, 58, 0, 0]
    ordinary = [
        r["attacker_barbarian_main_line_total_round_deaths"]
        - r["central_position_4_axe_bearer_deaths"]
        for r in obs[1:8]
    ]
    assert ordinary == [76, 76, 76, 83, 83, 83, 83]
    # Between snapshot 81->82, 82->83 ... 86->87, reserve falls by
    # exactly previous-round non-axe losses. Snapshot 80->81 rises 225.
    assert [reserves[i]-reserves[i+1] for i in range(1,7)] == ordinary[:6]
    assert reserves[1] - reserves[0] == 225
    assert reserves[7] - reserves[8] == 58
    assert reserves[7] < ordinary[6]
    assert all(r["ordinary_melee_reserve_count_source"].startswith("SCREENSHOT_")
               for r in obs)
    assert evidence()["source"]["screenshot_binary_present_in_repository"] is False


def test_player_round80_and_hp_bars_are_source_separated():
    data = evidence()
    obs = data["observations"]
    assert data["player_musketeer_upgrade"] == {"attack": 11, "armor": 3}
    assert (obs[0]["defender_player_main_line_deaths_total"],
            obs[0]["defender_player_siege_deaths_total"]) == (84, 19)
    assert all(r["defender_player_main_line_deaths_total"] == 0
               and r["defender_player_siege_deaths_total"] == 0 for r in obs[1:])
    assert [r["attacker_main_line_front_survivor_hp_percent_left_to_right"][3]
            for r in obs[:8]] == [99, 99, 99, 99, 97, 92, 96, 0]
    assert all(r["hp_percent_source"] == "USER_EXPLICIT_TEXT" for r in obs)
    assert all(
        (hp == 100) for row in obs[8:]
        for hp in row["attacker_main_line_front_survivor_hp_percent_left_to_right"]
        if hp is not None
    )
    assert len(data["source"]["battle_report_screenshot_filenames_in_chat"]) == 10
    assert "Original complete player army including every source firing or using ammunition" in data["source"]["importantly_not_confirmed"]


def test_empty_and_post_wall_formations_are_not_interpreted_as_zero_casualties():
    data = evidence()
    obs = data["observations"]
    assert obs[0]["barrier_context_image_inference"] == "open_field"
    assert all(x["barrier_context_image_inference"] == "town_wall_present"
               for x in obs[1:])
    assert [sum(x is not None for x in r["attacker_barbarian_main_line_deaths_left_to_right"])
            for r in obs[-3:]] == [7, 6, 4]
    # A rise from 92 to 96 percent while shrinking 11 -> 5 individuals
    # is NOT proof of healing: wounded soldiers could have died.
    assert obs[5]["attacker_main_line_front_survivor_hp_percent_left_to_right"][3] == 92
    assert obs[6]["attacker_main_line_front_survivor_hp_percent_left_to_right"][3] == 96
    assert obs[5]["central_position_4_axe_bearer_remaining_units"] == 11
    assert obs[6]["central_position_4_axe_bearer_remaining_units"] == 5


def test_future_agents_can_recover_land_case_without_mixing_naval_studies():
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    memory = (ROOT / ".codex/memory.md").read_text(encoding="utf-8")
    backlog = (ROOT / ".codex/backlog.md").read_text(encoding="utf-8")
    doc_path = ROOT / "docs/calibration/land-barbarian-rounds80-89-inverse-study.md"
    doc = doc_path.read_text(encoding="utf-8")
    # Routers must link to the document; the document need not link to itself.
    for source in (agents, memory, backlog):
        assert "land-barbarian-rounds80-89-inverse-study.md" in source
    assert "rounds 80–89" in doc
    assert "land_barbarian_rounds80_89_20261014.json" in agents
    assert "land_barbarian_rounds80_89_20261014.json" in memory
    assert "land_barbarian_rounds80_89_20261014.json" in doc
    assert "Issue #71" in doc
    assert "NAVAL" in doc and "NOT" in doc
    assert not evidence()["source"]["screenshot_binary_present_in_repository"]


def test_visible_seven_groups_of_twelve_do_not_suffice_under_naive_one_shot_one_kill():
    """A deliberately narrow hypothetical, NOT the game's source shot log."""
    observed = evidence()["observations"]
    visible_player_units = 7 * 12
    assert visible_player_units == 84
    assert [r["attacker_barbarian_main_line_total_round_deaths"] for r in observed[1:4]] == [84]*3
    assert [r["attacker_barbarian_main_line_total_round_deaths"] for r in observed[4:]] == [88, 88, 89, 88, 91, 91]
    assert all(r["attacker_barbarian_main_line_total_round_deaths"] > visible_player_units
               for r in observed[4:])
    # The fixture never labels 84 units as the entire damage-dealing army:
    # wall/other units, ammo phases and weapon identities remain unverified.
    assert "Original complete player army including every source firing or using ammunition" in evidence()["source"]["importantly_not_confirmed"]
