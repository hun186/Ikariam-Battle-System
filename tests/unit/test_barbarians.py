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


def test_barbarian_current_catalog_stats_and_explicit_derivation():
    registry = BarbarianRegistry.load()
    expected = {
        "barbarian_clubman": (240, 0, 100, 70, None, 1),
        "barbarian_axe_swinger": (1120, 20, 360, 90, None, 1),
        "barbarian_knifeman": (360, 0, 200, 90, None, 1),
        "barbarian_axe_thrower": (320, 0, 100, 40, 7, 1),
        "barbarian_war_walker": (3680, 60, 840, 80, None, 3),
        "barbarian_ram": (1400, 20, 2100, 10, None, 5),
        "barbarian_catapult": (640, 0, 5400, 10, 5, 5),
        "barbarian_dirigible": (800, 0, 960, 20, 2, 2),
        "barbarian_fighter": (580, 0, 340, 80, 4, 1),
    }
    actual = {
        unit.id: (
            unit.hit_points, unit.base_armor, unit.damage, unit.accuracy,
            unit.ammunition, unit.size,
        )
        for unit in registry.all()
    }
    assert actual == expected
    assert "CURRENT_HP_OBSERVED" in registry.get("barbarian_knifeman").provenance["confidence"]
    assert "DIRECT_LEGACY_CORE_X20" in registry.get("barbarian_ram").provenance["confidence"]


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
    assert clubman.primary_weapon.damage == 100
    assert clubman.primary_weapon.accuracy == 70



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
    assert registry.metadata["composition_status"] == "LEVEL_TO_QUANTITY_TABLE_NOT_YET_CAPTURED"
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
