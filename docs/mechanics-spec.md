# Mechanics and current-data evidence register

The simulator combines empirical mechanics with current numerical profiles; it is not Gameforge source code. Evidence classes remain separate: `OFFICIAL_CHANGELOG`, `GAMEFORGE_FORUM_PLAYER_TEST`, `COMMUNITY_PTS_TESTED`, `COMMUNITY_REFERENCE_CURRENT`, `USER_PROVIDED_BATTLE_OBSERVATION`, `EMPIRICAL_PAPER`, `DERIVED`, `HYPOTHESIS`, and `UNKNOWN`. A user observation is real calibration input but is **not** an official specification. Sources verified by the reviewer are marked `REVIEWER_WEB_VERIFIED`, not `CODEX_NETWORK_VERIFIED`.

## Versioned profiles and source matrix

| Profile/feature | Evidence | Status |
| --- | --- | --- |
| `battle-system-paper-2020`: Am, physical renumbering, RR | EMPIRICAL_PAPER | implemented; current calibration required |
| SR, IR, partial chronology | EMPIRICAL_PAPER | observed; triggers/generalization UNKNOWN |
| Kill selection, non-standard renumbering | UNKNOWN | strict stops |
| `infinite-horizons-current` complete land/sea values | COMMUNITY_REFERENCE_CURRENT | reviewer web verified 2026-09-24 |
| Naval raw values | COMMUNITY_REFERENCE_CURRENT + GAMEFORGE_FORUM_PLAYER_TEST, *Workshop Tests: Ship Technology*, 2025-06-04 | reviewer web verified |
| v14 Workshop ×5 and Forge direction change | OFFICIAL_CHANGELOG, v14.0.0, 2025-05-21 | reviewer web verified |
| Workshop exact land +5 / naval +10 | COMMUNITY_PTS_TESTED | not promoted to official |
| Forge exact levels 0–5 | COMMUNITY_PTS_TESTED | not promoted to official |
| Doctor/Tender healing ×20 | OFFICIAL_CHANGELOG, v17.0.0, 2026-04-16 | reviewer web verified |
| legacy healing 200 → current 4000 | legacy community/paper + DERIVED | allocation UNKNOWN |
| Cook/Doctor/Tender garrison exclusion | OFFICIAL_CHANGELOG, v17.4.0, 2026-08-11 | applies only to these support units |
| verified-through release | OFFICIAL_CHANGELOG, v17.5.0, 2026-09-08 | no later military/profile change reported |
| `legacy-community-land-targeting` | COMMUNITY_REFERENCE | experimental/calibration policy |
| `legacy-community-battle-end` | COMMUNITY_REFERENCE, REVIEWER_WEB_VERIFIED | sustaining classes and round-boundary termination; calibration required |

## Workshop and Forge ownership

Workshop levels belong to a player’s **unit type**, not the whole army. Every `ArmyUnit` has `attack_upgrade` and `armor_upgrade`; all rows/waves of the same `unit_id` on one side must agree. Duplicate rows aggregate only when unit, wave, and upgrades agree. Forge remains side-wide at level 0–5.

## Battlefield geometry

`land-mini` means Town Hall 1–4/minimum. It has front 3 × 30 space, long-range 3 × 30, flank 0, artillery 1 × 30, bomber 1 × 10, and anti-air 1 × 10. Thus Gyrocopter capacity is 10 and Bombardier capacity is 5. Other stable IDs (`land-small`, `land-medium`, `land-large`, `land-max`) are reserved and rejected until profiles are supplied.

A line stores `slot_space`, not a unit capacity. Deployment uses `floor(slot_space / unit.size)`. With slot space 30 this yields Hoplite 30, Steam Giant 10, Carabineer 7, and Catapult 6. Slots retain physical position and damage position separately. Am targets ascending damage positions; only vector export uses physical order. At round start the following-round formation refills before RR computes `D/N*s`. RR uses the explicit experimental half-up tie policy `EXP-RR-ROUND-HALF-UP-001`, follows damage priority, and preserves deployed + reserve wave damage; this is not claimed as Ikariam truth.

Only deployed waves (`any(slot.units > 0)`) are targetable; reserve-only and destroyed waves are skipped. Cross-line formation fallback remains unknown. If the initial state or a completed round leaves no main-line holder but living light/long-range candidates, both strict and experimental modes stop inconclusive with `UNKNOWN-FORMATION-FALLBACK`; neither continues firing from stale line positions.

## Ammunition, targeting, accuracy, and support boundaries

### Entry-batch ammunition semantics

Finite ammunition is owned by one entry batch (`wave_id`), never by the side, unit type, slot, or individual soldier. Its normal Phase A capacity is `entry quantity × primary ammunition per unit`; the mutable pool begins at that capacity and each firing unit consumes one shot. Two same-unit waves cannot lend or combine shots. Every slot occupied by a wave therefore reports the same `ammo_pool_shots`, `ammo_capacity_shots`, and derived `munition_percent = 100 × pool / normal entry capacity`. This is an explicit Phase A model/derived UI contract, not an independently verified reproduction of Ikariam's tooltip formula. Capacity is frozen when the entry batch is created, and later casualties do not shrink its denominator. Initial-garrison rejoin is excluded and may eventually require a richer replenishment ledger rather than changing this normal denominator silently.

A final partial volley uses named `EXP-AMMO-PARTIAL-ORDER-001`; an exhausted primary does not silently switch weapon.

Experimental targeting uses versioned priorities and `EXP-TARGET-LEGACY-001`: artillery front→flank; long-range front→flank→long-range; front front→long-range→artillery→flank; flank flank→long-range→artillery→front; anti-air bomber→anti-air; bomber artillery→long-range→front→flank. Transfer remains calibration-dependent. In particular, a Swordsman selects enemy flank before front.

Accuracy is stored per weapon, including different secondary accuracy. No complete accuracy algorithm is known: strict emits `UNKNOWN-ACCURACY`; experimental emits `EXP-ACCURACY-IGNORED-001` rather than silently claiming 100% accuracy.

Support effects are distinct: Doctor/Tender are `healing`, Cook is `morale`. They appear in `deployed_support`, not ordinary reserve or Am slots. Strict uses `UNKNOWN-HEALING-ALLOCATION` and `UNKNOWN-MORALE-SUPPORT`; experimental uses separate `EXP-HEAL-NONE-001` and `EXP-MORALE-NONE-001`. Support never enters Am.

Naval forum corroboration is field-specific: HP, armor, size, damage, shown secondary damage, and explicitly finite munition counts may cite *Workshop Tests: Ship Technology*. Accuracy cites only the current community reference because the forum accuracy fields are blank. Omitted munition does not prove infinity.

## Other experimental policies and remaining unknowns

Named policies include pooled I-kill, floor rounding, phase-start simultaneous chronology, no within-phase retarget, RR deployed-total rounding, ammo stop/partial ordering, legacy targeting, ignored accuracy, and separate no-healing/no-morale effects. Responses and events expose IDs. Remaining unknowns include kill selection, rounding selector, SR/IR triggers, complete chronology, target transfer after destruction, mixed-unit/multi-wave Am, secondary weapon trigger, healing/morale allocation, accuracy, non-standard renumbering, naval geometry, and long-duration intervals.

## Battle-end semantics

The versioned legacy/community battle-end profile separates `main_line_classes` (`first`), `fallback_candidate_classes` (`flank`, `second`), and definitely `non_sustaining_classes` (artillery, bomber, anti-air, support). Snapshots expose main-line and fallback counts plus `sustaining`, `fallback_required`, or `not_sustaining`. After simultaneous plans are applied, a definite one-sided main-line loss terminates in that same round and leaves non-sustaining survivors out of casualties. Fallback-required states stop inconclusive. If both sides are definitely not sustaining, `UNKNOWN-BOTH-SIDES-NO-MAIN-LINE-OUTCOME` replaces the former unqualified draw. Initial definite termination timing uses `EXP-BATTLE-END-ROUND-BOUNDARY-001`; strict reports `UNKNOWN-INITIAL-BATTLE-END-TIMING`.

Battle-end evidence remains `CALIBRATION_REQUIRED`. The packaged profile records reviewer-verified community formation evidence and two Gameforge forum player battle-report evidence classes; these are not official specifications. The review did not supply their URLs and this environment could not retrieve them, so the records preserve titles, evidence class, verification actor, and an explicit missing-URL status rather than inventing links.

Experimental results list only assumptions actually reached. Partial-ammunition assumptions are conditional, assumption IDs are unique, and formation fallback is an unsupported boundary rather than an assumption that permits continued combat.

`BattleReportFixture` retains game version, complete scenario, round, casualties, damage%, and life%; damage display percentages can be converted to integer intervals rather than hard-coding a winner.

Scope is unit-vs-unit Phase A. Town walls, wall target/damage rules, and garrison-limit-driven battlefield escalation are not implemented.

## Ranged formation calibration

The packaged calibration fixture is `USER_PROVIDED_BATTLE_OBSERVATION`, not Gameforge proof. Case A observes many surviving units in one ranged entry batch, but no supported exact surviving count: two pooled shots remain, the associated firing-eligible subset in the ranged line is two, additional same-batch units exist, and some non-firing remainder for that volley/formation appears at the front under conditions not yet generalized. Case B observes 838 alive and 282 shots: seven ranged slots are full and the non-firing remainder stays reserve/off-field instead of automatically filling an empty front. These cases establish that one wave may eventually occupy multiple runtime lines and that “no ammo → front” is invalid; they do not assign ammunition ownership to individual soldiers or enable fallback.

`Wave.slots` is structurally capable of storing distinct `line` values while ammunition remains on the parent wave, but the combat pipeline is not calibrated or safe for multi-line wave execution. In particular RR currently keys allocations by `damage_position`, which can collide across lines. `UNKNOWN-MULTILINE-WAVE-COMBAT-SEMANTICS` guards refill, RR, targeting, and firing rather than inventing cross-line semantics. Production deployment deliberately does not use that representational freedom yet. Unit metadata separates `semantic_class`, `native_line`, and runtime slot `line`; legacy `battlefield_class` remains behaviorally authoritative for compatibility. In particular Spearman is audited as semantic `light_infantry` with native/legacy line `first`; this PR does not change targeting or damage behavior.

`UNKNOWN-FORMATION-FALLBACK` remains the public production boundary. Its calibration matrix contains separate unknowns: `UNKNOWN-FALLBACK-PARTIAL-FRONT-TRIGGER`, `UNKNOWN-FALLBACK-PLACEMENT`, `UNKNOWN-FALLBACK-PRIORITY`, `UNKNOWN-FALLBACK-DAMAGE-TRANSFER`, `UNKNOWN-FALLBACK-LONG-RANGE-WEAPON`, and `UNKNOWN-FALLBACK-RR-ORDER`. Placement does not imply knowledge of weapon selection. Initial and completed-round fallback-required states remain inconclusive without another round of stale-line fire.

## Initial-garrison defender privilege (documented unsupported)

`USER_PROVIDED_BATTLE_OBSERVATION` reports a privilege only for units owned by the battle-town owner, already stationed there at battle start, and belonging to the battle-start initial garrison. They may partially retreat into the city, rejoin after a later round, and refill ammunition; retreating a subset reportedly does not proportionally subtract the on-field pool. Allied defenders, attackers, and town-owner batches arriving after battle start instead retreat as a whole batch.

This behavior is **not implemented**. Future provenance and orchestration work is tracked as `UNKNOWN-INITIAL-GARRISON-PARTIAL-RETREAT`, `UNKNOWN-INITIAL-GARRISON-JOIN-BATTLE-AMMO-REFILL`, `UNKNOWN-BATTLE-START-PROVENANCE-PRIVILEGE`, and `UNKNOWN-LATE-JOINING-OWNER-RETREAT-RULE`. Multi-owner continuation is also `UNKNOWN-MULTI-OWNER-BATTLE-CONTINUATION`: current continuation is side-level with one logical owner per side, not a precedent for ejecting one owner independently.

## UI battle-state semantics

Player mode defaults to an upper defender/lower attacker field, visual line slots, reserves, result and unsupported-boundary warnings, and round navigation. Hover/focus tooltips show registry display name, input upgrades, slot HP, and wave munition when applicable. Research mode adds batch IDs, native/current lines, reserve/ammo state, continuation state, events, and assumptions; it does not replace the player view.

`hit_points_percent` is engine-derived slot state using the current persistent-damage representation: `100 × (surviving count × unit HP − persistent slot damage) / (surviving count × unit HP)`. Dead units are absent from both numerator and denominator, matching the user-observed denominator rule. It is not claimed as a fully verified reconstruction of Ikariam's internal HP distribution while kill selection, damage distribution, and RR remain partly experimental. `munition_percent` is wave-level using the Phase A derived entry-batch contract above, so every slot of that wave shares it. Both are additive API fields; existing snapshot fields remain unchanged.
