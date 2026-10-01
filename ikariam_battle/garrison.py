from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import Army


MAX_TOWN_HALL_LEVEL = 66
OPEN_FIELD_BATTLEFIELD_ID = "land-max"
GARRISON_TRANSITION_RULE_ID = "UNKNOWN-GARRISON-BATTLEFIELD-TRANSITION"
BARBARIAN_GARRISON_RULE_ID = "UNKNOWN-BARBARIAN-GARRISON-LIMIT-FORMULA"

PLAYER_FORMULA_SOURCE = "COMMUNITY_CORROBORATED_CURRENT_RULE"
BARBARIAN_FORMULA_STATUS = "CONFLICTING_COMMUNITY_EVIDENCE"


def player_garrison_limit(town_hall_level: int, wall_level: int) -> int:
    if isinstance(town_hall_level, bool) or not isinstance(town_hall_level, int):
        raise ValueError("town hall level must be an integer")
    if not 1 <= town_hall_level <= MAX_TOWN_HALL_LEVEL:
        raise ValueError(f"town hall level must be 1..{MAX_TOWN_HALL_LEVEL}")
    if isinstance(wall_level, bool) or not isinstance(wall_level, int) or wall_level < 0:
        raise ValueError("wall level must be a non-negative integer")
    return 250 + 50 * (town_hall_level + wall_level)


def counted_garrison_quantity(army: "Army", through_round: int = 0) -> int:
    """Count surviving/stationed input units relevant to current land garrison rules.

    This input-side helper is for pre-battle/arrival planning. Since v17.4.0,
    Doctor and Cook do not count toward the land garrison limit.
    """
    excluded = {"doctor", "cook"}
    return sum(
        item.quantity
        for item in army.units
        if item.quantity > 0
        and item.arrival_round <= through_round
        and item.unit_id not in excluded
    )


def counted_live_waves(waves, registry) -> int:
    excluded = {"doctor", "cook"}
    return sum(
        wave.alive
        for wave in waves
        if wave.alive > 0 and registry.get(wave.unit.unit_id).id not in excluded
    )


def player_garrison_status(
    *,
    town_hall_level: int | None,
    wall_level: int,
    defender_army: "Army",
    base_battlefield_id: str,
    through_round: int = 0,
) -> dict[str, Any]:
    if defender_army.army_kind != "player":
        return {
            "modeled": False,
            "status": "barbarian_formula_unresolved",
            "formula_status": BARBARIAN_FORMULA_STATUS,
            "rule_id": BARBARIAN_GARRISON_RULE_ID,
            "garrison_limit": None,
            "counted_defenders": None,
            "open_field": None,
            "base_battlefield": base_battlefield_id,
            "effective_battlefield": None,
            "excluded_support_units": ["cook", "doctor"],
        }
    if town_hall_level is None:
        return {
            "modeled": False,
            "status": "town_hall_not_configured",
            "formula_status": PLAYER_FORMULA_SOURCE,
            "rule_id": None,
            "garrison_limit": None,
            "counted_defenders": None,
            "open_field": None,
            "base_battlefield": base_battlefield_id,
            "effective_battlefield": base_battlefield_id,
            "excluded_support_units": ["cook", "doctor"],
        }

    limit = player_garrison_limit(town_hall_level, wall_level)
    counted = counted_garrison_quantity(defender_army, through_round)
    open_field = counted > limit
    return {
        "modeled": True,
        "status": "open_field" if open_field else "behind_wall_limit",
        "formula_status": PLAYER_FORMULA_SOURCE,
        "rule_id": None,
        "town_hall_level": town_hall_level,
        "wall_level": wall_level,
        "garrison_limit": limit,
        "counted_defenders": counted,
        "open_field": open_field,
        "base_battlefield": base_battlefield_id,
        "effective_battlefield": OPEN_FIELD_BATTLEFIELD_ID if open_field else base_battlefield_id,
        "wall_active": bool(wall_level) and not open_field,
        "comparison": "counted_defenders > garrison_limit",
        "excluded_support_units": ["cook", "doctor"],
    }


def garrison_profile_metadata() -> dict[str, Any]:
    return {
        "player_formula": "250 + 50 * (town_hall_level + wall_level)",
        "player_formula_status": PLAYER_FORMULA_SOURCE,
        "max_town_hall_level": MAX_TOWN_HALL_LEVEL,
        "open_field_condition": "counted_defenders > garrison_limit",
        "open_field_battlefield": OPEN_FIELD_BATTLEFIELD_ID,
        "open_field_wall_active": False,
        "return_condition": "counted_defenders <= garrison_limit",
        "excluded_land_units_since_17_4_0": ["cook", "doctor"],
        "barbarian_formula_status": BARBARIAN_FORMULA_STATUS,
        "barbarian_candidates": [
            {
                "formula": "(barbarian_village_level + wall_level + 5) * 50",
                "evidence": "2024 Gameforge forum community report",
            },
            {
                "formula": "approximately 250 + 75 * wall_level",
                "evidence": "2022 Gameforge forum Barbarian Battle Guide",
            },
        ],
        "barbarian_rule_id": BARBARIAN_GARRISON_RULE_ID,
        "transition_rule_id": GARRISON_TRANSITION_RULE_ID,
    }
