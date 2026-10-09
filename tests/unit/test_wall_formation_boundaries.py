"""Town Wall occupies First and blocks both Flanks until the *next* round."""
from ikariam_battle import simulate
from ikariam_battle.battlefield import LAND_BATTLEFIELDS
from ikariam_battle.engine import _redistribute, _event, _supported_whole_wave_first_fallback
from ikariam_battle.formation import FormationRules
from ikariam_battle.models import ArmyUnit, Wave
from ikariam_battle.units import UnitRegistry
from ikariam_battle.wall import initial_wall_sections
from ikariam_battle.wall_formation import deploy_prior_round_wall_vacancies


def _case(*, wall=24, hall=25, rounds=2, attackers_mortar=30):
    return {
        "policy": "experimental", "battlefield": "land-max",
        "max_rounds": rounds, "wall_level": wall,
        "town_hall_level": hall,
        "attacker": {
            "forge_level": 5,
            "units": [
                {"unit_id": "hoplite", "quantity":700},
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


def test_competing_wall_gap_reinforcement_remains_an_explicit_unknown():
    s = _case(rounds=2)
    s["defender"]["units"].append({
        "unit_id": "steam_giant", "quantity":10,
        "entry_batch_id": "additional-first-wave", "arrival_round":1,
    })
    result = simulate(s)
    unresolved = [
        event for event in result["events"]
        if event["type"] == "unsupported_mechanic"
        and event["details"].get("rule_id") == "UNKNOWN-CROSS-WAVE-FORMATION-REBUILD"
        and any(item.get("reason") == "competing_wall_gap_native_waves"
                for item in event["details"].get("requirements", []))
    ]
    assert unresolved
    assert unresolved[0]["round"] == 2
    assert result["status"] == "inconclusive"


def test_newly_occupied_wall_gap_receives_existing_reserve_damage():
    registry = UnitRegistry.load()
    rules = FormationRules.load()
    field = LAND_BATTLEFIELDS["land-max"]
    sections = initial_wall_sections(24, field)
    sections[0].destroyed = True
    # The prior round's persistent damage belongs to this one state wave.
    wave = Wave(ArmyUnit("hoplite", 50), 50, [], 1120)
    events = []
    conflicts, placed = deploy_prior_round_wall_vacancies(
        [wave], registry, rules, field, sections, 2, "defender", events, _event,
    )
    assert conflicts == [] and placed is True
    assert wave.reserve == 0 and sum(slot.units for slot in wave.slots) == 50
    _redistribute([wave], events, 2, "defender", {})
    assert wave.reserve_damage == 0
    assert sum(slot.damage for slot in wave.slots) == 1120
    assert sum(slot.damage for slot in wave.slots) + wave.reserve_damage == 1120


def test_native_front_reserve_claims_all_wall_gaps_before_carabineer_fallback():
    # The reported P1: even though the Long-Range wave is out of shots, seven
    # already breached Town Wall slots must go first to native Hoplites.
    registry = UnitRegistry.load()
    rules = FormationRules.load()
    field = LAND_BATTLEFIELDS["land-max"]
    sections = initial_wall_sections(24, field)
    for section in sections:
        section.destroyed = True
    native = Wave(ArmyUnit("hoplite", 700), 700, [])
    exhausted = Wave(ArmyUnit("sulphur_carabineer", 84),
                     84, [], 0, 0)
    waves = [native, exhausted]
    events = []

    conflicts, placed = deploy_prior_round_wall_vacancies(
        waves, registry, rules, field, sections, 4, "defender",
        events, _event,
    )
    assert conflicts == [] and placed
    assert {slot.damage_position for slot in native.slots} == set(range(1, 8))
    assert sum(slot.units for slot in native.slots) == 350
    assert native.reserve == 350
    assert _supported_whole_wave_first_fallback(
        waves, registry, rules, field, events, 4, "defender",
        allowed_first_positions={
            section.damage_position for section in sections if section.destroyed
        },
    ) is False
    assert not any(slot.line == "first" and slot.units > 0
                   for slot in exhausted.slots)
    assert exhausted.reserve == 84


def test_fallback_only_uses_residual_breached_front_after_native_priority():
    registry = UnitRegistry.load()
    rules = FormationRules.load()
    field = LAND_BATTLEFIELDS["land-max"]
    sections = initial_wall_sections(24, field)
    for section in sections:
        section.destroyed = True
    native = Wave(ArmyUnit("hoplite", 250), 250, [])
    exhausted = Wave(ArmyUnit("sulphur_carabineer", 84),
                     84, [], 0, 0)
    waves = [native, exhausted]
    events = []
    conflicts, placed = deploy_prior_round_wall_vacancies(
        waves, registry, rules, field, sections, 4, "defender",
        events, _event,
    )
    assert conflicts == [] and placed
    assert {slot.damage_position for slot in native.slots} == {1,2,3,4,5}
    assert _supported_whole_wave_first_fallback(
        waves, registry, rules, field, events, 4, "defender",
        allowed_first_positions={
            section.damage_position for section in sections if section.destroyed
        },
    ) is False
    native_positions = {slot.damage_position for slot in native.slots if slot.units}
    fallback_positions = {
        slot.damage_position for wave in waves
        if wave.unit.unit_id == "sulphur_carabineer"
        for slot in wave.slots if slot.line == "first" and slot.units
    }
    assert native_positions == {1,2,3,4,5}
    assert fallback_positions and fallback_positions <= {6,7}
    assert fallback_positions.isdisjoint(native_positions)


def test_fallback_cannot_enter_intact_wall_position_after_partial_breach():
    registry = UnitRegistry.load()
    rules = FormationRules.load()
    field = LAND_BATTLEFIELDS["land-max"]
    sections = initial_wall_sections(24, field)
    for section in sections[:-1]:
        section.destroyed = True
    native = Wave(ArmyUnit("hoplite", 250), 250, [])
    exhausted = Wave(ArmyUnit("sulphur_carabineer", 84),
                     84, [], 0, 0)
    waves = [native, exhausted]
    events = []
    conflicts, placed = deploy_prior_round_wall_vacancies(
        waves, registry, rules, field, sections, 3, "defender",
        events, _event,
    )
    assert conflicts == [] and placed
    breached = {section.damage_position for section in sections if section.destroyed}
    intact = {section.damage_position for section in sections if not section.destroyed}
    assert _supported_whole_wave_first_fallback(
        waves, registry, rules, field, events, 3, "defender",
        allowed_first_positions=breached,
    ) is False
    first_positions = {
        slot.damage_position for wave in waves
        for slot in wave.slots if slot.line == "first" and slot.units
    }
    assert first_positions <= breached
    assert first_positions.isdisjoint(intact)
