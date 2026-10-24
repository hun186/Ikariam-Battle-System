# P0 actual two-round pre-volley / post-volley HP & casualty ledger

## Context and limits

This work follows owner-authorized merged PR #79, `main` head `6922bb436a1d1cb9258cbcc76a67baebc7bdc423`. Earlier PRs #78/#79 exercised real engine Round2 *start* using seeded existing wounds without running shots through the seeded cases. This follow-up exercises full public `ikariam_battle.simulate()` **both R1 and R2 combat** and records actual, untouched engine Wave/Slot state at the point **after supported Round2 placement + healing + RR but before individual fire queues are built**.

All armies are **SYNTHETIC**, not new Gameforge observations, not independent holdouts, and not assertions about the official Accuracy, concentration or overkill rules. No production battle formulas or API schemas are changed.

## Controlled baseline

An initial 410-Hoplite trial had insufficient living Reserve at the R2 pre-volley boundary; initial quantity was increased to 750 while the actual First-line deployed capacity remains 350. The prior test failure is preserved in Hosted CI history. This is scenario calibration, not a changed combat formula.


- Land: `land-max`, defender 750 Hoplites (350 deployed / 400 initial Reserve), 3 Gyrocopters and 3 Swordsmen; attacker 350 Hoplites, 3 Gyros, 3 Swordsmen. Baseline 0 Doctor vs 50 Doctors. This preserves some non-native support and low-HP phase cases alongside actual First-line reserve.
- Navy: `naval-max`, defender 48 Rams (36 deployed / 12 initial Reserve), 35 Steam Rams, Forge5, player Rams ATT20 ARM14; attacker 42 Barbarian Wedge Paddlers and 36 Deckwreckers. Baseline 0 Tender vs 50 Tenders. A 48-Ram configuration is **outside the previously calibrated exact 36-Ram in-sample candidate** and must remain a model-only fallback, not an asserted Gameforge match.
- Full `simulate()` with max_rounds=2, require actual Round 1 and Round 2 damage events and defender patient volleys in Round 2. Uses a **scoped `unittest.mock.patch.object`** only for research to capture snapshots precisely when existing `_build_damage_queues` starts; the real function executes normally and the patch is restored afterwards.
- Independently reconcile each Wave's true living count, deployed slot counts and Reserve; first and second-round `casualties` against live wave deltas; global casualty totals; all positive surviving HP, nonnegative Reserve wounds; no R1→R2 resurrection or changed Wave identities. Capture pre-volley snapshot **separately from damage/healing event claims**.

## Support comparison

Support at R1 should not change combat since healing is applied only at subsequent round boundaries. At R2, eligible patient R1 wounds should persist without support and be cleared with 50 Doctors/Tenders before shots. Preserve non-healable machine wounds and cross-wave accuracy/partial healing as separate open research questions; no full-real-game proof is asserted.

Artifacts include full per-round snapshot ledgers and provenance, a concise CSV, and explicit unknowns. The CI workflow runs the new 2-round audit, prior Land Doctor / Naval Tender multiround suites, full pytest, compileall, and uploads generated JSON/CSV.

    PYTHONPATH=. python tools/research/p0_live_round2_prefire_postfire_ledger.py --output-json research-output/p0-live-two-round-ledger.json --output-csv research-output/p0-live-two-round-ledger.csv

    python -m pytest -q tests/unit/test_p0_live_round2_prefire_postfire_ledger.py

## Exact-HEAD Codex P2 remediation (2026-10-24)

Formal Codex review of previous PR #80 source HEAD `fabca5250c0e3fe790f976e1ed5b562c7eebc52f` finished with **two actionable P2s**, not a clean review: (1) R1-end to R2-prefire wounds were only reconciled for the selected Hoplite/Ram patient and (2) Snapshot slot/Reserve HP percentages were not independently recomputed. Both are addressed in the research-only verifier, not production battle logic.

Every attacker and defender Wave now has its **total persistent injury** reconciled across the R1-end → R2-prefire boundary. Without full support (or on the attacker side), the same wave's aggregate Slot+Reserve wound HP must remain conserved. With enough defender Doctors, only eligible Human combat waves can be cleared to zero; Gyrocopter Machine waves must retain wounds. With enough Tenders, all naval combat waves can be cleared; support waves are excluded. Healing event per-Wave lists and amounts are separately cross-checked against these observed HP differences.

Each public Slot percentage is recomputed exactly to two decimals from `(units*unit_hp-damage)/(units*unit_hp)*100` with the simulator's rounding contract; for empty slots it must be zero. Reserve HP percentage is likewise independently recomputed for populated Reserves, and required to be `null` if Reserve has zero units. Mutations changing only an otherwise-valid percentage are caught. Mutations shifting one wound HP on a non-patient wave or Reserve **while also updating the percentage correctly** are caught by the cross-Wave continuity check; this avoids merely duplicating the same validator twice.

The tests and documentation remain entirely synthetic; no official healing allocation/targeting truth has been inferred. This P2 work must be rerun through Hosted CI and formally re-reviewed against the new exact commit. Do not resolve the old threads based solely on code edits or prior green CI.
## Still open on Issue #73

Gameforge independent hit traces, per-slot HP holdout, actual partial-capacity support selection and Healing/RR exact order, cross-Wave Reserve interactions, physical per-row individual D/I/P/IR death and overkill model, observed carrier 53%/65% vs simulated 57%/69% HP. Do not merge without explicit owner authorization.
