"""Official in-game Help Sea Fight screenshots -> independent five-tier geometry.

Do not infer damage-priority column labels from these screenshots: those come
from the separate 2020 empirical mechanics paper and remain revisable.
"""
import json
from pathlib import Path

import pytest

from ikariam_battle.battlefield import NAVAL_BATTLEFIELDS, battlefield, battlefield_metadata, deploy
from ikariam_battle.models import Army, Scenario
from ikariam_battle.units import UnitRegistry


EVIDENCE = Path(__file__).resolve().parents[1] / "fixtures/reverse_engineering/naval_help_geometry_20261013.json"
TIERS = json.loads(EVIDENCE.read_text(encoding="utf-8"))["tiers"]


@pytest.mark.parametrize("tier", TIERS, ids=lambda v: v["id"])
def test_help_screenshot_every_tier_has_exact_slot_count_and_space(tier):
    field = battlefield(tier["id"])
    assert field.domain == "naval"
    assert field.id == tier["id"]
    for line, (slots, slot_space) in tier["lines"].items():
        if slots == 0:
            assert line not in field.lines
            continue
        assert len(field.lines[line].physical_order) == slots
        assert field.lines[line].slot_space == slot_space
        assert len(set(field.lines[line].physical_order)) == slots

    assert set(field.lines) == {
        line for line, (slots, _) in tier["lines"].items() if slots > 0
    }
    assert Scenario.from_dict({
        "battlefield": tier["id"],
        "attacker": {"units": [{"unit_id": "ram_ship", "quantity": 1}]},
        "defender": {"units": [{"unit_id": "ram_ship", "quantity": 1}]},
    }).battlefield == tier["id"]


def test_five_tiers_are_selectable_and_keep_naval_max_id_compatible():
    expected = [x["id"] for x in TIERS]
    assert list(NAVAL_BATTLEFIELDS) == expected
    metas = [x for x in battlefield_metadata() if x["domain"] == "naval"]
    assert [x["id"] for x in metas] == expected
    assert all(x["supported"] is True for x in metas)
    assert [x["help_min_level"] for x in TIERS] == [0, 8, 15, 22, 29]
    assert "GAMEFORGE_HELP" in NAVAL_BATTLEFIELDS["naval-max"].provenance


@pytest.mark.parametrize("tier", TIERS, ids=lambda v: v["id"])
def test_each_field_deploys_light_ram_without_exceeding_its_physical_capacity(tier):
    registry = UnitRegistry.load()
    field = battlefield(tier["id"])
    army = Army.from_dict({"units": [{"unit_id": "ram_ship", "quantity": 36}]})
    waves = deploy(army, registry, field, "formation-naval")
    ram = next(w for w in waves if w.unit.unit_id == "ram_ship")
    total = sum(slot.units for slot in ram.slots)
    assert total + ram.reserve == 36
    for slot in ram.slots:
        assert slot.units <= field.lines[slot.line].slot_space // 3
        assert slot.physical_position == field.lines[slot.line].physical_position(
            slot.damage_position
        )
    if tier["id"] == "naval-mini":
        assert all(slot.line == "first" for slot in ram.slots)
        assert ram.reserve == 21


def test_pure_36_ram_naval_max_fills_first_before_flank_and_is_not_six_flank_slots():
    """Illustrates why a pure Ram-only battle is not the user's six-flank case."""
    registry = UnitRegistry.load()
    ram = deploy(
        Army.from_dict({"units": [{"unit_id": "ram_ship", "quantity": 36}]}),
        registry, NAVAL_BATTLEFIELDS["naval-max"], "formation-naval",
    )[0]
    assert [s.units for s in sorted(ram.slots, key=lambda s: s.damage_position)] == [
        8, 8, 8, 8, 4
    ]
    assert {s.line for s in ram.slots} == {"first"}
    assert ram.reserve == 0


def test_max_help_flank_slot_space_is_20_but_still_six_ram_ships():
    field = NAVAL_BATTLEFIELDS["naval-max"]
    assert field.lines["flank"].slot_space == 20
    assert field.lines["flank"].slot_space // UnitRegistry.load().get("ram_ship").size == 6
    assert field.lines["second"].slot_space == 25


@pytest.mark.parametrize("tier", TIERS, ids=lambda v: v["id"])
def test_each_help_geometry_can_execute_one_complete_naval_round(tier):
    """Supported means executable by the actual shared engine, not metadata-only."""
    from ikariam_battle.engine import simulate

    result = simulate({
        "policy": "experimental",
        "battlefield": tier["id"],
        "max_rounds": 1,
        "attacker": {"units": [{"unit_id": "steam_ram", "quantity": 35}]},
        "defender": {"units": [{"unit_id": "steam_ram", "quantity": 35}]},
    })
    assert result["profiles"]["formation"] == "formation-naval"
    assert any("five Level 0+/8+/15+/22+/29+" in w for w in result["warnings"])
    assert not any("smaller geometries" in w for w in result["warnings"])
    assert result["rounds_completed"] == 1
    assert any(e["type"] == "attacking_matrix" for e in result["events"])
    assert any(s["line"] == "first" for s in result["initial_state"]["attacker"]["slots"])


def test_active_project_state_does_not_reserve_supported_smaller_naval_fields():
    """A regression in the agent handoff is a runtime contract regression."""
    root = Path(__file__).resolve().parents[2]
    memory = (root / ".codex/memory.md").read_text(encoding="utf-8")
    issues = (root / ".codex/known_issues.md").read_text(encoding="utf-8")
    backlog = (root / ".codex/backlog.md").read_text(encoding="utf-8")
    assert "Smaller naval geometries beyond `naval-max`" not in memory
    assert "reject unsupported smaller naval IDs" not in issues
    assert "battlefield execution remains reserved" not in backlog
    assert "All five explicit Gameforge Help naval geometries" in issues
    assert "Geometry implemented; calibration ongoing" in backlog
    # Enabling geometries does not assert any unverified AM or Accuracy formula.
    assert "AM damage-position" in memory
    assert "Accuracy" in issues and "Accuracy" in backlog
