# REIKJAVIKAS — first-round casualty calibration (30 Mortars, updated 2026-10-08)

## Evidence and assumptions

Actual in-game **REIKJAVIKAS** land-max battle **Round 1/9** screenshot, dated 2026-06-25 14:48:54, was compared with two simulator round debug exports provided in chat. This is the **corrected** baseline from `ikariam-round-1-debug (2).json`, export timestamp **2026-10-08T14:55:26.841Z**, not the superseded 27-Mortar export `(1).json`. Raw private screenshots/debug JSON have not been uploaded to this repository.

**User-confirmed battle setup:** both sides entered Round 1 at full HP. In this **single initial round**, Doctor healing can be excluded from casualty generation and Cook is a morale-only factor; no late-round morale effects are invoked. It is not necessary to re-add absent Cook/Doctor to explain this round's kills. The attacker's previously mistyped Mortars are now **30** (five Artillery slots × six Mortars); the former 27-unit discrepancy is **resolved**. Do not keep citing the old 27-unit input as an outstanding blocker.

The source debug uses `policy=experimental`, `battlefield=land-max`, zero wall, Town Hall 25, both sides Forge 5. Historical actual Workshop values cannot be independently verified from the round screenshot alone; the simulator's entered levels are the best available source for calculations.

## Actual casualties versus corrected simulation

Counts are direct sums of each `(-N)` in the user's actual game screenshot, compared against `current_round.casualties` in the revised debug. Delta = simulation − observed; a negative number is under-prediction.

| Casualty side | Unit | Observed | Corrected sim | Delta |
| --- | --- | ---: | ---: | ---: |
| Attacker | Hoplite | **159** | **137** | **−22** |
| Attacker | Swordsman | **120** | **120** | 0 |
| Attacker | Gyrocopter | **26** | **30** | **+4** |
| Defender | Hoplite | **168** | **161** | **−7** |
| Defender | Swordsman | **132** | **132** | 0 |
| Defender | Bombardier | **30** | **30** | 0 |

The corrected 30 Mortars **did not** eliminate the Front and Air differences. Compared with the superseded 27-Mortar run, attacker Hoplite deaths changed **139→137** and defender Hoplite deaths **158→161**; Gyrocopter deaths remained **30**.

## Physical-slot losses (left → right)

| Unit and side | Observed slot deaths | Corrected simulator slot deaths |
| --- | --- | --- |
| Attacker Hoplite | **21, 23, 25, 25, 24, 23, 18** | 17, 21, 22, 22, 22, 21, 12 |
| Defender Hoplite | **22, 25, 26, 26, 25, 25, 19** | 20, 24, 26, 26, 26, 24, 15 |
| Attacker Gyrocopter | **13, 13** | 15, 15 |
| Attacker Swordsman | 18, 21, 21, 21, 21, 18 | 18, 21, 21, 21, 21, 18 |
| Defender Swordsman | 18, 24, 24, 24, 24, 18 | 18, 24, 24, 24, 24, 18 |
| Defender Bombardier | 15, 15 | 15, 15 |

Slots are displayed in *physical order*, not damage-priority order. On the 7-slot Land maximum field, the damage-position IDs left-to-right are `[6,4,2,1,3,5,7]`.

## Attribution by firing phase: no doctor or cook needed

The revised `current_round_events` reports the following kills (source side → target units):

| Target killed | Enemy Artillery (Third) | Enemy Long-range (Second) | Enemy Front (First) | Total |
| --- | ---: | ---: | ---: | ---: |
| Attacker Hoplite | 30 | 41 | 66 | **137** |
| Defender Hoplite | 30 | 41 | 90 | **161** |

The incoming Gyrocopter / Bombardier exchange is fully in **Air defence**: attacking Gyrocopters fire **30 hits into each of 2 defender Bomber slots**, producing 15 deaths in each (actual also 15); defending Gyrocopters fire **30 hits into each of 2 attacker Gyrocopter slots**, the model predicts 15 each while the actual report has 13 each.

The defender Gyrocopter → attacker Gyrocopter trace uses: net damage **355**, target HP **580**, weapon Accuracy **80**, `EXP-ACCURACY-CONCENTRATION-001`. The deterministic sequential D-kill model assigns 30 hits per slot, kills 15, loses 1950 damage per slot as overkill, and leaves no persistent damage. **Observed 13 deaths per slot does not identify which alternative target-selection or redistribution rule was active.** It could reflect different within-slot concentration, column-based aggregation, weapon interactions or other unmodeled rules. Do **not** convert Accuracy into Bernoulli hit/miss just to achieve 13.

## A critical damage threshold: 372 × 3 = 1116 < 1120

The incoming defender Hoplite → attacker Hoplite hit has **372 net damage** (after current Workshop, Forge and armor calculations). The target has **1120 HP**:

- `372 × 3 = 1116`: 3 hits leave **4 HP**, forcing a 4th under sequential D-kill.
- `374 × 3 = 1122`: 3 hits are lethal, a sharp discontinuity.
- A focused, *offline, non-production* replay of the uploaded first-round `damage` events reproduced **all 44** checked Hoplite/Gyrocopter/Bombardier damage events' kills and overkill using the current Accuracy-v1 selection. Holding the event addresses/shots otherwise fixed and increasing **only defending Front net damage +2** changed attacker Hoplite deaths from **137 to 161** (actual **159**). This is a **sensitivity test, not validation** of changing the effective damage formula. An improper +2 hardcode would simply overfit.

This threshold explains why a small stat/rounding difference **might** lead to a 20+ kill difference and should be examined before changing targeting or dispersal.

## The outermost slots are an independent constraint

The existing Attacking Matrix sends 30 Mortar shots to damage positions 1–6 (**5 per slot**), none to position 7; Long-range has `[14,14,14,14,14,7,7]` shots over damage positions 1–7 and First has `[43,43,43,38,38,37,37]` shots.

For the physical **rightmost** slot (damage position 7), given the model's fixed attack address books and observed incoming hit damage:

| Target slot | Sim Third kills | Sim Second kills | First hits × damage | Pre-First remaining injury | Max possible total deaths even if no overkill | Observed deaths |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| Attacker Hoplite, physical #7 | 0 | 3 | 37 × 372 | 579 | **15** | **18** |
| Defender Hoplite, physical #7 | 0 | 3 | 37 × 422 | 629 | **17** | **19** |

These are upper bounds at the *existing* damage, slot addresses and shot counts, assuming perfect reuse of all surviving pre-First and First damage. Thus **simply redistributing damage between individuals within that same slot cannot, by itself, produce the observed outer-right losses**. One or more inputs, source hit numbers, address-book/AM assumptions, phase chronology or armor/rounding values must differ from the game's process; cross-slot redistributions are another possible mechanism, but not proven.

A 2026 community explanation on the [Gameforge Ikariam forum](https://forum.ikariam.gameforge.com/forum/thread/114964-tutorial-sistema-de-batalha-do-ikariam-3/) reproduces the familiar **84 Carabineer** physical-slot vector `[7,14,14,14,14,14,7]`, matching the *simulator's* current Second-line AM after converting damage-position order to physical order. This is evidence **against indiscriminately replacing AM with uniform distribution**. The exact 30-Mortar/Front AM and redistribution mechanisms still require separate evidence.

## Next controlled investigation — do not patch production formulas blindly

1. **Input gate:** maintain 30 attacking Mortars, full HP at Round 0, all provided Workshop levels and Forge 5; ignore Doctor/Cook for this initial-round combat comparison, as specified by the user. Verify official equipment/level when available.
2. **Damage and arithmetic gate:** log net hit values before and after rounding and the exact HP breakpoints, especially defending Hoplite's 372 vs 374; do not add two damage without a rule/source.
3. **Attacking Matrix gate:** keep source row populations, target slot order, address assignments and freeze timing separately visible for Third/Second/First and both Air source/targets. Outer-slot discrepancies must not be dismissed as within-slot Accuracy alone.
4. **Kill-selection gate:** independently test D-kill/P-kill/M-kill, overkill retention, and *column boundaries*. Historic 2020 research (discussed in the same 2026 Gameforge forum tutorial) records unexplained Gyrocopter-vs-Gyrocopter M-kill behavior. No deterministic general replacement is established.
5. **Evidence-backed patch gate:** propose an engine PR only when one candidate matches both total and per-slot deaths, does not break already matching Swordsmen/Bombardiers, and can pass existing regression tests. Keep Strict unknowns honest and experimental assumptions named.

**Implementation status:** this is a research/calibration update only; the engine's Accuracy, D-kill, Attack Matrix and damage functions are intentionally **unchanged**.
