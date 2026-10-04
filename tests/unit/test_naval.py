from ikariam_battle.battlefield import NAVAL_BATTLEFIELDS, battlefield_metadata, deploy
from ikariam_battle.engine import _prepare_round_start, _snapshot_phase_fire, simulate
from ikariam_battle.models import Army, ArmyUnit, Slot, Wave
from ikariam_battle.profiles import TargetingProfile
from ikariam_battle.units import UnitRegistry


def test_naval_max_geometry_matches_current_full_formation_capacities():
    field = NAVAL_BATTLEFIELDS["naval-max"]
    assert len(field.lines["first"].physical_order) == 7
    assert len(field.lines["flank"].physical_order) == 6
    assert len(field.lines["second"].physical_order) == 7
    assert len(field.lines["third"].physical_order) == 5
    assert len(field.lines["balloon"].physical_order) == 2
    assert len(field.lines["anti-balloon"].physical_order) == 2
    assert field.lines["first"].slot_space == 25
    assert field.lines["flank"].slot_space == 18
    assert field.lines["second"].slot_space == 24
    assert field.lines["third"].slot_space == 15
    assert field.lines["balloon"].slot_space == 15
    assert field.lines["anti-balloon"].slot_space == 15
    meta = {row["id"]: row for row in battlefield_metadata()}
    assert meta["naval-max"]["supported"] is True
    assert meta["naval-mini"]["supported"] is False


def test_naval_runtime_line_classification_matches_current_roles():
    registry = UnitRegistry.load()
    assert registry.get("ram_ship").semantic_class == "light_infantry"
    assert registry.get("ram_ship").native_line == "flank"
    assert registry.get("ram_ship").battlefield_class == "flank"
    assert registry.get("diving_boat").semantic_class == "artillery"
    assert registry.get("diving_boat").native_line == "third"
    assert registry.get("diving_boat").battlefield_class == "third"


def test_full_naval_max_formation_deploys_to_verified_lines_and_counts():
    registry = UnitRegistry.load()
    field = NAVAL_BATTLEFIELDS["naval-max"]
    army = Army.from_dict({"units": [
        {"unit_id": "steam_ram", "quantity": 35},
        {"unit_id": "ram_ship", "quantity": 36},
        {"unit_id": "mortar_ship", "quantity": 42},
        {"unit_id": "rocket_ship", "quantity": 15},
        {"unit_id": "balloon_carrier", "quantity": 6},
        {"unit_id": "paddle_speedboat", "quantity": 30},
    ]})
    waves = deploy(army, registry, field, "formation-naval")
    deployed = {}
    for wave in waves:
        for slot in wave.slots:
            deployed[slot.line] = deployed.get(slot.line, 0) + slot.units
    assert deployed == {
        "first": 35, "flank": 36, "second": 42, "third": 15,
        "balloon": 6, "anti-balloon": 30,
    }
    assert all(wave.reserve == 0 for wave in waves)


def test_naval_targeting_profile_matches_official_help_contract():
    profile = TargetingProfile.load("official-help-naval-targeting")
    assert profile.firing_order == (
        "anti-balloon", "balloon", "third", "flank", "second", "first"
    )
    assert profile.formation_fill_order == (
        "balloon", "anti-balloon", "third", "second", "first", "flank"
    )
    assert profile.priorities == {
        "third": ("first", "flank"),
        "second": ("first", "flank", "second"),
        "first": ("first", "second", "third", "flank"),
        "flank": ("flank", "second", "third", "first"),
        "anti-balloon": ("balloon", "anti-balloon"),
        "balloon": ("third", "second", "first", "flank"),
    }
    assert profile.same_formation_simultaneous is True


def test_naval_front_uses_official_weakest_heavy_first_selection():
    registry = UnitRegistry.load()
    field = NAVAL_BATTLEFIELDS["naval-max"]
    army = Army.from_dict({"units": [
        {"unit_id": "steam_ram", "quantity": 5},
        {"unit_id": "fire_ship", "quantity": 12},
    ]})
    waves = deploy(army, registry, field, "formation-naval")
    fire = next(w for w in waves if w.unit.unit_id == "fire_ship")
    steam = next(w for w in waves if w.unit.unit_id == "steam_ram")
    # Fire Ship has the weaker primary attack and therefore owns the first
    # center-priority Front slots before Steam Ram under official Help.
    assert fire.slots
    assert min(slot.damage_position for slot in fire.slots) == 1
    assert all(
        slot.damage_position not in {s.damage_position for s in fire.slots}
        for slot in steam.slots
    )


def test_strict_naval_no_longer_reports_unknown_target_priorities():
    result = simulate({
        "policy": "strict", "battlefield": "naval-max", "max_rounds": 1,
        "attacker": {"units": [{"unit_id": "steam_ram", "quantity": 35}]},
        "defender": {"units": [{"unit_id": "steam_ram", "quantity": 35}]},
    })
    rules = {
        e["details"].get("rule_id")
        for e in result["events"] if e["type"] == "unsupported_mechanic"
    }
    assert "UNKNOWN-NAVAL-TARGET-PRIORITIES" not in rules


def test_experimental_naval_max_executes_shared_am_damage_engine():
    result = simulate({
        "policy": "experimental", "battlefield": "naval-max", "max_rounds": 1,
        "attacker": {"units": [{"unit_id": "steam_ram", "quantity": 35}]},
        "defender": {"units": [{"unit_id": "steam_ram", "quantity": 35}]},
    })
    assert result["rounds_completed"] == 1
    assert any(e["type"] == "attacking_matrix" for e in result["events"])
    assert any(e["type"] == "damage" for e in result["events"])
    assert "EXP-NAVAL-TARGETING-LAND-ROLE-ANALOGY-001" not in {
        row["id"] for row in result["assumptions"]
    }
    assert result["military_score"]["attacker"]["economy_status"] in {
        "modeled", "unavailable_for_units"
    }


def test_exhausted_naval_long_range_whole_wave_moves_to_front_like_land_fallback():
    registry = UnitRegistry.load()
    field = NAVAL_BATTLEFIELDS["naval-max"]
    rules = FormationRules.load("formation-naval")
    wave = Wave(
        ArmyUnit("mortar_ship", 6, "mortar-wave"),
        0,
        [Slot("second-1", "second", 4, 1, "mortar_ship", "mortar-wave", 6, 6, 740)],
        0,
        0,
        0,
        30,
    )
    events=[]; applied={}
    _prepare_round_start(
        [wave], events, 2, "attacker", applied,
        registry=registry, rules=rules, field=field,
    )
    assert {slot.line for slot in wave.slots if slot.units} == {"first"}
    assert sum(slot.units for slot in wave.slots) == 6
    assert wave.reserve == 0
    assert wave.ammo_pool_shots == 0
    fallback = next(e for e in events if e.type == "formation_fallback")
    assert fallback.details["rule"] == "naval_exhausted_long_range_to_front"
    assert fallback.details["primary_ammo_exhausted"] is True


def test_exhausted_naval_long_range_front_uses_secondary_without_primary_ammo():
    registry = UnitRegistry.load()
    targeting = TargetingProfile.load("official-help-naval-targeting")
    source = Wave(
        ArmyUnit("mortar_ship", 6, "mortar-wave"),
        0,
        [Slot("first-1", "first", 4, 1, "mortar_ship", "mortar-wave", 6, 6)],
        0,
        0,
        0,
        30,
    )
    target = Wave(
        ArmyUnit("steam_ram", 5, "steam-wave"),
        0,
        [Slot("first-1", "first", 4, 1, "steam_ram", "steam-wave", 5, 5)],
    )
    events=[]; applied={}
    volleys = _snapshot_phase_fire(
        [source], [target], registry, targeting, events, 2,
        "attacker", "first", applied,
    )
    assert len(volleys) == 1
    assert volleys[0]["weapon_id"] == registry.get("mortar_ship").weapons[1].id
    assert source.ammo_pool_shots == 0
    assert not any(e.type == "ammo_exhausted" for e in events)
