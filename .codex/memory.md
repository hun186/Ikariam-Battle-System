# Project Memory

## Current Focus
- PR #18 is merged; executable battle-report calibration is the current baseline.
- Workshop upgrades are per unit type; Forge is side-wide.
- All five land IDs use evidence-backed slot geometry and slot-space/unit-size capacity; selection remains explicit.
- Complete reviewer-verified current data is distinct from empirical mechanics.
- Ammo is a pooled shot count; targeting and ignored accuracy are named experimental policies.
- Doctor/Tender healing and Cook morale are separate unknowns.
- Support has separate deployed state; walls and garrison-limit escalation are out of current scope.
- Battle-end state separates actual main-line holders, unresolved fallback candidates, and non-sustaining survivors; fallback-required stops inconclusive and applied assumptions remain unique and conditional.
- Function B must later call `simulate()` without duplicating rules.
- Entry-batch ammo ownership and additive UI-derived HP/munition state are contracted; user-observed ranged fallback and initial-garrison retreat/rejoin remain calibration-only unsupported mechanics.

## Open Handoffs
Naval geometry, automatic Town Hall/garrison/wall selection and transitions, accuracy, target transfer, mixed rows, healing/morale, kill/rounding/SR/IR chronology and secondary triggers require future work.

## Recent Outcomes
- All five land geometries are executable with descriptive Town Hall metadata; this does not relax mixed/multi-line/fallback blockers.
- Battle-report calibration is executable through separate run/evaluate APIs with per-field MATCH/MISMATCH/NOT_ASSESSABLE results; a match does not promote empirical evidence into production truth, and life-percent semantics remain unknown.
- Explicit weapon selection preserves native primary behavior and enables homogeneous single-weapon Light Infantry in runtime first; runtime target priority remains separate.
- Mixed-unit Am, cross-wave rebuild, ranged fallback, and secondary-weapon triggers remain guarded or unsupported.
