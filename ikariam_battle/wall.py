from __future__ import annotations

from dataclasses import dataclass
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


@dataclass
class WallSection:
    """Mutable combat state for one physical Town Wall section.

    The section identity is the First-line damage-position label used by the
    existing battlefield geometry. Damage here is persistent damage accumulated
    inside the current round/redistribution interval. A destroyed section stays
    breached; defender refill into that breach is a separate engine concern.
    """

    damage_position: int
    physical_position: int
    damage: int = 0
    destroyed: bool = False


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


def initial_wall_sections(level: int, field) -> list[WallSection]:
    """Create intact wall-section state without making combat executable.

    Sections mirror the selected battlefield's First-line physical layout while
    retaining damage-position identity for later Attacking Matrix integration.
    """
    wall_stats(level)
    if level == 0:
        return []
    first = getattr(field, "lines", {}).get("first")
    if first is None:
        return []
    return [
        WallSection(
            damage_position=damage_position,
            physical_position=physical_position,
        )
        for physical_position, damage_position in enumerate(first.physical_order, start=1)
    ]


def wall_section_snapshot(sections: list[WallSection], level: int) -> list[dict[str, Any]]:
    """Return JSON-friendly section state for reports/debugging."""
    hp = int(wall_stats(level)["hit_points"] or 0)
    return [
        {
            "damage_position": section.damage_position,
            "physical_position": section.physical_position,
            "damage": section.damage,
            "remaining_hit_points": 0 if section.destroyed else max(0, hp - section.damage),
            "destroyed": section.destroyed,
        }
        for section in sections
    ]


def apply_wall_successful_hit(
    sections: list[WallSection],
    level: int,
    damage_position: int,
    attack_damage: int,
) -> dict[str, Any]:
    """Apply one already-selected successful hit to one intact wall section.

    This intentionally starts after target allocation and Accuracy. It uses the
    same current arithmetic as successful_hits_to_breach_wall_section:
    post-armour damage is attack_damage - wall Armor. Non-penetrating hits are
    rejected without changing state. No ammo semantics are handled here.
    """
    if isinstance(attack_damage, bool) or not isinstance(attack_damage, int) or attack_damage < 0:
        raise ValueError("attack damage must be a non-negative integer")
    stats = wall_stats(level)
    hp = int(stats["hit_points"] or 0)
    armor = int(stats["armor"] or 0)
    section = next(
        (item for item in sections if item.damage_position == damage_position),
        None,
    )
    if section is None:
        raise ValueError(f"unknown wall damage position: {damage_position}")
    if section.destroyed:
        return {
            "applied": False,
            "reason": "section_already_breached",
            "damage_position": damage_position,
            "net_damage": 0,
            "damage_applied": 0,
            "destroyed": True,
        }
    net_damage = attack_damage - armor
    if net_damage <= 0:
        return {
            "applied": False,
            "reason": "effective_attack_not_above_defense",
            "damage_position": damage_position,
            "net_damage": 0,
            "damage_applied": 0,
            "destroyed": False,
        }
    prior_damage = section.damage
    damage_applied = min(net_damage, hp - prior_damage)
    section.damage += damage_applied
    if section.damage >= hp:
        section.damage = hp
        section.destroyed = True
    return {
        "applied": True,
        "reason": "breached" if section.destroyed else "damaged",
        "damage_position": damage_position,
        "net_damage": net_damage,
        "damage_applied": damage_applied,
        "prior_damage": prior_damage,
        "persistent_damage": section.damage,
        "remaining_hit_points": 0 if section.destroyed else hp - section.damage,
        "destroyed": section.destroyed,
    }


def wall_breached_positions(sections: list[WallSection]) -> tuple[int, ...]:
    return tuple(sorted(
        section.damage_position for section in sections if section.destroyed
    ))


def wall_flanks_locked(sections: list[WallSection]) -> bool:
    """Known wall rule: any surviving wall section keeps flanks closed."""
    return any(not section.destroyed for section in sections)


def wall_redistribution_plan(sections: list[WallSection], level: int) -> dict[str, Any]:
    """Describe next-round redistribution without guessing integer rounding.

    The empirical battle-system paper reports that persistent damage on surviving
    wall sections is divided across the wall sections that remain intact at the
    start of the next round. The exact integer remainder selector is not known.
    This helper therefore marks redistribution directly executable only when the
    total divides evenly; otherwise it preserves an explicit unresolved boundary.
    """
    hp = int(wall_stats(level)["hit_points"] or 0)
    surviving = sorted(
        (section for section in sections if not section.destroyed),
        key=lambda section: section.damage_position,
    )
    total_damage = sum(section.damage for section in surviving)
    if not surviving:
        return {
            "status": "no_surviving_sections",
            "surviving_positions": [],
            "total_damage": 0,
            "per_section_damage": None,
            "remainder": 0,
        }
    quotient, remainder = divmod(total_damage, len(surviving))
    if quotient >= hp:
        raise ValueError("surviving wall damage cannot reach full section HP")
    return {
        "status": "exact" if remainder == 0 else "rounding_unresolved",
        "surviving_positions": [section.damage_position for section in surviving],
        "total_damage": total_damage,
        "per_section_damage": quotient if remainder == 0 else None,
        "remainder": remainder,
    }


def apply_exact_wall_redistribution(
    sections: list[WallSection],
    level: int,
) -> dict[str, Any]:
    """Apply next-round wall redistribution only when no rounding choice exists."""
    plan = wall_redistribution_plan(sections, level)
    if plan["status"] == "rounding_unresolved":
        raise ValueError("wall damage redistribution rounding is unresolved")
    if plan["status"] == "no_surviving_sections":
        return plan
    per_section_damage = int(plan["per_section_damage"])
    for section in sections:
        if not section.destroyed:
            section.damage = per_section_damage
    return plan


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
        "section_state_contract": {
            "status": "EXECUTABLE_CORE_AND_EXPERIMENTAL_ENGINE",
            "identity": "selected battlefield First-line damage_position",
            "successful_hit_application": "attack_damage - wall Armor against one already-selected section",
            "breach_condition": "persistent section damage >= section HP",
            "breached_position_refill": "defender First-line position is exposed when its wall section breaches; exact refill timing beyond already-deployed/round-start state remains under calibration",
            "flank_lock": "locked while any wall section survives",
            "round_start_redistribution": "divide surviving-section persistent damage across surviving sections",
            "redistribution_rounding": "unresolved when total damage is not evenly divisible",
        },
        "targeting_contract": {
            "status": "STRICT_GUARDED_EXPERIMENTAL_EXECUTABLE",
            "artillery_priority": ["wall", "first"],
            "rule": "Attacking land artillery targets the Town Wall before ordinary First-line units while intact wall sections are present.",
            "penetration_rule": "effective_attack > effective_defense",
            "non_penetrating_target_consumes_ammunition": False,
            "non_penetrating_target_action": "skip_and_continue_target_priority",
            "experimental_section_allocation": "focus lowest surviving damage-position until breached, then advance",
            "experimental_wall_accuracy": "penetrating Artillery firing tickets are treated as successful wall hits",
            "wall_offense": "not applied in Experimental until current Accuracy/individual-target interaction is calibrated",
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
