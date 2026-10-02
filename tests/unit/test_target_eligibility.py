from collections import defaultdict

from ikariam_battle.battlefield import LAND_MINI, deploy
from ikariam_battle.engine import (
    _build_damage_queues,
    _resolve_volleys,
    _snapshot_phase_fire,
)
from ikariam_battle.models import Army, ArmyUnit, Slot, Wave
from ikariam_battle.profiles import ForgeProfile, TargetingProfile, WorkshopProfile
from ikariam_battle.target_eligibility import (
    TARGET_PENETRATION_RULE_ID,
    unit_target_eligibility,
    wall_target_eligibility,
)
from ikariam_battle.units import UnitRegistry


def test_equal_effective_attack_and_defense_is_ineligible():
    registry = UnitRegistry.load()
    workshop = WorkshopProfile.load()
    forge = ForgeProfile.load()
    attacker = registry.get("sulphur_carabineer")
    target = registry.get("steam_giant")
    decision, trace = unit_target_eligibility(
        attacker,
        target,
        attack_upgrade=0,
        armor_upgrade=104,  # 60 base + 104*5 = 580, exactly Carabineer ATK.
        attacker_forge=0,
        defender_forge=0,
        workshop=workshop,
        forge=forge,
        weapon=attacker.primary_weapon,
    )
    assert trace.post_forge_damage == "580"
    assert decision.effective_defense == 580
    assert decision.eligible is False
    assert decision.reason == "effective_attack_not_above_defense"


def test_wall_penetration_helper_matches_observed_skip_rule():
    registry = UnitRegistry.load()
    workshop = WorkshopProfile.load()
    forge = ForgeProfile.load()
    mortar = registry.get("mortar")
    carabineer = registry.get("sulphur_carabineer")

    mortar_decision = wall_target_eligibility(
        mortar, 0, 0, 48, workshop, forge, weapon=mortar.primary_weapon
    )
    rifle_decision = wall_target_eligibility(
        carabineer, 0, 0, 48, workshop, forge, weapon=carabineer.primary_weapon
    )

    assert mortar_decision.eligible is True
    assert mortar_decision.effective_defense == 3456
    assert rifle_decision.eligible is False
    assert rifle_decision.effective_attack == "580"
    assert rifle_decision.effective_defense == 3456


def test_nonpenetrable_priority_target_is_skipped_for_next_damageable_formation():
    registry = UnitRegistry.load()
    workshop = WorkshopProfile.load()
    forge = ForgeProfile.load()
    targeting = TargetingProfile.load()

    attacker_army = Army.from_dict({
        "forge_level": 0,
        "units": [{"unit_id": "spearman", "quantity": 1}],
    })
    defender_army = Army.from_dict({
        "forge_level": 0,
        "units": [
            # Spearman ATK 80. Steam Giant DEF = 60 + 4*5 = 80: ineligible.
            {"unit_id": "steam_giant", "quantity": 1, "armor_upgrade": 4},
            {"unit_id": "sulphur_carabineer", "quantity": 1},
        ],
    })
    attacker = deploy(attacker_army, registry, LAND_MINI)
    defender = deploy(defender_army, registry, LAND_MINI)

    events = []
    applied = {}
    volleys = _snapshot_phase_fire(
        attacker, defender, registry, targeting, events, 1, "attacker", "first", applied
    )
    queues = _build_damage_queues(defender, registry, events, 1, "defender", applied)
    casualties = defaultdict(int)
    slot_casualties = defaultdict(int)
    fired = _resolve_volleys(
        volleys,
        defender,
        queues,
        registry,
        workshop,
        forge,
        targeting,
        events,
        1,
        attacker_army,
        defender_army,
        casualties,
        slot_casualties,
        applied,
    )

    assert fired == 1
    assert any(
        event.type == "target_ineligible"
        and event.details["rule_id"] == TARGET_PENETRATION_RULE_ID
        and event.details["target_unit_id"] == "steam_giant"
        and event.details["effective_attack"] == "80"
        and event.details["effective_defense"] == 80
        for event in events
    )
    damage = next(event for event in events if event.type == "damage")
    assert damage.details["target_unit_id"] == "sulphur_carabineer"
    assert damage.details["target_class"] == "second"


def test_finite_ammo_weapon_skips_armored_first_and_spends_only_on_next_target():
    registry = UnitRegistry.load()
    workshop = WorkshopProfile.load()
    forge = ForgeProfile.load()
    targeting = TargetingProfile.load()

    attacker_army = Army.from_dict({
        "forge_level": 0,
        "units": [{"unit_id": "sulphur_carabineer", "quantity": 1}],
    })
    defender_army = Army.from_dict({
        "forge_level": 0,
        "units": [
            {"unit_id": "steam_giant", "quantity": 1, "armor_upgrade": 104},
            {"unit_id": "slinger", "quantity": 1},
        ],
    })
    attacker = deploy(attacker_army, registry, LAND_MINI)
    defender = deploy(defender_army, registry, LAND_MINI)
    source_wave = next(wave for wave in attacker if wave.unit.unit_id == "sulphur_carabineer")
    assert source_wave.ammo_pool_shots == 3

    events = []
    applied = {}
    volleys = _snapshot_phase_fire(
        attacker, defender, registry, targeting, events, 1, "attacker", "second", applied
    )
    assert source_wave.ammo_pool_shots == 2

    queues = _build_damage_queues(defender, registry, events, 1, "defender", applied)
    fired = _resolve_volleys(
        volleys,
        defender,
        queues,
        registry,
        workshop,
        forge,
        targeting,
        events,
        1,
        attacker_army,
        defender_army,
        defaultdict(int),
        defaultdict(int),
        applied,
    )

    assert fired == 1
    assert source_wave.ammo_pool_shots == 2
    assert any(
        event.type == "target_ineligible"
        and event.details["target_unit_id"] == "steam_giant"
        and event.details["effective_attack"] == "580"
        and event.details["effective_defense"] == 580
        for event in events
    )
    damage = next(event for event in events if event.type == "damage")
    assert damage.details["target_unit_id"] == "slinger"
    assert damage.details["target_class"] == "second"


def test_no_damageable_target_preserves_finite_ammunition():
    registry = UnitRegistry.load()
    workshop = WorkshopProfile.load()
    forge = ForgeProfile.load()
    targeting = TargetingProfile.load()

    attacker_army = Army.from_dict({
        "forge_level": 0,
        "units": [{"unit_id": "sulphur_carabineer", "quantity": 21}],
    })
    defender_army = Army.from_dict({
        "forge_level": 0,
        "units": [
            # Carabineer ATK 580 equals this Steam Giant's effective DEF.
            {"unit_id": "steam_giant", "quantity": 10, "armor_upgrade": 104},
        ],
    })
    attacker = deploy(attacker_army, registry, LAND_MINI)
    defender = deploy(defender_army, registry, LAND_MINI)
    source_wave = next(wave for wave in attacker if wave.unit.unit_id == "sulphur_carabineer")
    source_wave.ammo_pool_shots = 5
    before = source_wave.ammo_pool_shots

    events = []
    applied = {}
    volleys = _snapshot_phase_fire(
        attacker, defender, registry, targeting, events, 1, "attacker", "second", applied
    )
    assert source_wave.ammo_pool_shots == 0  # five reserved firing tickets

    queues = _build_damage_queues(defender, registry, events, 1, "defender", applied)
    fired = _resolve_volleys(
        volleys,
        defender,
        queues,
        registry,
        workshop,
        forge,
        targeting,
        events,
        1,
        attacker_army,
        defender_army,
        defaultdict(int),
        defaultdict(int),
        applied,
    )

    assert fired == 0
    assert source_wave.ammo_pool_shots == before
    assert not any(event.type == "damage" and event.side == "attacker" for event in events)
    withheld = next(
        event for event in events
        if event.type == "shots_withheld_no_damageable_target"
    )
    assert withheld.details["count"] == 5
    assert withheld.details["ammunition_preserved"] == 5
    assert withheld.details["rule_id"] == TARGET_PENETRATION_RULE_ID
    assert not any(event.type == "partial_ammunition" for event in events)
    assert "EXP-AMMO-PARTIAL-ORDER-001" not in applied

def test_mixed_source_formation_freezes_address_book_per_eligibility_set():
    registry = UnitRegistry.load()
    workshop = WorkshopProfile.load()
    forge = ForgeProfile.load()
    targeting = TargetingProfile.load()

    steam = Wave(
        ArmyUnit("steam_giant", 1, "steam", armor_upgrade=4),
        0,
        [Slot("first-1", "first", 1, 1, "steam_giant", "steam", 1, 10, 0)],
    )
    hoplite = Wave(
        ArmyUnit("hoplite", 1, "hop"),
        0,
        [Slot("first-2", "first", 2, 2, "hoplite", "hop", 1, 30, 0)],
    )
    queues = {
        ("steam_giant", "steam", "first-1"): [0],
        ("hoplite", "hop", "first-2"): [0],
    }
    volleys = [
        {
            "side": "attacker",
            "source_unit": "spearman",
            "source_wave": "spear",
            "runtime_line": "first",
            "weapon_id": "primary",
            "attack_upgrade": 0,
            "row_numbers": [1],
            "source_damage_positions": [1],
        },
        {
            "side": "attacker",
            "source_unit": "hoplite",
            "source_wave": "source-hop",
            "runtime_line": "first",
            "weapon_id": "primary",
            "attack_upgrade": 0,
            "row_numbers": [1],
            "source_damage_positions": [2],
        },
    ]
    events = []
    _resolve_volleys(
        volleys,
        [steam, hoplite],
        queues,
        registry,
        workshop,
        forge,
        targeting,
        events,
        1,
        Army((ArmyUnit("spearman", 1, "spear"), ArmyUnit("hoplite", 1, "source-hop")), 0),
        Army((ArmyUnit("steam_giant", 1, "steam", armor_upgrade=4), ArmyUnit("hoplite", 1, "hop")), 0),
        defaultdict(int),
        defaultdict(int),
        {},
    )

    damage_by_source = {
        event.details["source_unit_id"]: event.details["target_unit_id"]
        for event in events
        if event.type == "damage"
    }
    # Spearman ATK 80 cannot penetrate Steam Giant DEF 80, so its frozen
    # address set contains only Hoplite. Hoplite ATK 360 can penetrate both and
    # gets a different frozen set whose row-1 address is Steam Giant position 1.
    assert damage_by_source["spearman"] == "hoplite"
    assert damage_by_source["hoplite"] == "steam_giant"

def test_promoted_light_elimination_does_not_shrink_frozen_first_address_book():
    registry = UnitRegistry.load()
    workshop = WorkshopProfile.load()
    forge = ForgeProfile.load()
    targeting = TargetingProfile.load()

    # Swordsman is native Flank but is already promoted to runtime First.
    promoted_sword = Wave(
        ArmyUnit("swordsman", 1, "sword"),
        0,
        [Slot("first-1", "first", 1, 1, "swordsman", "sword", 1, 30, 0)],
    )
    hoplite = Wave(
        ArmyUnit("hoplite", 1, "hop"),
        0,
        [Slot("first-2", "first", 2, 2, "hoplite", "hop", 1, 30, 0)],
    )
    queues = {
        ("swordsman", "sword", "first-1"): [0],
        ("hoplite", "hop", "first-2"): [0],
    }
    volleys = [{
        "side": "attacker",
        "source_unit": "mortar",
        "source_wave": "mortar-source",
        "runtime_line": "third",
        "weapon_id": "primary",
        "attack_upgrade": 0,
        # Two row-1 source columns both address damage-position 1 in the frozen
        # First book. The first kills Swordsman; the second must stay on the
        # now-empty address rather than remap to Hoplite.
        "row_numbers": [1, 1],
        "source_damage_positions": [1, 2],
    }]
    events = []
    casualties = defaultdict(int)
    fired = _resolve_volleys(
        volleys,
        [promoted_sword, hoplite],
        queues,
        registry,
        workshop,
        forge,
        targeting,
        events,
        1,
        Army((ArmyUnit("mortar", 2, "mortar-source"),), 0),
        Army((
            ArmyUnit("swordsman", 1, "sword"),
            ArmyUnit("hoplite", 1, "hop"),
        ), 0),
        casualties,
        defaultdict(int),
        {},
    )

    assert fired == 2
    assert casualties["swordsman"] == 1
    assert casualties.get("hoplite", 0) == 0
    assert promoted_sword.slots[0].units == 0
    assert hoplite.slots[0].units == 1
    assert any(
        event.type == "shot_addressed_empty_slot"
        and event.details["target_unit_id"] == "swordsman"
        and event.details["target_damage_position"] == 1
        for event in events
    )

