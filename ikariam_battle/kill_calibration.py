from __future__ import annotations

from dataclasses import dataclass

from .damage import RoundingPolicy, calculate_damage
from .models import Army, Slot, Wave
from .profiles import ForgeProfile, WorkshopProfile
from .units import UnitRegistry


RULE_ID = "EXP-SWORDSMAN-ODD-COLUMN-MKILL-HYPOTHESIS-001"


@dataclass(frozen=True)
class SwordsmanSlotHypothesis:
    target_slot: Slot
    target_wave: Wave
    casualties: int
    persistent_damage: int
    hit_damage: int
    column_hits: tuple[int, ...]
    baseline_d_kills: int
    odd_column_count: int
    odd_tail_damage: int
    p_recount_per_odd_column: int
    phase_start_damage: int
    mode: str


def _swordsman_flank_wave(waves: list[Wave]) -> Wave | None:
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
        key=lambda slot: slot.damage_position,
    )
    if len(slots) != 6:
        return None
    return wave


def _column_hits_for_target(source_slots: list[Slot], target_index: int, q: int) -> tuple[int, ...]:
    """Return the reduced-Am non-zero count contributed by each source column."""
    result = []
    for slot in sorted(source_slots, key=lambda item: item.damage_position):
        hits = sum(
            1 for row in range(1, slot.units + 1)
            if (row - 1) % q == target_index
        )
        result.append(hits)
    return tuple(result)


def swordsman_flank_mkill_plan(
    volleys: list[dict],
    targets: list[Wave],
    source_army: Army,
    target_army: Army,
    registry: UnitRegistry,
    workshop: WorkshopProfile,
    forge: ForgeProfile,
) -> tuple[SwordsmanSlotHypothesis, ...]:
    """Apply a column-aware Swordsman M-kill hypothesis, not an asserted game rule.

    Evidence-backed structure:
    - Swordsman flank Am has six source columns.
    - Historical tests show all-even reduced-column lengths use D-kill.
    - Full 40x6 flanks address the central four target slots with six 7-hit
      columns and the two outer slots with six 6-hit columns.

    Experimental hypothesis for a two-hit-kill regime when an odd column exists:
    1. Resolve D-kill pairs inside every reduced column.
    2. Keep each odd column's unpaired tail hit in a slot-level pool.
    3. For one lethal D pair per odd column, recount a P/M-like amount capped
       by min(pair overkill, target HP remaining after the first hit).
    4. Add phase-start persistent slot damage (the RR output) to that pool.
    5. Convert the pool into extra casualties + persistent damage.

    Accuracy is intentionally not inserted as an invented numeric multiplier.
    The empirical paper leaves Accuracy's role unresolved but explicitly lists
    IR occurrence / D-kill count per column as hypotheses. Swordsman's fixed
    Accuracy therefore remains a selector/calibration dimension for future
    fixtures rather than a fabricated formula here.
    """
    if source_army.forge_level != 5 or target_army.forge_level != 5:
        return ()
    if len(volleys) != 1:
        return ()
    volley = volleys[0]
    if volley.get("runtime_line") != "flank" or volley.get("source_unit") != "swordsman":
        return ()

    source_wave = volley.get("source_wave_state")
    if not isinstance(source_wave, Wave):
        return ()
    source_wave = _swordsman_flank_wave([source_wave])
    target_wave = _swordsman_flank_wave(targets)
    if source_wave is None or target_wave is None:
        return ()

    source_slots = sorted(
        (slot for slot in source_wave.slots if slot.line == "flank" and slot.units),
        key=lambda slot: slot.damage_position,
    )
    target_slots = sorted(
        (slot for slot in target_wave.slots if slot.line == "flank" and slot.units),
        key=lambda slot: slot.damage_position,
    )
    if len(source_slots) != 6 or len(target_slots) != 6:
        return ()

    source_unit = registry.get("swordsman")
    target_unit = registry.get("swordsman")
    trace = calculate_damage(
        source_unit,
        target_unit,
        int(volley.get("attack_upgrade", 0)),
        target_wave.unit.armor_upgrade,
        source_army.forge_level,
        target_army.forge_level,
        workshop,
        forge,
        RoundingPolicy.FLOOR,
        weapon=source_unit.primary_weapon,
    )
    hit_damage = trace.final_damage
    hp = target_unit.hit_points or 0

    # This hypothesis describes only the observed two-hit D-kill regime.
    if not (0 < hit_damage < hp and 2 * hit_damage >= hp):
        return ()

    result: list[SwordsmanSlotHypothesis] = []
    q = len(target_slots)
    for target_index, slot in enumerate(target_slots):
        column_hits = _column_hits_for_target(source_slots, target_index, q)
        if not column_hits or all(hits % 2 == 0 for hits in column_hits):
            # Historical Swordsman evidence says all-even reduced columns are
            # ordinary D-kill; the generic resolver already handles them.
            continue

        total_hits = sum(column_hits)
        phase_start_damage = slot.damage

        # Preserve the historical exact I-kill subset: when aggregate attack
        # divides target HP exactly, the old full-Swordsman test used I-kill.
        aggregate_damage = total_hits * hit_damage + phase_start_damage
        if phase_start_damage == 0 and aggregate_damage % hp == 0:
            casualties = min(slot.units, aggregate_damage // hp)
            result.append(SwordsmanSlotHypothesis(
                slot, target_wave, casualties, 0, hit_damage, column_hits,
                0, sum(hits % 2 for hits in column_hits), 0, 0,
                phase_start_damage, "exact_indirect_kill",
            ))
            continue

        baseline_d_kills = sum(hits // 2 for hits in column_hits)
        odd_column_count = sum(hits % 2 for hits in column_hits)
        odd_tail_damage = odd_column_count * hit_damage

        remaining_after_first = hp - hit_damage
        pair_overkill = max(0, 2 * hit_damage - hp)
        p_recount_per_odd_column = min(pair_overkill, remaining_after_first)

        pool = (
            phase_start_damage
            + odd_tail_damage
            + odd_column_count * p_recount_per_odd_column
        )
        extra_kills, persistent_damage = divmod(pool, hp)
        casualties = min(slot.units, baseline_d_kills + extra_kills)
        if casualties == slot.units:
            persistent_damage = 0

        result.append(SwordsmanSlotHypothesis(
            slot, target_wave, casualties, persistent_damage, hit_damage,
            column_hits, baseline_d_kills, odd_column_count, odd_tail_damage,
            p_recount_per_odd_column, phase_start_damage,
            "odd_column_d_pair_plus_p_m_recount",
        ))
    return tuple(result)
