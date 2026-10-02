from collections import defaultdict

from ikariam_battle.battlefield import LAND_MINI, deploy
from ikariam_battle.engine import (
    _build_damage_queues,
    _resolve_volleys,
    _snapshot_phase_fire,
)
from ikariam_battle.models import Army
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
    before = source_wave.ammo_pool_shots
    assert before == 63

    events = []
    applied = {}
    volleys = _snapshot_phase_fire(
        attacker, defender, registry, targeting, events, 1, "attacker", "second", applied
    )
    assert source_wave.ammo_pool_shots == 42  # reserved firing tickets

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
    assert withheld.details["count"] == 21
    assert withheld.details["ammunition_preserved"] == 21
    assert withheld.details["rule_id"] == TARGET_PENETRATION_RULE_ID
