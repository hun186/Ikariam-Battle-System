from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


IKILL_RULE_ID = "EXP-SWORDSMAN-FLANK-IKILL-EXACT-DIVISION-001"
MKILL_RULE_ID = "EXP-SWORDSMAN-FULL-FLANK-ROW-PIG-MKILL-001"


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
) -> SwordsmanKillAdjustment | None:
    """Column-aware Swordsman flank hypothesis.

    Evidence-backed selector pieces from AT Barbarossa/Xanto:
    - when every reduced-AM Swordsman source column has an even non-zero count,
      D-kill is observed;
    - the historical full-formation 6x7 central case used I-kill when aggregate
      damage divided target HP exactly;
    - M-kill starts P-kill-like, reassigns only some damage, and often loses
      theoretical damage.

    Current candidate for the modern full 6x40 central case:
    - six source columns each contribute seven hits;
    - generic sequential D-kill resolves first (21 deaths in the reviewed case);
    - exactly one lethal-pair overkill per AM row is retained, while the other
      overkills remain discarded;
    - the retained M-pool is added to generic persistent damage and converted
      to additional deaths + persistent damage.

    There are seven AM rows for one central target slot, so seven overkill chunks
    are retained.  This naturally reproduces the user observation:
      258 damage -> 21 + floor(7*156/360) = 24 deaths, 12 damage;
      183 damage -> 21 + floor(7*6/360) = 21 deaths, 42 damage.
    Both residuals display as 99% life under the empirical report rule that life
    percentage is rounded down.

    Accuracy is deliberately not turned into a multiplier.  The paper lists it
    only as a possible higher-level selector for IR/D-kill-column behavior and
    later AT Barbarossa posts still state that the Accuracy algorithm is unknown.
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

    if all(hits % 2 == 0 for hits in hits_by_column):
        return SwordsmanKillAdjustment(
            "d_kill_even_columns",
            baseline_casualties,
            baseline_persistent_damage,
            baseline_overkill_discarded,
            0,
            hit_damage,
            sum(hits // 2 for hits in hits_by_column),
            0,
            0,
            0,
            prior_damage,
        )

    aggregate_damage = prior_damage + incoming_damage
    if prior_damage == 0 and aggregate_damage % hit_points == 0:
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
            sum(hits // 2 for hits in hits_by_column),
            sum(hits % 2 for hits in hits_by_column),
            0,
            0,
            prior_damage,
        )

    # Current modern M-kill calibration is intentionally limited to the exact
    # full 6x40 central reduced-AM shape. Other odd/mixed shapes stay on the
    # generic D-kill baseline until more observations exist.
    if initial_units != 40:
        return None
    if len(hits_by_column) != 6 or any(hits != 7 for hits in hits_by_column):
        return None
    if not (0 < hit_damage < hit_points and 2 * hit_damage >= hit_points):
        return None

    pair_overkill = max(0, 2 * hit_damage - hit_points)
    retained_overkill_events = 7  # one retained lethal-pair overkill per AM row
    recovered_overkill = retained_overkill_events * pair_overkill

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
        "m_kill_full_flank_row_pig",
        casualties,
        persistent_damage,
        discarded_overkill,
        recovered_overkill,
        hit_damage,
        baseline_casualties,
        6,
        0,
        pair_overkill,
        prior_damage,
        retained_overkill_events,
    )
