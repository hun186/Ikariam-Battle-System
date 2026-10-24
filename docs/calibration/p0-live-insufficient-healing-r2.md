# P0 — Real R1/R2 shots with insufficient Doctor and Tender capacity

## Canonical continuation

Starts at owner-authorized merged [PR #82](https://github.com/hun186/Ikariam-Battle-System/pull/82) from Hosted `main` `6a0aebcb59bd3ba3dbeefc498d1cbd0c653047eb`. This work only extends **research, tests, CI and evidence**, with no modifications to the executable production battle formula, Gameforge accuracy, target concentration, RR or partial healing allocation.

Earlier PRs #78–#81 independently checked isolated boundary/support capacity and *actual* R1-to-R2 synthetic shooting **without support (0)** and **with abundant support (50)**. A crucial missing full-round control was **1 Doctor/Tender versus its actual R1 eligible wounds**: with the current invented Land armies, one 4000-HP Doctor **already covers all** eligible survivor wounds, whereas in the invented Naval armies one 4000-HP Tender **does not**. The naval shortfall leads to the explicitly named Experimental **no-partial-applied** fallback, which does *NOT* mean the real game repaired nobody. The difference was observed in first Hosted tests and is preserved instead of altering combat data to force a predicted outcome.

## What the new real simulate() audit does

On each land-max Hoplite/Doctor and naval-max Ram Ship/Tender synthetic control, call actual `simulate()` for **both R1 and R2**, with support count **0 / 1 / 50**. Scoped hook on `_build_damage_queues` captures real pre-volley Round1 and Round2 Slot/Wave/Reserve state without changing combat behavior. Independently validate each public snapshot (HP, percentages, Reserve and Wave conservation), reconcile actual R1/R2 per-wave casualty deltas against round and global deaths, and verify an actually wounded/refilled defender still emits positive shot damage events in R2.

For every Wave at the R1-end → R2-prefire transition, derive eligible human combat wounds (Doctor) or naval combat wounds (Tender) using the live registry, separate support and ineligible machine classes, retain per-wave living units and classify the *current simulator* outcome:

| Support level | Capacity vs eligible Round1 survivor wounds | Current Experimental output, not official game result |
| --- | --- | --- |
| 0 | zero | Preserve every Wave's wounds; no support events |
| 1 Doctor (Land) | eligible wounds at most 4000 HP in this actual controlled R1 result | **Full-clear** supported subset; Round2 still fires; no fabricated UNKNOWN |
| 1 Tender (Naval) | eligible wounds exceed 4000 HP in this actual controlled R1 result | Named `healing_allocation_unresolved` and `EXP-TENDER-HEAL-NONE-001`; **no invented partial healing**; wounds unchanged through current RR fallback |
| 50 | capacity 200000 HP and sufficient for controlled cases | Full healing of eligible surviving wounds; not resurrection; machine Gyrocopter remains unhealed |

Support cases must produce identical pre-healing Round1 combat-wave wounds and casualties. For insufficient Tender capacity, the second-round prefire **combative** wounds must equal the no-support control (model behavior only); for the sufficient single Doctor or abundant 50 supporters, only eligible Wave persistent wounds may clear. In all cases, R2 fire executes, and previous dead units remain dead. Corruption tests flip a living count, per-Wave wound HP, an unresolved event into a fake healing event, or event-reported eligible damage: all must be rejected.

Structured JSON and CSV evidence preserve the case identity, domain, support count and capacity, exact pre/post R2 Wave/Slot/Reserve numeric state, Round2 source damage-event groups, healing/unknown/redistribution events and source assumptions. Research output is marked as **SYNTHETIC_REAL_SIMULATE_R1_R2_PARTIAL_HEAL_UNKNOWN_NOT_GAME_OBSERVATION**.

## Reproduce

```bash
python -m pytest -q tests/unit/test_p0_live_insufficient_support_round2.py
PYTHONPATH=. python tools/research/p0_live_insufficient_support_round2.py \
  --output-json research-output/p0-live-insufficient-heal-r2.json \
  --output-csv research-output/p0-live-insufficient-heal-r2.csv
```

Hosted exact-head CI runs focused support/wound tests, full regression, Python compile and archives machine-readable synthetic evidence. Require formal exact-head Codex Review and explicit fresh owner instruction before any Merge.

## Remaining scientific unknowns

No Gameforge new observed battle, holdout, or actual individual-hit sequence is supplied. A real game could partially heal with capacity insufficient; how that capacity is assigned across wounded individuals, any true Healing-versus-RR order, Gameforge's per-slot focus/overkill/Accuracy, and original naval 53%/65% vs current model 57%/69% remain **unverified**. Do not replace strict UNKNOWN gates or production algorithms based solely on the controlled 0/1/50 comparison. Keep Issue #73 OPEN.

## First Hosted finding and corrected test expectation

Initial Hosted CI discovered the one-Doctor Land control enters **full-clear**, not insufficient-support; four expectation tests failed, while other tests passed. This was a flawed *test premise*, not a production error. The follow-up fixes test expectations to match independently measured Round1 eligible wounds and uses the one-Tender Naval case for adversarial unknown-partial-healing validation. Do not hardcode unsupported Gameforge healing behavior based on either scenario.

## Formal Codex Round 1: two P2 evidence-integrity fixes

The first formal review of source `3b7da7d687d3aac1c80ae487613bcf647e03095f` returned **two real P2 Findings** even though Hosted CI had passed 735 tests:

1. The global cumulative-death check used the *reported global map* as its unit-ID iteration source. If a nonzero unit casualty entry was deleted from that map, the check could silently ignore it. The updated audit independently sums **all** nonnegative per-round casualty entries after the prior per-wave death checks, then compares against the entire nonzero global map. Regression mutations delete a nonzero attacker or defender casualty key without touching R1/R2 records and require rejection.
2. The prior damage-event guard checked for *any* R1-or-R2 event. This admitted complete disappearance of R1 damage evidence while R2 events survived. The updated guard checks the presence of model damage records **separately for R1 and R2**. Regression mutations delete **all R1 damage events** while retaining R2 and must fail. R2 removal is also explicitly tested.

These are research evidence-integrity fixes, **not** changes to production Gameforge combat rules or historical observations. After the new source HEAD passes exact-head Hosted CI, explicitly reply and resolve both original review threads, then request a **new formal exact-head Codex Review**. Do not treat the old completed review as approval of the new HEAD; keep Draft and do not merge without user authorization.
