"""Wall-versus-musket source separation, conditional model (not official rules)."""
import json

from tools.research.land_round80_89_wall_source_probe import (
    FIXTURE, build_report, hypothetical_wall_kills_by_slot,
)


def test_user_confirmed_single_wall_attack_is_lethal_but_targeting_unknown():
    original = json.loads(FIXTURE.read_text(encoding="utf-8"))
    wall = original["wall_attack_followup"]
    assert wall["user_confirmed_high_level_wall"]
    assert wall["user_confirmed_each_effective_wall_hit_kills_one_barbarian"]
    assert wall["wall_target_position_distribution_not_verified"]
    assert wall["actually_fired_once_per_section_per_round_not_verified"]
    assert wall["wall_accuracy_and_damage_phase_not_verified"]
    assert original["source"]["user_confirmed_at_followup"]
    assert build_report()["official_wall_target_selection_algorithm_verified"] is False


def test_wall_and_84_musket_source_totals_are_not_naively_equated_to_observed():
    rounds = {x["round"]:x for x in build_report()["rounds"]}
    assert rounds[80]["wall_shot_kill_model"] is None
    assert rounds[80]["cannot_compare_to_7_walled_84_gun_budget"]
    assert [(r, rounds[r]["observed_total_deaths"],
             rounds[r]["wall_total_kills_IF_ALL_SEVEN_FIRE"],
             rounds[r]["derived_musket_kill_total"],
             rounds[r]["derived_musket_kill_total_minus_84_modeled_shots"])
            for r in range(81,90)] == [
        (81,84,7,77,-7),
        (82,84,7,77,-7),
        (83,84,7,77,-7),
        (84,88,7,81,-3),
        (85,88,7,81,-3),
        (86,89,7,82,-2),
        (87,88,7,81,-3),
        (88,91,7,84,0),
        (89,91,7,84,0),
    ]
    assert all(rounds[r]["hypothetical_musket_AM_addresses"]
               for r in range(81,90))
    assert all(sum(rounds[r]["hypothetical_wall_slot_kills_NOT_OBSERVED"].values())==7
               for r in range(81,90))


def test_per_slot_wall_one_kill_each_exposes_an_attack_reassignment_constraint():
    cases = {x["round"]:x for x in build_report()["rounds"]}
    for r in (81,82,83):
        assert list(cases[r]["hypothetical_wall_slot_kills_NOT_OBSERVED"].values()) == [1]*7
        assert list(cases[r]["derived_musket_kills_after_subtracting_wall_NOT_OBSERVED"].values()) == [
            7,14,14,7,14,14,7
        ]
        assert list(cases[r]["derived_musket_kills_minus_frozen_AM_address_NOT_REAL_HITS"].values()) == [
            0,0,0,-7,0,0,0
        ]
    for r in (84,85,87):
        assert list(cases[r]["derived_musket_kills_minus_frozen_AM_address_NOT_REAL_HITS"].values()) == [
            7,0,0,-10,0,0,0
        ]
        assert not cases[r]["all_slot_derived_musket_kills_within_frozen_AM_addresses"]
    assert list(cases[86]["derived_musket_kills_minus_frozen_AM_address_NOT_REAL_HITS"].values()) == [
        7,0,0,-9,0,0,0
    ]


def test_depleted_target_slots_expose_distinct_wall_targeting_hypotheses():
    cases = {x["round"]:x for x in build_report()["rounds"]}
    assert hypothetical_wall_kills_by_slot([1,2,3,4,5,6]) == {
        1:2,2:1,3:1,4:1,5:1,6:1
    }
    assert hypothetical_wall_kills_by_slot([2,3,4,5]) == {2:4,3:1,4:1,5:1}
    assert cases[88]["derived_musket_kills_minus_frozen_AM_address_NOT_REAL_HITS"] == {
        1:0,2:0,3:0,4:0,5:0,6:0
    }
    assert cases[89]["derived_musket_kills_minus_frozen_AM_address_NOT_REAL_HITS"] == {
        2:0,3:0,4:0,5:0
    }
    # A competing assumption that wall source also follows Land AM physical
    # damage priority DOES NOT give these zero residuals. Neither is official.
    # _shot_rows([1]*7) emits seven first-row addresses, NOT rows 1..7.
    # Under the ordinary target address priority all hypothetical wall hits
    # focus the central physical position 4. This does NOT establish wall
    # uses that attacking matrix in the original game.
    assert cases[88]["alternate_wall_same_AM_target_policy_NOT_OFFICIAL"] == {
        1:0,2:0,3:0,4:7,5:0,6:0
    }
    assert cases[88]["alternate_wall_AM_derived_gun_kills_minus_musket_AM"] == {
        1:2,2:1,3:1,4:-6,5:1,6:1
    }
    assert cases[89]["alternate_wall_same_AM_target_policy_NOT_OFFICIAL"] == {
        2:0,3:0,4:7,5:0
    }
    assert cases[89]["alternate_wall_AM_derived_gun_kills_minus_musket_AM"] == {
        2:4,3:1,4:-6,5:1
    }
    for r in (81,82,83):
        assert cases[r]["alternate_wall_same_AM_target_policy_NOT_OFFICIAL"] == {
            1:0,2:0,3:0,4:7,5:0,6:0,7:0
        }


def test_wall_budget_cannot_rescue_fixed_musket_addressing_on_rounds84_to87():
    """Seven kills cannot cover 13 positive per-slot deficits at R84-87.

    This is conditional on 84 modeled guns, <=1 kill per gun attack, and
    at most 7 one-kill wall shots; it does not identify what replaces them.
    """
    cases = {r["round"]:r for r in build_report()["rounds"]}
    for round_number in (84,85,86,87):
        row = cases[round_number]
        assert row[
            "required_kills_beyond_fixed_musket_AM_before_assigning_walls_by_position"
        ] == {1:8,2:1,3:1,4:0,5:1,6:1,7:1}
        assert row[
            "minimum_kills_requiring_other_gun_addresses_or_other_sources_even_if_seven_wall_kills"
        ] == 6
        assert row["fixed_musket_AM_plus_any_seven_wall_kill_distribution_is_sufficient"] is False
    for round_number, expected in [(81,6),(82,6),(83,6),(88,7),(89,7)]:
        row=cases[round_number]
        assert sum(row[
            "required_kills_beyond_fixed_musket_AM_before_assigning_walls_by_position"
        ].values()) == expected
        assert row["minimum_kills_requiring_other_gun_addresses_or_other_sources_even_if_seven_wall_kills"] == 0
        assert row["fixed_musket_AM_plus_any_seven_wall_kill_distribution_is_sufficient"]


def test_wall_sensitivity_is_experimental_not_misreported_as_game_trace():
    r = build_report()
    assert r["evidence_class"] == "RESEARCH_ONLY_WALL_AND_GUN_TWO_SOURCE_HYPOTHETICAL_DECOMPOSITION"
    assert r["source_count_assumptions_not_game_shot_log"]["musket_model_shots_total"] == 84
    assert r["source_count_assumptions_not_game_shot_log"]["wall_sections_visible_in_walled_rounds"] == 7
    assert r["source_count_assumptions_not_game_shot_log"]["wall_target_distribution_is_UNOBSERVED"]
    assert r["owner_verified_source"]["user_confirmed_at_followup"]
    assert all(
        "Wall single-hit lethal effect is user stated" in x["evidence_limits"]
        for x in r["rounds"] if x["round"] != 80
    )
