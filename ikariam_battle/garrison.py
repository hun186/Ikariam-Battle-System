from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import Army


MAX_TOWN_HALL_LEVEL = 66
MAX_BARBARIAN_VILLAGE_LEVEL = 50
OPEN_FIELD_BATTLEFIELD_ID = "land-max"
GARRISON_TRANSITION_RULE_ID = "UNKNOWN-GARRISON-BATTLEFIELD-TRANSITION"

PLAYER_FORMULA_SOURCE = "COMMUNITY_CORROBORATED_CURRENT_RULE"
BARBARIAN_FORMULA_SOURCE = "GAMEFORGE_FORUM_2024_COMMUNITY_REPORT"
BARBARIAN_HISTORICAL_APPROXIMATION = "approximately 250 + 75 * wall_level"


def player_garrison_limit(town_hall_level: int, wall_level: int) -> int:
    if isinstance(town_hall_level, bool) or not isinstance(town_hall_level, int):
        raise ValueError("town hall level must be an integer")
    if not 1 <= town_hall_level <= MAX_TOWN_HALL_LEVEL:
        raise ValueError(f"town hall level must be 1..{MAX_TOWN_HALL_LEVEL}")
    if isinstance(wall_level, bool) or not isinstance(wall_level, int) or wall_level < 0:
        raise ValueError("wall level must be a non-negative integer")
    return 250 + 50 * (town_hall_level + wall_level)


def barbarian_garrison_limit(village_level: int, wall_level: int) -> int:
    """Community-reported Barbarian land garrison formula.

    The 2024 Gameforge forum report states:
      (barbarian village level + town wall level + 5) * 50
    which is algebraically the same base formula as player towns with
    Barbarian Village level substituted for Town Hall level.  An older 2022
    guide published only an approximate wall-only expression; retain that as
    historical provenance rather than treating it as a competing exact rule.
    """
    if isinstance(village_level, bool) or not isinstance(village_level, int):
        raise ValueError("barbarian village level must be an integer")
    if not 1 <= village_level <= MAX_BARBARIAN_VILLAGE_LEVEL:
        raise ValueError(
            f"barbarian village level must be 1..{MAX_BARBARIAN_VILLAGE_LEVEL}"
        )
    if isinstance(wall_level, bool) or not isinstance(wall_level, int) or wall_level < 0:
        raise ValueError("wall level must be a non-negative integer")
    return (village_level + wall_level + 5) * 50


def counted_garrison_quantity(army: "Army", through_round: int = 0) -> int:
    """Count input units relevant to the current land garrison rule.

    Since v17.4.0, Cooks and Doctors do not count toward the land garrison
    limit. Tender is the naval counterpart and likewise excluded by the
    official change, but cannot appear in the current executable land package.
    """
    excluded = {"doctor", "cook", "tender"}
    return sum(
        item.quantity
        for item in army.units
        if item.quantity > 0
        and item.arrival_round <= through_round
        and item.unit_id not in excluded
    )


def counted_live_waves(waves, registry) -> int:
    return sum(
        wave.alive
        for wave in waves
        if wave.alive > 0
        and registry.get(wave.unit.unit_id).counts_toward_garrison_limit
    )


def land_garrison_status(
    *,
    town_hall_level: int | None,
    barbarian_village_level: int | None,
    wall_level: int,
    defender_army: "Army",
    base_battlefield_id: str,
    through_round: int = 0,
) -> dict[str, Any]:
    if defender_army.army_kind == "barbarian":
        if barbarian_village_level is None:
            return {
                "modeled": False,
                "status": "barbarian_village_level_not_configured",
                "formula_status": BARBARIAN_FORMULA_SOURCE,
                "garrison_limit": None,
                "counted_defenders": None,
                "open_field": None,
                "base_battlefield": base_battlefield_id,
                "effective_battlefield": base_battlefield_id,
                "excluded_support_units": ["cook", "doctor", "tender"],
            }
        limit = barbarian_garrison_limit(barbarian_village_level, wall_level)
        settlement = {
            "settlement_kind": "barbarian_village",
            "barbarian_village_level": barbarian_village_level,
            "formula_status": BARBARIAN_FORMULA_SOURCE,
        }
    else:
        if town_hall_level is None:
            return {
                "modeled": False,
                "status": "town_hall_not_configured",
                "formula_status": PLAYER_FORMULA_SOURCE,
                "garrison_limit": None,
                "counted_defenders": None,
                "open_field": None,
                "base_battlefield": base_battlefield_id,
                "effective_battlefield": base_battlefield_id,
                "excluded_support_units": ["cook", "doctor", "tender"],
            }
        limit = player_garrison_limit(town_hall_level, wall_level)
        settlement = {
            "settlement_kind": "player_town",
            "town_hall_level": town_hall_level,
            "formula_status": PLAYER_FORMULA_SOURCE,
        }

    counted = counted_garrison_quantity(defender_army, through_round)
    open_field = counted > limit
    return {
        "modeled": True,
        "status": "open_field" if open_field else "behind_wall_limit",
        **settlement,
        "wall_level": wall_level,
        "garrison_limit": limit,
        "counted_defenders": counted,
        "open_field": open_field,
        "base_battlefield": base_battlefield_id,
        "effective_battlefield": OPEN_FIELD_BATTLEFIELD_ID if open_field else base_battlefield_id,
        "wall_active": bool(wall_level) and not open_field,
        "comparison": "counted_defenders > garrison_limit",
        "return_condition": "counted_defenders <= garrison_limit",
        "excluded_support_units": ["cook", "doctor", "tender"],
    }


# Compatibility name retained for callers/tests added while player-only
# garrison support was being introduced.
def player_garrison_status(**kwargs) -> dict[str, Any]:
    kwargs.setdefault("barbarian_village_level", None)
    return land_garrison_status(**kwargs)


def garrison_profile_metadata() -> dict[str, Any]:
    return {
        "player_formula": "250 + 50 * (town_hall_level + wall_level)",
        "player_formula_status": PLAYER_FORMULA_SOURCE,
        "max_town_hall_level": MAX_TOWN_HALL_LEVEL,
        "barbarian_formula": "(barbarian_village_level + wall_level + 5) * 50",
        "barbarian_formula_status": BARBARIAN_FORMULA_SOURCE,
        "barbarian_formula_note": (
            "2024 Gameforge-forum community report; algebraically the player "
            "formula with Barbarian Village level substituted for Town Hall."
        ),
        "barbarian_historical_approximation": BARBARIAN_HISTORICAL_APPROXIMATION,
        "max_barbarian_village_level": MAX_BARBARIAN_VILLAGE_LEVEL,
        "open_field_condition": "counted_defenders > garrison_limit",
        "open_field_battlefield": OPEN_FIELD_BATTLEFIELD_ID,
        "open_field_wall_active": False,
        "return_condition": "counted_defenders <= garrison_limit",
        "excluded_land_units_since_17_4_0": ["cook", "doctor"],
        "excluded_naval_units_since_17_4_0": ["tender"],
        "transition_rule_id": GARRISON_TRANSITION_RULE_ID,
        "sources": {
            "player_formula": "https://ikariam.fandom.com/wiki/Garrison_limit",
            "barbarian_formula": "https://forum.ikariam.gameforge.com/forum/thread/99684-not-a-bug-battlefield-size-change-when-entering-battle/",
            "support_exclusion_v17_4_0": "https://forum.ikariam.gameforge.com/forum/thread/117393-version-17-4-0-11-08-2026/",
        },
    }
