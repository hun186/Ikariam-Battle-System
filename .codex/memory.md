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
- Entry-batch ammo ownership and additive UI-derived HP/munition state are contracted; mixed source unit types now share one row-major Attacking Matrix while preserving per-wave weapon/ammo state. User-observed ranged fallback and initial-garrison retreat/rejoin remain calibration-only unsupported mechanics.

## Open Handoffs
Naval geometry, automatic Town Hall/garrison/wall selection and transitions, accuracy, the actual healing/morale algorithms, kill-type selectors, rounding selector, SR/IR triggers and secondary-weapon triggers require future work.

## Recent Outcomes
- Barbarian Clubman is now classified as Heavy Infantry / First line independently of its Spearman-based numeric derivation. Mixed unit types in one runtime formation now execute as one row-major Attacking Matrix with a formation-wide frozen target address book, fixing the Catapult + Ram Round-0 debug blocker without merging their weapon/ammo state.
- Entry batches now model real mixed-unit arrivals: multiple unit types share one `entry_batch_id`/arrival round while retaining unit-specific `wave_id` ammo/damage state. Cross-wave rebuild is deferred until same-wave refill actually leaves an open slot, fixing the full-front Steam-Giant-in-Reserve Round-0 false blocker; setup rows also reclaim hidden identity space and render stats as a compact inline strip.
- Browser debugging now exports reproducible JSON: setup downloads use the exact same scenario builder as simulation, while each displayed round (including deployment round 0) can export scenario + summary + current snapshot/events + unsupported/warning/assumption diagnostics for direct bug reports.
- Mechanics status is now a first-class always-available tab that explicitly frames known/partial/unknown mechanics as the simulator's accuracy boundary; a separate Battle System PDF tab credits AT Barbarossa and co-author Xanto, links the original Gameforge thread, and exposes a stable local PDF link with the pre-v13 caveat.
- Round-boundary same-wave rebuild now follows the PDF damage-position priority as a physical center-first re-pack before RR, preventing late-round survivors from remaining stranded in outer slots; setup also exposes a second top `開始模擬` button that shares the same simulation handler.
- Compact report follow-up makes setup identity optional/default-hidden, wraps HP/ATK/DEF safely, removes unit names from slot faces, uses one viewport-clamped floating tooltip for slots/Reserve, and makes destroyed-slot gray identity round-local rather than a persistent tombstone.
- Battle-report UI calibration now retains destroyed slot identity with per-round casualties and vertical HP bars, visualizes Reserve as icon/HP cards using batch-local reserve damage, separates initial deployment from numbered pager navigation, and offers a default-collapsed live HP/ATK/DEF setup preview driven by API Workshop/Forge metadata.
- Am target-slot addresses are now stable within each volley: emptying one addressed slot does not change the modulo divisor or redirect later rows to surviving slots. Formation-class target transfer remains allowed only after the whole higher-priority formation class is eliminated.
- Art of Warfare chronology is now phase-based: Air defence → Air → Artillery → Flank → Long-range → Main. Same-formation sides snapshot firing eligibility simultaneously; earlier-phase casualties suppress later firing; target priority is re-evaluated individual-shot by individual-shot. Experimental uses sequential D-kill baseline, while IR/SR triggers and P/I/IR/PIR/M kill selectors remain explicit unknowns.
- Current land units now expose Human/Machine metadata for future Doctor eligibility. Machine land units are Steam Giant, Battering Ram, Catapult, Mortar, Gyrocopter and Bombardier; actual healing allocation is still not applied.
