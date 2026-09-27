# Project Memory

## Current Focus
- PR #21 is merged; General Score / gross-damage reporting is now part of the current baseline on top of the PR #20 game-like workbench.
- Workshop upgrades are per unit type; Forge is side-wide.
- All five land IDs use evidence-backed slot geometry and slot-space/unit-size capacity; selection remains explicit.
- Complete reviewer-verified current data is distinct from empirical mechanics.
- Ammo is a pooled shot count. Art of Warfare firing chronology and runtime-line target priorities are executable contracts; ignored accuracy remains a named experimental policy.
- Doctor/Tender healing and Cook morale are separate unknowns.
- Support has separate deployed state; walls and garrison-limit escalation are out of current scope.
- Battle-end state separates actual main-line holders, unresolved fallback candidates, and non-sustaining survivors; fallback-required stops inconclusive and applied assumptions remain unique and conditional.
- Function B must later call `simulate()` without duplicating rules.
- Entry-batch ammo ownership and additive UI-derived HP/munition state are contracted; user-observed ranged fallback and initial-garrison retreat/rejoin remain calibration-only unsupported mechanics.

## Open Handoffs
Naval geometry, automatic Town Hall/garrison/wall selection and transitions, accuracy, mixed rows, the actual healing/morale algorithms, kill-type selectors, rounding selector, SR/IR triggers and secondary-weapon triggers require future work.

## Recent Outcomes
- Battle-report UI calibration now retains destroyed slot identity with per-round casualties and vertical HP bars, visualizes Reserve as icon/HP cards using batch-local reserve damage, separates initial deployment from numbered pager navigation, and offers a default-collapsed live HP/ATK/DEF setup preview driven by API Workshop/Forge metadata.
- Am target-slot addresses are now stable within each volley: emptying one addressed slot does not change the modulo divisor or redirect later rows to surviving slots. Formation-class target transfer remains allowed only after the whole higher-priority formation class is eliminated.
- Art of Warfare chronology is now phase-based: Air defence → Air → Artillery → Flank → Long-range → Main. Same-formation sides snapshot firing eligibility simultaneously; earlier-phase casualties suppress later firing; target priority is re-evaluated individual-shot by individual-shot. Experimental uses sequential D-kill baseline, while IR/SR triggers and P/I/IR/PIR/M kill selectors remain explicit unknowns.
- Current land units now expose Human/Machine metadata for future Doctor eligibility. Machine land units are Steam Giant, Battering Ram, Catapult, Mortar, Gyrocopter and Bombardier; actual healing allocation is still not applied.
- Round combat statistics now expose per-side damage dealt/taken and cumulative values. Doctor presence is evidence-safe: healing amounts are null while allocation is unresolved, with `healing_status` exposing the 4000 derived capacity reference without treating it as a subtraction formula.
- Morale handling is explicit but not fabricated: results expose per-side `morale_status` and Cook counts; strict stops at `UNKNOWN-MORALE-SUPPORT`, experimental continues under `EXP-MORALE-NONE-001` without applying Cook effects, and the common ~15-Cook setup remains explanatory rather than a verified formula.
- HTTP long-battle transport is summary-first and stateless: `simulate()` stays complete in memory, while API responses return compact summary or bounded round pages (browser cache 10 rounds, API maximum 20), preventing hundreds of rounds from being buffered into one response.
- Round execution now uses a 100-round default and a 1000-round maximum safety cap. Reaching the cap is explicit via `safety_limit_reached`; normal battle termination and unsupported boundaries still stop earlier. The browser also states that Cook morale remains unresolved and does not treat the common ~15-Cook player setup as a verified formula.
- Browser defaults use `land-max`, Forge Lv5 on both sides, and a geometry-derived full Hoplite front. The land report renderer follows the supplied in-game screenshot: Flank and First/Main share the front row (`Flank | First | Flank`), while Air defense and Air bomber sit left/right of Third/artillery on the rear row; attacker/defender row order keeps each front line adjacent to the clash. This is presentation-only and does not alter engine slot identity or capacity. A land-max regression locks that 350 Hoplites + 240 Swordsmen deploys Swordsmen to six flank slots with no reserve.
- Round-report layout follow-up aligns the board with the supplied game screenshots: attacker above the clash line, defender below, and the simulator-only initial snapshot is labeled `部署` instead of numeric round 0.
