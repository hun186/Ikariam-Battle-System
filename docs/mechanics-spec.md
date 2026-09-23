# Mechanics and current-data evidence register

The simulator combines empirical mechanics with current numerical profiles; it is not Gameforge source code. Evidence classes remain separate: `OFFICIAL_CHANGELOG`, `GAMEFORGE_FORUM_PLAYER_TEST`, `COMMUNITY_PTS_TESTED`, `COMMUNITY_REFERENCE_CURRENT`, `EMPIRICAL_PAPER`, `DERIVED`, `HYPOTHESIS`, and `UNKNOWN`. Sources verified by the reviewer are marked `REVIEWER_WEB_VERIFIED`, not `CODEX_NETWORK_VERIFIED`.

## Versioned profiles and source matrix

| Profile/feature | Evidence | Status |
| --- | --- | --- |
| `battle-system-paper-2020`: Am, physical renumbering, RR | EMPIRICAL_PAPER | implemented; current calibration required |
| SR, IR, partial chronology | EMPIRICAL_PAPER | observed; triggers/generalization UNKNOWN |
| Kill selection, non-standard renumbering | UNKNOWN | strict stops |
| `infinite-horizons-current` complete land/sea values | COMMUNITY_REFERENCE_CURRENT | reviewer web verified 2026-09-24 |
| Naval raw values | COMMUNITY_REFERENCE_CURRENT + GAMEFORGE_FORUM_PLAYER_TEST, *Workshop Tests: Ship Technology*, 2025-06-04 | reviewer web verified |
| v14 Workshop ×5 and Forge direction change | OFFICIAL_CHANGELOG, v14.0.0, 2025-05-21 | reviewer web verified |
| Workshop exact land +5 / naval +10 | COMMUNITY_PTS_TESTED | not promoted to official |
| Forge exact levels 0–5 | COMMUNITY_PTS_TESTED | not promoted to official |
| Doctor/Tender healing ×20 | OFFICIAL_CHANGELOG, v17.0.0, 2026-04-16 | reviewer web verified |
| legacy healing 200 → current 4000 | legacy community/paper + DERIVED | allocation UNKNOWN |
| Cook/Doctor/Tender garrison exclusion | OFFICIAL_CHANGELOG, v17.4.0, 2026-08-11 | applies only to these support units |
| verified-through release | OFFICIAL_CHANGELOG, v17.5.0, 2026-09-08 | no later military/profile change reported |
| `legacy-community-land-targeting` | COMMUNITY_REFERENCE | experimental/calibration policy |

## Workshop and Forge ownership

Workshop levels belong to a player’s **unit type**, not the whole army. Every `ArmyUnit` has `attack_upgrade` and `armor_upgrade`; all rows/waves of the same `unit_id` on one side must agree. Duplicate rows aggregate only when unit, wave, and upgrades agree. Forge remains side-wide at level 0–5.

## Battlefield geometry

`land-mini` means Town Hall 1–4/minimum. It has front 3, long-range 3, flank 0, artillery 1, bomber 1, and anti-air 1 slots. Other stable IDs (`land-small`, `land-medium`, `land-large`, `land-max`) are reserved and rejected until profiles are supplied.

A line stores `slot_space`, not a unit capacity. Deployment uses `floor(slot_space / unit.size)`. With slot space 30 this yields Hoplite 30, Steam Giant 10, Carabineer 7, and Catapult 6. Slots retain physical position and damage position separately. Am targets ascending damage positions; only vector export uses physical order. RR remainder follows damage priority and preserves deployed + reserve wave damage.

## Ammunition, targeting, accuracy, and support boundaries

Finite ammunition is a wave shot pool initialized as `wave quantity × ammo per unit`. Each firing unit consumes one shot. A final partial volley uses named `EXP-AMMO-PARTIAL-ORDER-001`; an exhausted primary does not silently switch weapon.

Experimental targeting uses versioned priorities and `EXP-TARGET-LEGACY-001`: artillery front→flank; long-range front→flank→long-range; front front→long-range→artillery→flank; flank flank→long-range→artillery→front; anti-air bomber→anti-air; bomber artillery→long-range→front→flank. Transfer remains calibration-dependent. In particular, a Swordsman selects enemy flank before front.

Accuracy is stored per weapon, including different secondary accuracy. No complete accuracy algorithm is known: strict emits `UNKNOWN-ACCURACY`; experimental emits `EXP-ACCURACY-IGNORED-001` rather than silently claiming 100% accuracy.

Support effects are distinct: Doctor/Tender are `healing`, Cook is `morale`. Strict uses `UNKNOWN-HEALING-ALLOCATION` and `UNKNOWN-MORALE-SUPPORT`; experimental uses separate `EXP-HEAL-NONE-001` and `EXP-MORALE-NONE-001`. Support never enters Am.

## Other experimental policies and remaining unknowns

Named policies include pooled I-kill, floor rounding, phase-start simultaneous chronology, no within-phase retarget, RR deployed-total rounding, ammo stop/partial ordering, legacy targeting, ignored accuracy, and separate no-healing/no-morale effects. Responses and events expose IDs. Remaining unknowns include kill selection, rounding selector, SR/IR triggers, complete chronology, target transfer after destruction, mixed-unit/multi-wave Am, secondary weapon trigger, healing/morale allocation, accuracy, non-standard renumbering, naval geometry, and long-duration intervals.

`BattleReportFixture` retains game version, complete scenario, round, casualties, damage%, and life%; damage display percentages can be converted to integer intervals rather than hard-coding a winner.
