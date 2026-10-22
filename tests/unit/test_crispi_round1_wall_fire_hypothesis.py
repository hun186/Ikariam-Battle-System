"""Wall survivor split remains a conditional hypothesis, not battle logic."""
from copy import deepcopy

from ikariam_battle.wall import wall_stats
from tools.research.crispi_round1_damage_trace import (
    CASE_PATH,
    build_report,
    evaluate_surviving_wall_one_kill_hypothesis,
)
import json


def test_current_l24_wall_attack_is_one_shot_capable_but_no_wall_fire_is_modeled():
    # Current published profile: damage gross=5220, Hoplite HP=1120,
    # target's documented defense=100 in this pinned Crispi scenario.
    assert wall_stats(24)["damage"] == 5220
    assert 5220 - 100 >= 1120
    report = build_report()
    assert report["current_model"]["defender_first_damage_events"] == []
    assert report["current_model"]["attacker_hoplite_casualties"] == 44


def test_conditional_surviving_wall_split_exactly_recovers_candidate_pattern():
    report = build_report()
    conditional = report["conditional_wall_fire_hypothesis"]
    rows = conditional["rows"]
    assert conditional["status"] == "UNVERIFIED_CONDITIONAL_DECOMPOSITION"
    assert conditional["wall_kills_total"] == 2
    assert conditional["assumed_mortar_kills_total"] == 20
    assert conditional["inferred_carabineer_kills_total"] == 30
    assert conditional["all_inferred_carabineer_counts_nonnegative"]
    assert [r["hypothesized_wall_kills"] for r in rows] == [1, 0, 0, 0, 0, 0, 1]
    assert [r["assumed_mortar_kills"] for r in rows] == [0, 5, 5, 5, 5, 0, 0]
    assert [r["inferred_carabineer_kills"] for r in rows] == [0, 6, 6, 6, 6, 6, 0]
    assert [r["inferred_minus_modeled_carabineer_kills"] for r in rows] == [
        -2, 2, 2, 2, 2, 2, -2,
    ]
    assert report["current_model"]["defender_sources_to_attacker_hoplite"]["sulphur_carabineer"]["casualties"] == 24


def test_hypothesis_recomputes_on_changed_wall_mask_instead_of_hardcoding_two_kills():
    case = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    matrix = build_report()["physical_hoplite_comparison"]
    altered = deepcopy(case)
    altered["observed"]["wall_alive_physical"] = [0, 0, 0, 0, 0, 0, 1]
    result = evaluate_surviving_wall_one_kill_hypothesis(altered, matrix)
    assert result["wall_kills_total"] == 1
    assert result["inferred_carabineer_kills_total"] == 31
    assert [r["inferred_carabineer_kills"] for r in result["rows"]] == [
        1, 6, 6, 6, 6, 6, 0
    ]


def test_hypothesis_rejects_unordered_or_ambiguous_wall_position_data():
    import pytest

    case = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    matrix = build_report()["physical_hoplite_comparison"]
    altered = deepcopy(matrix)
    altered["positions"] = altered["positions"][::-1]
    with pytest.raises(ValueError, match="ordered physical slots"):
        evaluate_surviving_wall_one_kill_hypothesis(case, altered)

    malformed = deepcopy(case)
    malformed["observed"]["wall_alive_physical"][0] = 2
    with pytest.raises(ValueError, match="0/1 mask"):
        evaluate_surviving_wall_one_kill_hypothesis(malformed, matrix)
