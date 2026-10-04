from __future__ import annotations

from dataclasses import dataclass

from .models import Army, Slot, Wave


RULE_ID = "EXP-SWORDSMAN-FULL-FLANK-MKILL-ROW-PIG-001"


@dataclass(frozen=True)
class SwordsmanSlotMKillPlan:
    target_slot: Slot
    target_wave: Wave
    source_columns: int
    hits_per_source_column: int


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


def swordsman_full_flank_mkill_plan(
    volleys: list[dict],
    targets: list[Wave],
    source_army: Army,
    target_army: Army,
) -> tuple[SwordsmanSlotMKillPlan, ...]:
    """Identify the evidence-backed geometry where the row/P-kill hypothesis runs.

    The 2020 empirical paper establishes two relevant observations rather than a
    complete formula:
    - Swordsman columns with an even number of non-zero entries can perform
      ordinary D-kill.
    - Odd-column Swordsman cases can switch to I/M/P-like behavior, and M-kill
      starts like P-kill but loses some theoretical damage.

    For the current full 6x40 Swordsman-vs-Swordsman observation, the Attacking
    Matrix gives 36 hits to the two outer physical slots (6 per source column)
    and 42 hits to the four central slots (7 per source column).  The outer slots
    exactly match D-kill, while the central slots do not.

    This plan therefore selects only the four central 7-per-column slots.  The
    actual casualty/persistent-damage result is derived later from the normal
    engine's computed per-hit damage; Workshop values are not hard-coded.
    """
    if source_army.forge_level != target_army.forge_level:
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

    source_columns = len([
        slot for slot in source_flank.slots
        if slot.line == "flank" and slot.units
    ])
    if source_columns != 6:
        return ()

    result: list[SwordsmanSlotMKillPlan] = []
    for slot in sorted(
        (item for item in target_wave.slots if item.line == "flank"),
        key=lambda item: item.physical_position,
    ):
        # Full 6x40 AM: outer physical slots receive 36 hits = 6/column and
        # remain D-kill; central slots receive 42 = 7/column.
        if slot.physical_position in {1, 6}:
            continue
        result.append(SwordsmanSlotMKillPlan(
            slot, target_wave, source_columns, 7
        ))
    return tuple(result)


def row_pig_mkill_outcome(
    *,
    baseline_casualties: int,
    hit_damage: int,
    hit_points: int,
    source_columns: int,
    hits_per_source_column: int,
) -> tuple[int, int, int]:
    """Experimental M-kill candidate derived from the current 6x40 observation.

    Candidate chronology for one central target slot:
    1. The normal two-hit D-kill baseline resolves first.
    2. Each AM row contains six Swordsman attacks -> three D-kill pairs.
    3. Exactly one pair per row behaves P-kill-like: its overkill is retained in
       a shared M-pool; the other pair overkills are discarded.
    4. The M-pool is then converted to additional deaths plus persistent damage.

    With seven rows this retains seven overkill chunks.  For the reviewed battle:
    - 258 damage -> 21 baseline deaths + (7*156=1092) -> +3 deaths, 12 damage.
    - 183 damage -> 21 baseline deaths + (7*6=42) -> +0 deaths, 42 damage.

    This is an explicit hypothesis, not a claimed Gameforge formula.  It is
    deliberately limited to the two-hit regime and this full-flank geometry.
    """
    if source_columns != 6 or hits_per_source_column != 7:
        raise ValueError("row/P-kill hypothesis requires the full 6x40 central AM shape")
    if hit_points <= 0 or hit_damage <= 0:
        raise ValueError("hit points and damage must be positive")
    if not (hit_damage < hit_points <= 2 * hit_damage):
        raise ValueError("row/P-kill hypothesis currently covers only two-hit D-kill")

    overkill_per_pair = 2 * hit_damage - hit_points
    retained_overkill_events = hits_per_source_column
    m_pool = retained_overkill_events * overkill_per_pair
    extra_casualties, persistent_damage = divmod(m_pool, hit_points)
    return baseline_casualties + extra_casualties, persistent_damage, m_pool
