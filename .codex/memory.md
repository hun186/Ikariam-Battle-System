# Project Memory

## Current Focus
- PR #21 is merged; General Score / gross-damage reporting is now part of the current baseline on top of the PR #20 game-like workbench.
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
- Round execution now uses a 100-round default and a 1000-round maximum safety cap. Reaching the cap is explicit via `safety_limit_reached`; normal battle termination and unsupported boundaries still stop earlier. The browser also states that Cook morale remains unresolved and does not treat the common ~15-Cook player setup as a verified formula.
- Browser defaults use `land-max`, Forge Lv5 on both sides, and a geometry-derived full Hoplite front. The land report renderer follows the supplied in-game screenshot: Flank and First/Main share the front row (`Flank | First | Flank`), while Air defense and Air bomber sit left/right of Third/artillery on the rear row; attacker/defender row order keeps each front line adjacent to the clash. This is presentation-only and does not alter engine slot identity or capacity. A land-max regression locks that 350 Hoplites + 240 Swordsmen deploys Swordsmen to six flank slots with no reserve.
- Round-report layout follow-up aligns the board with the supplied game screenshots: attacker above the clash line, defender below, and the simulator-only initial snapshot is labeled `部署` instead of numeric round 0.
- Land military economy profile work now derives General Score from unmodified resource score basis / 50, exposes score metadata, and adds casualty-based score lost/destroyed plus separate gross damage statistics to the battle summary.
- Game-like battle setup/report work is in progress: setup is unit-row based, ±slot is derived from battlefield slot space and unit size, Workshop levels are per unit, Forge/Hephaistos is side-wide, and round/summary report views are separated.
- All five land geometries are executable with descriptive Town Hall metadata; this does not relax mixed/multi-line/fallback blockers.
- Battle-report calibration is executable through separate run/evaluate APIs with per-field MATCH/MISMATCH/NOT_ASSESSABLE results; a match does not promote empirical evidence into production truth, and life-percent semantics remain unknown.
- Explicit weapon selection preserves native primary behavior and enables homogeneous single-weapon Light Infantry in runtime first; runtime target priority remains separate.
- Mixed-unit Am, cross-wave rebuild, ranged fallback, and secondary-weapon triggers remain guarded or unsupported.
