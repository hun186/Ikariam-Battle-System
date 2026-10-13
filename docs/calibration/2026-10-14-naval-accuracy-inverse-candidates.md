# Naval Accuracy inverse candidates — cross-case integer-hit experiment

> Research-only work in Draft PR #69. Data sources are user chat and workbook fixtures; Gameforge's actual target-selection and overkill algorithms are **not** established. Read `docs/calibration/naval-inverse-engineering-handoff.md` first. Never merge without the owner's explicit authorization.

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

The user has independently verified that **both players had Forge5, 30 speedboats (two 15-ship source slots) vs six carriers (two 3-carrier target slots), and observed one TOTAL carrier sunk by end of Round 1**. They have **not** supplied the physical slot where that one carrier sunk or the two surviving-slot HP bars.

The candidate **T=74%** and modeled 16/14 all-hit address allocation predict this specific **previously unmeasured output**:

| Slot in **model** | Source AM hits in model | Candidate number sunk | Candidate round-one survivor HP bar (floor) | Model individual survivors (NOT visible in game) |
| --- | ---: | ---: | ---: | --- |
| 16-address-hit target slot | 16 × 271 | **1** | **75%** (actual 75.80%) | 2,258 HP; 1,987 HP |
| 14-address-hit target slot | 14 × 271 | **0** | **54%** (actual 54.83%) | 2,258 HP; 2,258 HP; **90 HP** |

**The bars 75%/54% are prospective test predictions, not user-reported facts.** If the actual one sink is in the 14-address-hit slot rather than the 16, or observed bars differ materially after establishing game UI rounding and other fleet effects, the combined 74%-focus/16+14-all-hit/discard-overkill explanation is **falsified for that game setting**. A mismatch by itself does not say which component—AM addressing, successful hit count, selector, support fleet, damage accounting or bar denominator—is responsible. No impossible per-individual target-hit record is required; Round1 per-slot deaths and displayed HP bars suffice.

For other source cases without reported bars, the JSON artifact similarly lists separately labeled, **unobserved model-only** first-round slot-health predictions. Keep that section distinct from the confirmed DEF14 65%/70% real-game bars.

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
