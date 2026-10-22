# Naval Accuracy inverse candidates — cross-case integer-hit experiment

> Research-only work in Draft PR #69. Data sources are user chat and workbook fixtures; Gameforge's actual target-selection and overkill algorithms are **not** established. Read `docs/calibration/naval-inverse-engineering-handoff.md` first. Never merge without the owner's explicit authorization.

## 2026-10-19: User-authorized provisional Experimental ENGINE rules (NOT official)

The owner explicitly requested **implement the available hypotheses provisionally in the simulator instead of assuming blanket 100% concentration**. Three **narrow, falsifiable** policies are now wired to the ACTUAL Experimental battle resolution on [Draft PR #69](https://github.com/hun186/Ikariam-Battle-System/pull/69), not only research probes:

1. `EXP-NAVAL-FAST-CARRIER-74PCT-001`: **Round1 only**, target `balloon_carrier` in the `balloon` class, **three fresh full-HP hulls in each slot**, exactly **30 live primary-fastboat firing tickets** in `anti-balloon` source formation (player `paddle_speedboat` or Barbarian `barbarian_dirigible_igniter`). Weapon native Accuracy **90/95 remains unchanged** and is separately reported; the bounded **74% remaining HP** concentration threshold replaces the old Accuracy-as-threshold proxy only in this case. Three synthetic player PvP scenarios under user-confirmed both Forge5 now predict **2,2,1** total sunk carriers instead of the prior **2,2,2**, matching all three user-reported first-round *totals*. Historical exact 16/14 hit addresses, source formation, per-slot deaths and survivor bars remain unverified. Seven-case fitting is IN-SAMPLE and no new held-out evidence has arrived.
2. `EXP-NAVAL-RAM-FOCUS-SHARE-001`: **Round1 only**, six **full fresh** `ram_ship` hulls in one Flank target slot, six full `barbarian_deckwrecker` primary hits in a complete **36-source six-column** `flank` firing formation; barbarian Forge0, defender Forge5. Allocate first-hull damage `floor(6 × effective_net_hit × F(Accuracy,6))`, where `F(A,N)=1/N+(1−1/N)*clip((A−60)/60,0,1)` and native weapon Accuracy80 → **F=4/9**. **This is a fractional damage-BUDGET allocation after shots, NOT six literal projectile targets, and does not alter source AM/ammunition or phases.** Pool the remaining damage across five other hulls, discard focal lethal excess. At defense14/15/19, effective hits1160/1150/1110 yield **1/0/0 casualties per six-hull slot** (six Flank slots give **6/0/0**), with defense19 **63%** model survivor bar if floor displays current average. This is a closely overfitted prior-case candidate and cannot claim actual Gameforge per-individual firing.
3. `EXP-NAVAL-DECK-OVERKILL-RETAIN-001`: **Round1 only**, player `ram_ship` Attack20 Forge5 sends six full primary hits to six fresh `barbarian_deckwrecker` Flank hulls under Barbarian Forge0 and matching 36-source full Flank. Keep three default D-kills; rather than discarding **1050 HP** of three×350 lethal-pair overkill (6×1715 hit damage against HP3080), distribute those HP equally as **350 injuries × three surviving hulls**. This conditionally reproduces three barbarian deaths and **88%** survivor bar per slot. **Overkill recovery/P/IR remains UNKNOWN** outside this very limited in-sample approximation.

All three **only apply to `policy=experimental`**, emit uniquely named `assumptions` plus per-slot `damage` event detail, and preserve `policy=strict` UNKNOWN-ACCURACY. Other naval formations and unrelated land scenarios continue existing Experimental baseline. Neither user-reported Gameforge outcomes nor research fixtures are overwritten; supplementary FRONT fillers in runnable regression scenarios are SYNTHETIC, not actual fleet composition. These policies do not implement missing partial Tender repair, insufficient-capacity Doctor healing, IR/SR/RR, cross-wave rebuild, or generalized Gameforge focus selection.

**Multi-round Tender implication:** Reconstructed per-survivor `slot.damage` and `queues` now feed the existing support/round boundary, so full-capacity Tender can act on estimated living damage, and permanent casualties remain dead. This is a conditional prediction, **not** validation of long-run observed battles; partial Tender capacity and exact heal timing remain unverified. Candidate scopes purposely do NOT auto-expand to Round2+ without empirical evidence.

**Test gate:** `tests/unit/test_naval_fast_carrier_experimental_engine.py` and `tests/unit/test_naval_ram_share_candidate_engine.py` exercise the real `simulate()` path, including all three PvP totals, defense14→15 kill cliff, defense19 63% and reverse 88%, with distinct assumption IDs. Fresh Round1 empirical held-out battle logs are still needed before treating a rule as verified.

## Question and method

Can one *executable*, deterministic, damage-responsive target selector explain the observed **first-round** death transitions without hardcoding individual armor or attack upgrades? This experiment compares competing within-slot selectors after the existing current-model Attack Matrix assigns hits to target slots.

`tools/research/naval_accuracy_inverse_candidates.py` reads all three source-tagged empirical JSON fixtures; derives hit damage and weapon Accuracy from the production `UnitRegistry`, `WorkshopProfile`, `ForgeProfile`, and `calculate_damage` via `_damage_trace`; then performs integer attacks against a list of concrete surviving individual ship damage values **without calling `accuracy.py`**.

The program keeps four concepts separate:

1. **User-observed outcome:** total casualties, and in some cases two independently observed surviving-slot health bars; confirmed first-round and both-side Forge5 for all three player-vs-player cases.
2. **Modeled eligible source firing and AM address:** 30 originally alive fast boats in two 15-ship columns assumed each able to fire once; existing AM predicts 16 vs 14 addressed successful hits into two three-carrier target slots. These are not independently observed individual Gameforge hit records; other fleet context unknown.
3. **Candidate within-slot selector:** choose healthiest (spread) until one already wounded survivor's remaining HP percentage is at/below a shared candidate threshold `T`, then focus most damaged. A fresh ship kill discards lethal excess. Pure spread (`T=None`) and pure focus (`T=100`) are competing controls; the earlier experimental engine effectively uses weapon Accuracy 90/95 as `T`.
4. **Separate damage accounting:** even if casualties match, compare survivor-slot HP bars under discarded overkill versus a *counterfactual* conserved-damage bar; do not declare overkill transfer a game rule.

Crucially `T` is **NOT the weapon's official Accuracy stat** and could be a completely wrong proxy. Its shared value for both Accuracy90 and Accuracy95 units is intentional as a falsification experiment, not evidence that Accuracy is ignored.

## Seven in-sample air-carrier casualty cases

Using the existing packaged damage calculator and **the above synthetic all-hit 16/14 conditions**, these are current observed totals and experimental candidate outcomes:

| Source | Fast boat hit damage | Real first-round total carrier losses | Candidate at T=74% | Existing Accuracy-stat-as-threshold proxy |
| --- | ---: | ---: | ---: | ---: |
| Barbarian fast, player carrier DEF7 Forge5 | 250 | 1 | **1** | 2 |
| Barbarian fast, player carrier DEF8 Forge5 | 240 | 0 | **0** | 2 |
| Barbarian fast, player carrier DEF14 Forge5 | 180 | 0 | **0** | 1 |
| Barbarian fast, player carrier DEF3 Forge0 | 310 | 2 | **2** | 2 |
| Player fast ATT12 vs player carrier DEF8, **both Forge5** | 314 | 2 | **2** | 2 |
| Player fast ATT20 vs player carrier DEF16, **both Forge5** | 326 | 2 | **2** | 2 |
| Player fast ATT17 vs player carrier DEF18, **both Forge5** | 271 | 1 | **1** | 2 |

The three player-versus-player totals are **user-confirmed end of Round 1**, and both players had Forge5. The no-Forge DEF3 30-vs-6 battle is also confirmed as Round 1; **the two deaths' physical-slot split is not known**.

**In-sample parameter sweep:** Scanning `T = 0.00% ... 100.00%` in 0.01-percentage-point steps identifies an interval of candidate values around **73.22% through 74.28%** fitting **all seven casualty totals**, not only T=74. There is no statistical validation or uniqueness just because one interval fits; all seven were used for parameter selection, not independent tests. It does not prove the real game has any percentage threshold.

Under T=74, the *model-predicted* two slot kills for these cases (in the above order) are `[1,0]`, `[0,0]`, `[0,0]`, `[1,1]`, `[1,1]`, `[1,1]`, `[1,0]`. The user confirmed each **total**, not these exact slot splits (except cases with separate explicitly reported slot deaths). Do not silently promote calculated positions into observed facts.

The previous `f≈70%` maximum/realized focused-gross-damage fraction is **another mathematical surrogate**, not a discrete shot allocation algorithm. This T-sweep replaces it as a *more operationally testable candidate*, but does not validate either proxy. It is possible for several unrelated selectors to give the same visible totals. A fixed shot-target assignment completely independent of hit damage cannot by itself explain the Barbarian DEF7→8 cliff since `ceil(2800/250)=ceil(2800/240)=12`: to obtain different kills in otherwise identical initial conditions, **some allocation, shot eligibility/count, or other mechanism must depend on changed numeric combat state**, or original full battle inputs differ.

## Parameter identifiability — leave-one-case-out audit

**Important correction to interpretation:** 7/7 matches do **not** provide seven independent constraints on the threshold. The critical boundaries are close to the candidate survivor's HP after **three modeled hits** by the Barbarian 95-Accuracy speedboat:

- DEF7 + Forge5: `d=250`; after three hits, `(2800−3×250)/2800×100 = 73.2142857%` HP.
- DEF8 + Forge5: `d=240`; after three hits, `(2800−3×240)/2800×100 = 74.2857143%` HP.
- A conditional focus threshold between these two survivor-health states can change whether follow-on modeled hits finish the same carrier. The brute-force exact integer-selector fit `73.22–74.28%` is essentially this **DEF7→DEF8 observed cliff**, not an independently observed 74% rule.

New `leave_one_reported_case_out` code **fits the threshold only to the OTHER SIX cases**, then checks all candidate threshold outputs for the omitted case:

| Omitted game record | Thresholds fitting other six, scanned at 0.01pp | Possible prediction for omitted record | Fully determined by the other six? |
| --- | --- | --- | --- |
| Barbarian DEF7 (game: 1 dead) | **70.97–74.28%** (332 candidate values) | **0 or 1 dead** | **No** |
| Barbarian DEF8 (game: 0 dead) | **73.22–80.64%** (743 values) | **0 or 1 dead** | **No** |
| Barbarian DEF14 (game: 0) | 73.22–74.28% | 0 | Yes, *within candidate family* |
| Barbarian DEF3 no-Forge (game: 2) | 73.22–74.28% | 2 | Yes, *within candidate family* |
| PvP ATT12/DEF8 (game: 2) | 73.22–74.28% | 2 | Yes, *within candidate family* |
| PvP ATT20/DEF16 (game: 2) | 73.22–74.28% | 2 | Yes, *within candidate family* |
| PvP ATT17/DEF18 (game: 1) | 73.22–74.28% | 1 | Yes, *within candidate family* |

This is *sensitivity analysis using known case outcomes* (the family, 16/14 input, and fitting range were designed after reviewing the same source records), **NOT genuinely prospective independent field validation**. A count of fitting grid points is NOT a probability of success. If DEF7 or DEF8 were unknown, other observations would admit conflicting guesses. Do not choose T=74 by a post-hoc likelihood claim.

## Concrete NEXT game-visible falsification: PvP ATT17/DEF18 end-of-Round-1 bars

The user has explicitly confirmed **both players had Forge5**, a **total of 30 player speedboats against six player carriers**, and **one TOTAL carrier lost by end of Round 1** in the ATT17/DEF18 case. **The 2×15 attacking / 2×3 defending slot arrangement is inferred from the chosen `naval-max` model geometry and was NOT independently reconfirmed for these three PvP battles.** They have **not** supplied the physical slot where that one carrier sunk or the two surviving-slot HP bars.

The candidate **T=74%** and modeled 16/14 all-hit address allocation predict this specific **previously unmeasured output**:

| Slot in **model** | Source AM hits in model | Candidate number sunk | Candidate round-one survivor HP bar (floor) | Model individual survivors (NOT visible in game) |
| --- | ---: | ---: | ---: | --- |
| 16-address-hit target slot | 16 × 271 | **1** | **75%** (actual 75.80%) | 2,258 HP; 1,987 HP |
| 14-address-hit target slot | 14 × 271 | **0** | **54%** (actual 54.83%) | 2,258 HP; 2,258 HP; **90 HP** |

**The bars 75%/54% are prospective test predictions, not user-reported facts.** If the actual one sink is in the 14-address-hit slot rather than the 16, or observed bars differ materially after establishing game UI rounding and other fleet effects, the combined 74%-focus/16+14-all-hit/discard-overkill explanation is **falsified for that game setting**. A mismatch by itself does not say which component—AM addressing, successful hit count, selector, support fleet, damage accounting or bar denominator—is responsible. No impossible per-individual target-hit record is required; Round1 per-slot deaths and displayed HP bars suffice.

For other source cases without reported bars, the JSON artifact similarly lists separately labeled, **unobserved model-only** first-round slot-health predictions. Keep that section distinct from the confirmed DEF14 65%/70% real-game bars.

## The owner's earlier insight: F(A,N) can differ by Accuracy and number of ships

**Important correction to the initial research conclusion:** A failed attempt to apply the carrier's common **74%-remaining-HP selector threshold `T`** to six-ship Ram slots does **NOT** disprove a shared family of combat allocation rules with **different effective concentration fractions `F`**. These parameters have entirely different meanings:

- `T`: fraction of **one target hull's remaining HP** at which a proposed shot-by-shot selector stops spreading and starts focusing. `T≈74%` was fitted in-sample to seven carrier totals; as a literal global selector it fails the Ram 14→15 first-round cliff.
- `F`: fraction of **one addressed slot's total modeled effective damage budget** that an aggregate first-hull approximation can concentrate on a fresh hull. It does **not** execute integer-shot allocation, kill/overkill redistribution, or target search; it was originally posited in earlier discussion before the three new PvP totals.

Previously proposed **SPECULATIVE common functional family**:
```
F(A, N) = 1/N + (1−1/N) × clip((A−60)/60, 0, 1)
A := source weapon's Accuracy stat
N := initial target ships per addressed formation slot
60 := a convenient fitted offset, NOT an official rule or observed parameter
```

This yields **Accuracy95 vs three carriers: F=72.222%**; **Accuracy90 vs three carriers: F=66.667%**; **Accuracy80 vs six Ram ships: F=44.444%**. Use the current production hit damage under workshop/Forge (Forge still treated as direct numeric effect only) and current hypothetical AM full fire:

| Case or family | Model hit damage × slot shots | F | First-hull effective damage in the slot(s) | Conditional first-carrier/ship death budget |
| --- | --- | --- | --- | --- |
| Barbarian speedboat DEF7, Forge5 | 250 × 16 / 14 | 72.222% | **2,889 / 2,528** vs HP2800 | **1 / 0** |
| Barbarian speedboat DEF8, Forge5 | 240 × 16 / 14 | 72.222% | **2,773 / 2,427** | **0 / 0** |
| Barbarian speedboat DEF14, Forge5 | 180 × 16 / 14 | 72.222% | **2,080 / 1,820** | **0 / 0** |
| Barbarian speedboat DEF3, no Forge | 310 × 16 / 14 | 72.222% | **3,582 / 3,134** | **1 / 1** |
| PvP ATT12/DEF8, both Forge5 | 314 × 16 / 14 | 66.667% | **3,349 / 2,931** | **1 / 1** |
| PvP ATT20/DEF16, both Forge5 | 326 × 16 / 14 | 66.667% | **3,477 / 3,043** | **1 / 1** |
| PvP ATT17/DEF18, both Forge5 | 271 × 16 / 14 | 66.667% | **2,891 / 2,529** | **1 / 0** |
| Barbarian Deckwrecker vs Ram DEF14 | 1160 × **six assumed hits per slot** | 44.444% | **3,093** vs HP3080 | **1** |
| Same vs Ram DEF15 | 1150 × six assumed hits | 44.444% | **3,067** | **0** |
| Same vs Ram DEF19 | 1110 × six assumed hits | 44.444% | **2,960** | **0** |

Thus this **ONE aggregate F formula** is compatible with all **seven carrier observed TOTAL death counts and the three selected Ram per-slot claims**, whereas the literal common T=74 individual selector fails Ram. The model predicts some per-slot casualty assignments, but where the game actually recorded only TOTAL deaths, these assignments are **not factual observations**. The PvP layout 2×15/2×3 and its 16/14 AM addressing are MODEL assumptions. This is a **conditional mathematical consistency check**, NOT 10 independent validations.

**Critical physical objection:** A fixed six successful-hit Ram slot with full indivisible shots of either 1160 or 1150 damage kills one HP3080 Ram ship after **three complete hits in BOTH cases** (3×1160=3480; 3×1150=3450). The `F×gross` amounts 3093 / 3067 are **fractional damage-budget accounting**, not actual combinations of a fixed number of full shots on one target. A genuine executable selector or group-pool model must explain **HOW** the changed numeric damage changes target placement/shot distribution or damage partition between those two defenses. Otherwise it cannot produce DEF14 death1 versus DEF15 death0 from the *same fixed whole-hit target sequence*. Matching thresholds by scalar multiplication alone does NOT solve reverse engineering.

Also the reverse carrier 53%/65% displayed bars remain unexplained by this F first-hull surrogate: it does not specify after-first-kill assignment, excess treatment, per-survivor HP or UI denominators. Keep separate the empirical fit and the existence proof of a playable source-level algorithm.

Research artifacts: `speculative_aggregate_F_surrogate_NOT_same_as_T` in `naval_accuracy_inverse_candidates.json` includes seven source-labeled carrier binary first-kill checks and the three Ram comparisons, with original fixture source provenance included, **without touching production Accuracy**.

## Mandatory falsification — other units and health bars

**Ram ships reject treating T≈74% as a universal rule.** With an isolated six successful-hit model in each synthetic six-ship Flank slot, Barbarian 1160/1150/1110 damage into HP3080 at player DEF14/15/19 yields **2/2/2 deaths** under T=74. The separate user game reports **1/0/0 per stated slot** (DEF19 from a separate chat case, not the Excel F4:F19 series). Even an exhaustive scan over fixed T=0–100 on this exact six-hit model gives **no threshold** that reproduces the 14→15 transition. However, these six shots per slot, complete First-line context, and original attack eligibility are NOT game-proven. The failure narrows the supported explanatory scope, not an official game rule.

**Remaining HP bars require a second unknown mechanism.**
- Barbarian fast to player carrier DEF14 with no kills and full 16/14 effective shots of 180 points predicts `65.714% / 70.000%` -> **65%/70%** if UI floors, matching actual game. This constrains **aggregate** effective damage, not individual targets.
- Reverse *player* fast ATT14/Forge5 into Barbarian carrier with 337 damage and one kill per target slot: T=74 predicts one kill per slot, but sequential lethal-overkill discard loses **233 HP per slot**, leaving **57%/69%** model survivor-slot health (floor). The user game reports **53%/65%**. A numerical **counterfactual** that charges the discarded 233 points back against the survivors would give **53%/65%**, but this is not proof of actual carried overkill, shared slot-damage pools, or UI denominator semantics.
- Ram DEF19 reported 0 deaths and a displayed 63% bar also remains unexplained by this selector, which sinks two of six and leaves other ships at 100% in a six-shot synthetic microprobe.

Thus **7/7 deaths is not 7/7 overall battle outcomes**, and candidate T=74 is **not ready for production**. Verified five-tier naval Help geometry only establishes physical slots/capacity, not target-level Accuracy. Source individual hits are unavailable in the real game report.

## Next discriminating checks and experiment hygiene

- Implement more than one genuinely different selector family (not merely tuning T): e.g. fixed spread/focus, health-relative thresholds, damage-budget batch allocation, or staged per-AM-row concentration; test **one common rule** across carrier and Ram with production numeric stats and controlled full-fleet conditions.
- Treat damage **retention/discard** as an independent axis, including surviving-ship HP bars and second-round carry states. No hidden per-ship game trace is required, only observable round-end counts and slot HP bars.
- Ideally obtain real ship/formation composition for a round with both carrier and Ram participants or an entirely new upgrade/target-HP boundary that was **not** used to fit T. A case with an alternate *target ship HP* or attacked ship count would be highly discriminating.
- Record case source, setting confirmations, *observed vs assumed physical slot kills*, thresholds searched, discarded candidate models and negative results in this note and the long-lived handoff. Keep unmerged Draft, run exact-head CI and request fresh exact-head Codex Review.
- One critical open observation: in the PvP ATT17/DEF18 case **which of the two carrier slots actually lost the one ship**? The model predicts the 16-shot column; direct screenshot would falsify the proposed explanation if the real death is in the 14-shot column.

Run in a clone of PR #69:
```bash
PYTHONPATH=. python tools/research/naval_accuracy_inverse_candidates.py --output research-output/naval_accuracy_inverse_candidates.json
python -m pytest -q tests/unit/test_naval_accuracy_inverse_candidates.py
python -m pytest -q
```

Hosted `.github/workflows/naval-ram-empirical-probe.yml` exports all four model JSON artifacts; the inverse output contains seven raw cases and their known source flags, current baseline, candidate interval, individual-slot model predictions, **failed Ram holdouts**, and counterfactual HP-bar check. No production battle code was edited.
