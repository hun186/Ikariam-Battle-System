# P0 actual R1/R2 Slot-by-Slot grouped damage, deaths and HP ledger

## Ground truth and scope

Continues from owner-merged [PR #80](https://github.com/hun186/Ikariam-Battle-System/pull/80) on authoritative `main` `78407ee72f6c72fc197d455815152a8dd1fd38e0`. A **research-only** full two-round `simulate()` instrument, built from **synthetic** land-max 750-Hoplite/Doctor and naval-max 48-Ram/Tender controls, now compares:

- Actual R1/R2 **pre-volley concrete Slot** population/damage from the research-only hook in PR #80.
- Actual grouped emitted `damage` events addressed by `target_side`, `target_unit_id`, `target_wave`, `target_slot` and `target_damage_position`.
- Actual post-fire concrete Slot `units`, `damage`, `casualties`, with R1/R2 per-unit round-level casualty totals as an independent ledger.

The source events are **grouped by source/target** and may contain multiple individual shots. They cannot verify the true Gameforge per-projectile attack trace or official targeting Accuracy, D, I, P or IR mechanics.

## Invariants and caveats

Each concrete Slot must have a stable identity and address across one firing phase. Reconstruct `dead = pre.units - end.units`, require equality with both post Slot casualties and the sum of all target-addressed damage-event casualties. Sum concrete deaths by unit type and compare to the published per-round unit casualties. No hidden resurrection or new identity is accepted during a firing phase.

For current baseline sequential hits only, the internal HP conservation equation is:

    prior_slot_wounds + incoming_grouped_damage = dead * unit_HP + end_slot_wounds + discarded_overkill

Experimentally bounded pooled naval focus and Swordsman M/I-Kill modes are **not official validated individual-hit formulae**. The ledger flags their unresolved nonzero balance as `experimental_focus_or_overkill_model_requires_separate_calibration` and never silently reports it as an exact sequential match. The original grouped event assumptions, residuals and provenance are archived alongside the full numeric Slot ledger.

Negative tests mutate per-slot casualties, grouped event kills, incoming hit damage and target slot address; the affected invariant must reject each without changing production combat code. Structured JSON/CSV are generated only from actual simulator output, never invented observation rows.

## Run

    python -m pytest -q tests/unit/test_p0_live_slot_damage_casualty_ledger.py

    PYTHONPATH=. python tools/research/p0_live_slot_damage_casualty_ledger.py --output-json research-output/p0-live-slot-damage-ledger.json --output-csv research-output/p0-live-slot-damage-ledger.csv

Exact-source-head Hosted CI additionally runs prior PR #80 HP witness tests, land HP baseline and naval support tests, complete pytest, compileall and archives evidence.

## Unresolved Issue #73

This research does **not** supply new Gameforge screenshots, actual independent per-slot HP holdouts, exact insufficient-capacity Doctor/Tender allocation, full healing/RR order, any validated official concentration/overkill mode, or resolution of owner-observed 53%/65% vs current experimental 57%/69% ship HP-bar discrepancy. No production damage or support formulas are changed. Keep Issue #73 open; do not merge Draft PR without explicit owner authorization.
