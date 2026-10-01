from __future__ import annotations

from typing import Any


MAX_TOWN_WALL_LEVEL = 48
TOWN_WALL_RULE_ID = "UNKNOWN-TOWN-WALL-COMBAT"
TOWN_WALL_SOURCE_URL = "https://gameforge.com/en-GB/games/ikariam-city-wall.html"
TOWN_WALL_COMMUNITY_SOURCE_URL = "https://ikariam.fandom.com/wiki/Building%3ATown_wall"


def wall_stats(level: int) -> dict[str, int]:
    """Return current published per-section Town Wall combat values.

    Level 0 is the explicit no-wall state. For levels 1..46, HP and armour are
    linear while damage/accuracy use the documented level-10/20 breakpoints.
    These published values do not by themselves define wall targeting,
    breaching, defender refill, or flank-lock semantics.
    """
    if isinstance(level, bool) or not isinstance(level, int) or not 0 <= level <= MAX_TOWN_WALL_LEVEL:
        raise ValueError(f"wall level must be 0..{MAX_TOWN_WALL_LEVEL}")
    if level == 0:
        return {"level": 0, "damage": 0, "accuracy": 0, "hit_points": 0, "armor": 0}
    if level < 10:
        damage = 10 + 2 * level
        accuracy = 30
    elif level < 20:
        damage = 30 + 5 * level
        accuracy = 50
    else:
        damage = 50 + 10 * level
        accuracy = 80
    return {
        "level": level,
        "damage": damage,
        "accuracy": accuracy,
        "hit_points": 100 + 50 * level,
        "armor": 4 * level,
    }


def wall_segments(field) -> int:
    """Derive wall sections from the selected land battlefield's First line."""
    first = getattr(field, "lines", {}).get("first")
    return len(first.physical_order) if first is not None else 0


def wall_status(
    level: int,
    field,
    *,
    active: bool | None = None,
    inactive_reason: str | None = None,
) -> dict[str, Any]:
    stats = wall_stats(level)
    if level == 0:
        status = "not_present"
    elif active is False:
        status = "suppressed"
    else:
        status = "unsupported_boundary"
    return {
        **stats,
        "segments": wall_segments(field) if level else 0,
        "status": status,
        "combat_model_status": "INPUT_CAPTURED_COMBAT_UNSUPPORTED",
        "rule_id": TOWN_WALL_RULE_ID,
        "effect_applied": False,
        "active": bool(level) if active is None else bool(active),
        "inactive_reason": inactive_reason,
    }


def wall_profile_metadata() -> dict[str, Any]:
    return {
        "max_level": MAX_TOWN_WALL_LEVEL,
        "level_0_means_no_wall": True,
        "input_supported": True,
        "combat_model_status": "INPUT_CAPTURED_COMBAT_UNSUPPORTED",
        "rule_id": TOWN_WALL_RULE_ID,
        "segment_count_source": "selected_battlefield_first_line",
        "published_stat_fields": ["damage", "accuracy", "hit_points", "armor"],
        "source_type": "GAMEFORGE_CURRENT_REFERENCE_PLUS_COMMUNITY_FORMULA",
        "source_urls": [TOWN_WALL_SOURCE_URL, TOWN_WALL_COMMUNITY_SOURCE_URL],
    }
