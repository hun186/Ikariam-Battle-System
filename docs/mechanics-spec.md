# Mechanics and current-data evidence register

The simulator combines empirical mechanics with current numerical profiles; it is not Gameforge source code. The primary empirical paper is *Ikariam Battle System* (AT Barbarossa, Xanto; 2020-07-16), originally shared by AT Barbarossa in the Gameforge EN forum thread `https://forum.ikariam.gameforge.com/forum/thread/43268-ikariam-battle-system/`. The paper's own/forum warning that its scenarios and tests predate version 13 is preserved: it is an algorithmic/evidence source, not authority for current unit numbers. Evidence classes remain separate: `OFFICIAL_CHANGELOG`, `GAMEFORGE_FORUM_PLAYER_TEST`, `COMMUNITY_PTS_TESTED`, `COMMUNITY_REFERENCE_CURRENT`, `USER_PROVIDED_BATTLE_OBSERVATION`, `EMPIRICAL_PAPER`, `DERIVED`, `HYPOTHESIS`, and `UNKNOWN`. A user observation is real calibration input but is **not** an official specification. Sources verified by the reviewer are marked `REVIEWER_WEB_VERIFIED`, not `CODEX_NETWORK_VERIFIED`.

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
| `legacy-community-land-targeting` | GAMEFORGE_IN_GAME_HELP + USER_PROVIDED_BATTLE_OBSERVATION corroboration | executable formation firing order and target-priority contract; IR/SR/kill selectors remain separate unknowns |
| `legacy-community-battle-end` | COMMUNITY_REFERENCE, REVIEWER_WEB_VERIFIED | sustaining classes and round-boundary termination; calibration required |
| `formation-land` | GAMEFORGE_IN_GAME_HELP + EMPIRICAL_PAPER; USER_PROVIDED_BATTLE_OBSERVATION corroboration | deterministic placement for all five land geometries; single-weapon Light fallback combat supported |
| `military-economy-current` | COMMUNITY_REFERENCE_CURRENT + derived score-basis validation | player land General Score metadata/reporting; score = unmodified resource basis / 50; combat buffs do not change score |

## Formation and runtime roles

Formation is separate from combat: planning establishes runtime lines, weapon eligibility is selected separately, runtime source line selects target-line priority, the Attacking Matrix distributes attacks among target slots, and only then do damage, kills, and redistribution occur. The Attacking Matrix never decides which units enter a line.

The versioned `formation-land` profile distinguishes tactical `semantic_class`, preferred `native_line`, compatibility-only `battlefield_class`, and authoritative runtime `Slot.line`. Its first-line eligible classes, precedence, and fallback classes are executable planner inputs and are validated for consistency. For first line, Heavy precedes eligible Light. A native-first Light remains eligible independently of fallback; a native-flank Light may enter first only when its semantic class is explicitly fallback-eligible. A partial Heavy batch owns its slot (one slot never mixes types/batches), Light fills only other front slots, and front allocation occurs before remaining Light can enter its native flank. The pure planner calculates this rule and never mutates registry metadata. Thus a Swordsman remains native flank while its planned runtime line can be `first`.

The paper's standard physical damage-label layouts are first/second `[6, 4, 2, 1, 3, 5, 7]`, third `[5, 3, 1, 2, 4]`, flank `[6, 4, 2, 1, 3, 5]`, balloon `[1, 2]`, and anti-balloon `[2, 1]`. Each geometry uses the specified centered subset, except that one-slot anti-balloon retains the existing `(1,)` compatibility label. These arrays remain `EMPIRICAL_PAPER` evidence, distinct from the community slot geometry. The formation profile explicitly delegates executable deployment order to `battlefield_geometry.damage_priority`; the planner validates that authority and refuses an unsupported alternative. Each battlefield geometry is the single executable source for its center-first deployment order while storing physical position separately. Non-standard renumbering remains unresolved.

Formation legality is not combat knowledge. Separate Heavy and Light slots can coexist in runtime first line and snapshots serialize native plus runtime lines. Weapon selection is an explicit step: native combat retains its primary weapon, while a non-native runtime-first Light with exactly one registry weapon deterministically uses that weapon. This supports homogeneous Swordsman-first combat without an unknown fallback rule. `UNKNOWN-FALLBACK-LIGHT-INFANTRY-COMBAT` is now limited to a non-native Light whose weapon is not uniquely selectable; `UNKNOWN-MIXED-UNIT-AM-ROWS` still rejects multiple unit types in one runtime line. `UNKNOWN-MULTILINE-WAVE-COMBAT-SEMANTICS`, `UNKNOWN-FALLBACK-LONG-RANGE-WEAPON`, and `UNKNOWN-SECONDARY-WEAPON-TRIGGER` remain protected. Official/help formation rules and user corroboration do not establish mixed Am rows, RR slot-internal individual allocation, IR/SR trigger conditions, special kill-type selectors, or secondary-weapon selection. Firing chronology and formation target priority are established separately by the Art of Warfare help contract described below.

### Formation filling, firing chronology, and target priority

Formation **filling order** and **shot sequence** are separate Art of Warfare rules. Land formation filling order is Air → Air defence → Artillery → Long-range combat → Close-combat → Flanks. Land shot sequence is Air defence (`anti-balloon`) → Air (`balloon`) → Artillery (`third`) → Flanks (`flank`) → Long-range (`second`) → Main battle line (`first`).

The same formation on both sides shoots simultaneously. The engine therefore snapshots both sides' firing eligibility at the start of each formation phase. Casualties caused in one formation phase immediately suppress firing in every later phase, but a casualty resolved while processing one side of a phase cannot cancel the opposing side's already-snapshotted firing eligibility in that same formation phase.

Formation target priority is also executable and belongs to runtime line, not unit identity:

- Artillery / `third`: Main/First → Flank.
- Flank: Flank → Long-range/Second → Artillery/Third → Main/First.
- Long-range / `second`: Main/First → Flank → Long-range/Second.
- Main / `first`: Main/First → Long-range/Second → Artillery/Third → Flank.
- Air defence / `anti-balloon`: Air/Balloon → Air defence.
- Air / `balloon`: Artillery/Third → Long-range/Second → Main/First → Flank.

Individual shots re-evaluate the highest surviving target formation. Once a higher-priority formation is eliminated, later shots in the same firing phase may transfer to the next listed formation. This is **formation-class transfer only**. Within one volley against one target formation, the Am row→damage-position address set is frozen when that formation is first targeted. If an addressed slot empties mid-volley, later rows that still address that slot are not remapped to surviving slots; the shot remains addressed to the empty slot and deals no damage. Only when the whole target formation is gone may a later shot transfer to the next formation class. Artillery therefore never silently attacks Long-range, Artillery, or Air: if neither Main nor Flank remains, it has no valid target.

At round boundary, `_prepare_round_start()` first re-establishes the following round's existing same-wave placements through `_rebuild_formation()`: survivors plus that wave's Reserve are packed into the wave's already-existing slots in ascending damage-position order, which is the empirical center-first physical order. It then applies RR using those deployed quantities, and only afterward may fire be planned. Cross-wave replacement after casualties is not silently inferred, and rebuild does not create new slots or cross runtime lines.

A reserve-only combat wave is not itself evidence that cross-wave rebuilding is needed. At each round boundary, existing waves first center-pack and refill from their own Reserve. Only if that process leaves a real empty physical slot and another active reserve-only wave is formation-profile-eligible for that line does `UNKNOWN-CROSS-WAVE-FORMATION-REBUILD` fire. The same requirement is re-evaluated after each round's volleys and casualties, before fallback/continuation/termination logic, because a deployed wave can be wiped during combat and expose a vacancy that did not exist at round start. That post-combat evaluation first projects the already-supported center-first refill of each wave into its own existing slots without mutating round state. Empty slots still owned by a wave are therefore consumed by that wave's own Reserve first; only physical vacancies left after this projection can trigger a different reserve-only wave's cross-wave boundary. This avoids Round-0 false blockers such as a full Hoplite front with Steam Giants waiting in Reserve, while still refusing to invent the later Hoplite→Steam-Giant handoff when an actual slot becomes available. Eligibility includes native and configured fallback placement. A single wave's ordinary reserve refill remains supported; unrelated-line reserves and support units are not cross-wave candidates.

## Workshop and Forge ownership

Workshop levels belong to a player’s **unit type**, not the whole army. Every `ArmyUnit` has `attack_upgrade` and `armor_upgrade`; all rows/waves of the same `unit_id` on one side must agree. Duplicate rows aggregate only when unit, wave, and upgrades agree. Forge remains side-wide at level 0–5.

## Battlefield geometry

All five land IDs are executable. Slot count × slot space is:

| ID (descriptive Town Hall range) | First | Second | Flank | Third | Balloon | Anti-balloon |
| --- | --- | --- | --- | --- | --- | --- |
| `land-mini` (1–4) | 3 × 30 | 3 × 30 | none | 1 × 30 | 1 × 10 | 1 × 10 |
| `land-small` (5–9) | 5 × 30 | 5 × 30 | 2 × 30 | 2 × 30 | 1 × 20 | 1 × 20 |
| `land-medium` (10–16) | 7 × 30 | 7 × 30 | 4 × 30 | 3 × 30 | 1 × 30 | 1 × 30 |
| `land-large` (17–24) | 7 × 40 | 7 × 40 | 6 × 30 | 4 × 30 | 2 × 20 | 2 × 20 |
| `land-max` (25+) | 7 × 50 | 7 × 50 | 6 × 40 | 5 × 30 | 2 × 30 | 2 × 30 |

Slot-count/space geometry is reviewer-web-verified community reference material hosted by Gameforge, not Gameforge source code. The current Gameforge battlefield page independently corroborates size-dependent structure and selected capacities. Battlefield selection is always the explicit scenario `battlefield` value; Town Hall ranges are display metadata only. Town Hall/wall inputs, automatic selection, garrison-limit escalation, open-field conversion, and mid-battle resizing are not implemented.

A line stores `slot_space`, not a unit capacity. Deployment uses `floor(slot_space / unit.size)`. With slot space 30 this yields Hoplite 30, Steam Giant 10, Carabineer 7, and Catapult 6. Slots retain physical position and damage position separately. Am targets ascending damage positions; only vector export uses physical order. At round start the following-round formation refills before RR computes `D/N*s`. RR uses the explicit experimental half-up tie policy `EXP-RR-ROUND-HALF-UP-001`, follows damage priority, and preserves deployed + reserve wave damage; this is not claimed as Ikariam truth.

Only deployed waves (`any(slot.units > 0)`) are targetable; reserve-only and destroyed waves are skipped. Art of Warfare line-role priority is modeled as a known contract: target priority derives from runtime `Slot.line`; native line is only a reserve-only internal compatibility fallback. Weapon selection remains a separate responsibility: a runtime-first Swordsman uses its sole `primary` weapon, while its target priority comes from `targeting.priorities["first"]`. Multi-weapon ranged fallback and secondary triggers remain unknown. If a completed round requires an unimplemented cross-wave rebuild (including long-range fallback), both policies stop inconclusive with `UNKNOWN-FORMATION-FALLBACK`; neither continues firing from stale positions.

## Ammunition, targeting, accuracy, and support boundaries

### Entry-batch ammunition semantics

An arrival batch is identified by `entry_batch_id` and may contain many unit types that enter together. Each unit type inside that arrival batch has its own unit-state `wave_id`, because ammunition and persistent damage must not be shared across different unit types. Since formation and runtime state use `(unit_id, wave_id)` as state identity, the same pair is rejected if explicitly reused across different entry batches; repeated rows inside the same entry batch/state identity may aggregate. Missing identity fields retain backward-compatible defaults, but a present `wave_id` or `entry_batch_id` must be a non-empty string and is never silently treated as absent. Finite ammunition is therefore owned by one unit-state wave, never by the whole arrival batch, side, slot, or individual soldier. Its normal Phase A capacity is `entry quantity × primary ammunition per unit`; the mutable pool begins at that capacity and each firing unit consumes one shot. Two same-unit waves cannot lend or combine shots. Every slot occupied by a wave therefore reports the same `ammo_pool_shots`, `ammo_capacity_shots`, and derived `munition_percent = 100 × pool / normal entry capacity`. This is an explicit Phase A model/derived UI contract, not an independently verified reproduction of Ikariam's tooltip formula. Capacity is frozen when the entry batch is created, and later casualties do not shrink its denominator. Initial-garrison rejoin is excluded and may eventually require a richer replenishment ledger rather than changing this normal denominator silently.

A final partial volley uses named `EXP-AMMO-PARTIAL-ORDER-001`; native ranged selection remains primary, and an exhausted primary does not silently switch weapon.

Targeting uses the executable Art of Warfare priority table above; the former experimental legacy-targeting assumption is no longer active. Target priority is a property of the runtime line, not the unit type: a Swordsman in runtime flank uses `targeting.priorities["flank"]` (flank before long-range), while a Swordsman deployed in runtime first uses `targeting.priorities["first"]`. Individual shots re-evaluate the current highest-priority surviving formation, so target transfer after a formation is destroyed is executable rather than an unknown blocker. Active-weapon selection remains a separate step.

Accuracy is stored per weapon, including different secondary accuracy. No complete accuracy algorithm is known: strict emits `UNKNOWN-ACCURACY`; experimental emits `EXP-ACCURACY-IGNORED-001` rather than silently claiming 100% accuracy.

Support effects are distinct: Doctor/Tender are `healing`, Cook is `morale`. They appear in `deployed_support`, not ordinary reserve or Am slots. Strict uses `UNKNOWN-HEALING-ALLOCATION` and `UNKNOWN-MORALE-SUPPORT`; experimental uses separate `EXP-HEAL-NONE-001` and `EXP-MORALE-NONE-001`. Future support batches apply those Experimental assumptions when the batch arrives, not only during Round-0 preflight, so ignored support is always explicit. The reach event carries the affected side and round; support scheduled beyond the reached simulation horizon remains `not_reached`, and per-round healing observability switches from known zero to unknown only when that side's Doctor boundary is actually reached. Arrival diagnostics aggregate repeated state waves of the same unit type within one entry batch, so `entry_batch_arrived.details.units` reports total quantity by `unit_id`. Support never enters Am.

Current land units expose `unit_class = human|machine`. Machine land units are Steam Giant, Battering Ram, Catapult, Mortar, Gyrocopter, and Bombardier; the other current land units are Human. Doctor eligibility is therefore constrained to Human land units, but this metadata does not by itself enable healing: allocation and the exact Healing/RR ordering remain unresolved.

Naval forum corroboration is field-specific: HP, armor, size, damage, shown secondary damage, and explicitly finite munition counts may cite *Workshop Tests: Ship Technology*. Accuracy cites only the current community reference because the forum accuracy fields are blank. Omitted munition does not prove infinity.

## Other experimental policies and remaining unknowns

Current named Experimental policies include `EXP-D-KILL-SEQUENTIAL-001` (sequential D-kill baseline with overkill discarded), `EXP-SLOT-DAMAGE-EVEN-001` (materialize RR aggregate slot damage evenly across surviving individuals when needed), `EXP-IR-DISABLED-001`, `EXP-SR-DISABLED-001`, floor rounding, RR deployed-total rounding, ammo stop/partial ordering, ignored accuracy, and separate no-healing/no-morale effects. Responses and events expose only assumptions actually reached. The former `EXP-I-KILL-001`, `EXP-CHRONOLOGY-001`, `EXP-RETARGET-NONE-001`, and `EXP-TARGET-LEGACY-001` policies are superseded and are not emitted by the current engine.

Remaining unknowns include the general kill-type selector (including when P-kill, I-kill, IR-kill, PIR-kill or M-kill applies), rounding selector, SR/IR triggers, exact within-slot individual damage allocation after RR, mixed-unit/multi-wave Am, secondary-weapon trigger, healing/morale allocation, accuracy, non-standard renumbering, naval geometry, and long-duration intervals. Formation firing chronology and class-level target transfer after destruction are no longer listed as unknowns.

## Battle-end semantics

The versioned legacy/community battle-end profile separates `main_line_classes` (`first`), `fallback_candidate_classes` (`flank`, `second`), and definitely `non_sustaining_classes` (artillery, bomber, anti-air, support). Snapshots expose main-line and fallback counts plus `sustaining`, `fallback_required`, or `not_sustaining`. After the ordered formation phases for a round are resolved, a definite one-sided main-line loss terminates in that same round and leaves non-sustaining survivors out of casualties. Fallback-required states stop inconclusive. If both sides are definitely not sustaining, `UNKNOWN-BOTH-SIDES-NO-MAIN-LINE-OUTCOME` replaces the former unqualified draw. Initial definite termination timing uses `EXP-BATTLE-END-ROUND-BOUNDARY-001`; strict reports `UNKNOWN-INITIAL-BATTLE-END-TIMING`.

Battle-end evidence remains `CALIBRATION_REQUIRED`. The packaged profile records reviewer-verified community formation evidence and two Gameforge forum player battle-report evidence classes; these are not official specifications. The review did not supply their URLs and this environment could not retrieve them, so the records preserve titles, evidence class, verification actor, and an explicit missing-URL status rather than inventing links.

Experimental results list only assumptions actually reached. Partial-ammunition assumptions are conditional, assumption IDs are unique, and formation fallback is an unsupported boundary rather than an assumption that permits continued combat.

`BattleReportFixture` retains game version, complete scenario, round, casualties, damage%, and life%; damage display percentages can be converted to integer intervals rather than hard-coding a winner.

Scope is unit-vs-unit Phase A. Executable geometry does not relax mixed-unit Am, multi-line-wave, cross-wave rebuild, fallback, ranged-weapon, or secondary-trigger guards. Town walls, wall target/damage rules, and garrison-limit-driven battlefield escalation or mid-battle transitions are not implemented.

## Ranged formation calibration

The packaged calibration fixture is `USER_PROVIDED_BATTLE_OBSERVATION`, not Gameforge proof. Case A observes many surviving units in one ranged entry batch, but no supported exact surviving count: two pooled shots remain, the associated firing-eligible subset in the ranged line is two, additional same-batch units exist, and some non-firing remainder for that volley/formation appears at the front under conditions not yet generalized. Case B observes 838 alive and 282 shots: seven ranged slots are full and the non-firing remainder stays reserve/off-field instead of automatically filling an empty front. These cases establish that one wave may eventually occupy multiple runtime lines and that “no ammo → front” is invalid; they do not assign ammunition ownership to individual soldiers or enable fallback.

`Wave.slots` is structurally capable of storing distinct `line` values while ammunition remains on the parent wave, but the combat pipeline is not calibrated or safe for multi-line wave execution. In particular RR currently keys allocations by `damage_position`, which can collide across lines. `UNKNOWN-MULTILINE-WAVE-COMBAT-SEMANTICS` guards rebuild, RR, targeting, and firing. Unit metadata separates `semantic_class`, `native_line`, runtime slot `line`, and legacy `battlefield_class`. Deployment uses semantic/native formation rules, targeting uses runtime lines, and battle-end holding uses runtime first-line occupancy; `battlefield_class` remains serialized compatibility metadata and legacy profile vocabulary. Spearman remains semantic `light_infantry` with native/legacy line `first`.

`UNKNOWN-FORMATION-FALLBACK` remains the public production boundary. Its calibration matrix contains separate unknowns: `UNKNOWN-FALLBACK-PARTIAL-FRONT-TRIGGER`, `UNKNOWN-FALLBACK-PLACEMENT`, `UNKNOWN-FALLBACK-PRIORITY`, `UNKNOWN-FALLBACK-DAMAGE-TRANSFER`, `UNKNOWN-FALLBACK-LONG-RANGE-WEAPON`, and `UNKNOWN-FALLBACK-RR-ORDER`. Placement does not imply knowledge of weapon selection. Initial and completed-round fallback-required states remain inconclusive without another round of stale-line fire.

## Initial-garrison defender privilege (documented unsupported)

`USER_PROVIDED_BATTLE_OBSERVATION` reports a privilege only for units owned by the battle-town owner, already stationed there at battle start, and belonging to the battle-start initial garrison. They may partially retreat into the city, rejoin after a later round, and refill ammunition; retreating a subset reportedly does not proportionally subtract the on-field pool. Allied defenders, attackers, and town-owner batches arriving after battle start instead retreat as a whole batch.

This behavior is **not implemented**. Future provenance and orchestration work is tracked as `UNKNOWN-INITIAL-GARRISON-PARTIAL-RETREAT`, `UNKNOWN-INITIAL-GARRISON-JOIN-BATTLE-AMMO-REFILL`, `UNKNOWN-BATTLE-START-PROVENANCE-PRIVILEGE`, and `UNKNOWN-LATE-JOINING-OWNER-RETREAT-RULE`. Multi-owner continuation is also `UNKNOWN-MULTI-OWNER-BATTLE-CONTINUATION`: current continuation is side-level with one logical owner per side, not a precedent for ejecting one owner independently.

## UI battle-state semantics

Player mode defaults to an upper attacker/lower defender field, matching the user-supplied in-game battle-report layout, with visual line slots, reserves, result and unsupported-boundary warnings, and round navigation. Air defense and bomber slots are rendered as a compact lateral air zone beside the central ground field, and flank slots are split to the left/right sides of the three central ground lines instead of consuming full-width rows. The simulator-only deployment snapshot remains accessible as a `部署` pager state rather than being presented as battle round 0. Browser setup defaults to the supported `land-max` battlefield and Forge level 5 on both sides; the initial Hoplite quantity is derived from the selected default field and fills its entire first line so a user can add Light Infantry and observe native flank placement without the default front being underfilled. When a user explicitly selects a battlefield with no flank geometry, the UI keeps any non-front Light Infantry in Reserve and shows a no-flank reserve note rather than making that placement look accidental. Hover/focus tooltips show registry display name, input upgrades, slot HP, and wave munition when applicable. Research mode adds batch IDs, native/current lines, reserve/ammo state, continuation state, events, and assumptions; it does not replace the player view.

`hit_points_percent` is engine-derived slot state using the current persistent-damage representation: `100 × (surviving count × unit HP − persistent slot damage) / (surviving count × unit HP)`. Dead units are absent from both numerator and denominator, matching the user-observed denominator rule. It is not claimed as a fully verified reconstruction of Ikariam's internal HP distribution while kill selection, damage distribution, and RR remain partly experimental. `munition_percent` is wave-level using the Phase A derived entry-batch contract above, so every slot of that wave shares it. Both are additive API fields; existing snapshot fields remain unchanged.

## Executable battle-report calibration

`evaluate_fixture()` compares a `BattleReportFixture` with a controlled simulator result, while `run_fixture()` keeps simulation and evaluation as separate steps. The requested round and slot are addressed by side, runtime line, and damage position; physical position is never calibration identity. Every requested field produces its own deterministic `match`, `mismatch`, or `not_assessable` assessment, and result metadata preserves simulator status, reached round, and named unsupported blockers.

Damage-percent observations use the existing documented round-up assumption to derive the exact compatible integer persistent-damage interval from surviving units × unit HP. This remains a calibration assumption rather than confirmed Ikariam law. Casualties are summed only from round `damage` events carrying exact target side, runtime line, and damage position; missing identity is not inferred from side totals. Battle-report `life_percent` remains `not_assessable` with `UNKNOWN-BATTLE-REPORT-LIFE-PERCENT-SEMANTICS`, because the report denominator and rounding have not been proven identical to engine-derived `hit_points_percent`.

A calibration match says only that one simulator result is compatible with one observation. It does not promote `USER_PROVIDED_BATTLE_OBSERVATION`, an experimental policy, or any empirical hypothesis into a production mechanic. Existing mixed-unit Am, accuracy, RR slot-internal allocation, SR/IR trigger, secondary-trigger, ranged-fallback, cross-wave rebuild, and formation blockers remain intact. Formation firing order and class-level shot-by-shot target transfer are executable current contracts.


## Military economy and General Score

The `military-economy-current` profile is presentation/reporting data, not a combat modifier. The current community score rule states that active military units and ships contribute 0.02 General Score per unmodified production resource, equivalent to one General point per 50 resources; reduction buildings do not reduce the score basis. The current land-unit GEN values are cross-checked against that formula, and the profile loader rejects any row whose published score does not equal `resource_cost_basis_total / 50`.

Spartan is a special case: its stored 40 + 40 resource values are nominal score-basis values rather than resources actually paid for recruitment, so its 1.6 score remains valid without pretending that 80 resources were spent. Population is not part of the General Score formula. Workshop levels, Forge/Hephaistos, and combat buffs are deliberately absent from the economy calculation.

Battle output derives `general_score_lost` only from actual casualties and derives `general_score_destroyed` as the opposing side's loss. `gross_damage_dealt` is separately the sum of simulator `damage` events; it is an engine observability metric and is not claimed to be an independently verified Ikariam war-report field with identical semantics.
