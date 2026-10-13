# Naval Ram Ship vs Barbarian Deckwrecker — first empirical evidence (2026-10-13)

## Source classification

1. **Observed game measurements**: user-attached Google Drive workbook `野蠻人.xlsx`, worksheet `野撞打開爐衝撞`, observed casualty values **F4:F19**; separately, user's chat statements for player defense Lv19 / attack Lv20 / status bars 63% and 88%. The original workbook is **not committed**.
2. **Current numeric definitions**: hosted `main` at `0887bea9137c070658282c63d91ac1395e31fefa`, player `ram_ship` and `barbarian_deckwrecker`, current Workshop/Forge calculation.
3. **Conditional arithmetic**: six full-health source ships addressing six full-health target ships in one Flank slot; this allocation is an experiment, not observed per-shot telemetry.
4. **Current simulator source**: `ikariam_battle/accuracy.py` `select_accuracy_target` and `ikariam_battle/engine.py` `_apply_sequential_hit`; their results are a **model** and not game facts.
5. **Community theories**: [2020 Battle System](https://www.scribd.com/document/638484147/ikariam) and [2026 Gameforge forum guide](https://forum.ikariam.gameforge.com/forum/thread/114964-tutorial-sistema-de-batalha-do-ikariam-3/) discuss D/P/I/IR kills, attack matrix, surplus damage and redistribution but explicitly are not infallible modern official engine code.

## Empirical fixture

Both Ram types have HP=3080, attack=1500, Accuracy=80; player armor=180, barbarian armor=240, six full Flank slots of six ships each (36 total). User player has Forge Lv5; opponent Barbarian has no Forge/Workshop upgrades. The latter is a different `army_kind`, not the player's base Ram stats.

| Player defense upgrade | Observed player deaths, all six slots | Per-slot deaths | Derived enemy net hit | HP remaining if one hit on one fresh ship |
|---:|---:|---:|---:|---:|
| 3–13 | 6 | 1 | varies by 10 each | not individually recorded |
| **14** | **6** | **1** | **1160** | 62.338% |
| **15** | **0** | **0** | **1150** | 62.662% |
| 16–18 | 0 | 0 | 1140,1130,1120 | not recorded |
| **19** | **0** | **0** | **1110** | **63.961%** (user saw 63%) |

Forge armor +20, current net hit formula `1500−(180+10*defense_level+20)`.

**Critical discontinuity:** 14→15 decreases net hit by 10, while **both** remain three hits to kill 3080 HP (`ceil(3080/1160)=ceil(3080/1150)=3`). This step-function in deaths must arise from a selector, allocation, redistribution, discrete boundary or different original battle conditions — not merely a change to the number of hits per kill.

The user's separate Lv20 attack case gives **1715 net damage** to barbarian 240 armor (`(1500+20×10)×1.15−240`). Conditional on six hits to one 6-ship slot: 6×1715 = **10290**, which equals HP of 3 sunk ships (3×3080=**9240**) + **1050**. If those 1050 are retained among 3 surviving ships, survivor remaining health would be **88.636%**, close to user's observed **88%** (consistent with truncation). With six shots alternating as pairs that each kill a ship, excess damage would be 3×(2×1715−3080)=**1050**.

## Actual exact-head machine experiments

Pinned read-only probe `tools/research/naval_ram_empirical_probe.py` yields two **distinct** experiments.

### A. Current pure 36-vs-36 full-engine simulation — *not the real battlefield*

Only player 36 Rams and barbarian 36 Deckwreckers were provided. At defense 14/15/19, player attack20 held constant. Initial naive expectation was six full Flank slots of six ships. Actual simulator did **not** preserve that formation: it produced **five populated slots** in other runtime lines and **inconclusive** status, reflecting incomplete front-line formation dependencies. Initial model totals:
- player Ram deaths **11** for all three defense grades;
- barbarian Deckwrecker deaths **16** for all three grades.

**These numbers MUST NOT be labeled exact expected deaths for the user's actual fleet battle.** They reflect a different deployment/formation. They are useful to show why exact whole-fleet composition, wave/reserve and per-slot snapshots are necessary.

### B. Exact current single-slot six-hit microprobe — isolates selector mechanics

Directly calls production `select_accuracy_target` and `_apply_sequential_hit` six times on one starting slot of six 3080-HP units with weapon Accuracy=80. There is no AM mapping, external formation, reserves, same-round cross-class fire or healing.

| Incoming direction | Net hit | Six-hit current model deaths | Survivors | Remaining HP bar in current micro-model | Overkill discarded |
|---|---:|---:|---:|---:|---:|
| Barbarian → player DEF14 | 1160 | **2** | 4 | **100%** | 800 |
| Barbarian → player DEF15 | 1150 | **2** | 4 | **100%** | 740 |
| Barbarian → player DEF19 | 1110 | **2** | 4 | **100%** | 500 |
| Player ATT20 → barbarian | 1715 | **3** | 3 | **100%** | 1050 |

The real game instead records **one/player-slot at DEF14, zero/player-slot at DEF15/19 and 63% bar at DEF19; three/barbarian-slot and 88% bar at ATT20**. This controlled comparison gives direct reasons to challenge the current **within-slot focus threshold** and **discard-overkill accounting**, but is not proof of which new formulas to implement.

**What remains unverified:**
- Whether all 6 source attacks were addressed to each slot, whether the game uses per-hit misses or target selection, and whether initial formations included other ships.
- Whether the game UI shows average current HP of only survivors, percent of original maximum total HP, a rounded floor, or another state.
- Whether the 1050 remainder actually comes from overkill or from different hit allocation/redistribution phases (P-kill, SR, IR, RR).
- Whether defense 14→15 triggers an accuracy/rounding selector boundary, a formation change, or some other condition. No fixed 1155-damage cutoff may be inferred as a global rule from one transition.
- The independent case at a different attacking ship count / HP / defender ratio necessary to falsify a candidate.

## Next empirical collection and safety gate

Need original actual battle report and exact simulator input/debug for the **same** battle to confirm all ships, round, each physical Flank slot, any Steam Rams or other formation, wave IDs, arrival, reserve and player armor/attack upgrades. If initial deployed slots are not 6×6 on both sides, reconstruct the exact formation before comparing hit-selection rules. Run model trace against the real fixture with independent observed and simulated fields. Do not merge this research PR or alter any combat/Accuracy formula absent exact-head CI, Codex Review and owner authorization.

**This is a research baseline, not a successful combat-mechanics calibration.**
