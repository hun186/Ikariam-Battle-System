from __future__ import annotations

from math import ceil
from typing import Any


MAX_TOWN_WALL_LEVEL = 48
GAMEFORGE_WALL_REFERENCE_MAX_LEVEL = 46
TOWN_WALL_RULE_ID = "UNKNOWN-TOWN-WALL-COMBAT"
TOWN_WALL_SOURCE_URL = "https://gameforge.com/en-GB/games/ikariam-city-wall.html"
TOWN_WALL_COMMUNITY_SOURCE_URL = "https://ikariam.fandom.com/wiki/Building%3ATown_wall"
TOWN_WALL_FORUM_MAX_SOURCE_URL = "https://forum.ikariam.gameforge.com/forum/thread/102643-wbbl-worldwide-biggest-building-levels/"
TOWN_WALL_FORUM_COMBAT_SOURCE_URL = "https://forum.ikariam.gameforge.com/forum/thread/92826-freighters-and-pushing/"
TOWN_WALL_FORUM_TARGETING_SOURCE_URL = "https://forum.ikariam.gameforge.com/forum/thread/95872-%D0%B2%D0%B5%D1%80%D1%81%D0%B8%D1%8F-0-4-2-%D0%BF%D0%BE-%D0%BF%D0%BE%D0%BB%D0%BA%D0%B0%D0%BC/"
TOWN_WALL_FORUM_PENETRATION_SOURCE_URL = "https://forum.ikariam.gameforge.com/forum/thread/30537-taverna-kaikias/?pageNo=70"
TOWN_WALL_V13_CHANGELOG_URL = "https://forum.ikariam.gameforge.com/forum/thread/107634-infinite-horizons-milestone-2/"
TOWN_WALL_V13_STATS_DISCUSSION_URL = "https://forum.ikariam.gameforge.com/forum/thread/107659-infinite-horizons-2/"


def wall_stats(level: int) -> dict[str, int | None]:
    """Return current per-section Town Wall values that are safe to assert.

    Infinite Horizons / v13.0.0 raised Town Wall base stats. Current evidence
    supports factor-18 scaling of the legacy wall HP, armour, and damage table:

      HP     = 1800 + 900 * level
      armour = 72 * level
      damage = 18 * legacy piecewise damage

    Current observed damage points Lv1=216, Lv9=504, Lv18=2160, and Lv26=5580 exactly
    match the legacy three-tier damage table multiplied by 18. Accuracy remains
    unresolved here; do not project the legacy 30/50/80 values without current
    evidence.
    """
    if isinstance(level, bool) or not isinstance(level, int) or not 0 <= level <= MAX_TOWN_WALL_LEVEL:
        raise ValueError(f"wall level must be 0..{MAX_TOWN_WALL_LEVEL}")
    if level == 0:
        return {"level": 0, "damage": 0, "accuracy": 0, "hit_points": 0, "armor": 0}
    if level < 10:
        damage = (10 + 2 * level) * 18
    elif level < 20:
        damage = (30 + 5 * level) * 18
    else:
        damage = (50 + 10 * level) * 18
    return {
        "level": level,
        "damage": damage,
        "accuracy": None,
        "hit_points": 1800 + 900 * level,
        "armor": 72 * level,
    }

def successful_hits_to_breach_wall_section(level: int, attack_damage: int) -> int | None:
    """Return successful hits needed to destroy one wall section.

    Arithmetic core:
      ceil((1800 + 900*level) / (attack_damage - 72*level))

    This counts successful hits, not deployed artillery pieces. Accuracy, shot
    distribution, target selection, and firing chronology are intentionally
    outside this helper. None means the hit cannot penetrate the wall armour.
    """
    if isinstance(attack_damage, bool) or not isinstance(attack_damage, int) or attack_damage < 0:
        raise ValueError("attack damage must be a non-negative integer")
    stats = wall_stats(level)
    if level == 0:
        return 0
    net_damage = attack_damage - int(stats["armor"] or 0)
    if net_damage <= 0:
        return None
    return ceil(int(stats["hit_points"] or 0) / net_damage)

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
        "published_stat_fields": ["hit_points", "armor", "damage"],
        "unresolved_current_stat_fields": ["accuracy"],
        "hit_points_formula": "1800 + 900 * level",
        "armor_formula": "72 * level",
        "damage_formula": {"1-9": "(10 + 2*level) * 18", "10-19": "(30 + 5*level) * 18", "20+": "(50 + 10*level) * 18"},
        "damage_observed_points": {"1": 216, "9": 504, "18": 2160, "26": 5580},
        "successful_breach_hits_formula": "ceil((1800 + 900*level) / (attack_damage - 72*level))",
        "successful_breach_hits_scope": "successful hits only; excludes accuracy and shot allocation",
        "targeting_contract": {
            "status": "TARGET_PRIORITY_KNOWN_COMBAT_STILL_GUARDED",
            "artillery_priority": ["wall", "first"],
            "rule": "Attacking land artillery targets the Town Wall before ordinary First-line units while intact wall sections are present.",
            "penetration_rule": "effective_attack > effective_defense",
            "non_penetrating_target_consumes_ammunition": False,
            "non_penetrating_target_action": "skip_and_continue_target_priority",
        },
        "source_type": "MIXED_CURRENT_REFERENCE",
        "gameforge_reference_max_level": GAMEFORGE_WALL_REFERENCE_MAX_LEVEL,
        "current_game_max_level_evidence": "GAMEFORGE_FORUM_PLUS_COMMUNITY_TABLE",
        "source_urls": [
            TOWN_WALL_SOURCE_URL,
            TOWN_WALL_COMMUNITY_SOURCE_URL,
            TOWN_WALL_FORUM_MAX_SOURCE_URL,
            TOWN_WALL_FORUM_COMBAT_SOURCE_URL,
            TOWN_WALL_FORUM_TARGETING_SOURCE_URL,
            TOWN_WALL_FORUM_PENETRATION_SOURCE_URL,
            TOWN_WALL_V13_CHANGELOG_URL,
            TOWN_WALL_V13_STATS_DISCUSSION_URL,
        ],
    }
