from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Mapping


IKILL_RULE_ID = "EXP-SWORDSMAN-FLANK-IKILL-EXACT-DIVISION-001"
MKILL_RULE_ID = "EXP-SWORDSMAN-SYMMETRIC-2HIT-ROW-PM-MKILL-001"


@dataclass(frozen=True)
class DKillBackbone:
    hits_to_kill: int
    kills: int
    tail_hits: int
    overkill_per_kill: int


def d_kill_backbone(hit_points: int, hit_damage: int, hit_count: int) -> DKillBackbone:
    """Return the deterministic n-hit D-kill skeleton for one target slot.

    The skeleton intentionally discards lethal overkill. It is useful as the
    baseline against which P/IR/M redistribution hypotheses are measured.
    """
    if hit_points <= 0 or hit_damage <= 0 or hit_count < 0:
        raise ValueError("hit points, hit damage and hit count must be positive/non-negative")
    hits_to_kill = max(1, ceil(hit_points / hit_damage))
    kills, tail_hits = divmod(hit_count, hits_to_kill)
    return DKillBackbone(
        hits_to_kill=hits_to_kill,
        kills=kills,
        tail_hits=tail_hits,
        overkill_per_kill=max(0, hits_to_kill * hit_damage - hit_points),
    )


@dataclass(frozen=True)
class SwordsmanKillAdjustment:
    mode: str
    casualties: int
    persistent_damage: int
    discarded_overkill: int
    recovered_overkill: int
    hit_damage: int
    baseline_d_kills: int
    odd_column_count: int
    odd_tail_damage: int
    p_m_recount_per_odd_column: int
    phase_start_damage: int
    retained_overkill_events: int = 0
    hits_to_kill: int = 0
    reciprocal_hits_to_kill: int = 0


def swordsman_flank_kill_adjustment(
    *,
    initial_units: int,
    hit_points: int,
    incoming_damage: int,
    prior_damage: int,
    baseline_casualties: int,
    baseline_persistent_damage: int,
    baseline_overkill_discarded: int,
    source_column_hits: Mapping[int, int],
    source_slot_units: Mapping[int, int] | None = None,
    reciprocal_hit_damage: int | None = None,
) -> SwordsmanKillAdjustment | None:
    """Bounded reduced-AM Swordsman flank hypotheses.

    The empirical paper shows that Swordsman deaths are not determined only by
    a target slot's reduced matrix; whole-field formation state can affect the
    selected kill path. Accordingly this function deliberately exposes only
    narrow selectors rather than pretending to implement a general M-kill.

    Supported subsets:
    - all-even source-column lengths: keep the generic sequential D-kill;
    - six odd columns with exact aggregate divisibility: historical I-kill;
    - full 6x40 source formation, six 7-hit columns, and a *symmetric two-hit*
      duel in both directions: bounded row/P-M candidate calibrated by the
      2026-06-25 user battle report.

    The symmetric-two-hit guard is important. A newer 2026-10-02 observation
    has a 2-hit direction near 259 damage and a reciprocal 3-hit direction near
    172 damage, yet produces a materially different casualty/damage pattern.
    Reusing the older seven-row M-pool there would be false generalization.

    Accuracy is not used as a multiplier or probability. Its official role in
    kill-path/redistribution selection remains unresolved.
    """
    if (
        initial_units <= 0
        or hit_points <= 0
        or incoming_damage < 0
        or prior_damage < 0
        or not source_column_hits
    ):
        return None

    hits_by_column = tuple(
        int(source_column_hits[key]) for key in sorted(source_column_hits)
    )
    if any(hits < 0 for hits in hits_by_column):
        return None
    total_hits = sum(hits_by_column)
    if total_hits <= 0 or incoming_damage % total_hits:
        return None

    hit_damage = incoming_damage // total_hits
    if hit_damage <= 0:
        return None
    backbone = d_kill_backbone(hit_points, hit_damage, total_hits)

    if all(hits % 2 == 0 for hits in hits_by_column):
        return SwordsmanKillAdjustment(
            "d_kill_even_columns",
            baseline_casualties,
            baseline_persistent_damage,
            baseline_overkill_discarded,
            0,
            hit_damage,
            backbone.kills,
            0,
            0,
            0,
            prior_damage,
            hits_to_kill=backbone.hits_to_kill,
        )

    six_odd_columns = (
        len(hits_by_column) == 6
        and all(hits > 0 and hits % 2 == 1 for hits in hits_by_column)
    )
    aggregate_damage = prior_damage + incoming_damage
    if (
        six_odd_columns
        and prior_damage == 0
        and aggregate_damage % hit_points == 0
    ):
        casualties, persistent = divmod(aggregate_damage, hit_points)
        casualties = min(initial_units, casualties)
        if casualties == initial_units:
            persistent = 0
        return SwordsmanKillAdjustment(
            "i_kill_exact_division",
            casualties,
            persistent,
            0,
            0,
            hit_damage,
            backbone.kills,
            6,
            0,
            0,
            prior_damage,
            hits_to_kill=backbone.hits_to_kill,
        )

    if initial_units != 40:
        return None
    if source_slot_units is None:
        return None
    source_counts = tuple(
        int(source_slot_units[key]) for key in sorted(source_slot_units)
    )
    if len(source_counts) != 6 or any(units != 40 for units in source_counts):
        return None
    if len(hits_by_column) != 6 or any(hits != 7 for hits in hits_by_column):
        return None
    if backbone.hits_to_kill != 2:
        return None
    if reciprocal_hit_damage is None or reciprocal_hit_damage <= 0:
        return None
    reciprocal = d_kill_backbone(hit_points, reciprocal_hit_damage, total_hits)
    if reciprocal.hits_to_kill != 2:
        return None

    retained_overkill_events = max(hits_by_column)
    recovered_overkill = retained_overkill_events * backbone.overkill_per_kill

    pool = baseline_persistent_damage + recovered_overkill
    extra_kills, persistent_damage = divmod(pool, hit_points)
    casualties = min(initial_units, baseline_casualties + extra_kills)
    if casualties == initial_units:
        persistent_damage = 0
    if casualties < baseline_casualties:
        return None

    discarded_overkill = max(
        0, baseline_overkill_discarded - recovered_overkill
    )
    return SwordsmanKillAdjustment(
        "m_kill_symmetric_two_hit_row_pm",
        casualties,
        persistent_damage,
        discarded_overkill,
        recovered_overkill,
        hit_damage,
        backbone.kills,
        6,
        0,
        backbone.overkill_per_kill,
        prior_damage,
        retained_overkill_events,
        backbone.hits_to_kill,
        reciprocal.hits_to_kill,
    )
