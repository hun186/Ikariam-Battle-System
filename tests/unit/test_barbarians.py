from decimal import Decimal
import pytest
from ikariam_battle.barbarians import BarbarianFleetRegistry, BarbarianRegistry
from ikariam_battle.models import ScenarioError
from ikariam_battle.units import UnitRegistry


IDS = {
    "barbarian_clubman",
    "barbarian_axe_swinger",
    "barbarian_knifeman",
    "barbarian_axe_thrower",
    "barbarian_war_walker",
    "barbarian_ram",
    "barbarian_catapult",
    "barbarian_dirigible",
    "barbarian_fighter",
}


def test_barbarian_catalog_is_separate_but_simulator_ready():
    registry = BarbarianRegistry.load()
    assert {unit.id for unit in registry.all()} == IDS
    assert registry.metadata["simulation_status"] == "LAND_COMBAT_READY"
    assert registry.metadata["selectable_by_player"] is False
    assert registry.metadata["selectable_in_simulator"] is True
    public = [unit.public() for unit in registry.all()]
    assert all(row["selectable_by_player"] is False for row in public)
    assert all(row["selectable_in_simulator"] is True for row in public)
    assert all(row["simulation_ready"] is True for row in public)
    assert all(row["domain"] == "land" and row["army_kind"] == "barbarian" for row in public)
    assert all(row["general_score"] == "0" and row["resource_cost_basis_total"] == 0 for row in public)


def test_barbarian_lines_and_first_appearance_levels():
    registry = BarbarianRegistry.load()
    expected = {
        "barbarian_clubman": ("first", 1),
        "barbarian_ram": ("third", 10),
        "barbarian_axe_swinger": ("first", 20),
        "barbarian_knifeman": ("flank", 30),
        "barbarian_axe_thrower": ("second", 40),
        "barbarian_catapult": ("third", 40),
        "barbarian_war_walker": ("first", 50),
        "barbarian_dirigible": ("balloon", 50),
        "barbarian_fighter": ("anti-balloon", 50),
    }
    assert {unit.id: (unit.native_line, unit.first_appearance_level) for unit in registry.all()} == expected
    assert registry.get("barbarian_clubman").last_appearance_level == 22


def test_barbarian_current_catalog_stats_are_official_help_verified():
    registry = BarbarianRegistry.load()
    expected = {
        "barbarian_clubman": (240, 20, 60, 1, [(100,85,None)]),
        "barbarian_axe_swinger": (1120, 20, 60, 1, [(360,90,None)]),
        "barbarian_knifeman": (360, 0, 60, 1, [(200,90,None)]),
        "barbarian_axe_thrower": (320, 0, 60, 1, [(200,30,7),(100,60,None)]),
        "barbarian_war_walker": (3680, 60, 40, 3, [(840,80,None)]),
        "barbarian_ram": (1400, 20, 40, 5, [(2100,20,None),(200,20,None)]),
        "barbarian_catapult": (640, 0, 40, 5, [(5400,20,5),(200,20,None)]),
        "barbarian_dirigible": (800, 0, 20, 2, [(960,20,2)]),
        "barbarian_fighter": (580, 0, 80, 1, [(340,80,4)]),
    }
    actual = {
        unit.id: (
            unit.hit_points, unit.base_armor, unit.speed, unit.size,
            [(w.damage,w.accuracy,w.ammunition) for w in unit.weapons],
        )
        for unit in registry.all()
    }
    assert actual == expected
    assert all(
        unit.provenance["confidence"] == "OFFICIAL_HELP_COMBAT_STATS"
        for unit in registry.all()
    )


def test_combat_registry_can_opt_in_barbarian_definitions():
    player_only = UnitRegistry.load()
    with pytest.raises(ScenarioError, match="unsupported unit_id"):
        player_only.get("barbarian_clubman")
    combined = UnitRegistry.load(include_barbarians=True)
    clubman = combined.get("barbarian_clubman")
    assert clubman.army_kind == "barbarian"
    assert clubman.domain == "land"
    assert clubman.role == "combat"
    assert clubman.semantic_class == "heavy_infantry"
    assert clubman.native_line == "first"
    assert clubman.base_armor == 20
    assert clubman.primary_weapon.damage == 100
    assert clubman.primary_weapon.accuracy == 85
    axe_thrower = combined.get("barbarian_axe_thrower")
    assert [(w.damage,w.accuracy,w.ammunition) for w in axe_thrower.weapons] == [
        (200,30,7),(100,60,None)
    ]
    ram = combined.get("barbarian_ram")
    assert [(w.damage,w.accuracy) for w in ram.weapons] == [(2100,20),(200,20)]



FLEET_IDS = {
    "barbarian_deckwrecker",
    "barbarian_sail_shredder",
    "barbarian_pyroboat",
    "barbarian_boulder_catapult",
    "barbarian_wedge_paddler",
    "barbarian_powder_pitcher",
    "barbarian_terror_of_the_deep",
    "barbarian_dragonfire",
    "barbarian_dirigible_igniter",
    "barbarian_nest",
}


def test_official_help_barbarian_fleet_catalog_is_complete_and_ready():
    registry = BarbarianFleetRegistry.load()
    assert {unit.id for unit in registry.all()} == FLEET_IDS
    assert registry.metadata["simulation_status"] == "NAVAL_COMBAT_READY_MANUAL_QUANTITIES"
    assert registry.metadata["composition_status"] == "LEVEL_50_PLUS_USER_SPREADSHEET_MODEL_READY;LOWER_LEVEL_FULL_TABLE_NOT_CAPTURED"
    public = registry.public()
    assert all(row["domain"] == "naval" for row in public)
    assert all(row["army_kind"] == "barbarian" for row in public)
    assert all(row["unit_class"] == "machine" for row in public)
    assert all(row["simulation_ready"] is True for row in public)


def test_official_help_barbarian_fleet_stats_and_accuracy_bars_are_locked():
    registry = BarbarianFleetRegistry.load()
    expected = {
        "barbarian_deckwrecker": (3080,240,40,3,[(1500,80,None)]),
        "barbarian_sail_shredder": (3080,280,40,2,[(800,50,7),(1020,70,None)]),
        "barbarian_pyroboat": (4380,220,40,2,[(1640,50,None)]),
        "barbarian_boulder_catapult": (2960,200,40,3,[(900,25,8),(620,70,None)]),
        "barbarian_wedge_paddler": (11520,400,40,4,[(3320,95,None)]),
        "barbarian_powder_pitcher": (3080,120,30,4,[(1500,5,11),(740,50,None)]),
        "barbarian_terror_of_the_deep": (1600,120,40,3,[(2800,80,6),(2000,75,None)]),
        "barbarian_dragonfire": (2200,180,30,4,[(7000,20,3),(600,80,None)]),
        "barbarian_dirigible_igniter": (400,60,60,1,[(340,95,5)]),
        "barbarian_nest": (2800,100,20,5,[(2000,50,5)]),
    }
    actual = {
        unit.id: (
            unit.hit_points, unit.base_armor, unit.speed, unit.size,
            [(w.damage,w.accuracy,w.ammunition) for w in unit.weapons],
        )
        for unit in registry.all()
    }
    assert actual == expected


def test_combat_registry_includes_barbarian_fleet_and_preserves_weapon_order():
    combined = UnitRegistry.load(include_barbarians=True)
    sail = combined.get("barbarian_sail_shredder")
    assert sail.army_kind == "barbarian"
    assert sail.domain == "naval"
    assert sail.native_line == "second"
    assert sail.primary_weapon.damage == 800
    assert sail.primary_weapon.accuracy == 50
    assert sail.primary_weapon.ammunition == 7
    assert sail.weapons[1].damage == 1020
    assert sail.weapons[1].accuracy == 70
    assert sail.weapons[1].ammunition is None



def test_level_50_plus_barbarian_fleet_composition_matches_user_spreadsheet():
    registry = BarbarianFleetRegistry.load()
    assert registry.composition_for_stage(1) == {
        "barbarian_deckwrecker": 482,
        "barbarian_powder_pitcher": 84,
        "barbarian_dragonfire": 100,
        "barbarian_wedge_paddler": 400,
        "barbarian_nest": 60,
        "barbarian_dirigible_igniter": 180,
    }
    assert registry.composition_for_stage(2) == {
        "barbarian_deckwrecker": 555,
        "barbarian_powder_pitcher": 97,
        "barbarian_dragonfire": 115,
        "barbarian_wedge_paddler": 460,
        "barbarian_nest": 69,
        "barbarian_dirigible_igniter": 207,
    }
    assert registry.composition_for_stage(50) == {
        "barbarian_deckwrecker": 4025,
        "barbarian_powder_pitcher": 702,
        "barbarian_dragonfire": 835,
        "barbarian_wedge_paddler": 3340,
        "barbarian_nest": 501,
        "barbarian_dirigible_igniter": 1503,
    }
    assert registry.reward_multiplier_for_stage(50) == Decimal("5.9")



def test_barbarian_official_help_accuracy_bars_quantize_to_5_percent_grid():
    import json
    from importlib.resources import files
    evidence=json.loads(
        files("ikariam_battle.data.calibration")
        .joinpath("barbarian-land-official-help-2026-10-05.json")
        .read_text(encoding="utf-8")
    )
    assert len(evidence["units"])==9
    for row in evidence["units"]:
        for weapon in row["weapons"]:
            measured=100*weapon["fill_px"]/weapon["track_px"]
            assert round(measured/5)*5==weapon["accuracy"]
