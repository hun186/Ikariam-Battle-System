from __future__ import annotations

from dataclasses import dataclass

from .models import Army, Slot, Wave


RULE_ID = "EXP-SWORDSMAN-FULL-FLANK-MKILL-CALIBRATION-001"


@dataclass(frozen=True)
class SwordsmanSlotCalibration:
    target_slot: Slot
    target_wave: Wave
    casualties: int
    reported_damage_percent: int
    persistent_damage: int


# One reviewer/user-supplied current battle observation.  This is deliberately
# narrow: it is not a general M-kill selector and must not be extrapolated to
# other upgrade/Forge combinations.
_OBSERVED_OUTCOMES = {
    # source attack upgrade, target armor upgrade:
    # central casualties, central displayed damage percentage.
    (24, 18): (24, 1),
    (18, 26): (21, 1),
}


def _full_swordsman_flank_wave(waves: list[Wave]) -> Wave | None:
    candidates = [
        wave for wave in waves
        if wave.unit.unit_id == "swordsman"
        and len([slot for slot in wave.slots if slot.line == "flank" and slot.units]) == 6
    ]
    if len(candidates) != 1:
        return None
    wave = candidates[0]
    slots = sorted(
        (slot for slot in wave.slots if slot.line == "flank" and slot.units),
        key=lambda slot: slot.physical_position,
    )
    if [slot.physical_position for slot in slots] != [1, 2, 3, 4, 5, 6]:
        return None
    if any(slot.units != 40 or slot.capacity != 40 for slot in slots):
        return None
    return wave


def swordsman_full_flank_plan(
    volleys: list[dict],
    targets: list[Wave],
    source_army: Army,
    target_army: Army,
    *,
    target_hit_points: int,
) -> tuple[SwordsmanSlotCalibration, ...]:
    """Return the exact user-observation calibration when its full scope matches.

    Evidence scope:
    - land-max style full flank: one 6-slot Swordsman wave, 40 units per slot;
    - both sides Forge 5;
    - phase-start target flank is undamaged;
    - Workshop pair is exactly 24 ATK -> 18 DEF or 18 ATK -> 26 DEF.

    Outer physical positions 1 and 6 are already reproduced by the generic
    sequential D-kill baseline (18 deaths, no persistent damage), so this plan
    only overrides the four central 42-hit positions.
    """
    if source_army.forge_level != 5 or target_army.forge_level != 5:
        return ()
    if len(volleys) != 1:
        return ()
    volley = volleys[0]
    if (
        volley.get("runtime_line") != "flank"
        or volley.get("source_unit") != "swordsman"
    ):
        return ()

    source_wave = volley.get("source_wave_state")
    if not isinstance(source_wave, Wave):
        return ()
    source_flank = _full_swordsman_flank_wave([source_wave])
    target_wave = _full_swordsman_flank_wave(targets)
    if source_flank is None or target_wave is None:
        return ()
    if any(slot.damage for slot in target_wave.slots if slot.line == "flank"):
        return ()

    observed = _OBSERVED_OUTCOMES.get(
        (int(volley.get("attack_upgrade", -1)), target_wave.unit.armor_upgrade)
    )
    if observed is None:
        return ()
    casualties, damage_percent = observed

    result: list[SwordsmanSlotCalibration] = []
    for slot in sorted(
        (item for item in target_wave.slots if item.line == "flank"),
        key=lambda item: item.physical_position,
    ):
        if slot.physical_position in {1, 6}:
            continue
        survivors = 40 - casualties
        alive_hp = survivors * target_hit_points
        # The battle report supplied a whole-percent residual state (99% life,
        # represented here as 1% damage). Exact UI rounding semantics are still
        # unresolved, so choose the largest integer damage compatible with a
        # one-percent round-up interval. This yields ~99.01% engine HP and keeps
        # the observation explicit rather than inventing a hidden formula.
        persistent_damage = max(1, alive_hp * damage_percent // 100)
        result.append(SwordsmanSlotCalibration(
            slot, target_wave, casualties, damage_percent, persistent_damage
        ))
    return tuple(result)
