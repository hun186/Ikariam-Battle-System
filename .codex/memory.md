# Project Memory

## Current Focus
- PR #16 is merged; PR #17 focuses on explicit weapon selection and homogeneous single-weapon Light Infantry fallback combat.
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
- Explicit weapon selection preserves native primary behavior and enables homogeneous single-weapon Light Infantry in runtime first; runtime target priority remains separate.
- Mixed-unit Am, cross-wave rebuild, ranged fallback, and secondary-weapon triggers remain guarded or unsupported.
