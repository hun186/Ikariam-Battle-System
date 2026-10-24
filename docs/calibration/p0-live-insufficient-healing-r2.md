# P0 — Real R1/R2 shots with insufficient Doctor and Tender capacity

## Canonical continuation

Starts at owner-authorized merged [PR #82](https://github.com/hun186/Ikariam-Battle-System/pull/82) from Hosted `main` `6a0aebcb59bd3ba3dbeefc498d1cbd0c653047eb`. This work only extends **research, tests, CI and evidence**, with no modifications to the executable production battle formula, Gameforge accuracy, target concentration, RR or partial healing allocation.

Earlier PRs #78–#81 independently checked isolated boundary/support capacity and *actual* R1-to-R2 synthetic shooting **without support (0)** and **with abundant support (50)**. A crucial missing full-round control was **1 Doctor/Tender whose 4000 HP nominal capacity cannot repair all R1 wounds**: the simulator currently proceeds under explicitly named Experimental **no-partial-applied** fallback, but that is *NOT* a claim that the real game did not heal.

## What the new real simulate() audit does

On each land-max Hoplite/Doctor and naval-max Ram Ship/Tender synthetic control, call actual `simulate()` for **both R1 and R2**, with support count **0 / 1 / 50**. Scoped hook on `_build_damage_queues` captures real pre-volley Round1 and Round2 Slot/Wave/Reserve state without changing combat behavior. Independently validate each public snapshot (HP, percentages, Reserve and Wave conservation), reconcile actual R1/R2 per-wave casualty deltas against round and global deaths, and verify an actually wounded/refilled defender still emits positive shot damage events in R2.

For every Wave at the R1-end → R2-prefire transition, derive eligible human combat wounds (Doctor) or naval combat wounds (Tender) using the live registry, separate support and ineligible machine classes, retain per-wave living units and classify the *current simulator* outcome:

| Support level | Capacity vs eligible Round1 survivor wounds | Current Experimental output, not official game result |
| --- | --- | --- |
| 0 | zero | Preserve every Wave's wounds; no support events |
| 1 | if eligible total exceeds 4000 HP | Named `healing_allocation_unresolved` event and `EXP-HEAL-NONE-001` / `EXP-TENDER-HEAL-NONE-001`; **no invented partial healing**, wounds unchanged through existing RR |
| 50 | capacity 200000 HP and sufficient for controlled cases | Full healing of eligible surviving wounds; not resurrection; machine Gyrocopter remains unhealed |

Support cases must produce identical pre-healing Round1 combat-wave wounds and casualties. For insufficient support, the second-round prefire **combative** wounds must equal the no-support control (model behavior only); for abundant support, only eligible Wave persistent wounds may clear. In all cases, R2 fire executes, and previous dead units remain dead. Corruption tests flip a living count, per-Wave wound HP, an unresolved event into a fake healing event, or event-reported eligible damage: all must be rejected.

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
