# Naval Ram Ship vs Barbarian Deckwrecker — evidence-first calibration (2026-10-13)

## Primary sources and strict provenance

1. **Workbook observations**: the user's Google Drive `野蠻人.xlsx`, sheet `野撞打開爐衝撞`, gameplay casualties in `F4:F19`. These cells describe **total** player casualties for **defense upgrades 3–18 only**. The original private workbook is not committed; other worksheet columns include theoretical formulas and are not themselves observed battle outcomes.
2. **Separate chat observations**: the user explicitly stated that with player Forge Lv5, defense upgrades 3–14 cause a total loss of six Rams, described as **one dead in each of six Flank slots** (five remaining per slot); upgrade 15 causes **zero dead, all damaged**. This finer slot-level description is **reported by the user in chat, not independently recorded as per-position measurements in the workbook F cells**.
3. **Another separate user-chat case**: player defense **Lv19**, attack **Lv20**, Forge Lv5: player deaths 0 and displayed bar **63%** per reported slot; barbarian Deckwrecker deaths **3 per reported slot**, bar **88%**. **Defense Lv19 is not in workbook F4:F19**; no per-shot traces or original battle screenshots have been supplied.
4. **Current model**: packaged `UnitRegistry.load(include_barbarians=True)`, `WorkshopProfile.load()`, `ForgeProfile.load()`, production `calculate_damage(..., rounding=FLOOR)`, `select_accuracy_target`, `_apply_sequential_hit`, and `simulate`. These define *model predictions*, not observed game algorithms.
5. **Independent geometry**: user-provided Gameforge Sea Fight Help diagrams now merged into `main` by PR #70, merge SHA `f170726121990d28dde10d736ba9c03c49a08800`. Five supported naval tier IDs are selectable; max First=7×25, Second=7×25, Third=5×15, Flank=6×20. Help does **not** prove Attack Matrix physical priority or source-level auto-selection.

## Current conditional arithmetic

Current profiles define both ships with HP 3,080, base weapon damage 1,500 and Accuracy 80; the player's base armor is 180 versus barbarian Deckwrecker armor 240. Workshop naval increment, Forge multipliers and bonuses must be read from the packaged profiles. The probe now calls `calculate_damage` rather than hard-coding those values.

| Defense upgrade | Workbook **total** player deaths | Separate chat per-slot claim | Derived enemy net hit | Remaining HP from ONE independent hit |
|---:|---:|---:|---:|---:|
| 3–13 | 6 | 1 in each of six Flank slots | decreases 10 / upgrade | not individually recorded |
| **14** | **6** | **1 in each slot** | **1,160** | 62.338% |
| **15** | **0** | **0 in each slot** | **1,150** | 62.662% |
| 16–18 | 0 | no individual position breakdown independently captured | 1,140 / 1,130 / 1,120 | not recorded |
| **19 (chat, not workbook)** | **not in F4:F19** | **0 per reported slot** | **1,110** | **63.961%** (reported bar 63%) |

**Important threshold observation:** `ceil(3080/1160) = ceil(3080/1150) = 3`. A ten-point reduction in net hit damage at defense 14→15 does not by itself cross an integer 3-to-4-hit-to-kill threshold, even though the total observed deaths change from 6 to 0. The difference needs a targeting, redistribution/rounding or actual context explanation; it does **not** prove any particular Accuracy mechanism.

At player attack upgrade 20, Forge Lv5 against enemy armor 240, net damage derived from production profiles is **1,715**. In a hypothetical six-hit *single-slot* model: six successful hits give 10,290 damage; three enemy kills would account for 9,240 HP. **If** the remaining 1,050 were retained as damage on exactly three survivors, their average remaining HP would be **88.636%**, consistent with reported 88% if UI truncates. This is a **conditional equivalence only**: neither six successful strikes/address selection nor excess-damage transfer nor UI rounding has been verified from the user's game trace. It must **not** be promoted to an implemented global Overkill rule from this one numeric match.

## Two deliberately different current-engine experiments

### A. Synthetic whole battle (36 Barbarian Deckwreckers vs 36 player Rams)

Player Forge Lv5, attack upgrade 20, defender armor upgrades 14/15/19, naval-max, one round. In this **pure Ram-only** scenario, the current formation rules allocate the 36 Light/Flank-native Rams to **First** fallback slots, yielding **8+8+8+8+4**, not six full Flank slots of six units. The documented initial model comparison before main's Help geometry correction produced player losses 11, barbarian losses 16 and an inconclusive battle-end outcome, not an observed user's deployment. The probe now emits the **actual current main-derived initial layout** for every run; refresh all synthetic counts using the hosted exact-head Actions artifact.

**Do not compare whole-battle totals with real Flank deaths as if deployment were equal.** The user's original opposing First/other naval forces, wave IDs and battle screenshots are not in the fixture. Also `inconclusive` after `max_rounds=1` is not necessarily a simulator error: both sides can still have surviving forces.

### B. Isolated six-hit target-selection microprobe

Six consecutive net hits are artificially directed into one full-health slot of six targets. **Hit damage, HP and weapon Accuracy are derived from the live packaged units, Workshop and Forge via `calculate_damage`**. The routine calls the exact current `select_accuracy_target` and `_apply_sequential_hit`, but does **not** use actual game firing counts, AM addresses or a complete mixed-ship battle.

| Incoming direction | Net hit | Model deaths in six hits | Survivors' average HP | Model overkill discarded |
|---|---:|---:|---:|---:|
| Barbarian → player DEF14 | 1,160 | 2 | 100% | 800 |
| Barbarian → player DEF15 | 1,150 | 2 | 100% | 740 |
| Barbarian → player DEF19 | 1,110 | 2 | 100% | 500 |
| Player ATT20 → barbarian | 1,715 | 3 | 100% | 1,050 |

The current Experimental concentration hypothesis focuses the same damaged unit when remaining HP% drops below Accuracy (80); the current sequential hit resolver discards lethal excess. Those behaviors, **if** six hits really reach each real game Flank slot, contradict the user's reported no-death 63% bar and opponent 88% surviving bar. The counterfactuals provide testable mechanism candidates, not proof of how the official game computes hit selection or HP bars.

### C. Synthetic six-Flank-slot formation with *invented* heavy front fillers

For a stronger geometry-control experiment (not a historical reconstruction), place:
- **Player defender:** 35 `steam_ram` at First (7 slots × 5 ships) plus 36 `ram_ship` at Flank (6 slots × 6).
- **Barbarian attacker:** 42 `barbarian_wedge_paddler` at First (7 slots × 6 ships) plus 36 `barbarian_deckwrecker` at Flank (6 slots × 6).
- Invented filler units' levels are fixed at zero; actual player Ram Workshop/Forge settings follow the controlled input, and Barbarian Forge/Workshop remain zero.

These ships were **not observed in the user's battle**. Their sole purpose is to satisfy the currently executable First→Flank placement mechanics and avoid misreading First fallback as Flank combat. The hosted synthetic probe now confirms **six genuinely populated Flank slots, six Rams per position on each side**. At player defense 14/15/19 and fixed player attack 20/Forge 5, the *current model* reports:

| Synthetic player DEF level | User-observed player total deaths (Excel 3–18; chat 19) | **Synthetic model** player deaths | **Synthetic model** Barbarian deaths |
|---:|---:|---:|---:|
| 14 | 6 | **12** | **18** |
| 15 | 0 | **12** | **18** |
| 19 | 0 (chat) | **12** | **18** |

This is a more useful **controlled geometry** result than the Ram-only First fallback. It still cannot prove that the difference comes from Accuracy alone: the fabricated heavy front lines affect other attack phases, and original screenshots, round state and combat sequencing are missing. Its Barbarian total of 18 equals 3 per six hypothetical Flank slots, but the source-slot kill assignment and user 88% display remain independently unverified. Do not use a numeric match to force overkill redistribution into the production engine.

## Research gaps and validation plan

- Need full original battle input, per-round actual screenshots and corresponding simulator Debug JSON to confirm battlefield tier, **all** deployed First/Second/Flank ships, arrivals/reinforcements, player Workshop and Forge levels, selected wave ownership and simultaneous phases.
- Keep user-reported per-slot Flank assertions in a **separate chat evidence field** from workbook totals. If screenshots do not corroborate positions, retain the stronger source distinction.
- Before any code changes to general Accuracy, D/P/IR/SR/RR/Overkill, reproduce a true six-Flank-slot formation plus unrelated first-line participants in both the current model and a held-out independent battle.
- UI bar meaning (averaged only over surviving ships, rounding/truncation, redistributed slot-damage display) is not proven; test separately.
- An independent second scenario varying unit count, weapon damage or upgrade level is needed to discriminate selector rules rather than fitting a fixed casualty lookup.

**State:** research, not engine calibration. No official formula has been verified or modified. Leave Draft PR #69 unmerged until its own exact-head CI and fresh Codex Review are complete and the owner explicitly authorizes merge.
