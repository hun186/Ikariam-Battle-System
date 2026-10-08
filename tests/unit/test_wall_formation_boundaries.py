"""Town Wall occupies First and blocks both Flanks until the *next* round."""
from ikariam_battle import simulate


def _case(*, wall=24, hall=25, rounds=2, attackers_mortar=30):
    return {
        "policy": "experimental", "battlefield": "land-max",
        "max_rounds": rounds, "wall_level": wall,
        "town_hall_level": hall,
        "attacker": {
            "forge_level": 5,
            "units": [
                {"unit_id": "hoplite", "quantity":350},
                {"unit_id": "swordsman", "quantity":160},
                {"unit_id": "mortar", "quantity":attackers_mortar,
                 "attack_upgrade":7},
            ],
        },
        "defender": {
            "forge_level": 0,
            "units": [
                {"unit_id": "hoplite", "quantity":350},
                {"unit_id": "swordsman", "quantity":160},
                {"unit_id": "sulphur_carabineer", "quantity":84},
                {"unit_id": "mortar", "quantity":30},
            ],
        },
    }


def _live_line(row, side, line):
    return [
        slot for slot in row[side]["slots"]
        if slot["line"] == line and slot["units"] > 0
    ]


def test_initial_active_wall_occupies_first_and_blocks_both_flanks():
    result = simulate(_case(rounds=1))
    assert result["garrison_status"]["open_field"] is False
    assert not _live_line(result["rounds"][0], "defender", "first")
    assert not _live_line(result["rounds"][0], "defender", "flank")
    assert not _live_line(result["rounds"][0], "attacker", "flank")
    assert result["rounds"][0]["defender"]["reserve"]["hoplite"] >= 350
    assert not [
        e for e in result["events"]
        if e["round"] == 0 and e["type"] == "deployment"
        and (e["details"].get("line") == "flank"
             or (e["side"] == "defender" and e["details"].get("line") == "first"))
    ]
    assert not _live_line(result["rounds"][1], "defender", "first")
    assert not [
        e for e in result["events"]
        if e["round"] == 1 and e["side"] == "defender"
        and e["type"] == "damage"
        and e["details"].get("firing_phase") == "first"
    ]


def test_wall_breach_fills_defender_first_only_after_round_boundary():
    result = simulate(_case(rounds=2))
    breached = {
        e["details"]["damage_position"] for e in result["events"]
        if e["round"] == 1 and e["type"] == "wall_section_breached"
    }
    assert breached and len(breached) < 7
    assert result["rounds_completed"] >= 2
    assert not _live_line(result["rounds"][1], "defender", "first")
    first = _live_line(result["rounds"][2], "defender", "first")
    assert first
    assert {slot["damage_position"] for slot in first} <= breached
    assert not _live_line(result["rounds"][2], "defender", "flank")
    assert not _live_line(result["rounds"][2], "attacker", "flank")
    assert any(
        e["round"] == 2 and e["type"] == "deployment"
        and e["details"].get("reason") == "wall_gap_next_round"
        for e in result["events"]
    )


def test_full_wall_breach_opens_flanks_only_at_following_round_start():
    s = _case(wall=1, hall=40, rounds=2)
    result = simulate(s)
    assert result["garrison_status"]["open_field"] is False
    breaches = [
        e for e in result["events"]
        if e["round"] == 1 and e["type"] == "wall_section_breached"
    ]
    assert len(breaches) == 7
    for side in ("attacker", "defender"):
        assert not _live_line(result["rounds"][1], side, "flank")
    assert result["rounds_completed"] >= 2
    for side in ("attacker", "defender"):
        assert _live_line(result["rounds"][2], side, "flank")
        assert any(
            e["round"] == 2 and e["side"] == side
            and e["type"] == "deployment"
            and e["details"].get("reason") == "wall_all_breached_previous_round"
            for e in result["events"]
        )


def test_open_field_suppressed_wall_allows_initial_flank():
    s = _case(wall=1, hall=1, rounds=1)
    # Force the garrison above 250+50*(Town Hall + Wall)=350.
    s["defender"]["units"][0]["quantity"] = 1400
    result = simulate(s)
    assert result["garrison_status"]["open_field"] is True
    assert _live_line(result["rounds"][0], "attacker", "flank")
    assert _live_line(result["rounds"][0], "defender", "flank")
