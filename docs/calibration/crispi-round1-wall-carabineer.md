# Crispi battle — Round 1 Town Wall and Sulphur Carabineer calibration

## Evidence

- Real detailed combat screenshot titled **Kauja par crispi1 Rounds 1/8**, timestamp **2026-04-12 10:33:32** (provided in conversation).
- Current simulator export **ikariam-round-1-debug (3).json**, exported **2026-10-08T15:18:27.708Z** (provided in conversation; raw bytes **not** committed).
- Simulator: `land-max`, `wall_level=24`, `town_hall_level=25`, `policy=experimental`. Attacker Forge 5; defender Forge 0. User specifically notes defender 20 surviving Mortars each kill one Hoplite, then Sulphur Carabineers fire, then surviving wall bombs account for two Hoplites. These attributions are the user's empirical interpretation, not independently logged by the in-game client.

## What actually matches and differs

| Attacker loss | Game screenshot | Simulator Round 1 |
|---|---:|---:|
| Hoplite | **52** | **94** |
| Bombardier | 20 | 20 |

| Defender loss | Game screenshot | Simulator Round 1 |
|---|---:|---:|
| Mortar | 10 (five slots of 2) | 10 |
| Bombardier | 30 (two slots of 15) | 30 |
| Wall sections breached | **5 of 7** (physical positions 2–6) | **5 of 7** (damage positions 1–5 = physical positions 2–6) |

Game attacker Hoplite physical-slot losses: **[1, 11, 11, 11, 11, 6, 1]**, 52 total. Simulator: **[9, 16, 16, 17, 16, 11, 9]**, 94 total. Game wall physical line is **[1,0,0,0,0,0,1]** alive, matching the simulator's five breaches in physical positions 2–6. The earlier claim that only three wall sections were breached was a screenshot-reading error. Game defender Hoplites remain in Reserve behind Wall in this screenshot; simulator treats exposed defender Hoplite slots as eligible for immediate same-round First-phase fire.

## User-confirmed wall formation constraints (2026-10-08)

1. Seven active Town Wall sections initially occupy First; defender Hoplites must **not** deploy into First until **the next round** after a wall physical-position vacancy appears.
2. While **any wall section** survives, defender Flank stays **empty**. Flank may fill only **the round after** the last section breaks; open-field battles with suppressed walls use normal Flank deployment.
3. **Only the attacker has Forge Lv5**; the defender has Forge Lv0. Both Gyrocopter groups have zero casualties, while the attacker's Gyrocopters kill 30 defending Bombardiers and defender's Gyrocopters kill 20 attacking Bombardiers.
4. This PR fixes per-round wall **reporting/rendering** only, not the initial wall occupancy, reinforcement timing, Flank lock, or wall offensive mechanics. A visual overlay must not be mistaken for actual engine parity.

## Split the model's 94 losses by actual firing phases

| Simulator source | Hoplites killed |
|---|---:|
| Defender Mortars / Third | **20** |
| Defender Sulphur Carabineers / Second | **24** |
| Defender Hoplites / First | **50** |
| Town Wall | **0** — `EXP-WALL-OFFENSE-NONE-001` explicitly disables offensive fire |
| **Total** | **94** |

Compare the user's candidate actual causal explanation **20 Mortar + 30 Carabineer + 2 Wall = 52**. The same-round defender Hoplite exposure accounts for **50 of the model's 94 deaths**. **Do not** conclude that all 42 extra deaths arise from Firearm Accuracy. The wall is not merely absent from the picture: its offensive firing is absent in the engine, and the premature defender Hoplite deployment and same-round firing are a distinct battle-mechanics mismatch. The observed breach count and positions do match the model in this case.

## Carabineer case: an unusually clear damage-allocation test

Defender 84 Carabineers, 7 Long-range slots × 12, fire at attacker Hoplites. Per debug:

- `attack_upgrade=4`, no Forge: 580 base + 20 Workshop = **600 gross**; Hoplite defense = 20 base + 60 Workshop + 20 Forge = **100**, so **500 net per shot**.
- Each Hoplite has **1120 HP**. Current AM addresses the First-line damage positions with **[14,14,14,14,14,7,7] hits**; the central five positions get 14 × 500 = 7000 net damage each, in principle enough for **six** kills per full slot (6720 HP) if aggregation permits and no overkill is lost; the outer positions get 7 × 500 = 3500 damage each.
- The existing `EXP-ACCURACY-CONCENTRATION-001` + sequential D-kill generates `[4,4,4,4,4,2,2]` kills in damage-position order, **24 total**, and persistent damage remains.
- Subtracting the model's 20 Mortar deaths by physical slot from the actual total gives **[1,6,6,6,6,6,1]**. If the 2 wall deaths occurred at physical leftmost and rightmost positions, the **inferred** Carabineer casualties would be **[0,6,6,6,6,6,0]**, total 30. This is **a constrained hypothesis**, not direct screenshot proof that the wall specifically hit both outer positions; other wall-target distributions would alter the per-position vector.
- The apparent 6 kills in each of the central five physical slots is **numerically compatible** with 7000 / 1120 (integer six-kill threshold), but the 7-hit outer slots demonstrably do **not** behave like a naive global I-kill total. Evidence may involve reduced Attacking Matrix columns and P-/M-kill or redistribution selectors; don't convert this correlation into a universal firing formula.

## RR vs SR vs IR: timing confirmed from Barbarossa's Battle System paper

AT Barbarossa, *Ikariam Battle System* (2020), chapter 4, [published Gameforge forum discussion](https://forum.ikariam.gameforge.com/forum/thread/43268-ikariam-battle-system/), [publicly readable text of the PDF](https://www.scribd.com/document/638484147/ikariam):

- **RR — Reserve Redistribution:** happens **between rounds**, and is applied to surviving members of the **same wave**, including Reserve, before subsequent-round combat. Not between Mortar and Sulphur Carabineer, or between Sulphur Carabineer and the Wall within Round 1.
- **SR — Slot Redistribution:** hypothesized/observed **between firing formations within the same round** (chapter 4.5). Candidate for carrying prior damage from Mortar into Second or onward; **not** RR.
- **IR — Immediate Redistribution:** potential redistribution **inside a slot after individual shots**; applicability is unresolved for the present 500-damage Carabineer test.
- The 2020 paper predates current version-13+ numeric stats; **timing/structure can guide hypotheses but not be assumed to prove current damage formula**.

The current engine explicitly uses `EXP-SR-DISABLED-001`, `EXP-IR-DISABLED-001`, `EXP-WALL-OFFENSE-NONE-001` and `EXP-WALL-ARTILLERY-SUCCESSFUL-HIT-001`. Wall Level 24 has **23,400 HP/section** and each modeled Mortar hit applies **4,522** after armor: **six hits to breach one section**. Counting all 30 modeled hits as successful produces five breached sections, **matching the screenshot's five breached positions (physical 2–6)**. This single case supports the breach-count outcome but does not independently establish a universal wall Accuracy or address-selection formula.

## UI fix delivered in this PR

The existing final `simulation_summary.wall_status.sections_state` is **final-round** wall state. Its values cannot represent Round 1. Previously no `round.wall` existed, so the UI rendered defender Hoplites in Front even while the wall was active.

This PR adds an **immutable per-round `round.wall` snapshot** for regular Experimental simulation, including active/suppressed flag, HP and 7 per-position sections. The browser shows the current-round wall icons and breached locations while the wall is at least partially intact, and the UI explicitly warns that wall offense is **not modeled**. It does not alter `EXP-WALL-OFFENSE-NONE-001`, first-line eligibility, wall successful-hit assumptions or damage calculations.

**Next separate mechanics PR** after multiple cases confirm: test wall attacking phase and shots, defender First-line entry **one round after** a wall gap becomes available, flank deployment only on the round after full wall removal (or immediate open-field), independently verify wall Accuracy across other observations, and test the Carabineer per-slot casualty vector. Do not hide incomplete mechanics by forcing `52` with arbitrary adjustment.
