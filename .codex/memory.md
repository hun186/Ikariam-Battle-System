# Project Memory

## Current Focus
- PR #16 work is based locally on user-confirmed hosted `main` merge `2ac572063209c6d23a3707d2f8bd246939ff70bb`; hosted re-check returns HTTP 403.
- PR #15 corrective baseline is hosted head `003141798b1d20f4b212db4b8730a20b1cf9260a` on `main` base `b70a1888f1f65a45b1b374759773d8a76dff4f54`; network re-check was attempted but this environment returned HTTP 403.
- Workshop upgrades are per unit type; Forge is side-wide.
- `land-mini` uses line slot counts and slot-space/unit-size capacity.
- Complete reviewer-verified current data is distinct from empirical mechanics.
- Ammo is a pooled shot count; targeting and ignored accuracy are named experimental policies.
- Doctor/Tender healing and Cook morale are separate unknowns.
- Support has separate deployed state; walls and garrison-limit escalation are out of current scope.
- Battle-end state separates actual main-line holders, unresolved fallback candidates, and non-sustaining survivors; fallback-required stops inconclusive and applied assumptions remain unique and conditional.
- Function B must later call `simulate()` without duplicating rules.
- Entry-batch ammo ownership and additive UI-derived HP/munition state are contracted; user-observed ranged fallback and initial-garrison retreat/rejoin remain calibration-only unsupported mechanics.

## Open Handoffs
Larger land and naval geometry, accuracy, target transfer, mixed rows, healing/morale, kill/rounding/SR/IR chronology and secondary triggers require calibration.

## Recent Outcomes
- Corrected PR #16 so reserve-only native-same-line waves stop at `UNKNOWN-CROSS-WAVE-FORMATION-REBUILD`, while same-wave refill remains supported; GET metadata now derives every profile, including formation, from `Profiles()`.
