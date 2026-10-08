# REIKJAVIKAS: Round 1 battle-report calibration baseline

**Evidence captured:** 2026-10-08; **battle shown:** 2026-06-25 14:48:54, Round 1/9, land-max. This record compares the user's *actual in-game round screenshot* with the user's exported simulator debug `ikariam-round-1-debug (1).json` (exported 2026-10-08T14:41:36Z). Both artifacts were shared in chat; their original bytes are **not** stored in this repository.

## First normalize the scenario

The two sides' battlefield visuals are similar, but the simulator inputs are **not identical** to the in-game battle:

| Attacker force | In-game screenshot | Simulator exported scenario |
| --- | ---: | ---: |
| Mortar | 30 deployed (5 slots × 6) | **27** (one 3-unit slot, four 6-unit slots) |
| Cook | 33 in Reserve | **0 / absent** |
| Doctor | 40 in Reserve | **0 / absent** |

These differences matter before treating a kill mismatch as a flaw in Accuracy / targeting. The screenshot does not expose complete per-unit upgrades and all stateful damage; the debug contains configured Workshop/Forge input levels, but identical real upgrades cannot be independently proven from the image alone.

## Round-1 casualties: actual versus simulator

The following actual values are sums of the explicit `(-N)` casualty labels on the screenshot. The simulator values come from `current_round.casualties` in the exported debug. Delta = simulator minus actual, not vice versa.

| Casualty side | Unit | Actual | Simulator | Delta |
| --- | --- | ---: | ---: | ---: |
| Attacker | Hoplite | **159** | 139 | **−20** |
| Attacker | Swordsman | 120 | 120 | 0 |
| Attacker | Gyrocopter | **26** | 30 | **+4** |
| Defender | Hoplite | **168** | 158 | **−10** |
| Defender | Swordsman | 132 | 132 | 0 |
| Defender | Bombardier | 30 | 30 | 0 |

Slot-level physical left-to-right casualties provide a more precise calibration target than totals:

| Side / Unit | Actual seven/six/two slots | Simulator | Comment |
| --- | --- | --- | --- |
| Attacker Hoplite | 21, 23, 25, 25, 24, 23, 18 | 17, 22, 22, 23, 22, 21, 12 | Distributed differences, especially outer slots |
| Defender Hoplite | 22, 25, 26, 26, 25, 25, 19 | 19, 23, 26, 26, 26, 23, 15 | Outer slots deviate |
| Attacker Gyrocopter | **13, 13** | **15, 15** | Air-defense damage/individual selection candidate |
| Attacker Swordsman | 18, 21, 21, 21, 21, 18 | 18, 21, 21, 21, 21, 18 | Exact slot-level match |
| Defender Swordsman | 18, 24, 24, 24, 24, 18 | 18, 24, 24, 24, 24, 18 | Exact slot-level match |

## Engine-event diagnosis from exported debug

- The experimental model computes the defender's Gyrocopter → attacker's Gyrocopter net **355 damage per shot**, with 30 addressed shots against each of two 30-unit air-defense slots. It predicts **15 casualties per slot**, `persistent_damage=0`, and `overkill_discarded=1950` per slot, while the screenshot shows **13 deaths per slot**.
- The trace shows `weapon_accuracy=80`, `accuracy_model=EXP-ACCURACY-CONCENTRATION-001`, and `accuracy_decisions={spread_above_accuracy_threshold:15, focus_below_accuracy_threshold:15}` on these Gyrocopter targets. This is a *current experimental concentration hypothesis*, not a verified official hit/dispersion formula.
- The simulator's attacker Hoplite casualties split by enemy firing phase: `third=30`, `second=41`, `first=68` (total 139). Defender Hoplite: `third=27`, `second=41`, `first=90` (total 158). The missing three attacker Mortars plausibly influence the `third` phase against defenders; they **cannot by themselves establish** why attacker Hoplites lose 20 more in the real battle.
- The close match for both Swordsman formations and defending Bombardiers suggests **not** globally changing damage, target addressing or kill rounding to force the Hoplite/Gyrocopter totals.

## Next calibration experiment (not implemented in this UI PR)

1. Align the simulator scenario to the screenshot: attacker Mortar=30, Cook=33, Doctor=40; verify all real Workshop upgrades, Forge buffs, battle starts and any preceding persistent damage. Rerun and save a *new* Round-1 export.
2. Compare damage events by **firing phase, target slot, source count, effective damage, kills, persistent damage and overkill** against the observed casualty arrays above.
3. For Gyrocopters, test multiple **damage concentration / individual target distribution** policies on independent observed rounds, preserving Attacking Matrix addressing, units fired, ammo, armor, and firing order. With one round, 13 versus 15 could arise from different individual selection/spread, another combat effect, or hidden initial state; it does **not** uniquely identify a new Accuracy formula.
4. Treat changes to the engine as a separate evidence-backed calibration PR with reproducible tests. Keep Strict mode unknown guards; in Experimental, mark the chosen hypothesis and quantify regressions on known cases.

**Scope of this PR:** remove formation line text headings from the *round board only*, keep setup/reference labels, tooltip accessibility and all battlefield slot/targeting/weapon mechanics unchanged. Numerical differences are documented, **not silently tuned**.
