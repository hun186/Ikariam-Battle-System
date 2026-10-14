# Land Barbarian battle — verified rounds 80–89, source casualty / reserve / displayed HP inverse research

> **Research-only, source-grounded, not a Gameforge combat-rule specification.** Created 2026-10-14 for [Issue #71](https://github.com/hun186/Ikariam-Battle-System/issues/71). Keep independent of NAVAL Draft PR #69 and its Accuracy/overkill calibration. Do not merge or change the production battle engine without explicit authorization.

## 0. Quick start for the next AI agent

1. Inspect Hosted GitHub **main**, this research branch `research/land-barbarian-rounds80-89-observations`, issue #71, Draft PR if opened, last exact-head CI, last exact-head Codex Review and unresolved threads; never assume a historical review approves current head.
2. Read the **user-verified** machine-readable fixture `tests/fixtures/reverse_engineering/land_barbarian_rounds80_89_20261014.json` and the corresponding static regression `tests/unit/test_land_barbarian_rounds80_89_research.py`.
3. Distinguish **(i)** owner-confirmed casualty labels and provided slot HP %, **(ii)** other screenshot-transcribed reserve/remaining unit counts, **(iii)** cross-round conservation calculations, **(iv)** *hypotheses* of engine mechanics. Screenshots were attached in the originating ChatGPT conversation (ten PNG images), not committed to this repository; if raw pixels are required for new automated processing, request source image access. The long-lived numeric fixture is independently useful without them.
4. Examine current Land engine's `attacking_matrix` addressing, first/second/third firing order, target eligibility `ATK>DEF`, Forge and Workshop, ammunition/reload and existing `same-wave` / `cross-wave` refill rules. Do not import NAVAL Accuracy assumptions as Land facts.
5. A useful first goal is to explain front-line **loss patterns with reinforcement capacity constrained**. Follow with models predicting newly measured adjacent-round totals/slot distribution, without requiring game-hidden per-individual shot logs. Keep a research-only experimental probe; don't hard-code round numbers or verified casualties as combat outputs.

## 1. Actual visual evidence and explicit confirmations

This is one lengthy Barbarian Village attacking/defending battle. User's **player musketeers Workshop Attack Lv11 / Defense Lv3**. The ten screenshots span rounds **80,81,82,83,84,85,86,87,88,89** in ascending order. The user explicitly confirmed:

- `35 (-15)` means **35 remaining displayed and 15 lost IN THAT ROUND**, not total losses across all previous rounds.
- Earlier assistant transcription of **all Barbarian seven-cell front-line deaths for rounds80–89** was correct.
- The player at round80 had **84 main-line + 19 siege-unit deaths** (the seven `0(-12)` cells and the siege `0(-6)×3`, `0(-1)`).
- Supplied front-line seven-cell *displayed surviving-health bar percentages*, in rank order L→R, including central anomalies.

Do NOT infer every Barbarian death was necessarily caused by the user's musket attack alone. Other player army sources, passive wall rules, phase sequencing and units not represented by a single icon might be relevant.

| R | Barbarian per-cell deaths L→R (— is EMPTY, not zero) | Total | Fourth cell (central special axe) remaining | Fourth cell HP% | Ordinary-melee reserve (image read only) |
|---:|---|---:|---:|---:|---:|
| 80 | 3, 3, 3, 4, 3, 3, 0 | **19** | 45 | 99 | 310 |
| 81 | 8, 15, 15, 8, 15, 15, 8 | **84** | 37 | 99 | 535 |
| 82 | 8, 15, 15, 8, 15, 15, 8 | **84** | 29 | 99 | 459 |
| 83 | 8, 15, 15, 8, 15, 15, 8 | **84** | 21 | 99 | 383 |
| 84 | 15, 15, 15, 5, 15, 15, 8 | **88** | 16 | 97 | 307 |
| 85 | 15, 15, 15, 5, 15, 15, 8 | **88** | 11 | 92 | 224 |
| 86 | 15, 15, 15, 6, 15, 15, 8 | **89** | 5 | 96 | 141 |
| 87 | 15, 15, 15, 5, 15, 15, 8 | **88** | 0 | 0 | 58 |
| 88 | 16, 15, 15, 15, 15, 15, — | **91** | — (no axe) | all occupied cells 100 | 0 |
| 89 | —, 25, 22, 22, 22, —, — | **91** | — (no axe) | all occupied cells 100 | 0 |

**Full 7-cell HP readout reported by owner:** R80–R83 `100/100/100/99/100/100/100`; R84 `100/100/100/97/100/100/100`; R85 `100/100/100/92/100/100/100`; R86 `100/100/100/96/100/100/100`; R87 `100/100/100/0/100/100/100`; R88 and R89: all *occupied* cells displayed 100. **The scope of the UI denominator and the meaning of 100% are NOT verified.**

The whole user-confirmed row-total series sums to **806** displayed deaths from R80 through R89. This is an arithmetic sum of round-specific casualty labels, **not** a claim that the entire battle had only 806 Barbarian casualties; it may have other combat lines/rounds.

**Other screenshot transcriptions, not separately owner-confirmed:** top rear rank seven groups of `50(-0)`; R80 side flanks `40(-0)`; R81–R89 player's on-field seven groups `12(-0)` and seven wall sections `1(-0)`; reserve numbers as above. This secondary visual evidence must retain its weaker provenance classification.

## 2. Conservation checks: a rare way to factor away reinforcement confounding

### A. The central axe group is arithmetically self-contained

Central distinct-image holder's shown survivors R80..87 are:

`45 → 37 → 29 → 21 → 16 → 11 → 5 → 0`

The death labels are `4,8,8,8,5,5,6,5`. The first shown state is compatible with a **49-unit group** (`45+4=49`). All next decreases satisfy `remaining_r − remaining_(r+1) = deaths_(r+1)`. Total deaths **49**. No visible refill is needed to explain this particular unit group over this window; it is not evidence of a general "axe cannot refill" official rule. On R88 that occupant has disappeared and ordinary front units use other positions.

### B. Ordinary-melee reserves balance repeated 15-casualty slots

Separate the central axe from all other front losses on R81–R87:
- R81–R83: each total84 − central8 = **76 ordinary melee casualties**.
- R84–R85: each total88 − central5 = **83 ordinary melee casualties**.
- R86: total89 − central6 = **83 ordinary casualties**.
- R87: total88 − central5 = **83 ordinary casualties**.

Visual ordinary reserve snapshots show:

`535 → 459 → 383 → 307 → 224 → 141 → 58 → 0` for R81→R88.

Adjacent reserve drops for R81→R82 through R86→R87 are exactly `76,76,76,83,83,83`, equal to ordinary losses at those previous turns. The drop R87→R88 is only **58** despite the previous row displaying 83 ordinary losses, **consistent with reserve exhaustion/capped replenishment** and next-round loss of full slot occupancy. The reserve rise R80→R81 `310→535` is a **225-unit increase**, NOT explained by normal losses; R80 shows open field while R81 onward shows a walled setting, so possible reinforcements/re-entry/rebuild need independent analysis.

This excellent arithmetic is **strong evidence** for a reserve-to-front replenishment step, even though it does **not** independently settle the exact snapshot order or official placement/ranking rule.

### C. Front attrition versus redistribution at depleted reserve

R87 has 7 occupied front cells and loses 88 units including the final 5 axe. R88 has **6 occupied cells and loses 91**; R89 has **4 occupied cells and loses 91**, despite the reserve becoming empty. More casualties per surviving physical cell become visible; may reflect **target-address redistribution** as the target set contracts. But other variables might have changed (eligible target set, damage priorities, one-shot caps, ammunition, shooter quantities), so **91 constant is a pattern, not proof of a fixed damage-budget rule**.

### D. Exact endgame population conservation across formation compaction

**A stronger independent arithmetic finding than fixed per-slot death counts:** Screenshot-read ordinary female melee remaining units for R87/R88/R89, combined with user-verified round deaths and visual reserves, reconcile **without losing or inventing a single ordinary melee unit** across R87→R88→R89.

| Stage | Ordinary melee on occupied front slots | Ordinary reserve | Combined |
|---|---:|---:|---:|
| R87 **end** | `35+35+35+35+35+42=217` (axe slot at zero excluded) | **58** | **275** |
| R88 **before round damage**, reconstructed | six slots `25+50+50+50+50+50=275` | **0** | **275** |
| R88 **end** | six slots `9+35+35+35+35+35=184` | **0** | **184** |
| R89 **before round damage**, reconstructed | four slots `34+50+50+50=184` | **0** | **184** |
| R89 **end** | four slots `9+28+28+28=93` | **0** | **93** |

The equations are exact:

```
R87-end visible ordinary 217 + reserve 58 = 275
R88 killed = 16+15+15+15+15+15 = 91
R88-end visible = 9+35+35+35+35+35 = 184 = 275−91
R89 killed = 25+22+22+22 = 91
R89-end visible = 9+28+28+28 = 93 = 184−91
```

Reconstructed R88-before slot counts `25,50,50,50,50,50` and R89-before `34,50,50,50` follow **mechanically** from shown remaining+round deaths; these before-round slot counts were **not directly seen as complete Gameforge target log states**. They suggest **same-type group consolidation across physical positions, then refill/reuse of reserves**, and provide a stringent conservation property for a candidate Land formation-rebuild algorithm. They **do not uniquely determine** Gameforge's target-address sequence or individual HP distribution.

The data could be an especially useful held-out test for code implementing cross-slot compaction: force a model to pass `217+58→275→184→93` with the proper 7→6→4 visible slot identities *without injecting fake units or killing unseen units*. Beware reserve screenshot transcription has not been independently confirmed by owner, and stage labels before/after-round are deductions based on UI interpretation.

### D. Restrictive "84 visible defenders each kill at most one enemy" theory fails

From R81 onward, screenshots show **seven** defender positions labeled `12(-0)`, i.e. **84 visible deployed units** in those positions (unit-type identity and attack source/weapon role not independently established). The Barbarian front-line displayed kills are **84** on R81–83, but increase to **88/89** on R84–87 and **91** on R88–89. Therefore **IF** those 84 were the ONLY damage-dealing source, **IF** each fired exactly ONE hit per round, and **IF** each hit could kill at most one target, totals greater than 84 are impossible. At least one assumption of that overly restrictive mechanism would have to fail: other firing lines, wall damage, multi-shot/extra attack, multi-target effects, casualty phase differences, game UI source semantics, etc. The images alone cannot determine which.

Crucially **don't assert** these seven `12(-0)` displayed groups are necessarily the player's 84 musketeers or the only attackers. The owner provided musket Workshop ATT11/DEF3 but did not supply a weapon-by-weapon fire ledger. This bound is a **falsifying sanity check on a narrow hypothetical**, not proof of more than 84 musket hits.

### D. Health bar rises as unit count falls

R85 central axe = **11 remaining, HP bar 92%**; R86 central axe = **5 remaining, bar 96%**; R87 unit count0, bar0. If the UI bar represents **average HP of living survivors**, the bar can rise naturally when the worst-wounded individuals die, without any healing. It might instead reflect another aggregation/replacement rule. Treat `92→96` as an important counterexample to naively interpreting bars as cumulative damage to an immutable group.

## 3. Significant confound at R80→R81

R80 appears to be an **open field** setup, with player's seven main slots at `0(-12)` and siege at `0(-6),0(-6),0(-6),0(-1)`, all confirmed casualties. R81 onward pictures show **seven castle wall sections and seven fresh `12(-0)` player units**, so it is NOT a controlled identical-formation repeat of R80. Do not attribute jump `19→84` enemy casualties to a change in Accuracy alone. Evaluate wall appearance, unit lineup, phase changes and actual reinforcement order; official timing must be proven independently.

Player screen reserve reading also suggests 1184 at R80 and 1100 from R81 onward, a drop of 84, matching newly deployed seven groups ×12, but this is **only screenshot transcription** and may indicate refilling rather than new losses. Do not use it to double-count player casualties.

## 4. Candidate model families worth testing independently

1. **Fixed per-slot shot address with replacement:** baseline attacks fixed target slots; ordinary units die and refill up to slot capacity. Predict repeated `35(-15)` and `42(-8)`; check whether reserve moves match previous-round casualties.
2. **Readdress targets after a cell disappears:** with N active physical slots shrinking 7→6→4, rebuild shared `attacking_matrix` and compare visibility of `16`, `25`, `22` kills, subject to casualty cap. Must not repurpose NAVAL model's 16/14 assumption.
3. **Finite-ammo/source-line phase and priority:** identify exact attacking musket position, player's other combat source units and wall source status before attributing 84–91 deaths to one type of shot. Use packaged `calculate_damage` and source unit registry to test quantitative predictions.
4. **Group-health display models:** remaining-HP weighted by live individual units, possibly survivor-only versus initial-unit denominator. Compare the non-monotonic `99,97,92,96,0` center bar. Avoid fabricating per-individual game shot histories.
5. **Reinforcement limitations:** separately audit non-axe melee reserve consumption and central axe no-refill. The observation that reserve drops correlate with non-axe losses is a stronger starting constraint than a presumed global Accuracy parameter.

For every candidate, retain exact scene/round scope, unit-ID mapping confidence, high-vs-low provenance, predicted casualty counts by **slot**, reserve residuals and user-provided health percentages. Mark each compatible / incompatible / underdetermined. Never modify the production engine merely to get 806 casualties.

## 5. Long-lived audit references

- [Issue #71](https://github.com/hun186/Ikariam-Battle-System/issues/71) tracks this **Land** sequence.
- `tests/fixtures/reverse_engineering/land_barbarian_rounds80_89_20261014.json` is the canonical typed numerical evidence; `tests/unit/test_land_barbarian_rounds80_89_research.py` pins confirmed totals, 49 central deaths, and the reserve reconciliation checks.
- Original screenshot filenames are listed in the JSON fixture but **the images are not committed to Hosted GitHub**; preserve them in this ChatGPT conversation. Do not claim an AI in a new conversation can visually inspect them without reattaching/uploading.
- NAVAL model studies remain separate in Draft PR #69 and [Issue #68](https://github.com/hun186/Ikariam-Battle-System/issues/68); do not use inferred naval 74% or F(A,N) as verified Land calculations.
- To resume: verify Hosted main, Land research Draft PR and exact-head review; run `python -m pytest -q tests/unit/test_land_barbarian_rounds80_89_research.py` and then full `python -m pytest -q`; compare current Land engine event traces against observed within-round casualty maps. Observe the rule that a change in front formation or reserve levels is not a change in the target-selection algorithm.

**Status:** Separate user-confirmed observations and research cases. No official focus mechanism has yet been inferred, and no production combat formula changes are authorized.
