# Naval anti-balloon speedboats vs balloon carriers — observable-outcome inverse test (2026-10-13)

**Status:** Research-only user observations, no change to production combat formulas. The actual game report cannot show individual ship hit counts; neither the user's message nor an engine debug JSON should be represented as ground-truth per-ship shot telemetry. These cases were supplied verbally in the same chat as the Ram Ship vs Deckwrecker study; store them as a separate `USER_CHAT` fixture, not as the `野蠻人.xlsx` Ram workbook measurements.

## Roles and provenance

Provisional matching based on current Gameforge unit roles:
- `barbarian_dirigible_igniter` (Barbarian **anti-balloon fast boat**): 400 HP / 60 armor / 1 space / 340 base damage / Accuracy 95 / five magazine shots.
- `balloon_carrier` (player **carrier**): 2,800 HP / 0 base armor / 5 space / 2,000 damage / Accuracy 50 / five magazine shots.
- `paddle_speedboat` (player **anti-balloon fast boat**): 400 HP / 0 armor / 1 space / 240 damage / Accuracy 90 / five magazine shots.
- `barbarian_nest` (Barbarian **carrier counterpart**): 2,800 HP / 100 armor / 5 space / 2,000 damage / Accuracy 50 / five magazine shots.

The user's unit names are gameplay labels; the mapping to these internal IDs is **provisional**, pending their exact source battle/preset. On `naval-max`, each `anti-balloon` and `balloon` formation has two physical slots of 15 **space**; thus 15 speedboats and three carriers in each slot are consistent with the previously merged five-tier Help geometry.

The official Help-based **firing order** currently encoded in `official-help-naval-targeting` is:

`anti-balloon -> balloon -> third -> flank -> second -> first`.

Thus speedboats fire **before** carriers in this engine; carriers still fire before the Third/Flank/Second/First phases and can materially change subsequent shot eligibility and casualty propagation. Do not use a same-time pairwise DPS comparison across different formations. The carrier's own target priority is Third -> Second -> First -> Flank, whereas anti-balloon speedboats prioritize Balloon. With invented supporting First units, the same-round stages exist; the unknown real mixed-fleet composition must not be inferred from the synthetic filler.

## Four independent user-reported cases

| Game scenario | Reported target casualties | Reported bars |
|---|---:|---|
| 30 Barbarian fast boats vs six player carriers, player defense Lv7, Forge5 | 1 player carrier **total** | not supplied |
| Same count/setup, player defense Lv8, Forge5 | 0 player carriers | not supplied |
| Same count/setup, player defense Lv14, Forge5 | 0 player carriers | 65%, 70% across two slots |
| Player Forge5 fast boats with attack Lv14 vs Barbarian carriers | 1 Barbarian carrier **in each slot** | 53%, 65% among reported surviving carriers |

**Follow-up confirmation from the user:** the reverse last case is indeed **30 player fast boats (two slots × 15) attacking six Barbarian carriers (two slots × 3)**, and the **53% / 65% bars are the first-round end-of-round display**. Counts and timing are therefore user-confirmed observations, **not** extrapolations from the forward case. No information about other active First/Second/Third ships or the unavailable per-individual target hit sequence was provided.

## Why 16 and 14 shots, rather than 15 and 15?

A full speedboat formation has two source AM columns of 15 ships. The current engine's **row-major Attacking Matrix** places two shots in each of 15 rows; with two valid addressed carrier slots it uses the **row number**, not a flat shot counter, to choose target slot.

Odd rows (1,3,...,15) = 8 rows × 2 source slots = **16 shots to physical damage-position 1**. Even rows (2,4,...,14) = 7 rows × 2 source slots = **14 shots to position 2**. The new control uses the actual production `_shot_rows` and one-round engine `attacking_matrix` event for comparison.

**Condition:** all 30 speedboats can fire one valid shot in the target phase, there are two accessible carrier target slots, and no prior casualties/phase rules remove any firing eligibility. This is a *modeled* firing allocation, not a recovered real-game per-ship hit history.

## Damage and observable bars

All net damages below are computed from production `UnitRegistry`, `WorkshopProfile`, `ForgeProfile`, and `calculate_damage` rather than repeated free-floating combat constants.

### Barbarian fast boat -> player carrier with defense Lv14 and Forge5

`d = 340 - (0 + 14 × 10 + 20) = 180`.

At three full-health 2,800-HP carriers per slot, initial HP=8,400. With no casualties or lost damage:
- 16 hits ×180 -> `(8400−2880)/8400=65.714%` -> **65%** if floor-displayed.
- 14 hits ×180 -> `(8400−2520)/8400=70.000%` -> **70%**.

This exactly reproduces the two reported no-death bars using only the *aggregate net hit counts*. It **cannot identify which carrier was hit**, and it does not require each carrier taking the same number of hits.

### Player fast boat attack Lv14 / Forge5 -> Barbarian carrier

`d = floor[(240+14×10)×1.15 - 100] = 337`.

Each carrier has 2,800 HP. If **one per slot sinks**, two survivors have 5,600 full HP per slot. Conserving the entire 16- or 14-hit slot damage budget gives:

- 16 ×337=5,392; 2,800 counted as the sunk hull; 2,592 damage remains on two survivors; `(5600−2592)/5600=53.714%` -> **53%** floor.
- 14 ×337=4,718; 2,800 sunk, 1,918 survivor damage; `(5600−1918)/5600=65.750%` -> **65%** floor.

Current **sequential D-kill engine** sinks one carrier after **nine hits**, loses `9×337−2800=233` overkill **per slot**, and gives the two surviving carrier bars **57% and 69%**, not the observed 53% and 65%, even though the *deaths* match. This is direct evidence that model-only zero-overkill accounting and/or target allocation cannot explain these cases jointly. **Not proof** that the official game transfers overkill: the same visible survivor bars may result from within-slot pooled damage, alternative aggregate death allocation, other hit histories, different bar denominators, or other ship classes.

### Barbarian fast boat -> player carrier defense Lv7 vs Lv8

With Forge5, calculated incoming net hits are **250** at Lv7 and **240** at Lv8. Both have `ceil(2800/d)=12` hits-to-kill for one fresh carrier. The reported **one total death to zero** across the upgrade cannot come solely from the integer kill-hit threshold, just as the Ram defense14->15 jump cannot.

The existing Experimental Accuracy concentration (source speedboat Accuracy **95**) is very aggressive. The full-engine controlled one-round trial currently predicts:
- player carrier DEF7: **two** deaths (one in each slot), observed **one total**;
- DEF8: **two** deaths, observed **zero**;
- DEF14: **one** death, observed **zero**;
- reverse player attack14: **one per slot** (correct deaths), but residual HP **57%/69%** instead of **53%/65%**.

These mismatch results are from a **synthetic First-fill experiment**, not the user's actual complete fleet. The first lines are intentionally created by inserting 35 player Steam Rams and 42 Barbarian Wedge Paddlers as appropriate. They merely allow the production one-round engine to execute; do not assert such front ships appeared in the real battle.

## Additional user observation: no Forge, player carrier Defense Lv3, two deaths

**New user report:** with **no player Forge** and carrier armor upgrade **Lv3**, **two player carriers are lost**. This is recorded independently from the three Forge5 scenarios and the confirmed reverse attack14 case.

**User follow-up confirmation:** For this distinct no-Forge Lv3 case, the user has explicitly confirmed the **same 30 Barbarian fast boats (two 15-ship slots) versus six player carriers (two 3-carrier slots)** and that **two player carriers were killed by the end of ROUND ONE**. **Which slot(s) lost them remains unknown**, as do the final HP bars and unseen supporting fleet. Treat the 30-versus-6 setup and round number as real chat observations, while **16/14 successful shots remains an AM model calculation, not a recovered game shot trace**.

With the user-confirmed 30-vs-6 configuration and Round 1, the production damage profile predicts `d=340-(3×10)=310` net hit (no +20 Forge armor), **assuming the provisional Gameforge counterpart mapping and identical eligibility**. The *current model* predicts AM-addressed 16 and 14 shots with 4,960 / 4,340 gross damage per slot; eligibility and individual shot hits are not game-proven. Under an **effective focus budget** abstraction `f`, both slots have capacity to concentrate at least one 2,800-HP carrier kill only if `f ≥ 2800/(14×310)=64.516%` **provided that the two deaths are one per slot; the user has not confirmed that split**. The previous independently reported Forge5 defense7/8 cliff conditionally suggests `70% ≤ f < 72.917%` under this same abstraction; hence the new **total** death count is *consistent* but does **not** narrow that interval, **because one death per slot has not been independently observed for this Lv3 case**. Fixed `f` is not yet an officially verified Accuracy rule, and the model must still specify how surplus damage behaves after each kill.

This observation therefore supplies **a different Forge state** for an out-of-sample check and offers a concrete falsification target. Matching two deaths alone cannot prove whether Accuracy is deterministic, a Bernoulli hit chance, an aggregate focus coefficient, or tied to another combat phase. At most, a conditional one-round 30-v-6 control may verify that *a chosen model can accommodate the new evidence*.

**Forge null hypothesis:** The user considers it most plausible that the miracle adjusts effective Attack or Defense only. For now, compare Forge0 and Forge5 via the packaged **numeric** damage calculator and leave Accuracy, AM addressing, target selection and firing chronology unchanged across Forge states; this is a parsimonious *research hypothesis*, not a newly verified official Forge rule. The durable, cross-session evidence/derivation record is `docs/calibration/naval-inverse-engineering-handoff.md`.

## Inverse simulation strategy without game shot logs

Use **observable constraints** rather than pretending a hidden target sequence is known:
1. Candidate shot-allocation rules must first reproduce the model's *available AM row* mapping and eligible firing order, including carrier-stage vs speedboat-stage chronology.
2. Candidate individual damage allocation must produce the same deaths **and** reported floor-display survivor HP across both symmetric slots with one shared rule and the same unit profiles.
3. Benchmark at **defense 7/8/14** and the **reverse attack14** case simultaneously. Reject a rule that reproduces only the 65/70 bars but kills a carrier at DEF14, or matches reverse kills but discards the 233 overkill that would explain 53/65.
4. Keep Accuracy selection and overkill/pooled damage as **separate latent model dimensions**, compare against the original Ram 14/15 cliff as held-out evidence. Do not hard-code observed casualties into the engine.
5. If possible collect first/second round *slot-level deaths and bars* with fully described battle context, not impossible per-ship shot counts. Exact labels for Barbarian counterpart units, the full original supporting fleet, and the **physical slot(s) of the two losses and HP bars** of the no-Forge DEF3 case remain to be determined; **its 30-vs-6 two-slot configuration AND end-of-Round-1 timing have already been explicitly confirmed**. The reverse attack14 counts and round-one bars have also been confirmed by the user.

## File locations and status

- User-observed fixture: `tests/fixtures/reverse_engineering/naval_air_counterparts_20261013.json`.
- Read-only model: `tools/research/naval_air_counterpart_probe.py`.
- Regression: `tests/unit/test_naval_air_counterpart_probe.py`.
- Hosted Actions runs same full pytest plus both air and Ram comparison scripts, uploads machine-readable JSON artifacts. The air artifact exports the **entire synthetic round-one engine event stream** (including `damage`, `damage_calculation`, `attacking_matrix`, Accuracy/overkill/assumption details) and the complete model assumption list, so that its 57%/69% prediction can be independently audited without access to unseen game shot traces.
- [Issue #68](https://github.com/hun186/Ikariam-Battle-System/issues/68) tracks both inverse studies; [Draft PR #69](https://github.com/hun186/Ikariam-Battle-System/pull/69) is strictly research and remains unmerged.
