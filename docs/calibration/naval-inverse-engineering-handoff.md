# Naval inverse engineering — durable evidence, mathematics, and agent handoff

> **Living research record, not a verified Gameforge combat algorithm.**
> Last research-note update: 2026-10-13. Hosted GitHub `main` is authoritative for the **merged** simulator, currently including five Sea Fight geometries from PR #70; draft PR #69 holds **unmerged** experimental evidence and tests. Verify live heads, review and CI at the start of every new session. Do **not** merge without the owner explicitly saying so.

## 0. Agent quick-start: first five minutes

1. Read root `AGENTS.md`, `.codex/project.md`, `.codex/memory.md`, then **this note**; use `.codex/known_issues.md` and `.codex/backlog.md` for unresolved tasks. Read the existing docs under `docs/calibration/` rather than re-discovering the same numeric constraints.
2. Query the **Hosted** `hun186/Ikariam-Battle-System` `main` head, Draft [PR #69](https://github.com/hun186/Ikariam-Battle-System/pull/69) head/mergeability, Codex Review summary **reviewed head**, review threads, exact-head workflow runs. [PR #70](https://github.com/hun186/Ikariam-Battle-System/pull/70) geometry was merged previously; `main` remains sole authoritative executable baseline. Research work belongs on `research/naval-ram-deckwrecker-empirical-probe` until owner authorization.
3. Read input fixtures *before* writing formulas:
   - `tests/fixtures/reverse_engineering/naval_ram_deckwrecker_20261013.json`
   - `tests/fixtures/reverse_engineering/naval_air_counterparts_20261013.json`
   - `tests/fixtures/reverse_engineering/naval_pvp_fast_boat_carrier_20261013.json`
   Treat separately (A) Excel observed aggregate, (B) user chat-reported observations and later clarifications, (C) current production-profile calculations, (D) synthetic simulator outputs, (E) speculative hypotheses. A verified geometry is not a verified target allocator.
4. Review code:
   - `tools/research/naval_ram_empirical_probe.py`
   - `tools/research/naval_air_counterpart_probe.py`
   - `tests/unit/test_naval_ram_empirical_probe.py`
   - `tests/unit/test_naval_air_counterpart_probe.py`
   - `ikariam_battle/accuracy.py`, `ikariam_battle/damage.py`, `ikariam_battle/engine.py`.
   The synthetic air report exports full **model-generated** round-one events and assumptions, **not real-game individual-shot logs**. CI `.github/workflows/naval-ram-empirical-probe.yml` runs full tests and uploads research JSON; recheck live run ID for current head.
5. Continue **inverse model competition**, not an immediate global Accuracy rule replacement: run held-out predictions across both Ram and air fleets with the same model parameters, distinguish spread/focus, per-slot damage pools/overkill/redistribution, shot eligibility/chronology, and UI HP-bar aggregation; do not hardcode specific upgrade casualty outputs into the engine. Track rejected as well as surviving hypotheses. Add regression and refresh this record after each meaningful new case.

## 1. Evidence ledger — what was actually supplied

User has **not** supplied underlying real-game per-ship hit sequence; Gameforge battle reports do not show that. A locally generated Debug/event JSON can only demonstrate what **our simulator** did. Case labels and source provenance are recorded in the machine-readable fixtures.

| ID | Source status | Observed configuration | Observed results | Still unknown |
| --- | --- | --- | --- | --- |
| RAM-EXCEL-03-18 | Workbook `野蠻人.xlsx`, worksheet `野撞打開爐衝撞`, **F4:F19** | Player Ram Ship, Forge5; defender Workshop armor levels 3–18; Barbarian Deckwrecker | **Total** player losses 6 at DEF3–14; 0 at DEF15–18 | Exact original fleet and per-individual hits; Excel F cells do **not** encode per-slot losses |
| RAM-CHAT-POSITIONS | Independent **user-chat description**, not Excel per-slot telemetry | Six active Flank positions, six Rams per position | 1 player ship killed in each position at DEF3–14; none at DEF15; 15 survivors damaged | Original supporting First/other formations, individual shots |
| RAM-CHAT-19-20 | Independent user-chat case, **DEF19 not in F4:F19** | Player DEF19, ATT20, Forge5, Barbarian Ram counterparts | Player deaths 0, displayed **63%** bar; Barbarian dies 3 per reported Flank slot, survivors' bar **88%** | HP bar definition and exact shots |
| AIR-BARB-DEF7 | User chat | 30 Barbarian fast boats (two slots ×15) vs 6 player carriers (two ×3), player Forge5, carrier DEF7 | 1 player carrier killed **total** | Slot of death and per-ship shots; source unit-ID mapping provisional |
| AIR-BARB-DEF8 | User chat | Same, player Forge5, carrier DEF8 | 0 carriers killed | Slot HP bars not supplied |
| AIR-BARB-DEF14 | User chat | Same, player Forge5, carrier DEF14 | 0 killed, two carrier-slot HP bars **65%, 70%** | Shot sequence/bar rounding rule |
| AIR-PLAYER-ATT14 | User chat **later explicitly confirmed** | Player 30 speedboats (2×15), ATT14, Forge5, Barbarian 6 carriers (2×3); **first-round end** | **1 enemy carrier killed in each slot**; displayed survivors' HP bars **53%, 65%** | Other fleet composition, exact internal unit mapping |
| **AIR-BARB-DEF3-NOFORGE** | **New user-chat report explicitly reconfirmed** | **30 Barbarian fast boats (2×15)** vs **6 player carriers (2×3)**; player carrier **DEF3**; **NO Forge**, **Round 1** | **2 player carriers killed, total** by end of Round 1 | **Which slot(s) had the two deaths is NOT known**, bars not supplied, source mapping and other formations still unknown |

**Forge working hypothesis (owner intuition, NOT confirmed Gameforge rule):** Forge changes **effective attack or defense numbers** only. In current packaged calculation, Forge5 contributes **+20 defense armor** or **×1.15 effective player attack** when relevant; Forge-off removes those bonuses. No separate Forge effect on AM column addresses, within-slot Accuracy targeting, target priority, firing eligibility beyond changed ATK/DEF, damage redistribution, or phase order should be invented without evidence. When Forge changes effective ATK/DEF, penetration eligibility can change **indirectly** via the existing `ATK > DEF` rule. Design a matched-effective-damage experiment (Forge off vs on with comparable resulting net damage) to test for any *direct* Forge-mechanic difference.

## 2. Verified numeric profiles versus assumptions

Current profile baseline: Ram Ship and Barbarian Deckwrecker **HP3080**; player Ram armor180, Barbarian armor240; both attacks1500, weapon Accuracy80. Player Balloon Carrier **HP2800**, armor0, 5 slot-space; player Paddle Speedboat **240 attack**, Accuracy90, slot-size1; Barbarian Dirigible Igniter **340 attack**, Accuracy95; Barbarian Nest **HP2800**, armor100. Unit names are provisional mappings of user's game terminology, not independent screenshots.

Current profile math, under applicable Forge and Workshop rules:
- Barbarian Deckwrecker into player Ram: DEF14 Forge5 `1500−(180+140+20)=1160`; DEF15 Forge5 `1150`; DEF19 Forge5 `1110`. All require **three** 100%-HP hits to kill; the **6→0** death transition does not follow from integer hit-to-kill alone.
- Barbarian fast boat into player carrier: DEF7 Forge5 `340−(70+20)=250`; DEF8 Forge5 `240`; DEF14 Forge5 `180`; **DEF3 Forge0 `340−30=310`**. Both 250 and 240 require **12 hits** to kill one 2,800-HP carrier; cannot alone explain DEF7→8 total losses **1→0**.
- Player ATT14/Forge5 Paddle Speedboat into Barbarian Nest: `floor((240+140)×1.15−100)=337` effective damage.
- Current AM model (two 15-ship source slots, two active target slots, all firing tickets eligible) gives **16 and 14** target-slot addressed shots, based on **15 alternating row-major AM rows**; **this is model-predicted address allocation, not actual individual ship hits**.
- `naval-max` anti-balloon 2×15 spaces, balloon 2×15 spaces: 15 speedboats per source slot, 3 carriers per target slot. Official Help-supported profile firing order in simulator: **anti-balloon before balloon before third / flank / second / first**. Carrier phase is early relative to most formations, but **not** before anti-balloon.

## 3. Critical arithmetic derivations, kept reproducible

### 3.1 Aggregate carrier HP bars

Three full carriers in a slot total `3×2800=8400 HP`.
- **DEF14/Forge5, no casualty:** slot1 `8400−16×180=5520` → `65.714%`, floor=**65%**; slot2 `8400−14×180=5880` → **70%**. Matches 65/70 from the actual game **if** all 30 hits apply and UI uses floor/remaining-slot-HP aggregation.
- **Reverse player ATT14/Forge5, one killed per slot:** gross `16×337=5392`, `14×337=4718`. Under a **conditional conserved slot-damage** model, after subtracting one sunk 2800-HP hull, 2 surviving carriers have `2×2800=5600` max HP: first `(5600−(5392−2800))/5600=53.714%` → **53%**; second `(5600−(4718−2800))/5600=65.750%` → **65%**. **Only conditional support for pooled/retained damage**, not proof of physical overkill transfer.
- **Current production sequential D-kill hypothesis:** 9 hits of 337 sink a carrier, discarding `9×337−2800=233` overkill per slot, leaving model bars **57%/69%** despite producing correct 1/slot kills. There are **466 points of discarded overkill total** in that controlled two-slot scenario. Comparing both deaths and bars matters.
- **No Forge DEF3/first round:** hypothetical 16×310=4960, 14×310=4340 gross slot damage. If two deaths = one per slot (**not yet observed per slot**), a focus hypothesis with enough concentration could explain both; but two kills could alternatively occur in the same slot under other allocation rules. Do **not** bake a 1+1 distribution into the source fixture.

### 3.2 Ram cliff and equivalent thresholds

DEF14: `3080−2×1160=760=24.675%` HP. DEF15: `3080−2×1150=780=25.325%`. The candidate **25%-remaining-after-two-hits** threshold straddles the observed 6→0 transition, **but** it is mathematically indistinguishable at those damages from a **62.5%-remaining-after-one-hit** threshold; both are `d≥1155` against 3080 HP. Neither is proven to be an official Accuracy mechanic. Current Experimental `EXP-ACCURACY-CONCENTRATION-001` uses remaining-HP% ≤ weapon Accuracy to focus and predicts 2 deaths per hypothetical six-hit Ram slot even at DEF15; do not disguise this as verified.

### 3.3 Effective focus share, an *inverse* surrogate—not a targeting algorithm

**Conditional surrogate with a restrictive assumption:** Define `f` as the **same deterministic REALIZED concentration fraction** of a slot's addressed effective damage delivered to one initially full 2,800-HP carrier across the compared Forge5 DEF7 and DEF8 observations—not a maximum allowable share and not a verified game-targeting algorithm. **Assume** DEF7's one death occurred in the 16-hit target slot and DEF8's zero deaths arose because that slot received insufficient concentrated damage. Under only those assumptions:

```
DEF7 Forge5 (d=250): 16*250*f ≥ 2800    => f ≥ 0.700000
DEF8 Forge5 (d=240): 16*240*f < 2800    => f < 0.729167
=> conditional 70.0000% ≤ f < 72.9167%
```

The no-Forge DEF3 two-death observation, **if** interpreted as one death per slot, adds `14×310*f ≥ 2800 => f ≥ 64.516%`—a **weaker bound**, hence it is *consistent* with but **does not tighten** the prior 70–72.9167% interval. Since two deaths' **slot distribution remains unknown**, even that lower bound is **not an unconditional deduction** from the new game report. These inequalities **depend on** the same 16/14 active shots, per-slot target counts, a single equal realized focus share across Forge modes, one-death-per-16-slot assumption at DEF7, same timing and no other mixed-fleet effects. They are a convenient falsifiable model-fit summary, **not evidence that Accuracy95 literally maps to f=72%**. There is no reason to extrapolate it to another unit count or Accuracy80 without held-out validation.

## 4. Current engine results and why they are not the game

The synthetic baseline inserts **invented First-line ships** to satisfy the simulator's formation prerequisites. Those fillers were *not* identified in real battle reports. Using such controls, simulator DEF7/8/14 produces **2/2/1** carrier deaths against observed **1/0/0**. Reverse ATT14 produces **1/slot deaths**, but **57%/69%** versus observed **53%/65%**. Separately, full 36-vs-36 Ram-only ships fall back to First (not real Flank geometry); an invented full-First control moves the two 36-Ram fleets to six real Flank slots but still predicts **12** player deaths for DEF14/15/19, not observed **6/0/0**. The whole model is therefore **not calibrated**.

Strict mode continues to mark the unknown Accuracy algorithm as unresolved. Experimental `EXP-ACCURACY-CONCENTRATION-001` is one deterministic candidate. **Do not silently update** accuracy.py, engine.py, profiles or official damage formulas to pass a handful of cases; do not present synthetic casualties as measurements.

## 5. Inverse simulation research design / falsifiable next tasks

1. Treat Forge as a *numeric-effect-only null hypothesis*: vary only effective attack/armor while keeping identical AM, target choice, Accuracy and priority rules; separately test a possible direct Forge effect if the baseline fails on an independent repeated case. No new Forge-to-Accuracy link absent evidence.
2. Build independent candidate selector implementations around a fixed source AM with **row-major 16/14**, phase order, and a target multiset of individual HP; compare (a) spread healthy, (b) focus wounded, (c) damage-dependent threshold, (d) pooled slot damage, (e) hit success/miss variants. Avoid fixed `f` as an executable physical targeting strategy unless one can define its shot-level/aggregate realization.
3. Vary excess handling **orthogonally**: discard lethal overkill; retain surplus into a slot pool; distribute after kill; or calculate aggregate D/P/IR/SR/RR. Tests must demand *both* correct casualties and floor HP-bar percentages, with explicit UI denominator alternatives.
4. Score all supplied cases **jointly**; hold out at least one player-vs-Barbarian air case, Forge-on/off case, Ram DEF14/15 case, or follow-up round. Find parameter-identifiable ranges or label **UNDERDETERMINED** instead of choosing a single appealing formula.
5. Collect only **observable** game data: first/second-round per-slot casualties and bars, available ship counts, Workshop/Forge, supporting fleet, ammo and arrival stage. No impossible real per-ship shot record is required. Still needed: which slot(s) lost the **two carriers** at no-Forge DEF3; whether bars are truncated; true original non-air fleet composition; and the slot split for the new player-vs-player speedboat/carrier three-case holdout. **Both player sides' Forge5 status AND first-round casualty timing are user-confirmed and must not be re-requested.** **The DEF3 30-vs-6 layout and Round 1 timing are already user-confirmed and must not be requested again.**
6. Preserve every meaningful new source/derivation and each falsification result in this document and the source-specific fixtures, update `.codex/memory.md` and `.codex/backlog.md`; keep **proposed formula**, **current simulator behavior**, and **Gameforge-confirmed behavior** clearly distinguished. Request fresh exact-head CI/Codex Review and never merge without explicit owner command.

## 6. Continuous audit trail / current gates

- [Issue #68](https://github.com/hun186/Ikariam-Battle-System/issues/68): chronology, user-supplied evidence updates and inverse-constraint design.
- [Draft PR #69](https://github.com/hun186/Ikariam-Battle-System/pull/69): actual research code / source fixtures / tests / documents. Research commits and Hosted main may advance independently; this note does not assert that a **past reviewed SHA is current**. **Historical audit anchor:** the most recent *completed* Codex Review seen before the three player-vs-player holdouts was for exact head `3b41c714be38efcfb47575897713aeeeb83cfa19` on 2026-10-13 15:13:50 UTC (three P2 findings: define `f` as realized; remove already confirmed DEF3 data from open backlog; persist reviewed SHA). Its exact-head CI [#38419470506](https://github.com/hun186/Ikariam-Battle-System/actions/runs/38419470506) succeeded, 471 passed / 3 expected xfailed. **Those findings are not a pass for any newer head**; check currently submitted review threads and exact-head actions before concluding review status. Recheck live repository.
- [Merged PR #70](https://github.com/hun186/Ikariam-Battle-System/pull/70): official five-tier naval geometry fix. It established physical slots / spaces, **not** whole fleet identity or official Accuracy.
- The first unmerged air-HP holdout comparison had CI **466 passed/3 xfailed**. Subsequent user-confirmed reverse data and full round-event trace reached **467 passed/3 xfailed**; after the additional no-Forge observation, CI reached **469 passed/3 xfailed** on then-current head. These are *historical verified runs*, not an assertion about a newer, untested head. New commits require a new run and a new exact-head Codex Review.
- Latest known Codex feedback on previous head requested preservation of `additional_observations` in the uploaded report. It must remain a **separate raw evidence field**, without fabricating a synthetic simulator trace for any case lacking inputs. Check that the current test explicitly protects this field and whether the thread was resolved.

**Work handoff promise:** A new AI agent should be able to read this one note and all three fixtures and state exactly which empirical outcomes are confirmed, which numbers are conditional current-model predictions, which hypotheses remain competitive, what Forge's working hypothesis is, and which GitHub checks are outstanding—*before* proposing changes to battle rules.

## 7. New player-vs-player fast boat versus carrier held-out cases (2026-10-13)

**User's NEW game evidence, with subsequent explicit confirmation:** 30 player Paddle Speedboats attacked six **player** Balloon Carriers, and **BOTH players had Level 5 Forge active**. The owner explicitly confirmed all three reported totals were at the **END OF ROUND ONE**. Per-slot casualty split and remaining original fleet are not yet confirmed. The model comparison must use BOTH-FORGE5 and Round1; supporting First fleets in the controlled simulation were invented and are not historical evidence. Preserve game-reported **total** carrier deaths as follows:

| Player speedboat Attack | Player carrier Armor upgrade | Observed TOTAL player-carrier losses | Two-sided Forge5 production net hit | Model hits to kill 2800 HP carrier |
|---:|---:|---:|---:|---:|
| 12 | 8 | **2** | 314 | 9 |
| 20 | 16 | **2** | 326 | 9 |
| 17 | 18 | **1** | 271 | 11 |

**New data fixture:** `tests/fixtures/reverse_engineering/naval_pvp_fast_boat_carrier_20261013.json` (separate from Barbarian targets and from Ram workbook). **Executable exact-engine control:** `tools/research/naval_pvp_fast_carrier_probe.py` with regression `tests/unit/test_naval_pvp_fast_carrier_probe.py`. To execute a full first-round engine test, it adds **invented 35 Steam Rams per side** and selects `naval-max`; those frontlines are NOT asserted to have existed in the user's battle. Two Forge scopes remain in the research tool, but **only both-sides Forge5 is the user-confirmed real-game setting**. The attacker-only Forge5 row is retained explicitly as an **unobserved counterfactual sensitivity analysis**, never another plausible description of these three battles:

| PvP ATT/DEF | Observed total | CURRENT synthetic engine **both sides Forge5** | CURRENT synthetic engine **attacker-only Forge5** |
| --- | ---: | ---: | ---: |
| 12 / 8 | 2 | **2** (slots 1+1) | **2** (slots 1+1) |
| 20 / 16 | 2 | **2** (slots 1+1) | **2** (slots 1+1) |
| **17 / 18** | **1** | **2** (slots 1+1) — **FAIL** | **2** (slots 1+1) — **FAIL** |

**Confirmation note:** The user explicitly stated on 2026-10-13 that **both players in all three holdout observations had Forge5**. Source fixture and model artifact mark the both-on condition observed and attacker-only as counterfactual. The reported deaths for all three cases are explicitly confirmed as **ROUND 1 END** in a later user-chat reply. This eliminates timing uncertainty, but does NOT establish real-game First-line fleets, target-specific hits, or which slot lost the third case's one carrier.

**Conditional source AM:** with two full 15-ship source slots and two target slots, current row-major `_shot_rows` and actual simulator AM events both produce **16 / 14** shots. Current Experimental Accuracy90 concentrates both sufficiently to kill one in each slot, even at net damage 271 (eleven shots needed on a fresh target). Thus the **ATT17/DEF18 observation is a held-out falsifier** for the current 90%-based within-slot wounded-focus rule under those controls, and remains a mismatch if only attacker Forge5.

**Separate conditional focus-share numerical fit, not official rule:** If a **single deterministic realized fraction** `f` of gross slot damage applies to one carrier with both slots firing 16/14 full shots, and the third observation's one loss happens in 16-hit slot (not game-confirmed), then
```
ATT12/DEF8 d=314: 14*314*f >= 2800 (both slots one kill, conditional)
ATT20/DEF16 d=326: 14*326*f >= 2800
ATT17/DEF18 d=271: 16*271*f >= 2800; 14*271*f < 2800
=> f ∈ [ max(2800/4396, 2800/4564, 2800/4336), 2800/3794 )
     = [~0.64576, ~0.73801)
```
A test `f=0.70` predicts totals 2/2/1, and ALSO falls in the *separate, more restrictive* Barbarian Accuracy95 conditional DEF7/DEF8 range `[0.70,0.72917)`. **Do not infer Accuracy90 or Accuracy95 literally implies f=0.70**: this is a non-executable, aggregate fit, conditional on shot success and slot allocation; many dissimilar discrete selectors can fit. The cross-Accuracy overlap especially warns against assuming a simple direct Accuracy-to-focus formula. Need a **single implementable selector** that predicts original Ram results AND these carrier outcomes without case IDs or special defense thresholds.

**Source/holdout update:** 2026-10-13 follow-up confirms all three PVP death counts are **Round-1 results**. Current experimental **Round-1** synthetic prediction remains 2/2/2 against 2/2/1 with equal confirmed Forge5 on both players. The failed third case is therefore **not attributable to a wrong-round comparison**; however, incomplete real front-line fleet and exact per-slot death position remain confounders. No production targeting change has been justified. Last completed Codex review observed before this new update: **head `0fa68a249f3cd3e0c300cdb2bc8d43cd86b03c75`**, completed **2026-10-13T15:44:30Z** with 2 P2 notes (cross-agent memory routing and stale no-Forge collection guidance), now patched on the newer research head. Requery current review rather than treating old reviewed SHA as passing new code.

**Reproducibility:** Source-only GitHub workflow `.github/workflows/naval-ram-empirical-probe.yml` uploads the new `naval_pvp_fast_carrier_probe.json` artifact alongside prior two JSON artifacts. Historical first execution on head `acd67d22dd74a5f79cc963b11924576de132cb98` [Actions #38421340989](https://github.com/hun186/Ikariam-Battle-System/actions/runs/38421340989) succeeded (471 tests passed / 3 expected xfailed, BEFORE new PvP regression tests), with six actual model-control outcomes. Verify exact-head CI anew after subsequent documentation and regression changes. **No actual game individual-shot data exists.**

